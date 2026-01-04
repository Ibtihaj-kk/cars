from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseForbidden
from .permissions import get_vendor_profile


class VendorAccessMiddleware:
    """
    Middleware to control vendor access to business partner features.
    Ensures only authorized vendors can access vendor-specific functionality.
    """
    
    VENDOR_URLS = [
        '/business_partners/vendor/',
        '/business-partners/vendor/',  # Add dash version
        '/vendor/',  # Add this for vendor-specific URLs
        '/business_partners/dashboard/',
        '/business-partners/dashboard/',  # Add dash version
        '/business_partners/profile/',
        '/business-partners/profile/',  # Add dash version
        '/business_partners/documents/',
        '/business-partners/documents/',  # Add dash version
        '/business_partners/contracts/',
        '/business-partners/contracts/',  # Add dash version
    ]
    
    EXEMPT_URLS = [
        '/business_partners/login/',
        '/accounts/login/',
        '/business_partners/register/',
        '/business-partners/vendor/register/',
        '/business_partners/apply/',
        '/business_partners/logout/',
        '/business-partners/vendor/logout/',
        '/business_partners/2fa/',
        '/business-partners/vendor/2fa/',
        '/business_partners/vendor/registration/status/',
        '/business-partners/vendor/register/status/',
        '/vendor/registration/status/',  # Add this for direct vendor URLs
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Skip middleware for non-vendor URLs
        if not any(request.path.startswith(url) for url in self.VENDOR_URLS):
            return self.get_response(request)
        
        # Skip exempt URLs
        if any(request.path.startswith(url) for url in self.EXEMPT_URLS):
            return self.get_response(request)
        
        # Check if user is authenticated
        print(f"Middleware check: User authenticated: {request.user.is_authenticated}, Path: {request.path}")
        
        # Debug session accessibility
        print(f"Middleware DEBUG: Has session: {hasattr(request, 'session')}")
        if hasattr(request, 'session'):
            print(f"Middleware DEBUG: Session keys: {list(request.session.keys())}")
            print(f"Middleware DEBUG: _auth_user_id: {request.session.get('_auth_user_id')}")
            print(f"Middleware DEBUG: _just_logged_in: {request.session.get('_just_logged_in')}")
        
        # Check for recent login flag - this helps with first-time login redirect issue
        if (hasattr(request, 'session') and 
            request.session.get('_just_logged_in')):
            print(f"Middleware: Detected recent login, allowing request to proceed")
            
            # Skip incrementing counter for HTMX polling requests to prevent premature flag clearing
            is_htmx = request.headers.get('HX-Request') == 'true'
            
            if not is_htmx:
                # Add a counter to eventually clear the flag
                login_count = request.session.get('_login_request_count', 0)
                login_count += 1
                request.session['_login_request_count'] = login_count
                
                # Clear flags after 10 full page requests (to handle redirect chain and session persistence)
                if login_count >= 10:
                    request.session.pop('_just_logged_in', None)
                    request.session.pop('_login_timestamp', None)
                    request.session.pop('_login_session_id', None)
                    request.session.pop('_login_request_count', None)
                    print(f"Middleware: Cleared login flags after {login_count} requests")
            
            return self.get_response(request)
        
        # Check for recent login timestamp (fallback for timing issues)
        if (hasattr(request, 'session') and 
            request.session.get('_login_timestamp')):
            from datetime import datetime, timedelta
            try:
                login_time = datetime.fromisoformat(request.session.get('_login_timestamp'))
                if datetime.now() - login_time < timedelta(minutes=5):
                    print(f"Middleware: Detected recent login timestamp, allowing request to proceed")
                    
                    # Skip counter for HTMX
                    is_htmx = request.headers.get('HX-Request') == 'true'
                    if not is_htmx:
                        # Add a counter to eventually clear the flag
                        login_count = request.session.get('_login_request_count', 0)
                        login_count += 1
                        request.session['_login_request_count'] = login_count
                        
                        # Clear flags after several requests
                        if login_count >= 15:
                            request.session.pop('_just_logged_in', None)
                            request.session.pop('_login_timestamp', None)
                            request.session.pop('_login_session_id', None)
                            request.session.pop('_login_request_count', None)
                    
                    return self.get_response(request)
            except (ValueError, TypeError):
                pass
        
        # Debug session state
        import logging
        logger = logging.getLogger(__name__)
        session_id = getattr(request.session, 'session_key', 'No Key')
        logger.info(f"Middleware DEBUG: Path: {request.path}")
        logger.info(f"Middleware DEBUG: Session ID: {session_id}")
        logger.info(f"Middleware DEBUG: Session Keys: {list(request.session.keys())}")
        logger.info(f"Middleware DEBUG: User: {request.user}")
        logger.info(f"Middleware DEBUG: Auth: {request.user.is_authenticated}")
        
        # Check if user is authenticated OR if session has auth user ID (login in progress)
        has_auth_user_id = hasattr(request, 'session') and request.session.get('_auth_user_id')
        has_just_logged_in = hasattr(request, 'session') and request.session.get('_just_logged_in')
        has_login_timestamp = hasattr(request, 'session') and request.session.get('_login_timestamp')
        
        # Emergency recovery: if we have auth user ID but request.user is not authenticated,
        # it means AuthenticationMiddleware might have missed it due to session race condition.
        if not request.user.is_authenticated and has_auth_user_id:
            from django.contrib.auth import get_user
            logger.warning(f"Middleware: User not authenticated but _auth_user_id found for session {request.session.session_key}. Attempting recovery.")
            request.user = get_user(request)
            logger.info(f"Middleware: Recovery successful. User: {request.user}, Auth: {request.user.is_authenticated}")
        
        if not request.user.is_authenticated and not has_auth_user_id and not has_just_logged_in and not has_login_timestamp:
            logger.warning(f"Middleware: Unauthorized access attempt to {request.path}. Redirecting to login.")
            return redirect('login')
        
        # If we have auth user ID but user is not authenticated yet, allow the request to proceed
        if has_auth_user_id and not request.user.is_authenticated:
            return self.get_response(request)
        
        # Also check for the _just_logged_in flag as a fallback
        if has_just_logged_in and not request.user.is_authenticated:
            return self.get_response(request)
        
        # Check for login timestamp as additional fallback
        if has_login_timestamp and not request.user.is_authenticated:
            return self.get_response(request)
        
        # Check if user has vendor profile
        vendor_profile = get_vendor_profile(request.user)
        if not vendor_profile:
            return HttpResponseForbidden("Access denied: Vendor profile required.")
        
        # Define pages that DON'T require approval (accessible to unapproved vendors)
        no_approval_required_paths = [
            '/business-partners/vendor/profile/',     # Profile page
            '/business-partners/vendor/settings/',    # Settings page
            '/business-partners/vendor/dashboard/',   # Dashboard (to see pending status)
            '/business-partners/vendor/registration/status/',  # Registration status
            '/business-partners/vendor/register/status/',      # Alt registration status
        ]
        
        # Check if current path is one that doesn't require approval
        is_no_approval_page = any(request.path.startswith(path) for path in no_approval_required_paths)
        
        # For unapproved vendors, only allow specific pages
        if not vendor_profile.is_approved and not is_no_approval_page:
            return redirect('business_partners:vendor_registration_status')
        
        # Check if vendor account is active (for approved vendors)
        if vendor_profile.is_approved and vendor_profile.business_partner.status != 'active':
            return HttpResponseForbidden("Access denied: Vendor account suspended.")
        
        # Log session state before view processing
        if request.user.is_authenticated:
            request._initial_session_id = request.session.session_key
            request._initial_user_id = request.user.id

        response = self.get_response(request)
        
        # Log session state after view processing to detect wipes
        if hasattr(request, '_initial_user_id'):
            current_session_id = request.session.session_key
            current_user_id = getattr(request.user, 'id', None)
            
            if not request.user.is_authenticated or current_user_id != request._initial_user_id:
                logger.error(f"CRITICAL: Session wipe detected during request to {request.path}!")
                logger.error(f"Initial User: {request._initial_user_id}, Current User: {current_user_id}")
                logger.error(f"Initial Session: {request._initial_session_id}, Current Session: {current_session_id}")
                logger.error(f"Session Keys: {list(request.session.keys())}")
        
        return response


class Require2FAMiddleware:
    """
    Middleware to enforce 2FA for vendor users.
    Redirects to 2FA setup if not configured.
    """
    
    EXEMPT_URLS = [
        '/business_partners/2fa/setup/',
        '/business_partners/2fa/verify/',
        '/business_partners/logout/',
        '/accounts/logout/',
        '/admin/',  # Admin has separate 2FA
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        # Skip check for exempt URLs
        if any(request.path.startswith(url) for url in self.EXEMPT_URLS):
            return self.get_response(request)
        
        # Check if user is a vendor
        vendor_profile = get_vendor_profile(request.user)
        if not vendor_profile:
            return self.get_response(request)
        
        # Check if 2FA is required but not set up
        if vendor_profile.requires_2fa_setup():
            return redirect('business_partners:vendor_2fa_setup')
        
        # Check if 2FA is verified in this session
        if vendor_profile.two_factor_enabled:
            if not request.session.get('2fa_verified', False):
                return redirect('business_partners:vendor_2fa_verify')
        
        return self.get_response(request)
