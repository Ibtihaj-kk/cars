"""
Enhanced admin authentication middleware for Cars Portal admin panel.
Provides session timeout, IP validation, and comprehensive security features.
"""
import logging
from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth import logout
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from .utils import get_client_ip, log_activity
from .models import ActivityLogType

logger = logging.getLogger('security')


class AdminSecurityMiddleware(MiddlewareMixin):
    """
    Enhanced security middleware for admin panel access.
    
    Features:
    - Session timeout management
    - IP address validation and tracking
    - Suspicious activity detection
    - Automatic logout on security violations
    - Comprehensive security logging
    """
    
    # Admin panel URL patterns that require enhanced security
    ADMIN_PANEL_PATHS = [
        '/admin-panel/',
        '/admin_panel/',
    ]
    
    # Session timeout in minutes (default: 30 minutes)
    SESSION_TIMEOUT = getattr(settings, 'ADMIN_SESSION_TIMEOUT', 30)
    
    # Maximum allowed IP changes per session
    MAX_IP_CHANGES = getattr(settings, 'ADMIN_MAX_IP_CHANGES', 2)
    
    def process_request(self, request):
        """Process incoming request for admin panel security."""
        
        # Check if this is an admin panel request
        if not self._is_admin_panel_request(request):
            return None
            
        # Skip security checks for login/logout pages
        if self._is_auth_page(request):
            return None
            
        # Check if user is authenticated and has admin privileges
        if not self._is_admin_user(request.user):
            return self._redirect_to_login(request, 'Authentication required for admin panel access')
            
        # Perform security checks
        security_violation = self._check_security_violations(request)
        if security_violation:
            return security_violation
            
        # Update session activity
        self._update_session_activity(request)
        
        return None
    
    def _is_admin_panel_request(self, request):
        """Check if the request is for admin panel."""
        return any(request.path.startswith(path) for path in self.ADMIN_PANEL_PATHS)
    
    def _is_auth_page(self, request):
        """Check if the request is for authentication pages."""
        try:
            auth_paths = [
                reverse('admin_panel:login'),
                reverse('admin_panel:logout'),
            ]
            return request.path in auth_paths
        except Exception:
            # Fallback to path-based checking if reverse fails
            auth_paths = [
                '/admin-panel/login/',
                '/admin-panel/logout/',
                '/admin_panel/login/',
                '/admin_panel/logout/',
            ]
            return request.path in auth_paths
    
    def _is_admin_user(self, user):
        """Check if user has admin privileges."""
        return (
            user.is_authenticated and 
            (user.is_staff or user.is_superuser or user.role in ['admin', 'staff']) and
            not user.is_banned and 
            not user.is_suspended and 
            not user.is_deleted
        )
    
    def _check_security_violations(self, request):
        """Check for various security violations."""
        
        # Check session timeout
        timeout_violation = self._check_session_timeout(request)
        if timeout_violation:
            return timeout_violation
            
        # Check IP address consistency
        ip_violation = self._check_ip_consistency(request)
        if ip_violation:
            return ip_violation
            
        # Check for concurrent sessions (if enabled)
        concurrent_violation = self._check_concurrent_sessions(request)
        if concurrent_violation:
            return concurrent_violation
            
        return None
    
    def _check_session_timeout(self, request):
        """Check if admin session has timed out."""
        last_activity = request.session.get('admin_last_activity')
        
        if last_activity:
            last_activity_time = timezone.datetime.fromisoformat(last_activity)
            timeout_threshold = timezone.now() - timedelta(minutes=self.SESSION_TIMEOUT)
            
            if last_activity_time < timeout_threshold:
                logger.warning(
                    f"Admin session timeout for user {request.user.email} "
                    f"from IP {get_client_ip(request)}"
                )
                
                # Log the timeout event
                log_activity(
                    user=request.user,
                    action_type=ActivityLogType.LOGOUT,
                    description="Admin session timeout",
                    request=request,
                    data={'reason': 'session_timeout'}
                )
                
                return self._redirect_to_login(
                    request, 
                    'Your admin session has expired due to inactivity. Please log in again.'
                )
        
        return None
    
    def _check_ip_consistency(self, request):
        """Check for suspicious IP address changes."""
        current_ip = get_client_ip(request)
        session_ips = request.session.get('admin_session_ips', [])
        
        if current_ip not in session_ips:
            session_ips.append(current_ip)
            request.session['admin_session_ips'] = session_ips
            
            # Check if too many IP changes
            if len(session_ips) > self.MAX_IP_CHANGES:
                logger.warning(
                    f"Suspicious IP changes detected for admin user {request.user.email}. "
                    f"IPs: {session_ips}"
                )
                
                # Log the suspicious activity
                log_activity(
                    user=request.user,
                    action_type=ActivityLogType.OTHER,
                    description="Suspicious IP address changes detected",
                    request=request,
                    data={
                        'reason': 'multiple_ip_changes',
                        'ip_addresses': session_ips,
                        'current_ip': current_ip
                    }
                )
                
                return self._redirect_to_login(
                    request,
                    'Suspicious activity detected. Please log in again for security.'
                )
            
            # Log IP change for audit
            if len(session_ips) > 1:
                log_activity(
                    user=request.user,
                    action_type=ActivityLogType.OTHER,
                    description=f"Admin IP address changed to {current_ip}",
                    request=request,
                    data={'previous_ips': session_ips[:-1]}
                )
        
        return None
    
    def _check_concurrent_sessions(self, request):
        """Check for concurrent admin sessions (if enabled)."""
        # This can be implemented based on specific requirements
        # For now, we'll skip this check
        return None
    
    def _update_session_activity(self, request):
        """Update session activity timestamp."""
        request.session['admin_last_activity'] = timezone.now().isoformat()
        
        # Initialize IP tracking if not exists
        if 'admin_session_ips' not in request.session:
            request.session['admin_session_ips'] = [get_client_ip(request)]
    
    def _redirect_to_login(self, request, message):
        """Redirect to login page with security message."""
        # Logout the user
        logout(request)
        
        # Add message
        messages.warning(request, message)
        
        # Redirect to login page
        try:
            login_url = reverse('admin_panel:login')
        except Exception:
            # Fallback to hardcoded path if reverse fails
            login_url = '/admin-panel/login/'
        
        return redirect(f"{login_url}?next={request.path}")


class AdminActivityTrackingMiddleware(MiddlewareMixin):
    """
    Middleware to track admin panel activity for audit purposes.
    """
    
    def process_request(self, request):
        """Track admin panel requests."""
        
        # Only track admin panel requests
        if not any(request.path.startswith(path) for path in AdminSecurityMiddleware.ADMIN_PANEL_PATHS):
            return None
            
        # Only track authenticated admin users
        if not (request.user.is_authenticated and 
                (request.user.is_staff or request.user.is_superuser)):
            return None
            
        # Skip tracking for certain paths (like static files, AJAX calls)
        skip_paths = ['/static/', '/media/', '/api/']
        if any(request.path.startswith(path) for path in skip_paths):
            return None
            
        # Log the admin panel access
        log_activity(
            user=request.user,
            action_type=ActivityLogType.VIEW,
            description=f"Accessed admin panel page: {request.path}",
            request=request,
            data={
                'method': request.method,
                'path': request.path,
                'query_params': dict(request.GET) if request.GET else None
            }
        )
        
        return None


class AdminBruteForceProtectionMiddleware(MiddlewareMixin):
    """
    Middleware to protect against brute force attacks on admin panel.
    """
    
    def process_request(self, request):
        """Check for brute force attempts."""
        
        # This middleware works in conjunction with django-axes
        # Additional custom logic can be added here if needed
        
        return None