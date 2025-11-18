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
    
    def detect_brute_force_login(self, username, ip_address, failed_attempts_threshold=5, time_window_minutes=15):
        """
        Detect brute force login attempts.
        """
        time_threshold = timezone.now() - timedelta(minutes=time_window_minutes)
        
        # Count failed login attempts from this IP for this username
        failed_attempts = VendorAuditLog.objects.filter(
            action_type='login_failed',
            ip_address=ip_address,
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
    
    def detect_account_takeover(self, user, current_ip, user_agent):
        """
        Detect potential account takeover based on unusual access patterns.
        """
        # Get recent successful logins
        recent_logins = VendorAuditLog.objects.filter(
            user=user,
            action_type='login_success',
            created_at__gte=timezone.now() - timedelta(days=30)
        ).order_by('-created_at')[:10]
        
        if not recent_logins:
            return None
        
        # Check for unusual IP address
        previous_ips = set(login.ip_address for login in recent_logins if login.ip_address)
        if current_ip not in previous_ips and len(previous_ips) > 0:
            logger.warning(f"Unusual IP address detected for user {user.email}: {current_ip}")
            return {
                'type': 'unusual_ip_address',
                'current_ip': current_ip,
                'previous_ips': list(previous_ips),
                'user': user.email
            }
        
        # Check for unusual user agent
        previous_agents = set(login.user_agent for login in recent_logins if login.user_agent)
        if user_agent not in previous_agents and len(previous_agents) > 0:
            logger.warning(f"Unusual user agent detected for user {user.email}: {user_agent}")
            return {
                'type': 'unusual_user_agent',
                'current_agent': user_agent,
                'previous_agents': list(previous_agents),
                'user': user.email
            }
        
        return None
    
    def detect_data_exfiltration(self, user, request_size_threshold=1000000):
        """
        Detect potential data exfiltration attempts.
        """
        # Check for large data requests from unusual sources
        # This is a simplified implementation
        
        recent_access = VendorAuditLog.objects.filter(
            user=user,
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).count()
        
        # If user is making unusually high number of requests
        if recent_access > 100:  # Threshold for suspicious activity
            logger.warning(f"High frequency access detected for user {user.email}: {recent_access} requests in 1 hour")
            return {
                'type': 'high_frequency_access',
                'request_count': recent_access,
                'user': user.email,
                'time_window': '1 hour'
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
                    VendorAuditLogger.log_security_event(
                        vendor=vendor,
                        action='security_suspicious_activity',
                        details=incident_details,
                        severity=severity
                    )
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