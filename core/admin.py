from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Skill, Request

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('school_id', 'department', 'profile_picture', 'bio')}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'department')

admin.site.register(CustomUser, CustomUserAdmin)

@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'category', 'exchange_type', 'created_at')
    list_filter = ('category', 'exchange_type', 'owner')
    search_fields = ('title', 'description', 'owner__username')

@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ('skill', 'requester', 'status', 'created_at')
    list_filter = ('status', 'requester')
    search_fields = ('skill__title', 'requester__username')