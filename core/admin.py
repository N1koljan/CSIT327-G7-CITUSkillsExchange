# in core/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib import admin
from .models import (
    CustomUser,
    Skill,
    Request,
    BarterProposal,
    Transaction,
    Rating,
    Comment,
    Schedule,
    Message,
    Notification,
    NotificationPreference
)

# --- Existing CustomUser Admin Configuration (with minor improvements) ---
# I've added your other custom fields to the fieldsets so they are editable in the admin.
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('school_id', 'department', 'profile_picture', 'bio')}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'department')

# Register the CustomUser model with its custom admin class
admin.site.register(CustomUser, CustomUserAdmin)


# --- NEW: Register the Skill and Request Models ---

# This uses a decorator, which is a modern way to register models.
# It makes the admin interface for Skills more useful.
@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    # Fields to display in the list view
    list_display = ('title', 'owner', 'category', 'exchange_type', 'created_at')
    # Add filters on the right side
    list_filter = ('category', 'exchange_type', 'owner')
    # Add a search bar to search these fields
    search_fields = ('title', 'description', 'owner__username')


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ('skill', 'requester', 'status', 'created_at')
    list_filter = ('status', 'requester')
    search_fields = ('skill__title', 'requester__username')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['recipient__username', 'title', 'message']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Notification Details', {
            'fields': ('recipient', 'notification_type', 'title', 'message', 'link')
        }),
        ('Status', {
            'fields': ('is_read', 'created_at')
        }),
        ('Related Objects', {
            'fields': ('related_request', 'related_user'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'recipient', 'related_user', 'related_request'
        )


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'email_new_request',
        'email_request_accepted',
        'push_enabled',
        'updated_at'
    ]
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Email Notifications', {
            'fields': (
                'email_new_request',
                'email_request_accepted',
                'email_schedule_reminders',
                'email_new_messages'
            )
        }),
        ('Push Notifications', {
            'fields': ('push_enabled', 'push_session_reminders')
        }),
        ('Feedback & Reviews', {
            'fields': ('feedback_reminders', 'feedback_received')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )