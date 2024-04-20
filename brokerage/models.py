from django.conf import settings 
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Transaction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE) # Replace bit in parens?
    timestamp = models.DateTimeField(default=timezone.now)
    type = models.CharField(max_length=3)
    symbol = models.CharField(max_length=20)
    transaction_shares = models.IntegerField()
    shares_outstanding = models.IntegerField(null=True, blank=True)
    transaction_value_per_share = models.DecimalField(decimal_places=2, max_digits=10)
    transaction_value_total = models.DecimalField(decimal_places=2, max_digits=10)
    STCG = models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)
    LTCG = models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)
    STCG_tax = models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)
    LTCG_tax = models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)

    def __str__(self):
        return f'Txn #{self.pk}: {self.type} {self.transaction_shares} of {self.symbol}'



class Listing(models.Model):
    symbol = models.CharField(blank=True, max_length=20, null=True)
    name = models.CharField(blank=True, max_length=100, null=True)
    price = models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)
    exchange = models.CharField(blank=True, max_length=20, null=True)
    exchange_short = models.CharField(blank=True, max_length=20, null=True)
    listing_type= models.CharField(blank=True, max_length=20, null=True)

    def __str__(self):
        return f'{self.name} ({self.symbol})'

