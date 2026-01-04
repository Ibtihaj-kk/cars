"""
ISO 27001 & NIST Compliant Security Middleware
Enterprise-grade security middleware with circuit breakers and protection mechanisms
"""
import logging
import time
import re
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.conf import settings
from django.http import HttpResponseForbidden, HttpResponseServerError
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger('security')


class GlobalRateLimitMiddleware(MiddlewareMixin):
    """Global rate limiting middleware to prevent abuse"""
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.rate_limits = {
            'global': {'limit': 1000, 'window': 60},  # 1000 requests per minute globally
            'ip': {'limit': 100, 'window': 60},      # 100 requests per minute per IP
            'auth': {'limit': 10, 'window': 60},     # 10 auth attempts per minute per IP
        }
    
    def __call__(self, request):
        client_ip = self._get_client_ip(request)
        
        # Check global rate limit
        if not self._check_rate_limit('global', 'global'):
            return self._handle_rate_limit_exceeded(request)
        
        # Check IP-based rate limit
        if not self._check_rate_limit(f'ip_{client_ip}', 'ip'):
            return self._handle_rate_limit_exceeded(request)
        
        # Check auth-specific rate limit for login endpoints
        if self._is_auth_request(request):
            if not self._check_rate_limit(f'auth_{client_ip}', 'auth'):
                return self._handle_rate_limit_exceeded(request)
        
        response = self.get_response(request)
        return response
    
    def _check_rate_limit(self, key, limit_type):
        """Check if rate limit is exceeded"""
        current_time = time.time()
        window = self.rate_limits[limit_type]['window']
        limit = self.rate_limits[limit_type]['limit']
        
        cache_key = f'ratelimit:{key}'
        requests = cache.get(cache_key, [])
        
        # Remove old requests outside the time window
        requests = [ts for ts in requests if current_time - ts < window]
        
        if len(requests) >= limit:
            return False
        
        # Add current request timestamp
        requests.append(current_time)
        cache.set(cache_key, requests, window)
        return True
    
    def _handle_rate_limit_exceeded(self, request):
        """Handle rate limit exceeded"""
        logger.warning(f"Rate limit exceeded for IP: {self._get_client_ip(request)}")
        return HttpResponseForbidden(
            "Rate limit exceeded. Please try again later.",
            content_type='text/plain'
        )
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        return ip
    
    def _is_auth_request(self, request):
        """Check if this is an authentication request"""
        auth_paths = ['/login/', '/api/auth/', '/admin/login/']
        return any(request.path.startswith(path) for path in auth_paths)


class CircuitBreakerMiddleware(MiddlewareMixin):
    """Circuit breaker middleware for fault tolerance"""
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.circuit_breakers = {}
        self.failure_threshold = 5  # Number of failures before opening circuit
        self.reset_timeout = 300   # 5 minutes in seconds
    
    def __call__(self, request):
        # Check if circuit is open for this service
        service_name = self._get_service_name(request)
        
        if self._is_circuit_open(service_name):
            return self._handle_circuit_open(request, service_name)
        
        try:
            response = self.get_response(request)
            
            # If successful, reset failure count
            if response.status_code < 500:
                self._record_success(service_name)
            else:
                self._record_failure(service_name)
            
            return response
            
        except Exception as e:
            self._record_failure(service_name)
            raise e
    
    def _get_service_name(self, request):
        """Get service name from request"""
        # Use path-based service identification
        path = request.path
        if path.startswith('/api/'):
            return 'api'
        elif path.startswith('/admin/'):
            return 'admin'
        elif path.startswith('/auth/'):
            return 'auth'
        else:
            return 'web'
    
    def _is_circuit_open(self, service_name):
        """Check if circuit is open for service"""
        circuit_key = f'circuit_breaker:{service_name}'
        circuit_data = cache.get(circuit_key)
        
        if not circuit_data:
            return False
        
        # Check if circuit is open and reset timeout hasn't expired
        if circuit_data.get('state') == 'open':
            opened_at = circuit_data.get('opened_at', 0)
            if time.time() - opened_at < self.reset_timeout:
                return True
            # Reset circuit if timeout has passed
            self._reset_circuit(service_name)
        
        return False
    
    def _record_failure(self, service_name):
        """Record failure and potentially open circuit"""
        circuit_key = f'circuit_breaker:{service_name}'
        circuit_data = cache.get(circuit_key, {'failures': 0, 'state': 'closed'})
        
        circuit_data['failures'] += 1
        
        if circuit_data['failures'] >= self.failure_threshold:
            circuit_data['state'] = 'open'
            circuit_data['opened_at'] = time.time()
            logger.warning(f"Circuit opened for service: {service_name}")
        
        cache.set(circuit_key, circuit_data, self.reset_timeout * 2)
    
    def _record_success(self, service_name):
        """Record success and reset circuit if closed"""
        circuit_key = f'circuit_breaker:{service_name}'
        circuit_data = cache.get(circuit_key)
        
        if circuit_data and circuit_data.get('state') == 'closed':
            circuit_data['failures'] = max(0, circuit_data.get('failures', 0) - 1)
            cache.set(circuit_key, circuit_data, self.reset_timeout * 2)
    
    def _reset_circuit(self, service_name):
        """Reset circuit to closed state"""
        circuit_key = f'circuit_breaker:{service_name}'
        cache.delete(circuit_key)
        logger.info(f"Circuit reset for service: {service_name}")
    
    def _handle_circuit_open(self, request, service_name):
        """Handle circuit open state"""
        logger.warning(f"Circuit open for service: {service_name}, request: {request.path}")
        return HttpResponseServerError(
            "Service temporarily unavailable. Please try again later.",
            content_type='text/plain'
        )


class SecurityHeadersMiddleware(MiddlewareMixin):
    """NIST-compliant security headers middleware"""
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://unpkg.com https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://fonts.googleapis.com; img-src 'self' data: https:; font-src 'self' data: https://fonts.gstatic.com https://cdnjs.cloudflare.com; connect-src 'self' https:;"
        }
    
    def __call__(self, request):
        response = self.get_response(request)
        return self.process_response(request, response)
    
    def process_response(self, request, response):
        """Add security headers to response"""
        for header, value in self.security_headers.items():
            if header not in response:
                response[header] = value
        return response


# Security utility functions
def get_client_ip(request):
    """Get client IP address with validation"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
    
    # Validate IP format
    if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
        ip = '0.0.0.0'
    
    return ip


def validate_session_security(request):
    """Validate session security parameters"""
    if not request.user.is_authenticated:
        return True
    
    # Check session age
    login_time = request.session.get('login_time')
    if login_time:
        try:
            login_dt = timezone.datetime.fromisoformat(login_time)
            session_age = timezone.now() - login_dt
            
            # Warn if session is older than 12 hours
            if session_age.total_seconds() > 43200:  # 12 hours
                logger.warning(f"Old session detected for user {request.user.id}")
                
        except (ValueError, TypeError):
            # Invalid login time format
            request.session['login_time'] = timezone.now().isoformat()
    
    return True
