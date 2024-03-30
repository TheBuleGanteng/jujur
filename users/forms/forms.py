from .custom_fields import CharFieldRegexPhone, CharFieldRegexStrict, CharFieldTitleCaseRegexStrict, EmailFieldLowerRegexStrict
from django import forms


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



"""
class ContactForm(forms.Form):
    name = CharFieldTitleCaseRegexStrict(
        label='Name:',
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'Your name here', 
        'class': 'form-control', 
        'autofocus': 'autofocus'}))

    email = EmailFieldLowerRegexStrict(
        label='Email address:', 
        max_length=100,
        widget=forms.EmailInput(attrs={'placeholder': 'emailaddress@example.com',
        'class': 'form-control'}))
    
    phone = CharFieldRegexPhone(
        label='WhatsApp number:',
        widget=PhoneNumberPrefixWidget(attrs={'class': 'form-control'}, initial='ID'))

    
    body = CharFieldRegexStrict(
        label='Message:', 
        max_length= 2000,
        min_length= 5,
        widget=forms.Textarea(attrs={'rows': 3, 
        'placeholder': 'A hot dog is absolutely a sandwich. Convince me otherwise.',
        'class': 'form-control'}))
    """