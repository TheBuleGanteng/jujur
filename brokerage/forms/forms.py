from .filters_validators import *
import decimal
from django import forms
from django.core.exceptions import ValidationError
from .filters_validators import *
from .generic_fields import *
#from ..models import UserProfile
__all__ = ['BuyForm', 'QuoteForm', 'SellForm']

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


#---------------------------------------------------------------------------------------

class QuoteForm(forms.Form):
    symbol=symbol

    def clean(self):
        cleaned_data = super().clean() # Use of super().clean() allows Django's built-in validation to happen first, and then the additional custom validation below is applied to that cleaned data.
        return cleaned_data


#---------------------------------------------------------------------------------------


class SellForm(forms.Form):
    
    transaction_type = forms.CharField(
        initial='SLD',
        widget=forms.HiddenInput()  # This makes the field a hidden type in HTML
    )    
    
    symbol = forms.ChoiceField(
    label='Symbol:',
    widget=forms.Select(attrs={
        'class': 'select-custom',
    })
)
    shares=shares

    def __init__(self, *args, **kwargs):
        symbols = kwargs.pop('symbols', [])  # Remove symbols from kwargs and provide a default empty list
        super(SellForm, self).__init__(*args, **kwargs)
        # Sort symbols alphabetically
        sorted_symbols = sorted(symbols, key=lambda x: x[1])  # Assuming symbols is a list of tuples (value, label)
        self.fields['symbol'].choices = sorted_symbols
        self.fields['shares'].required = True

    def clean(self):
        cleaned_data = super().clean() # Use of super().clean() allows Django's built-in validation to happen first, and then the additional custom validation below is applied to that cleaned data.
        return cleaned_data
