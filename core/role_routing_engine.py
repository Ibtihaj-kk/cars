"""
ISO 27001 Compliant Role-Based Routing Engine
Enterprise-grade role resolution and routing system
"""
import logging
from django.conf import settings
from django.urls import reverse
from django.core.exceptions import PermissionDenied

logger = logging.getLogger('security')


class RoleRoutingEngine:
    """NIST-compliant role-based routing engine"""
    
    # Role hierarchy from most privileged to least
    ROLE_HIERARCHY = [
        'super_admin',          # System owner - all privileges
        'system_administrator', # Manages roles and permissions
        'business_administrator', # Manages business operations
        'admin',                # User with admin role
        'staff',                # User with staff role
        'vendor_manager',       # Manages vendor relationships
        'vendor',               # Business partner with vendor role
        'customer',             # End user
        'guest'                 # Unauthenticated user
    ]
    
    @staticmethod
    def _check_vendor_permission(user):
        """Check if user has vendor permission safely"""
        try:
            from business_partners.permissions import get_vendor_profile
            # Check if user has any vendor profile (approved or not)
            # We want to route them to vendor dashboard even if pending, 
            # so they can see their status
            profile = get_vendor_profile(user)
            return profile is not None
        except ImportError:
            return False

    # Role routing configuration
    ROLE_ROUTING_MAP = {
        'super_admin': {
            'dashboard': 'admin_panel:dashboard',
            'permissions': lambda user: user.is_superuser,
            'description': 'System owner with all privileges'
        },
        'system_administrator': {
            'dashboard': 'admin_panel:dashboard',
            'permissions': lambda user: user.has_perm('rbac.manage_roles'),
            'description': 'Manages system roles and permissions'
        },
        'business_administrator': {
            'dashboard': 'admin_panel:dashboard',
            'permissions': lambda user: user.has_perm('business.manage_operations'),
            'description': 'Manages business operations and partnerships'
        },
        'admin': {
            'dashboard': 'admin_panel:dashboard',
            'permissions': lambda user: getattr(user, 'is_admin', lambda: False)(),
            'description': 'User with administrative privileges'
        },
        'staff': {
            'dashboard': 'admin_panel:dashboard',
            'permissions': lambda user: getattr(user, 'is_staff_member', lambda: False)(),
            'description': 'User with staff privileges'
        },
        'vendor_manager': {
            'dashboard': 'admin_panel:vendor_management',
            'permissions': lambda user: user.has_perm('vendors.manage_vendors'),
            'description': 'Manages vendor relationships and approvals'
        },
        'vendor': {
            'dashboard': 'business_partners:vendor_dashboard',
            'permissions': lambda user: RoleRoutingEngine._check_vendor_permission(user),
            'description': 'Business partner with vendor capabilities'
        },
        'customer': {
            'dashboard': 'users:user-dashboard',
            'permissions': lambda user: user.is_authenticated,
            'description': 'Registered customer user'
        },
        'guest': {
            'dashboard': 'home',
            'permissions': lambda user: not user.is_authenticated,
            'description': 'Unauthenticated guest user'
        }
    }
    
    def resolve_primary_role(self, user):
        """
        Resolve user's primary functional role following NIST guidelines
        Returns the most privileged role the user possesses
        """
        if not user or not user.is_authenticated:
            return 'guest'
        
        # Check role hierarchy from most privileged to least
        for role_name in self.ROLE_HIERARCHY:
            role_config = self.ROLE_ROUTING_MAP.get(role_name)
            if role_config and role_config['permissions'](user):
                return role_name
        
        # Fallback to customer role for authenticated users
        return 'customer'
    
    def get_redirect_url(self, primary_role, user):
        """
        Get appropriate redirect URL based on primary role
        """
        role_config = self.ROLE_ROUTING_MAP.get(primary_role)
        if not role_config:
            logger.warning(f"No routing configuration for role: {primary_role}")
            return reverse('home')
        
        # Get dashboard URL
        dashboard_url = role_config.get('dashboard')
        
        if not dashboard_url:
            logger.warning(f"No dashboard URL configured for role: {primary_role}")
            return reverse('home')
        
        # Handle URL reversal
        try:
            return reverse(dashboard_url)
        except Exception as e:
            logger.error(f"Error reversing URL {dashboard_url}: {str(e)}")
            return reverse('home')
    
    def get_role_description(self, role_name):
        """Get description for a specific role"""
        role_config = self.ROLE_ROUTING_MAP.get(role_name)
        return role_config.get('description', 'Unknown role') if role_config else 'Unknown role'
    
    def validate_role_transition(self, current_role, target_role):
        """
        Validate if role transition is allowed
        Prevents privilege escalation attacks
        """
        current_index = self.ROLE_HIERARCHY.index(current_role)
        target_index = self.ROLE_HIERARCHY.index(target_role)
        
        # Only allow transitions to less privileged roles
        # or within the same privilege level
        return target_index >= current_index
    
    def get_available_roles(self, user):
        """
        Get all roles available to the user
        Useful for role switching functionality
        """
        available_roles = []
        
        for role_name in self.ROLE_HIERARCHY:
            role_config = self.ROLE_ROUTING_MAP.get(role_name)
            if role_config and role_config['permissions'](user):
                available_roles.append({
                    'name': role_name,
                    'description': role_config.get('description'),
                    'dashboard': role_config.get('dashboard')
                })
        
        return available_roles


class RoleResolver:
    """ISO 27001 compliant role resolution service"""
    
    def __init__(self):
        self.routing_engine = RoleRoutingEngine()
    
    def resolve_primary_role(self, user):
        """Resolve user's primary functional role"""
        return self.routing_engine.resolve_primary_role(user)
    
    def get_role_based_redirect(self, user):
        """Get redirect URL based on user's primary role"""
        primary_role = self.resolve_primary_role(user)
        return self.routing_engine.get_redirect_url(primary_role, user)
    
    def can_access_role(self, user, target_role):
        """Check if user can access a specific role"""
        role_config = self.routing_engine.ROLE_ROUTING_MAP.get(target_role)
        return role_config and role_config['permissions'](user)
    
    def get_user_roles(self, user):
        """Get all roles assigned to the user"""
        return self.routing_engine.get_available_roles(user)


def has_vendor_role(user):
    """Check if user has vendor role"""
    resolver = RoleResolver()
    return resolver.can_access_role(user, 'vendor')


def has_admin_role(user):
    """Check if user has any admin role"""
    resolver = RoleResolver()
    admin_roles = ['super_admin', 'system_administrator', 'business_administrator', 'admin', 'staff']
    
    for role in admin_roles:
        if resolver.can_access_role(user, role):
            return True
    return False


def require_role(role_name):
    """Decorator to require specific role access"""
    def decorator(view_func):
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            
            resolver = RoleResolver()
            
            if not resolver.can_access_role(request.user, role_name):
                raise PermissionDenied("Insufficient role privileges")
            
            return view_func(request, *args, **kwargs)
        
        return wrapped_view
    return decorator


def require_any_role(*role_names):
    """Decorator to require any of the specified roles"""
    def decorator(view_func):
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            
            resolver = RoleResolver()
            
            for role_name in role_names:
                if resolver.can_access_role(request.user, role_name):
                    return view_func(request, *args, **kwargs)
            
            raise PermissionDenied("Insufficient role privileges")
        
        return wrapped_view
    return decorator