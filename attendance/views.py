from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, FileResponse
from django.db.models import Count
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
import io
import base64
import json
import tempfile
from datetime import date
import cv2
import numpy as np
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from .models import Student, Course, AttendanceSession, AttendanceRecord
from .forms import LoginForm, RegistrationForm, LecturerRegistrationForm, CourseForm


HAAR_CASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'


def is_lecturer(user):
    return user.is_staff


def train_lbph_model_from_samples(face_samples_b64: list) -> str:

    face_cascade = cv2.CascadeClassifier(HAAR_CASCADE_PATH)
    
    face_samples = []

    user_id = 1 
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
            
            if User.objects.filter(username=email).exists() or Student.objects.filter(matric_number=matric_number).exists():
                messages.error(request, 'A user with this email or matric number already exists.')
                return redirect('student_registration')

            face_samples_json = request.POST.get('face_samples')
            if not face_samples_json:
                messages.error(request, 'No face samples were captured. Please try again.')
                return redirect('student_registration')

            model_b64 = train_lbph_model_from_samples(json.loads(face_samples_json))

            if not model_b64:
                messages.error(request, 'Could not detect a clear face in enough samples. Try again in better lighting.')
                return redirect('student_registration')
            
            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=email,
                        password=form.cleaned_data['password'],
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        email=email
                    )
                    Student.objects.create(user=user, matric_number=matric_number, lbph_model_data=model_b64)
                messages.success(request, 'Registration successful! You can now log in.')
                return redirect('login')
            except Exception as e:
                messages.error(request, f'An error occurred: {e}')
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
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                return redirect('lecturer_dashboard' if user.is_staff else 'student_dashboard')
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
@user_passes_test(is_lecturer, login_url='login', redirect_field_name=None)
def add_course(request):

    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course has been successfully added.')
            return redirect('lecturer_dashboard')
    else:
        form = CourseForm()
    
    return render(request, 'attendance/add_course.html', {'form': form})


@login_required
@user_passes_test(is_lecturer, login_url='login', redirect_field_name=None)
def lecturer_dashboard(request):

    courses = Course.objects.all().order_by('course_name')
    student_count = Student.objects.count()
    context = {
        'courses': courses,
        'student_count': student_count,
    }
    return render(request, 'attendance/dashboard.html', context)


@login_required
@user_passes_test(is_lecturer, login_url='login', redirect_field_name=None)
def attendance_terminal(request, course_id):

    course = get_object_or_404(Course, id=course_id)
    session = AttendanceSession.objects.create(course=course)
    return render(request, 'attendance/terminal.html', {'course': course, 'session_id': session.id})


@login_required
@user_passes_test(is_lecturer, login_url='login', redirect_field_name=None)
def session_list(request):

    sessions = AttendanceSession.objects.select_related('course').annotate(
        attendee_count=Count('attendancerecord')
    ).order_by('-created_at')
    
    return render(request, 'attendance/session_list.html', {'sessions': sessions})


@login_required
@user_passes_test(is_lecturer, login_url='login', redirect_field_name=None)
def session_detail(request, session_id):

    session = get_object_or_404(AttendanceSession, id=session_id)
    records = AttendanceRecord.objects.filter(session=session).select_related('student__user').order_by('student__user__last_name')
    return render(request, 'attendance/session_detail.html', {'session': session, 'records': records})


@login_required
@user_passes_test(is_lecturer, login_url='login', redirect_field_name=None)
def export_session_pdf(request, session_id):

    session = get_object_or_404(AttendanceSession, id=session_id)
    records = AttendanceRecord.objects.filter(session=session).select_related('student__user').order_by('student__user__last_name')

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=60, bottomMargin=60)
    
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph(f"Attendance Report: {session.course.course_name}", styles['h1']))
    elements.append(Paragraph(f"Date: {session.created_at.strftime('%A, %B %d, %Y')}", styles['h3']))
    elements.append(Paragraph(f"Course Code: {session.course.course_code}", styles['Normal']))
    elements.append(Paragraph(f"Total Attendees: {records.count()}", styles['Normal']))

    table_data = [['S/N', 'Full Name', 'Matriculation Number', 'Time Marked']]
    for i, record in enumerate(records, 1):
        table_data.append([
            i, record.student.user.get_full_name(),
            record.student.matric_number, record.timestamp.strftime('%I:%M:%S %p')
        ])
    
    table = Table(table_data, colWidths=[40, 200, 150, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#002366')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), 
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),

        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#E6F7FF')),
    ]))
    elements.append(table)
    doc.build(elements)
    
    buffer.seek(0)
    filename = f"Attendance_{session.course.course_code}_{session.created_at.strftime('%Y-%m-%d')}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)



@csrf_exempt
@user_passes_test(is_lecturer, login_url='login', redirect_field_name=None)
@login_required
def process_frame(request):

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        session = get_object_or_404(AttendanceSession, id=session_id)
        

        image_data_url = data.get('image')
        format, imgstr = image_data_url.split(';base64,')
        image_data = base64.b64decode(imgstr)
        nparr = np.frombuffer(image_data, np.uint8)
        gray = cv2.cvtColor(cv2.imdecode(nparr, cv2.IMREAD_COLOR), cv2.COLOR_BGR2GRAY)
        
        face_cascade = cv2.CascadeClassifier(HAAR_CASCADE_PATH)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)

        if len(faces) != 1:
            return JsonResponse({'status': 'error', 'message': 'Please ensure one clear face is visible.'})

        x, y, w, h = faces[0]
        face_roi = gray[y:y+h, x:x+w]

        students_data = Student.objects.values('id', 'lbph_model_data')
        
        for student_data in students_data:
            model_b64 = student_data['lbph_model_data']
            with io.BytesIO(base64.b64decode(model_b64)) as mem_buffer:
                recognizer = cv2.face.LBPHFaceRecognizer_create()
                recognizer.read(mem_buffer)
            
            label, confidence = recognizer.predict(face_roi)

            if confidence < 65:
                matched_student = get_object_or_404(Student, id=student_data['id'])
                record, created = AttendanceRecord.objects.get_or_create(student=matched_student, session=session)

                if created:
                    return JsonResponse({'status': 'success', 'student_name': matched_student.user.get_full_name(), 'matric_number': matched_student.matric_number, 'timestamp': timezone.now().strftime('%I:%M:%S %p')})
                else:
                    return JsonResponse({'status': 'already_marked', 'student_name': matched_student.user.get_full_name()})
        
        return JsonResponse({'status': 'error', 'message': 'Face not recognized.'})

    except Exception:
        return JsonResponse({'status': 'error', 'message': 'An unexpected server error occurred.'}, status=500)
        
        
def custom_404_view(request, exception):
    return render(request, '404.html', status=404)

def custom_500_view(request):
    return render(request, '500.html', status=500)
