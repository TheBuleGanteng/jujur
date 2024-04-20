from datetime import datetime
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Case, Q, F, Func, Value, When
from django.db.models.functions import Length
import logging
from ..models import Listing, Transaction
import os
import requests
from users.models import UserProfile
logger = logging.getLogger('django')

__all__ = ['check_valid_shares', 'check_valid_symbol', 'company_data', 'fmp_key', 'process_buy', 'update_listings', 'reformat_usd']


# Pull company data via FMP API
def company_data(symbol):
    logger.debug(f'running get_stock_info(symbol): ... symbol is: { symbol }')
        
    try:
        limit = 1
        response = requests.get(f'https://financialmodelingprep.com/api/v3/profile/{symbol}?apikey={fmp_key}')       
        #increment_ping()
        logger.debug(f'running company_data(symbol): ... response is: { response }')
        data = response.json()
        
        # Check if data contains at least one item
        if data and isinstance(data, list):
            return data[0]
        else:
            return None

    except Exception as e:
        logger.debug(f'running company_data(symbol): ... function tried symbol: { symbol } but errored with error: { e }')
        return None


# Defines key for FMP api
fmp_key = os.getenv('FMP_API_KEY')


# Reformat argument as usd
def reformat_usd(value):
    """Format value as USD."""
    if value >= 0:
        return f"${value:,.2f}"
    else:
        return f"(${-value:,.2f})" 


# Checks if a user has sufficient cash to process a purchase or sufficient shares to process a sale
def check_valid_shares(shares, symbol, transaction_type, user):    

    # Instantiate the response that will be updated as needed throughout the function    
    response = {
        'success': False,
        'message': '',
        'data': {}
    }
    
    # Step 1: Check if shares is (a) an integer and (b) positive
    try:
        shares = int(shares)
        if shares < 0:
            logger.error(f'running brokerage app, check_valid_shares ... user entered negative value for shares: { shares }')
            response['message'] = 'Cannot enter a negative value for shares.'
            return response
    
        # Step 2: Pull user object for signed-in user from DB
        user_cash = user.userprofile.cash
        user_cash_reformatted = reformat_usd(user_cash)
        logger.debug(f'running brokerage app, check_valid_shares ... pulled user object: { user }')

        # Step 3: Query the API to get an updated price for symbol
        company_data_result = company_data(symbol)
        transaction_value_per_share = Decimal(company_data_result['price']).quantize(Decimal('0.01'))
        transaction_value_total = Decimal(shares) * transaction_value_per_share
        transaction_value_total_reformatted = reformat_usd(transaction_value_total)

        # Step 4: Commence logic if user is buying shares
        if transaction_type == 'BOT':    
            
            # Purchase fails due to insufficient cash
            if user_cash < transaction_value_total:
                logger.error(f'running brokerage app, check_valid_shares ... User has insufficient cash to complete purchase. Test failed.')
                response['message'] = f'Insufficient funds. Cash required of {transaction_value_total_reformatted} exceeds cash available of { user_cash_reformatted }.'

            # Purchase proceeds
            else:
                response['success'] = True
                response['message'] = f'User cash of { user_cash_reformatted } is sufficient to cover proposed purchase cost of { transaction_value_total_reformatted }'
                response['data'] = {
                    'transaction_value_per_share': transaction_value_per_share,
                    'transaction_value_total': transaction_value_total
                }

        # Step 6: Commence logic if user is selling shares
        elif transaction_type == 'SLD':
            logger.debug(f'running brokerage app, check_valid_shares ... user: {user} is trying to sell shares')
            
            # Step 6.1: Test if user has sufficient shares to sell
            total_shares_owned = Transaction.objects.filter(
                user=user,
                symbol=symbol,
                type='BOT'
            ).aggregate(total_shares=Sum('shares_outstanding'))['total_shares'] or 0
            
            # Step 6.2: User trying to sell more shares than owned. Sale fails.
            if shares > total_shares_owned: 
                logger.error(f'running brokerage app, check_valid_shares ... user: {user} entered more shares than owned: { total_shares_owned}. Test failed')
                result['message'] = f'User cannot sell { shares } shares, as it exceeds the current total of { total_shares_owned } shares.'

            # Step 6.3: Seller has sufficient shares to sell. Sale proceeds.
            else:
                result['success'] = True, 
                result['message'] = f'User able to sell { shares } shares from current total of { total_shares_owned } shares.' 
                response['data'] = {
                    'transaction_value_per_share': transaction_value_per_share,  
                    'transaction_value_total': transaction_value_total  
                }

    # If user didn't enter an integer for shares
    except ValueError:
        response['message'] = 'Non-integer value entered for shares.'
    
    # Catch-all for other errors
    except Exception as e:
        response['message'] = f'Unexpected error: {str(e)}'
        logger.error(f'Error in check_valid_shares: {e}')    

    return response


# Checks if a symbol is valid
def check_valid_symbol(symbol):
    print(f'running check_valid_symbol ... function started')
    print(f'running check_valid_symbol ... symbol is: { symbol }')

    try:
        # Determine the primary filter and ordering of results (limited to 5 items)
        if len(symbol) < 5: # User input is likely a symbol

            # Emulates 'ilike' using 'icontains' for case-insensitivity and annotates with a relevance score
            listings = Listing.objects.filter(symbol__icontains=symbol).annotate(
                relevance=Func(Length('symbol') - len(symbol), function='ABS')
            ).order_by('relevance', Length('symbol'))[:5]

        else: # User input is likely a company name (limited to 5 items)
            listings = Listing.objects.filter(
                Q(name__icontains=symbol) | Q(symbol__icontains=symbol)
            ).annotate(
                relevance=Case(
                    When(name__icontains=symbol, then=Func(Length('name') - len(symbol), function='ABS')),
                    default=Func(Length('symbol') - len(symbol), function='ABS')
                )
            ).order_by('relevance', Length('symbol'), Length('name'))[:5]

        data = [{
            'symbol': listing.symbol, 
            'name': listing.name, 
            'exchange_short': listing.exchange_short
            }
            for listing in listings
        ]
        print(f'running check_valid_symbol ... data: { data }')
        return {'success': True, 'data': data}

    except Exception as e:
        # Log error to console or file
        logger.debug(f'running brokerage app, check_valid_symbol() ... no results found, returned error: {str(e)}')
        return {'success': False, 'error': str(e)}


# Process the purchase of shares
def process_buy(symbol, shares, user, check_valid_shares_result):
    logger.debug(f'running brokerage app, process_purchase() ... function started')

    if not check_valid_shares_result['success']:
        logger.error('Purchase cannot be processed due to validation failure.')
        raise ValueError(check_valid_shares_result['message'])  # Or handle this case as appropriate

    transaction_value_total = check_valid_shares_result['data'].get('transaction_value_total')
    transaction_value_per_share = check_valid_shares_result['data'].get('transaction_value_per_share')

    if transaction_value_total is None or transaction_value_per_share is None:
        logger.error('Required transaction values are missing.')
        raise ValueError("Transaction values are missing from the validation result.")

    # Start a database transaction to ensure atomicity
    with transaction.atomic():
        new_transaction = Transaction.objects.create(
                        user = user,
                        type = 'BOT',
                        symbol = symbol,
                        transaction_shares = shares,
                        transaction_value_per_share = transaction_value_per_share, 
                        transaction_value_total = transaction_value_total,
                        shares_outstanding = shares,
                        )
        logger.debug(f'running brokerage app, process_purchase() ... new transaction added: { new_transaction }')
        
        # Update the user's cash balance
        user.userprofile.cash -= transaction_value_total
        user.userprofile.save()  # Don't forget to save the updated profile
        logger.debug(f'running brokerage app, process_purchase() ... user.userprofile.cash updated to: { user.userprofile.cash }')
    
    return new_transaction

    

# Update the listings table in the DB
def update_listings():
    url = f'https://financialmodelingprep.com/api/v3/available-traded/list?apikey={fmp_key}'
    try:
        response = requests.get(url)
    
        # If the response is not problematic, do the following..
        if response.status_code == 200:
            listings_data = response.json()
            with transaction.atomic():  # ensures that all database operations are either fully completed or fully rolled back if an error occurs.
                for item in listings_data:
                    Listing.objects.update_or_create(
                        symbol=item.get('symbol'),
                        defaults={
                            'name': item.get('name'),
                            'price': item.get('price'),
                            'exchange': item.get('exchange'),
                            'exchange_short': item.get('exchangeShortName'),
                            'listing_type': item.get('type')
                        }
                    )
                logger.error('Updated Listings in DB')
        # If response from FMP API is problematic
        else:
            logger.error('Failed to fetch data from API')
    # Catch-all if the try above fails
    except requests.RequestException as e:
        logger.error(f'Error fetching data from API: {e}')
