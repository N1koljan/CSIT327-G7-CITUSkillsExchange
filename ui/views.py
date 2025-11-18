# In ui/views.py

# --- CORRECTED & COMPLETE IMPORTS ---
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages  # <-- THIS IS THE MISSING IMPORT
from django.urls import reverse
from django.contrib.auth import login, logout
from django.db.models import Q      # <-- ADD THIS IMPORT FOR SEARCHING
from core.models import Skill, Comment,  Rating
from core.forms import CustomLoginForm, CustomSignUpForm, CommentForm
from .forms import EditProfileForm, SkillForm
from django.http import JsonResponse
from core.models import Request, Schedule

from django.contrib.auth import get_user_model
from core.models import Message


# --- Existing Authentication & Profile Views ---

def home(request):
    return render(request, 'ui/index.html')

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = CustomLoginForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('dashboard')
    else:
        form = CustomLoginForm()
    return render(request, 'ui/auth/login.html', {'form': form})

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
def profile_view(request):
    context = {'user': request.user}
    return render(request, 'ui/student/profile.html', context)

@login_required
def dashboard_view(request):
    return render(request, 'ui/student/dashboard.html')

@login_required
def edit_profile_view(request):
    if request.method == 'POST':
        form = EditProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('profile')
    else:
        form = EditProfileForm(instance=request.user)
    context = {'form': form}
    return render(request, 'ui/student/edit_profile.html', context)

def logout_view(request):
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect('login')

# --- Placeholder Views ---



@login_required
def schedule_view(request):
    """
    Fetches pending requests, confirmed sessions, and user-created schedules.
    """
    # Get all requests that are 'Pending' where the current user is either
    # the one who sent it (requester) or the one who received it (skill owner).
    pending_requests = Request.objects.filter(
        Q(requester=request.user) | Q(skill__owner=request.user),
        status='Pending'
    ).select_related('skill', 'skill__owner', 'requester').order_by('-created_at')

    # Get all requests that are 'Accepted' where the current user is involved.
    confirmed_sessions = Request.objects.filter(
        Q(requester=request.user) | Q(skill__owner=request.user),
        status='Accepted'
    ).select_related('skill', 'skill__owner', 'requester').order_by('-updated_at')

    # NEW: Get all Schedule objects created by the user or where they are a participant
    user_schedules = Schedule.objects.filter(
        Q(organizer=request.user) | Q(participants=request.user)
    ).distinct().order_by('start_time')

    context = {
        'pending_requests': pending_requests,
        'confirmed_sessions': confirmed_sessions,
        'user_schedules': user_schedules,  # NEW: Pass schedules to template
    }
    return render(request, 'ui/student/schedule.html', context)

@login_required
def notification_view(request):
    return render(request, 'ui/student/notification.html')

# --- NEW & UPDATED Skill Management Views ---

@login_required
def my_skills_list(request):
    """
    Handles both displaying the list of skills AND creating a new skill via the modal form.
    """
    if request.method == 'POST':
        form = SkillForm(request.POST, user=request.user)
        if form.is_valid():
            skill = form.save(commit=False)
            skill.owner = request.user
            skill.save()
            messages.success(request, f"Skill '{skill.title}' was successfully added!")
            return redirect('my_skills')
        else:
            error_message = "Please correct the errors below. "
            for field, errors in form.errors.items():
                error_message += f"{field.capitalize()}: {', '.join(errors)} "
            messages.error(request, error_message)

    skills = Skill.objects.filter(owner=request.user)
    form = SkillForm()
    context = {'skills': skills, 'form': form}
    return render(request, 'ui/student/my_skills.html', context)


@login_required
def find_skill_view(request):
    """
    Displays all available skills and handles search/filtering.
    """
    query = request.GET.get('q', '')

    # 👇 MODIFIED: Use prefetch_related for a massive performance boost!
    # This fetches all skills and their related comments + authors in just 2-3 database queries
    # instead of hundreds.
    skills = Skill.objects.exclude(owner=request.user).prefetch_related('comments__author')

    if query:
        skills = skills.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(category__icontains=query)
        )

    # We create one instance of the comment form to pass to the templates for all skills.
    comment_form = CommentForm()

    context = {'skills': skills, 'query': query, 'comment_form': comment_form}
    return render(request, 'ui/student/find_skills.html', context)


# 👇 --- ADD THIS ENTIRE NEW VIEW --- 👇
@login_required
def add_comment_to_skill(request, skill_id):
    # This view only accepts POST requests
    if request.method == 'POST':
        skill = get_object_or_404(Skill, id=skill_id)
        form = CommentForm(request.POST)
        if form.is_valid():
            new_comment = form.save(commit=False)
            new_comment.skill = skill
            new_comment.author = request.user
            new_comment.save()
            messages.success(request, "Your comment has been added.")
        else:
            # If the form is invalid (e.g., empty), show an error.
            messages.error(request, "Comment cannot be empty.")

    # Redirect back to the find_skills page, with an anchor to the skill card
    return redirect(f"{reverse('find_skills')}#skill-{skill_id}")

@login_required
def skill_edit(request, pk):
    skill = get_object_or_404(Skill, pk=pk)
    if skill.owner != request.user:
        messages.error(request, "You are not authorized to edit this skill.")
        return redirect('my_skills')
    if request.method == 'POST':
        form = SkillForm(request.POST, instance=skill, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your skill has been updated!')
            return redirect('my_skills')
    else:
        form = SkillForm(instance=skill, user=request.user)
    return render(request, 'ui/student/skill_form.html', {'form': form, 'page_title': 'Edit Skill'})

@login_required
def skill_delete(request, pk):
    skill = get_object_or_404(Skill, pk=pk)
    if skill.owner != request.user:
        messages.error(request, "You are not authorized to delete this skill.")
        return redirect('my_skills')
    if request.method == 'POST':
        skill_title = skill.title
        skill.delete()
        messages.success(request, f"The skill '{skill_title}' has been deleted.")
        return redirect('my_skills')
    return render(request, 'ui/student/skill_confirm_delete.html', {'skill': skill})


@login_required
def request_create(request, skill_pk):
    """
    Handles the creation of a new request for a specific skill.
    """
    skill = get_object_or_404(Skill, pk=skill_pk)

    # Security Check 1: Prevent users from requesting their own skills
    if skill.owner == request.user:
        messages.error(request, "You cannot request your own skill.")
        return redirect('find_skills')

    # Security Check 2: Prevent duplicate requests for the same skill
    if Request.objects.filter(skill=skill, requester=request.user).exists():
        messages.info(request, "You have already sent a request for this skill.")
        return redirect('find_skills')

    if request.method == 'POST':
        form = RequestForm(request.POST)
        if form.is_valid():
            new_request = form.save(commit=False)
            new_request.skill = skill
            new_request.requester = request.user
            new_request.save()
            messages.success(request, f"Your request for '{skill.title}' has been sent!")
            return redirect('my_requests')
    else:
        form = RequestForm()

    return render(request, 'ui/student/request_form.html', {'form': form, 'skill': skill})





@login_required
def update_request_status(request, pk, action):
    """
    Handles accepting or declining a received request.
    """
    # This view should only accept POST requests for security
    if request.method != 'POST':
        return redirect('requests_received')

    req_to_update = get_object_or_404(Request, pk=pk)

    # Security Check: Ensure the person updating is the owner of the skill
    if req_to_update.skill.owner != request.user:
        messages.error(request, "You are not authorized to perform this action.")
        return redirect('requests_received')

    if action == 'accept' and req_to_update.status == 'Pending':
        req_to_update.status = 'Accepted'
        messages.success(request, f"You have accepted the request from {req_to_update.requester.username}.")
    elif action == 'decline' and req_to_update.status == 'Pending':
        req_to_update.status = 'Declined'
        messages.info(request, f"You have declined the request from {req_to_update.requester.username}.")
    else:
        messages.error(request, "This request is not pending or the action is invalid.")

    req_to_update.save()
    return redirect('requests_received')

@login_required
def request_dashboard(request):
    """
    Displays the main request dashboard.
    Excludes 'Completed' requests as they belong in Transaction History.
    """
    # Fetch requests sent BY the current user (Excluding Completed)
    sent_requests = Request.objects.filter(
        requester=request.user
    ).exclude(status='Completed').select_related('skill', 'skill__owner').order_by('-created_at')

    # Fetch requests sent TO the current user (Excluding Completed)
    received_requests = Request.objects.filter(
        skill__owner=request.user
    ).exclude(status='Completed').select_related('skill', 'requester').order_by('-created_at')

    context = {
        'sent_requests': sent_requests,
        'received_requests': received_requests
    }
    return render(request, 'ui/student/request.html', context)

@login_required
def feedback_history_view(request):
    """
    Displays all feedback the user has given and received.
    """
    # Fetch all ratings GIVEN BY the current user
    given_ratings = Rating.objects.filter(rater=request.user).select_related('skill', 'rated_user')

    # Fetch all ratings RECEIVED BY the current user
    received_ratings = Rating.objects.filter(rated_user=request.user).select_related('skill', 'rater')

    context = {
        'given_ratings': given_ratings,
        'received_ratings': received_ratings,
    }
    return render(request, 'ui/student/feedback_history.html', context)



User = get_user_model()

@login_required
def chat_view(request, username=None):
    current_user = request.user
    other_user = None
    messages_qs = []
    conversation_id = None

    # Fetch all conversations for the sidebar
    conversations_raw = Message.objects.filter(
        Q(sender=current_user) | Q(recipient=current_user)
    ).order_by('-id')

    # Build a unique list of conversations
    conversation_dict = {}
    for msg in conversations_raw:
        ids = sorted([msg.sender.id, msg.recipient.id])
        conv_id = f"chat_{ids[0]}_{ids[1]}"
        other_id = ids[1] if ids[0] == current_user.id else ids[0]

        if conv_id not in conversation_dict:
            conversation_dict[conv_id] = {
                'conversation_id': conv_id,
                'other_user': User.objects.get(id=other_id),
                'last_message': msg,
                'unread_count': Message.objects.filter(
                    conversation_id=conv_id,
                    recipient=current_user,
                    is_read=False
                ).count()
            }

    conversations = list(conversation_dict.values())

    # If a username is selected, fetch that conversation
    if username:
        try:
            other_user = User.objects.get(username=username)
            ids = sorted([current_user.id, other_user.id])
            conversation_id = f"chat_{ids[0]}_{ids[1]}"
            messages_qs = Message.objects.filter(conversation_id=conversation_id).order_by('id')
        except User.DoesNotExist:
            messages.error(request, f"User '{username}' does not exist.")
            return redirect('conversation_list')  # redirect to your chat list page

    return render(request, 'ui/student/chat.html', {
        'messages': messages_qs,
        'conversations': conversations,
        'other_user': other_user,
        'conversation_id': conversation_id,
    })


def transaction_view(request):
    # You can pass context if needed
    return render(request, 'ui/student/transaction_history.html')
@login_required
def skill_get_json(request, pk):
    """
    Returns skill data as JSON for AJAX requests (used by the edit modal).
    """
    skill = get_object_or_404(Skill, pk=pk, owner=request.user)
    return JsonResponse({
        'title': skill.title,
        'category': skill.category,
        'exchange_type': skill.exchange_type,
        'description': skill.description,
    })


