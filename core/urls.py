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

]