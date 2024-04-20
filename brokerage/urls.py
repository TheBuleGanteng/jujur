from django.urls import path
from . import views

app_name = 'brokerage'  # Namespace for the users app

urlpatterns = [
    path('', views.index, name='index'),
    path("buy/", views.buy_view, name='buy'),
    path('check-shares/', views.check_valid_shares_view, name='check_valid_shares'),
    path('check-symbol/', views.check_valid_symbol_view, name='check_valid_symbol'),
    #path("logout", views.logout_view, name="logout")
]