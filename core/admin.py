# in core/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
# Import the new models
from .models import CustomUser, Skill, Request

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