# in core/views.py
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import CustomSignUpForm, SkillRequestForm, BarterProposalForm, FeedbackForm
# 👇 CHANGE #1: Import 'Request', not 'SkillRequest'
from .models import CustomUser, Skill, Request, BarterProposal, Transaction, Rating
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

# Real-time imports
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.db.models import Max
from django.http import JsonResponse
from .models import Message

# This is your existing signup view. It's perfectly fine.
def signup_view(request):
    if request.method == 'POST':
        # ... your existing code ...
        form = CustomSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Account for {user.username} created successfully! You can now log in.')
            return redirect('login')
    else:
        form = CustomSignUpForm()
    return render(request, 'ui/auth/signup.html', {'form': form})


# =========================================================================
# === ADD THIS NEW VIEW TO HANDLE CREATING A REQUEST AND SENDING NOTIFICATIONS ===
# =========================================================================
@login_required
def create_skill_request(request, skill_id):
    skill = get_object_or_404(Skill, id=skill_id)

    if skill.owner == request.user:
        messages.error(request, "You cannot request your own skill.")
        # 👇 Assuming you have a URL named 'find_skills'
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

            # --- REAL-TIME NOTIFICATION LOGIC (no changes here) ---
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
            # 👇 MODIFIED: Redirect to the new requests list page
            return redirect('find_skills')
    else:
        form = SkillRequestForm()

    return render(request, 'ui/student/request_form.html', {'form': form, 'skill': skill})


@login_required
def create_barter_proposal(request, request_id):
    skill_request = get_object_or_404(Request, id=request_id)

    # --- Validation Checks ---
    # 1. Ensure the user is the one who made the request
    if skill_request.requester != request.user:
        messages.error(request, "You are not authorized to perform this action.")
        return redirect('dashboard')  # Or wherever your main dashboard is

    # 2. Ensure the skill is actually a 'Barter' type
    if skill_request.skill.exchange_type != 'Barter':
        messages.error(request, "This skill is not listed for barter.")
        return redirect('find_skills')

    # 3. Ensure a proposal doesn't already exist
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
            # TODO: Add real-time notification to the skill owner
            return redirect('dashboard')
    else:
        form = BarterProposalForm(user=request.user)

    return render(request, 'ui/student/propose_barter.html', {
        'form': form,
        'skill_request': skill_request
    })


# =========================================================================
# === NEW VIEW TO SHOW TRANSACTION HISTORY ===
# =========================================================================
@login_required
def transaction_history(request):
    # Get all transactions where the current user was either the provider OR the receiver
    transactions = Transaction.objects.filter(
        Q(provider=request.user) | Q(receiver=request.user)
    ).select_related('request__skill', 'provider', 'receiver').order_by('-completed_at')

    return render(request, 'ui/student/transaction_history.html', {'transactions': transactions})

@login_required
@require_POST  # This view only accepts POST requests
def update_request_status(request, request_id, status):
    # Find the request object, or return a 404 error if not found
    skill_request = get_object_or_404(Request, id=request_id)

    # --- SECURITY CHECK ---
    # Ensure the person trying to update the request is the owner of the skill
    if skill_request.skill.owner != request.user:
        messages.error(request, "You are not authorized to perform this action.")
        return redirect('requests') # Assuming 'requests' is the name of your request dashboard URL

    # --- LOGIC ---
    # Check if the provided status is valid
    if status in ['Accepted', 'Declined']:
        skill_request.status = status
        skill_request.save()
        messages.success(request, f"Request has been successfully {status.lower()}.")
        # TODO: Send a real-time notification back to the requester
    else:
        messages.error(request, "Invalid status update.")

    return redirect('requests')


@login_required
def leave_feedback(request, request_id):
    skill_request = get_object_or_404(Request, id=request_id)

    # ... (keep the validation checks 1, 2, and 3 same as before) ...
    if skill_request.requester != request.user:
        messages.error(request, "You are not authorized to leave feedback for this request.")
        return redirect('requests')

    if skill_request.status not in ['Accepted', 'Completed']:
        messages.error(request, "You can only leave feedback for accepted or completed requests.")
        return redirect('requests')

    if hasattr(skill_request, 'rating'):
        messages.warning(request, "You have already submitted feedback for this exchange.")
        # 👇 CHANGE 1: If they try to rate again, send them to history
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

            # 👇 CHANGE 2: Redirect to Transaction History after success
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

    # --- SECURITY CHECKS ---
    # 1. Ensure the user is part of this exchange
    if request.user != skill_request.requester and request.user != skill_request.skill.owner:
        messages.error(request, "You are not authorized to perform this action.")
        return redirect('schedule')

    # 2. Ensure the request was accepted
    if skill_request.status != 'Accepted':
        messages.error(request, "This session is not in an accepted state.")
        return redirect('schedule')

    # --- CORE LOGIC ---
    # Update the request status to 'Completed'
    skill_request.status = 'Completed'
    skill_request.save()

    # Create a transaction record. Use get_or_create to prevent duplicates
    # if both users click the button around the same time.
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


@login_required
def chat_page(request, username):
    """
    Display chat page for a conversation with another user.
    Task 6.1.3 dependency - This view will be used by Nicole's chat UI.
    """
    other_user = get_object_or_404(CustomUser, username=username)
    current_user = request.user

    # Generate conversation_id (consistent for both users)
    users_sorted = sorted([current_user.username, other_user.username])
    conversation_id = f"{users_sorted[0]}_{users_sorted[1]}"

    # Get chat history (Task 6.1.5: Save chat history in DB)
    messages_list = Message.objects.filter(
        Q(sender=current_user, recipient=other_user) |
        Q(sender=other_user, recipient=current_user)
    ).order_by('created_at')

    # Mark messages from other user as read (Task 6.1.8: Add unread message)
    Message.objects.filter(
        sender=other_user,
        recipient=current_user,
        is_read=False
    ).update(is_read=True)

    context = {
        'other_user': other_user,
        'conversation_id': conversation_id,
        'messages': messages_list,
    }

    return render(request, 'core/chat.html', context)


@login_required
def conversation_list(request):
    """
    Display list of all conversations for the current user.
    Task 6.1.6 dependency - Will be implemented by Gerard Grant Estella.
    Shows latest message preview and unread count.
    """
    current_user = request.user

    # Get all users the current user has conversations with
    conversations = Message.objects.filter(
        Q(sender=current_user) | Q(recipient=current_user)
    ).values(
        'sender', 'recipient'
    ).annotate(
        last_message_time=Max('created_at')
    ).order_by('-last_message_time')

    # Build conversation list with details
    conversation_list = []
    seen_users = set()

    for conv in conversations:
        # Determine the other user
        if conv['sender'] == current_user.id:
            other_user_id = conv['recipient']
        else:
            other_user_id = conv['sender']

        # Skip if we've already processed this user
        if other_user_id in seen_users:
            continue
        seen_users.add(other_user_id)

        other_user = CustomUser.objects.get(id=other_user_id)

        # Get last message
        last_message = Message.objects.filter(
            Q(sender=current_user, recipient=other_user) |
            Q(sender=other_user, recipient=current_user)
        ).order_by('-created_at').first()

        # Count unread messages (Task 6.1.8: Add unread message)
        unread_count = Message.objects.filter(
            sender=other_user,
            recipient=current_user,
            is_read=False
        ).count()

        # Generate conversation_id
        users_sorted = sorted([current_user.username, other_user.username])
        conversation_id = f"{users_sorted[0]}_{users_sorted[1]}"

        conversation_list.append({
            'other_user': other_user,
            'last_message': last_message,
            'unread_count': unread_count,
            'conversation_id': conversation_id,
        })

    context = {
        'conversations': conversation_list,
    }

    return render(request, 'core/conversation_list.html', context)


@login_required
def get_unread_count(request):
    """
    API endpoint to get total unread message count.
    Task 6.1.8: Add unread message indicator.
    """
    unread_count = Message.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()

    return JsonResponse({
        'unread_count': unread_count
    })


@login_required
def mark_conversation_as_read(request, username):
    """
    Mark all messages in a conversation as read.
    Task 6.1.8: Add unread message functionality.
    """
    if request.method == 'POST':
        other_user = get_object_or_404(CustomUser, username=username)

        Message.objects.filter(
            sender=other_user,
            recipient=request.user,
            is_read=False
        ).update(is_read=True)

        return JsonResponse({'success': True})

    return JsonResponse({'success': False}, status=400)


# Add these to core/views.py (at the bottom, after your chat views)

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import Q


# ========== SEARCH VIEWS (Task 7.1.1: Configure Supabase Full-Text Search) ==========

@login_required
def search_skills(request):
    """
    Search for skills using full-text search.
    Task 7.1.1: Configure Supabase full-text search
    """
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    exchange_type = request.GET.get('exchange_type', '').strip()

    # Start with all skills
    skills = Skill.objects.select_related('owner').all()

    # Apply full-text search if query provided
    if query:
        # Use PostgreSQL full-text search
        search_query = SearchQuery(query, search_type='websearch')
        skills = skills.filter(search_vector=search_query).annotate(
            rank=SearchRank('search_vector', search_query)
        ).order_by('-rank', '-created_at')
    else:
        # Default ordering if no search query
        skills = skills.order_by('-created_at')

    # Apply category filter
    if category:
        skills = skills.filter(category__icontains=category)

    # Apply exchange type filter
    if exchange_type:
        skills = skills.filter(exchange_type=exchange_type)

    # Get unique categories for filter dropdown
    all_categories = Skill.objects.values_list('category', flat=True).distinct().order_by('category')

    context = {
        'skills': skills[:50],  # Limit to 50 results
        'query': query,
        'category': category,
        'exchange_type': exchange_type,
        'all_categories': all_categories,
        'exchange_types': Skill.EXCHANGE_TYPE_CHOICES,
        'total_results': skills.count(),
    }

    return render(request, 'core/search_results.html', context)


@login_required
def search_users(request):
    """
    Search for users using full-text search.
    Task 7.1.1: Configure Supabase full-text search
    """
    query = request.GET.get('q', '').strip()
    department = request.GET.get('department', '').strip()

    # Start with all users (exclude current user)
    users = CustomUser.objects.exclude(id=request.user.id)

    # Apply full-text search if query provided
    if query:
        search_query = SearchQuery(query, search_type='websearch')
        users = users.filter(search_vector=search_query).annotate(
            rank=SearchRank('search_vector', search_query)
        ).order_by('-rank')
    else:
        users = users.order_by('username')

    # Apply department filter
    if department:
        users = users.filter(department=department)

    context = {
        'users': users[:50],  # Limit to 50 results
        'query': query,
        'department': department,
        'departments': CustomUser.DEPARTMENT_CHOICES,
        'total_results': users.count(),
    }

    return render(request, 'core/search_users.html', context)


@login_required
def advanced_search(request):
    """
    Combined search for skills and users.
    Task 7.1.1: Configure Supabase full-text search
    """
    query = request.GET.get('q', '').strip()
    search_type = request.GET.get('type', 'all')  # 'all', 'skills', 'users'

    results = {
        'skills': [],
        'users': [],
        'query': query,
        'search_type': search_type,
    }

    if query:
        search_query = SearchQuery(query, search_type='websearch')

        # Search skills
        if search_type in ['all', 'skills']:
            skills = Skill.objects.select_related('owner').filter(
                search_vector=search_query
            ).annotate(
                rank=SearchRank('search_vector', search_query)
            ).order_by('-rank')[:20]
            results['skills'] = skills

        # Search users
        if search_type in ['all', 'users']:
            users = CustomUser.objects.filter(
                search_vector=search_query
            ).exclude(
                id=request.user.id
            ).annotate(
                rank=SearchRank('search_vector', search_query)
            ).order_by('-rank')[:20]
            results['users'] = users

    return render(request, 'core/advanced_search.html', results)


# API endpoint for autocomplete (optional but useful)
@login_required
def search_autocomplete(request):
    """
    Autocomplete API for search suggestions.
    Task 7.1.1: Configure Supabase full-text search
    """
    query = request.GET.get('q', '').strip()

    if not query or len(query) < 2:
        return JsonResponse({'suggestions': []})

    # Get skill suggestions
    skill_suggestions = Skill.objects.filter(
        Q(title__icontains=query) | Q(category__icontains=query)
    ).values_list('title', flat=True).distinct()[:5]

    # Get category suggestions
    category_suggestions = Skill.objects.filter(
        category__icontains=query
    ).values_list('category', flat=True).distinct()[:3]

    suggestions = list(skill_suggestions) + list(category_suggestions)

    return JsonResponse({
        'suggestions': suggestions[:8]  # Max 8 suggestions
    })