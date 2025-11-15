# in core/urls.py

from django.urls import path
from . import views

# 👇 ======================= THIS IS THE FIX ======================= 👇
# Add this line to create the 'core' namespace that the template is looking for.
app_name = 'core'
# 👆 ============================================================= 👆

urlpatterns = [
    # Note: We removed list_requests from here in a previous step, which was correct.
    path('signup/', views.signup_view, name='signup'),
    path('skill/<int:skill_id>/request/', views.create_skill_request, name='create_skill_request'),
    path('request/<int:request_id>/propose-barter/', views.create_barter_proposal, name='propose_barter'),
    path('transactions/', views.transaction_history, name='transaction_history'),
    path('request/<int:request_id>/update/<str:status>/', views.update_request_status, name='update_request_status'),
    path('request/<int:request_id>/feedback/', views.leave_feedback, name='leave_feedback'),
    path('request/<int:request_id>/complete/', views.complete_session, name='complete_session'),
    path('request/<int:request_id>/complete/', views.complete_session, name='complete_session'),

    #========== ADD THESE 4 CHAT URLs ==========
    path('chat/<str:username>/', views.chat_page, name='chat_page'),
    path('conversations/', views.conversation_list, name='conversation_list'),
    path('api/unread-count/', views.get_unread_count, name='get_unread_count'),
    path('api/mark-read/<str:username>/', views.mark_conversation_as_read, name='mark_conversation_as_read'),
]