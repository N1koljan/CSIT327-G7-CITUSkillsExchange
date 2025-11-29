# ui/urls.py - Updated version

from django.urls import path
from . import views

urlpatterns = [
    # --- Existing URLs ---
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('edit_profile/', views.edit_profile_view, name='edit_profile'),
    path('logout/', views.logout_view, name='logout'),
    path('requests/', views.request_dashboard, name='requests'),
    path('find_skills/', views.find_skill_view, name='find_skills'),
    path('schedule/', views.schedule_view, name='schedule'),

    # --- Notification URLs ---
    path('notification/', views.notification_view, name='notification'),
    path('notification/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notification/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notification/<int:notification_id>/delete/', views.delete_notification, name='delete_notification'),
    path('notification/preferences/update/', views.update_notification_preferences,
         name='update_notification_preferences'),
    path('api/notifications/unread-count/', views.get_unread_notification_count, name='get_unread_notification_count'),

    path('feedback/', views.feedback_history_view, name='feedback_history'),

    # --- Skill Management URLs ---
    path('my-skills/', views.my_skills_list, name='my_skills'),
    path('skill/<int:pk>/edit/', views.skill_edit, name='skill_edit'),
    path('skill/<int:skill_id>/comment/', views.add_comment_to_skill, name='add_comment'),
    path('skill/<int:pk>/delete/', views.skill_delete, name='skill_delete'),
    path('skill/<int:pk>/get/', views.skill_get_json, name='skill_get_json'),
    path('skill/<int:skill_pk>/request/', views.request_create, name='request_create'),

    # --- Request URLs ---
    path('request/<int:pk>/update/<str:action>/', views.update_request_status, name='request_update_status'),

    # --- Chat URLs ---
    path('chat/', views.chat_view, name='conversation_list'),
    path('chat/<str:username>/', views.chat_view, name='chat_page'),

    # --- Transaction URLs ---
    path('transactions/', views.transaction_view, name='transaction'),

    # --- Schedule URLs ---
    path('schedule/delete/<int:schedule_id>/', views.delete_schedule, name='delete_schedule'),

]