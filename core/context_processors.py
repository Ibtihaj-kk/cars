from django.conf import settings

DEBUG = settings.DEBUG


def cache_clearing(request):
    """
    Context processor to enable cache clearing for development environments.
    Returns a flag indicating whether cache clearing should be enabled.
    """
    host = request.get_host()
    
    # Enable cache clearing for localhost and 127.0.0.1 in development
    is_development = (
        host.startswith('localhost:') or 
        host.startswith('127.0.0.1:') or
        (DEBUG and any(host.startswith(dev_host) for dev_host in ['localhost', '127.0.0.1']))
    )
    
    return {
        'SHOW_CACHE_CLEARING': is_development
    }


def currency_processor(request):
    """
    Context processor for multi-currency support
    
    Makes available in templates:
    - current_currency: The user's selected currency object
    - available_currencies: All active currencies for currency selector
    """
    try:
        from core.models import Currency
        return {
            'current_currency': getattr(request, 'currency', None),
            'available_currencies': Currency.objects.filter(is_active=True).order_by('name'),
        }
    except Exception:
        return {
            'current_currency': None,
            'available_currencies': [],
        }