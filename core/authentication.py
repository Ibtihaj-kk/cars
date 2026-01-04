"""
ISO 27001 & NIST Compliant Centralized Authentication Gateway
Enterprise-grade authentication system with role-based routing
"""
import logging
import time
from datetime import datetime, timedelta
from django.contrib.auth import authenticate, login
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.conf import settings
from django.db import DatabaseError, IntegrityError
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone

from .exceptions import (
    AuthenticationError, RateLimitExceededError, CircuitBreakerOpenError,
    SecurityViolationError, DatabaseConnectionError
)
from .audit_logging import AuditLogger

logger = logging.getLogger('security')
User = get_user_model()


class AuthenticationCircuitBreaker:
    """NIST-compliant circuit breaker for authentication services"""
    
    def __init__(self, failure_threshold=5, reset_timeout=300):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.circuit_open = False
    
    def is_open(self):
        """Check if circuit breaker is open"""
        if self.circuit_open and self.last_failure_time:
            time_since_failure = time.time() - self.last_failure_time
            if time_since_failure > self.reset_timeout:
                # Half-open state - allow one attempt
                self.circuit_open = False
                return False
        return self.circuit_open
    
    def record_success(self):
        """Record successful operation"""
        self.failure_count = 0
        self.circuit_open = False
        self.last_failure_time = None
    
    def record_failure(self):
        """Record failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.circuit_open = True
            logger.warning(
                f"Authentication circuit breaker opened after {self.failure_count} failures"
            )


class AuthenticationRateLimiter:
    """ISO 27001 compliant rate limiting for authentication attempts"""
    
    def __init__(self, requests_per_minute=10, block_duration=300):
        self.requests_per_minute = requests_per_minute
        self.block_duration = block_duration
    
    def check_rate_limit(self, identifier):
        """Check if rate limit is exceeded for given identifier"""
        cache_key = f"auth_rate_limit:{identifier}"
        block_key = f"auth_blocked:{identifier}"
        
        # Check if identifier is blocked
        if cache.get(block_key):
            raise RateLimitExceededError("Too many authentication attempts")
        
        # Get current timestamp and clean old entries
        current_time = time.time()
        timestamps = cache.get(cache_key, [])
        timestamps = [ts for ts in timestamps if current_time - ts < 60]
        
        if len(timestamps) >= self.requests_per_minute:
            # Block identifier for specified duration
            cache.set(block_key, True, self.block_duration)
            raise RateLimitExceededError("Too many authentication attempts")
        
        # Add current timestamp and update cache
        timestamps.append(current_time)
        cache.set(cache_key, timestamps, 60)
        
        return True


class CentralizedAuthenticationService:
    """Enterprise-grade centralized authentication gateway"""
    
    def __init__(self):
        self.circuit_breaker = AuthenticationCircuitBreaker()
        self.rate_limiter = AuthenticationRateLimiter()
        self.audit_logger = AuditLogger()
    
    def authenticate_user(self, request, email, password, remember_me=False, perform_login=True, backend=None):
        """
        ISO 27001 compliant authentication flow
        """
        try:
            # Check circuit breaker
            if self.circuit_breaker.is_open():
                raise CircuitBreakerOpenError("Authentication service temporarily unavailable")
            
            # Check rate limiting
            client_ip = self._get_client_ip(request)
            self.rate_limiter.check_rate_limit(client_ip)
            self.rate_limiter.check_rate_limit(email)
            
            # Perform authentication
            # Pass request to support Axes and other request-aware backends
            user = self._authenticate_credentials(request, email, password)
            
            if not user:
                self._handle_authentication_failure(email, client_ip, request)
                return None, "Invalid credentials"
            
            # Determine primary functional role
            primary_role = self._determine_primary_role(user)
            
            # Validate role access
            if not self._validate_role_access(user, primary_role):
                self._handle_access_denied(user, primary_role, request)
                return None, "Access denied"
            
            # Establish secure session if requested
            if perform_login:
                self._establish_secure_session(request, user, remember_me, backend=backend)
            
            # Get role-based redirect URL
            redirect_url = self._get_role_based_redirect(primary_role, user)
            
            # Log successful authentication
            self.audit_logger.log_authentication_success(
                user, primary_role, client_ip, request
            )
            
            # Record circuit breaker success
            self.circuit_breaker.record_success()
            
            return user, redirect_url
            
        except (RateLimitExceededError, CircuitBreakerOpenError) as e:
            # Re-raise rate limiting and circuit breaker errors
            raise e
            
        except Exception as e:
            # Handle all other errors
            self.circuit_breaker.record_failure()
            logger.error(f"Authentication error: {str(e)}", exc_info=True)
            return None, str(e)
    
    def _authenticate_credentials(self, request, email, password):
        """Authenticate user credentials"""
        try:
            # Pass request to authenticate for Axes support
            # Set is_centralized_service_call=True to avoid recursion if CentralizedAuthenticationBackend is active
            return authenticate(request=request, username=email, password=password, is_centralized_service_call=True)
        except DatabaseError as e:
            logger.error(f"Database error during authentication: {str(e)}")
            raise DatabaseConnectionError("Authentication service unavailable")
        except Exception as e:
            logger.error(f"Unexpected error during authentication: {str(e)}")
            raise AuthenticationError("Authentication failed")
    
    def _determine_primary_role(self, user):
        """Determine user's primary functional role"""
        from .role_routing_engine import RoleRoutingEngine
        return RoleRoutingEngine().resolve_primary_role(user)
    
    def _validate_role_access(self, user, primary_role):
        """Validate user has access to their primary role"""
        from .permission_validator import PermissionValidator
        return PermissionValidator().validate_role_access(user, primary_role)
    
    def establish_secure_session(self, request, user, remember_me=False, backend=None):
        """
        Public method to establish a secure session for an already authenticated user.
        Can be called from views after a successful authenticate() call.
        """
        # Specify backend to avoid ValueError
        if not backend and hasattr(user, 'backend'):
            backend = user.backend
        if not backend:
            backend = 'django.contrib.auth.backends.ModelBackend'
            
        # Perform Django login
        login(request, user, backend=backend)
        
        # Immediate save to persist auth keys before adding security flags
        request.session.save()
        
        # Set security flags and persistence
        return self._setup_session_security(request, user, remember_me)

    def _setup_session_security(self, request, user, remember_me):
        """Set security flags and ensure session persistence"""
        # Set session expiration based on remember_me
        if remember_me:
            request.session.set_expiry(settings.SESSION_COOKIE_AGE_LONG)
        else:
            request.session.set_expiry(settings.SESSION_COOKIE_AGE)
        
        # Set security flags
        request.session['login_time'] = timezone.now().isoformat()
        request.session['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        request.session['client_ip'] = self._get_client_ip(request)
        
        # Set flag for middleware to detect recent login
        import uuid
        request.session['_just_logged_in'] = True
        request.session['_login_timestamp'] = timezone.now().isoformat()
        request.session['_login_session_id'] = str(uuid.uuid4())
        
        # Ensure session is properly established
        request.session.modified = True
        
        # Force session save with multiple attempts
        max_retries = 3
        session_id = getattr(request.session, 'session_key', 'No Key')
        logger.info(f"Establishing secure session. Current ID: {session_id}")
        logger.info(f"Session data to save: {list(request.session.keys())}")
        
        # Ensure we have the latest session data
        request.session.modified = True
        
        for attempt in range(max_retries):
            try:
                request.session.save()
                new_session_id = getattr(request.session, 'session_key', 'No Key')
                
                # Verify data is actually in the session object
                if request.session.get('_just_logged_in') and request.session.get('_auth_user_id'):
                    logger.info(f"Login data verified in session object on attempt {attempt + 1}. Session ID: {new_session_id}")
                    break
                else:
                    logger.warning(f"Login data missing from session object on attempt {attempt + 1}, retrying...")
                    # Re-set keys just in case something cleared them
                    request.session['_just_logged_in'] = True
                    request.session['_login_timestamp'] = timezone.now().isoformat()
                    request.session['_login_session_id'] = new_session_id
                    request.session['_login_request_count'] = 0
                    request.session.modified = True
            except Exception as e:
                logger.error(f"Session save failed on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(0.1)
        
        return True

    def _establish_secure_session(self, request, user, remember_me, backend=None):
        """Internal method used by authenticate_user"""
        # Specify backend to avoid ValueError when multiple backends are configured
        if not backend and hasattr(user, 'backend'):
            backend = user.backend
        
        if not backend:
            # Fallback to ModelBackend if no backend specified
            backend = 'django.contrib.auth.backends.ModelBackend'
         # Perform Django login
        login(request, user, backend=backend)
        
        # Immediate save to persist auth keys before adding security flags
        request.session.save()
        
        # Call the new security setup method
        return self._setup_session_security(request, user, remember_me)
    
    def _get_role_based_redirect(self, primary_role, user):
        """Get redirect URL based on primary role"""
        from .role_routing_engine import RoleRoutingEngine
        return RoleRoutingEngine().get_redirect_url(primary_role, user)
    
    def _handle_authentication_failure(self, email, client_ip, request):
        """Handle authentication failure"""
        self.circuit_breaker.record_failure()
        self.audit_logger.log_authentication_failure(
            email, client_ip, request
        )
    
    def _handle_access_denied(self, user, primary_role, request):
        """Handle access denied"""
        client_ip = self._get_client_ip(request)
        self.audit_logger.log_access_denied(
            user, primary_role, client_ip, request
        )
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


def centralized_login_view(request):
    """Centralized login view endpoint"""
    auth_service = CentralizedAuthenticationService()
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me') == 'true'
        
        try:
            user, redirect_url = auth_service.authenticate_user(
                request, email, password, remember_me
            )
            
            if user:
                return HttpResponseRedirect(redirect_url)
            else:
                # Handle authentication failure
                return render_login_form(request, error_message=redirect_url)
                
        except RateLimitExceededError:
            return render_login_form(request, error_message="Too many attempts. Please try again later.")
            
        except CircuitBreakerOpenError:
            return render_login_form(request, error_message="Authentication service temporarily unavailable.")
    
    # GET request - show login form
    return render_login_form(request)


def render_login_form(request, error_message=None):
    """Render login form with optional error message"""
    from django.shortcuts import render
    
    context = {
        'error_message': error_message,
        'next': request.GET.get('next', '')
    }
    
    return render(request, 'authentication/login.html', context)


class CentralizedAuthenticationBackend:
    """Django authentication backend for centralized authentication service"""
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """Authenticate user using centralized authentication service"""
        if not username or not password:
            return None
            
        # Avoid recursion if called by CentralizedAuthenticationService
        if kwargs.get('is_centralized_service_call'):
            return None
            
        auth_service = CentralizedAuthenticationService()
        
        try:
            # When called from Django's authenticate(), we only want to check credentials,
            # not perform the actual login yet (the view will do that).
            user, redirect_url = auth_service.authenticate_user(
                request, username, password, False, perform_login=False
            )
            return user
        except (RateLimitExceededError, CircuitBreakerOpenError):
            # Let other backends handle authentication if centralized service is unavailable
            return None
        except AuthenticationError:
            return None
    
    def get_user(self, user_id):
        """Get user by ID"""
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
