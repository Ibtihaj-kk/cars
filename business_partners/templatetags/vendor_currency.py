from django import template
from django.contrib.humanize.templatetags.humanize import intcomma
from business_partners.utils import get_user_currency

register = template.Library()

CURRENCY_SYMBOLS = {
    'USD': '$',
    'EUR': '€',
    'GBP': '£',
    'PKR': '₨',
    'AED': 'د.إ',
    'SAR': '﷼',
    'CAD': 'C$',
    'AUD': 'A$',
    'JPY': '¥',
    'CNY': '¥',
    'INR': '₹',
}

def _compact_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return value

    sign = '-' if number < 0 else ''
    number = abs(number)

    if number < 1000:
        if number.is_integer():
            return f"{sign}{intcomma(int(number))}"
        return f"{sign}{number:g}"

    unit = 1_000
    suffix = 'K'
    if number >= 1_000_000_000:
        unit = 1_000_000_000
        suffix = 'B'
    elif number >= 1_000_000:
        unit = 1_000_000
        suffix = 'M'

    scaled = number / unit

    if scaled >= 100:
        decimals = 0
    elif scaled >= 10:
        decimals = 1
    else:
        decimals = 2

    rounded = round(scaled, decimals)

    if rounded >= 1000 and suffix == 'K':
        suffix = 'M'
        unit = 1_000_000
        scaled = number / unit
        decimals = 0 if scaled >= 100 else (1 if scaled >= 10 else 2)
        rounded = round(scaled, decimals)
    elif rounded >= 1000 and suffix == 'M':
        suffix = 'B'
        unit = 1_000_000_000
        scaled = number / unit
        decimals = 0 if scaled >= 100 else (1 if scaled >= 10 else 2)
        rounded = round(scaled, decimals)

    text = f"{rounded:.{decimals}f}"
    if '.' in text:
        text = text.rstrip('0').rstrip('.')

    return f"{sign}{text}{suffix}"

@register.filter
def compact_number(value):
    return _compact_number(value)

@register.simple_tag(takes_context=True)
def vendor_currency(context, amount):
    """
    Formats the amount with the vendor's preferred currency symbol.
    Usage: {% vendor_currency amount %}
    """
    if amount is None:
        return ""

    request = context.get('request')
    currency_code = None

    if request:
        currency_code = request.session.get('currency_code') if hasattr(request, 'session') else None
        if not currency_code and getattr(request, 'currency', None):
            currency_code = request.currency.code

    if not currency_code and request and hasattr(request, 'user') and request.user.is_authenticated:
        currency_code = get_user_currency(request.user)

    currency_code = (currency_code or 'USD').upper()

    if hasattr(amount, 'get_display_price') and callable(getattr(amount, 'get_display_price', None)):
        try:
            return amount.get_display_price(currency_code)
        except Exception:
            pass

    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return amount

    try:
        from core.models import Currency, ExchangeRate
        from decimal import Decimal as D

        display_currency = Currency.objects.get(code=currency_code, is_active=True)
        base_amount = D(str(amount))

        if display_currency.code != 'USD':
            rate_from_usd = ExchangeRate.get_current_rate('USD', display_currency.code)
            base_amount = base_amount * D(str(rate_from_usd))

        return display_currency.format_price(base_amount)
    except Exception:
        symbol = CURRENCY_SYMBOLS.get(currency_code, currency_code)
        formatted_amount = intcomma(f"{float(amount):.2f}")
        return f"{symbol} {formatted_amount}"

@register.simple_tag(takes_context=True)
def vendor_currency_part_field(context, part, field_name):
    if part is None or not field_name:
        return ""

    amount = getattr(part, field_name, None)
    if amount in (None, ""):
        return ""

    request = context.get('request')
    currency_code = None

    if request:
        currency_code = request.session.get('currency_code') if hasattr(request, 'session') else None
        if not currency_code and getattr(request, 'currency', None):
            currency_code = request.currency.code

    if not currency_code and request and hasattr(request, 'user') and request.user.is_authenticated:
        currency_code = get_user_currency(request.user)

    currency_code = (currency_code or 'USD').upper()

    try:
        from core.models import Currency, ExchangeRate
        from decimal import Decimal as D

        display_currency = Currency.objects.get(code=currency_code, is_active=True)
        original_curr_code = (getattr(part, 'original_currency', 'USD') or 'USD').upper()
        base_amount = D(str(amount))

        if original_curr_code != 'USD':
            rate_to_usd = ExchangeRate.get_current_rate(original_curr_code, 'USD')
            base_amount = base_amount * D(str(rate_to_usd))

        if display_currency.code != 'USD':
            rate_from_usd = ExchangeRate.get_current_rate('USD', display_currency.code)
            base_amount = base_amount * D(str(rate_from_usd))

        return display_currency.format_price(base_amount)
    except Exception:
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            return amount
        symbol = CURRENCY_SYMBOLS.get(currency_code, currency_code)
        formatted_amount = intcomma(f"{float(amount):.2f}")
        return f"{symbol} {formatted_amount}"

@register.simple_tag(takes_context=True)
def vendor_currency_compact(context, amount):
    if amount is None:
        return ""

    request = context.get('request')
    currency_code = None

    if request:
        currency_code = request.session.get('currency_code') if hasattr(request, 'session') else None
        if not currency_code and getattr(request, 'currency', None):
            currency_code = request.currency.code

    if not currency_code and request and hasattr(request, 'user') and request.user.is_authenticated:
        currency_code = get_user_currency(request.user)

    currency_code = (currency_code or 'USD').upper()

    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return amount

    try:
        from core.models import Currency, ExchangeRate
        from decimal import Decimal as D

        display_currency = Currency.objects.get(code=currency_code, is_active=True)
        base_amount = D(str(amount))

        if display_currency.code != 'USD':
            rate_from_usd = ExchangeRate.get_current_rate('USD', display_currency.code)
            base_amount = base_amount * D(str(rate_from_usd))

        compact = _compact_number(float(base_amount))
        if abs(float(base_amount)) < 1000:
            return display_currency.format_price(base_amount)

        if display_currency.symbol_position == 'left':
            return f"{display_currency.symbol}{compact}"
        return f"{compact} {display_currency.symbol}"
    except Exception:
        symbol = CURRENCY_SYMBOLS.get(currency_code, currency_code)
        compact = _compact_number(amount)
        if abs(amount) < 1000:
            formatted_amount = intcomma(f"{float(amount):.2f}")
            return f"{symbol} {formatted_amount}"
        return f"{symbol} {compact}"

@register.simple_tag(takes_context=True)
def vendor_currency_symbol(context):
    """
    Returns just the vendor's preferred currency symbol.
    Usage: {% vendor_currency_symbol %}
    """
    request = context.get('request')
    currency_code = None

    if request:
        currency_code = request.session.get('currency_code') if hasattr(request, 'session') else None
        if not currency_code and getattr(request, 'currency', None):
            currency_code = request.currency.code

    if not currency_code and request and hasattr(request, 'user') and request.user.is_authenticated:
        currency_code = get_user_currency(request.user)

    currency_code = (currency_code or 'USD').upper()
    return CURRENCY_SYMBOLS.get(currency_code, currency_code)

@register.simple_tag(takes_context=True)
def vendor_currency_code(context):
    """
    Returns just the vendor's preferred currency code.
    Usage: {% vendor_currency_code %}
    """
    request = context.get('request')
    currency_code = None

    if request:
        currency_code = request.session.get('currency_code') if hasattr(request, 'session') else None
        if not currency_code and getattr(request, 'currency', None):
            currency_code = request.currency.code

    if not currency_code and request and hasattr(request, 'user') and request.user.is_authenticated:
        currency_code = get_user_currency(request.user)

    return (currency_code or 'USD').upper()
