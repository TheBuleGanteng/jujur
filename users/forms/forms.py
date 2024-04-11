from .custom_fields import *
import decimal
from django import forms
from django.core.exceptions import ValidationError
from .form_fields import *
from ..models import UserProfile
__all__ = ['LoginForm', 'PasswordChangeForm', 'PasswordResetForm', 'PasswordResetConfirmationForm', 'ProfileForm', 'RegisterForm']

#------------------------------------------------------------------------

class LoginForm(forms.Form):
    email = EmailFieldLowerRegexStrict(
        label='Email address:', 
        max_length=100,
        widget=forms.EmailInput(attrs={
            'autocomplete': 'off',
            'class': 'form-control mx-auto w-auto',
            'placeholder': 'email address',
            })
        )

    password = forms.CharField(
        label='Password',
        strip=True,  # This acts like the strip_filter in Flask-WTF
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'off',
            'class': 'form-control mx-auto w-auto',
            'placeholder': 'password',
            })
        )

#------------------------------------------------------------------------

class PasswordChangeForm(forms.Form):
    
    email=email
    password_old=password_old
    password=password
    password_confirmation=password_confirmation
    
    def clean(self):
        cleaned_data = super().clean() # Use of super().clean() allows Django's built-in validation to happen first, and then the additional custom validation below is applied to that cleaned data.
        password_old = cleaned_data.get("password_old")
        password = cleaned_data.get('password')
        password_confirmation = cleaned_data.get('password_confirmation')

        if password and password_confirmation and password != password_confirmation:
            self.add_error('password_confirmation', 'Error: Password and Confirm Password do not match')

        if password_old and password and password_old == password:
            self.add_error('password', 'Error: New password must differ from current password')

        return cleaned_data

#-------------------------------------------------------------------------

class PasswordResetForm(forms.Form):
    
    email=email

    def clean(self):
        cleaned_data = super().clean() # Use of super().clean() allows Django's built-in validation to happen first, and then the additional custom validation below is applied to that cleaned data.
        return cleaned_data

#-------------------------------------------------------------------------

class PasswordResetConfirmationForm(forms.Form):

    password=password
    password_confirmation=password_confirmation

    def clean(self):
        cleaned_data = super().clean() # Use of super().clean() allows Django's built-in validation to happen first, and then the additional custom validation below is applied to that cleaned data.
        password = cleaned_data.get("password")
        password_confirmation = cleaned_data.get("password_confirmation")

        if password and password_confirmation and password != password_confirmation:
            self.add_error('password_confirmation', "Error: Password and Confirm Password do not match")

        return cleaned_data

#-------------------------------------------------------------------------

class ProfileForm(forms.ModelForm):
    first_name=first_name
    last_name=last_name
    #username_old=username_old
    username=username
    #email=email
    accounting_method=accounting_method
    tax_loss_offsets=tax_loss_offsets
    tax_rate_STCG=tax_rate_STCG
    tax_rate_LTCG=tax_rate_LTCG

    class Meta:
        model = UserProfile
        fields = ['first_name', 'last_name', 'username', 'accounting_method', 'tax_loss_offsets', 'tax_rate_STCG', 'tax_rate_LTCG']
        
#------------------------------------------------------------------------

class RegisterForm(forms.Form):
    first_name=first_name
    last_name=last_name
    username=username
    email=email
    password=password
    password_confirmation=password_confirmation
    cash_initial=cash_initial
    accounting_method=accounting_method
    tax_loss_offsets=tax_loss_offsets
    tax_rate_STCG=tax_rate_STCG
    tax_rate_LTCG=tax_rate_LTCG

    def __init__(self, *args, **kwargs):
        super(RegisterForm, self).__init__(*args, **kwargs)
        # Set required=True for all fields in this form
        for field_name in self.fields:
            self.fields[field_name].required = True

    def clean(self):
        cleaned_data = super().clean() # Use of super().clean() allows Django's built-in validation to happen first, and then the additional custom validation below is applied to that cleaned data.
        password = cleaned_data.get("password")
        password_confirmation = cleaned_data.get("password_confirmation")

        if password and password_confirmation and password != password_confirmation:
            self.add_error('password_confirmation', "Error: Password and Confirm Password do not match")

        return cleaned_data

#------------------------------------------------------------------------
