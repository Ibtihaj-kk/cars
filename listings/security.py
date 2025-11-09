"""
Security features for listings API including rate limiting and access controls.
"""
import time
from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django.contrib.auth.models import AnonymousUser
import logging

logger = logging.getLogger(__name__)


class RateLimitMixin:
    """Mixin to add rate limiting to API views."""
    
    rate_limit_key = None
    rate_limit_rate = '100/h'  # Default: 100 requests per hour
    rate_limit_method = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
    
    def get_rate_limit_key(self, request):
        """Generate cache key for rate limiting."""
        if self.rate_limit_key:
            return self.rate_limit_key
        
        # Use IP address for anonymous users, user ID for authenticated users
        if request.user.is_authenticated:
            identifier = f"user_{request.user.id}"
        else:
            # Get IP address
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
            identifier = f"ip_{ip}"
        
        return f"rate_limit_{self.__class__.__name__}_{identifier}"
    
    def check_rate_limit(self, request):
        """Check if request exceeds rate limit."""
        if request.method not in self.rate_limit_method:
            return True
        
        # Parse rate limit (e.g., '100/h' -> 100 requests per hour)
        rate_parts = self.rate_limit_rate.split('/')
        if len(rate_parts) != 2:
            return True
        
        try:
            limit = int(rate_parts[0])
            period = rate_parts[1]
        except ValueError:
            return True
        
        # Convert period to seconds
        period_seconds = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400
        }.get(period, 3600)
        
        cache_key = self.get_rate_limit_key(request)
        current_time = int(time.time())
        window_start = current_time - period_seconds
        
        # Get current request count
        requests = cache.get(cache_key, [])
        
        # Filter requests within the current window
        requests = [req_time for req_time in requests if req_time > window_start]
        
        # Check if limit exceeded
        if len(requests) >= limit:
            return False
        
        # Add current request
        requests.append(current_time)
        cache.set(cache_key, requests, period_seconds)
        
        return True
    
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to check rate limit."""
        if not self.check_rate_limit(request):
            return Response({
                'error': 'Rate limit exceeded',
                'detail': f'Maximum {self.rate_limit_rate} requests allowed'
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        return super().dispatch(request, *args, **kwargs)


def rate_limit(rate='100/h', methods=None, key_func=None):
    """
    Decorator for rate limiting API views.
    
    Args:
        rate: Rate limit string (e.g., '100/h', '10/m')
        methods: List of HTTP methods to rate limit
        key_func: Function to generate cache key
    """
    if methods is None:
        methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
    
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.method not in methods:
                return view_func(request, *args, **kwargs)
            
            # Generate cache key
            if key_func:
                cache_key = key_func(request)
            else:
                if hasattr(request, 'user') and request.user.is_authenticated:
                    identifier = f"user_{request.user.id}"
                else:
                    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                    if x_forwarded_for:
                        ip = x_forwarded_for.split(',')[0]
                    else:
                        ip = request.META.get('REMOTE_ADDR')
                    identifier = f"ip_{ip}"
                
                cache_key = f"rate_limit_{view_func.__name__}_{identifier}"
            
            # Parse rate limit
            rate_parts = rate.split('/')
            if len(rate_parts) != 2:
                return view_func(request, *args, **kwargs)
            
            try:
                limit = int(rate_parts[0])
                period = rate_parts[1]
            except ValueError:
                return view_func(request, *args, **kwargs)
            
            # Convert period to seconds
            period_seconds = {
                's': 1,
                'm': 60,
                'h': 3600,
                'd': 86400
            }.get(period, 3600)
            
            current_time = int(time.time())
            window_start = current_time - period_seconds
            
            # Get current request count
            requests = cache.get(cache_key, [])
            
            # Filter requests within the current window
            requests = [req_time for req_time in requests if req_time > window_start]
            
            # Check if limit exceeded
            if len(requests) >= limit:
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'detail': f'Maximum {rate} requests allowed'
                }, status=429)
            
            # Add current request
            requests.append(current_time)
            cache.set(cache_key, requests, period_seconds)
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


class SecurityHeadersMiddleware:
    """Middleware to add security headers."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # Add HSTS header for HTTPS
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response


class APISecurityMixin:
    """Mixin to add security features to API views."""
    
    def get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def log_security_event(self, request, event_type, details=None):
        """Log security events."""
        logger.warning(
            f"Security Event: {event_type} - "
            f"User: {getattr(request.user, 'id', 'Anonymous')} - "
            f"IP: {self.get_client_ip(request)} - "
            f"Details: {details or 'N/A'}"
        )
    
    def check_suspicious_activity(self, request):
        """Check for suspicious activity patterns."""
        ip = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Check for common bot patterns
        bot_patterns = [
            'bot', 'crawler', 'spider', 'scraper', 'curl', 'wget'
        ]
        
        if any(pattern in user_agent.lower() for pattern in bot_patterns):
            self.log_security_event(
                request, 
                'BOT_DETECTED', 
                f'User-Agent: {user_agent}'
            )
            return True
        
        # Check for rapid requests from same IP
        cache_key = f"request_count_{ip}"
        request_count = cache.get(cache_key, 0)
        
        if request_count > 50:  # More than 50 requests per minute
            self.log_security_event(
                request, 
                'RAPID_REQUESTS', 
                f'Count: {request_count}'
            )
            return True
        
        cache.set(cache_key, request_count + 1, 60)  # 1 minute window
        return False


def require_api_key(view_func):
    """Decorator to require API key for certain endpoints."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        api_key = request.META.get('HTTP_X_API_KEY')
        
        if not api_key:
            return JsonResponse({
                'error': 'API key required',
                'detail': 'X-API-Key header is required'
            }, status=401)
        
        # Validate API key (implement your validation logic)
        valid_keys = getattr(settings, 'API_KEYS', [])
        if api_key not in valid_keys:
            return JsonResponse({
                'error': 'Invalid API key',
                'detail': 'The provided API key is invalid'
            }, status=401)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def admin_required(view_func):
    """Decorator to require admin privileges."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'error': 'Authentication required'
            }, status=401)
        
        if not request.user.is_staff:
            return JsonResponse({
                'error': 'Admin privileges required'
            }, status=403)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


class CacheControlMixin:
    """Mixin to add cache control to API responses."""
    
    cache_timeout = 300  # 5 minutes default
    cache_vary_headers = ['Authorization', 'Accept-Language']
    
    @method_decorator(vary_on_headers(*cache_vary_headers))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def finalize_response(self, request, response, *args, **kwargs):
        """Add cache headers to response."""
        response = super().finalize_response(request, response, *args, **kwargs)
        
        if request.method == 'GET' and response.status_code == 200:
            response['Cache-Control'] = f'public, max-age={self.cache_timeout}'
        else:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        
        return response


# Rate limiting configurations for different endpoints
RATE_LIMITS = {
    'listing_create': '10/h',      # 10 listings per hour
    'listing_update': '20/h',      # 20 updates per hour
    'listing_delete': '5/h',       # 5 deletions per hour
    'image_upload': '50/h',        # 50 image uploads per hour
    'video_upload': '10/h',        # 10 video uploads per hour
    'search': '100/h',             # 100 searches per hour
    'bulk_operations': '5/h',      # 5 bulk operations per hour
    'status_change': '30/h',       # 30 status changes per hour
}


def get_rate_limit(operation):
    """Get rate limit for specific operation."""
    return RATE_LIMITS.get(operation, '100/h')