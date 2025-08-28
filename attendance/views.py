from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, FileResponse
from django.db.models import Count
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import authenticate, login, logout, views as auth_views
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse_lazy
import io
import base64
import json
import tempfile
from datetime import date
import cv2
import logging
import numpy as np
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from .models import Student, Course, AttendanceSession, AttendanceRecord
from .forms import LoginForm, RegistrationForm, LecturerRegistrationForm, CourseForm, SessionCreationForm


logger = logging.getLogger(__name__)

HAAR_CASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'


def is_lecturer(user):
    return user.is_staff


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
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            matric_number = form.cleaned_data['matric_number']
            
            if User.objects.filter(username=email).exists():
                messages.error(request, 'A user with this email already exists.')
                return render(request, 'attendance/registration.html', {'form': form})
            if Student.objects.filter(matric_number=matric_number).exists():
                messages.error(request, 'A student with this matriculation number already exists.')
                return render(request, 'attendance/registration.html', {'form': form})

            face_samples_json = request.POST.get('face_samples')
            if not face_samples_json:
                messages.error(request, 'Face samples were not provided. Please complete the face capture step.')
                return render(request, 'attendance/registration.html', {'form': form})

            try:
                face_samples = json.loads(face_samples_json)
                
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=email,
                        password=form.cleaned_data['password'],
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        email=email
                    )
                    
                    # Train the model AFTER user creation (now user.id exists)
                    model_b64 = train_lbph_model_from_samples(face_samples, user.id)
                    
                    Student.objects.create(
                        user=user, 
                        matric_number=matric_number, 
                        lbph_model_data=model_b64
                    )
                
                messages.success(request, 'Registration successful! You can now log in.')
                return redirect('login')
            except ValueError as ve:
                messages.error(request, f"Face recognition failed: {ve}. Please try again in better lighting and ensure your face is clear.")
            except Exception as e:
                logger.error(f"An unexpected error occurred during student registration: {e}")
                messages.error(request, 'An unexpected error occurred. Please check your details and try again.')
    
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

            user = authenticate(request, username=email, password=password)

            if user is not None:
                if user_type == 'lecturer' and user.is_staff:
                    login(request, user)
                    return redirect('lecturer_dashboard')
                elif user_type == 'student' and not user.is_staff:
                    login(request, user)
                    return redirect('student_dashboard')
                else:
                    messages.error(request, f"You do not have permission to log in as a {user_type}.")
            else:
                messages.error(request, 'Invalid email or password.')
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
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = LecturerRegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            
            if User.objects.filter(username=email).exists():
                messages.error(request, 'A user with this email already exists.')
                return redirect('lecturer_registration')
            
            try:

                user = User.objects.create_user(
                    username=email,
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    email=email,
                    is_staff=True
                )
                messages.success(request, 'Lecturer account created successfully. You can now log in.')
                return redirect('login')
            except Exception as e:
                messages.error(request, f'An error occurred: {e}')
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
    total_students = Student.objects.filter(records__session__course__lecturer=request.user).distinct().count()

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
            
            session = AttendanceSession(
                course=course,
                start_time=form.cleaned_data['start_time'],
                end_time=form.cleaned_data['end_time']
            )
            session.save()
            
            return redirect('attendance_terminal', session_id=session.id)
    else:
        initial_data = {
            'start_time': timezone.now(),
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
    return render(request, 'attendance/attendance_terminal.html', {'course': session.course, 'session_id': session.id})


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
    records = AttendanceRecord.objects.filter(session=session).select_related('student__user').order_by('student__user__last_name')
    return render(request, 'attendance/session_detail.html', {'session': session, 'records': records})


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