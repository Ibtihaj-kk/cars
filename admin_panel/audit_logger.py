"""
Admin panel audit logging and suspicious activity detection.
Provides comprehensive logging and monitoring for admin panel activities.
"""
import logging
import json
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from datetime import timedelta, datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict
import hashlib

from .models import ActivityLog, ActivityLogType
from .utils import get_client_ip, get_user_agent_info
from users.models import User

logger = logging.getLogger('audit')
security_logger = logging.getLogger('security')


class AdminAuditLogger:
    """
    Comprehensive audit logging for admin panel activities.
    """
    
    # Cache keys for suspicious activity tracking
    FAILED_ATTEMPTS_KEY = "admin_failed_attempts_{ip}"
    SUSPICIOUS_IPS_KEY = "admin_suspicious_ips"
    USER_ACTIVITY_KEY = "admin_user_activity_{user_id}"
    RATE_LIMIT_KEY = "admin_rate_limit_{user_id}_{action}"
    
    # Thresholds for suspicious activity
    MAX_FAILED_ATTEMPTS = 5
    SUSPICIOUS_ACTIVITY_WINDOW = 300  # 5 minutes
    MAX_ACTIONS_PER_MINUTE = 60
    
    @classmethod
    def log_access_attempt(cls, request, user=None, success=True, reason=None):
        """
        Log admin panel access attempts.
        """
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Prepare log data
        log_data = {
            'ip_address': ip_address,
            'user_agent': user_agent,
            'success': success,
            'reason': reason,
            'timestamp': timezone.now().isoformat(),
            'path': request.path,
            'method': request.method,
        }
        
        if user:
            log_data.update({
                'user_id': user.id,
                'user_email': user.email,
                'user_role': getattr(user, 'role', 'unknown'),
            })
        
        # Log to database
        try:
            with transaction.atomic():
                ActivityLog.objects.create(
                    user=user,
                    action_type=ActivityLogType.LOGIN if success else ActivityLogType.SECURITY_VIOLATION,
                    description=f"Admin access {'successful' if success else 'failed'}: {reason or 'N/A'}",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    additional_data=log_data
                )
        except Exception as e:
            logger.error(f"Failed to log access attempt: {e}")
        
        # Track failed attempts for suspicious activity detection
        if not success:
            cls._track_failed_attempt(ip_address)
        
        # Log to file
        if success:
            logger.info(f"Admin access successful - User: {user.email if user else 'N/A'}, IP: {ip_address}")
        else:
            security_logger.warning(f"Admin access failed - Reason: {reason}, IP: {ip_address}, User: {user.email if user else 'N/A'}")
    
    @classmethod
    def log_admin_action(cls, request, action_type, description, target_object=None, additional_data=None):
        """
        Log admin panel actions with detailed information.
        """
        user = request.user
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Check for rate limiting
        if cls._is_rate_limited(user, action_type):
            security_logger.warning(f"Rate limit exceeded for user {user.id} action {action_type}")
            return False
        
        # Prepare comprehensive log data
        log_data = {
            'action_type': action_type,
            'description': description,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'timestamp': timezone.now().isoformat(),
            'path': request.path,
            'method': request.method,
            'user_id': user.id,
            'user_email': user.email,
            'user_role': getattr(user, 'role', 'unknown'),
        }
        
        # Add target object information
        if target_object:
            log_data.update({
                'target_object_type': target_object.__class__.__name__,
                'target_object_id': getattr(target_object, 'id', None),
                'target_object_str': str(target_object)[:200],  # Limit length
            })
        
        # Add additional data
        if additional_data:
            log_data.update(additional_data)
        
        # Log to database
        try:
            with transaction.atomic():
                ActivityLog.objects.create(
                    user=user,
                    action_type=action_type,
                    description=description,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    data=log_data
                )
        except Exception as e:
            logger.error(f"Failed to log admin action: {e}")
            return False
        
        # Track user activity for pattern analysis
        cls._track_user_activity(user.id, action_type)
        
        # Log to file
        logger.info(f"Admin action - User: {user.email}, Action: {action_type}, Description: {description}")
        
        return True
    
    @classmethod
    def log_security_event(cls, request, event_type, description, severity='medium', additional_data=None):
        """
        Log security-related events.
        """
        user = getattr(request, 'user', None)
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Prepare security event data
        event_data = {
            'event_type': event_type,
            'severity': severity,
            'description': description,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'timestamp': timezone.now().isoformat(),
            'path': request.path,
            'method': request.method,
        }
        
        if user and user.is_authenticated:
            event_data.update({
                'user_id': user.id,
                'user_email': user.email,
                'user_role': getattr(user, 'role', 'unknown'),
            })
        
        if additional_data:
            event_data.update(additional_data)
        
        # Log to database
        try:
            with transaction.atomic():
                ActivityLog.objects.create(
                    user=user if user and user.is_authenticated else None,
                    action_type=ActivityLogType.OTHER,
                    description=f"Security Event [{severity.upper()}]: {description}",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    data=event_data
                )
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
        
        # Log to security file based on severity
        if severity in ['high', 'critical']:
            security_logger.critical(f"Security Event - Type: {event_type}, Description: {description}, IP: {ip_address}")
        elif severity == 'medium':
            security_logger.warning(f"Security Event - Type: {event_type}, Description: {description}, IP: {ip_address}")
        else:
            security_logger.info(f"Security Event - Type: {event_type}, Description: {description}, IP: {ip_address}")
        
        # Check if this triggers suspicious activity alerts
        cls._check_suspicious_activity(ip_address, event_type, severity)
    
    @classmethod
    def detect_suspicious_activity(cls, request) -> List[Dict]:
        """
        Detect suspicious activity patterns.
        """
        suspicious_activities = []
        ip_address = get_client_ip(request)
        user = getattr(request, 'user', None)
        
        # Check for multiple failed login attempts
        failed_attempts = cls._get_failed_attempts(ip_address)
        if failed_attempts >= cls.MAX_FAILED_ATTEMPTS:
            suspicious_activities.append({
                'type': 'multiple_failed_logins',
                'severity': 'high',
                'description': f'Multiple failed login attempts from IP {ip_address}',
                'count': failed_attempts
            })
        
        # Check for unusual access patterns
        if user and user.is_authenticated:
            user_activity = cls._get_user_activity(user.id)
            
            # Check for rapid successive actions
            recent_actions = [
                action for action in user_activity 
                if action['timestamp'] > (timezone.now() - timedelta(minutes=1)).isoformat()
            ]
            
            if len(recent_actions) > cls.MAX_ACTIONS_PER_MINUTE:
                suspicious_activities.append({
                    'type': 'rapid_actions',
                    'severity': 'medium',
                    'description': f'Unusually rapid actions by user {user.email}',
                    'count': len(recent_actions)
                })
            
            # Check for unusual time access
            current_hour = timezone.now().hour
            if current_hour < 6 or current_hour > 22:  # Outside normal business hours
                suspicious_activities.append({
                    'type': 'unusual_time_access',
                    'severity': 'low',
                    'description': f'Admin access outside normal hours by {user.email}',
                    'hour': current_hour
                })
        
        # Check for suspicious IP addresses
        if cls._is_suspicious_ip(ip_address):
            suspicious_activities.append({
                'type': 'suspicious_ip',
                'severity': 'high',
                'description': f'Access from known suspicious IP {ip_address}',
                'ip_address': ip_address
            })
        
        return suspicious_activities
    
    @classmethod
    def get_audit_summary(cls, start_date=None, end_date=None) -> Dict:
        """
        Get audit summary for a date range.
        """
        if not start_date:
            start_date = timezone.now() - timedelta(days=7)
        if not end_date:
            end_date = timezone.now()
        
        # Query activity logs
        logs = ActivityLog.objects.filter(
            timestamp__range=[start_date, end_date]
        )
        
        # Calculate summary statistics
        summary = {
            'total_activities': logs.count(),
            'unique_users': logs.values('user').distinct().count(),
            'unique_ips': logs.values('ip_address').distinct().count(),
            'activity_by_type': {},
            'activity_by_hour': defaultdict(int),
            'top_users': [],
            'top_ips': [],
            'security_events': 0,
            'failed_logins': 0,
        }
        
        # Activity by type
        for log_type in ActivityLogType.choices:
            count = logs.filter(action_type=log_type[0]).count()
            summary['activity_by_type'][log_type[1]] = count
        
        # Security events and failed logins
        summary['security_events'] = logs.filter(
            action_type=ActivityLogType.SECURITY_VIOLATION
        ).count()
        
        summary['failed_logins'] = logs.filter(
            action_type=ActivityLogType.LOGIN,
            description__icontains='failed'
        ).count()
        
        # Activity by hour
        for log in logs:
            hour = log.timestamp.hour
            summary['activity_by_hour'][hour] += 1
        
        # Top users by activity
        user_activity = logs.values('user__email').annotate(
            count=models.Count('id')
        ).order_by('-count')[:10]
        
        summary['top_users'] = [
            {'email': item['user__email'], 'count': item['count']}
            for item in user_activity if item['user__email']
        ]
        
        # Top IPs by activity
        ip_activity = logs.values('ip_address').annotate(
            count=models.Count('id')
        ).order_by('-count')[:10]
        
        summary['top_ips'] = [
            {'ip': item['ip_address'], 'count': item['count']}
            for item in ip_activity
        ]
        
        return summary
    
    # Private helper methods
    
    @classmethod
    def _track_failed_attempt(cls, ip_address):
        """Track failed login attempts by IP."""
        cache_key = cls.FAILED_ATTEMPTS_KEY.format(ip=ip_address)
        attempts = cache.get(cache_key, 0)
        attempts += 1
        cache.set(cache_key, attempts, cls.SUSPICIOUS_ACTIVITY_WINDOW)
        
        # Add to suspicious IPs if threshold exceeded
        if attempts >= cls.MAX_FAILED_ATTEMPTS:
            cls._add_suspicious_ip(ip_address)
    
    @classmethod
    def _get_failed_attempts(cls, ip_address):
        """Get number of failed attempts for IP."""
        cache_key = cls.FAILED_ATTEMPTS_KEY.format(ip=ip_address)
        return cache.get(cache_key, 0)
    
    @classmethod
    def _track_user_activity(cls, user_id, action_type):
        """Track user activity for pattern analysis."""
        cache_key = cls.USER_ACTIVITY_KEY.format(user_id=user_id)
        activity = cache.get(cache_key, [])
        
        # Add new activity
        activity.append({
            'action_type': action_type,
            'timestamp': timezone.now().isoformat()
        })
        
        # Keep only recent activity (last hour)
        cutoff_time = (timezone.now() - timedelta(hours=1)).isoformat()
        activity = [a for a in activity if a['timestamp'] > cutoff_time]
        
        cache.set(cache_key, activity, 3600)  # 1 hour
    
    @classmethod
    def _get_user_activity(cls, user_id):
        """Get recent user activity."""
        cache_key = cls.USER_ACTIVITY_KEY.format(user_id=user_id)
        return cache.get(cache_key, [])
    
    @classmethod
    def _is_rate_limited(cls, user, action_type):
        """Check if user is rate limited for action type."""
        cache_key = cls.RATE_LIMIT_KEY.format(user_id=user.id, action=action_type)
        current_count = cache.get(cache_key, 0)
        
        # Different limits for different action types
        limits = {
            ActivityLogType.CREATE: 30,  # 30 creates per minute
            ActivityLogType.UPDATE: 60,  # 60 updates per minute
            ActivityLogType.DELETE: 10,  # 10 deletes per minute
            ActivityLogType.VIEW: 120,   # 120 views per minute
        }
        
        limit = limits.get(action_type, cls.MAX_ACTIONS_PER_MINUTE)
        
        if current_count >= limit:
            return True
        
        # Increment counter
        cache.set(cache_key, current_count + 1, 60)  # 1 minute window
        return False
    
    @classmethod
    def _add_suspicious_ip(cls, ip_address):
        """Add IP to suspicious list."""
        suspicious_ips = cache.get(cls.SUSPICIOUS_IPS_KEY, set())
        suspicious_ips.add(ip_address)
        cache.set(cls.SUSPICIOUS_IPS_KEY, suspicious_ips, 86400)  # 24 hours
    
    @classmethod
    def _is_suspicious_ip(cls, ip_address):
        """Check if IP is marked as suspicious."""
        suspicious_ips = cache.get(cls.SUSPICIOUS_IPS_KEY, set())
        return ip_address in suspicious_ips
    
    @classmethod
    def _check_suspicious_activity(cls, ip_address, event_type, severity):
        """Check if event triggers suspicious activity alerts."""
        if severity in ['high', 'critical']:
            # Immediately mark IP as suspicious for high/critical events
            cls._add_suspicious_ip(ip_address)
            
            # Could trigger additional alerts here (email, Slack, etc.)
            security_logger.critical(f"Suspicious activity detected from IP {ip_address}: {event_type}")


# Decorator for automatic audit logging
def audit_admin_action(action_type, description_template=None):
    """
    Decorator to automatically log admin actions.
    
    Usage:
    @audit_admin_action(ActivityLogType.UPDATE, "Updated listing {listing_id}")
    def update_listing(request, listing_id):
        # view logic
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            # Execute the view
            result = view_func(request, *args, **kwargs)
            
            # Generate description
            if description_template:
                try:
                    description = description_template.format(**kwargs)
                except (KeyError, ValueError):
                    description = f"Admin action: {view_func.__name__}"
            else:
                description = f"Admin action: {view_func.__name__}"
            
            # Log the action
            AdminAuditLogger.log_admin_action(
                request=request,
                action_type=action_type,
                description=description,
                additional_data={
                    'view_name': view_func.__name__,
                    'args': args,
                    'kwargs': kwargs
                }
            )
            
            return result
        
        return wrapper
    return decorator