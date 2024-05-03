from dotenv import load_dotenv
import os

CSS_CACHE_ENABLED = True
DEBUG = False # Debug must be false for prod
SECURE_SSL_REDIRECT = True # Must = True for deployment. If user tries to access via http, user is redirected to https

# Logging configurations
log_to_file = True
log_to_terminal = False

# My domain (used for composing the URL for generate_confirmation_url(token))
MY_SITE_DOMAIN = os.getenv('MY_SITE_DOMAIN')