from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid 

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    matric_number = models.CharField(max_length=100, unique=True, verbose_name="Matriculation Number")
    face_encodings_data = models.TextField(
        null=True,
        blank=True,
        help_text="JSON-encoded list of 128-dimensional face encodings from dlib."
    )


    def __str__(self):
        return self.user.get_full_name()


class Course(models.Model):
    course_code = models.CharField(max_length=20, unique=True)
    course_name = models.CharField(max_length=200)
    lecturer = models.ForeignKey(User, on_delete=models.CASCADE)
    enrolled_students = models.ManyToManyField('Student', related_name='courses', blank=True)

    def __str__(self):
        return f"{self.course_code} - {self.course_name}"

class AttendanceSession(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Session for {self.course.course_code} on {self.created_at.strftime('%Y-%m-%d')}"

class AttendanceRecord(models.Model):
    STATUS_CHOICES = (
        ('on_time', 'On Time'),
        ('late', 'Late'),
    )
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name='records')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='records')
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='on_time')

    class Meta:
        unique_together = ('session', 'student')

    def __str__(self):
        return f"{self.student} marked for {self.session.course.course_code} - {self.status}"
        
        
class PasswordReset(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reset_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_when = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Password reset for {self.user.username}"