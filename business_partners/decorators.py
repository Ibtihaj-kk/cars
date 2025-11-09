from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.contrib import messages
from .permissions import get_vendor_profile


def vendor_required(view_func):
    """
    Decorator that checks if the user is authenticated and has an approved vendor profile.
    Redirects to login page if not authenticated, or to vendor application if not approved.
    """
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to access vendor features.')
            return redirect('business_partners:vendor_login')
        
        vendor_profile = get_vendor_profile(request.user)
        if not vendor_profile:
            messages.warning(request, 'Please complete your vendor registration.')
            return redirect('business_partners:vendor_register')
        
        # Check if vendor profile is approved (assuming is_approved is a property or method)
        if hasattr(vendor_profile, 'is_approved') and not vendor_profile.is_approved:
            messages.warning(request, 'Your vendor application is still under review.')
            return redirect('business_partners:vendor_application_status')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def vendor_approved_required(view_func):
    """
    Decorator that checks if the user has an approved vendor profile.
    More lenient than vendor_required - allows access if user has vendor profile
    regardless of approval status (useful for status checking pages).
    """
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to access vendor features.')
            return redirect('business_partners:vendor_login')
        
        vendor_profile = get_vendor_profile(request.user)
        if not vendor_profile:
            messages.warning(request, 'Please complete your vendor registration.')
            return redirect('business_partners:vendor_register')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def admin_required(view_func):
    """
    Decorator that checks if the user is a superuser (admin).
    """
    decorated_view_func = user_passes_test(
        lambda user: user.is_superuser,
        login_url='admin:login'
    )(view_func)
    return decorated_view_func