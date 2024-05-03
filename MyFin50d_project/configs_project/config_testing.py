from dotenv import load_dotenv
import os

CSS_CACHE_ENABLED = False
DEBUG = True
SECURE_SSL_REDIRECT = True # Must = True for deployment. If user tries to access via http, user is redirected to https


# Logging configurations
log_to_file = False
log_to_terminal = True

# My domain (used for composing the URL for generate_confirmation_url(token))
MY_SITE_DOMAIN = 'https://127.0.0.1:8080'