# In ui/views.py

# --- CORRECTED & COMPLETE IMPORTS ---
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages  # <-- THIS IS THE MISSING IMPORT
from django.urls import reverse
from django.contrib.auth import login, logout
from django.db.models import Q      # <-- ADD THIS IMPORT FOR SEARCHING
from core.models import Skill, Comment, Rating, Transaction
from core.forms import CustomLoginForm, CustomSignUpForm, CommentForm
from .forms import EditProfileForm, SkillForm
from django.http import JsonResponse
from core.models import Request, Schedule
from django.utils import timezone
from core.models import Notification, NotificationPreference
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model
from core.models import Message


# --- Existing Authentication & Profile Views ---

def home(request):
    return render(request, 'ui/index.html')

def login_view(request):
    if request.user.is_authenticated:
        messages.success(request, 'Successfully logged in!')
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
    user = request.user

    # Count skills offered by the user
    skills_count = Skill.objects.filter(owner=user).count()

    # Count active requests (Pending and Accepted only, exclude Completed, Declined, Cancelled)
    active_requests_count = Request.objects.filter(
        Q(requester=user) | Q(skill__owner=user),
        status__in=['Pending', 'Accepted']
    ).count()

    # Count completed sessions (Completed requests)
    completed_sessions_count = Request.objects.filter(
        Q(requester=user) | Q(skill__owner=user),
        status='Completed'
    ).count()

    # Get recent transactions (last 5)
    recent_transactions = Transaction.objects.filter(
        Q(provider=user) | Q(receiver=user)
    ).select_related(
        'request__skill', 'provider', 'receiver'
    ).order_by('-completed_at')[:5]

    # Get upcoming sessions (Accepted requests + future Schedules)
    from datetime import datetime
    from django.utils import timezone

    # Get accepted requests
    upcoming_requests = Request.objects.filter(
        Q(requester=user) | Q(skill__owner=user),
        status='Accepted'
    ).select_related('skill', 'skill__owner', 'requester').order_by('-updated_at')[:3]

    # Get future schedules
    upcoming_schedules = Schedule.objects.filter(
        Q(organizer=user) | Q(participants=user),
        start_time__gte=timezone.now()
    ).distinct().order_by('start_time')[:3]

    context = {
        'skills_count': skills_count,
        'active_requests_count': active_requests_count,
        'completed_sessions_count': completed_sessions_count,
        'recent_transactions': recent_transactions,
        'upcoming_requests': upcoming_requests,
        'upcoming_schedules': upcoming_schedules,
    }

    return render(request, 'ui/student/dashboard.html', context)

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
    """
    Display user notifications and preferences.
    """
    # Get all notifications for the current user
    notifications = Notification.objects.filter(
        recipient=request.user
    ).select_related('related_user', 'related_request__skill').order_by('-created_at')

    # Get or create notification preferences
    preferences, created = NotificationPreference.objects.get_or_create(
        user=request.user
    )

    # Count unread notifications
    unread_count = notifications.filter(is_read=False).count()

    # DEBUG: Print to console
    print(f"=== NOTIFICATION VIEW DEBUG ===")
    print(f"User: {request.user.username}")
    print(f"Total notifications: {notifications.count()}")
    print(f"Unread count: {unread_count}")
    print(f"Preferences exist: {not created}")

    # DEBUG: Print first few notifications
    for notif in notifications[:5]:
        print(f"  - [{notif.notification_type}] {notif.title} (Read: {notif.is_read})")

    context = {
        'notifications': notifications,
        'preferences': preferences,
        'unread_count': unread_count,
    }
    return render(request, 'ui/student/notification.html', context)

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
    category = request.GET.get('category', '')  # ✅ Add this line

    # Use prefetch_related for performance
    skills = Skill.objects.exclude(owner=request.user).prefetch_related('comments__author')

    # Apply search filter
    if query:
        skills = skills.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(category__icontains=query)
        )

    # ✅ Apply category filter
    if category:
        skills = skills.filter(category=category)

    # Create one instance of the comment form
    comment_form = CommentForm()

    context = {
        'skills': skills,
        'query': query,
        'selected_category': category,  # ✅ Add this to preserve selection
        'comment_form': comment_form
    }
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
    Excludes 'Completed' and 'Cancelled' requests as they don't need action.
    """
    # Fetch requests sent BY the current user (Excluding Completed and Cancelled)
    sent_requests = Request.objects.filter(
        requester=request.user
    ).exclude(status__in=['Completed', 'Cancelled']).select_related('skill', 'skill__owner').order_by('-created_at')

    # Fetch requests sent TO the current user (Excluding Completed and Cancelled)
    received_requests = Request.objects.filter(
        skill__owner=request.user
    ).exclude(status__in=['Completed', 'Cancelled']).select_related('skill', 'requester').order_by('-created_at')

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


@login_required
def transaction_view(request):
    # Fetch all transactions where the user is provider or receiver
    transactions = Transaction.objects.filter(
        Q(provider=request.user) | Q(receiver=request.user)
    ).select_related('request__skill', 'provider', 'receiver').order_by('-completed_at')

    context = {
        'transactions': transactions
    }
    return render(request, 'ui/student/transaction_history.html', context)

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


@login_required
def delete_schedule(request, schedule_id):
    """
    Deletes a schedule session.
    Only the organizer can delete their own schedule.
    """
    if request.method == 'POST':
        schedule = get_object_or_404(Schedule, id=schedule_id)

        if schedule.organizer != request.user:
            messages.error(request, "You are not authorized to delete this session.")
            return redirect('schedule')

        schedule_title = schedule.title
        schedule.delete()

        messages.success(request, f"Session '{schedule_title}' has been successfully removed!")
        return redirect('schedule')

    return redirect('schedule')


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """
    Mark a single notification as read.
    """
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()

    return JsonResponse({
        'success': True,
        'notification_id': notification_id
    })


@login_required
@require_POST
def mark_all_notifications_read(request):
    """
    Mark all notifications as read for the current user.
    """
    updated_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).update(is_read=True)

    return JsonResponse({
        'success': True,
        'updated_count': updated_count
    })


@login_required
@require_POST
def delete_notification(request, notification_id):
    """
    Delete a specific notification.
    """
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.delete()

    return JsonResponse({
        'success': True,
        'notification_id': notification_id
    })


@login_required
@require_POST
def update_notification_preferences(request):
    """
    Update user's notification preferences.
    """
    preferences, created = NotificationPreference.objects.get_or_create(
        user=request.user
    )

    # Update email notification preferences
    preferences.email_new_request = request.POST.get('email_new_request') == 'on'
    preferences.email_request_accepted = request.POST.get('email_request_accepted') == 'on'
    preferences.email_schedule_reminders = request.POST.get('email_schedule_reminders') == 'on'
    preferences.email_new_messages = request.POST.get('email_new_messages') == 'on'

    # Update push notification preferences
    preferences.push_enabled = request.POST.get('push_enabled') == 'on'
    preferences.push_session_reminders = request.POST.get('push_session_reminders') == 'on'

    # Update feedback preferences
    preferences.feedback_reminders = request.POST.get('feedback_reminders') == 'on'
    preferences.feedback_received = request.POST.get('feedback_received') == 'on'

    preferences.save()

    messages.success(request, 'Notification preferences saved successfully!')
    return redirect('notification')


@login_required
def get_unread_notification_count(request):
    """
    API endpoint to get unread notification count.
    """
    count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()

    return JsonResponse({
        'unread_count': count
    })
