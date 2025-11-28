# in core/views.py
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import CustomSignUpForm, SkillRequestForm, BarterProposalForm, FeedbackForm
from .models import CustomUser, Skill, Request, BarterProposal, Transaction, Rating, Schedule
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse

# Real-time imports
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.db.models import Max
from django.http import JsonResponse
from .models import Message
from django.db.models import Q, Max, Count, Case, When, IntegerField
from .utils import get_conversation_id
from datetime import datetime
from django.utils.dateparse import parse_datetime
import json


def get_user_conversations(user):
    """
    Helper function to get all conversations for a user with metadata.
    Fixed to prevent duplicate conversation entries.
    """

    # Get all unique conversation_ids where user is involved
    conversations_data = Message.objects.filter(
        Q(sender=user) | Q(recipient=user)
    ).values('conversation_id').annotate(
        last_message_time=Max('created_at'),
        unread_count=Count(
            Case(
                When(recipient=user, is_read=False, then=1),
                output_field=IntegerField()
            )
        )
    ).order_by('-last_message_time')


    conversation_list = []
    seen_users = set()  # Track users we've already added

    for conv_data in conversations_data:
        conv_id = conv_data['conversation_id']

        # Get the last message for this conversation
        last_msg = Message.objects.filter(
            conversation_id=conv_id
        ).select_related('sender', 'recipient').order_by('-created_at').first()

        if last_msg:
            # Determine who the "other user" is
            other_user = last_msg.recipient if last_msg.sender == user else last_msg.sender

            print(f"  Other user: {other_user.username}, ID: {other_user.id}")  # DEBUG

            # Skip if we've already added this user
            if other_user.id in seen_users:
                continue

            seen_users.add(other_user.id)

            conversation_list.append({
                'other_user': other_user,
                'last_message': last_msg,
                'unread_count': conv_data['unread_count'],
                'conversation_id': conv_id
            })

    return conversation_list

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

    # Check if user is trying to request their own skill
    if skill.owner == request.user:
        messages.error(request, "You cannot request your own skill.")
        return redirect('find_skills')

    # Check if user already sent a request for this skill
    existing_request = Request.objects.filter(skill=skill, requester=request.user).first()
    if existing_request:
        messages.warning(
            request,
            f"You have already sent a request for '{skill.title}'. Its status is '{existing_request.get_status_display()}'."
        )
        return redirect('find_skills')

    if request.method == 'POST':
        form = SkillRequestForm(request.POST)

        if form.is_valid():
            new_request = form.save(commit=False)
            new_request.requester = request.user
            new_request.skill = skill
            new_request.save()

            # Send real-time notification
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

            messages.success(request, f"Your request for '{skill.title}' has been sent successfully!")
            return redirect('find_skills')
        else:
            # Form has errors - display them
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            return redirect('find_skills')

    # For GET requests (fallback if someone accesses the URL directly)
    # Since we're using modal now, just redirect to find_skills
    # Optionally, you can still render the old page as a fallback
    return redirect('find_skills')

    # OR keep the old template as fallback:
    # form = SkillRequestForm()
    # return render(request, 'ui/student/request_form.html', {'form': form, 'skill': skill})


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

    # Validation 1: Check if user is authorized (only requester can leave feedback)
    if skill_request.requester != request.user:
        messages.error(request, "You are not authorized to leave feedback for this request.")
        return redirect('core:transaction_history')

    # Validation 2: Check if request is in correct status
    if skill_request.status not in ['Accepted', 'Completed']:
        messages.error(request, "You can only leave feedback for accepted or completed requests.")
        return redirect('core:transaction_history')

    # Validation 3: Check if rating already exists
    if hasattr(skill_request, 'rating') and skill_request.rating:
        messages.warning(request, "You have already submitted feedback for this exchange.")
        return redirect('core:transaction_history')

    if request.method == 'POST':
        # Get the rating and comment from POST data
        # The modal uses name="rating" and name="feedback"
        # But your model uses "rating" and "comment"
        rating_value = request.POST.get('rating')
        comment_text = request.POST.get('feedback')  # Modal uses "feedback"
        tags = request.POST.getlist('tags')  # Optional quick tags

        # Validate required fields
        if not rating_value or not comment_text:
            messages.error(request, "Please provide both a rating and a review.")
            return redirect('core:transaction_history')

        try:
            # Create a dictionary with the correct field names for your model
            form_data = {
                'rating': int(rating_value),
                'comment': comment_text
            }

            # If tags were selected, append them to the comment
            if tags:
                form_data['comment'] += f"\n\n✓ {', '.join(tags).replace('_', ' ').title()}"

            # Create the form instance with the data
            form = FeedbackForm(form_data)

            if form.is_valid():
                # Save the form but don't commit to DB yet
                rating = form.save(commit=False)

                # Set the required foreign key relationships
                rating.request = skill_request
                rating.skill = skill_request.skill
                rating.rater = request.user
                rating.rated_user = skill_request.skill.owner

                # Now save to database
                rating.save()

                messages.success(request, "Thank you! Your feedback has been submitted successfully.")
                return redirect('core:transaction_history')
            else:
                # If form validation fails, show the errors
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
                return redirect('core:transaction_history')

        except ValueError:
            messages.error(request, "Invalid rating value. Please select between 1-5 stars.")
            return redirect('core:transaction_history')
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('core:transaction_history')

    # For GET requests, redirect to transaction history
    # (since we're using a modal, direct access should redirect)
    return redirect('core:transaction_history')

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
    """
    other_user = get_object_or_404(CustomUser, username=username)
    current_user = request.user

    # Prevent users from chatting with themselves
    if other_user == current_user:
        messages.error(request, "You cannot chat with yourself.")
        return redirect('core:conversation_list')

    # Generate conversation_id
    conversation_id = get_conversation_id(current_user, other_user)

    # Get chat history
    chat_messages = Message.objects.filter(
        conversation_id=conversation_id
    ).select_related('sender', 'recipient').order_by('created_at')

    # Mark messages as read
    Message.objects.filter(
        conversation_id=conversation_id,
        recipient=current_user,
        is_read=False
    ).update(is_read=True)

    # Get all conversations for sidebar
    conversations = get_user_conversations(current_user)

    context = {
        'other_user': other_user,
        'conversation_id': conversation_id,
        'chat_messages': chat_messages,  # ✅ Pass as chat_messages
        'conversations': conversations,
    }

    return render(request, 'core/chat.html', context)


@login_required
def conversation_list(request):
    """
    Display list of all conversations for the current user.
    This is the default chat page when no conversation is selected.
    """
    conversations = get_user_conversations(request.user)

    context = {
        'conversations': conversations,
        'other_user': None,
        'conversation_id': None,
        'chat_messages': [],  # ✅ CHANGED from 'messages' to 'chat_messages'
    }

    return render(request, 'core/chat.html', context)


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


@login_required
@require_POST
def send_message_api(request, username):
    """
    API endpoint to send a message via AJAX.
    """
    try:
        other_user = get_object_or_404(CustomUser, username=username)
        data = json.loads(request.body)
        message_content = data.get('message', '').strip()

        if not message_content:
            return JsonResponse({'success': False, 'error': 'Message cannot be empty'})

        # Calculate conversation_id
        conversation_id = get_conversation_id(request.user, other_user)


        # Create message
        message = Message.objects.create(
            sender=request.user,
            recipient=other_user,
            content=message_content,
            conversation_id=conversation_id
        )

        return JsonResponse({
            'success': True,
            'message_id': message.id,
            'timestamp': message.created_at.strftime('%I:%M %p')
        })

    except CustomUser.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def cancel_request(request, request_id):
    """
    Allows the requester to cancel their own pending request.
    """
    req_to_cancel = get_object_or_404(Request, pk=request_id)

    # Ensure ONLY the sender can cancel their own request
    if req_to_cancel.requester != request.user:
        messages.error(request, "You are not authorized to cancel this request.")
        return redirect('requests')  # Changed from 'request_dashboard'

    # Only Pending requests can be cancelled
    if req_to_cancel.status != 'Pending':
        messages.error(request, "Only pending requests can be canceled.")
        return redirect('requests')  # Changed from 'request_dashboard'

    req_to_cancel.status = 'Cancelled'
    req_to_cancel.save()

    messages.success(request, "Your request has been cancelled successfully.")
    return redirect('requests')  # Changed from 'request_dashboard'


@login_required
def create_session(request):
    if request.method == 'POST':
        try:
            # Get data from the form
            title = request.POST.get('title', 'New Session')
            description = request.POST.get('details', '')

            # Get date and time separately
            session_date = request.POST.get('session_date')  # YYYY-MM-DD format
            start_time_str = request.POST.get('start_time')  # HH:MM format
            end_time_str = request.POST.get('end_time')  # HH:MM format

            # Combine date and time into datetime objects
            from datetime import datetime

            start_datetime = datetime.strptime(
                f"{session_date} {start_time_str}",
                "%Y-%m-%d %H:%M"
            )
            end_datetime = datetime.strptime(
                f"{session_date} {end_time_str}",
                "%Y-%m-%d %H:%M"
            )

            # Create the Schedule object
            new_schedule = Schedule.objects.create(
                organizer=request.user,
                title=title,
                description=description,
                start_time=start_datetime,
                end_time=end_datetime,
                status='confirmed'
            )

            messages.success(request, f"Session '{title}' created successfully!")
            return redirect('schedule')

        except ValueError as ve:
            print(f"Date/Time parsing error: {ve}")
            messages.error(request, "Invalid date or time format. Please try again.")
            return redirect('schedule')
        except Exception as e:
            print(f"Error creating session: {e}")
            messages.error(request, f"There was an error creating the session: {str(e)}")
            return redirect('schedule')

    return redirect('schedule')