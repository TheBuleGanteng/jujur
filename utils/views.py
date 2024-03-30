# In views.py of the 'utils' app
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import logging


# View manages logging of CSP violations. See settings.py for CSP settings
@csrf_exempt
@require_POST
def csp_violation_report(request):
    logger = logging.getLogger('csp_reports') # Here, we use the csp_reports logger, which allows us to set the threshold of this logger independently of the django logger used elsewhere in the project.
    logger.debug(f'running utils app ... logger set to csp_reports')
    logger.debug(f'running utils app, csp_report view ... view started')
    
    if request.method == 'POST':
        report = json.loads(request.body.decode('utf-8'))
        # Log the CSP report.
        logger.error(json.dumps(report, indent=2))
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)



# ---------------------------------------------------------------------


# Readiness check used in deployment
# Readiness check (needed for serving via GCP)
def readiness_check(request):
    logger = logging.getLogger('django')
    logger.debug(f'running utils app, readiness_check view ... logger set to django')
    logger.debug(f'running utils app, readiness_check view ... view started')
    
    try:
        # Your check logic here
        # For example: check_database_connection()
        logger.info("Readiness check passed")
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return HttpResponse('Service Unavailable', status=503)

    logger.debug(f'running utils app, readiness_check view ... view completed w/ HttpResponse of "Ready" and status=200')
    return HttpResponse('Ready', status=200)


