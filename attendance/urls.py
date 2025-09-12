from django.urls import path, reverse_lazy
from . import views

urlpatterns = [
    # Main and Authentication URLs
    path('', views.home, name='home'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    
    # Registration URLs
    path('register/student/', views.student_registration, name='student_registration'),
    path('register/lecturer/', views.lecturer_registration, name='lecturer_registration'),
    
    # Custom Password Reset URLs
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('password-reset-sent/<uuid:reset_id>/', views.password_reset_sent, name='password_reset_sent'),
    path('reset-password/<uuid:reset_id>/', views.reset_password, name='reset_password'),
    path('reset-password/complete/', views.password_reset_complete, name='password_reset_complete'),

    # Student Dashboard
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/dashboard/profile/', views.student_update_profile, name='student_update_profile'),
    
    # Lecturer Dashboard and Course Management
    path('dashboard/', views.lecturer_dashboard, name='lecturer_dashboard'),
    path('dashboard/profile/', views.lecturer_update_profile, name='lecturer_update_profile'),
    path('dashboard/students/', views.student_list, name='student_list'),
    path('dashboard/add-course/', views.add_course, name='add_course'),
    path('dashboard/course/edit/<int:course_id>/', views.edit_course, name='edit_course'),
    path('dashboard/course/delete/<int:course_id>/', views.delete_course, name='delete_course'),
    
    # Session and Attendance Management
    path('session/create/<int:course_id>/', views.create_session, name='create_session'),
    path('terminal/<int:session_id>/', views.attendance_terminal, name='attendance_terminal'),
    path('session/close/<int:session_id>/', views.close_session, name='close_session'),
    path('record/update_status/<int:record_id>/', views.update_record_status, name='update_record_status'),
    path('dashboard/sessions/', views.session_list, name='session_list'),
    path('dashboard/session/<int:session_id>/', views.session_detail, name='session_detail'),
    path('dashboard/session/<int:session_id>/pdf/', views.export_session_pdf, name='export_session_pdf'),
    
    # API Endpoint for Face Recognition
    path('api/process-frame/<int:session_id>/', views.process_frame, name='process_frame_api'),
    path('profile/delete/', views.delete_account, name='delete_account'),
]