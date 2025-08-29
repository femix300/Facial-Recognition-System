from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, FileResponse
from django.db.models import Count, Q
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import authenticate, login, logout
from .models import PasswordReset 
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse_lazy, reverse
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings
import io
import base64
import json
import tempfile
from datetime import date
import cv2
import logging
import numpy as np
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from .models import Student, Course, AttendanceSession, AttendanceRecord, PasswordReset
from .forms import LoginForm, RegistrationForm, LecturerRegistrationForm, CourseForm, SessionCreationForm, LecturerProfileUpdateForm, StudentProfileUpdateForm


logger = logging.getLogger(__name__)

HAAR_CASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'


def is_lecturer(user):
    return user.is_staff
    
def is_student(user):
    return not user.is_staff and hasattr(user, 'student')


def train_lbph_model_from_samples(face_samples_b64: list, user_id: int) -> str:

    face_cascade = cv2.CascadeClassifier(HAAR_CASCADE_PATH)
    
    face_samples = []
    ids = []

    for b64_img in face_samples_b64:
        try:

            _format, img_str = b64_img.split(';base64,')
   
            image_data = base64.b64decode(img_str)
          
            nparr = np.frombuffer(image_data, np.uint8)
            
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)
            
            if len(faces) == 1:
                x, y, w, h = faces[0]

                face_samples.append(gray[y:y+h, x:x+w])
                ids.append(user_id)
        except Exception as e:

            print(f"Skipping a problematic image sample. Error: {e}")
            continue

    
    if len(face_samples) < 10:
        raise ValueError(f"Insufficient valid face samples. Found {len(face_samples)}, need at least 10.")

    
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(face_samples, np.array(ids))
    
    with tempfile.NamedTemporaryFile(delete=True, suffix='.yml') as temp_f:
        recognizer.write(temp_f.name)
        temp_f.seek(0)
        model_bytes = temp_f.read()
    return base64.b64encode(model_bytes).decode('utf-8')



def home(request):

    return render(request, 'attendance/home.html')


def student_registration(request):
    """
    Handles new student registration by leveraging form validation and ensuring
    database operations are atomic and secure.
    """
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            try:

                with transaction.atomic():
                    user = User.objects.create_user(
                        username=form.cleaned_data['email'],
                        email=form.cleaned_data['email'],
                        password=form.cleaned_data['password'],
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name']
                    )
                    face_samples_b64 = json.loads(form.cleaned_data['face_samples'])
                    model_data = train_lbph_model_from_samples(face_samples_b64, user.id)
                    
                    Student.objects.create(
                        user=user,
                        matric_number=form.cleaned_data['matric_number'],
                        lbph_model_data=model_data
                    )
                
                messages.success(request, 'Student account created successfully! You can now log in.')
                return redirect('login')

            except ValueError as ve:

                messages.error(request, f"Face recognition setup failed: {ve}. Please try again in better lighting and ensure your face is clear.")
            except Exception as e:

                logger.error(f"An unexpected error occurred during student registration: {e}")
                messages.error(request, 'An unexpected server error occurred. Please try again.')
    
    else: 

        form = RegistrationForm()
    return render(request, 'attendance/registration.html', {'form': form})


def login_user(request):
    """Handles user login and redirects based on role (student or lecturer)."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user_type = form.cleaned_data['user_type']

            try:
                user_obj = User.objects.get(username=email)
            except User.DoesNotExist:
            
                messages.error(request, f"No account is registered with the email: {email}.")
                return render(request, 'attendance/login.html', {'form': form})

            user = authenticate(request, username=email, password=password)

            if user is not None:
                if user_type == 'lecturer' and user.is_staff:
                    login(request, user)
                    return redirect('lecturer_dashboard')
                elif user_type == 'student' and not user.is_staff:
                    login(request, user)
                    return redirect('student_dashboard')
                else:
                    messages.error(request, f"Your account does not have permission to log in as a {user_type}.")
            else:

                messages.error(request, 'Incorrect password. Please try again.')
    else:
        form = LoginForm()

    return render(request, 'attendance/login.html', {'form': form})


@login_required
def logout_user(request):
    """Logs the current user out."""
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('home')



@login_required
def student_dashboard(request):
    if request.user.is_staff:
        return redirect('lecturer_dashboard')

    student = get_object_or_404(Student, user=request.user)
    

    records = AttendanceRecord.objects.filter(student=student).select_related(
        'session__course'
    ).order_by('-session__created_at')


    today = timezone.now()
    attendance_dates_this_month = records.filter(
        session__created_at__year=today.year,
        session__created_at__month=today.month
    ).values_list('session__created_at__day', flat=True)
    
    import calendar
    cal = calendar.Calendar()
    month_days = cal.itermonthdates(today.year, today.month)
    

    day_headers = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    context = {
        'student': student,
        'records': records,
        'attendance_this_month': len(attendance_dates_this_month),
        'attended_days_set': set(attendance_dates_this_month),
        'month_days': month_days,
        'today': today.date(),
        'day_headers': day_headers,
    }
    
    return render(request, 'attendance/student_dashboard.html', context)



def lecturer_registration(request):
    """Handles new lecturer registration using form validation."""
    if request.user.is_authenticated:
        return redirect(home)
        
    if request.method == 'POST':
        form = LecturerRegistrationForm(request.POST)
        if form.is_valid():
            User.objects.create_user(
                username=form.cleaned_data['email'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                is_staff=True
            )
            messages.success(request, 'Lecturer account created successfully! Please log in.')
            return redirect('login')
    else:
        form = LecturerRegistrationForm()

    return render(request, 'attendance/lecturer_registration.html', {'form': form})
    
@login_required
@user_passes_test(is_lecturer)
def add_course(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            new_course = form.save(commit=False)
            new_course.lecturer = request.user
            new_course.save()
            messages.success(request, f"Course '{new_course.course_name}' created successfully!")
            return redirect('lecturer_dashboard')
    else:
        form = CourseForm()
    
    return render(request, 'attendance/add_course.html', {'form': form})
    
@login_required
@user_passes_test(is_lecturer)
def lecturer_dashboard(request):
    # Fetch courses with annotations for student and session counts
    courses = Course.objects.filter(lecturer=request.user).annotate(
        student_count=Count('attendancesession__records__student', distinct=True),  # Traverse relations: course <- session <- record -> student
        session_count=Count('attendancesession')  # Direct reverse relation to sessions (distinct not needed here)
    ).order_by('course_code')

    # Aggregate totals
    total_courses = courses.count()
    total_sessions = AttendanceSession.objects.filter(course__lecturer=request.user).count()
    total_students = Student.objects.filter(
        records__session__course__lecturer=request.user, 
        user__is_staff=False
    ).distinct().count()


    context = {
        'courses': courses,
        'total_courses': total_courses,
        'total_sessions': total_sessions,
        'total_students': total_students,
    }
    
    return render(request, 'attendance/dashboard.html', context)

    
@login_required
@user_passes_test(is_lecturer)
def edit_course(request, course_id):
    """
    Handles editing an existing course.
    """
    course = get_object_or_404(Course, id=course_id, lecturer=request.user)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, f"'{course.course_name}' has been updated successfully.")
            return redirect('lecturer_dashboard')
    else:
        form = CourseForm(instance=course)
    
    return render(request, 'attendance/edit_course.html', {'form': form, 'course': course})


@login_required
@user_passes_test(is_lecturer)
def delete_course(request, course_id):
    """
    Handles deleting a course after confirmation.
    This view should only accept POST requests for safety.
    """
    course = get_object_or_404(Course, id=course_id, lecturer=request.user)
    if request.method == 'POST':
        course_name = course.course_name
        course.delete()
        messages.success(request, f"The course '{course_name}' has been deleted.")
        return redirect('lecturer_dashboard')
    
    return redirect('lecturer_dashboard')
    
@login_required
@user_passes_test(is_lecturer)
def create_session(request, course_id):
    course = get_object_or_404(Course, id=course_id, lecturer=request.user)
    
    if request.method == 'POST':
        form = SessionCreationForm(request.POST)
        if form.is_valid():
            start_time = timezone.now()
            end_time = form.cleaned_data['end_time']

            if AttendanceSession.objects.filter(course=course, end_time__gt=start_time, is_active=True).exists():
                messages.error(request, "An active session for this course is already running.")
                return redirect('lecturer_dashboard')

            session = AttendanceSession.objects.create(
                course=course,
                start_time=start_time,
                end_time=end_time,
                is_active=True
            )
        
            return redirect('attendance_terminal', session_id=session.id)
    else:
        initial_data = {
            'end_time': timezone.now() + timedelta(hours=1)
        }
        form = SessionCreationForm(initial=initial_data)
        
    context = {
        'form': form,
        'course': course
    }
    return render(request, 'attendance/create_session.html', context)


@login_required
@user_passes_test(is_lecturer)
def attendance_terminal(request, session_id):
    session = get_object_or_404(AttendanceSession, id=session_id, course__lecturer=request.user)
    context = {
        'session': session,
        'course': session.course 
    }
    return render(request, 'attendance/terminal.html', context)


@login_required
@user_passes_test(is_lecturer, login_url='login', redirect_field_name=None)
def session_list(request):
    sessions = AttendanceSession.objects.filter(
        course__lecturer=request.user
    ).select_related('course').annotate(
        attendee_count=Count('records')
    ).order_by('-created_at')

    return render(request, 'attendance/session_list.html', {'sessions': sessions})


@login_required
@user_passes_test(is_lecturer, login_url='login', redirect_field_name=None)
def session_detail(request, session_id):
    session = get_object_or_404(
        AttendanceSession, 
        id=session_id, 
        course__lecturer=request.user
    )
    on_time_records = session.records.filter(status='on_time').select_related('student__user')
    late_records = session.records.filter(status='late').select_related('student__user')
    
    context = {
        'session': session,
        'on_time_records': on_time_records,
        'late_records': late_records,
    }
    
    return render(request, 'attendance/session_detail.html', context)


@login_required
@user_passes_test(is_lecturer)
def export_session_pdf(request, session_id):
    session = get_object_or_404(AttendanceSession, id=session_id, course__lecturer=request.user)
    records = AttendanceRecord.objects.filter(session=session).select_related('student__user').order_by('status', 'student__user__last_name')

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph(f"Attendance Report: {session.course.course_name}", styles['h1']))
    elements.append(Paragraph(f"Course Code: {session.course.course_code}", styles['h2']))
    elements.append(Paragraph(f"Date: {session.created_at.strftime('%A, %B %d, %Y')}", styles['h3']))
    elements.append(Paragraph(f"Class Time Window: {session.start_time.strftime('%I:%M %p')} - {session.end_time.strftime('%I:%M %p')}", styles['h3']))

    data = [["S/N", "Full Name", "Matric Number", "Time Marked", "Status"]]
    for i, record in enumerate(records):
        data.append([
            str(i + 1),
            record.student.user.get_full_name(),
            record.student.matric_number,
            record.timestamp.strftime('%I:%M:%S %p'),
            record.get_status_display() # e.g., "On Time" or "Late"
        ])
    
    table = Table(data, colWidths=[40, 180, 120, 100, 60])
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0056b3')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])
    table.setStyle(style)
    elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f'attendance_{session.course.course_code}_{session.id}.pdf')

@csrf_exempt
@login_required
@user_passes_test(is_lecturer)
def process_frame(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

    try:
        data = json.loads(request.body)
        image_data_url = data.get('image')
        session_id = data.get('session_id')

        if not image_data_url or not session_id:
            return JsonResponse({'status': 'error', 'message': 'Missing image or session ID.'}, status=400)

        session = get_object_or_404(AttendanceSession, id=session_id)

        # Decode the image and prepare it for processing
        _format, img_str = image_data_url.split(';base64,')
        image_data = base64.b64decode(img_str)
        nparr = np.frombuffer(image_data, np.uint8)
        gray = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)

        # Detect faces in the image
        face_cascade = cv2.CascadeClassifier(HAAR_CASCADE_PATH)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)

        if len(faces) != 1:
            return JsonResponse({'status': 'error', 'message': 'Please ensure one clear face is visible.'})

        x, y, w, h = faces[0]
        face_roi = gray[y:y+h, x:x+w]
        
        students = Student.objects.select_related('user').all()
        """
        students = session.course.enrolled_students.select_related('user').all()
        
        if not students:
            return JsonResponse({'status': 'error', 'message': 'No students are enrolled in this course.'})
        """
        
        recognized_student = None
        recognition_confidence = 100 

        for student in students:
            if not student.lbph_model_data:
                continue

            with tempfile.NamedTemporaryFile(delete=True, suffix='.yml') as temp_f:
                temp_f.write(base64.b64decode(student.lbph_model_data))
                temp_f.flush()
                
                recognizer = cv2.face.LBPHFaceRecognizer_create()
                recognizer.read(temp_f.name)

                label, confidence = recognizer.predict(face_roi)

                if label == student.user.id and confidence < 65:
                    recognized_student = student
                    recognition_confidence = confidence
                    break

        if recognized_student:
            current_status = 'on_time' if timezone.now() <= session.end_time else 'late'
            
            record, created = AttendanceRecord.objects.get_or_create(
                student=recognized_student,
                session=session,
                defaults={'status': current_status}
            )

            if created:
                return JsonResponse({
                    'status': 'success',
                    'student_name': recognized_student.user.get_full_name(),
                    'matric_number': recognized_student.matric_number,
                    'timestamp': record.timestamp.strftime('%I:%M:%S %p'),
                    'attendance_status': record.get_status_display()
                })
            else:
                return JsonResponse({
                    'status': 'already_marked',
                    'student_name': recognized_student.user.get_full_name()
                })
        
        return JsonResponse({'status': 'error', 'message': 'Face not recognized.'})

    except Exception as e:
        print("="*60)
        print(f"CRITICAL ERROR IN process_frame: The error is '{e}'")
        import traceback
        traceback.print_exc()
        print("="*60)
        logger.error(f"An error occurred in process_frame: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'An unexpected server error occurred.'}, status=500)
        
@login_required
@user_passes_test(is_lecturer)
def update_record_status(request, record_id):
    if request.method == 'POST':
        record = get_object_or_404(AttendanceRecord, id=record_id, session__course__lecturer=request.user)
        # Toggle status between 'late' and 'on_time'
        if record.status == 'late':
            record.status = 'on_time'
        else:
            record.status = 'late'
        record.save()
        return redirect('session_detail', session_id=record.session.id)
    return redirect('lecturer_dashboard')
        
        
def custom_404_view(request, exception):
    return render(request, '404.html', status=404)

def custom_500_view(request):
    return render(request, '500.html', status=500)
    

def forgot_password(request):
    """Handles the first step of password reset: sending the email."""
    if request.method == "POST":
        email = request.POST.get('email')
        try:
            user = User.objects.get(email__iexact=email)
            
            new_password_reset = PasswordReset.objects.create(user=user)

            password_reset_url = reverse('reset_password', kwargs={'reset_id': new_password_reset.reset_id})
            full_reset_url = f'{request.scheme}://{request.get_host()}{password_reset_url}'

            html_message = render_to_string('attendance/password_reset_email.html', {'reset_url': full_reset_url})
            subject = "[Action Required] Reset Your Password for Smart Attendance System"
            
            email_msg = EmailMessage(subject, html_message, settings.EMAIL_HOST_USER, [user.email])
            email_msg.content_subtype = "html"
            email_msg.send()

            messages.success(request, "A password reset link has been sent to your email.")
            return redirect('password_reset_sent', reset_id=new_password_reset.reset_id)
        except User.DoesNotExist:
            messages.error(request, f"No user is registered with the email '{email}'.")
            return redirect('forgot_password')

    return render(request, 'attendance/forgot-password.html')


def password_reset_sent(request, reset_id):
    """Confirms that the password reset email has been sent."""
    if not PasswordReset.objects.filter(reset_id=reset_id).exists():
        messages.error(request, 'Invalid or expired reset link.')
        return redirect('forgot_password')
    return render(request, 'attendance/password-reset-sent.html')


def reset_password(request, reset_id):
    """Handles the actual password reset after the user clicks the email link."""
    try:
        password_reset_obj = PasswordReset.objects.get(reset_id=reset_id)
        expiration_time = password_reset_obj.created_when + timedelta(minutes=10)

        if timezone.now() > expiration_time:
            messages.error(request, 'This password reset link has expired. Please request a new one.')
            password_reset_obj.delete()
            return redirect('forgot_password')

        if request.method == "POST":
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirmPassword')

            if password and password == confirm_password and len(password) >= 6:
                user = password_reset_obj.user
                user.set_password(password)
                user.save()
                password_reset_obj.delete()
                return redirect('password_reset_complete')
            else:
                if password != confirm_password:
                    messages.error(request, 'Passwords do not match. Please try again.')
                if len(password) < 6:
                    messages.error(request, 'Password must be at least 6 characters long.')
                return redirect('reset_password', reset_id=reset_id)

    except PasswordReset.DoesNotExist:
        messages.error(request, 'The reset link is invalid or has already been used.')
        return redirect('forgot_password')

    return render(request, 'attendance/reset-password.html')


def password_reset_complete(request):
    """Displays a success message after the password has been reset."""
    return render(request, 'attendance/password_reset_complete.html')
    
@login_required
def student_list(request):
    student_list = Student.objects.filter(user__is_staff=False).select_related('user').order_by('user__last_name', 'user__first_name')
    
    query = request.GET.get('q')
    if query:
        student_list = student_list.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query) |
            Q(matric_number__icontains=query)
        )
    paginator = Paginator(student_list, 10)
    page_number = request.GET.get('page')
    try:
        students = paginator.page(page_number)
    except PageNotAnInteger:
        students = paginator.page(1)
    except EmptyPage:
        students = paginator.page(paginator.num_pages)

    context = {
        'students': students,
        'total_students': paginator.count,
        'search_query': query or ''
    }
    return render(request, 'attendance/student_list.html', context)
    
@login_required
@user_passes_test(is_lecturer)
def lecturer_update_profile(request):
    user = request.user
    if request.method == 'POST':
        form = LecturerProfileUpdateForm(request.POST, instance=user, user=user)
        if form.is_valid():
            with transaction.atomic():
                user = form.save(commit=False)
                user.username = form.cleaned_data['email']
                user.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('lecturer_dashboard')
    else:
        form = LecturerProfileUpdateForm(instance=user, user=user)

    return render(request, 'attendance/lecturer_update_profile.html', {'form': form})


@login_required
@user_passes_test(is_student)
def student_update_profile(request):
    user = request.user
    if request.method == 'POST':
        form = StudentProfileUpdateForm(request.POST, instance=user, user=user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user_instance = form.save(commit=False)
                    user_instance.username = form.cleaned_data['email']
                    user_instance.save()
                    student_instance = user.student
                    student_instance.matric_number = form.cleaned_data['matric_number']
                    student_instance.save()
                    
                messages.success(request, 'Your profile has been updated successfully!')
                return redirect('student_dashboard')
            except Exception as e:
                messages.error(request, f'An error occurred: {e}')
    else:
        form = StudentProfileUpdateForm(instance=user, user=user)

    return render(request, 'attendance/student_update_profile.html', {'form': form})
    
@login_required
def delete_account(request):
    user_to_delete = request.user

    if request.method == 'POST':
        try:
            logout(request)
            user_to_delete.delete()
            
            messages.success(request, 'Your account has been successfully deleted.')
            return redirect('home')
            
        except Exception as e:
            messages.error(request, f'An error occurred while deleting your account: {e}')
            return redirect('home')

    return render(request, 'attendance/delete_account_confirm.html')
    
@login_required
@user_passes_test(is_lecturer)
def close_session(request, session_id):
    session = get_object_or_404(AttendanceSession, id=session_id, course__lecturer=request.user)
    session.is_active = False
    session.save()

    if not session.records.exists():
        session.delete()
        messages.warning(request, f"Session for {session.course.course_name} was closed and deleted because no students attended.")
    else:
        messages.success(request, f"Session for {session.course.course_name} has been successfully closed.")
        
    return redirect('lecturer_dashboard')