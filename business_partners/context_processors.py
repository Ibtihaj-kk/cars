"""
Context processors for business partners app.
"""
from .permissions import get_vendor_profile, user_has_vendor_access

def vendor_access(request):
    """
    Add vendor access information to all templates.
    """
    return {
        'user_has_vendor_access': user_has_vendor_access(request.user) if request.user.is_authenticated else False,
    }

def vendor_profile_completion(request):
    """
    Add vendor profile completion percentage to all vendor templates.
    """
    # Only calculate for authenticated users
    if not request.user or not request.user.is_authenticated:
        return {}
    
    # Get vendor profile
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        return {}
    
    # Get profile completion percentage
    profile_completion_percentage = vendor_profile.get_profile_completion_percentage()
    
    return {
        'profile_completion_percentage': profile_completion_percentage,
    }