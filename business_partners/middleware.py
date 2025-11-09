"""
Middleware for business partners and vendor access.
"""
from .permissions import get_vendor_profile, user_has_vendor_access


class VendorAccessMiddleware:
    """
    Middleware to add vendor access information to all requests.
    This helps templates and views easily check vendor status.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Add vendor access information to request
        if hasattr(request, 'user') and request.user.is_authenticated:
            request.has_vendor_access = user_has_vendor_access(request.user)
            request.vendor_profile = get_vendor_profile(request.user)
        else:
            request.has_vendor_access = False
            request.vendor_profile = None
        
        response = self.get_response(request)
        return response