from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings

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


class Skill(models.Model):
    EXCHANGE_TYPE_CHOICES = [
        ('Voluntary', 'Voluntary (Free)'),
        ('Barter', 'Barter (Skill for Skill)'),
        ('Low-Cost', 'Low-Cost (Small Fee)'),
    ]

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='skills')
    title = models.CharField(max_length=100)
    description = models.TextField(max_length=1000)
    category = models.CharField(max_length=50)
    exchange_type = models.CharField(max_length=20, choices=EXCHANGE_TYPE_CHOICES, default='Voluntary')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('owner', 'title')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} by {self.owner.username}"


class Request(models.Model):
    REQUEST_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Accepted', 'Accepted'),
        ('Declined', 'Declined'),
        ('Completed', 'Completed'),
    ]

    PAYMENT_CHOICES = [
        ('Online', 'Online Payment'),
        ('Cash', 'Cash on Meetup'),
    ]

    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='requests')
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_requests')
    extra_description = models.TextField(max_length=500, help_text="Explain what you need help with.")
    requested_date_time = models.CharField(max_length=100, blank=True, null=True, help_text="e.g., 'Tomorrow around 5 PM', or 'Weekend anytime'")
    payment_choice = models.CharField(max_length=10, choices=PAYMENT_CHOICES, null=True, blank=True)
    status = models.CharField(max_length=20, choices=REQUEST_STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('skill', 'requester')
        ordering = ['-created_at']

    def __str__(self):
        return f"Request for '{self.skill.title}' from {self.requester.username} ({self.status})"

class Comment(models.Model):
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Comment by {self.author.username} on {self.skill.title}'


class BarterProposal(models.Model):
    PROPOSAL_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Accepted', 'Accepted'),
        ('Declined', 'Declined'),
    ]

    request = models.OneToOneField(Request, on_delete=models.CASCADE, related_name='barter_proposal')
    offered_skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='barter_offers')
    status = models.CharField(max_length=20, choices=PROPOSAL_STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Barter Proposal for '{self.request.skill.title}' offering '{self.offered_skill.title}'"


class Transaction(models.Model):
    TRANSACTION_STATUS_CHOICES = [
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    request = models.ForeignKey(Request, on_delete=models.SET_NULL, null=True, related_name='transactions')
    provider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                 related_name='provided_transactions')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                 related_name='received_transactions')
    exchange_type = models.CharField(max_length=20, choices=Skill.EXCHANGE_TYPE_CHOICES)
    barter_proposal = models.OneToOneField(BarterProposal, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS_CHOICES, default='Completed')
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-completed_at']

    def __str__(self):
        return f"Transaction for '{self.request.skill.title}' on {self.completed_at.strftime('%Y-%m-%d')}"


class Rating(models.Model):
    request = models.OneToOneField(Request, on_delete=models.SET_NULL, null=True, related_name='rating')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='ratings')
    rater = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='given_ratings')
    rated_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_ratings')
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('request', 'rater')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.rating} stars for '{self.skill.title}' by {self.rater.username}"