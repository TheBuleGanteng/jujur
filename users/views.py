# Provides ability to authenticate username+pw, log a user in, log a user out.
import base64
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.views.decorators.http import require_http_methods
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .forms import *
from google.oauth2 import service_account
from googleapiclient.discovery import build
from .models import UserProfile
import logging
import os
import re
import traceback
from urllib.parse import unquote
logger = logging.getLogger('django')

#-------------------------------------------------------------------------------

# Helper functions to be externalized

# Validates password strength, subject to the requirements listed below. 
pw_req_length = 4
pw_req_letter = 2
pw_req_num = 2
pw_req_symbol = 0
def check_password_strength(user_input):
    if (
        len(user_input) >= pw_req_length and 
        len(re.findall(r'[a-zA-Z]', user_input)) >= pw_req_letter and 
        len(re.findall(r'[0-9]', user_input)) >= pw_req_num and
        len(re.findall(r'[^a-zA-Z0-9]', user_input)) >= pw_req_symbol
        ):
        return True

# Get email addresses from .env
EMAIL_ADDRESS_PERSONAL= os.getenv('EMAIL_ADDRESS_PERSONAL') 
EMAIL_ADDRESS_INFO = os.getenv('EMAIL_ADDRESS_INFO')
EMAIL_ADDRESS_DNR = os.getenv('EMAIL_ADDRESS_DNR')



# Custom jinja filter: $x.xx or ($x.xx)
def filter_usd(value):
    """Format value as USD."""
    if value >= 0:
        return f"${value:,.2f}"
    else:
        return f"(${-value:,.2f})"


# Generates confirmation url that, when clicked, runs the 
def generate_confirmation_url(route, token, user):
    logger.debug(f'running users app, generate_confirmation_url(user, token) ... function started')
    
    # Encode the user's email with base64 to safely include it in the URL
    encoded_email = urlsafe_base64_encode(force_bytes(user.email))

    # This gives you the relative URL path, assuming your URL pattern expects a 'token' parameter
    relative_url = reverse(f'users:{route}')
    
    # Append the token and the encoded email as query parameters
    url_with_query_params = f"{relative_url}?token={token}&email={encoded_email}"

    # The value for MY_SITE_DOMAIN (e.g., 'www.example.com' or 'localhost:800') is defined in configs_project and then imported into settings.py
    domain = settings.MY_SITE_DOMAIN
    logger.debug(f'running users app, generate_confirmation_url(token) ... domain is: {domain}')

    # Decide the protocol based on your setup; use 'https' if your site is served over SSL/TLS
    #protocol = 'https'
    #logger.debug(f'running users app, generate_confirmation_url(token) ... protocol is: {protocol}')

    # Construct the full URL
    url = f'{domain}{url_with_query_params}'
    #url = f"{protocol}://{domain}{url_with_query_params}"
    return url

    
# Generates a nonce to work with Talisman-managed CSP
def generate_nonce():
    logger.debug('running users app, generate_nonce() ... generated nonce')
    return os.urandom(16).hex()


# Token generation for password reset and registration
def generate_unique_token(user):
    logger.debug(f'running generate_unique_token(user_id)... starting')
    
    # Note that tokens generated via PasswordResetTokenGenerator() are one-time use by default
    token_generator = PasswordResetTokenGenerator()
    token = token_generator.make_token(user)
    
    logger.debug(f'running generate_unique_token(user)... generated token')
    return token


# Get PROJECT_NAME from .env
PROJECT_NAME = os.getenv("PROJECT_NAME") 
logger.debug(f'PROJECT_NAME is: { PROJECT_NAME }')


# Queries the DB to check if user_input matches a registered email. Returns None if no match.
def retrieve_email(user_input):
    logger.debug(f'running retrieve_email(user_input) ... function started')
    user = User.objects.filter(email__iexact=user_input).first()
    logger.debug(f'running retrieve_email(user_input) ... returned user: { user }')
    return user


# Queries the DB to check if user_input matches a registered email
def retrieve_username(user_input):
    logger.debug(f'running retrieve_username(user_input) ... function started')
    return User.objects.filter(username__iexact=user_input).first()


# Send emails
def send_email(body, recipient, sender, subject):    
    logger.debug(f'running retrieve_username(user_input) ... function started')
    logger.debug(f'running retrieve_username(user_input) ... body is: { body }')
    logger.debug(f'running retrieve_username(user_input) ... recipient is: { recipient }')
    
    try:
        # Absolute path to the service account file
        SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), '..', 'gitignored', 'gmail_access_credentials.json')

        # Define the required scope for sending emails
        SCOPES = ['https://www.googleapis.com/auth/gmail.send']

        # Use the service account to acquire credentials
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)

        # Specify the user to impersonate
        user_to_impersonate = 'matt@mattmcdonnell.net'
        logger.debug(f'running retrieve_username(user_input) ... user_to_impersonate is: { user_to_impersonate }')

        # Impersonate the user
        credentials = credentials.with_subject(user_to_impersonate)

        # Build the Gmail service
        service = build('gmail', 'v1', credentials=credentials)

        # Create a simple MIMEText email
        email_msg = MIMEText(body)
        email_msg['to'] = recipient  # Replace with the recipient's email address
        email_msg['from'] = sender
        email_msg['subject'] = subject

        # Encode the email message in base64
        encoded_message = base64.urlsafe_b64encode(email_msg.as_bytes()).decode()

        # Create the message body
        message_body = {'raw': encoded_message}

        # Send the email
        message = service.users().messages().send(userId='me', body=message_body).execute()
        print(f"Message Id: {message['id']}")

    except Exception as e:
        print(f"An error occurred: {e}")
        raise


# Token validation for password reset and registration
def verify_unique_token(token, user_id):
    logger.debug(f'running verify_unique_token(token, user_id) ... function starting')
    
    try:
        # Initialize the token generator
        token_generator = PasswordResetTokenGenerator()
        
        # Retrieve the user based on the provided user_id
        user = User.objects.get(pk=user_id)

        # Use the token generator to check if the token is valid for the given user
        if token_generator.check_token(user, token):
            logger.debug('Token is valid')
            return user
        else:
            logger.debug('Token is invalid or has expired')
            return None
    except User.DoesNotExist:
        logger.debug('User does not exist')
        return None
    except Exception as e:
        logger.error(f'Error during token verification: {e}')
        return None


#-------------------------------------------------------------------------------

# Returns the email if registered or otherwise, None
# Used with jsEmailValidation()
@require_http_methods(['POST'])
def check_email_registered_view(request):
    logger.debug('running users app, check_email_registered_view(request) ... view started')

    email = request.POST.get('user_input', None)
    if email:
        user = retrieve_email(email)
        # If a user object is found, return the email in the JsonResponse
        if user:
            return JsonResponse({'email': user.email})
        else:
            # If no user is found, return a response indicating the email is not taken
            return JsonResponse({'email': None})
    else:
        # If no email was provided in the request, return an error response
        return JsonResponse({'error': 'No email provided'}, status=400)

#--------------------------------------------------------------------------------

# Returns '{'result': True}' if user_input meets password requirements and '{'result': False}' if not.
@require_http_methods(["POST"])
def check_password_strength_view(request):
    logger.debug('running users app, check_password_strength_view(request) ... view started')

    password = request.POST.get('user_input', None)
    if password:
        result = check_password_strength(password)
        return JsonResponse({'result': result})
    else:
        # If no email was provided in the request, return an error response
        return JsonResponse({'error': 'No password provided'}, status=400)

#--------------------------------------------------------------------------------

# Checks if password passes custom strength requirements
# Used with jsPasswordValidation()
@require_http_methods(["POST"])
def check_password_valid_view(request):
    logger.debug('running users app, check_password_valid_view(request) ... view started')

    # Step 1: Pull in data passed in by JavaScript
    password = request.POST.get('password')
    password_confirmation = request.POST.get('password_confirmation')

    # Step 2: Initialize checks_passed array
    checks_passed = []
    logger.debug(f'running users app, check_password_valid_view(request) ... initialized checks_passed array ')    
    
    # Step 3: Start performing checks, adding the name of each check passed to the checks_passed array.
    if len(password) >= pw_req_length:
            checks_passed.append('pw_reg_length')
            logger.debug(f'running users app, check_password_valid_view(request) ... appended pw_reg_length to checks_passed array. Length of array is: { len(checks_passed) }.')
    if len(re.findall(r'[a-zA-Z]', password)) >= pw_req_letter:
            checks_passed.append('pw_req_letter')
            logger.debug(f'running users app, check_password_valid_view(request) ... appended pw_req_letter to checks_passed array. Length of array is: { len(checks_passed) }. ')
    if len(re.findall(r'[0-9]', password)) >= pw_req_num:
            checks_passed.append('pw_req_num')
            logger.debug(f'running users app, check_password_valid_view(request) ... appended pw_req_num to checks_passed array. Length of array is: { len(checks_passed) }. ')
    if len(re.findall(r'[^a-zA-Z0-9]', password)) >= pw_req_symbol:
            checks_passed.append('pw_req_symbol')
            logger.debug(f'running users app, check_password_valid_view(request) ... appended pw_req_symbol to checks_passed array. Length of array is: { len(checks_passed) }. ')
    logger.debug(f'running users app, check_password_valid_view(request) ... checks_passed array contains: { checks_passed }. Length of array is: { len(checks_passed) }.')

    # Step 4: Ensure password and confirmation match
    if password == password_confirmation:
        confirmation_match = True
    else:
        confirmation_match = False
    logger.debug(f'running users app, check_password_valid_view(request) ... confirmation_match is: { confirmation_match }')

    # Step 5: Pass the checks_passed array and confirmation_match back to JavaScript
    logger.debug(f'running users app, check_password_valid_view(request) ... check finished, passing data back to JavaScript')
    return JsonResponse({'checks_passed': checks_passed, 'confirmation_match': confirmation_match} )

#--------------------------------------------------------------------------------

# Returns the username if registered or otherwise, None
# Used with jsUsernameValidation()
@require_http_methods(["POST"])
def check_username_registered_view(request):
    username = request.POST.get('user_input', None)
    if username:
        user = retrieve_username(username)
        # If a user object is found, return the username in the JsonResponse
        if user:
            return JsonResponse({'username': user.username})
        else:
            # If no user is found, return a response indicating the username is not taken
            return JsonResponse({'username': None})
    else:
        # If no username was provided in the request, return an error response
        return JsonResponse({'error': 'No username provided'}, status=400)

#--------------------------------------------------------------------------------

@require_http_methods(["GET", "POST"])
def login_view(request):
    logger.debug(f'running users app, login_view ... view started')

    nonce = generate_nonce()
    logger.debug(f'running users app, login_view ... generated nonce of: { nonce }')

    # Instantiate the form with request.POST or no data depending on the request type
    form = LoginForm(request.POST or None)

    if request.method == "POST":
        logger.debug('running users app, login_view ... user submitted via POST')
        
        form = LoginForm(request.POST)

        # Do the following if submission=POST && submission passes validation...
        if form.is_valid():
            logger.debug('running users app, login_view ... user submitted via POST and form passed validation')
        
            # Assigns to variables the username and password passed in via the form in login.html
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            logger.debug(f'running users app, login_view ... email is: { email }')
            logger.debug(f'running users app, login_view ... password is: { password }')
        
            # Runs the authenticate function on username and password and saves the result as the variable "user"
            user = authenticate(request, username=email, password=password)
            logger.debug(f'running users app, login_view ... retrieved user object: { user }')

            # If user is registered and confirmed, display a message and redirect to index.
            if user and user.userprofile.confirmed == True:
                logger.debug('running users app login_view ... user found in DB and is confirmed. Showing success message and redirecting to index.')
                
                login(request, user)
                logger.debug('running users app login_view ... user logged in, reversing to index')
                messages.success(request, f'Welcome { user.get_username() }, you are now logged in to { PROJECT_NAME }.')
                return HttpResponseRedirect(reverse('brokerage:index'))
        
            # If user is registered and not yet confirmed, display a message and redirect to login.
            elif user and user.userprofile.confirmed == False:
                logger.debug('running users app login_view ... user found in DB and is not confirmed. Showing error message and redirecting to login.')
                
                messages.error(request, f'You must confirm your account before logging in. Please check your email inbox and spam folders to an email from { PROJECT_NAME } or re-register your account.')
                return render(request, 'users/login.html', {'form': form})

            # If user is not registered, display a message and redirect to login.
            else:
                logger.debug('running users app login_view ... user not found in DB')
                messages.error(request, f'Error: Invalid credentials. Please check your entries for email and password. If you have not yet registered for { PROJECT_NAME }, please do so via the link below.')
                return render(request, 'users/login.html', {'form': form})

        # Do the following if submission=POST && submission fails validation...
        else:
            logger.debug('running users app, login_view ... user submitted via POST and form failed validation')
            messages.error(request, 'Error: Invalid input. Please see the red text below for assistance.')
            return render(request, 'users/login.html', {'form': form})

    # If arrived via GET, display the login form.
    else:
        logger.debug('running users app login_view ... user arrived via GET')
        form = LoginForm()
        
    return render(request, 'users/login.html', {'form': form})

#--------------------------------------------------------------------------------

@require_http_methods(['GET', 'POST'])
@login_required(login_url='users:login')
def logout_view(request):
    logger.debug('running users app, logout_view ... view started')

    user = request.user
    cache_key = f'portfolio_{user.pk}'
    cache.delete(cache_key)  # Clear cache for this user

    # logout is a function built into django.
    logout(request)

    # Tee up the login form
    form = LoginForm

    # After user is logged out, he is redirected to the login page with the message "Logged out.".
    logger.debug('running users app, logout_view ... user is logged out and is being redirected to login.html')
    messages.info(request, f'You have been logged out of { PROJECT_NAME }')
    return render(request, "users/login.html", {
        "form": form  # Pass the form instance to the template.
    })

#---------------------------------------------------------------------------

@login_required(login_url='users:login')
@require_http_methods(["GET", "POST"])
def password_change_view(request):
    logger.debug('running users app, password_change_view ... view started')

    # Instantiate the form with request.POST or no data depending on the request type
    form = PasswordChangeForm(request.POST or None)
    
    # Since the form is rendered several times, defining context here for brevity
    context = {
        "form": form,
        "pw_req_length": pw_req_length,
        "pw_req_letter": pw_req_letter,
        "pw_req_num": pw_req_num,
        "pw_req_symbol": pw_req_symbol,
    }

    if request.method == "POST":
        logger.debug('running users app, password_change_view ... user submitted via POST')

        # Do the following if submission=POST && submission passes validation...
        if form.is_valid():
            logger.debug('running users app, password_change_view ... user submitted via POST and form passed validation')
        
            try:
                # Assigns to variables the username and password passed in via the form
                email = form.cleaned_data['email']
                password_old = form.cleaned_data['password_old']
                password = form.cleaned_data['password']
                password_confirmation = form.cleaned_data['password_confirmation']
                
                logger.debug(f'running users app, password_change_view ... user-submitted email address is: { email }')
                
            # If pulling in data from the form fails, flash error message and return to password_change
            except Exception as e:
                logger.error(f'running users app, password_change_view ... could not pull in data from form: {e}. Flashing error msg and rendering password_change.html ')
                messages.error(request, 'Error: Please ensure all fields are completed.')
                return render(request, "users/password_change.html", context)

            try:                
                # Check if the email+password_old pair submitted are legit.
                user = authenticate(username=email, password=password_old)
                
                if not user:
                    messages.error(request, "Error: The old password is incorrect.")
                    return render(request, "users/password_change.html", context)

                # Ensure password (a) differs from password_old and (b) matches password_confirmation
                if password_old == password or password != password_confirmation:
                    logger.error(f'running users app, password_change_view ... user did not submit a valid new password or new password does not match confirmation. Flashing error msg. and rendering password_change.html')
                    messages.error(request, 'Error: New password must differ from existing password and must match password confirmation.')
                    return render(request, "users/password_change.html", context)

                user.set_password(password)
                user.save()
                logger.debug(f'running users app, password_change_view ... user submitted valid password, email_old, email, and email_confirmation. Flashing success msg. and redirecting')
                messages.success(request, 'You have successfully updated your password.')
                return redirect('users:login')

            except Exception as e:
                logger.debug(f'running users app, password_change_view ... unable to run authenticate on email+password_old with error: { e }. Flashing error msg. and rendering password_change.html')
                messages.error(request, 'Error: Please check your inputs and try again.')
        # If form did not pass validation, throw error and render password_change
        else:
            logger.debug(f'running users app, password_change_view ... Error: form validation errors. flashing message and redirecting user to /register')    
            for field, errors in form.errors.items():
                logger.debug(f'running users app, password_change_view ... erroring field is: { field }')
                for error in errors:
                    logger.debug(f'running users app, password_change_view ... erroring on this field is: {error}')
            messages.error(request, 'Error: Invalid input. Please see the red text below for assistance.')
            return render(request, "users/password_change.html", context)

    # User arrived via GET
    else:
        logger.debug(f'running users app, password_change_view ... user arrived via GET')
        return render(request, "users/password_change.html", context)

#---------------------------------------------------------------------------

@require_http_methods(["GET", "POST"])
def password_reset_view(request):
    logger.debug('running users app, password_reset_view ... view started')

    # Instantiate the form with request.POST or no data depending on the request type
    form = PasswordResetForm(request.POST or None)

    if request.method == "POST":
        logger.debug('running users app, password_reset_view ... user submitted via POST')

        # Do the following if submission=POST && submission passes validation...
        if form.is_valid():
            logger.debug('running users app, password_reset_view ... user submitted via POST and form passed validation')
        
            # Try to pull in the data submitted via the form
            try:
                # Assigns to variables the username and password passed in via the form
                email = form.cleaned_data['email']
                logger.debug(f'running users app, password_reset_view ... user-submitted email address is: { email }')
                
            # If pulling in data from the form fails, flash error message and return to password_reset
            except Exception as e:
                logger.error(f'running users app, password_reset_view ... could not pull in data from form: {e}. Flashing error msg and rendering password_change.html ')
                messages.error(request, 'Error: Please ensure all fields are completed.')
                return render(request, 'users/password_reset.html', {'form':form})
            
            # Try to find the user corresponding to the email address submitted via the form
            try:
                # Queries the DB to check if the user-entered value is in the DB
                user = User.objects.filter(email=email).first()

                # If the user is found and is confirmed, compose and sent the email with a token
                if user and user.userprofile.confirmed == True:
                    # Generate token
                    token = generate_unique_token(user)
                    logger.debug(f'running users app, password_reset_view ... token generated')
                
                    # Formulate email
                    TOKEN_TIMEOUT_minutes = int(int(os.getenv('TOKEN_TIMEOUT'))/60)
                    username = user.username
                    sender = EMAIL_ADDRESS_INFO
                    recipient = user.email
                    subject = f'Reset your { PROJECT_NAME } password'
                    url = generate_confirmation_url(route='password_reset_confirmation', token=token, user=user)
                    body = f'''Dear { user.username }: to reset your { PROJECT_NAME } password, please visit the following link within the next { TOKEN_TIMEOUT_minutes } minutes:
                    
{ url }

If you did not make this request, you may ignore it.

Thank you,
Team {PROJECT_NAME}'''


                    # Send email.
                    send_email(body=body, recipient=recipient, sender=sender, subject=subject)
                    logger.debug(f'running users app, password_reset_view ... user found and reset email sent to email address: { user.email }.')
                    messages.success(request, 'Please check your email inbox and spam folders for an email containing your password reset link.')
                    return redirect('users:login')
                
                # If no user matching the user-supplied email is found, fake send an email
                else:
                    logger.debug(f'running users app, password_reset_view ... user not found and email not sent. Flashing fake confirmation message and redirecting to login.')
                    messages.success(request, 'Please check your email inbox and spam folders for an email containing your password reset link.')
                    return redirect('users:login')
            
            # Handle if DB query on user-supplied email fails 
            except Exception as e:
                logger.error(f'running users app, password_reset_view ... could not pull in data from form: {e}. Flashing error msg and rendering password_reset.html ')
                messages.error(request, 'Error: Please ensure all fields are completed.')
                return render(request, "users/password-reset.html", {'form': form})
        
        # Handle submission via post + user input fails form validation
        else:
            logger.debug(f'running users app, password_reset_view ... Error: form validation errors, flashing message and redirecting user to /password_reset')    
            for field, errors in form.errors.items():
                logger.debug(f'running users app, register_view ... erroring field is: { field }')
                for error in errors:
                    logger.debug(f'running users app, register_view ... erroring on this field is: {error}')
            messages.error(request, 'Error: Invalid input. Please see the red text below for assistance.')
            return render(request, "users/password-reset.html", {'form': form})
            
    # Step 3: User arrived via GET
    else:
        logger.debug(f'running users app, password_reset_view ... user arrived via GET')
        return render(request, "users/password-reset.html", {'form': form})

#---------------------------------------------------------------------------

@require_http_methods(["GET", "POST"])
def password_reset_confirmation_view(request):
    logger.debug('running users app, password_reset_confirmation_view ... view started')
        
    # Extract 'token' and 'email' from the request
    token = request.GET.get('token') or request.POST.get('token')
    encoded_email = request.GET.get('email') or request.POST.get('email')
    
    # Initialize context
    context = {
        'form': PasswordResetConfirmationForm(),
        'token': token,
        'email': encoded_email,
        'pw_req_length': pw_req_length,
        'pw_req_letter': pw_req_letter,
        'pw_req_num': pw_req_num,
        'pw_req_symbol': pw_req_symbol,
    }
    logger.debug('running users app, password_reset_confirmation_view ... context initialized.')

    # Check for presence of encoded_email and token in the url
    if not encoded_email or not token:
        logger.error(f'running users app, password_reset_confirmation_view ... Error: url is missing encoded_email and/or token.')
        messages.error(request, 'Error: Your token is invalid or expired. Please log in or request a new password reset email.')
        return redirect('users:login')

    # Try to decode the email in the url and find the associated user
    try:
        email = force_str(urlsafe_base64_decode(encoded_email))
        user = User.objects.get(email=email)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    # Handle ff no user found or token is invalid
    if not user or not PasswordResetTokenGenerator().check_token(user, token):
        logger.error(f'running users app, password_reset_confirmation_view ... Error: no user found or token is invalid.')
        messages.error(request, 'Invalid or expired token. Please log in or request a new password reset email.')
        return redirect('users:login')

    if request.method == "POST":
        logger.debug('running users app, password_reset_confirmation_view ... user submitted via POST')
        
        form = PasswordResetConfirmationForm(request.POST)
        
        if form.is_valid():
            logger.debug('running users app, password_reset_confirmation_view ... user submitted via POST + form passed validation')

            password = form.cleaned_data['password']
            
            if not user.check_password(password):
                user.set_password(password)
                user.save()
                logger.debug(f'running users app, password_reset_confirmation_view ... successfully reset password for user: { user }')
                messages.success(request, 'Your password has been reset successfully.')
                return redirect('users:login')
            else:
                logger.debug(f'running users app, password_reset_confirmation_view ... failed to reset password for user: { user }')
                messages.error(request, 'New password must differ from the existing password. Please try again.')

    return render(request, 'users/password-reset-confirmation.html', context)

#---------------------------------------------------------------------------

@require_http_methods(['GET', 'POST'])
@login_required(login_url='users:login')
def profile_view(request):
    logger.debug('running users app, profile_view ... view started')

    # Instantiate the form with request.POST or no data depending on the request type
    user = request.user
    user_profile, created = UserProfile.objects.get_or_create(user=user)

    form = ProfileForm(instance=user_profile)
    context = {
        'form': form,
        'full_name': f'{user.first_name} {user.last_name}',
    }

    if request.method == 'POST':
        logger.debug('running users app, profile_view ... user submitted via POST')

        form = ProfileForm(request.POST, instance=user_profile)
        context['form'] = form  # Update context with the bound form

        # Do the following if submission=POST && submission passes validation...
        if form.is_valid():
            logger.debug('running users app, profile_view ... user submitted via POST and form passed validation')
        
            try:
                # Secondary validation to ensure user does not change username to one that is already registered
                username = form.cleaned_data['username']
                if user.username != username and retrieve_username(username):
                    logger.error(f'running users app, profile_view ... user entered an already-registered username. Flashing error msg and rendering register.html ')
                    messages.error(request, 'Error: username is already registered.')
                    return render(request, 'users/profile.html', context)
                
                # Assemble the user object fields into a list and the profile object fields into a list.
                user_fields = ['first_name', 'last_name', 'username']
                profile_fields = ['accounting_method', 'tax_loss_offsets', 'tax_rate_STCG', 'tax_rate_LTCG']

                # Update User fields if there's new data
                for field in user_fields:
                    if form.cleaned_data.get(field) is not (None or ''):
                        setattr(user, field, form.cleaned_data[field])
                user.save()  # Save changes to the User model

                # Update UserProfile fields if there's new data
                for field in profile_fields:
                    if form.cleaned_data.get(field) is not None or (''):
                        setattr(user_profile, field, form.cleaned_data[field])
                user_profile.save()  # Save changes to the UserProfile model
                            
                # Save the updated user profile and complete update process
                logger.debug(f'running users app, profile_view ... successfully pulled in all data from RegistrationForm')
                messages.success(request, 'You have successfully updated your profile.')
                return redirect('brokerage:index')

            # If pulling in data from the form fails, flash error message and return to register
            except Exception as e:
                logger.error(f'running users app, profile_view ... could not pull in data from form: {e}. Flashing error msg and rendering register.html ')
                messages.error(request, 'Error: Unable to update your selections. Please ensure you have inputted data correctly, including a username that is not already taken, and try again.')
                return render(request, "users/profile.html", context)

        # Handle submission via post + user input fails form validation
        else:
            logger.debug(f'running users app, profile_view ... Error 2.2 (form validation errors), flashing message and redirecting user to /profile')    
            for field, errors in form.errors.items():
                logger.debug(f'running users app, profile_view ... erroring field is: { field }')
                for error in errors:
                    logger.debug(f'running users app, profile_view ... erroring on this field is: {error}')
            messages.error(request, 'Error: Invalid input. Please see the red text below for assistance.')
            return render(request, "users/profile.html", context)
            
    # Step 3: User arrived via GET
    else:
        logger.debug(f'running users app, profile_view ... user arrived via GET')
        return render(request, "users/profile.html", context)


#---------------------------------------------------------------------------

@require_http_methods(["GET", "POST"])
def register_view(request):
    logger.debug('running users app, register_view ... view started')

    # Instantiate the form with request.POST or no data depending on the request type
    form = RegisterForm(request.POST or None)
    
    # Since the form is registered several times, defining context here for brevity
    context = {
        "form": form,
        "pw_req_length": pw_req_length,
        "pw_req_letter": pw_req_letter,
        "pw_req_num": pw_req_num,
        "pw_req_symbol": pw_req_symbol,
    }

    if request.method == "POST":
        logger.debug('running users app, register_view ... user submitted via POST')

        # Do the following if submission=POST && submission passes validation...
        if form.is_valid():
            logger.debug('running users app, register_view ... user submitted via POST and form passed validation')
        
            # Assigns to variables the username and password passed in via the form in login.html
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            cash_initial = form.cleaned_data['cash_initial']
            accounting_method = form.cleaned_data['accounting_method']
            tax_loss_offsets = form.cleaned_data['tax_loss_offsets']
            tax_rate_STCG = form.cleaned_data['tax_rate_STCG']
            tax_rate_LTCG = form.cleaned_data['tax_rate_LTCG']

            try:
                # Step 2.1.1.1: If email and/or username are already registered, flash error and redirect to register.html.
                if retrieve_email(email) or retrieve_username(username):
                    logger.debug(f'running users app, register_view ... user-submitted email and/or username is already registered. Flashing error msg and returning to register.html')
                    messages.error(request, 'Error: Email address and/or username is unavailable. If you already have an account, please log in. Otherwise, please amend your entries.')
                    return render(request, "users/register.html", context)
                
                # Step 2.1.1.2: If email and username are not already registered, input data to DB.
                user = User.objects.create_user(
                    first_name=first_name,
                    last_name=last_name,
                    username=username, 
                    email=email, 
                    password=password, 
                )
                user.save()
                logger.debug(f'running users app, register_view ... user added to DB. user is: { user }')

                
                user_profile = UserProfile.objects.create(
                    user=user,
                    cash_initial=cash_initial,
                    cash=cash_initial,
                    accounting_method=accounting_method,
                    tax_loss_offsets=tax_loss_offsets,
                    tax_rate_STCG=tax_rate_STCG,
                    tax_rate_LTCG=tax_rate_LTCG,
                )
                logger.debug(f'running users app, register_view ... user_profile successfully added to DB. user_profile is: { user_profile }')

                # Step 2.1.1.3: Query new user object from DB.
                user = User.objects.filter(email=email).first()
                logger.debug(request, f'running users app, register_view ... successfully pulled user object post-creation using email: { email }. User object is: { user }')
                
                # Step 2.1.1.3: Generate token
                token = generate_unique_token(user)
                logger.debug(f'running users app, register_view ... token generated')
                
                # Step 2.1.1.4: Formulate email
                TOKEN_TIMEOUT_minutes = int(int(os.getenv('TOKEN_TIMEOUT'))/60)
                username = user.username
                sender = EMAIL_ADDRESS_INFO
                recipient = user.email
                subject = f'Confirm your registration with { PROJECT_NAME }'
                url = generate_confirmation_url(route='register_confirmation', token=token, user=user)
                body = f'''Dear { user.username }: to confirm your registration with MyFinance50, please visit the following link within the next { TOKEN_TIMEOUT_minutes } minutes:
                    
{ url }

If you did not make this request, you may ignore it.

Thank you,
Team {PROJECT_NAME}'''


                # Step 2.1.1.5: Send email.
                send_email(body=body, recipient=recipient, sender=sender, subject=subject)
                #logger.debug(f'running users app, register_view ... reset email sent to email address: { user.email }.')
                messages.success(request, 'Thank you for registering. Please check your email inbox and spam folders for an email containing your confirmation link.')
                return redirect('users:login')

            # Step 2.1.2: If sending email fails, flash error message and return to register
            except Exception as e:
                logger.error(f'running users app, register_view ... Error 2.1.2 (unable to register user in DB and send email): {e}. Flashing error msg and rendering register.html ')
                messages.error(request, f'Error: Unable to send email. Please ensure you are using a valid email address.')
                return render(request, "users/register.html", context)

        # Step 2.2: Handle submission via post + user input fails form validation
        else:
            logger.debug(f'running users app, register_view ... Error 2.2 (form validation errors), flashing message and redirecting user to /register')    
            for field, errors in form.errors.items():
                logger.debug(f'running users app, register_view ... erroring field is: { field }')
                for error in errors:
                    logger.debug(f'running users app, register_view ... erroring on this field is: {error}')
            messages.error(request, 'Error: Invalid input. Please see the red text below for assistance.')
            return render(request, "users/register.html", context)
            
    # Step 3: User arrived via GET
    else:
        logger.debug(f'running users app, register_view ... user arrived via GET')
        return render(request, "users/register.html", context)

#-------------------------------------------------------------------------

# Changes user's status to confirmed
@require_http_methods(["GET", "POST"])
def register_confirmation_view(request):
    logger.debug('running users app, register_confirmation_view ... view started')

    try:
        token = request.GET.get('token')
        encoded_email = request.GET.get('email')
        email = force_str(urlsafe_base64_decode(encoded_email))
        logger.debug(f'running users app, register_confirmation_view ... email from url is: { email }')

        user = User.objects.filter(email=email).first()
        logger.debug(f'running users app, register_confirmation_view ... user object retrieved via email in url: { email } is: { user }')

        # Step 1: Take the token and decode it
        #user = verify_unique_token(decoded_token, settings.SECRET_KEY, int(os.getenv('MAX_TOKEN_AGE_SECONDS')))
        token_generator = PasswordResetTokenGenerator()

        # Step 2: If token is invalid, flash error msg and redirect user to register
        if not token_generator.check_token(user, token):
            logger.debug(f'running users app, register_confirmation_view ... no user found.')
            messages.error(request, 'Error: If you have already confirmed your account, please log in. Otherwise please re-register your account to get a new confirmation link via email.')    
            return redirect('users:login')

        user_profile = UserProfile.objects.filter(user=user).first()
        
        # If the user associated with the token does not exist, flash message and redirect to register.
        if not user_profile:
            logger.error(f"No UserProfile found for user: { user }")
            messages.error(request, "Error: User profile not found.")
            return redirect('users:register')
        
        # Step 4: If user,confirmed = false, change to true, flash success, and redirect to login.
        if not user_profile.confirmed:
            user_profile.confirmed = True
            user_profile.save()
            logger.debug(f'running /register_confirmation ... updated user: { user } to confirmed. Redirecting to user:login.')
            messages.success(request, f'Your registration is confirmed. Welcome to { PROJECT_NAME }! Please log into your account to begin.')
            return redirect('users:login')
        # If user + confirmed = true, flash error message and redirect to login. Note: this should not be possible since token is one-time-use.
        else:
            logger.debug(f'running /register_confirmation ... Error 4 (user already confirmed). Flashing msg and redirecting to login.')
            messages.error(request, 'Error: This account is already confirmed. Please log in.')
            return redirect('user:login')

    # Step 5: If token is invalid or DB update fails, flask error message and redirect to reset.html
    except Exception as e:
            logger.debug(f'running /register_confirmation ...  Error: unable to change user_profile.concerned to True. Error is: {e}. Flashing error msg and rendering register.html ')
            messages.error(request, 'Error: Invalid or expired authentication link. Please log in or re-register.')
            return redirect('users:login')
