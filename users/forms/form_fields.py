from .custom_fields import *
import decimal
from django import forms
from django.core.exceptions import ValidationError
from ..models import UserProfile
__all__ = ['accounting_method', 'cash_initial', 'CustomDecimalField', 'email', 'first_name', 'last_name', 'password', 'password_confirmation', 'password_old', 'tax_loss_offsets', 'tax_rate_STCG', 'tax_rate_LTCG', 'USDTextInput', 'username', 'username_old']



class CustomDecimalField(forms.DecimalField):
    def to_python(self, value):
        try:
            # Attempt to convert comma-separated strings to Python decimal
            return decimal.Decimal(value.replace(',', ''))
        except decimal.InvalidOperation:
            raise ValidationError('Enter a valid number.')


class USDTextInput(forms.TextInput):
    def format_value(self, value):
        # Check if the value is a Decimal instance and format it
        if isinstance(value, decimal.Decimal):
            return f"${value:,.2f}"
        return value  # Return the original value if it's not a Decimal instance


accounting_method = forms.ChoiceField(
    label='Accounting method:',
    choices=[('FIFO', 'FIFO'), ('LIFO', 'LIFO')],
    initial='FIFO',
    required=False,
    widget=forms.Select(attrs={
        'class': 'select-custom',
    })
)

cash_initial = CustomDecimalField(
    label='Initial cash deposit:',
    max_digits=10,
    decimal_places=2,
    initial=decimal.Decimal("10000.00"),  # Use a Decimal for the initial value
    required=False,
    widget=USDTextInput(attrs={  # Use the custom widget
        'autocomplete': 'off',
        'class': 'form-control USD',
    })
)

email = EmailFieldLowerRegexStrict(
    label='Email address:', 
    max_length=100,
    widget=forms.EmailInput(attrs={
        'autocomplete': 'off',
        'class': 'form-control',
        #'placeholder': 'Your email address',
    })
)

first_name = CharFieldTitleCaseRegexStrict(
    label='First name:', 
    max_length=25,
    required=False,
    strip=True,
    widget=forms.TextInput(attrs={
        'autocomplete': 'off',
        'class': 'form-control',
        #'placeholder': 'Your first name',
    })
)
    
last_name = CharFieldTitleCaseRegexStrict(
    label='Last name:', 
    max_length=25,
    required=False,
    strip=True,
    widget=forms.TextInput(attrs={
        'autocomplete': 'off',
        'class': 'form-control',
        #'placeholder': 'Your last name',
    })
)

password = forms.CharField(
    label='Password:', 
    max_length=50,
    strip=True,
    widget=forms.PasswordInput(attrs={
        'autocomplete': 'off',
        'class': 'form-control',
        #'placeholder': 'Your password',
    })
)

password_confirmation = forms.CharField(
    label='Password:', 
    max_length=50,
    strip=True,
    widget=forms.PasswordInput(attrs={
        'autocomplete': 'off',
        'class': 'form-control',
        #'placeholder': 'Your password',
    })
)

password_old = forms.CharField(
    label='Current password:',
    max_length=50,
    strip=True,
    widget=forms.PasswordInput(attrs={
        'autocomplete': 'off',
        'class': 'form-control',
        #'placeholder': 'Your current password',
    })
)

tax_loss_offsets = forms.ChoiceField(
    label='Tax loss offsets:',
    choices=[('On', 'On'), ('Off', 'Off')],
    initial='On',
    required=False,
    widget=forms.Select(attrs={
        'class': 'select-custom',
    })
)

tax_rate_STCG = forms.DecimalField(
    label='Tax rate, short-term capital gains:',
    decimal_places=2,  # Number of decimal places
    initial=30.00,  # Default value
    min_value=0,  # Minimum value
    max_value=50,  # Maximum value
    required=False,  # Makes the field optional
    widget=forms.NumberInput(attrs={
        'type': 'range',  # Changes the input type to a range slider
        'step': 0.50,  # Step for the input
        'class': 'form-control-range w-75',  # Use Bootstrap's range input styling
        'min': 0,  # Minimum value
        'max': 50,  # Maximum value
    })
)

tax_rate_LTCG = forms.DecimalField(
    label='Tax rate, long-term capital gains:',
    initial=15.00,  # Default value
    min_value=0,  # Minimum value
    max_value=50,  # Maximum value
    decimal_places=2,  # Number of decimal places
    required=False,  # Makes the field optional
    widget=forms.NumberInput(attrs={
        'type': 'range',  # Changes the input type to a range slider
        'step': 0.50,  # Step for the input
        'class': 'form-control-range w-75',  # Use Bootstrap's range input styling
        'min': 0,  # Minimum value
        'max': 50,  # Maximum value
    })
)

username = CharFieldRegexStrict(
    label='Username:', 
    max_length=25,
    required=False,  # Makes the field optional
    strip=True,
    widget=forms.TextInput(attrs={
        'autocomplete': 'off',
        'class': 'form-control',
        #'placeholder': 'Your username',
        })
    )


username_old = CharFieldRegexStrict(
    label='Username:', 
    max_length=25,
    required=False,  # Makes the field optional
    strip=True,
    widget=forms.TextInput(attrs={
        'autocomplete': 'off',
        'class': 'form-control',
        #'placeholder': 'Your username',
        })
    )

