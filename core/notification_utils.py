# core/notification_utils.py
# This file contains all the utility functions for creating and sending notifications

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification, NotificationPreference
from django.core.mail import send_mail
from django.conf import settings


def create_notification(recipient, notification_type, title, message, link=None, related_request=None,
                        related_user=None):
    """
    Creates a notification and sends real-time update via WebSocket.

    Args:
        recipient: User who will receive the notification
        notification_type: Type of notification (e.g., 'request_received', 'request_accepted')
        title: Short title of the notification
        message: Full notification message
        link: Optional URL to redirect user when clicking notification
        related_request: Optional related Request object
        related_user: Optional related User object

    Returns:
        Notification object that was created
    """
    # Create notification in database
    notification = Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link,
        related_request=related_request,
        related_user=related_user
    )

    # Send real-time notification via WebSocket
    channel_layer = get_channel_layer()
    notification_group_name = f'user_{recipient.id}_notifications'

    try:
        async_to_sync(channel_layer.group_send)(
            notification_group_name,
            {
                'type': 'send_notification',
                'notification': {
                    'id': notification.id,
                    'type': notification_type,
                    'title': title,
                    'message': message,
                    'link': link or '',
                    'timestamp': notification.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'is_read': False
                }
            }
        )
    except Exception as e:
        # If WebSocket fails, just log it - the database notification is still created
        print(f"WebSocket notification error: {e}")

    # Send email notification if user has it enabled
    send_email_notification(recipient, notification_type, title, message, link)

    return notification


def send_email_notification(recipient, notification_type, title, message, link=None):
    """
    Sends email notification based on user preferences.

    Args:
        recipient: User who will receive the email
        notification_type: Type of notification to check preferences
        title: Email subject line
        message: Email body message
        link: Optional link to include in email
    """
    # Get or create user preferences
    prefs, created = NotificationPreference.objects.get_or_create(user=recipient)

    # Check if email notifications are enabled for this type
    should_send = False

    if notification_type == 'request_received' and prefs.email_new_request:
        should_send = True
    elif notification_type == 'request_accepted' and prefs.email_request_accepted:
        should_send = True
    elif notification_type == 'session_reminder' and prefs.email_schedule_reminders:
        should_send = True
    elif notification_type == 'new_message' and prefs.email_new_messages:
        should_send = True
    elif notification_type == 'feedback_received' and prefs.feedback_received:
        should_send = True

    # Only send if user has enabled this notification type AND email is configured
    if should_send and hasattr(settings, 'EMAIL_HOST'):
        try:
            email_body = f"{message}\n\n"
            if link:
                # Add full URL if SITE_URL is configured
                site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
                email_body += f"View details: {site_url}{link}\n\n"
            email_body += "You can manage your notification preferences in your account settings."

            send_mail(
                subject=f"CIT-U Skills Exchange: {title}",
                message=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient.email],
                fail_silently=True,  # Don't crash if email fails
            )
        except Exception as e:
            print(f"Email notification error: {e}")


# ============================================================================
# SPECIFIC NOTIFICATION FUNCTIONS
# These are called from your views when specific events happen
# ============================================================================

def notify_new_request(skill_request):
    """
    Notify skill owner about a new request.
    Called when someone requests their skill.
    """
    create_notification(
        recipient=skill_request.skill.owner,
        notification_type='request_received',
        title='New Skill Request',
        message=f'{skill_request.requester.username} requested your skill: "{skill_request.skill.title}"',
        link='/requests/',
        related_request=skill_request,
        related_user=skill_request.requester
    )


def notify_request_accepted(skill_request):
    """
    Notify requester that their request was accepted.
    Called when skill owner accepts a request.
    """
    create_notification(
        recipient=skill_request.requester,
        notification_type='request_accepted',
        title='Request Accepted!',
        message=f'{skill_request.skill.owner.username} accepted your request for "{skill_request.skill.title}"',
        link='/schedule/',
        related_request=skill_request,
        related_user=skill_request.skill.owner
    )


def notify_request_declined(skill_request):
    """
    Notify requester that their request was declined.
    Called when skill owner declines a request.
    """
    create_notification(
        recipient=skill_request.requester,
        notification_type='request_declined',
        title='Request Declined',
        message=f'{skill_request.skill.owner.username} declined your request for "{skill_request.skill.title}"',
        link='/find_skills/',
        related_request=skill_request,
        related_user=skill_request.skill.owner
    )


def notify_new_message(message_obj):
    """
    Notify user about a new message.
    Called when someone sends them a message.
    """
    # Get user preferences to check if they want message notifications
    prefs, _ = NotificationPreference.objects.get_or_create(user=message_obj.recipient)

    if prefs.email_new_messages:
        create_notification(
            recipient=message_obj.recipient,
            notification_type='new_message',
            title='New Message',
            message=f'{message_obj.sender.username} sent you a message',
            link=f'/chat/{message_obj.sender.username}/',
            related_user=message_obj.sender
        )


def notify_feedback_received(rating):
    """
    Notify user about new feedback/review.
    Called when someone leaves feedback for them.
    """
    create_notification(
        recipient=rating.rated_user,
        notification_type='feedback_received',
        title='New Review Received',
        message=f'{rating.rater.username} left you a {rating.rating}-star review',
        link='/feedback/',
        related_user=rating.rater
    )


def notify_session_reminder(schedule):
    """
    Send reminder notification 30 minutes before session.
    This should be called by a scheduled task (celery beat) or cron job.

    NOTE: This function is prepared but you'll need to set up Celery Beat
    or a cron job to call this automatically.
    """
    participants = [schedule.organizer] + list(schedule.participants.all())

    for user in participants:
        prefs, _ = NotificationPreference.objects.get_or_create(user=user)

        if prefs.push_session_reminders:
            create_notification(
                recipient=user,
                notification_type='session_reminder',
                title='Session Starting Soon',
                message=f'Your session "{schedule.title}" starts in 30 minutes',
                link='/schedule/'
            )


def notify_barter_proposal(barter_proposal):
    """
    Notify skill owner about a barter proposal.
    Called when someone proposes a barter exchange.
    """
    create_notification(
        recipient=barter_proposal.request.skill.owner,
        notification_type='barter_proposal',
        title='New Barter Proposal',
        message=f'{barter_proposal.request.requester.username} proposed "{barter_proposal.offered_skill.title}" as barter',
        link='/requests/',
        related_request=barter_proposal.request,
        related_user=barter_proposal.request.requester
    )


def notify_session_completed(transaction):
    """
    Notify both parties about session completion.
    Called when a session is marked as complete.
    """
    # Notify provider
    create_notification(
        recipient=transaction.provider,
        notification_type='session_completed',
        title='Session Completed',
        message=f'Your session with {transaction.receiver.username} has been marked as complete',
        link='/transactions/'
    )

    # Notify receiver
    create_notification(
        recipient=transaction.receiver,
        notification_type='session_completed',
        title='Session Completed',
        message=f'Your session with {transaction.provider.username} has been marked as complete',
        link='/transactions/'
    )