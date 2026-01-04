"""
ISO 27001 & NIST Compliant Audit Logging System
Enterprise-grade audit logging with security event tracking
"""

import logging
import json
from datetime import datetime
from django.utils import timezone
from django.conf import settings


class AuditLogger:
    """NIST-compliant audit logging system for security events"""
    
    def __init__(self):
        self.logger = logging.getLogger('audit.security')
        
    def log_event(self, event_type, user=None, ip_address=None, details=None, status='success'):
        """
        Log a security event with NIST-compliant formatting
        
        Args:
            event_type (str): Type of event (login, logout, access_denied, etc.)
            user: User object or username
            ip_address (str): Client IP address
            details (dict): Additional event details
            status (str): Event status (success, failure, warning)
        """
        try:
            audit_data = {
                'timestamp': timezone.now().isoformat(),
                'event_type': event_type,
                'status': status,
                'user': self._get_user_identifier(user),
                'ip_address': ip_address or 'unknown',
                'details': details or {},
                'system': 'authentication_service',
                'compliance': {
                    'nist_framework': 'NIST CSF v2.0',
                    'iso_standard': 'ISO 27001:2022'
                }
            }
            
            self.logger.info(
                f"AUDIT_EVENT: {json.dumps(audit_data, default=str)}"
            )
            
        except Exception as e:
            # Fallback to basic logging if audit logging fails
            logging.error(f"Audit logging failed: {e}")
    
    def _get_user_identifier(self, user):
        """Extract user identifier safely"""
        if user is None:
            return 'anonymous'
        elif hasattr(user, 'username'):
            return user.username
        elif hasattr(user, 'email'):
            return user.email
        elif isinstance(user, str):
            return user
        else:
            return 'unknown_user'
    
    def log_login_success(self, user, ip_address, method='password', details=None):
        """Log successful login event"""
        event_details = {
            'authentication_method': method,
            'session_id': getattr(user, 'session_key', None),
            'user_agent': details.get('user_agent') if details else None,
            'additional_info': details
        }
        self.log_event('login_success', user, ip_address, event_details, 'success')
    
    def log_login_failure(self, username, ip_address, reason, method='password', details=None):
        """Log failed login attempt"""
        event_details = {
            'authentication_method': method,
            'failure_reason': reason,
            'attempted_username': username,
            'additional_info': details
        }
        self.log_event('login_failure', username, ip_address, event_details, 'failure')
    
    def log_logout(self, user, ip_address, details=None):
        """Log user logout event"""
        event_details = {
            'session_duration': details.get('session_duration') if details else None,
            'additional_info': details
        }
        self.log_event('logout', user, ip_address, event_details, 'success')
    
    def log_access_denied(self, user, ip_address, resource, reason, details=None):
        """Log access denied event"""
        event_details = {
            'accessed_resource': resource,
            'denial_reason': reason,
            'required_permissions': details.get('required_permissions') if details else None,
            'additional_info': details
        }
        self.log_event('access_denied', user, ip_address, event_details, 'failure')
    
    def log_security_violation(self, user, ip_address, violation_type, details=None):
        """Log security policy violation"""
        event_details = {
            'violation_type': violation_type,
            'severity': 'high',
            'additional_info': details
        }
        self.log_event('security_violation', user, ip_address, event_details, 'failure')
    
    def log_password_change(self, user, ip_address, details=None):
        """Log password change event"""
        event_details = {
            'change_type': 'password_update',
            'additional_info': details
        }
        self.log_event('password_change', user, ip_address, event_details, 'success')
    
    def log_rate_limit_hit(self, user, ip_address, limit_type, details=None):
        """Log rate limiting event"""
        event_details = {
            'limit_type': limit_type,
            'threshold': details.get('threshold') if details else None,
            'window_seconds': details.get('window_seconds') if details else None,
            'additional_info': details
        }
        self.log_event('rate_limit', user, ip_address, event_details, 'warning')


def get_audit_logger():
    """Get singleton audit logger instance"""
    if not hasattr(get_audit_logger, '_instance'):
        get_audit_logger._instance = AuditLogger()
    return get_audit_logger._instance