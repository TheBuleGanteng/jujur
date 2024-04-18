
import multiprocessing
import os

# The socket to bind
#bind = f"0.0.0.0:{os.getenv('PORT', 8000)}"

# Number of worker processes
workers = multiprocessing.cpu_count() * 2 + 1

# Worker class
# 'sync', 'gthread', 'gevent', 'eventlet' are some of the options
# Depending on your application's I/O profile, you might want to experiment with 'gthread' or 'gevent'
worker_class = 'sync'

# Max number of requests a worker will process before restarting
# This can help prevent memory leaks
max_requests = 1000

# How many seconds to wait for the next request on a Keep-Alive HTTP connection
keepalive = 5

# Amount of time a worker will wait for a connection (increase if experiencing timeouts)
timeout = 60

# Log level
# Increasing log level can help diagnose issues; consider setting it to 'debug' temporarily
#loglevel = 'debug'

# Path to log file
# Make sure the 'logs' directory exists or adjust the path as necessary
#logfile = 'logs/gunicorn.log'

# Access log - consider enabling during debugging
#accesslog = 'logs/access.log'

# Error log
#errorlog = 'logs/error.log'

# Use this setting to prevent data loss on worker restart
preload_app = False

# Specify self-signed keys, so they are not needed in the command line when
# starting gunicorn via 'gunicorn --config gunicorn_config.py homepage_project_settings.wsgi:application --bind 0.0.0.0:8000'
certfile = './gitignored/your_certificate.pem'
keyfile = './gitignored/your_private.key'