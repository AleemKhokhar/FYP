from django import forms
from django.contrib.auth import get_user_model
from .models import Profile

User = get_user_model()

class AccountUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email'] 
        
    def __init__(self, *args, **kwargs):
        super(AccountUpdateForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['avatar', 'bio']