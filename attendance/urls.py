from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('register/student/', views.student_registration, name='student_registration'),
    path('register/lecturer/', views.lecturer_registration, name='lecturer_registration'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('dashboard/', views.lecturer_dashboard, name='lecturer_dashboard'),
    path('dashboard/add-course/', views.add_course, name='add_course'),
    path('terminal/start/<int:course_id>/', views.attendance_terminal, name='attendance_terminal'),
    path('api/process-frame/', views.process_frame, name='process_frame_api'),
    path('dashboard/sessions/', views.session_list, name='session_list'),
    path('dashboard/session/<int:session_id>/', views.session_detail, name='session_detail'),
    path('dashboard/session/<int:session_id>/pdf/', views.export_session_pdf, name='export_session_pdf'),
]