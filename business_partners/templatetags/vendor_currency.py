from django import template
from django.contrib.humanize.templatetags.humanize import intcomma
from business_partners.utils import get_user_currency

register = template.Library()

CURRENCY_SYMBOLS = {
    'USD': '$',
    'EUR': '€',
    'GBP': '£',
    'PKR': 'Rs',
    'AED': 'AED',
    'SAR': 'SAR',
    'CAD': 'C$',
    'AUD': 'A$',
    'JPY': '¥',
    'CNY': '¥',
    'INR': '₹',
}

@register.simple_tag(takes_context=True)
def vendor_currency(context, amount):
    """
    Formats the amount with the vendor's preferred currency symbol.
    Usage: {% vendor_currency amount %}
    """
    if amount is None:
        return ""
        
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return amount

    request = context.get('request')
    currency_code = 'USD' # Default
    
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        currency_code = get_user_currency(request.user)

    symbol = CURRENCY_SYMBOLS.get(currency_code, currency_code)
    formatted_amount = intcomma(f"{amount:.2f}")
    
    return f"{symbol} {formatted_amount}"

@register.simple_tag(takes_context=True)
def vendor_currency_symbol(context):
    """
    Returns just the vendor's preferred currency symbol.
    Usage: {% vendor_currency_symbol %}
    """
    request = context.get('request')
    currency_code = 'USD' # Default
    
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        currency_code = get_user_currency(request.user)

    return CURRENCY_SYMBOLS.get(currency_code, currency_code)

@register.simple_tag(takes_context=True)
def vendor_currency_code(context):
    """
    Returns just the vendor's preferred currency code.
    Usage: {% vendor_currency_code %}
    """
    request = context.get('request')
    currency_code = 'USD' # Default
    
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        currency_code = get_user_currency(request.user)

    return currency_code
