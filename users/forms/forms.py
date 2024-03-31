from .custom_fields import CharFieldRegexPhone, CharFieldRegexStrict, CharFieldTitleCaseRegexStrict, EmailFieldLowerRegexStrict
from django import forms

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

class RegisterForm(forms.Form):
    name_first = CharFieldTitleCaseRegexStrict(
        label='First name:', 
        max_length=25,
        widget=forms.TextInput(attrs={
            'autocomplete': 'off',
            'class': 'form-control',
            #'placeholder': 'Your first name',
            })
        )
    
    name_last = CharFieldTitleCaseRegexStrict(
        label='Last name:', 
        max_length=25,
        widget=forms.TextInput(attrs={
            'autocomplete': 'off',
            'class': 'form-control',
            #'placeholder': 'Your last name',
            })
        )

    username = CharFieldTitleCaseRegexStrict(
        label='Username:', 
        max_length=25,
        widget=forms.TextInput(attrs={
            'autocomplete': 'off',
            'class': 'form-control',
            #'placeholder': 'Your username',
            })
        ) 

    email = EmailFieldLowerRegexStrict(
        label='Email address:', 
        max_length=25,
        widget=forms.EmailInput(attrs={
            'autocomplete': 'off',
            'class': 'form-control',
            #'placeholder': 'Your email address',
            })
        )

    password = forms.CharField(
        label='Password:', 
        max_length=50,
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'off',
            'class': 'form-control',
            #'placeholder': 'Your password',
            })
        )

    password_confirmation = forms.CharField(
    label='Confirm Password:',
    max_length=50,
    widget=forms.PasswordInput(attrs={
        'autocomplete': 'off',
        'class': 'form-control',
        # 'placeholder': 'Confirm your password',
        })
    )

    cash_initial = DecimalField(
        label='Initial cash deposit:', 
        max_digits=10,
        decimal_places=2,
        initial=10000.00,
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'off',
            'class': 'form-control',
            #'placeholder': 'Your initial cash deposit (USD $XX.XX)',
            'step': '0.01',  # This allows input of decimal values
            })
        ) 

    accounting_method = forms.ChoiceField(
        label='Accounting method:',
        choices=[('FIFO', 'FIFO'), ('LIFO', 'LIFO')],
        initial='FIFO',
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
        })
    )

    tax_loss_offsets = forms.ChoiceField(
        label='Accounting method:',
        choices=[('On', 'On'), ('Off', 'Off')],
        initial='On',
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
        })
    )

    tax_rate_STCG = forms.DecimalField(
        label='Tax rate, short-term capital gains:',
        required=False,  # Makes the field optional
        initial=30.00,  # Default value
        min_value=0,  # Minimum value
        max_value=50,  # Maximum value
        decimal_places=2,  # Number of decimal places
        widget=forms.NumberInput(attrs={
            'step': 0.50,  # Step for the input
            'class': 'form-control',
        })
    )

    tax_rate_LTCG = forms.DecimalField(
        label='Tax rate, long-term capital gains:',
        required=False,  # Makes the field optional
        initial=15.00,  # Default value
        min_value=0,  # Minimum value
        max_value=50,  # Maximum value
        decimal_places=2,  # Number of decimal places
        widget=forms.NumberInput(attrs={
            'step': 0.50,  # Step for the input
            'class': 'form-control',
        })
    )

    def clean(self):
        cleaned_data = super().clean() # Use of super().clean() allows Django's built-in validation to happen first, and then the additional custom validation below is applied to that cleaned data.
        password = cleaned_data.get("password")
        password_confirmation = cleaned_data.get("password_confirmation")

        if password and password_confirmation and password != password_confirmation:
            self.add_error('password_confirmation', "Error: Password and Confirm Password do not match")

        return cleaned_data

#------------------------------------------------------------------------
