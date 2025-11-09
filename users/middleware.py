from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model

User = get_user_model()


class UserRestrictionMiddleware(MiddlewareMixin):
    """
    Middleware to automatically check and clear expired user restrictions.
    """
    
    def process_request(self, request):
        """
        Check and clear expired restrictions for authenticated users.
        """
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Check and clear expired restrictions
            request.user.check_and_clear_expired_restrictions()
        
        return None