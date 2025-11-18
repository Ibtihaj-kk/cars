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
        '/business_partners/dashboard/',
        '/business_partners/profile/',
        '/business_partners/documents/',
        '/business_partners/contracts/',
    ]
    
    EXEMPT_URLS = [
        '/business_partners/login/',
        '/business_partners/register/',
        '/business_partners/apply/',
        '/business_partners/logout/',
        '/business_partners/2fa/',
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
        if not request.user.is_authenticated:
            return redirect('business_partners:vendor_login')
        
        # Check if user has vendor profile and is approved
        vendor_profile = get_vendor_profile(request.user)
        if not vendor_profile:
            return HttpResponseForbidden("Access denied: Vendor profile required.")
        
        # Check if vendor is approved
        if not vendor_profile.is_approved:
            return redirect('business_partners:application_pending')
        
        # Check if vendor account is active
        if not vendor_profile.is_active:
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