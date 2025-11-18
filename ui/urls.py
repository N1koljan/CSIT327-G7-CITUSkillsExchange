# in ui/urls.py

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
    path('notification/', views.notification_view, name='notification'),
    path('feedback/', views.feedback_history_view, name='feedback_history'),

    # --- NEW & UPDATED URLs for Skill Management ---

    # "My Skills" Dashboard (WBS 4.1.7) - This replaces the old 'my_skills' path.
    path('my-skills/', views.my_skills_list, name='my_skills'),

    # Edit an existing skill (WBS 4.1.5)
    # The <int:pk> part captures the unique ID of the skill.
    path('skill/<int:pk>/edit/', views.skill_edit, name='skill_edit'),
    path('skill/<int:skill_id>/comment/', views.add_comment_to_skill, name='add_comment'),

    # Delete a skill (WBS 4.1.6)
    path('skill/<int:pk>/delete/', views.skill_delete, name='skill_delete'),
    # Your placeholder URL for requests/ can now be used for the main dashboard
    path('requests/', views.request_dashboard, name='requests'),

    path('skill/<int:skill_pk>/request/', views.request_create, name='request_create'),

    # Action URL to update a request's status (e.g., accept or decline)
    path('request/<int:pk>/update/<str:action>/', views.update_request_status, name='request_update_status'),
    path('chat/', views.chat_view, name='chat'),
    path('logout/', views.logout_view, name='logout'),

    # Chat URLs
    path('chat/', views.chat_view, name='conversation_list'),
    path('chat/<str:username>/', views.chat_view, name='chat_page'),

    #transaction URLs
    path('transactions/', views.transaction_view, name='transaction'),
]
