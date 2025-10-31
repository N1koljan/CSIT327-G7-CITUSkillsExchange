from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('edit_profile/', views.edit_profile_view, name='edit_profile'),
    path('my_skills/', views.my_skill_view, name='my_skills'),
    path('requests/', views.request_view, name='requests'),
    path('find_skills/', views.find_skill_view, name='find_skills'),
    path('schedule/', views.schedule_view, name='schedule'),
    path('notification/', views.notification_view, name='notification'),
    path('chat/', views.chat_view, name='chat'),
    path('skill/', views.skill_view, name='skill'),
    path('logout/', views.logout_view, name='logout'),
]
