from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import Project, Prompt, User


class RegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "password1", "password2")
        widgets = {"email": forms.EmailInput(attrs={"autocomplete": "email"})}


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}))


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ("name", "description", "system_prompt")
        widgets = {"description": forms.Textarea(attrs={"rows": 3}), "system_prompt": forms.Textarea(attrs={"rows": 5})}


class PromptForm(forms.ModelForm):
    class Meta:
        model = Prompt
        fields = ("title", "content")
        widgets = {"content": forms.Textarea(attrs={"rows": 5})}
