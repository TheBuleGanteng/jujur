
from django.conf import settings 
from django.db import models
from django.utils import timezone

# Create your models here.
# Notes: 
# 1. Unlike in flask/SQLAlchemy, fields are required by default, so nullable=false is not needed.
# 2. To override this default, you must set 'blank=True' in form validation and 'null=True' in the model definition. 



# Note: Not explicitly listed here, but used is Django's default User class, which includes the following:
# username: A string representing the username for the user.
# first_name: A string representing the user's first name.
# last_name: A string representing the user's last name.
# email: A string representing the user's email address.
# password: A string representing the hashed password for the user.
# groups: A many-to-many relationship representing the groups the user belongs to.
# user_permissions: A many-to-many relationship representing the specific permissions the user has.
# is_staff: A boolean indicating whether the user can access the admin site.
# is_active: A boolean indicating whether the user's account is considered active.
# is_superuser: A boolean indicating whether the user has all permissions without explicitly assigning them.
# last_login: A datetime of the user's last login.
# date_joined: A datetime indicating when the account was created.


# An extension of the default Django User class (see above)
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    cash = models.DecimalField(max_digits=10, decimal_places=2, default=10000.00)
    cash_initial = models.DecimalField(max_digits=10, decimal_places=2, default=10000.00)
    accounting_method = models.CharField(max_length=64, default='FIFO')
    tax_loss_offsets = models.CharField(max_length=64, default='On')
    tax_rate_STCG = models.DecimalField(max_digits=5, decimal_places=2, default=15.00)
    tax_rate_LTCG = models.DecimalField(max_digits=5, decimal_places=2, default=30.00)
    confirmed = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.user.first_name} {self.user.last_name}'