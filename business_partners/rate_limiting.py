"""
Rate limiting configuration for business partners API.
Provides comprehensive DDoS protection and rate limiting for vendor operations.
"""

from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited
from rest_framework.response import Response
from rest_framework import status
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# Rate limiting configurations
RATE_LIMIT_CONFIGS = {
    # Authentication endpoints
    'login': {'rate': '5/m', 'key': 'ip', 'method': 'POST'},
    'password_reset': {'rate': '3/h', 'key': 'ip', 'method': 'POST'},
    'password_reset_confirm': {'rate': '5/h', 'key': 'ip', 'method': 'POST'},
    '2fa_verify': {'rate': '10/m', 'key': 'ip', 'method': 'POST'},
    '2fa_setup': {'rate': '3/h', 'key': 'user', 'method': 'POST'},
    
    # Vendor application endpoints
    'application_create': {'rate': '2/h', 'key': 'user', 'method': 'POST'},
    'application_update': {'rate': '10/h', 'key': 'user', 'method': 'PUT'},
    'application_submit': {'rate': '5/h', 'key': 'user', 'method': 'POST'},
    'application_status_check': {'rate': '20/m', 'key': 'user', 'method': 'GET'},
    
    # File upload endpoints
    'document_upload': {'rate': '5/h', 'key': 'user', 'method': 'POST'},
    'file_download': {'rate': '50/h', 'key': 'user', 'method': 'GET'},
    
    # Bank details endpoints
    'bank_details_update': {'rate': '3/h', 'key': 'user', 'method': 'PUT'},
    'bank_details_view': {'rate': '10/h', 'key': 'user', 'method': 'GET'},
    
    # Vendor management endpoints
    'vendor_list': {'rate': '100/h', 'key': 'user', 'method': 'GET'},
    'vendor_create': {'rate': '5/h', 'key': 'user', 'method': 'POST'},
    'vendor_update': {'rate': '20/h', 'key': 'user', 'method': 'PUT'},
    'vendor_delete': {'rate': '5/h', 'key': 'user', 'method': 'DELETE'},
    
    # Performance and analytics endpoints
    'performance_view': {'rate': '50/h', 'key': 'user', 'method': 'GET'},
    'analytics_view': {'rate': '30/h', 'key': 'user', 'method': 'GET'},
    
    # General API endpoints
    'api_general': {'rate': '200/h', 'key': 'ip', 'method': '*'},
    
    # Search endpoints
    'vendor_search': {'rate': '60/h', 'key': 'user', 'method': 'GET'},
    'part_search': {'rate': '100/h', 'key': 'user', 'method': 'GET'},
    
    # Bulk operations
    'bulk_import': {'rate': '2/h', 'key': 'user', 'method': 'POST'},
    'bulk_export': {'rate': '5/h', 'key': 'user', 'method': 'GET'},
    
    # Admin endpoints (stricter limits)
    'admin_vendor_approve': {'rate': '20/h', 'key': 'user', 'method': 'POST'},
    'admin_vendor_reject': {'rate': '20/h', 'key': 'user', 'method': 'POST'},
    'admin_bulk_operations': {'rate': '10/h', 'key': 'user', 'method': 'POST'},
}

def get_rate_limit_config(operation_type):
    """
    Get rate limiting configuration for a specific operation.
    
    Args:
        operation_type (str): Type of operation to get config for
        
    Returns:
        dict: Rate limiting configuration
    """
    return RATE_LIMIT_CONFIGS.get(operation_type, RATE_LIMIT_CONFIGS['api_general'])

def rate_limit_operation(operation_type):
    """
    Decorator to apply rate limiting to a specific operation.
    
    Args:
        operation_type (str): Type of operation to rate limit
        
    Returns:
        function: Decorated function with rate limiting
    """
    config = get_rate_limit_config(operation_type)
    
    def decorator(func):
        @wraps(func)
        @ratelimit(
            rate=config['rate'],
            key=config['key'],
            method=config['method'],
            block=True
        )
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Ratelimited:
                logger.warning(
                    f"Rate limit exceeded for operation '{operation_type}' "
                    f"by user {getattr(args[0], 'request', None) and getattr(args[0].request, 'user', None) and args[0].request.user.id or 'anonymous'} "
                    f"from IP {getattr(args[0], 'request', None) and getattr(args[0].request, '_get_client_ip', lambda: 'unknown')() or 'unknown'}"
                )
                
                # Log to audit log if user is authenticated
                if (getattr(args[0], 'request', None) and 
                    hasattr(args[0].request, 'user') and 
                    args[0].request.user.is_authenticated):
                    from .audit_logger import VendorAuditLogger
                    VendorAuditLogger.log_rate_limit_exceeded(
                        args[0].request.user,
                        operation_type,
                        ip_address=getattr(args[0], 'request', None) and getattr(args[0].request, '_get_client_ip', lambda: None)() or None,
                        user_agent=getattr(args[0], 'request', None) and args[0].request.META.get('HTTP_USER_AGENT') or None
                    )
                
                return Response(
                    {
                        'error': 'Rate limit exceeded',
                        'message': f'Too many requests. Please try again later.',
                        'retry_after': '60 seconds',
                        'operation': operation_type
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
        
        # Add method to get client IP if not already present
        if not hasattr(wrapper, '_get_client_ip'):
            def _get_client_ip(request):
                """Get client IP address from request."""
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    ip = x_forwarded_for.split(',')[0]
                else:
                    ip = request.META.get('REMOTE_ADDR')
                return ip
            wrapper._get_client_ip = _get_client_ip
        
        return wrapper
    return decorator

def rate_limit_class_operations(operation_mappings):
    """
    Class decorator to apply rate limiting to multiple methods.
    
    Args:
        operation_mappings (dict): Mapping of method names to operation types
        
    Returns:
        function: Class decorator
    """
    def class_decorator(cls):
        for method_name, operation_type in operation_mappings.items():
            if hasattr(cls, method_name):
                original_method = getattr(cls, method_name)
                decorated_method = rate_limit_operation(operation_type)(original_method)
                setattr(cls, method_name, decorated_method)
        return cls
    return class_decorator

# Predefined operation mappings for common viewsets
VENDOR_APPLICATION_RATE_LIMITS = {
    'create': 'application_create',
    'update': 'application_update',
    'retrieve': 'application_status_check',
    'list': 'application_status_check',
}

VENDOR_RATE_LIMITS = {
    'create': 'vendor_create',
    'update': 'vendor_update',
    'destroy': 'vendor_delete',
    'list': 'vendor_list',
    'retrieve': 'vendor_list',
    'performance': 'performance_view',
}

FILE_UPLOAD_RATE_LIMITS = {
    'create': 'document_upload',
    'update': 'document_upload',
    'retrieve': 'file_download',
}

def apply_rate_limits_to_viewset(viewset_class, operation_mappings):
    """
    Apply rate limiting to a viewset class.
    
    Args:
        viewset_class (class): ViewSet class to decorate
        operation_mappings (dict): Mapping of method names to operation types
        
    Returns:
        class: Decorated viewset class
    """
    return rate_limit_class_operations(operation_mappings)(viewset_class)