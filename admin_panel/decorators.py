"""
Role-based access control (RBAC) decorators for Cars Portal admin panel.
Provides fine-grained permission control for different admin functions.
"""
import logging
from functools import wraps
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse, HttpResponseForbidden
from django.core.exceptions import PermissionDenied
from .utils import log_activity, get_client_ip
from .models import ActivityLogType
from users.models import UserRole

logger = logging.getLogger('security')


def admin_required(view_func=None, *, min_role='staff', require_2fa=False, log_access=True):
    """
    Decorator to require admin access with specific role level.
    
    Args:
        min_role: Minimum role required ('staff', 'admin', 'superuser')
        require_2fa: Whether 2FA is required for this view
        log_access: Whether to log access attempts
    """
    def decorator(func):
        @wraps(func)
        @login_required
        def wrapper(request, *args, **kwargs):
            user = request.user
            
            # Check if user is active and not restricted
            if not _is_user_active(user):
                if log_access:
                    _log_access_denied(request, 'User account is inactive or restricted')
                return _handle_access_denied(request, 'Your account is inactive or restricted.')
            
            # Check role permissions
            if not _has_required_role(user, min_role):
                if log_access:
                    _log_access_denied(request, f'Insufficient role permissions. Required: {min_role}')
                return _handle_access_denied(request, 'You do not have permission to access this area.')
            
            # Check 2FA requirement
            if require_2fa and not _has_valid_2fa(user):
                if log_access:
                    _log_access_denied(request, '2FA required but not enabled or verified')
                return _handle_2fa_required(request)
            
            # Log successful access
            if log_access:
                _log_successful_access(request, func.__name__)
            
            return func(request, *args, **kwargs)
        return wrapper
    
    if view_func is None:
        return decorator
    else:
        return decorator(view_func)


def superuser_required(view_func=None, *, require_2fa=True, log_access=True):
    """Decorator to require superuser access."""
    return admin_required(view_func, min_role='superuser', require_2fa=require_2fa, log_access=log_access)


def staff_required(view_func=None, *, require_2fa=False, log_access=True):
    """Decorator to require staff access."""
    return admin_required(view_func, min_role='staff', require_2fa=require_2fa, log_access=log_access)


def admin_role_required(view_func=None, *, require_2fa=True, log_access=True):
    """Decorator to require admin role access."""
    return admin_required(view_func, min_role='admin', require_2fa=require_2fa, log_access=log_access)


def permission_required(permissions, require_all=True, log_access=True):
    """
    Decorator to require specific Django permissions.
    
    Args:
        permissions: List of permission strings or single permission string
        require_all: Whether all permissions are required (True) or any (False)
        log_access: Whether to log access attempts
    """
    if isinstance(permissions, str):
        permissions = [permissions]
    
    def decorator(func):
        @wraps(func)
        @login_required
        def wrapper(request, *args, **kwargs):
            user = request.user
            
            # Check if user is active
            if not _is_user_active(user):
                if log_access:
                    _log_access_denied(request, 'User account is inactive or restricted')
                return _handle_access_denied(request, 'Your account is inactive or restricted.')
            
            # Check permissions
            if require_all:
                has_permission = user.has_perms(permissions)
            else:
                has_permission = any(user.has_perm(perm) for perm in permissions)
            
            if not has_permission:
                if log_access:
                    _log_access_denied(request, f'Missing required permissions: {permissions}')
                return _handle_access_denied(request, 'You do not have the required permissions.')
            
            # Log successful access
            if log_access:
                _log_successful_access(request, func.__name__)
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def can_manage_listings(view_func=None, *, log_access=True):
    """Decorator for listing management permissions."""
    return permission_required(
        ['listings.change_vehiclelisting', 'listings.delete_vehiclelisting'],
        require_all=False,
        log_access=log_access
    )(view_func) if view_func else permission_required(
        ['listings.change_vehiclelisting', 'listings.delete_vehiclelisting'],
        require_all=False,
        log_access=log_access
    )


def can_manage_users(view_func=None, *, log_access=True):
    """Decorator for user management permissions."""
    return permission_required(
        ['users.change_user', 'users.delete_user'],
        require_all=False,
        log_access=log_access
    )(view_func) if view_func else permission_required(
        ['users.change_user', 'users.delete_user'],
        require_all=False,
        log_access=log_access
    )


def can_view_analytics(view_func=None, *, log_access=True):
    """Decorator for analytics viewing permissions."""
    def decorator(func):
        @wraps(func)
        @admin_required(min_role='staff', log_access=log_access)
        def wrapper(request, *args, **kwargs):
            return func(request, *args, **kwargs)
        return wrapper
    
    if view_func is None:
        return decorator
    else:
        return decorator(view_func)


def can_view_audit_logs(view_func=None, *, log_access=True):
    """Decorator for audit log viewing permissions."""
    return admin_required(view_func, min_role='admin', require_2fa=True, log_access=log_access)


def ajax_admin_required(min_role='staff', require_2fa=False):
    """
    Decorator for AJAX endpoints that require admin access.
    Returns JSON responses instead of redirects.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Authentication required'}, status=401)
            
            user = request.user
            
            # Check if user is active
            if not _is_user_active(user):
                _log_access_denied(request, 'User account is inactive or restricted')
                return JsonResponse({'error': 'Account is inactive or restricted'}, status=403)
            
            # Check role permissions
            if not _has_required_role(user, min_role):
                _log_access_denied(request, f'Insufficient role permissions. Required: {min_role}')
                return JsonResponse({'error': 'Insufficient permissions'}, status=403)
            
            # Check 2FA requirement
            if require_2fa and not _has_valid_2fa(user):
                _log_access_denied(request, '2FA required but not enabled or verified')
                return JsonResponse({'error': '2FA verification required'}, status=403)
            
            # Log successful access
            _log_successful_access(request, func.__name__)
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def rate_limit_admin(rate='100/h'):
    """
    Rate limiting decorator for admin endpoints.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # This can be implemented with django-ratelimit or custom logic
            # For now, we'll just pass through
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


# Helper functions

def _is_user_active(user):
    """Check if user is active and not restricted."""
    return (
        user.is_active and 
        not user.is_banned and 
        not user.is_suspended and 
        not user.is_deleted
    )


def _has_required_role(user, min_role):
    """Check if user has the required role level."""
    role_hierarchy = {
        'staff': 1,
        'admin': 2,
        'superuser': 3
    }
    
    user_level = 0
    
    # Check Django built-in roles
    if user.is_superuser:
        user_level = 3
    elif user.is_staff:
        user_level = max(user_level, 1)
    
    # Check custom role field
    if hasattr(user, 'role'):
        if user.role == UserRole.ADMIN:
            user_level = max(user_level, 2)
        elif user.role == UserRole.STAFF:
            user_level = max(user_level, 1)
    
    required_level = role_hierarchy.get(min_role, 0)
    return user_level >= required_level


def _has_valid_2fa(user):
    """Check if user has valid 2FA setup."""
    # Check if 2FA is enabled and properly configured
    return getattr(user, 'is_2fa_enabled', False)


def _log_access_denied(request, reason):
    """Log access denied attempts."""
    try:
        log_activity(
            user=request.user if request.user.is_authenticated else None,
            action_type=ActivityLogType.OTHER,
            description=f"Admin access denied: {reason}",
            request=request,
            data={
                'reason': reason,
                'path': request.path,
                'method': request.method
            }
        )
    except Exception as e:
        logger.error(f"Failed to log access denied: {e}")


def _log_successful_access(request, view_name):
    """Log successful admin access."""
    try:
        log_activity(
            user=request.user,
            action_type=ActivityLogType.VIEW,
            description=f"Admin access granted to {view_name}",
            request=request,
            data={
                'view_name': view_name,
                'path': request.path,
                'method': request.method
            }
        )
    except Exception as e:
        logger.error(f"Failed to log successful access: {e}")


def _handle_access_denied(request, message):
    """Handle access denied scenarios."""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # AJAX request
        return JsonResponse({'error': message}, status=403)
    else:
        # Regular request
        messages.error(request, message)
        return redirect(reverse('admin_panel:login'))


def _handle_2fa_required(request):
    """Handle 2FA requirement."""
    message = 'Two-factor authentication is required for this action.'
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': message, 'require_2fa': True}, status=403)
    else:
        messages.warning(request, message)
        return redirect(reverse('admin_panel:setup_2fa'))  # This view would need to be created