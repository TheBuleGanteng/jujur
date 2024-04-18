from django import template

register = template.Library()

@register.filter(name='filter_usd')
def filter_usd(value):
    """Format value as USD."""
    if value >= 0:
        return f"${value:,.2f}"
    else:
        return f"(${-value:,.2f})"


# Custom jinja filter: x.xx% or (x.xx%)
@register.filter(name='filter_percentage')
def percentage(value):
    if value >= 0:
        return f"{value*100:,.2f}%"
    else:
        return f"({-value*100:,.2f}%)"

