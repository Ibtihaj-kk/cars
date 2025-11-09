"""
Comprehensive Audit Logging System
Provides centralized audit logging for all system activities
"""
import json
import logging
import traceback
from datetime import datetime, timedelta
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from django.http import HttpRequest
from django.db import transaction
from .models import AuditLog
from .rbac_manager import rbac_manager

logger = logging.getLogger('audit')


class AuditLogger:
    """Centralized audit logging service"""
    
    @staticmethod
    def log_action(
        action_type,
        user,
        object_type=None,
        object_id=None,
        object_repr=None,
        changes=None,
        ip_address=None,
        user_agent=None,
        session_id=None,
        request_path=None,
        request_method=None,
        additional_data=None,
        success=True,
        error_message=None,
        error_traceback=None
    ):
        """
        Log an action to the audit log.
        
        Args:
            action_type: Type of action performed
            user: User who performed the action (None for system actions)
            object_type: Type of object affected
            object_id: ID of object affected
            object_repr: String representation of object
            changes: Dictionary of changes made
            ip_address: IP address of request
            user_agent: User agent string
            session_id: Session ID
            request_path: Request path
            request_method: HTTP method
            additional_data: Additional context data
            success: Whether the action was successful
            error_message: Error message if action failed
            error_traceback: Error traceback if action failed
        """
        try:
            with transaction.atomic():
                audit_log = AuditLog.objects.create(
                    action_type=action_type,
                    user=user,
                    object_type=object_type,
                    object_id=object_id,
                    object_repr=object_repr,
                    changes=changes,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    session_id=session_id,
                    request_path=request_path,
                    request_method=request_method,
                    additional_data=additional_data,
                    success=success,
                    error_message=error_message,
                    error_traceback=error_traceback
                )
                
                # Log to file as well
                logger.info(f"AUDIT: {action_type} by {user} on {object_type}:{object_id} - Success: {success}")
                
                return audit_log
                
        except Exception as e:
            logger.error(f"Failed to create audit log entry: {str(e)}")
            return None
    
    @staticmethod
    def log_from_request(request, action_type, **kwargs):
        """
        Log an action extracting data from the request.
        
        Args:
            request: Django request object
            action_type: Type of action
            **kwargs: Additional logging parameters
        """
        # Extract request data
        ip_address = AuditLogger.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        session_id = request.session.session_key if request.session else None
        request_path = request.path
        request_method = request.method
        
        # Get user (handle anonymous users)
        user = request.user if request.user.is_authenticated else None
        
        # Create audit log
        return AuditLogger.log_action(
            action_type=action_type,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            request_path=request_path,
            request_method=request_method,
            **kwargs
        )
    
    @staticmethod
    def log_model_change(user, instance, action_type, changes=None, request=None):
        """
        Log changes to a model instance.
        
        Args:
            user: User making the change
            instance: Model instance being changed
            action_type: Type of action (CREATE, UPDATE, DELETE)
            changes: Dictionary of changes
            request: Optional request object
        """
        object_type = instance.__class__.__name__
        object_id = instance.pk
        object_repr = str(instance)
        
        # Extract request data if available
        ip_address = None
        user_agent = None
        session_id = None
        request_path = None
        request_method = None
        
        if request:
            ip_address = AuditLogger.get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            session_id = request.session.session_key if request.session else None
            request_path = request.path
            request_method = request.method
        
        return AuditLogger.log_action(
            action_type=action_type,
            user=user,
            object_type=object_type,
            object_id=object_id,
            object_repr=object_repr,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            request_path=request_path,
            request_method=request_method
        )
    
    @staticmethod
    def log_login_attempt(username, success, ip_address=None, user_agent=None, error_message=None):
        """Log login attempt"""
        return AuditLogger.log_action(
            action_type='LOGIN_ATTEMPT',
            user=None,  # User might not be authenticated yet
            object_type='User',
            object_repr=username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message
        )
    
    @staticmethod
    def log_permission_change(user, target_user, action, permission=None, role=None, request=None):
        """Log permission/role changes"""
        changes = {}
        if permission:
            changes['permission'] = permission.codename
        if role:
            changes['role'] = role.name
        
        return AuditLogger.log_action(
            action_type=action,
            user=user,
            object_type='User',
            object_id=target_user.id,
            object_repr=str(target_user),
            changes=changes,
            ip_address=AuditLogger.get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else None
        )
    
    @staticmethod
    def log_security_event(event_type, user=None, details=None, request=None, success=False):
        """Log security-related events"""
        return AuditLogger.log_action(
            action_type=f'SECURITY_{event_type}',
            user=user,
            additional_data=details,
            ip_address=AuditLogger.get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else None,
            success=success
        )
    
    @staticmethod
    def log_api_call(request, action_type, success=True, error_message=None, **kwargs):
        """Log API calls"""
        return AuditLogger.log_from_request(
            request=request,
            action_type=f'API_{action_type}',
            success=success,
            error_message=error_message,
            **kwargs
        )
    
    @staticmethod
    def log_data_access(user, object_type, object_id, action, fields_accessed=None, request=None):
        """Log data access for compliance"""
        additional_data = {
            'fields_accessed': fields_accessed or [],
            'access_type': action
        }
        
        return AuditLogger.log_action(
            action_type='DATA_ACCESS',
            user=user,
            object_type=object_type,
            object_id=object_id,
            additional_data=additional_data,
            ip_address=AuditLogger.get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else None
        )
    
    @staticmethod
    def log_system_event(event_type, details=None, success=True, error_message=None):
        """Log system events"""
        return AuditLogger.log_action(
            action_type=f'SYSTEM_{event_type}',
            user=None,  # System events have no user
            additional_data=details,
            success=success,
            error_message=error_message
        )
    
    @staticmethod
    def get_client_ip(request):
        """Get client IP address from request"""
        if not request:
            return None
        
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @staticmethod
    def get_audit_summary(user=None, days=30):
        """Get audit summary for user or system"""
        from_date = timezone.now() - timedelta(days=days)
        
        queryset = AuditLog.objects.filter(timestamp__gte=from_date)
        
        if user:
            queryset = queryset.filter(user=user)
        
        total_actions = queryset.count()
        successful_actions = queryset.filter(success=True).count()
        failed_actions = total_actions - successful_actions
        
        # Action type breakdown
        action_breakdown = queryset.values('action_type').annotate(
            count=models.Count('id')
        ).order_by('-count')[:10]
        
        # Security events
        security_events = queryset.filter(
            action_type__startswith='SECURITY_'
        ).count()
        
        # Login attempts
        login_attempts = queryset.filter(
            action_type='LOGIN_ATTEMPT'
        ).count()
        
        successful_logins = queryset.filter(
            action_type='LOGIN_ATTEMPT',
            success=True
        ).count()
        
        return {
            'total_actions': total_actions,
            'successful_actions': successful_actions,
            'failed_actions': failed_actions,
            'success_rate': (successful_actions / total_actions * 100) if total_actions > 0 else 0,
            'security_events': security_events,
            'login_attempts': login_attempts,
            'successful_logins': successful_logins,
            'top_actions': list(action_breakdown),
            'period_days': days
        }


# Global audit logger instance
audit_logger = AuditLogger()


# Decorators for easy audit logging
def audit_log_action(action_type, include_request_data=True, include_changes=True):
    """
    Decorator to automatically log function calls.
    
    Usage:
        @audit_log_action('CREATE_PART')
        def create_part(request, data):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            request = None
            user = None
            success = True
            error_message = None
            error_traceback = None
            
            # Try to find request in arguments
            for arg in args:
                if isinstance(arg, HttpRequest):
                    request = arg
                    user = request.user if request.user.is_authenticated else None
                    break
            
            try:
                result = func(*args, **kwargs)
                
                # Log successful action
                if include_request_data and request:
                    audit_logger.log_from_request(
                        request=request,
                        action_type=action_type,
                        success=True
                    )
                else:
                    audit_logger.log_action(
                        action_type=action_type,
                        user=user,
                        success=True
                    )
                
                return result
                
            except Exception as e:
                success = False
                error_message = str(e)
                error_traceback = traceback.format_exc()
                
                # Log failed action
                if include_request_data and request:
                    audit_logger.log_from_request(
                        request=request,
                        action_type=action_type,
                        success=False,
                        error_message=error_message,
                        error_traceback=error_traceback
                    )
                else:
                    audit_logger.log_action(
                        action_type=action_type,
                        user=user,
                        success=False,
                        error_message=error_message,
                        error_traceback=error_traceback
                    )
                
                # Re-raise the exception
                raise
        
        return wrapper
    return decorator


# Model mixins for automatic audit logging
class AuditLogMixin:
    """Mixin to automatically log model changes"""
    
    def save(self, *args, **kwargs):
        """Override save to log changes"""
        is_new = self.pk is None
        
        # Get old values for existing objects
        if not is_new:
            try:
                old_instance = self.__class__.objects.get(pk=self.pk)
                changes = self._get_changes(old_instance)
            except self.__class__.DoesNotExist:
                changes = None
        else:
            changes = None
        
        # Call original save
        super().save(*args, **kwargs)
        
        # Log the action
        action_type = 'CREATE' if is_new else 'UPDATE'
        
        # Try to get user from thread-local storage or request
        user = getattr(self, '_audit_user', None)
        request = getattr(self, '_audit_request', None)
        
        if request and request.user.is_authenticated:
            user = request.user
        
        audit_logger.log_model_change(
            user=user,
            instance=self,
            action=action_type,
            changes=changes,
            request=request
        )
    
    def delete(self, *args, **kwargs):
        """Override delete to log deletion"""
        # Get user before deletion
        user = getattr(self, '_audit_user', None)
        request = getattr(self, '_audit_request', None)
        
        if request and request.user.is_authenticated:
            user = request.user
        
        # Log deletion
        audit_logger.log_model_change(
            user=user,
            instance=self,
            action='DELETE',
            request=request
        )
        
        # Call original delete
        super().delete(*args, **kwargs)
    
    def _get_changes(self, old_instance):
        """Get changes between old and current instance"""
        changes = {}
        
        for field in self._meta.fields:
            field_name = field.name
            old_value = getattr(old_instance, field_name)
            new_value = getattr(self, field_name)
            
            if old_value != new_value:
                changes[field_name] = {
                    'old': str(old_value),
                    'new': str(new_value)
                }
        
        return changes if changes else None
    
    def set_audit_context(self, user=None, request=None):
        """Set audit context for this instance"""
        if user:
            self._audit_user = user
        if request:
            self._audit_request = request