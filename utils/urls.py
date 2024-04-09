
from django.urls import path
from . import views

app_name = 'utils'  # Namespace for the users app

urlpatterns = [
    path('csp_violation_report/', views.csp_violation_report, name='csp_violation_report'),
    


]
