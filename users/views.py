# Provides ability to authenticate username+pw, log a user in, log a user out.
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from django.urls import reverse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .forms import LoginForm
from google.oauth2 import service_account
from googleapiclient.discovery import build
from .models import User
import logging
import os
logger = logging.getLogger('django')

#-------------------------------------------------------------------------------

# Helper functions to be externalized

# Generates confirmation url that, when clicked, runs the 
def generate_confirmation_url(token):
    logger.debug(f'running users app, generate_confirmation_url(token) ... function started')
    
    # This gives you the relative URL path, assuming your URL pattern expects a 'token' parameter
    relative_url = reverse('register_confirmation', args=[token])
    
    # The value for MY_SITE_DMAIN (e.g., 'www.example.com' or 'localhost:800' is defined in configs_project and then imported into settings.py)
    domain = settings.MY_SITE_DOMAIN  # Make sure to add MY_SITE_DOMAIN in your settings.py
    logger.debug(f'running users app, generate_confirmation_url(token) ... domain is: { domain }')

    # Decide the protocol based on your setup; use 'https' if your site is served over SSL/TLS
    protocol = 'https'
    logger.debug(f'running users app, generate_confirmation_url(token) ... protocol is: { protocol }')

    # Construct the full URL
    url = f"{protocol}://{domain}{relative_url}"
    return url


# Generates a nonce to work with Talisman-managed CSP
def generate_nonce():
    logger.debug('running users app, generate_nonce() ... generated nonce')
    return os.urandom(16).hex()


# Token generation for password reset and registration
def generate_unique_token(user):
    logger.debug(f'running generate_unique_token(user_id)... starting')
    
    token_generator = PasswordResetTokenGenerator()
    token = token_generator.make_token(user)
    
    logger.debug(f'running generate_unique_token(user)... generated token')
    return token


# Queries the DB to check if user_input matches a registered email. Returns None if no match.
def retrieve_email_address(user_input):
    logger.debug(f'running retrieve_email_address(user_input) ... function started')
    return User.objects.filter(email=user_input).first()


# Queries the DB to check if user_input matches a registered email
def retrieve_username(user_input):
    logger.debug(f'running retrieve_username(user_input) ... function started')
    return User.objects.filter(username=user_input).exists()


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



#-------------------------------------------------------------------------------

def index(request):
    logger.debug('running users app, index ... view started')

    # Request has "user" and "is_authenticated" built into it that tells us if the user is signed in or not.
    if not request.user.is_authenticated:
        logger.debug('running users app, index ... user is not authenticated')

        # If user isn't signed in, we redirect them to the login view
        return HttpResponseRedirect(reverse('users:login'))
    
    # Otherwise, if the user is authenticated
    return render(request, "users/user.html")
    
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
        
        # Do the following if submission=POST && submission passes validation...
        if form.is_valid():
            logger.debug('running users app, login_view ... user submitted via POST and form passed validation')
        
            # Assigns to variables the username and password passed in via the form in login.html
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
        
            # Runs the authenticate function on username and password and saves the result as the variable "user"
            user = authenticate(request, email=email, password=password)
        
            if user is not None:
                logger.debug('running users app login_view ... user found in DB')
                
                # This logs the user in if a matching username+password pair is found.
                login(request, user)
                logger.debug('running users app login_view ... user logged in, reversing to index')
                return HttpResponseRedirect(reverse('index'))
        
            # If user = None (e.g. user is not found in DB)    
            else:
                # If the user is None, that means that the user has not yet 
                # registered or has entered the wrong username and/or password.
                # In that case, we will render the login page with the message: Invalid credentials.
                logger.debug('running users app login_view ... user not found in DB')
                messages.error(request, 'Error: Invalid credentials.')
                return render(request, "users/login.html", {"form": form})

        # Do the following if submission=POST && submission fails validation...
        else:
            logger.debug('running users app, login_view ... user submitted via POST and form failed validation')
            messages.error(request, 'Error: Invalid input. Please see the red text below for assistance.')
            return render(request, "users/login.html", {"form": form})

    else:
        logger.debug('running users app login_view ... user arrived via GET')
        # If not submitted via post (e.g. we are not handling data submitted 
        # by the user via the form), then display the login page.
        return render(request, "users/login.html", {"form": form})

#--------------------------------------------------------------------------------

@login_required(login_url="login")
def logout_view(request):
    logger.debug('running users app, logout_view ... view started')

    # logout is a function built into django.
    # This simply logs out the currently logged-in user.
    logout(request)
    # After user is logged out, he is redirected to the login 
    # page with the message "Logged out.".
    logger.debug('running users app, logout_view ... user is logged out and is being redirected to login.html')
    return render(request, "users/login.html", {
        "message": "Logged out."
    })

#---------------------------------------------------------------------------

def register_view(request):
    logger.debug('running users app, register_view ... view started')

    # Instantiate the form with request.POST or no data depending on the request type
    form = RegisterForm(request.POST or None)

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
                logger.debug(f'running users app, register_view ... user-submitted first_name is: { first_name }')
                logger.debug(f'running users app, register_view ... user-submitted last_name is: { last_name }')
                logger.debug(f'running users app, register_view ... user-submitted username is: { username }')
                logger.debug(f'running users app, register_view ... user-submitted email address is: { email }')
                logger.debug(f'running users app, register_view ... user-submitted accounting_method is: { accounting_method }')
                logger.debug(f'running users app, register_view ... user-submitted tax_loss_offsets is: { tax_loss_offsets }')
                logger.debug(f'running users app, register_view ... user-submitted tax_rate_STCG is: { tax_rate_STCG }')
                logger.debug(f'running users app, register_view ... user-submitted tax_rate_LTCG is: { tax_rate_LTCG }')


                # Step 2.1.1.1: If email and/or username are already registered, flash error and redirect to register.html.
                if retrieve_email_address(email) or retrieve_username(username):
                    logger.debug(f'running users app, register_view ... user-submitted email and/or username is already registered. Flashing error msg and returning to register.html')
                    messages.error(request, 'Error: Email address and/or username is unavailable. If you already have an account, please log in. Otherwise, please amend your entries.')
                    return render(request, "users/register.html", {"form": form})
                
                # Step 2.1.1.2: If email and username are not already registered, input data to DB.
                user = User.objects.create_user(
                    first_name=first_name,
                    last_name=last_name,
                    username=username, 
                    email=email, 
                    password=password, 
                )
                user.save()
                
                user_profile = UserProfile.objects.create(
                    user=user,
                    cash_initial=cash_initial,
                    cash=cash_initial,
                    accounting_method=accounting_method,
                    tax_loss_offsets=tax_loss_offsets,
                    tax_rate_STCG=tax_rate_STCG,
                    tax_rate_LTCG=tax_rate_LTCG,
                )
                logger.debug(f'running users app, register_view ... new user and user_profile added to DB w/ unconfirmed=0')

                # Step 2.1.1.3: Query new user object from DB to get id.
                user = User.objects.filter(email=email).scalar()

                # Step 2.1.1.3: Generate token
                token = generate_unique_token(user)
                logger.debug(f'running users app, register_view ... token generated')
                logger.debug(f'running users app, register_view ... int(os.getenv(MAX_TOKEN_AGE_SECONDS) is: { int(os.getenv("MAX_TOKEN_AGE_SECONDS")) }')

                # Step 2.1.1.4: Formulate email
                token_age_max_minutes = int(int(os.getenv('MAX_TOKEN_AGE_SECONDS'))/60)
                username = user.username
                recipient = user.email
                subject = 'Confirm your registration with Jujur'
                url = generate_confirmation_url(token)
                body = f'''Dear { user.username }: to confirm your registration with MyFinance50, please visit the following link within the next { token_age_max_minutes } minutes:
                    
{ url }

If you did not make this request, you may ignore it.

Thank you,
Team {project_name}'''


                # Step 2.1.1.5: Send email.
                send_email(body=body, recipient=recipient, sender=sender, subject=subject)
                logger.debug(f'running users app, register_view ... reset email sent to email address: { user.email }.')
                messages.success(request, 'Your message has been sent. Thank you!')
                return redirect('users:login')

            # Step 2.1.2: If sending email fails, flash error message and return to register
            except Exception as e:
                logger.error(f'running users app, register_view ... Error 2.1.2 (unable to register user in DB and send email): {e}. Flashing error msg and rendering register.html ')
                messages.error('Error: Unable to send email. Please ensure you are using a valid email address.')
                return render(request, "users/register.html", {"form": form})

        # Step 2.2: Handle submission via post + user input fails form validation
        else:
            logger.debug(f'running users app, register_view ... Error 2.2 (form validation errors), flashing message and redirecting user to /register')    
            for field, errors in form.errors.items():
                logger.debug(f'running users app, register_view ... erroring field is: { field }')
                for error in errors:
                    logger.debug(f'running users app, register_view ... erroring on this field is: {error}')
            messages.error('Error: Invalid input. Please see the red text below for assistance.')
            return render(request, "users/register.html", {"form": form})
            
    # Step 3: User arrived via GET
    else:
        logger.debug(f'running users app, register_view ... user arrived via GET')
        return render(request, "users/register.html", {"form": form})

