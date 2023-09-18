from django import forms
from .models import userprofile


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = userprofile
        fields = ['fname', 'lname','is_issuer','group']

    username = forms.CharField(max_length=100)
    password = forms.CharField(max_length=100, widget=forms.PasswordInput)

