from .filters_validators import *
import decimal
from django import forms
from django.core.exceptions import ValidationError
from .filters_validators import *
from .generic_fields import *
#from ..models import UserProfile
__all__ = ['BuyForm']

#------------------------------------------------------------------------

class BuyForm(forms.Form):
    
    transaction_type = forms.CharField(
        initial='BOT',
        widget=forms.HiddenInput()  # This makes the field a hidden type in HTML
    )    
    symbol=symbol
    shares=shares

    def __init__(self, *args, **kwargs):
        super(BuyForm, self).__init__(*args, **kwargs)
        self.fields['symbol'].required = True
        self.fields['shares'].required = True

    def clean(self):
        cleaned_data = super().clean() # Use of super().clean() allows Django's built-in validation to happen first, and then the additional custom validation below is applied to that cleaned data.
        return cleaned_data


