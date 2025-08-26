from django.contrib import admin
from .models import Student, Course, AttendanceSession, AttendanceRecord


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'matric_number', 'user_email')
    search_fields = ('matric_number', 'user__first_name', 'user__last_name')

    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Full Name'

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('course_name', 'course_code')
    search_fields = ('course_name', 'course_code')

@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ('course', 'created_at')
    list_filter = ('course',)

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'session', 'timestamp')
    list_filter = ('session__course', 'session__created_at')

