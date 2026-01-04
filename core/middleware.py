"""
Currency detection middleware for multi-currency support
"""
import ipaddress
import re

import requests
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin

from business_partners.utils import get_user_currency
from core.models import Currency

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")

_ALLOWED_CURRENCY_CODES = {"AED", "SAR", "QAR", "OMR", "BHD", "PKR"}

_ISO2_TO_CURRENCY = {
    
    "AE": "AED",
    "SA": "SAR",
    "QA": "QAR",
    "OM": "OMR",
    "BH": "BHD",
    "PK": "PKR",
    
}


def _normalize_currency_code(value):
    code = (value or "").strip().upper()
    return code if _CURRENCY_RE.match(code) else None


def _normalize_allowed_currency_code(value):
    code = _normalize_currency_code(value)
    return code if code in _ALLOWED_CURRENCY_CODES else None


def _get_client_ip(request):
    meta = getattr(request, "META", {}) or {}

    ip = meta.get("HTTP_CF_CONNECTING_IP")
    if ip:
        return ip.strip()

    xff = meta.get("HTTP_X_FORWARDED_FOR")
    if xff:
        first = xff.split(",")[0].strip()
        if first:
            return first

    ip = meta.get("HTTP_X_REAL_IP")
    if ip:
        return ip.strip()

    ip = meta.get("REMOTE_ADDR")
    return ip.strip() if ip else None


def _is_public_ip(ip):
    try:
        addr = ipaddress.ip_address(ip)
        return not (addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_link_local)
    except Exception:
        return False


def _get_cf_country_iso2(request):
    meta = getattr(request, "META", {}) or {}
    value = (meta.get("HTTP_CF_IPCOUNTRY") or "").strip().upper()
    if len(value) == 2 and value != "XX":
        return value
    return None


def _get_accept_language_country_iso2(request):
    meta = getattr(request, "META", {}) or {}
    header = (meta.get("HTTP_ACCEPT_LANGUAGE") or "").strip()
    if not header:
        return None

    first = header.split(",")[0].strip()
    if not first:
        return None

    locale = first.split(";")[0].strip()
    if "-" in locale:
        parts = locale.split("-", 1)
    elif "_" in locale:
        parts = locale.split("_", 1)
    else:
        return None

    if len(parts) != 2:
        return None
    country = parts[1].strip().upper()
    return country if len(country) == 2 else None


def _ipapi_currency_lookup(ip):
    try:
        resp = requests.get(f"https://ipapi.co/{ip}/json/", timeout=(0.75, 1.5))
        if resp.status_code != 200:
            return None
        data = resp.json() or {}
        currency = _normalize_allowed_currency_code(data.get("currency"))
        country = (data.get("country") or "").strip().upper()
        country = country if len(country) == 2 else None
        return {"currency": currency, "country": country}
    except Exception:
        return None


def _get_active_currency(code):
    if not code:
        return None
    try:
        return Currency.objects.get(code=code, is_active=True)
    except Exception:
        return None


def _get_base_currency():
    try:
        base = Currency.objects.filter(is_active=True, is_base=True).first()
        if base:
            return base
        return Currency.objects.filter(is_active=True).order_by("code").first()
    except Exception:
        return None


class SessionProtectionMiddleware(MiddlewareMixin):
    """
    Middleware to protect session integrity during HTMX background polling.
    Prevents race conditions where background polls might overwrite a fresh 
    authenticated session cookie with a stale anonymous one.
    """
    
    def process_request(self, request):
        # Identify background HTMX requests that shouldn't modify the session
        is_htmx = request.headers.get('HX-Request') == 'true'
        is_polling = 'status' in request.path or 'poll' in request.path
        
        if is_htmx and is_polling:
            # Mark this request as a background poll to be handled in process_response
            request._is_htmx_polling = True
            
            # Also prevent any session modification in process_request
            if hasattr(request, 'session'):
                request.session.modified = False
        
        return None

    def process_response(self, request, response):
        # If this was a background HTMX poll, strip any Set-Cookie headers
        # to prevent overwriting the main session cookie.
        if getattr(request, '_is_htmx_polling', False):
            if 'Set-Cookie' in response:
                import logging
                logger = logging.getLogger('security')
                # logger.debug(f"Stripping Set-Cookie from HTMX poll: {request.path}")
                del response['Set-Cookie']
                
            # Ensure the session is NOT marked as modified if it was touched during the view
            if hasattr(request, 'session'):
                request.session.modified = False
                
        return response


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
            # Skip session modification for HTMX requests to prevent session cycling race conditions
            # especially during login polling.
            is_htmx = request.headers.get('HX-Request') == 'true'
            
            session = getattr(request, "session", None)
            
            # Ensure session is NOT marked as modified for HTMX background requests
            if is_htmx and session is not None:
                session.modified = False

            # Emergency Session Recovery: If AuthenticationMiddleware missed the user due to race conditions
            # but we have a valid _auth_user_id in the session, recover the user object.
            # This is critical for preventing "anonymous user" redirects immediately after successful login.
            if session is not None and not getattr(request.user, "is_authenticated", False):
                auth_user_id = session.get("_auth_user_id")
                if auth_user_id:
                    from django.contrib.auth import get_user
                    recovered_user = get_user(request)
                    if recovered_user and recovered_user.is_authenticated:
                        request.user = recovered_user
                        import logging
                        logger = logging.getLogger("security")
                        logger.info(f"Global recovery successful for session {session.session_key}. User: {recovered_user.email}")
                else:
                    # Session Wipe Detection: If we had a just_logged_in flag but no auth_user_id,
                    # it means the session was likely wiped or corrupted.
                    if session.get('_just_logged_in'):
                        import logging
                        logger = logging.getLogger("security")
                        logger.error(f"SESSION WIPE DETECTED: _just_logged_in is True but _auth_user_id is MISSING for session {session.session_key}")
                        logger.error(f"Current session keys: {list(session.keys())}")
                
            currency_code = None
            detected_country = None
            source = None

            if hasattr(request, "GET") and "currency" in request.GET:
                selected_code = _normalize_allowed_currency_code(request.GET.get("currency"))
                selected_currency = _get_active_currency(selected_code)
                if selected_currency and session is not None:
                    # Only modify session if NOT a background HTMX request or if user is authenticated
                    if not is_htmx or getattr(request.user, "is_authenticated", False):
                        if session.get("currency_code") != selected_currency.code:
                            session["currency_code"] = selected_currency.code
                            session["currency_override"] = selected_currency.code
                if selected_currency:
                    currency_code = selected_currency.code
                    source = "override"

            if not currency_code and session is not None:
                override_code = _normalize_allowed_currency_code(session.get("currency_override"))
                override_currency = _get_active_currency(override_code)
                if override_currency:
                    currency_code = override_currency.code
                    # Only modify session if NOT a background HTMX request
                    if not is_htmx or getattr(request.user, "is_authenticated", False):
                        if session.get("currency_code") != override_currency.code:
                            session["currency_code"] = override_currency.code
                    source = "override"

            if not currency_code and hasattr(request, "user") and getattr(request.user, "is_authenticated", False):
                preferred = None
                profile = getattr(request.user, "profile", None)
                preferred = _normalize_allowed_currency_code(getattr(profile, "preferred_currency", None)) if profile else None
                if not preferred:
                    preferred = _normalize_allowed_currency_code(get_user_currency(request.user))
                preferred_currency = _get_active_currency(preferred)
                if preferred_currency:
                    currency_code = preferred_currency.code
                    source = "user"
                    if session is not None and session.get("currency_code") != currency_code:
                        session["currency_code"] = currency_code

            if not currency_code and session is not None:
                existing = _normalize_allowed_currency_code(session.get("currency_code"))
                existing_currency = _get_active_currency(existing)
                if existing_currency:
                    currency_code = existing_currency.code
                    source = "session"

            if not currency_code:
                cf_country = _get_cf_country_iso2(request)
                if cf_country:
                    detected_country = cf_country
                    mapped = _normalize_allowed_currency_code(_ISO2_TO_CURRENCY.get(cf_country))
                    mapped_currency = _get_active_currency(mapped)
                    if mapped_currency:
                        currency_code = mapped_currency.code
                        source = "cdn"
                        if session is not None and not is_htmx: # Skip session write for HTMX background requests
                            if session.get("currency_code") != currency_code:
                                session["currency_code"] = currency_code

            if not currency_code:
                ip = _get_client_ip(request)
                if ip and _is_public_ip(ip):
                    cache_key = f"geoip:ip:{ip}"
                    cached = cache.get(cache_key)
                    cached_code = _normalize_allowed_currency_code((cached or {}).get("currency"))
                    cached_currency = _get_active_currency(cached_code)
                    if cached_currency:
                        currency_code = cached_currency.code
                        detected_country = (cached or {}).get("country") or None
                        source = "cache"
                    else:
                        lock_key = f"geoip:lock:{ip}"
                        if cache.add(lock_key, 1, 10):
                            data = _ipapi_currency_lookup(ip)
                            if data and data.get("currency"):
                                cache.set(cache_key, data, 86400)
                                currency_code = data["currency"]
                                detected_country = data.get("country")
                                source = "ip"

            if not currency_code:
                locale_country = _get_accept_language_country_iso2(request)
                if locale_country:
                    detected_country = detected_country or locale_country
                    mapped = _normalize_allowed_currency_code(_ISO2_TO_CURRENCY.get(locale_country))
                    mapped_currency = _get_active_currency(mapped)
                    if mapped_currency:
                        currency_code = mapped_currency.code
                        source = "locale"

            if not currency_code:
                currency_code = "AED"
                source = "default"

            currency_obj = _get_active_currency(currency_code)
            if not currency_obj:
                currency_obj = _get_base_currency()

            request.currency = currency_obj
            request.currency_source = source
            request.detected_country = detected_country

            if session is not None and currency_obj and not is_htmx:
                if session.get("currency_code") != currency_obj.code:
                    session["currency_code"] = currency_obj.code
                    session.modified = True
        except Exception:
            # Database table might not exist yet, set currency to None
            request.currency = None


class CartValidationMiddleware(MiddlewareMixin):
    """
    Middleware to validate cart exchange rates and handle expired rates
    
    This middleware ensures that:
    1. Cart items with expired exchange rates are refreshed or removed
    2. Users are notified when rates expire during their session
    3. Prevents checkout with stale exchange rates
    """
    
    def process_request(self, request):
        # Only process requests that might involve cart operations
        if not (request.path.startswith('/cart/') or 
                request.path.startswith('/checkout/') or
                request.path.startswith('/parts/') and 'cart' in request.path):
            return
        
        try:
            # For authenticated users, validate database cart rates
            if request.user.is_authenticated:
                from parts.models import Cart
                try:
                    cart = Cart.objects.get(user=request.user, is_active=True)
                    # Check if any cart items have expired rates
                    expired_items = []
                    for item in cart.items.all():
                        if hasattr(item, 'rate_valid_until') and item.rate_valid_until:
                            from django.utils import timezone
                            if timezone.now() > item.rate_valid_until:
                                expired_items.append(item)
                    
                    # If we have expired items, refresh their rates
                    if expired_items:
                        cart.refresh_rate_locks()
                        # Store message for user notification
                        if hasattr(request, 'session'):
                            request.session['rate_refresh_message'] = 'Exchange rates have been updated for your cart items.'
                
                except Cart.DoesNotExist:
                    pass
            
            # For guest users, validate session cart rates
            else:
                from datetime import timedelta
                from django.utils import timezone
                
                cart_data = request.session.get('cart', {})
                rate_expired = False
                
                for part_id, item_data in cart_data.items():
                    # Check if this item has a locked rate in session
                    rate_key = f"locked_rate_{part_id}"
                    if rate_key in request.session:
                        rate_data = request.session[rate_key]
                        locked_at = rate_data.get('locked_at')
                        if locked_at and timezone.now() > locked_at + timedelta(minutes=15):
                            rate_expired = True
                            break
                
                if rate_expired:
                    # Store message for user notification
                    if hasattr(request, 'session'):
                        request.session['rate_expired_message'] = 'Some exchange rates in your cart have expired. Please review your items.'
        
        except Exception as e:
            # Log error but don't break the request
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Cart validation middleware error: {str(e)}")
