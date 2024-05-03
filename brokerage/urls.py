from django.urls import path
from django.shortcuts import redirect
from . import views

app_name = 'brokerage'  # Namespace for the users app

urlpatterns = [
    path('', lambda request: redirect('index/', permanent=False)),  # Temporary redirect to /index/
    path('index/', views.index_view, name='index'),
    path('index-detail/', views.index_detail_view, name='index_detail'),
    path('buy/', views.buy_view, name='buy'),
    path('check-shares/', views.check_valid_shares_view, name='check_valid_shares'),
    path('check-symbol/', views.check_valid_symbol_view, name='check_valid_symbol'),
    path('history/', views.history_view, name='history'),
    path('quote/', views.quote_view, name='quote'),
    path('sell/', views.sell_view, name='sell'),
]