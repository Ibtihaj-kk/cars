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
        
        # Check for recent login flag - this helps with first-time login redirect issue
        if (hasattr(request, 'session') and 
            request.session.get('_just_logged_in')):
            print(f"Middleware: Detected recent login, allowing request to proceed")
            # Don't clear the flag immediately - let it persist for a few requests
            # This handles the JavaScript redirect delay
            
            # Add a counter to eventually clear the flag
            login_count = request.session.get('_login_request_count', 0)
            login_count += 1
            request.session['_login_request_count'] = login_count
            
            # Clear flags after 3 requests (to handle redirect chain)
            if login_count >= 3:
                request.session.pop('_just_logged_in', None)
                request.session.pop('_login_timestamp', None)
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
                    
                    # Add a counter to eventually clear the flag
                    login_count = request.session.get('_login_request_count', 0)
                    login_count += 1
                    request.session['_login_request_count'] = login_count
                    
                    # Clear flags after 3 requests (to handle redirect chain)
                    if login_count >= 3:
                        request.session.pop('_just_logged_in', None)
                        request.session.pop('_login_timestamp', None)
                        request.session.pop('_login_request_count', None)
                        print(f"Middleware: Cleared login flags after {login_count} requests")
                    
                    return self.get_response(request)
            except (ValueError, TypeError):
                pass  # Invalid timestamp format, ignore
        
        if not request.user.is_authenticated:
            # Check if this is a login redirect by examining session
            # This prevents redirect loops when user just logged in
            print(f"Middleware: Request user: {request.user}")
            print(f"Middleware: User not authenticated. Session auth ID: {request.session.get('_auth_user_id')}, Method: {request.method}")
            
            # Allow the request if user just logged in (session has auth user ID but user not yet authenticated)
            if (hasattr(request, 'session') and 
                request.session.get('_auth_user_id')):
                print(f"Middleware: Detected auth user ID in session, allowing request to proceed")
                return self.get_response(request)
            
            # Also check for the _just_logged_in flag as a fallback
            if (hasattr(request, 'session') and 
                request.session.get('_just_logged_in')):
                print(f"Middleware: Detected _just_logged_in flag, allowing request to proceed")
                return self.get_response(request)
            
            print(f"Middleware: Redirecting to login")
            return redirect('login')
        
        # Check if user has vendor profile and is approved
        vendor_profile = get_vendor_profile(request.user)
        if not vendor_profile:
            return HttpResponseForbidden("Access denied: Vendor profile required.")
        
        # Allow unapproved vendors to access their dashboard and status pages
        # Only restrict access to certain sensitive operations, not basic dashboard access
        if not vendor_profile.is_approved:
            # Allow access to dashboard and status pages for unapproved vendors
            allowed_paths = [
                '/vendor/dashboard/',  # Main vendor dashboard
                '/vendor/profile/',    # Vendor profile page
                '/business_partners/vendor/dashboard/',  # Legacy dashboard path
                '/business-partners/vendor/dashboard/',  # Dashboard path with dash
                '/business_partners/vendor/profile/',     # Legacy profile path
                '/business-partners/vendor/profile/',     # Profile path with dash
                '/business_partners/vendor/registration/status/',  # Registration status
                '/business-partners/vendor/register/status/',  # Registration status with dash
                '/business_partners/vendor/settings/',    # Settings page
                '/business-partners/vendor/settings/',    # Settings page with dash
            ]
            if not any(request.path.startswith(path) for path in allowed_paths):
                return redirect('business_partners:vendor_registration_status')
        
        # Check if vendor account is active
        if vendor_profile.business_partner.status != 'active':
            return HttpResponseForbidden("Access denied: Vendor account suspended.")
        
        return self.get_response(request)


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