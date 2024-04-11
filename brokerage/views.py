from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from .helpers import *
import logging
import os
import re
import traceback

logger = logging.getLogger('django')



#-------------------------------------------------------------------------------

@login_required(login_url='users:login')
@require_http_methods(['GET'])
def index(request):
    logger.debug('running users app, index ... view started')

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

