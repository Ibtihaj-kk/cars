"""
Breach detection and monitoring utilities.
"""
import re
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from .models import BusinessPartner, VendorAuditLog
from .audit_logger import VendorAuditLogger


logger = logging.getLogger('security_breach_detection')


class BreachDetectionEngine:
    """
    Detects potential security breaches and suspicious activities.
    """
    
    def __init__(self):
        self.suspicious_patterns = [
            r'select.*from.*users',  # SQL injection attempts
            r'drop.*table',  # SQL injection attempts
            r'<script.*>',  # XSS attempts
            r'javascript:',  # XSS attempts
            r'\.\.\/\.\.\/',  # Directory traversal
            r'etc\/passwd',  # Unix system file access
            r'windows\\system32',  # Windows system file access
            r'union.*select',  # SQL injection
            r'or.*1.*=.*1',  # SQL injection bypass
            r'admin.*--',  # SQL injection comment bypass
        ]
    
    def analyze_request(self, request, response=None):
        """
        Analyze HTTP request for suspicious patterns.
        """
        suspicious_indicators = []
        
        # Check request parameters
        if hasattr(request, 'GET') and request.GET:
            for key, value in request.GET.items():
                if self.contains_suspicious_pattern(str(value)):
                    suspicious_indicators.append({
                        'type': 'suspicious_get_param',
                        'param': key,
                        'value': str(value)[:100]  # Limit length for logging
                    })
        
        if hasattr(request, 'POST') and request.POST:
            for key, value in request.POST.items():
                if self.contains_suspicious_pattern(str(value)):
                    suspicious_indicators.append({
                        'type': 'suspicious_post_param',
                        'param': key,
                        'value': str(value)[:100]
                    })
        
        # Check headers for suspicious patterns
        for header, value in request.META.items():
            if header.startswith('HTTP_') and self.contains_suspicious_pattern(str(value)):
                suspicious_indicators.append({
                    'type': 'suspicious_header',
                    'header': header,
                    'value': str(value)[:100]
                })
        
        # Check user agent for suspicious patterns
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        if self.contains_suspicious_pattern(user_agent):
            suspicious_indicators.append({
                'type': 'suspicious_user_agent',
                'value': user_agent[:100]
            })
        
        return suspicious_indicators
    
    def contains_suspicious_pattern(self, text):
        """Check if text contains suspicious patterns."""
        text_lower = text.lower()
        for pattern in self.suspicious_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False

    def detect_sql_injection(self, text):
        if not text:
            return None
        patterns = [
            r"\b(or|and)\b\s*['\"]?\d+['\"]?\s*=\s*['\"]?\d+['\"]?",
            r"union\s+select",
            r"drop\s+table",
            r"select\s+.*\s+from\s+",
            r"';\s*--",
            r"--\s*$",
            r"'\s*--",
        ]
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return {'type': 'sql_injection', 'payload': text}
        return None

    def detect_xss(self, text):
        if not text:
            return None
        patterns = [
            r"<\s*script\b",
            r"javascript\s*:",
            r"onerror\s*=",
            r"onload\s*=",
            r"<\s*iframe\b[^>]*\bsrc\s*=\s*['\"]?\s*javascript\s*:",
        ]
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return {'type': 'xss', 'payload': text}
        return None

    def detect_directory_traversal(self, text):
        if not text:
            return None
        patterns = [
            r"\.\./",
            r"\.\.\\",
            r"/etc/passwd",
            r"windows\\system32",
            r"file:///",
        ]
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return {'type': 'directory_traversal', 'payload': text}
        return None
    
    def detect_brute_force_login(self, username, ip_address, failed_attempts_threshold=5, time_window_minutes=15):
        """
        Detect brute force login attempts.
        """
        time_threshold = timezone.now() - timedelta(minutes=time_window_minutes)
        
        # Count failed login attempts from this IP for this username
        failed_attempts = VendorAuditLog.objects.filter(
            action_type='login_failed',
            ip_address=ip_address,
            details__username=username,
            created_at__gte=time_threshold
        ).count()
        
        if failed_attempts >= failed_attempts_threshold:
            logger.warning(f"Potential brute force detected from {ip_address} for user {username}")
            return {
                'type': 'brute_force_login',
                'ip_address': ip_address,
                'username': username,
                'failed_attempts': failed_attempts,
                'time_window_minutes': time_window_minutes
            }
        
        return None

    def detect_account_takeover(self, user_id, current_ip, current_user_agent, usual_ip, usual_user_agent):
        if current_ip != usual_ip or current_user_agent != usual_user_agent:
            return {
                'type': 'account_takeover',
                'user_id': user_id,
                'details': 'unusual login context detected'
            }
        return None

    def detect_data_exfiltration(self, user_id, ip_address, access_threshold=10, time_window_minutes=5):
        time_threshold = timezone.now() - timedelta(minutes=time_window_minutes)
        access_count = VendorAuditLog.objects.filter(
            action_type='data_access',
            user_id=user_id,
            ip_address=ip_address,
            created_at__gte=time_threshold,
        ).count()
        if access_count >= access_threshold:
            return {
                'type': 'data_exfiltration',
                'user_id': user_id,
                'ip_address': ip_address,
                'access_count': access_count,
                'time_window_minutes': time_window_minutes,
            }
        return None
    
    def log_security_incident(self, incident_details, severity='medium'):
        """
        Log security incident and take appropriate action.
        """
        logger.critical(f"Security incident detected: {incident_details}")
        
        # Log to vendor audit log if user is involved
        if 'user' in incident_details:
            try:
                user = User.objects.get(email=incident_details['user'])
                vendor = BusinessPartner.objects.filter(user=user, type='vendor').first()
                if vendor:
                    VendorAuditLogger.log_security_event(user=user, vendor=vendor, event_type='suspicious_activity', severity=severity, details=incident_details)
            except User.DoesNotExist:
                pass
        
        # Take action based on severity
        if severity == 'critical':
            # Block IP address or user account
            self.take_defensive_action(incident_details)
    
    def take_defensive_action(self, incident_details):
        """
        Take defensive action against detected threats.
        """
        if 'ip_address' in incident_details:
            # In a real implementation, you might:
            # - Add IP to blacklist
            # - Rate limit the IP
            # - Block the IP at firewall level
            logger.critical(f"Taking defensive action against IP: {incident_details['ip_address']}")
        
        if 'user' in incident_details:
            # In a real implementation, you might:
            # - Lock user account
            # - Force password reset
            # - Require additional verification
            logger.critical(f"Taking defensive action against user: {incident_details['user']}")


# Global instance for easy access
breach_detector = BreachDetectionEngine()
