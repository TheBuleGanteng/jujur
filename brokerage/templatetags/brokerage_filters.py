from decimal import Decimal, ROUND_HALF_UP
from django import template
import locale

register = template.Library()


@register.filter(name='filter_reformat_number')
def reformat_number(value):
    if value is None:
        return ""
     # Format number
    try:
        # Convert the value to a Decimal for precision and consistent formatting
        decimal_value = Decimal(value)
        # Format the number with commas for thousands separators and two decimal places
        return "{:,.0f}".format(decimal_value)
    except (ValueError, TypeError, decimal.InvalidOperation) as e:
        return str(value)


@register.filter(name='filter_reformat_number_two_decimals')
# Reformat argument as comma-separated number 
def reformat_number_two_decimals(value):
    if value is None:
        return ""
    # Format number
    try:
        # Convert the value to a Decimal for precision and consistent formatting
        decimal_value = Decimal(value)
        # Format the number with commas for thousands separators and two decimal places
        return "{:,.2f}".format(decimal_value)
    except (ValueError, TypeError, decimal.InvalidOperation) as e:
        return str(value)


@register.filter(name='filter_usd')
def filter_usd(value):
    """Format value as USD."""
    # Threshold for considering a value effectively zero
    threshold = 0.005  # Adjust this value as necessary
    if -threshold < value < threshold:
        value = 0  # Treat as zero
    if value >= 0:
        return f'${value:,.2f}'
    else:
        return f'(${-value:,.2f})'


# Custom jinja filter: x.xx% or (x.xx%)
@register.filter(name='filter_percentage')
def filter_percentage(value):
    # Threshold for considering a value effectively zero
    threshold = 0.005  # Adjust this value as necessary
    if -threshold < value < threshold:
        value = 0  # Treat as zero
    if value >= 0:
        return f"{value*100:,.2f}%"
    else:
        return f"({-value*100:,.2f}%)"

