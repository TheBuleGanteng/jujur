from django import forms
from django.core.exceptions import ValidationError
from phonenumber_field.formfields import PhoneNumberField
from phonenumber_field.phonenumber import to_python
import re


# Custom validator 1: Ensure user input does not contain prohibited chars. 
allowed_input_letters_lower = 'a-z'
allowed_input_letters_upper = 'A-Z'
allowed_input_numbers = '0-9'
allowed_input_symbols_strict = '-.@_ :'
allowed_input_symbols_phone = '+-. ()+ext'

def regex_strict(user_input, allowed_input_letters_lower, allowed_input_letters_upper, allowed_input_numbers, allowed_input_symbols_strict ):
    # Step 1: Define regex
    # Escape the symbols for safe inclusion in regex pattern
    allowed_input_symbols_escaped = re.escape(allowed_input_symbols_strict)
    allowed_input_all = ''.join([allowed_input_letters_lower, 
                                    allowed_input_letters_upper,
                                    allowed_input_numbers, 
                                    allowed_input_symbols_escaped])
    # Regular expression pattern to match the entire string
    allowed_chars_check_pattern = r'^[' + allowed_input_all + r']+$'

    # Step 2: Check if user_input matches regex returns True if no prohibited chars.
    if not re.match(allowed_chars_check_pattern, str(user_input)):
        print(f'running allowed_chars_validator...  failed for input: {user_input}')
        raise ValidationError(f'Error: Allowed characters include: { allowed_input_letters_lower}, { allowed_input_letters_upper}, { allowed_input_numbers}, and { allowed_input_symbols_strict }')
    print(f'running allowed_chars_validator...  passed for input: {user_input}')



def regex_phone(user_input, allowed_input_letters_lower, allowed_input_letters_upper, allowed_input_numbers, allowed_input_symbols_phone):
    # Step 1: Define regex
    # Escape the symbols for safe inclusion in regex pattern
    allowed_input_symbols_escaped = re.escape(allowed_input_symbols_phone)
    allowed_input_all = ''.join([allowed_input_numbers, 
                                    allowed_input_symbols_escaped])
    # Regular expression pattern to match the entire string
    allowed_chars_check_pattern = r'^[' + allowed_input_all + r']+$'

    # Step 2: Check if user_input matches regex returns True if no prohibited chars.
    if not re.match(allowed_chars_check_pattern, str(user_input)):
        print(f'running allowed_chars_validator...  failed for input: {user_input}')
        raise ValidationError(f'Error: Allowed characters include: { allowed_input_numbers}, and { allowed_input_symbols_phone }')
    print(f'running allowed_chars_validator...  passed for input: {user_input}')

#-----------------------------------------------------------------------------

# EmailField plus:
# - forces user input to lowercase
# - trims input
class EmailFieldLowerRegexStrict(forms.EmailField):
    def clean(self, user_input):
        user_input = super().clean(user_input)  # Perform the standard cleaning and validation first
        user_input = user_input.lower().strip()
        regex_strict(user_input, allowed_input_letters_lower, allowed_input_letters_upper, 
        allowed_input_numbers, allowed_input_symbols_strict)
        return user_input

#-----------------------------------------------------------------------------

# CharField: plus
# - trims input
# - Strict regex
class CharFieldRegexStrict(forms.CharField):
    def clean(self, user_input):
        user_input = super().clean(user_input)  # Perform the standard cleaning and validation first
        user_input = user_input.strip()
        regex_strict(user_input, allowed_input_letters_lower, allowed_input_letters_upper, 
        allowed_input_numbers, allowed_input_symbols_strict)
        return user_input

#-----------------------------------------------------------------------------

# CharField: plus
# - trims input
# - TitleCases input
# - Strict regex
class CharFieldTitleCaseRegexStrict(forms.CharField):
    def clean(self, user_input):
        user_input = super().clean(user_input)  # Perform the standard cleaning and validation first
        user_input = user_input.title().strip()
        regex_strict(user_input, allowed_input_letters_lower, allowed_input_letters_upper, 
        allowed_input_numbers, allowed_input_symbols_strict)
        return user_input

#-----------------------------------------------------------------------------

# CharField: plus
# - trims input
# - TitleCases input
class CharFieldRegexPhone(PhoneNumberField):
    def clean(self, value):
        phone_number = to_python(value)
        if phone_number and not phone_number.is_valid():
            raise forms.ValidationError('Error: Please enter a valid phone number.')
        
        phone_number_str = str(phone_number.national_number)
        regex_phone(phone_number_str, allowed_input_letters_lower, allowed_input_letters_upper, 
        allowed_input_numbers, allowed_input_symbols_phone)
        return super().clean(value)
        