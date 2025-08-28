from django import forms
from .models import Course, Student
from django.utils import timezone
import datetime
from django.contrib.auth.models import User

class LoginForm(forms.Form):
    USER_TYPE_CHOICES = (
        ('student', 'Student'),
        ('lecturer', 'Lecturer'),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "name@example.com"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"})
    )
    user_type = forms.ChoiceField(
        choices=USER_TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        initial='student'
    )


class RegistrationForm(forms.Form):
    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'First Name', 'class': 'form-control'}))
    last_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'Last Name', 'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Email Address', 'class': 'form-control'}))
    matric_number = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'Matriculation Number', 'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'class': 'form-control'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password', 'class': 'form-control'}))
    face_samples = forms.CharField(widget=forms.HiddenInput())

    def clean_email(self):
    
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email

    def clean_matric_number(self):
        
        matric_number = self.cleaned_data.get('matric_number')
        if Student.objects.filter(matric_number__iexact=matric_number).exists():
            raise forms.ValidationError("A student with this Matriculation Number is already registered.")
        return matric_number

    def clean(self):
      
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match. Please try again.")
        
        return cleaned_data
    
    
class LecturerRegistrationForm(forms.Form):
    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'First Name', 'class': 'form-control'}))
    last_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'Last Name', 'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Email Address', 'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'class': 'form-control'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password', 'class': 'form-control'}))

    def clean_email(self):
      
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email

    def clean(self):
        
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match. Please try again.")

        return cleaned_data


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['course_name', 'course_code']
        widgets = {
            'course_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Introduction to AI'}),
            'course_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., CSC415'}),
        }
        
class SessionCreationForm(forms.Form):
    start_time = forms.DateTimeField(
        label="Session Start Time",
        widget=forms.DateTimeInput(
            attrs={
                'type': 'datetime-local',
                'class': 'form-control form-control-lg'
            }
        )
    )
    end_time = forms.DateTimeField(
        label="Session End Time",
        widget=forms.DateTimeInput(
            attrs={
                'type': 'datetime-local',
                'class': 'form-control form-control-lg'
            }
        )
    )

    def clean(self):
        
        cleaned_data = super().clean()
        start = cleaned_data.get("start_time")
        end = cleaned_data.get("end_time")

        if start and end:
            if end <= start:
                raise forms.ValidationError("The session end time must be after the start time.")
            if start < timezone.now() - datetime.timedelta(minutes=1):
                raise forms.ValidationError("The session start time cannot be in the past.")
        return cleaned_data