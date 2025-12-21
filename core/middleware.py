"""
Currency detection middleware for multi-currency support
"""
from django.utils.deprecation import MiddlewareMixin
from core.models import Currency


class CurrencyMiddleware(MiddlewareMixin):
    """
    Middleware to detect and set user's display currency
    
    Priority order:
    1. User manually selects currency (via ?currency= parameter)
    2. Currency stored in session
    3. Detect from user's location/IP (TODO: implement GeoIP)
    4. Default to USD
    """
    
    def process_request(self, request):
        try:
            # Check if user manually selected currency via URL parameter
            if 'currency' in request.GET:
                selected_code = request.GET['currency'].upper()
                try:
                    currency = Currency.objects.get(code=selected_code, is_active=True)
                    request.session['currency_code'] = currency.code
                except Currency.DoesNotExist:
                    pass  # Invalid currency code, ignore
            
            # Get currency from session or default to USD
            currency_code = request.session.get('currency_code', 'USD')
            
            # Attach currency object to request
            try:
                request.currency = Currency.objects.get(code=currency_code, is_active=True)
            except Currency.DoesNotExist:
                # Fallback to base currency (USD)
                request.currency = Currency.objects.filter(is_base=True).first()
                if request.currency:
                    request.session['currency_code'] = request.currency.code
        except Exception:
            # Database table might not exist yet, set currency to None
            request.currency = None
