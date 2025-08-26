from django import forms
from .models import Course

class LoginForm(forms.Form):
  
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "name@example.com"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"})
    )


class RegistrationForm(forms.Form):
    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'First Name', 'class': 'form-control'}))
    last_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'Last Name', 'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Email Address', 'class': 'form-control'}))
    matric_number = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'Matriculation Number', 'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'class': 'form-control'}))
    
class LecturerRegistrationForm(forms.Form):

    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'First Name', 'class': 'form-control'}))
    last_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'Last Name', 'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Official Email Address', 'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'class': 'form-control'}))
    
    
class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['course_name', 'course_code']
        widgets = {
            'course_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Introduction to Computer Science'}),
            'course_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., CMP 101'}),
        }