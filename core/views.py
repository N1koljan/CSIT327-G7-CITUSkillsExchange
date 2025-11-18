from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import CustomSignUpForm, SkillRequestForm, BarterProposalForm, FeedbackForm
from .models import CustomUser, Skill, Request, BarterProposal, Transaction, Rating
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def signup_view(request):
    if request.method == 'POST':
        form = CustomSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Account for {user.username} created successfully! You can now log in.')
            return redirect('login')
    else:
        form = CustomSignUpForm()
    return render(request, 'ui/auth/signup.html', {'form': form})


@login_required
def create_skill_request(request, skill_id):
    skill = get_object_or_404(Skill, id=skill_id)

    if skill.owner == request.user:
        messages.error(request, "You cannot request your own skill.")
        return redirect('find_skills')

    existing_request = Request.objects.filter(skill=skill, requester=request.user).first()
    if existing_request:
        messages.warning(request,
                         f"You have already sent a request for '{skill.title}'. Its status is '{existing_request.get_status_display()}'.")
        return redirect('find_skills')

    if request.method == 'POST':
        form = SkillRequestForm(request.POST)
        print("Form errors:", form.errors)
        if form.is_valid():
            new_request = form.save(commit=False)
            new_request.requester = request.user
            new_request.skill = skill
            new_request.save()

            channel_layer = get_channel_layer()
            notification_group_name = f'user_{skill.owner.id}_notifications'
            async_to_sync(channel_layer.group_send)(
                notification_group_name,
                {
                    'type': 'send_notification',
                    'message': {
                        'text': f'{request.user.username} sent you a request for: "{skill.title}"',
                        'url': '/requests/'
                    }
                }
            )

            messages.success(request, "Your skill request has been sent successfully!")
            return redirect('find_skills')
    else:
        form = SkillRequestForm()

    return render(request, 'ui/student/request_form.html', {'form': form, 'skill': skill})


@login_required
def create_barter_proposal(request, request_id):
    skill_request = get_object_or_404(Request, id=request_id)

    if skill_request.requester != request.user:
        messages.error(request, "You are not authorized to perform this action.")
        return redirect('dashboard')

    if skill_request.skill.exchange_type != 'Barter':
        messages.error(request, "This skill is not listed for barter.")
        return redirect('find_skills')

    if hasattr(skill_request, 'barter_proposal'):
        messages.warning(request, "A barter proposal already exists for this request.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = BarterProposalForm(request.POST, user=request.user)
        if form.is_valid():
            proposal = form.save(commit=False)
            proposal.request = skill_request
            proposal.save()
            messages.success(request, f"Your barter proposal offering '{proposal.offered_skill.title}' has been sent!")
            return redirect('dashboard')
    else:
        form = BarterProposalForm(user=request.user)

    return render(request, 'ui/student/propose_barter.html', {
        'form': form,
        'skill_request': skill_request
    })


@login_required
def transaction_history(request):
    transactions = Transaction.objects.filter(
        Q(provider=request.user) | Q(receiver=request.user)
    ).select_related('request__skill', 'provider', 'receiver').order_by('-completed_at')

    return render(request, 'ui/student/transaction_history.html', {'transactions': transactions})

@login_required
@require_POST
def update_request_status(request, request_id, status):
    skill_request = get_object_or_404(Request, id=request_id)

    if skill_request.skill.owner != request.user:
        messages.error(request, "You are not authorized to perform this action.")
        return redirect('requests')

    if status in ['Accepted', 'Declined']:
        skill_request.status = status
        skill_request.save()
        messages.success(request, f"Request has been successfully {status.lower()}.")
    else:
        messages.error(request, "Invalid status update.")

    return redirect('requests')


@login_required
def leave_feedback(request, request_id):
    skill_request = get_object_or_404(Request, id=request_id)

    if skill_request.requester != request.user:
        messages.error(request, "You are not authorized to leave feedback for this request.")
        return redirect('requests')

    if skill_request.status not in ['Accepted', 'Completed']:
        messages.error(request, "You can only leave feedback for accepted or completed requests.")
        return redirect('requests')

    if hasattr(skill_request, 'rating'):
        messages.warning(request, "You have already submitted feedback for this exchange.")
        return redirect('core:transaction_history')

    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.request = skill_request
            feedback.skill = skill_request.skill
            feedback.rater = request.user
            feedback.rated_user = skill_request.skill.owner
            feedback.save()
            messages.success(request, "Thank you! Your feedback has been submitted.")
            return redirect('core:transaction_history')
    else:
        form = FeedbackForm()

    context = {
        'form': form,
        'skill_request': skill_request
    }
    return render(request, 'ui/student/leave_feedback.html', context)

@login_required
@require_POST
def complete_session(request, request_id):
    skill_request = get_object_or_404(Request, id=request_id)

    if request.user != skill_request.requester and request.user != skill_request.skill.owner:
        messages.error(request, "You are not authorized to perform this action.")
        return redirect('schedule')

    if skill_request.status != 'Accepted':
        messages.error(request, "This session is not in an accepted state.")
        return redirect('schedule')

    skill_request.status = 'Completed'
    skill_request.save()

    Transaction.objects.get_or_create(
        request=skill_request,
        defaults={
            'provider': skill_request.skill.owner,
            'receiver': skill_request.requester,
            'exchange_type': skill_request.skill.exchange_type,
            'status': 'Completed'
        }
    )

    messages.success(request, f"Session for '{skill_request.skill.title}' has been marked as complete!")
    return redirect('schedule')