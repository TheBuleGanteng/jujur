from django.urls import path

from . import views

app_name = 'users'  # Namespace for the users app

urlpatterns = [
    path('', views.index, name='index'),
    path('login', views.login_view, name='login'),
    #path('check_email_registered', views.check_email_registered_view, name='check_email_registered'),
    #path('check_username_registered', views.check_username_registered_view, name='check_username_registered'),
    path('logout', views.logout_view, name='logout'),
    path('register', views.register_view, name='register'),
]