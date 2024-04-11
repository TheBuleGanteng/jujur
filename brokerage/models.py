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
    transaction_value_per_share = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_value_total = models.DecimalField(max_digits=10, decimal_places=2)
    STCG = models.DecimalField(max_digits=10, decimal_places=2)
    LTCG = models.DecimalField(max_digits=10, decimal_places=2)
    STCG_tax = models.DecimalField(max_digits=10, decimal_places=2)
    LTCG_tax = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f'Txn #{self.pk}: {self.type} {self.transaction_shares} of {self.symbol}'



class Listing(models.Model):
    symbol = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    exchange = models.CharField(max_length=20)
    exchange_short = models.CharField(max_length=20)
    listing_type= models.CharField(max_length=20)

    def __str__(self):
        return f'{self.name} ({self.symbol})'

