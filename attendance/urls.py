from django.urls import path, reverse_lazy
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('register/student/', views.student_registration, name='student_registration'),
    path('register/lecturer/', views.lecturer_registration, name='lecturer_registration'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('dashboard/', views.lecturer_dashboard, name='lecturer_dashboard'),
    path('dashboard/add-course/', views.add_course, name='add_course'),
    path('dashboard/course/edit/<int:course_id>/', views.edit_course, name='edit_course'),
    path('dashboard/course/delete/<int:course_id>/', views.delete_course, name='delete_course'),
    #new form to set the session duration.
    path('session/create/<int:course_id>/', views.create_session, name='create_session'),
    #terminal operates on a specific, pre-configured session.
    path('terminal/<int:session_id>/', views.attendance_terminal, name='attendance_terminal'),
    # this url allow lecturers to update a student's status
    path('record/update_status/<int:record_id>/', views.update_record_status, name='update_record_status'),
    
    path('api/process-frame/', views.process_frame, name='process_frame_api'),
    path('dashboard/sessions/', views.session_list, name='session_list'),
    path('dashboard/session/<int:session_id>/', views.session_detail, name='session_detail'),
    path('dashboard/session/<int:session_id>/pdf/', views.export_session_pdf, name='export_session_pdf'),
    
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='attendance/password_reset_form.html',
        html_email_template_name='attendance/password_reset_email.html',
        subject_template_name='attendance/password_reset_subject.txt',
        success_url=reverse_lazy('password_reset_done')
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='attendance/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='attendance/password_reset_confirm.html',
        success_url=reverse_lazy('password_reset_complete')
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='attendance/password_reset_complete.html'
    ), name='password_reset_complete'),
]