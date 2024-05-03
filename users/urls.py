from django.urls import path

from . import views

app_name = 'users'  # Namespace for the users app

urlpatterns = [
    path('check_email_registered/', views.check_email_registered_view, name='check_email_registered'),
    path('check_password_strength/', views.check_password_strength_view, name='check_password_strength'),
    path('check_password_valid/', views.check_password_valid_view, name='check_password_valid'),
    path('check_username_registered/', views.check_username_registered_view, name='check_username_registered'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('password_change/', views.password_change_view, name='password_change'),
    path('password-reset/', views.password_reset_view, name='password_reset'),
    path('password-reset-confirmation/', views.password_reset_confirmation_view, name='password_reset_confirmation'),
    path('profile/', views.profile_view, name='profile'),
    path('register/', views.register_view, name='register'),
    path('register_confirmation/', views.register_confirmation_view, name='register_confirmation'),
]