from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
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
def index(request):
    logger.debug('running brokerage app, index ... view started')

    # Retrieve the user object for the logged-in user
    user = request.user

    # Call the function to create the portfolio object for the user
    portfolio = process_user_transactions(user)
    logger.debug(f'running / ... for user {user} ... portfolio.cash is: { portfolio.cash }')

    # Render the index page with the user and portfolio context
    context = {
        'user': user,
        'portfolio': portfolio,
    }
    
    # Render page, passing user and portfolio objects
    return render(request, 'brokerage/index.html', context)



#----------------------------------------------------------------------------

@login_required(login_url='users:login')
@require_http_methods(['GET', 'POST'])
def buy_view(request):
    logger.debug('running brokerage app, index ... view started')

    # Retrieve the user object for the logged-in user
    user = request.user

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
            print(f'running buy_view ... check_valid_symbol_result is: { check_valid_symbol_result }')
            if not check_valid_symbol_result['success']:
                logger.debug(f'running brokerage app, buy_view ... user-entered symbol: { symbol } is not valid')
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
    shares = int(request.POST.get('shares', 0))
    transaction_type = request.POST.get('transaction_type', '')
    
    # Ensure shares are parsed as integer safely
    try:
        shares = int(shares)
    except ValueError:
        return JsonResponse({'success': False, 'message': 'Shares must be an integer.'}, status=400)
    
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

#--------------------------------------------------------------------------------