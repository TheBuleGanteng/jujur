from bs4 import BeautifulSoup  # Import BeautifulSoup for parsing HTML
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
from .helpers import *
import logging
from .models import Listing, Transaction
from users.models import UserProfile
import re
from unittest.mock import patch


User = get_user_model()
logger = logging.getLogger('django')



# Define global variables here:
password_correct = 'abc123'
password_incorrect = 'abc1234'

email_correct_confirmed = 'confirmed@mattmcdonnell.net'
email_correct_unconfirmed = 'unconfirmed@mattmcdonnell.net'
email_incorrect = 'wrongemail@mattmcdonnell.net'

test_number = 0
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
        logger.debug(f'running brokerage/tests.py, setup ... user_confirmed created: {self.user_confirmed.username}, Email: {self.user_confirmed.email}, Active: {self.user_confirmed.is_active}') 
        # Test authenticating confirmed user
        authenticated_user = authenticate(username=email_correct_confirmed, password=password_correct)
        logger.debug(f'running brokerage/tests.py, setup ... user_confirmed Authentication Success: {authenticated_user is not None}')


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
        logger.debug(f'running brokerage/tests.py, setup ... unconfirmed user created: {self.user_unconfirmed.username}, Email: {self.user_unconfirmed.email}, Active: {self.user_unconfirmed.is_active}') 
        
        # Test authenticating unconfirmed user
        authenticated_user = authenticate(email=email_correct_unconfirmed, password=password_correct)
        logger.debug(f'running brokerage/tests.py, setup ... user_unconfirmed Authentication Success: {authenticated_user is not None}')

        # Create listings for AAPL and GOOG ( needed for check_valid_shares() )
        Listing.objects.create(
            symbol='AAPL',
            name='Apple, Inc.',
            price=100.00,
            exchange='NASDAQ Global Select',
            exchange_short='NASDAQ',
            listing_type='Stock',
        )
        logger.debug(f'running brokerage/tests.py, setup ... created listing object for AAPL')
        
        Listing.objects.create(
            symbol='GOOG',
            name='Alphabet Inc.',
            price=100.00,
            exchange='NASDAQ Global Select',
            exchange_short='NASDAQ',
            listing_type='Stock',
        )
        logger.debug(f'running brokerage/tests.py, setup ... created listing object for GOOG')

        Listing.objects.create(
            symbol='TSLA',
            name='Tesla Inc.',
            price=100.00,
            exchange='NASDAQ Global Select',
            exchange_short='NASDAQ',
            listing_type='Stock',
        )
        logger.debug(f'running brokerage/tests.py, setup ... created listing object for TSLA')

    def tearDown(self):
        # Stop patching 'users.views.send_email'
        patch.stopall()


    def extract_shares(self, soup, symbol):
            """Extracts shares from the response using BeautifulSoup based on the symbol."""
            # Find table row by symbol
            symbol_tag = soup.find('a', href=f"/quote?symbol={symbol}")
            if symbol_tag:
                row = symbol_tag.find_parent('tr')
                shares_cell = row.find_all('td')[1]  # Assuming the second column is shares
                return int(shares_cell.text.strip())
            return None


    #---------------------------------------------------------------------------

    """
    # Tests for index_view:
    # 1: /index/ returns status 200 if user is logged in
    # 2: /index/ returns status 302 if user is not logged in
    # 3: Clicking on a symbol directs the user to the profile for that symbol
    # 4: A random symbol is not present on index.html
    # 5: If a user sells all the shares in a given stock, that symbol is no longer visible on index.html
    # 6: If a user sells some, but not all of the shares in a given stock, that symbol remains visible on index.html
    # 7: If a user buys shares in a stock already owned, the number of shares owned on index.html is incremented appropriately.

    
    # index_view Test 1: index.html returns code 200
    def test_brokerage_index_200(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Access index
        response = self.client.get(reverse('brokerage:index'), follow=False)  # Use 'login' as your named URL pattern
        
        if response.status_code in [301, 302]:
            logger.debug(f'running brokerage/tests.py, test { test_number } ... redirected to URL: {response.url}')
        
        self.assertEqual(response.status_code, 200)

    
    # index_view Test 2: index.html returns code 302 if user is not logged in
    def test_brokerage_index_302(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Access index
        response = self.client.get(reverse('brokerage:index'), follow=False)  # Use 'login' as your named URL pattern
        
        if response.status_code in [200]:
            logger.debug(f'running brokerage/tests.py, test { test_number } ... redirected to URL: {response.url}')
        
        self.assertEqual(response.status_code, 302)


    # index_view Test 3: Symbols are clickable links on index.html
    def test_brokerage_index_contains_clickable_link(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Simulate navigating to buy page
        self.client.get(reverse('brokerage:buy'), follow=True)

        # Perform purchase of TSLA shares
        self.client.post(
            reverse('brokerage:buy'), 
            {
                'symbol': 'TSLA',
                'shares': 10,
                'transaction_type': 'BOT'
            }, follow=True
        )
        
        # Access index and ensure it contains a link for a stock already owned.
        response = self.client.get(reverse('brokerage:index'), follow=False)  # Use 'login' as your named URL pattern
        self.assertContains(response, 'href="/quote?symbol=TSLA"')
        
        # Follow the link to the quote page and ensure it loads properly (simulates clicking the link)
        response = self.client.get('https://127.0.0.1:8080/quote/?symbol=AAPL', follow=True)
        self.assertEqual(response.status_code, 200)

        # Ensure the response uses the correct template
        self.assertTemplateUsed(response, 'brokerage/quoted.html')
    

    # index_view Test 4: A random symbol not in the user's portfolio is not present on index.html
    def test_brokerage_index_does_not_contain_invalid_symbol(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Access index and check there isn't a link for a stock not owned
        response = self.client.get(reverse('brokerage:index'), follow=False)  # Use 'login' as your named URL pattern
        self.assertNotContains(response, 'href="/quote?symbol=MMM"')


    # index_view Test 5: If a user sells all the shares in a given stock, that symbol is no longer visible on index.html
    def test_brokerage_index_does_not_contain_symbol_when_shares_are_sold(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Simulate navigating to buy page
        self.client.get(reverse('brokerage:buy'), follow=True)

        # Perform purchase of TSLA shares
        self.client.post(
            reverse('brokerage:buy'), 
            {
                'symbol': 'TSLA',
                'shares': 10,
                'transaction_type': 'BOT'
            }, follow=True
        )
        
        # Simulate navigating to index page to update the portfolio after buying shares
        response = self.client.get(reverse('brokerage:index'), follow=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        initial_shares = self.extract_shares(soup, 'TSLA')
        logger.debug(f'Initial shares for TSLA: {initial_shares}')
        self.assertEqual(initial_shares, 10, "Initial shares should be 10")
        
        # Simulate navigating to sell page
        self.client.get(reverse('brokerage:sell'), follow=True)

        # Perform sale of all TSLA shares
        self.client.post(
            reverse('brokerage:sell'), 
            {
                'symbol': 'TSLA',
                'shares': 10,
                'transaction_type': 'SLD'
            }, follow=True
        )

        # Simulate navigating to index page to update the portfolio after selling shares
        response = self.client.get(reverse('brokerage:index'), follow=True)
        self.assertNotContains(response, 'href="/quote?symbol=TSLA"')


    # index_view Test 6: If a user sells some, but not all of the shares in a given stock, that symbol remains visible on index.html
    def test_brokerage_index_decrements_shares_when_shares_are_sold(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Simulate navigating to buy page
        self.client.get(reverse('brokerage:buy'), follow=True)

        # Perform purchase of TSLA shares
        self.client.post(
            reverse('brokerage:buy'), 
            {
                'symbol': 'TSLA',
                'shares': 10,
                'transaction_type': 'BOT'
            }, follow=True
        )
        
        # Simulate navigating to index page to update the portfolio after buying shares
        response = self.client.get(reverse('brokerage:index'), follow=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        initial_shares = self.extract_shares(soup, 'TSLA')
        logger.debug(f'Initial shares for TSLA: {initial_shares}')
        self.assertEqual(initial_shares, 10, 'Initial shares should be 10')

        # Simulate navigating to sell page
        self.client.get(reverse('brokerage:sell'), follow=True)

        # Perform sale of 5 TSLA shares
        self.client.post(
            reverse('brokerage:sell'), 
            {
                'symbol': 'TSLA',
                'shares': 5,
                'transaction_type': 'SLD'
            }, follow=True
        )

        # Simulate navigating to index page to update the portfolio after buying shares
        response = self.client.get(reverse('brokerage:index'), follow=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        post_sale_shares = self.extract_shares(soup, 'TSLA')
        logger.debug(f'Post-sale for TSLA: { post_sale_shares }')
        self.assertEqual(post_sale_shares, 5, 'post_sale_shares shares should be 5')


    # index_view Test 7: If a user buys shares in a stock already owned, the number of shares owned on index.html is incremented appropriately. 
    def test_brokerage_index_increments_shares_when_shares_are_purchased(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Simulate navigating to buy page
        self.client.get(reverse('brokerage:buy'), follow=True)

        # Perform purchase of TSLA shares
        self.client.post(
            reverse('brokerage:buy'), 
            {
                'symbol': 'TSLA',
                'shares': 10,
                'transaction_type': 'BOT'
            }, follow=True
        )
        
        # Simulate navigating to index page to update the portfolio after buying shares
        response = self.client.get(reverse('brokerage:index'), follow=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        initial_shares = self.extract_shares(soup, 'TSLA')
        logger.debug(f'Initial shares for TSLA: {initial_shares}')
        self.assertEqual(initial_shares, 10, 'Initial shares should be 10')

        # Simulate navigating to buy page
        self.client.get(reverse('brokerage:buy'), follow=True)

        # Perform purchase of TSLA shares
        self.client.post(
            reverse('brokerage:buy'), 
            {
                'symbol': 'TSLA',
                'shares': 5,
                'transaction_type': 'BOT'
            }, follow=True
        )

        # Simulate navigating to index page to update the portfolio after buying shares
        response = self.client.get(reverse('brokerage:index'), follow=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        initial_shares = self.extract_shares(soup, 'TSLA')
        logger.debug(f'Initial shares for TSLA: {initial_shares}')
        self.assertEqual(initial_shares, 15, 'Initial shares should be 15')


#---------------------------------------------------------------------------


# Tests for buy_view:
    # Test 8: /buy/ returns status 200 if user is logged in
    # Test 9: /buy/ returns status 302 if user is not logged in
    # Test 10: Happy path: buy
    # Test 11: Submission with missing CSRF results in code 400
    # Test 12: Does not permit purchases if symbol is invalid
    # Test 13: Does not permit purchases if txn amount > cash
    # Test 14: Does not allow for negative share amounts
    # Test 15: Does not allow for non-integer share amounts
    # Test 16: SQL injection attempt for symbol
    # Test 17: HTML/JS injection attempt for symbol
    # Test 18: SQL injection attempt for shares
    # Test 19: HTML/JS injection attempt for shares

    # buy_view Test 8. /buy/ returns status 200 if user is logged in
    def test_brokerage_buy_result_in_200_if_logged_in(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Access index
        response = self.client.get(reverse('brokerage:buy'), follow=False)  # Use 'login' as your named URL pattern
        
        if response.status_code in [301, 302]:
            logger.debug(f'running brokerage/tests.py, test { test_number } ... redirected to URL: {response.url}')
        
        self.assertEqual(response.status_code, 200)

    
    # buy_view Test 9: returns code 302 if user is not logged in
    def test_brokerage_buy_302_if_not_logged_in(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Access index
        response = self.client.get(reverse('brokerage:buy'), follow=False)  # Use 'login' as your named URL pattern
        
        if response.status_code in [200]:
            logger.debug(f'running brokerage/tests.py, test { test_number } ... redirected to URL: {response.url}')
        
        self.assertEqual(response.status_code, 302)

    
    # buy_view Test 10: buy: happy path
    def test_brokerage_buy_happy_path(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Simulate navigating to buy page
        self.client.get(reverse('brokerage:buy'), follow=True)

        # Perform purchase of TSLA shares
        self.client.post(
            reverse('brokerage:buy'), 
            {
                'symbol': 'TSLA',
                'shares': 10,
                'transaction_type': 'BOT'
            }, follow=True
        )
        
        # Simulate navigating to index page to update the portfolio after buying shares
        response = self.client.get(reverse('brokerage:index'), follow=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        initial_shares = self.extract_shares(soup, 'TSLA')
        logger.debug(f'Initial shares for TSLA: {initial_shares}')
        self.assertEqual(initial_shares, 10, 'Initial shares should be 10')

    
    # buy_view Test 11: Submission with missing CSRF results in code 400
    def test_brokerage_buy_missing_CSRF(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Initialize the Django test client
        client = Client(enforce_csrf_checks=True)  # This enforces CSRF checks

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Visits /buy/ and submits valid data
        buy_url = reverse('brokerage:buy')
        logger.debug(f'running users/tests.py, test { test_number } ... buy URL is: {buy_url}')

        # Perform purchase of TSLA shares
        response = client.post(
            buy_url, 
            {
                'symbol': 'TSLA',
                'shares': 10,
                'transaction_type': 'BOT'
            }, follow=True
        )

        # Assert the final response is 403: forbidden
        self.assertEqual(response.status_code, 403)
        
    
    # buy_view Test 12: Does not permit purchases if symbol is invalid
    def test_brokerage_buy_invalid_symbol(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Simulate navigating to buy page
        self.client.get(reverse('brokerage:buy'), follow=True)

        # Perform purchase of TSLA shares
        response = self.client.post(
            reverse('brokerage:buy'), 
            {
                'symbol': 'InvalidSymbol',
                'shares': 10,
                'transaction_type': 'BOT'
            }, follow=True
        )

        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: invalid symbol. Please enter a valid symbol and try again.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'brokerage/buy.html')


    # buy_view Test 13: Does not permit purchases if txn amount > cash
    def test_brokerage_buy_insufficient_cash(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Simulate navigating to buy page
        self.client.get(reverse('brokerage:buy'), follow=True)

        # Perform purchase of TSLA shares
        response = self.client.post(
            reverse('brokerage:buy'), 
            {
                'symbol': 'TSLA',
                'shares': 1000,
                'transaction_type': 'BOT'
            }, follow=True
        )

        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_phrase = 'Insufficient funds.'
        contains_phrase = any(expected_phrase in message for message in messages)
        self.assertTrue(contains_phrase, f"Expected phrase '{expected_phrase}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'brokerage/buy.html')


    # buy_view Test 14: Does not allow for negative share amounts
    def test_brokerage_buy_negative_shares(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Simulate navigating to buy page
        self.client.get(reverse('brokerage:buy'), follow=True)

        # Perform purchase of TSLA shares
        response = self.client.post(
            reverse('brokerage:buy'), 
            {
                'symbol': 'TSLA',
                'shares': -10,
                'transaction_type': 'BOT'
            }, follow=True
        )

        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_phrase = 'Error: Invalid input. Please see the red text below for assistance.'
        contains_phrase = any(expected_phrase in message for message in messages)
        self.assertTrue(contains_phrase, f"Expected phrase '{expected_phrase}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'brokerage/buy.html')


    # buy_view Test 15: Does not allow for non-integer share amounts
    def test_brokerage_buy_non_integer_shares(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Simulate navigating to buy page
        self.client.get(reverse('brokerage:buy'), follow=True)

        # Perform purchase of TSLA shares
        response = self.client.post(
            reverse('brokerage:buy'), 
            {
                'symbol': 'TSLA',
                'shares': 5.5,
                'transaction_type': 'BOT'
            }, follow=True
        )

        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid input. Please see the red text below for assistance.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'brokerage/buy.html')
    

    # buy_view Test 16: SQL injection attempt for symbol
    def test_brokerage_buy_sql_injection_to_symbol(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Simulate navigating to buy page
        self.client.get(reverse('brokerage:buy'), follow=True)

        # Perform purchase of TSLA shares
        response = self.client.post(
            reverse('brokerage:buy'), 
            {
                'symbol': malicious_sql_code,
                'shares': 10,
                'transaction_type': 'BOT'
            }, follow=True
        )

        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: invalid symbol. Please enter a valid symbol and try again.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'brokerage/buy.html')


    # buy_view Test 17: HTML/JS injection attempt for symbol
    def test_brokerage_buy_html_injection_to_symbol(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Simulate navigating to buy page
        self.client.get(reverse('brokerage:buy'), follow=True)

        # Perform purchase of TSLA shares
        response = self.client.post(
            reverse('brokerage:buy'), 
            {
                'symbol': malicious_html_code,
                'shares': 10,
                'transaction_type': 'BOT'
            }, follow=True
        )

        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: invalid symbol. Please enter a valid symbol and try again.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'brokerage/buy.html')


    # buy_view Test 18: SQL injection attempt for shares
    def test_brokerage_buy_sql_injection_to_shares(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Simulate navigating to buy page
        self.client.get(reverse('brokerage:buy'), follow=True)

        # Perform purchase of TSLA shares
        response = self.client.post(
            reverse('brokerage:buy'), 
            {
                'symbol': 'TSLA',
                'shares': malicious_sql_code,
                'transaction_type': 'BOT'
            }, follow=True
        )

        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid input. Please see the red text below for assistance.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'brokerage/buy.html')


    # buy_view Test 19: HTML injection attempt for shares
    def test_brokerage_buy_html_injection_to_shares(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Simulate navigating to buy page
        self.client.get(reverse('brokerage:buy'), follow=True)

        # Perform purchase of TSLA shares
        response = self.client.post(
            reverse('brokerage:buy'), 
            {
                'symbol': 'TSLA',
                'shares': malicious_html_code,
                'transaction_type': 'BOT'
            }, follow=True
        )

        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid input. Please see the red text below for assistance.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'brokerage/buy.html')
    
    
#-------------------------------------------------------------------------------------

# Tests for sell_view:
    # Test 20: /sell/ returns status 200 if user is logged in
    # Test 21: /sell/ returns status 302 if user is not logged in
    # Test 22: Happy path: sell
    # Test 23: Submission with missing CSRF results in code 400
    # Test 24: Does not permit sale if symbol is invalid
    # Test 25: Does not permit sale if txn shares > shares held
    # Test 26: Does not allow for negative share amounts
    # Test 27: Does not allow for non-integer share amounts
    # Test 28: SQL injection attempt for symbol
    # Test 29: HTML/JS injection attempt for symbol
    # Test 30: SQL injection attempt for shares
    # Test 31: HTML/JS injection attempt for shares


    # buy_view Test 20. /sell/ returns status 200 if user is logged in
    def test_brokerage_sell_result_in_200_if_logged_in(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)  # Use the password you used to create the user_confirmed in setUp
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Access index
        response = self.client.get(reverse('brokerage:sell'), follow=False)  # Use 'login' as your named URL pattern
        
        if response.status_code in [301, 302]:
            logger.debug(f'running brokerage/tests.py, test { test_number } ... redirected to URL: {response.url}')
        
        self.assertEqual(response.status_code, 200)

    
    # buy_view Test 21: index.html returns code 302 if user is not logged in
    def test_brokerage_sell_302_if_not_logged_in(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Access index
        response = self.client.get(reverse('brokerage:sell'), follow=False)  # Use 'login' as your named URL pattern
        
        if response.status_code in [200]:
            logger.debug(f'running brokerage/tests.py, test { test_number } ... redirected to URL: {response.url}')
        
        self.assertEqual(response.status_code, 302)


    # buy_view Test 22: sell happy path
    def test_brokerage_sell_happy_path(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Simulate navigating to buy page
        self.client.get(reverse('brokerage:buy'), follow=True)

        # Perform purchase of TSLA shares
        self.client.post(
            reverse('brokerage:buy'), 
            {
                'symbol': 'TSLA',
                'shares': 10,
                'transaction_type': 'BOT'
            }, follow=True
        )
        
        # Simulate navigating to index page to update the portfolio after buying shares
        response = self.client.get(reverse('brokerage:index'), follow=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        initial_shares = self.extract_shares(soup, 'TSLA')
        logger.debug(f'Initial shares for TSLA: {initial_shares}')
        self.assertEqual(initial_shares, 10, 'Initial shares should be 10')

        # Perform sale of TSLA shares
        self.client.post(
            reverse('brokerage:sell'), 
            {
                'symbol': 'TSLA',
                'shares': 5,
                'transaction_type': 'SLD'
            }, follow=True
        )
        
        # Simulate navigating to index page to update the portfolio after buying shares
        response = self.client.get(reverse('brokerage:index'), follow=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        initial_shares = self.extract_shares(soup, 'TSLA')
        logger.debug(f'Initial shares for TSLA: {initial_shares}')
        self.assertEqual(initial_shares, 5, 'Initial shares should be 5')

    
    # buy_view Test 23: Submission with missing CSRF results in code 400
    def test_brokerage_sell_missing_CSRF(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Initialize the Django test client
        client = Client(enforce_csrf_checks=True)  # This enforces CSRF checks

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Perform purchase of TSLA shares
        self.client.post(
            reverse('brokerage:buy'), 
            {
                'symbol': 'TSLA',
                'shares': 10,
                'transaction_type': 'BOT'
            }, follow=True
        )
        
        # Simulate navigating to index page to update the portfolio after buying shares
        response = self.client.get(reverse('brokerage:index'), follow=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        initial_shares = self.extract_shares(soup, 'TSLA')
        logger.debug(f'Initial shares for TSLA: {initial_shares}')
        self.assertEqual(initial_shares, 10, 'Initial shares should be 10')
        
        # Visits /sell/ and submits valid data
        sell_url = reverse('brokerage:sell')
        logger.debug(f'running users/tests.py, test { test_number } ... URL is: {sell_url}')

        # Perform purchase of TSLA shares
        response = client.post(
            sell_url, 
            {
                'symbol': 'TSLA',
                'shares': 5,
                'transaction_type': 'SLD'
            }, follow=True
        )

        # Assert the final response is 403: forbidden
        self.assertEqual(response.status_code, 403)
    """

    # buy_view Test 24: Does not permit sale if symbol is invalid
    def test_brokerage_sell_invalid_symbol(self):
        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Simulate navigating to buy page
        self.client.get(reverse('brokerage:buy'), follow=True)

        # Perform purchase of TSLA shares
        self.client.post(
            reverse('brokerage:buy'), 
            {
                'symbol': 'TSLA',
                'shares': 10,
                'transaction_type': 'BOT'
            }, follow=True
        )
        
        # Simulate navigating to index page to update the portfolio after buying shares
        response = self.client.get(reverse('brokerage:index'), follow=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        initial_shares = self.extract_shares(soup, 'TSLA')
        logger.debug(f'Initial shares for TSLA: {initial_shares}')
        self.assertEqual(initial_shares, 10, 'Initial shares should be 10')

        # Simulate navigating to sell page
        self.client.get(reverse('brokerage:sell'), follow=True)

        # Perform sale of 5 TSLA shares
        response = self.client.post(
            reverse('brokerage:sell'), 
            {
                'symbol': 'InvalidSymbol',
                'shares': 5,
                'transaction_type': 'SLD'
            }, follow=True
        )

        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid input. Please see the red text below for assistance.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'brokerage/sell.html')


    # buy_view Test 25: Does not permit sale if txn shares > shares held
    def test_brokerage_sell_insufficient_shares_held(self):
        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Simulate navigating to buy page
        self.client.get(reverse('brokerage:buy'), follow=True)

        # Perform purchase of TSLA shares
        self.client.post(
            reverse('brokerage:buy'), 
            {
                'symbol': 'TSLA',
                'shares': 10,
                'transaction_type': 'BOT'
            }, follow=True
        )
        
        # Simulate navigating to index page to update the portfolio after buying shares
        response = self.client.get(reverse('brokerage:index'), follow=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        initial_shares = self.extract_shares(soup, 'TSLA')
        logger.debug(f'Initial shares for TSLA: {initial_shares}')
        self.assertEqual(initial_shares, 10, 'Initial shares should be 10')

        # Simulate navigating to sell page
        self.client.get(reverse('brokerage:sell'), follow=True)

        # Perform sale of 5 TSLA shares
        response = self.client.post(
            reverse('brokerage:sell'), 
            {
                'symbol': 'TSLA',
                'shares': 15,
                'transaction_type': 'SLD'
            }, follow=True
        )

        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_phrase = 'exceeds the current total'
        contains_phrase = any(expected_phrase in message for message in messages)
        self.assertTrue(contains_phrase, f"Expected phrase '{expected_phrase}' not found in response messages: {messages}")
        
        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'brokerage/sell.html')

    
    # buy_view Test 26: Does not allow for negative share amounts
    def test_brokerage_sell_negative_shares(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Simulate navigating to buy page
        self.client.get(reverse('brokerage:buy'), follow=True)

        # Perform purchase of TSLA shares
        self.client.post(
            reverse('brokerage:buy'), 
            {
                'symbol': 'TSLA',
                'shares': 10,
                'transaction_type': 'BOT'
            }, follow=True
        )
        
        # Simulate navigating to index page to update the portfolio after buying shares
        response = self.client.get(reverse('brokerage:index'), follow=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        initial_shares = self.extract_shares(soup, 'TSLA')
        logger.debug(f'Initial shares for TSLA: {initial_shares}')
        self.assertEqual(initial_shares, 10, 'Initial shares should be 10')

        # Perform sale of TSLA shares
        response = self.client.post(
            reverse('brokerage:sell'), 
            {
                'symbol': 'TSLA',
                'shares': -5,
                'transaction_type': 'SLD'
            }, follow=True
        )
        
        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid input. Please see the red text below for assistance.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'brokerage/sell.html')


    # buy_view Test 27: Does not allow for non-integer share amounts
    def test_brokerage_sell_non_integer_shares(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Simulate navigating to buy page
        self.client.get(reverse('brokerage:buy'), follow=True)

        # Perform purchase of TSLA shares
        self.client.post(
            reverse('brokerage:buy'), 
            {
                'symbol': 'TSLA',
                'shares': 10,
                'transaction_type': 'BOT'
            }, follow=True
        )
        
        # Simulate navigating to index page to update the portfolio after buying shares
        response = self.client.get(reverse('brokerage:index'), follow=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        initial_shares = self.extract_shares(soup, 'TSLA')
        logger.debug(f'Initial shares for TSLA: {initial_shares}')
        self.assertEqual(initial_shares, 10, 'Initial shares should be 10')

        # Perform sale of TSLA shares
        response = self.client.post(
            reverse('brokerage:sell'), 
            {
                'symbol': 'TSLA',
                'shares': 5.5,
                'transaction_type': 'SLD'
            }, follow=True
        )
        
        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid input. Please see the red text below for assistance.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'brokerage/sell.html')


    # buy_view Test 28: SQL injection attempt for symbol
    def test_brokerage_sell_SQL_to_symbol(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Simulate navigating to buy page
        self.client.get(reverse('brokerage:buy'), follow=True)

        # Perform purchase of TSLA shares
        self.client.post(
            reverse('brokerage:buy'), 
            {
                'symbol': 'TSLA',
                'shares': 10,
                'transaction_type': 'BOT'
            }, follow=True
        )
        
        # Simulate navigating to index page to update the portfolio after buying shares
        response = self.client.get(reverse('brokerage:index'), follow=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        initial_shares = self.extract_shares(soup, 'TSLA')
        logger.debug(f'Initial shares for TSLA: {initial_shares}')
        self.assertEqual(initial_shares, 10, 'Initial shares should be 10')

        # Perform sale of TSLA shares
        response = self.client.post(
            reverse('brokerage:sell'), 
            {
                'symbol': malicious_sql_code,
                'shares': 5,
                'transaction_type': 'SLD'
            }, follow=True
        )
        
        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid input. Please see the red text below for assistance.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'brokerage/sell.html')

    
    # buy_view Test 29: HTML injection attempt for symbol
    def test_brokerage_sell_HTML_to_symbol(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Simulate navigating to buy page
        self.client.get(reverse('brokerage:buy'), follow=True)

        # Perform purchase of TSLA shares
        self.client.post(
            reverse('brokerage:buy'), 
            {
                'symbol': 'TSLA',
                'shares': 10,
                'transaction_type': 'BOT'
            }, follow=True
        )
        
        # Simulate navigating to index page to update the portfolio after buying shares
        response = self.client.get(reverse('brokerage:index'), follow=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        initial_shares = self.extract_shares(soup, 'TSLA')
        logger.debug(f'Initial shares for TSLA: {initial_shares}')
        self.assertEqual(initial_shares, 10, 'Initial shares should be 10')

        # Perform sale of TSLA shares
        response = self.client.post(
            reverse('brokerage:sell'), 
            {
                'symbol': malicious_html_code,
                'shares': 5,
                'transaction_type': 'SLD'
            }, follow=True
        )
        
        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid input. Please see the red text below for assistance.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'brokerage/sell.html')


    # buy_view Test 30: SQL injection attempt for symbol
    def test_brokerage_sell_SQL_to_shares(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Simulate navigating to buy page
        self.client.get(reverse('brokerage:buy'), follow=True)

        # Perform purchase of TSLA shares
        self.client.post(
            reverse('brokerage:buy'), 
            {
                'symbol': 'TSLA',
                'shares': 10,
                'transaction_type': 'BOT'
            }, follow=True
        )
        
        # Simulate navigating to index page to update the portfolio after buying shares
        response = self.client.get(reverse('brokerage:index'), follow=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        initial_shares = self.extract_shares(soup, 'TSLA')
        logger.debug(f'Initial shares for TSLA: {initial_shares}')
        self.assertEqual(initial_shares, 10, 'Initial shares should be 10')

        # Perform sale of TSLA shares
        response = self.client.post(
            reverse('brokerage:sell'), 
            {
                'symbol': 'TSLA',
                'shares': malicious_sql_code,
                'transaction_type': 'SLD'
            }, follow=True
        )
        
        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid input. Please see the red text below for assistance.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'brokerage/sell.html')

    
    # buy_view Test 31: HTML injection attempt for shares
    def test_brokerage_sell_HTML_to_shares(self):
        global test_number
        test_number += 1
        logger.debug(f'running brokerage/tests.py, test { test_number } ... starting test')

        # Log in the confirmed user
        login_successful = self.client.login(username=self.user_confirmed.username, password=password_correct)
        self.assertTrue(login_successful, "Logging in user_confirmed")

        # Simulate navigating to buy page
        self.client.get(reverse('brokerage:buy'), follow=True)

        # Perform purchase of TSLA shares
        self.client.post(
            reverse('brokerage:buy'), 
            {
                'symbol': 'TSLA',
                'shares': 10,
                'transaction_type': 'BOT'
            }, follow=True
        )
        
        # Simulate navigating to index page to update the portfolio after buying shares
        response = self.client.get(reverse('brokerage:index'), follow=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        initial_shares = self.extract_shares(soup, 'TSLA')
        logger.debug(f'Initial shares for TSLA: {initial_shares}')
        self.assertEqual(initial_shares, 10, 'Initial shares should be 10')

        # Perform sale of TSLA shares
        response = self.client.post(
            reverse('brokerage:sell'), 
            {
                'symbol': 'TSLA',
                'shares': malicious_html_code,
                'transaction_type': 'SLD'
            }, follow=True
        )
        
        # Extract messages from the response context
        messages = [str(message) for message in get_messages(response.wsgi_request)]

        # Directly assert that the expected message is in the list of messages
        expected_message = 'Error: Invalid input. Please see the red text below for assistance.'
        self.assertIn(expected_message, messages, f"Expected message '{expected_message}' not found in response messages: {messages}")

        # Check which template is used in the final response
        self.assertTemplateUsed(response, 'brokerage/sell.html')
