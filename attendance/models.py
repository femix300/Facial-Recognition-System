from django.db import models
from django.contrib.auth.models import User

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    matric_number = models.CharField(max_length=100, unique=True, verbose_name="Matriculation Number")
    lbph_model_data = models.TextField()

    def __str__(self):
        return self.user.get_full_name()


class Course(models.Model):
    course_code = models.CharField(max_length=20, unique=True)
    course_name = models.CharField(max_length=200)
    lecturer = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.course_code} - {self.course_name}"

class AttendanceSession(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session for {self.course.course_code} on {self.created_at.strftime('%Y-%m-%d')}"

class AttendanceRecord(models.Model):
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_present = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.student} marked in {self.session}"