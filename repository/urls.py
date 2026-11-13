from django.urls import path
from . import views

app_name = 'repository'

urlpatterns = [
    # Existing URLs
    path('', views.home, name='home'),
    path('library/', views.library, name='library'),
    
    # Core-Sage Doubt Engine URLs
    path('ask/', views.ask_core_sage, name='ask_core_sage'),
    path('api/submit-doubt/', views.submit_doubt, name='submit_doubt'),
    path('history/', views.doubt_history, name='doubt_history'),
    path('doubt/<int:doubt_id>/', views.doubt_detail, name='doubt_detail'),
    
    # Payment & Upgrade URLs
    path('upgrade/', views.upgrade_to_premium, name='upgrade'),
    path('api/verify-payment/<str:transaction_id>/', views.verify_payment, name='verify_payment'),
    
    # Teacher Inbox (Command Uplink)
    path('teacher/inbox/', views.teacher_inbox, name='teacher_inbox'),
    path('teacher/respond/<int:inbox_id>/', views.respond_to_doubt, name='respond_to_doubt'),
    path('login/', views.login_register_page, name='login_page'),
path('api/login/', views.api_login, name='api_login'),
path('api/register/', views.api_register, name='api_register'),
    path('logout/', views.logout_view, name='logout'),
    path('test-chatgpt/', views.test_chatgpt, name='test_chatgpt'),
    path('dashboard/', views.dashboard, name='dashboard'),
path('api/update-profile/', views.update_profile, name='update_profile'),
path('classes/', views.classes_list, name='classes'),
path('api/enroll-class/<int:class_id>/', views.enroll_class, name='enroll_class'),
path('schedule-class/', views.schedule_class, name='schedule_class'),
path('api/schedule-class/', views.api_schedule_class, name='api_schedule_class'),
path('python-interpreter/', views.python_interpreter, name='python_interpreter'),
]
