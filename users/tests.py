from datetime import timedelta
from django.test import Client, override_settings, TestCase
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator, PasswordResetTokenGenerator
from django.contrib.messages import get_messages
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
import logging
from .models import UserProfile
import re
from unittest.mock import patch
from users import urls as users_urls


User = get_user_model()
logger = logging.getLogger('django')
logger.debug(f'running users.tests.py ... users URL patterns: {users_urls.urlpatterns}')

# Define global variables here:
password_correct = 'abc123'
password_incorrect = 'abc1234'

email_correct_confirmed = 'confirmed@mattmcdonnell.net'
email_correct_unconfirmed = 'unconfirmed@mattmcdonnell.net'
email_incorrect = 'wrongemail@mattmcdonnell.net'

test_number = 1
counter = 1


malicious_sql_code = "' OR '1'='1' --"
malicious_html_code = "<script>alert('test')</script>"

class MyModelTests(TestCase):
    def setUp(self):

        # Start patching 'users.views.send_email' and add the mock to the instance
        self.mock_send_email = patch('users.views.send_email').start()
        self.mock_send_email.return_value = None # Set any default behaviors for your mock here, if needed

        # Create confirmed user
        self.user_confirmed = get_user_model().objects.create_user(
            first_name='John',
            last_name='Doe',
            email=email_correct_confirmed,
            password=password_correct,
            is_superuser=False,
            username='confirmedtestuser',
            is_staff=False,
            is_active=True,
        )

        UserProfile.objects.create(
            user=self.user_confirmed,
            cash=10000,
            cash_initial=10000,
            accounting_method='FIFO',
            tax_loss_offsets='On',
            tax_rate_STCG=30,
            tax_rate_LTCG=15,
            confirmed=True,
        )
        # Print statements for confirmed user
        logger.debug(f'running users/tests.py, setup ... user_confirmed created: {self.user_confirmed.username}, Email: {self.user_confirmed.email}, Active: {self.user_confirmed.is_active}') 
        # Test authenticating confirmed user
        authenticated_user = authenticate(username=email_correct_confirmed, password=password_correct)
        logger.debug(f'running users/tests.py, setup ... user_confirmed Authentication Success: {authenticated_user is not None}')


        # Create unconfirmed user
        self.user_unconfirmed = get_user_model().objects.create_user(
            first_name='John',
            last_name='Doe',
            email=email_correct_unconfirmed,
            password=password_correct,
            is_superuser=False,
            username='unconfirmedtestuser',
            is_staff=False,
            is_active=True,
        )

        UserProfile.objects.create(
            user=self.user_unconfirmed,
            cash=10000,
            cash_initial=10000,
            accounting_method='FIFO',
            tax_loss_offsets='On',
            tax_rate_STCG=30,
            tax_rate_LTCG=15,
            confirmed=False,
        )
        # Print statements for unconfirmed user
        logger.debug(f'running users/tests.py, setup ... unconfirmed user created: {self.user_unconfirmed.username}, Email: {self.user_unconfirmed.email}, Active: {self.user_unconfirmed.is_active}') 
        # Test authenticating unconfirmed user
        authenticated_user = authenticate(email=email_correct_unconfirmed, password=password_correct)
        logger.debug(f'running users/tests.py, setup ... user_unconfirmed Authentication Success: {authenticated_user is not None}')


    def tearDown(self):
        # Stop patching 'users.views.send_email'
        patch.stopall()

    #---------------------------------------------------------------------------

    # Tests for login_view:
    # 1. /login/ returns status 200
    # 2. Happy path: login -> index
    # 3: Missing CSRF token
    # 4. Missing email
    # 5. Missing password
    # 6. Confirmed user + correct email + wrong password
    # 7. Unconfirmed user + correct email + correct password
    # 8. Email input not in format of an email address
    # 9. Confirmed user w/ prohibited chars in password
    # 10. SQL injection into password
    # 11. HTML/JS injection into password

    # login_view Test 1: login.html returns code 200
    def test_users_login_code_200(self):
        logger.debug(f'running users/tests.py, test { test_number } ... requested URL in test 1 is: {reverse("users:login")}')
        
        response = self.client.get(reverse('users:login'), follow=False)  # Use 'login' as your named URL pattern
        
        if response.status_code in [301, 302]:
            logger.debug(f'running users/tests.py, test { test_number } ... redirected to URL: {response.url}')
        
        self.assertEqual(response.status_code, 200)
        

    # login_view Test 2: Happy Path: Confirmed user logs in w/ valid email address + valid password --> user redirected to / w/ success message.
    def test_users_login_happy_path(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        login_url = reverse('users:login')
        logger.debug(f'running users/tests.py, test { test_number } ... login URL is: {login_url}')

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:login'), {
            'email': email_correct_confirmed,
            'password': password_correct,
        })

        # Check for the initial redirect
        self.assertEqual(response.status_code, 302)

        # Manually follow the redirect if necessary
        redirect_url = response.url  # This is the URL to which the response is redirecting
        logger.debug(f'Running users/tests.py, test { test_number } ... response.url is: {redirect_url}')  # Check the URL

        # Follow the redirect manually
        response_followed = self.client.get(redirect_url, follow=True)
        logger.debug(f'Running users/tests.py, test { test_number } ... final destination after following redirect is: {response_followed.request["PATH_INFO"]}')

        # Assert the final response is 200
        self.assertEqual(response_followed.status_code, 200)

        # Assert the final destination uses the expected template (if applicable)
        self.assertTemplateUsed(response_followed, 'brokerage/index.html')  # Replace 'index_template_name.html' with your actual index template

    
    # login_view Test 3: Missing CSRF token on form submission
    def test_users_login_missing_CSRF(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Initialize the Django test client
        client = Client(enforce_csrf_checks=True)  # This enforces CSRF checks

        login_url = reverse('users:login')
        logger.debug(f'running users/tests.py, test { test_number } ... login URL is: {login_url}')

        # Post without following redirects to check the immediate response
        response = client.post(login_url, {
            'email': email_correct_confirmed,
            'password': password_correct,
        })

        # Since a CSRF token is missing, we expect a 403 Forbidden response
        self.assertEqual(response.status_code, 403)
        
        
    # login_view Test 4: Confirmed user omits email from form submission
    def test_users_login_missing_email(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:login'), {
            'email': ' ',
            'password': password_correct,
        }, follow=True)  # Notice follow=True, it ensures that after the post request if there is a redirect, it will be followed and the final response will be captured.

        # Check if the error message is present in the response content
        self.assertIn("This field is required.", response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/login.html')  # Ensure 'users/login.html' is the correct path to your login template


    # login_view Test 5: Confirmed user omits password from form submission
    def test_users_login_missing_password(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:login'), {
            'email': email_correct_confirmed,
            'password': ' ',
        }, follow=True)  # Notice follow=True, it ensures that after the post request if there is a redirect, it will be followed and the final response will be captured.

        # Check if the error message is present in the response content
        self.assertIn("This field is required.", response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/login.html')  # Ensure 'users/login.html' is the correct path to your login template


    # login_view Test 6: Confirmed user uses wrong password
    def test_users_login_bad_password(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:login'), {
            'email': email_correct_confirmed,
            'password': password_incorrect,
        }, follow=True)  # Notice follow=True, it ensures that after the post request if there is a redirect, it will be followed and the final response will be captured.

        # Check if the error message is present in the response content
        self.assertIn('Invalid credentials', response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/login.html')  # Ensure 'users/login.html' is the correct path to your login template


    # login_view Test 7: Unconfirmed user tries to log in
    def test_users_login_unconfirmed_user(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:login'), {
            'email': email_correct_unconfirmed,
            'password': password_correct,
        }, follow=True)  # Notice follow=True, it ensures that after the post request if there is a redirect, it will be followed and the final response will be captured.

        # Check if the error message is present in the response content
        self.assertIn('You must confirm your account before logging in', response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/login.html')  # Ensure 'users/login.html' is the correct path to your login template


    # login_view Test 8: User enters something other than an email address in login form
    def test_users_login_not_email_format(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test {test_number} ... starting test')

        global malicious_sql_code
        
        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:login'), {
            'email': 'mattatmattmcdonnell.net',
            'password': password_correct,
        }, follow=True)

        # Since SQL injection should not be successful, we expect the form to be displayed again
        # with an error message related to invalid credentials rather than a database error.
        # This implies that the inputs are sanitized.
        # Check if a generic error message is present in the response content
        self.assertIn('Invalid input', response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/login.html')
    

    # login_view Test 9: User enters prohibited chars for password
    def test_users_login_password_prohibited_chars(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test {test_number} ... starting test')

        global malicious_sql_code
        
        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:login'), {
            'email': email_correct_confirmed,
            'password': 'abc123!@@#$%^&*()(*&^%$#)',
        }, follow=True)

        # Since SQL injection should not be successful, we expect the form to be displayed again
        # with an error message related to invalid credentials rather than a database error.
        # This implies that the inputs are sanitized.
        # Check if a generic error message is present in the response content
        self.assertIn('Invalid credentials', response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/login.html')
    
    
    # login_view Test 10: Attempted SQL Injection in password
    def test_users_login_sql_injection_attempt(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test {test_number} ... starting test')

        global malicious_sql_code
        
        # Initialize the Django test client
        client = Client(enforce_csrf_checks=True)  # This enforces CSRF checks

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:login'), {
            'email': email_correct_confirmed,
            'password': malicious_sql_code,
        }, follow=True)

        # Since SQL injection should not be successful, we expect the form to be displayed again
        # with an error message related to invalid credentials rather than a database error.
        # This implies that the inputs are sanitized.
        # Check if a generic error message is present in the response content
        self.assertIn('Invalid credentials', response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/login.html')


    # login_view Test 11: Attempted HTML/JS Injection in login form
    def test_users_login_html_injection_attempt(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test {test_number} ... starting test')

        global malicious_html_code
        
        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:login'), {
            'email': malicious_html_code,
            'password': password_correct,
        }, follow=True)

        # Since SQL injection should not be successful, we expect the form to be displayed again
        # with an error message related to invalid credentials rather than a database error.
        # This implies that the inputs are sanitized.
        # Check if a generic error message is present in the response content
        self.assertIn('Invalid input', response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/login.html')

    #---------------------------------------------------------------------------

    # Tests for register_view:

    # /register/ returns status 200
    # Register happy path: navigate to register --> enter details --> email sent --> redirected to login
    # Missing CSRF
    # Missing first_name
    # Missing last_name
    # Missing username
    # Missing email
    # Missing password
    # Missing password_confirmation
    # Missing cash_initial
    # Missing accounting_method
    # Missing tax_loss_offsets
    # Missing tax_rate_STCG
    # Missing tax_rate_LTCG
    # Email is not in email format
    # password != password_confirmation
    # cash_initial < 0
    # accounting_method is something other than 'LIFO' or 'FIFO'
    # tax_rate_STCG is < 0
    # tax_rate_STCG is > 50%
    # tax_rate_LTCG is < 0
    # tax_rate_LTCG is > 50%
    # SQL injection attempt for password
    # HTML/JS injection attempt for password




    # register_view Test 1: /register/ returns code 200
    def test_users_register_code_200(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... requested URL in test 1 is: {reverse("users:register")}')
        
        response = self.client.get(reverse('users:register'), follow=False)  # Use 'login' as your named URL pattern
        
        if response.status_code in [301, 302]:
            logger.debug(f'running users/tests.py, test { test_number } ... redirected to URL: {response.url}')
        
        self.assertEqual(response.status_code, 200)


    # register_view Test 2: Happy path
    def test_users_register_happy_path(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Visits /register/ and submits valid data
        register_url = reverse('users:register')
        logger.debug(f'running users/tests.py, test { test_number } ... register URL is: {register_url}')

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:register'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'UnregisteredUser',
            'email': 'matt@mattmcdonnell.net',
            'password': password_correct,
            'password_confirmation': password_correct,
            'cash_initial': 10000,
            'accounting_method': 'FIFO',
            'tax_loss_offsets': 'On',
            'tax_rate_STCG': 15,
            'tax_rate_LTCG': 30
        }, follow = True)
        
        # Check that the send_email function was called
        self.mock_send_email.assert_called_once()

        # Assert the final response is 200
        self.assertEqual(response.status_code, 200)

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'users/login.html')


    # register_view Test 3: Missing CSRF
    def test_users_register_missing_CSRF(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Initialize the Django test client
        client = Client(enforce_csrf_checks=True)  # This enforces CSRF checks
        
        # Visits /register/ and submits valid data
        register_url = reverse('users:register')
        logger.debug(f'running users/tests.py, test { test_number } ... register URL is: {register_url}')

        # Post without following redirects to check the immediate response
        response = client.post(register_url, {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'UnregisteredUser',
            'email': 'matt@mattmcdonnell.net',
            'password': password_correct,
            'password_confirmation': password_correct,
            'cash_initial': 10000,
            'accounting_method': 'FIFO',
            'tax_loss_offsets': 'On',
            'tax_rate_STCG': 15,
            'tax_rate_LTCG': 30
        }, follow = True)
        
        # Assert the final response is 403: forbidden
        self.assertEqual(response.status_code, 403)

        
    # register_view Test 4: Missing first_name
    def test_users_register_missing_first_name(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Visits /register/ and submits valid data
        register_url = reverse('users:register')
        logger.debug(f'running users/tests.py, test { test_number } ... register URL is: {register_url}')

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:register'), {
            'first_name': '  ',
            'last_name': 'Doe',
            'username': 'UnregisteredUser',
            'email': 'matt@mattmcdonnell.net',
            'password': password_correct,
            'password_confirmation': password_correct,
            'cash_initial': 10000,
            'accounting_method': 'FIFO',
            'tax_loss_offsets': 'On',
            'tax_rate_STCG': 15,
            'tax_rate_LTCG': 30
        }, follow = True)
        
        # Check if the error message is present in the response content
        self.assertIn("This field is required.", response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/register.html')


    # register_view Test 5: Missing last_name
    def test_users_register_missing_last_name(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Visits /register/ and submits valid data
        register_url = reverse('users:register')
        logger.debug(f'running users/tests.py, test { test_number } ... register URL is: {register_url}')

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:register'), {
            'first_name': 'John',
            'last_name': '  ',
            'username': 'UnregisteredUser',
            'email': 'matt@mattmcdonnell.net',
            'password': password_correct,
            'password_confirmation': password_correct,
            'cash_initial': 10000,
            'accounting_method': 'FIFO',
            'tax_loss_offsets': 'On',
            'tax_rate_STCG': 15,
            'tax_rate_LTCG': 30
        }, follow = True)
        
        # Check if the error message is present in the response content
        self.assertIn("This field is required.", response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/register.html')


    # register_view Test 6: Missing username
    def test_users_register_missing_username(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Visits /register/ and submits valid data
        register_url = reverse('users:register')
        logger.debug(f'running users/tests.py, test { test_number } ... register URL is: {register_url}')

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:register'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': '  ',
            'email': 'matt@mattmcdonnell.net',
            'password': password_correct,
            'password_confirmation': password_correct,
            'cash_initial': 10000,
            'accounting_method': 'FIFO',
            'tax_loss_offsets': 'On',
            'tax_rate_STCG': 15,
            'tax_rate_LTCG': 30
        }, follow = True)
        
        # Check if the error message is present in the response content
        self.assertIn("This field is required.", response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/register.html')


    # register_view Test 7: Missing email
    def test_users_register_missing_email(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Visits /register/ and submits valid data
        register_url = reverse('users:register')
        logger.debug(f'running users/tests.py, test { test_number } ... register URL is: {register_url}')

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:register'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'testusername',
            'email': '  ',
            'password': password_correct,
            'password_confirmation': password_correct,
            'cash_initial': 10000,
            'accounting_method': 'FIFO',
            'tax_loss_offsets': 'On',
            'tax_rate_STCG': 15,
            'tax_rate_LTCG': 30
        }, follow = True)
        
        # Check if the error message is present in the response content
        self.assertIn("This field is required.", response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/register.html')


    # register_view Test 8: Missing password
    def test_users_register_missing_password(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Visits /register/ and submits valid data
        register_url = reverse('users:register')
        logger.debug(f'running users/tests.py, test { test_number } ... register URL is: {register_url}')

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:register'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'testusername',
            'email': 'testemail@mattmcdonnell.net',
            'password': '  ',
            'password_confirmation': password_correct,
            'cash_initial': 10000,
            'accounting_method': 'FIFO',
            'tax_loss_offsets': 'On',
            'tax_rate_STCG': 15,
            'tax_rate_LTCG': 30
        }, follow = True)
        
        # Check if the error message is present in the response content
        self.assertIn("This field is required.", response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/register.html')
        
        
    # register_view Test 9: Missing password_confirmation
    def test_users_register_missing_password_confirmation(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Visits /register/ and submits valid data
        register_url = reverse('users:register')
        logger.debug(f'running users/tests.py, test { test_number } ... register URL is: {register_url}')

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:register'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'testusername',
            'email': 'testemail@mattmcdonnell.net',
            'password': password_correct,
            'password_confirmation': '  ',
            'cash_initial': 10000,
            'accounting_method': 'FIFO',
            'tax_loss_offsets': 'On',
            'tax_rate_STCG': 15,
            'tax_rate_LTCG': 30
        }, follow = True)
        
        # Check if the error message is present in the response content
        self.assertIn("This field is required.", response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/register.html')


    # register_view Test 10: Missing cash_initial
    def test_users_register_missing_cash_initial(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Visits /register/ and submits valid data
        register_url = reverse('users:register')
        logger.debug(f'running users/tests.py, test { test_number } ... register URL is: {register_url}')

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:register'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'testusername',
            'email': 'testemail@mattmcdonnell.net',
            'password': password_correct,
            'password_confirmation': password_correct,
            'cash_initial': '  ',
            'accounting_method': 'FIFO',
            'tax_loss_offsets': 'On',
            'tax_rate_STCG': 15,
            'tax_rate_LTCG': 30
        }, follow = True)
        
        # Check if the error message is present in the response content
        self.assertIn("Enter a valid number.", response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/register.html')


    # register_view Test 11: Missing accounting_method
    def test_users_register_missing_accounting_method(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Visits /register/ and submits valid data
        register_url = reverse('users:register')
        logger.debug(f'running users/tests.py, test { test_number } ... register URL is: {register_url}')

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:register'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'testusername',
            'email': 'testemail@mattmcdonnell.net',
            'password': password_correct,
            'password_confirmation': password_correct,
            'cash_initial': 10000,
            'accounting_method': '  ',
            'tax_loss_offsets': 'On',
            'tax_rate_STCG': 15,
            'tax_rate_LTCG': 30
        }, follow = True)
        
        # Check if the error message is present in the response content
        self.assertIn('Select a valid choice.', response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/register.html')


    # register_view Test 12: Missing tax_loss_offsets
    def test_users_register_missing_tax_loss_offsets(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Visits /register/ and submits valid data
        register_url = reverse('users:register')
        logger.debug(f'running users/tests.py, test { test_number } ... register URL is: {register_url}')

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:register'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'testusername',
            'email': 'testemail@mattmcdonnell.net',
            'password': password_correct,
            'password_confirmation': password_correct,
            'cash_initial': 10000,
            'accounting_method': 'FIFO',
            'tax_loss_offsets': '  ',
            'tax_rate_STCG': 15,
            'tax_rate_LTCG': 30
        }, follow = True)
        
        # Check if the error message is present in the response content
        self.assertIn('Select a valid choice.', response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/register.html')


    # register_view Test 13: Missing tax_rate_STCG
    def test_users_register_missing_tax_rate_STCG(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Visits /register/ and submits valid data
        register_url = reverse('users:register')
        logger.debug(f'running users/tests.py, test { test_number } ... register URL is: {register_url}')

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:register'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'testusername',
            'email': 'testemail@mattmcdonnell.net',
            'password': password_correct,
            'password_confirmation': password_correct,
            'cash_initial': 10000,
            'accounting_method': 'FIFO',
            'tax_loss_offsets': 'On',
            'tax_rate_STCG': '  ',
            'tax_rate_LTCG': 30
        }, follow = True)
        
        # Check if the error message is present in the response content
        self.assertIn('Enter a number.', response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/register.html')


    # register_view Test 14: Missing tax_rate_LTCG
    def test_users_register_missing_tax_rate_LTCG(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Visits /register/ and submits valid data
        register_url = reverse('users:register')
        logger.debug(f'running users/tests.py, test { test_number } ... register URL is: {register_url}')

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:register'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'testusername',
            'email': 'testemail@mattmcdonnell.net',
            'password': password_correct,
            'password_confirmation': password_correct,
            'cash_initial': 10000,
            'accounting_method': 'FIFO',
            'tax_loss_offsets': 'On',
            'tax_rate_STCG': 15,
            'tax_rate_LTCG': '  '
        }, follow = True)
        
        # Check if the error message is present in the response content
        self.assertIn('Enter a number.', response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/register.html')


    # register_view Test 15: Email not in email address format
    def test_users_register_not_email_format(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Visits /register/ and submits valid data
        register_url = reverse('users:register')
        logger.debug(f'running users/tests.py, test { test_number } ... register URL is: {register_url}')

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:register'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'testusername',
            'email': 'testemailatmattmcdonnell.net',
            'password': password_correct,
            'password_confirmation': password_correct,
            'cash_initial': 10000,
            'accounting_method': 'FIFO',
            'tax_loss_offsets': 'On',
            'tax_rate_STCG': 15,
            'tax_rate_LTCG': 30
        }, follow = True)
        
        # Check if the error message is present in the response content
        self.assertIn('Enter a valid email address.', response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/register.html')


    # register_view Test 16: password != password_confirmation
    def test_users_register_passwords_not_matching(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Visits /register/ and submits valid data
        register_url = reverse('users:register')
        logger.debug(f'running users/tests.py, test { test_number } ... register URL is: {register_url}')

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:register'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'testusername',
            'email': email_correct_confirmed,
            'password': password_correct,
            'password_confirmation': password_incorrect,
            'cash_initial': 10000,
            'accounting_method': 'FIFO',
            'tax_loss_offsets': 'On',
            'tax_rate_STCG': 15,
            'tax_rate_LTCG': 30
        }, follow = True)
        
        # Check if the error message is present in the response content
        self.assertIn('Invalid input.', response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/register.html')


    # register_view Test 17: cash_initial < 0
    def test_users_register_cash_initial_negative(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Visits /register/ and submits valid data
        register_url = reverse('users:register')
        logger.debug(f'running users/tests.py, test { test_number } ... register URL is: {register_url}')

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:register'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'testusername',
            'email': email_correct_confirmed,
            'password': password_correct,
            'password_confirmation': password_incorrect,
            'cash_initial': -10000,
            'accounting_method': 'FIFO',
            'tax_loss_offsets': 'On',
            'tax_rate_STCG': 15,
            'tax_rate_LTCG': 30
        }, follow = True)
        
        # Check if the error message is present in the response content
        self.assertIn('Invalid input.', response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/register.html')


    # register_view Test 18: Accounting method not 'LIFO' or 'FIFO'
    def test_users_register_accounting_method_not_LIFO_not_FIFO(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Visits /register/ and submits valid data
        register_url = reverse('users:register')
        logger.debug(f'running users/tests.py, test { test_number } ... register URL is: {register_url}')

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:register'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'testusername',
            'email': email_correct_confirmed,
            'password': password_correct,
            'password_confirmation': password_incorrect,
            'cash_initial': 10000,
            'accounting_method': 'New',
            'tax_loss_offsets': 'On',
            'tax_rate_STCG': 15,
            'tax_rate_LTCG': 30
        }, follow = True)
        
        # Check if the error message is present in the response content
        self.assertIn('Invalid input.', response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/register.html')


    # register_view Test 19: tax_rate_STCG < 0
    def test_users_register_tax_rate_STCG_negative(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Visits /register/ and submits valid data
        register_url = reverse('users:register')
        logger.debug(f'running users/tests.py, test { test_number } ... register URL is: {register_url}')

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:register'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'testusername',
            'email': email_correct_confirmed,
            'password': password_correct,
            'password_confirmation': password_incorrect,
            'cash_initial': 10000,
            'accounting_method': 'New',
            'tax_loss_offsets': 'On',
            'tax_rate_STCG': -15,
            'tax_rate_LTCG': 30
        }, follow = True)
        
        # Check if the error message is present in the response content
        self.assertIn('Invalid input.', response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/register.html')


    # register_view Test 20: tax_rate_STCG > 50%
    def test_users_register_tax_rate_STCG_excessive(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Visits /register/ and submits valid data
        register_url = reverse('users:register')
        logger.debug(f'running users/tests.py, test { test_number } ... register URL is: {register_url}')

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:register'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'testusername',
            'email': email_correct_confirmed,
            'password': password_correct,
            'password_confirmation': password_incorrect,
            'cash_initial': 10000,
            'accounting_method': 'New',
            'tax_loss_offsets': 'On',
            'tax_rate_STCG': 95,
            'tax_rate_LTCG': 30
        }, follow = True)
        
        # Check if the error message is present in the response content
        self.assertIn('Invalid input.', response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/register.html')


    # register_view Test 21: tax_rate_LTCG < 0
    def test_users_register_tax_rate_LTCG_negative(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Visits /register/ and submits valid data
        register_url = reverse('users:register')
        logger.debug(f'running users/tests.py, test { test_number } ... register URL is: {register_url}')

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:register'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'testusername',
            'email': email_correct_confirmed,
            'password': password_correct,
            'password_confirmation': password_incorrect,
            'cash_initial': 10000,
            'accounting_method': 'New',
            'tax_loss_offsets': 'On',
            'tax_rate_STCG': 15,
            'tax_rate_LTCG': -30
        }, follow = True)
        
        # Check if the error message is present in the response content
        self.assertIn('Invalid input.', response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/register.html')


    # register_view Test 22: tax_rate_LTCG > 50%
    def test_users_register_tax_rate_LTCG_excessive(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Visits /register/ and submits valid data
        register_url = reverse('users:register')
        logger.debug(f'running users/tests.py, test { test_number } ... register URL is: {register_url}')

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:register'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'testusername',
            'email': email_correct_confirmed,
            'password': password_correct,
            'password_confirmation': password_incorrect,
            'cash_initial': 10000,
            'accounting_method': 'New',
            'tax_loss_offsets': 'On',
            'tax_rate_STCG': 15,
            'tax_rate_LTCG': 95
        }, follow = True)
        
        # Check if the error message is present in the response content
        self.assertIn('Invalid input.', response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/register.html')


        # register_view Test 19: tax_rate_STCG < 0
    def test_users_register_tax_rate_STCG_negative(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Visits /register/ and submits valid data
        register_url = reverse('users:register')
        logger.debug(f'running users/tests.py, test { test_number } ... register URL is: {register_url}')

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:register'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'testusername',
            'email': email_correct_confirmed,
            'password': password_correct,
            'password_confirmation': password_incorrect,
            'cash_initial': 10000,
            'accounting_method': 'New',
            'tax_loss_offsets': 'On',
            'tax_rate_STCG': -15,
            'tax_rate_LTCG': 30
        }, follow = True)
        
        # Check if the error message is present in the response content
        self.assertIn('Invalid input.', response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/register.html')


    # register_view Test 23: SQL injection attack for password
    def test_users_register_sql_injection_attack_password(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Visits /register/ and submits valid data
        register_url = reverse('users:register')
        logger.debug(f'running users/tests.py, test { test_number } ... register URL is: {register_url}')

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:register'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'testusername',
            'email': email_correct_confirmed,
            'password': malicious_sql_code,
            'password_confirmation': malicious_sql_code,
            'cash_initial': 10000,
            'accounting_method': 'New',
            'tax_loss_offsets': 'On',
            'tax_rate_STCG': 95,
            'tax_rate_LTCG': 30
        }, follow = True)
        
        # Check if the error message is present in the response content
        self.assertIn('Invalid input.', response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/register.html')


    # register_view Test 24: HTML/JS injection attack for password
    def test_users_register_html_injection_attack_password(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Visits /register/ and submits valid data
        register_url = reverse('users:register')
        logger.debug(f'running users/tests.py, test { test_number } ... register URL is: {register_url}')

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:register'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'testusername',
            'email': email_correct_confirmed,
            'password': malicious_html_code,
            'password_confirmation': malicious_html_code,
            'cash_initial': 10000,
            'accounting_method': 'New',
            'tax_loss_offsets': 'On',
            'tax_rate_STCG': 95,
            'tax_rate_LTCG': 30
        }, follow = True)
        
        # Check if the error message is present in the response content
        self.assertIn('Invalid input.', response.content.decode('utf-8'))

        # Optionally, check if the login template is used in the response
        self.assertTemplateUsed(response, 'users/register.html')


    #---------------------------------------------------------------------------


    # Tests for register_confirmation_view:

    # Happy path
    # Test 2: No token in url
    # Test 3: User re-uses confirmation link
    # Test 4: Token is expired

    # register_confirmation Test 25: Happy path
    def test_users_register_confirmation_happy_path(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Create a token for the user
        token_generator = PasswordResetTokenGenerator()
        token = token_generator.make_token(self.user_unconfirmed)
        uid = urlsafe_base64_encode(force_bytes(self.user_unconfirmed.email))
        
        # Construct the URL with the token and uid
        url = reverse('users:register_confirmation') + f'?token={token}&email={uid}'

        # Make the GET request
        response = self.client.get(url)

        # Reload the user's profile from the database to get updated values
        self.user_unconfirmed.userprofile.refresh_from_db()

        # Check the user's status has been changed to confirmed
        self.assertTrue(self.user_unconfirmed.userprofile.confirmed)

        # Extract messages from the response context
        messages = list(get_messages(response.wsgi_request))
        success_message_found = any('Your registration is confirmed.' in str(message) for message in messages)
        
        # Check the response redirects to the login page
        self.assertRedirects(response, reverse('users:login'))


    # register_view Test 26: No token in url
    def test_users_register_confirmation_no_token_in_url(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... requested URL in test 1 is: {reverse("users:register")}')
        
        response = self.client.get(reverse('users:register_confirmation'), follow=False)  # Use 'login' as your named URL pattern
        
        # Check for initial redirect
        self.assertEqual(response.status_code, 302)

        # Manually follow the redirect if necessary
        redirect_url = response.url  # This is the URL to which the response is redirecting
        logger.debug(f'Running users/tests.py, test { test_number } ... response.url is: {redirect_url}')  # Check the URL

        # Follow the redirect manually
        response_followed = self.client.get(redirect_url, follow=True)
        logger.debug(f'Running users/tests.py, test { test_number } ... final destination after following redirect is: {response_followed.request["PATH_INFO"]}')

        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid or expired authentication link. Please log in or re-register.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Assert the final response is 200
        self.assertEqual(response_followed.status_code, 200)

        # Assert the final destination uses the expected template (if applicable)
        self.assertTemplateUsed(response_followed, 'users/login.html')  # Replace 'index_template_name.html' with your actual index template


    # register_confirmation Test 27: User re-uses confirmation link
    def test_users_register_confirmation_re_use_link(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Create a token for the user
        token_generator = PasswordResetTokenGenerator()
        token = token_generator.make_token(self.user_unconfirmed)
        uid = urlsafe_base64_encode(force_bytes(self.user_unconfirmed.email))
        
        # Construct the URL with the token and uid
        url = reverse('users:register_confirmation') + f'?token={token}&email={uid}'

        # Make the GET request
        response = self.client.get(url)

        # Reload the user's profile from the database to get updated values
        self.user_unconfirmed.userprofile.refresh_from_db()

        # Check the user's status has been changed to confirmed
        self.assertTrue(self.user_unconfirmed.userprofile.confirmed)

        # Make the GET request again (re-using the link)
        response_reuse = self.client.get(url)
        
        # Extract messages from the response context after re-using the link
        messages_reuse = [str(message) for message in get_messages(response_reuse.wsgi_request)]

        # Directly assert that the expected error message is in the list of messages
        expected_error_message = 'Error: This account is already confirmed. Please log in.'
        self.assertIn(expected_error_message, messages_reuse, f"Expected error message '{expected_error_message}' not found in response messages after re-using the link: {messages_reuse}")
    
        # Check that the response redirects to the login page after re-using the link
        self.assertRedirects(response_reuse, reverse('users:login'))


    # register_confirmation Test 28: Expired token
    def test_users_register_confirmation_expired_token(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Create a token for the user
        token_generator = PasswordResetTokenGenerator()
        token = token_generator.make_token(self.user_unconfirmed)
        uid = urlsafe_base64_encode(force_bytes(self.user_unconfirmed.email))
        
        # Set the user's last_login to 48 hours in the past
        self.user_unconfirmed.last_login = timezone.now() - timedelta(hours=48)
        self.user_unconfirmed.save()

        # Construct the URL with the token and uid
        url = reverse('users:register_confirmation') + f'?token={token}&email={uid}'

        # Make the GET request
        response = self.client.get(url)

        # Reload the user's profile from the database to get updated values
        self.user_unconfirmed.userprofile.refresh_from_db()

        # Check the user's status has NOT been changed to confirmed
        self.assertFalse(self.user_unconfirmed.userprofile.confirmed)

        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: If you have already confirmed your account, please log in. Otherwise please re-register your account to get a new confirmation link via email.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")
        
        # Check the response redirects to the login page
        self.assertRedirects(response, reverse('users:login'))


    #---------------------------------------------------------------------------


    # Tests for password_change view:

    # Test 1: Returns 200
    # Test 2: Happy path
    # Test 3: Missing CSRF
    # Test 4: Unauthenticated user
    # missing email
    # missing password
    # missing password_old
    # missing password
    # missing password_confirmation
    # wrong password_old
    # password != password_confirmation
    # new password == old password
    # SQL injection to password
    # HTML/JS injection to password

    # Test 29: Returns 200
    def test_users_password_change_200(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, "Logging in user_confirmed failed")

        # Access password_change
        response = self.client.get(reverse('users:password_change'), follow=False)  # Use 'login' as your named URL pattern
        
        if response.status_code in [301, 302]:
            logger.debug(f'running users/tests.py, test { test_number } ... redirected to URL: {response.url}')
        
        self.assertEqual(response.status_code, 200)


    # Test 30: Happy path
    def test_users_password_change_happy_path(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, "Logging in user_confirmed failed")

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:password_change'), {
            'email': email_correct_confirmed,
            'password_old': password_correct,
            'password': 'updatedpassword12345',
            'password_confirmation': 'updatedpassword12345'
        }, follow = True)
        
        # Check for the initial redirect
        #self.assertEqual(response.status_code, 302)
        
        # Assert the final response is 200
        self.assertEqual(response.status_code, 200)
        
        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'You have successfully updated your password.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'users/login.html')


    # Test 31: Missing CSRF
    def test_users_password_change_missing_csrf(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, "Logging in user_confirmed failed")

        # Initialize the Django test client
        client = Client(enforce_csrf_checks=True)  # This enforces CSRF checks
        
        # Visits /register/ and submits valid data
        register_url = reverse('users:register')
        logger.debug(f'running users/tests.py, test { test_number } ... register URL is: {register_url}')

        # Post without following redirects to check the immediate response
        response = client.post(register_url, {
            'email': email_correct_confirmed,
            'password_old': password_correct,
            'password': 'updatedpassword12345',
            'password_confirmation': 'updatedpassword12345'
        }, follow = True)
        
        # Assert the final response is 403: forbidden
        self.assertEqual(response.status_code, 403)


    # Test 32: Unauthenticated user
    def test_users_password_change_unauthenticated_user(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:password_change'), {
            'email': email_correct_confirmed,
            'password_old': password_correct,
            'password': 'updatedpassword12345',
            'password_confirmation': 'updatedpassword12345'
        }, follow = True)
        
        # Check for the initial redirect
        self.assertEqual(response.status_code, 200)
        
        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'users/login.html')



























    
    
    
    
    # Test 33: Missing email
    def test_users_password_change_missing_email(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, "Logging in user_confirmed failed")

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:password_change'), {
            'email': '  ',
            'password_old': password_correct,
            'password': 'updatedpassword12345',
            'password_confirmation': 'updatedpassword12345'
        }, follow = True)
        
        # Assert the final response is 200
        self.assertEqual(response.status_code, 200)
        
        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid input. Please see the red text below for assistance.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'users/password_change.html')


    # Test 34: Missing password_old
    def test_users_password_change_missing_password_old(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, "Logging in user_confirmed failed")

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:password_change'), {
            'email': email_correct_confirmed,
            'password_old': '  ',
            'password': 'updatedpassword12345',
            'password_confirmation': 'updatedpassword12345'
        }, follow = True)
        
        # Assert the final response is 200
        self.assertEqual(response.status_code, 200)
        
        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid input. Please see the red text below for assistance.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'users/password_change.html')


    # Test 35: Missing password
    def test_users_password_change_missing_password(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, "Logging in user_confirmed failed")

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:password_change'), {
            'email': email_correct_confirmed,
            'password_old': password_correct,
            'password': '  ',
            'password_confirmation': 'updatedpassword12345'
        }, follow = True)
        
        # Assert the final response is 200
        self.assertEqual(response.status_code, 200)
        
        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid input. Please see the red text below for assistance.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'users/password_change.html')


    # Test 36: Missing password_confirmation
    def test_users_password_change_missing_password_confirmation(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, "Logging in user_confirmed failed")

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:password_change'), {
            'email': email_correct_confirmed,
            'password_old': password_correct,
            'password': 'updatedpassword12345',
            'password_confirmation': '  '
        }, follow = True)
        
        # Assert the final response is 200
        self.assertEqual(response.status_code, 200)
        
        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid input. Please see the red text below for assistance.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'users/password_change.html')


    # Test 37: Incorrect password_old
    def test_users_password_change_incorrect_password_old(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, "Logging in user_confirmed failed")

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:password_change'), {
            'email': email_correct_confirmed,
            'password_old': password_incorrect,
            'password': 'updatedpassword12345',
            'password_confirmation': '  '
        }, follow = True)
        
        # Assert the final response is 200
        self.assertEqual(response.status_code, 200)
        
        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid input. Please see the red text below for assistance.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'users/password_change.html')


    # Test 38: password != password_confirmation
    def test_users_password_change_mismatch_password_and_password_confirmation(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, "Logging in user_confirmed failed")

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:password_change'), {
            'email': email_correct_confirmed,
            'password_old': password_correct,
            'password': 'updatedpassword12345',
            'password_confirmation': 'updatedpassword123456'
        }, follow = True)
        
        # Assert the final response is 200
        self.assertEqual(response.status_code, 200)
        
        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid input. Please see the red text below for assistance.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'users/password_change.html')


    # Test 39: User enters the old password for new password 
    def test_users_password_change_password_old_matches_password(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, "Logging in user_confirmed failed")

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:password_change'), {
            'email': email_correct_confirmed,
            'password_old': password_correct,
            'password': password_correct,
            'password_confirmation': password_correct
        }, follow = True)
        
        # Assert the final response is 200
        self.assertEqual(response.status_code, 200)
        
        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid input. Please see the red text below for assistance.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'users/password_change.html')


    # Test 40: SQL injection to password
    def test_users_password_change_sql_injection_to_password(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, "Logging in user_confirmed failed")

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:password_change'), {
            'email': email_correct_confirmed,
            'password_old': password_correct,
            'password': malicious_sql_code,
            'password_confirmation': malicious_sql_code
        }, follow = True)
        
        # Assert the final response is 200
        self.assertEqual(response.status_code, 200)
        
        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'You have successfully updated your password.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'users/login.html')


    # Test 41: HTML/JS injection to password
    def test_users_password_change_html_injection_to_password(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, "Logging in user_confirmed failed")

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:password_change'), {
            'email': email_correct_confirmed,
            'password_old': password_correct,
            'password': malicious_html_code,
            'password_confirmation': malicious_html_code
        }, follow = True)
        
        # Assert the final response is 200
        self.assertEqual(response.status_code, 200)
        
        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'You have successfully updated your password.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'users/login.html')


    #---------------------------------------------------------------------------


    # Tests for password_reset_view:

    # Test 1: Returns 200
    # Test 2: Happy path
    # Missing CSRF
    # missing email
    # random email
    # SQL injection to password
    # HTML/JS injection to password


    # Test 42: returns code 200
    def test_users_password_reset_code_200(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... requested URL in test 1 is: {reverse("users:password_reset")}')
        
        response = self.client.get(reverse('users:password_reset'), follow=False)  # Use 'login' as your named URL pattern
        
        if response.status_code in [301, 302]:
            logger.debug(f'running users/tests.py, test { test_number } ... redirected to URL: {response.url}')
        
        self.assertEqual(response.status_code, 200)


    # Test 43: Happy path
    def test_users_password_reset_happy_path(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:password_reset'), {
            'email': email_correct_confirmed,
        }, follow = True)
        
        # Check that the send_email function was called
        self.mock_send_email.assert_called_once()

        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Please check your email inbox and spam folders for an email containing your password reset link.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")
        
        # Assert the final response is 200
        self.assertEqual(response.status_code, 200)

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'users/login.html')


    # Test 44: Missing CSRF
    def test_users_password_reset_missing_CSRF(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Initialize the Django test client
        client = Client(enforce_csrf_checks=True)  # This enforces CSRF checks
        
        # Visits /register/ and submits valid data
        register_url = reverse('users:password_reset')
        logger.debug(f'running users/tests.py, test { test_number } ... register URL is: {register_url}')

        # Post without following redirects to check the immediate response
        response = client.post(register_url, {
            'email': email_correct_confirmed,
        }, follow = True)
        
        # Assert the final response is 403: forbidden
        self.assertEqual(response.status_code, 403)


    # Test 45: Missing email
    def test_users_password_reset_missing_email(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:password_reset'), {
            'email': '  ',
        }, follow = True)
        
        # Check that the send_email function was called
        self.mock_send_email.assert_not_called()

        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid input. Please see the red text below for assistance.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")
        
        # Assert the final response is 200
        self.assertEqual(response.status_code, 200)

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'users/password-reset.html')


    # Test 46: Uses random email address
    def test_users_password_reset_random_email(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:password_reset'), {
            'email': 'randomemail@mattmcdonnell.net',
        }, follow = True)
        
        # Check that the send_email function was called
        self.mock_send_email.assert_not_called()

        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Please check your email inbox and spam folders for an email containing your password reset link.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")
        
        # Assert the final response is 200
        self.assertEqual(response.status_code, 200)

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'users/login.html')


    # Test 47: SQL injection to password
    def test_users_password_reset_SQL_injection_to_email(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:password_reset'), {
            'email': malicious_sql_code,
        }, follow = True)
        
        # Check that the send_email function was called
        self.mock_send_email.assert_not_called()

        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid input. Please see the red text below for assistance.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")
        
        # Assert the final response is 200
        self.assertEqual(response.status_code, 200)

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'users/password-reset.html')


    # Test 48: HTML/JS injection to password
    def test_users_password_reset_HTML_injection_to_email(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')
        
        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:password_reset'), {
            'email': malicious_html_code,
        }, follow = True)
        
        # Check that the send_email function was called
        self.mock_send_email.assert_not_called()

        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid input. Please see the red text below for assistance.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")
        
        # Assert the final response is 200
        self.assertEqual(response.status_code, 200)

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'users/password-reset.html')


    #---------------------------------------------------------------------------


    # Tests for password_reset_confirmation_view:

    # Happy path
    # Test 3: User re-uses confirmation link
    # Test 4: Token is expired

    # Test 49: Happy path
    def test_users_password_reset_confirmation_happy_path(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Create a token for the user
        token_generator = PasswordResetTokenGenerator()
        token = token_generator.make_token(self.user_confirmed)
        uid = urlsafe_base64_encode(force_bytes(self.user_confirmed.email))
        
        # Construct the URL with the token and uid
        url = reverse('users:password_reset_confirmation') + f'?token={token}&email={uid}'

        # Make the GET request
        response = self.client.get(url)

        # Assert the GET request loads the form page correctly
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/password-reset-confirmation.html')

        # Make the POST request with new password data
        response_post = self.client.post(url, {
            'password': 'newpassword1234',
            'password_confirmation': 'newpassword1234'
        }, follow = True)
        
        # Assert the final response is 200
        self.assertEqual(response_post.status_code, 200)
        
        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response_post.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Your password has been reset successfully.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response_post, 'users/login.html')
        

    # Test 50: User re-uses confirmation link
    def test_users_password_reset_confirmation_re_use_link(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Create a token for the user
        token_generator = PasswordResetTokenGenerator()
        token = token_generator.make_token(self.user_confirmed)
        uid = urlsafe_base64_encode(force_bytes(self.user_confirmed.email))
        
        # Construct the URL with the token and uid
        url = reverse('users:password_reset_confirmation') + f'?token={token}&email={uid}'

        # Make the GET request
        response = self.client.get(url)

        # Assert the GET request loads the form page correctly
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/password-reset-confirmation.html')

        # Make the POST request with new password data
        response_post = self.client.post(url, {
            'password': 'newpassword1234',
            'password_confirmation': 'newpassword1234'
        }, follow = True)
        
        # Assert the final response is 200
        self.assertEqual(response_post.status_code, 200)
        
        # Reload the user's profile from the database to get updated values
        self.user_confirmed.userprofile.refresh_from_db()

        # Make the GET request again (re-using the link)
        response_reuse = self.client.get(url)
        
        # Extract messages from the response context after re-using the link
        messages_reuse = [str(message) for message in get_messages(response_reuse.wsgi_request)]

        # Directly assert that the expected error message is in the list of messages
        expected_error_message = 'Invalid or expired token. Please log in or request a new password reset email.'
        self.assertIn(expected_error_message, messages_reuse, f"Expected error message '{expected_error_message}' not found in response messages after re-using the link: {messages_reuse}")
    
        # Check that the response redirects to the login page after re-using the link
        self.assertRedirects(response_reuse, reverse('users:login'))


    # Test 51: Expired token
    @patch('django.contrib.auth.tokens.PasswordResetTokenGenerator.check_token')
    def test_users_password_reset_confirmation_expired_token(self, mock_check_token):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Mock the check_token method to return False, simulating an expired token
        mock_check_token.return_value = False

        # Create a token for the user (this token will be treated as expired due to the mocked check_token method)
        token = default_token_generator.make_token(self.user_confirmed)
        uid = urlsafe_base64_encode(force_bytes(self.user_confirmed.email))

        # Construct the URL with the token and uid
        url = reverse('users:password_reset_confirmation') + f'?token={token}&email={uid}'

        # Make the GET request to the password reset confirmation view
        response = self.client.get(url, follow=True)

        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Invalid or expired token. Please log in or request a new password reset email.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'users/login.html')
        
    
    #---------------------------------------------------------------------------


    # Tests for profile_view:

    # Returns 200
    # Happy path a: no user input
    # Happy path b: user input
    # Missing CSRF
    # Unauthenticated user
    # accounting_method is something other than 'LIFO' or 'FIFO'
    # tax_rate_STCG is < 0
    # tax_rate_STCG is > 50%
    # tax_rate_LTCG is < 0
    # tax_rate_LTCG is > 50%
    # SQL injection attempt for password
    # HTML/JS injection attempt for password
    
    # Test 52: Returns 200
    def test_users_profile_200(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, "Logging in user_confirmed failed")

        # Access password_change
        response = self.client.get(reverse('users:profile'), follow=False)  # Use 'login' as your named URL pattern
        
        if response.status_code in [301, 302]:
            logger.debug(f'running users/tests.py, test { test_number } ... redirected to URL: {response.url}')
        
        self.assertEqual(response.status_code, 200)

    
    # Test 53: Happy path a: no user input
    def test_users_profile_happy_path_a(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, "Logging in user_confirmed failed")

        # Save the old user and user profile
        user_old = User.objects.get(username=self.user_confirmed.username)
        userprofile_old = UserProfile.objects.get(user=self.user_confirmed)
        
        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:profile'), {
            'first_name': ' ',
            'last_name': ' ',
            'username': '',
            'accounting_method': 'FIFO',
            'tax_loss_offsets': 'On',
            'tax_rate_STCG': 30,
            'tax_rate_LTCG': 15
        }, follow = True)
        
        # Fetch the updated user and user profile
        self.user_confirmed.refresh_from_db()
        userprofile_updated = UserProfile.objects.get(user=self.user_confirmed)

        # Compare the old and updated user attributes
        self.assertEqual(user_old.first_name, self.user_confirmed.first_name)
        self.assertEqual(user_old.last_name, self.user_confirmed.last_name)
        self.assertEqual(user_old.username, self.user_confirmed.username)
        self.assertEqual(user_old.email, self.user_confirmed.email)
        self.assertEqual(user_old.password, self.user_confirmed.password)

        # Compare the old and updated user profiles
        self.assertEqual(userprofile_old.cash_initial, userprofile_updated.cash_initial)
        self.assertEqual(userprofile_old.cash, userprofile_updated.cash)
        self.assertEqual(userprofile_old.accounting_method, userprofile_updated.accounting_method)
        self.assertEqual(userprofile_old.tax_loss_offsets, userprofile_updated.tax_loss_offsets)
        self.assertEqual(userprofile_old.tax_rate_STCG, userprofile_updated.tax_rate_STCG)
        self.assertEqual(userprofile_old.tax_rate_LTCG, userprofile_updated.tax_rate_LTCG)
        
        # Assert the final response is 200
        self.assertEqual(response.status_code, 200)
        
        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'You have successfully updated your profile.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'brokerage/index.html')


    # Test 54: Happy path b: user input
    def test_users_profile_happy_path_b(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, 'Logging in user_confirmed')

        # Save the old user and user profile
        user_old = User.objects.get(username=self.user_confirmed.username)
        userprofile_old = UserProfile.objects.get(user=self.user_confirmed)
        
        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:profile'), {
            'first_name': 'Newfirst',
            'last_name': 'Newlast',
            'username': 'newusername',
            'accounting_method': 'LIFO',
            'tax_loss_offsets': 'Off',
            'tax_rate_STCG': 45,
            'tax_rate_LTCG': 45
        }, follow = True)
        
        # Fetch the updated user and user profile
        self.user_confirmed.refresh_from_db()
        userprofile_updated = UserProfile.objects.get(user=self.user_confirmed)

        # Compare the old and updated user attributes
        self.user_confirmed.first_name = 'Newfirst'
        self.user_confirmed.last_name = 'Newlast'
        self.user_confirmed.username = 'newusername'
        self.assertEqual(user_old.email, self.user_confirmed.email)
        self.assertEqual(user_old.password, self.user_confirmed.password)

        # Compare the old and updated user profiles
        self.assertEqual(userprofile_old.cash_initial, userprofile_updated.cash_initial)
        self.assertEqual(userprofile_old.cash, userprofile_updated.cash)
        userprofile_updated.accounting_method = 'LIFO'
        userprofile_updated.tax_loss_offsets = 'Off'
        userprofile_updated.tax_rate_STCG = 45
        userprofile_updated.tax_rate_LTCG = 45
        
        # Assert the final response is 200
        self.assertEqual(response.status_code, 200)
        
        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'You have successfully updated your profile.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'brokerage/index.html')

    
    # Test 55: Missing CSRF
    def test_users_profile_missing_csrf(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, "Logging in user_confirmed failed")

        # Initialize the Django test client
        client = Client(enforce_csrf_checks=True)  # This enforces CSRF checks
        
        # Visits /register/ and submits valid data
        register_url = reverse('users:profile')
        logger.debug(f'running users/tests.py, test { test_number } ... register URL is: {register_url}')

        # Post without following redirects to check the immediate response
        response = client.post(register_url, {
            'first_name': 'Newfirst',
            'last_name': 'Newlast',
            'username': 'newusername',
            'accounting_method': 'LIFO',
            'tax_loss_offsets': 'Off',
            'tax_rate_STCG': 45,
            'tax_rate_LTCG': 45
        }, follow = True)
        
        # Assert the final response is 403: forbidden
        self.assertEqual(response.status_code, 403)

    
    # Test 56: Unauthenticated user
    def test_users_profile_unauthenticated_user(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:profile'), {
            'first_name': 'Newfirst',
            'last_name': 'Newlast',
            'username': 'newusername',
            'accounting_method': 'LIFO',
            'tax_loss_offsets': 'Off',
            'tax_rate_STCG': 45,
            'tax_rate_LTCG': 45
        }, follow = True)
        
        # Check for the initial redirect
        self.assertEqual(response.status_code, 200)
        
        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'users/login.html')


    # Test 57: accounting_method is something other than 'LIFO' or 'FIFO'
    def test_users_profile_accounting_method_not_LIFO_not_FIFO(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, "Logging in user_confirmed failed")

        # Save the old user and user profile
        user_old = User.objects.get(username=self.user_confirmed.username)
        userprofile_old = UserProfile.objects.get(user=self.user_confirmed)
        
        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:profile'), {
            'first_name': 'Newfirst',
            'last_name': 'Newlast',
            'username': 'newusername',
            'accounting_method': 'Other', # Invalid input
            'tax_loss_offsets': 'Off',
            'tax_rate_STCG': 45,
            'tax_rate_LTCG': 45
        }, follow = True)
                
        # Assert the final response is 200
        self.assertEqual(response.status_code, 200)
        
        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid input. Please see the red text below for assistance.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'users/profile.html')


    # Test 58: tax_rate_STCG is < 0
    def test_users_profile_tax_rate_STCG_is_negative(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, "Logging in user_confirmed failed")

        # Save the old user and user profile
        user_old = User.objects.get(username=self.user_confirmed.username)
        userprofile_old = UserProfile.objects.get(user=self.user_confirmed)
        
        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:profile'), {
            'first_name': 'Newfirst',
            'last_name': 'Newlast',
            'username': 'newusername',
            'accounting_method': 'LIFO', # Invalid input
            'tax_loss_offsets': 'Off',
            'tax_rate_STCG': -45,
            'tax_rate_LTCG': 45
        }, follow = True)
                
        # Assert the final response is 200
        self.assertEqual(response.status_code, 200)
        
        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid input. Please see the red text below for assistance.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'users/profile.html')


    # Test 59: tax_rate_STCG is > 50%
    def test_users_profile_tax_rate_STCG_too_high(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, "Logging in user_confirmed failed")

        # Save the old user and user profile
        user_old = User.objects.get(username=self.user_confirmed.username)
        userprofile_old = UserProfile.objects.get(user=self.user_confirmed)
        
        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:profile'), {
            'first_name': 'Newfirst',
            'last_name': 'Newlast',
            'username': 'newusername',
            'accounting_method': 'LIFO', # Invalid input
            'tax_loss_offsets': 'Off',
            'tax_rate_STCG': 95,
            'tax_rate_LTCG': 45
        }, follow = True)
                
        # Assert the final response is 200
        self.assertEqual(response.status_code, 200)
        
        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid input. Please see the red text below for assistance.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'users/profile.html')
    
    
    # Test 60: tax_rate_LTCG is < 0
    def test_users_profile_tax_rate_LTCG_is_negative(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, "Logging in user_confirmed failed")

        # Save the old user and user profile
        user_old = User.objects.get(username=self.user_confirmed.username)
        userprofile_old = UserProfile.objects.get(user=self.user_confirmed)
        
        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:profile'), {
            'first_name': 'Newfirst',
            'last_name': 'Newlast',
            'username': 'newusername',
            'accounting_method': 'LIFO', # Invalid input
            'tax_loss_offsets': 'Off',
            'tax_rate_STCG': 45,
            'tax_rate_LTCG': -45
        }, follow = True)
                
        # Assert the final response is 200
        self.assertEqual(response.status_code, 200)
        
        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid input. Please see the red text below for assistance.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'users/profile.html')


    # Test 61: tax_rate_LTCG is > 50%
    def test_users_profile_tax_rate_LTCG_too_high(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, "Logging in user_confirmed failed")

        # Save the old user and user profile
        user_old = User.objects.get(username=self.user_confirmed.username)
        userprofile_old = UserProfile.objects.get(user=self.user_confirmed)
        
        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:profile'), {
            'first_name': 'Newfirst',
            'last_name': 'Newlast',
            'username': 'newusername',
            'accounting_method': 'LIFO', # Invalid input
            'tax_loss_offsets': 'Off',
            'tax_rate_STCG': 45,
            'tax_rate_LTCG': 95
        }, follow = True)
                
        # Assert the final response is 200
        self.assertEqual(response.status_code, 200)
        
        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid input. Please see the red text below for assistance.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'users/profile.html')


    # Test 62: SQL injection attempt for first_name
    def test_users_profile_SQL_injection_to_password(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, "Logging in user_confirmed failed")

        # Save the old user and user profile
        user_old = User.objects.get(username=self.user_confirmed.username)
        userprofile_old = UserProfile.objects.get(user=self.user_confirmed)
        
        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:profile'), {
            'first_name': malicious_sql_code,
            'last_name': 'Newlast',
            'username': 'newusername',
            'accounting_method': 'LIFO', # Invalid input
            'tax_loss_offsets': 'Off',
            'tax_rate_STCG': 45,
            'tax_rate_LTCG': 45
        }, follow = True)
                
        # Assert the final response is 200
        self.assertEqual(response.status_code, 200)
        
        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid input. Please see the red text below for assistance.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'users/profile.html')


    # Test 63: HTML/JS injection attempt for first_name
    def test_users_profile_HTML_injection_to_password(self):
        global test_number
        test_number += 1
        logger.debug(f'running users/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, "Logging in user_confirmed failed")

        # Save the old user and user profile
        user_old = User.objects.get(username=self.user_confirmed.username)
        userprofile_old = UserProfile.objects.get(user=self.user_confirmed)
        
        # Post without following redirects to check the immediate response
        response = self.client.post(reverse('users:profile'), {
            'first_name': malicious_html_code,
            'last_name': 'Newlast',
            'username': 'newusername',
            'accounting_method': 'LIFO', # Invalid input
            'tax_loss_offsets': 'Off',
            'tax_rate_STCG': 45,
            'tax_rate_LTCG': 45
        }, follow = True)
                
        # Assert the final response is 200
        self.assertEqual(response.status_code, 200)
        
        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid input. Please see the red text below for assistance.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'users/profile.html')
 