from decimal import Decimal, ROUND_HALF_UP
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Q, F, Func, Sum, Value
from django.db.models.functions import Length
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from .forms import *
from .helpers import *
import logging
from .models import Listing, Transaction
import os
import re
import traceback
from users.models import UserProfile

logger = logging.getLogger('django')



#-------------------------------------------------------------------------------

@login_required(login_url='users:login')
@require_http_methods(['GET'])
def index_view(request):
    logger.debug('running brokerage app, index ... view started')

    
    # Retrieve the user object for the logged-in user
    user = request.user
    cache_key = f'portfolio_{user.pk}'  # Unique key for each user
    portfolio = cache.get(cache_key)

    if not portfolio:
        portfolio = process_user_transactions(user)
        cache.set(cache_key, portfolio, timeout=300)  # Cache the data for 5 minutes (300 seconds)
        logger.debug(f'running / ... for user {user} ... portfolio.cash is: { portfolio.cash }')
    

    """
    # Call the function to create the portfolio object for the user
    user = request.user
    portfolio = process_user_transactions(user)
    logger.debug(f'running / ... for user {user} ... portfolio.cash is: { portfolio.cash }')
    """

    # Render the index page with the user and portfolio context
    context = {
        'user': user,
        'portfolio': portfolio,
    }
    
    # Render page, passing user and portfolio objects
    return render(request, 'brokerage/index.html', context)

#----------------------------------------------------------------------------

@login_required(login_url='users:login')
@require_http_methods(['GET'])
def index_detail_view(request):
    logger.debug('running brokerage app, index_detail_view ... view started')

    # Retrieve the user object for the logged-in user
    user = request.user
    cache_key = f'portfolio_{user.pk}'  # Unique key for each user
    portfolio = cache.get(cache_key)

    if not portfolio:
        portfolio = process_user_transactions(user)
        cache.set(cache_key, portfolio, timeout=300)  # Cache the data for 5 minutes (300 seconds)
        logger.debug(f'running / ... for user {user} ... portfolio.cash is: { portfolio.cash }')

    # Call the function to create the portfolio object for the user
    portfolio = process_user_transactions(user)
    logger.debug(f'running / ... for user {user} ... portfolio.cash is: { portfolio.cash }')

    # Render the index page with the user and portfolio context
    context = {
        'user': user,
        'portfolio': portfolio,
    }
    
    # Render page, passing user and portfolio objects
    return render(request, 'brokerage/index-detail.html', context)

#----------------------------------------------------------------------------

@login_required(login_url='users:login')
@require_http_methods(['GET', 'POST'])
def buy_view(request):
    logger.debug('running brokerage app, buy_view ... view started')

    # Retrieve the user object for the logged-in user
    user = request.user
    cache_key = f'portfolio_{user.pk}'  # Unique key for each user
    portfolio = cache.get(cache_key)

    # Display the BuyForm
    form = BuyForm(request.POST or None) # This will handle both POST and initial GET

    if request.method == 'POST':
        logger.debug('running brokerage app, buy_view ... user submitted via POST')

        if form.is_valid():
            logger.debug('running brokerage app, buy_view ... user submitted via POST and form passed validation')
        
            # Assigns to variables the username and password passed in via the form in login.html
            symbol = form.cleaned_data['symbol']
            shares = form.cleaned_data['shares']
            print(f'running buy_view ... symbol is: { symbol }')
            print(f'running buy_view ... shares is: { shares }')
            transaction_type = 'BOT'
            logger.debug(f'running brokerage app, buy_view ... symbol is: { symbol } and shares is: { shares }')

            # Check is symbol is valid
            check_valid_symbol_result = check_valid_symbol(symbol)
            logger.debug(f'running buy_view ... check_valid_symbol_result is: { check_valid_symbol_result }')
            
            if not check_valid_symbol_result['success']:
                logger.debug(f'running brokerage app, buy_view ... user-entered symbol: { symbol } is not valid. check_valid_symbol_result is: { check_valid_symbol_result }')
                messages.error(request, check_valid_symbol_result['message'])
                return render(request, 'brokerage/buy.html', {'form': form})
            
            # Check if shares is valid
            check_valid_shares_result = check_valid_shares(shares=shares, symbol=symbol, transaction_type=transaction_type, user=user)
            if not check_valid_shares_result['success']:
                logger.debug(f'running brokerage app, buy_view ... user-entered shares: { shares } is not sufficient for transaction type: { transaction_type } and symbol: { symbol }.')
                messages.error(request, check_valid_shares_result['message'])
                return render(request, 'brokerage/buy.html', {'form': form})

            # If symbol + shares are valid, proceed with processing the share purchase
            new_transaction = process_buy(symbol=symbol, shares=shares, user=user, check_valid_shares_result=check_valid_shares_result)
            
            # Refresh the portfolio to account for the purchase
            portfolio = process_user_transactions(user)
            cache.set(cache_key, portfolio, timeout=300)  # Cache the data for 5 minutes (300 seconds)
            logger.debug(f'running brokerage app, buy_view ... for user {user} ... portfolio.cash is: { portfolio.cash }')
            
            # Flash success message and redirect to index
            logger.debug(f'running brokerage app, buy_view ... successfully processed new_transaction: { new_transaction }.')
            messages.success(request, 'Share purchase processed successfully!')
            return HttpResponseRedirect(reverse('brokerage:index'))
        
        # If form fails validation
        else:
            logger.debug('running brokerage app, buy_view ... user submitted via POST and form failed validation')
            messages.error(request, 'Error: Invalid input. Please see the red text below for assistance.')
            return render(request, 'brokerage/buy.html', {'form': form})

    # If user arrived via GET
    else:
        logger.debug(f'running users app, profile_view ... user arrived via GET')
        return render(request, 'brokerage/buy.html', {'form': form})


#--------------------------------------------------------------------------------------------

# Checks if a symbol is valid, returns either a JSON list of results or an exception + error message
@require_http_methods(['POST'])
def check_valid_shares_view(request):
    logger.debug('running brokerage app, check_valid_shares_view ... view started')

    user = request.user
    symbol = request.POST.get('symbol', '')
    shares = request.POST.get('shares', 0)
    transaction_type = request.POST.get('transaction_type', '')
    
    # Ensure shares are parsed as integer safely
    try:
        shares = int(shares)
    except ValueError:
        return JsonResponse({'success': False, 'message': 'Shares must be an integer.'})
    
    check_valid_shares_result = check_valid_shares(shares=shares, symbol=symbol, transaction_type=transaction_type, user=user)
    
    return JsonResponse(check_valid_shares_result)
    
#-------------------------------------------------------------------------------------------

# Checks if a symbol is valid per FMP API
@require_http_methods(['POST'])
def check_valid_symbol_view(request):
    
    symbol = request.POST.get('symbol', '')
    if not symbol:
        return JsonResponse({'success': False, 'error': 'No symbol provided'}, status=400)
    
    check_valid_symbol_result = check_valid_symbol(symbol)
    
    if not check_valid_symbol_result['success']:
        return JsonResponse({'success': False, 'error': check_valid_symbol_result['error']}, status=500)
    else:
        return JsonResponse({'success': True, 'data': check_valid_symbol_result['data']})

#----------------------------------------------------------------------------

@login_required(login_url='users:login')
@require_http_methods(['GET', 'POST'])
def history_view(request):
    logger.debug('running brokerage app, history_view ... view started')

    # Retrieve the user object for the logged-in user
    user = request.user
    history = user.transaction_set.all()

    # Some additional calculations needed to for history:
    for transaction in history:
        if transaction.type == 'SLD':
            transaction.total_CG_pre_tax = transaction.STCG + transaction.LTCG
            transaction.total_CG_pre_tax_percent = transaction.total_CG_pre_tax / transaction.transaction_value_total
            transaction.total_CG_tax = transaction.LTCG_tax + transaction.STCG_tax
            transaction.STCG_post_tax = transaction.STCG * (1 - user.userprofile.tax_rate_STCG)
            transaction.LTCG_post_tax = transaction.LTCG * (1 - user.userprofile.tax_rate_LTCG)
            transaction.total_CG_post_tax = transaction.STCG_post_tax + transaction.LTCG_post_tax 
            transaction.total_CG_post_tax_percent = transaction.total_CG_post_tax /  transaction.transaction_value_total

    # Render the index page with the user and portfolio context
    context = {
        'user': user,
        'history': history,
    }
    
    # Render page, passing user and portfolio objects
    return render(request, 'brokerage/history.html', context)

#--------------------------------------------------------------------------------

@require_http_methods('GET')
def quote_view(request):
    logger.debug('running brokerage app, quote_view ... view started')

    symbol = request.GET.get('symbol' or None)

    if request.method == 'POST' or symbol:
        
        # Display the QuoteForm
        form = QuoteForm(request.POST or None) # This will handle both POST and initial GET

        # If user submits QuoteForm or there is a symbol in the url
        if form.is_valid() or symbol:
            logger.debug('running brokerage app, quote_view ... user submitted via POST and form passed validation')
        
            # Assigns to variables the username and password passed in via the form in login.html
            symbol = symbol or form.cleaned_data['symbol']
            company_profile = company_data(symbol)
            logger.debug(f'running brokerage app, quote_view ... quote requested for symbol: {symbol}')
            print(f'(printed) running brokerage app, quote_view ... quote requested for symbol: {symbol}')

            # Some additional calculations displayed in in the html
            company_profile['changes_percent'] = reformat_number_two_decimals(company_profile['changes'] / (company_profile['price'] - company_profile['changes']) )
            company_profile['changes_percent_negative'] = company_profile['changes_percent'] + '%'
            company_profile['changes_percent_positive'] = '+' + company_profile['changes_percent'] + '%'
            company_profile['mktCap_reformatted'] = reformat_usd(company_profile['mktCap'] / 1000000000) + ' billion'
            company_profile['volAvg_reformatted'] = reformat_number(company_profile['volAvg']) + ' daily shares'
            min_val, max_val = company_profile['range'].split('-')
            company_profile['range_reformatted'] = f"${min_val} - ${max_val}"

            # Render a template with the company data
            return render(request, 'brokerage/quoted.html', {'company_profile': company_profile, 'symbol': symbol})

        # If QuoteForm fails validation
        else:
            logger.debug('running brokerage app, quote_view ... validation errors in QuoteForm')
            messages.error(request, 'Error: Invalid input. Please see the red text below for assistance.')            
            return render(request, 'brokerage/quote.html', {'form': form})

    else:
        # GET request without a symbol, show only the form
        form = QuoteForm()
        return render(request, 'brokerage/quote.html', {'form': form})        
            
#--------------------------------------------------------------------------------

@login_required(login_url='users:login')
@require_http_methods(['GET', 'POST'])
def sell_view(request):
    logger.debug('running brokerage app, sell_view ... view started')

    # Retrieve the user object and portfolio for the logged-in user
    user = request.user
    cache_key = f'portfolio_{user.pk}'  # Unique key for each user
    portfolio = cache.get(cache_key)
    logger.debug(f'running sell_view ... user is { user }')
    
    # Retrieve the list of shares owned
    symbols_query = Transaction.objects.filter(user=user, type='BOT').values_list('symbol', flat=True).distinct()
    logger.debug(f'running sell_view ... user is { user }, symbols_query is { symbols_query }')
    symbols = [(symbol, symbol) for symbol in symbols_query]  # Prepare tuple pairs
    logger.debug(f'running sell_view ... user is { user }, symbols_query is { symbols_query }, symbols is: { symbols }')
    form = SellForm(request.POST or None, symbols=symbols)  # Form is instantiated here for both GET and POST

    if request.method == 'POST':
    
        if form.is_valid():
            
            # Assigns to variables the username and password passed in via the form in login.html
            symbol = form.cleaned_data['symbol']
            shares = form.cleaned_data['shares']
            transaction_type = 'SLD'
            logger.debug(f'running sell_view ... user is: { user } and symbol is: { symbol }')
            logger.debug(f'running buy_view ... user is: { user } and shares is: { shares }')
                    
            # Back-end validation to ensure symbol is valid
            if symbol not in symbols_query:
                logger.debug(f'running sell_view ... user is: { user } and symbol is: { symbol }, but symbol not found in symbols: { symbols } ')
                messages.error(request, 'Error: Symbol not found in user list of symbols already owned. Please check your input and try again.')
                return render(request, 'brokerage/sell.html', {'form': form})

            # Back-end validation to ensure shares is valid
            check_valid_shares_result = check_valid_shares(shares=shares, symbol=symbol, transaction_type=transaction_type, user=user)
            if not check_valid_shares_result['success']:
                logger.debug(f'running brokerage app, sell_view ... user is: { user }, symbol is {symbol}, user-entered shares: { shares } is not sufficient for transaction type: { transaction_type }.')
                messages.error(request, check_valid_shares_result['message'])
                return render(request, 'brokerage/sell.html', {'form': form})
    
            # If both back-end validations pass, process the sale
            new_transaction = process_sell(symbol=symbol, shares=shares, user=user)
            logger.debug(f'running sell_view ... user is: { user }, new transaction processed successfully: { new_transaction }')
            
            # Refresh the portfolio to account for the purchase
            portfolio = process_user_transactions(user)
            cache.set(cache_key, portfolio, timeout=300)  # Cache the data for 5 minutes (300 seconds)
            logger.debug(f'running brokerage app, sell_view ... for user {user} ... portfolio.cash is: { portfolio.cash }')
            
            # Flash the success message and redirect to index.
            logger.debug(f'running brokerage app, sell_view ... for user {user} ... processed share sale and refreshed user portfolio. Redirecting to index.')
            messages.success(request, 'Share sale processed successfully!')
            return HttpResponseRedirect(reverse('brokerage:index'))

        # If form fails validation
        else:
            logger.debug('running brokerage app, sell_view ... user submitted via POST and form failed validation')
            messages.error(request, 'Error: Invalid input. Please see the red text below for assistance.')
            return render(request, 'brokerage/sell.html', {'form': form})
    
    # If request is GET
    else:
        return render(request, 'brokerage/sell.html', {'form': form})
