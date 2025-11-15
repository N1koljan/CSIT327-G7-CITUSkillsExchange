# in core/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings  # Use settings to reference the custom user model


# --- Your Existing CustomUser Model (No changes needed here) ---
class CustomUser(AbstractUser):
    DEPARTMENT_CHOICES = [
        ('CS', 'Computer Science'),
        ('IT', 'Information Technology'),
        ('EN', 'Engineering'),
        ('BA', 'Business Administration'),
        ('ED', 'Education'),
        ('AS', 'Arts and Sciences'),
        ('AR', 'Architecture'),
        ('NU', 'Nursing'),
        ('MS', 'Maritime Studies'),
        ('OT', 'Other'),
    ]

    school_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    department = models.CharField(max_length=2, choices=DEPARTMENT_CHOICES, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True, null=True)

    def __str__(self):
        return self.username


# --- NEW MODELS FOR SPRINT 2 ---

class Skill(models.Model):
    """
    Represents a skill that a student can offer.
    Corresponds to User Story US-01: Skill Management.
    """
    # Define choices for the exchange type, as per WBS ID 4
    EXCHANGE_TYPE_CHOICES = [
        ('Voluntary', 'Voluntary (Free)'),
        ('Barter', 'Barter (Skill for Skill)'),
        ('Low-Cost', 'Low-Cost (Small Fee)'),
    ]

    # The student who owns/offers this skill.
    # ForeignKey creates a many-to-one relationship. One user can have many skills.
    # related_name='skills' lets us do user.skills.all() to get all skills for a user.
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='skills')

    title = models.CharField(max_length=100)
    description = models.TextField(max_length=1000)
    category = models.CharField(max_length=50)  # Example: 'Programming', 'Math', 'Writing'

    # The exchange type field with the predefined choices.
    exchange_type = models.CharField(max_length=20, choices=EXCHANGE_TYPE_CHOICES, default='Voluntary')

    # Timestamps for tracking when the skill was created or last updated.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Ensures that a user cannot create two skills with the exact same title.
        unique_together = ('owner', 'title')
        # Default ordering: show the newest skills first, as per US-01.6
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} by {self.owner.username}"


class Request(models.Model):
    """
    Represents a request made by one student for another student's skill.
    Corresponds to User Story US-02: Request Management.
    """
    REQUEST_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Accepted', 'Accepted'),
        ('Declined', 'Declined'),
        ('Completed', 'Completed'),  # <-- ADD THIS LINE
    ]

    # 👇 NEW: Add choices for payment method
    PAYMENT_CHOICES = [
        ('Online', 'Online Payment'),
        ('Cash', 'Cash on Meetup'),
    ]

    # The skill that is being requested.
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='requests')

    # The student who is making the request.
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_requests')

    # 👇 MODIFIED: Renamed from 'message' to be more specific
    extra_description = models.TextField(max_length=500, help_text="Explain what you need help with.")

    # 👇 NEW: Field for the proposed date and time
    requested_date_time = models.CharField(max_length=100, blank=True, null=True, help_text="e.g., 'Tomorrow around 5 PM', or 'Weekend anytime'")

    # 👇 NEW: Field for the payment choice
    payment_choice = models.CharField(max_length=10, choices=PAYMENT_CHOICES, null=True, blank=True)

    # The current status of the request. Defaults to 'Pending'.
    status = models.CharField(max_length=20, choices=REQUEST_STATUS_CHOICES, default='Pending')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # A user can only request a specific skill once while a request is pending. (Adjust if needed)
        unique_together = ('skill', 'requester')
        # Default ordering: show the newest requests first.
        ordering = ['-created_at']

    def __str__(self):
        return f"Request for '{self.skill.title}' from {self.requester.username} ({self.status})"

class Comment(models.Model):
        """
        Represents a comment made by a user on a specific skill.
        """
        # The skill the comment is attached to. If a skill is deleted, all its comments are also deleted.
        # related_name='comments' lets us easily access all comments for a skill with skill.comments.all()
        skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='comments')

        # The user who wrote the comment.
        author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

        # The actual text content of the comment.
        content = models.TextField(max_length=500)

        # Automatically records the time the comment was created.
        created_at = models.DateTimeField(auto_now_add=True)

        class Meta:
            # Orders the comments with the newest ones appearing first.
            ordering = ['-created_at']

        def __str__(self):
            return f'Comment by {self.author.username} on {self.skill.title}'


class BarterProposal(models.Model):
    """
    Represents a barter proposal made in response to an accepted 'Barter' type skill request.
    WBS ID: 5.2.1
    """
    PROPOSAL_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Accepted', 'Accepted'),
        ('Declined', 'Declined'),
    ]

    # The original request this proposal is for. A request can only have one barter proposal.
    request = models.OneToOneField(Request, on_delete=models.CASCADE, related_name='barter_proposal')

    # The skill being offered by the original requester in exchange.
    # We limit choices to skills owned by the requester in the form.
    offered_skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='barter_offers')

    # Status of the proposal, managed by the skill owner.
    status = models.CharField(max_length=20, choices=PROPOSAL_STATUS_CHOICES, default='Pending')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Barter Proposal for '{self.request.skill.title}' offering '{self.offered_skill.title}'"


class Transaction(models.Model):
    """
    Logs a completed exchange, serving as a history record.
    WBS ID: 5.3.1
    """
    TRANSACTION_STATUS_CHOICES = [
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    # The original request that led to this transaction.
    request = models.ForeignKey(Request, on_delete=models.SET_NULL, null=True, related_name='transactions')

    # The user who provided the skill/service.
    provider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                 related_name='provided_transactions')

    # The user who received the skill/service.
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                 related_name='received_transactions')

    # The type of exchange, copied from the skill for historical record.
    exchange_type = models.CharField(max_length=20, choices=Skill.EXCHANGE_TYPE_CHOICES)

    # If the transaction was a barter, this links to the final proposal.
    barter_proposal = models.OneToOneField(BarterProposal, on_delete=models.SET_NULL, null=True, blank=True)

    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS_CHOICES, default='Completed')
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-completed_at']

    def __str__(self):
        return f"Transaction for '{self.request.skill.title}' on {self.completed_at.strftime('%Y-%m-%d')}"


class Rating(models.Model):
    """
    Represents a rating and comment left by a requester for a skill provider
    after a request has been marked as 'Accepted'.
    """
    # The original request that this feedback is for.
    # If the request is deleted, the rating remains but is unlinked.
    request = models.OneToOneField(Request, on_delete=models.SET_NULL, null=True, related_name='rating')

    # The skill that was rated.
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='ratings')

    # The user who is LEAVING the rating (the original requester).
    rater = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='given_ratings')

    # The user who is RECEIVING the rating (the skill owner).
    rated_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_ratings')

    # The star rating, from 1 to 5.
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])

    # The textual feedback.
    comment = models.TextField(max_length=1000)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # A user can only rate a specific request once.
        unique_together = ('request', 'rater')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.rating} stars for '{self.skill.title}' by {self.rater.username}"

# Add to core/models.py (append after your existing models)

from django.conf import settings
from django.utils import timezone
from django.db import models

class Exchange(models.Model):
    REQUEST_STATUS = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    proposer = models.ForeignKey(settings.AUTH_USER_MODEL,
                                 on_delete=models.CASCADE,
                                 related_name='proposed_exchanges')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL,
                                 on_delete=models.CASCADE,
                                 related_name='received_exchanges')
    skill_offered = models.ForeignKey('Skill', on_delete=models.CASCADE, related_name='offered_exchanges')
    skill_requested = models.ForeignKey('Skill', on_delete=models.CASCADE, related_name='requested_exchanges')
    status = models.CharField(max_length=20, choices=REQUEST_STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.proposer.username} ↔ {self.receiver.username} ({self.status})"


class Message(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_messages',
                               on_delete=models.CASCADE)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_messages',
                                  on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    is_read = models.BooleanField(default=False, db_index=True)
    conversation_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['conversation_id', 'created_at']),
        ]

    def __str__(self):
        return f"{self.sender} -> {self.recipient}: {self.content[:40]}"


class Schedule(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('declined', 'Declined'),
        ('completed', 'Completed'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='organized_schedules',
                                  on_delete=models.CASCADE)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='schedules', blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reminder_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ['start_time']
        indexes = [
            models.Index(fields=['start_time']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.title} ({self.start_time.isoformat()})"
