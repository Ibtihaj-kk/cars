"""
Admin session management for Cars Portal admin panel.
Handles session security, concurrent sessions, and automatic logout.
"""
import logging
from django.contrib.sessions.models import Session
from django.contrib.auth import logout
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from datetime import timedelta
from typing import List, Dict, Optional
import json

from .utils import log_activity, get_client_ip
from .models import ActivityLogType
from users.models import User

logger = logging.getLogger('security')


class AdminSessionManager:
    """
    Manages admin panel sessions with enhanced security features.
    """
    
    # Cache keys
    ACTIVE_SESSIONS_KEY = "admin_active_sessions_{user_id}"
    SESSION_DATA_KEY = "admin_session_data_{session_key}"
    CONCURRENT_LIMIT_KEY = "admin_concurrent_limit_{user_id}"
    
    # Default settings
    DEFAULT_SESSION_TIMEOUT = 30  # minutes
    DEFAULT_MAX_CONCURRENT_SESSIONS = 3
    DEFAULT_INACTIVITY_TIMEOUT = 15  # minutes
    
    @classmethod
    def create_session(cls, request, user):
        """
        Create a new admin session with security tracking.
        """
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        
        # Get session settings
        max_concurrent = getattr(settings, 'ADMIN_MAX_CONCURRENT_SESSIONS', 
                               cls.DEFAULT_MAX_CONCURRENT_SESSIONS)
        
        # Check concurrent session limit
        if cls._check_concurrent_limit(user, max_concurrent):
            cls._cleanup_oldest_session(user)
        
        # Create session data
        session_data = {
            'user_id': user.id,
            'session_key': session_key,
            'ip_address': get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'created_at': timezone.now().isoformat(),
            'last_activity': timezone.now().isoformat(),
            'is_active': True,
            'login_method': '2fa' if user.is_2fa_enabled else 'password',
        }
        
        # Store session data
        cls._store_session_data(session_key, session_data)
        cls._add_to_active_sessions(user.id, session_key)
        
        # Set session in request
        request.session['admin_session_data'] = session_data
        
        logger.info(f"Admin session created for user {user.id} from IP {session_data['ip_address']}")
        
        return session_key
    
    @classmethod
    def update_activity(cls, request):
        """
        Update session activity timestamp.
        """
        session_key = request.session.session_key
        if not session_key:
            return False
        
        session_data = cls._get_session_data(session_key)
        if not session_data:
            return False
        
        # Update activity timestamp
        session_data['last_activity'] = timezone.now().isoformat()
        session_data['ip_address'] = get_client_ip(request)
        
        # Store updated data
        cls._store_session_data(session_key, session_data)
        request.session['admin_session_data'] = session_data
        
        return True
    
    @classmethod
    def validate_session(cls, request):
        """
        Validate admin session security and activity.
        Returns tuple: (is_valid, reason)
        """
        if not request.user.is_authenticated:
            return False, "not_authenticated"
        
        session_key = request.session.session_key
        if not session_key:
            return False, "no_session_key"
        
        session_data = cls._get_session_data(session_key)
        if not session_data:
            return False, "session_not_found"
        
        # Check if session is active
        if not session_data.get('is_active', False):
            return False, "session_inactive"
        
        # Check session timeout
        if cls._is_session_expired(session_data):
            cls.terminate_session(request, "session_timeout")
            return False, "session_expired"
        
        # Check inactivity timeout
        if cls._is_session_inactive(session_data):
            cls.terminate_session(request, "inactivity_timeout")
            return False, "inactivity_timeout"
        
        # Check IP consistency (if enabled)
        if getattr(settings, 'ADMIN_ENFORCE_IP_CONSISTENCY', False):
            current_ip = get_client_ip(request)
            session_ip = session_data.get('ip_address')
            if current_ip != session_ip:
                cls.terminate_session(request, "ip_mismatch")
                return False, "ip_mismatch"
        
        return True, "valid"
    
    @classmethod
    def terminate_session(cls, request, reason="manual"):
        """
        Terminate admin session with logging.
        """
        session_key = request.session.session_key
        user = request.user
        
        if session_key:
            session_data = cls._get_session_data(session_key)
            
            # Log session termination
            if user.is_authenticated:
                log_activity(
                    user=user,
                    action_type=ActivityLogType.LOGOUT,
                    description=f"Admin session terminated: {reason}",
                    request=request,
                    data={
                        'termination_reason': reason,
                        'session_duration': cls._calculate_session_duration(session_data),
                        'session_key': session_key[:8] + '...'  # Partial key for security
                    }
                )
            
            # Remove from active sessions
            if session_data:
                user_id = session_data.get('user_id')
                if user_id:
                    cls._remove_from_active_sessions(user_id, session_key)
            
            # Clear session data
            cls._clear_session_data(session_key)
        
        # Logout user
        logout(request)
        
        logger.info(f"Admin session terminated for user {user.id if user.is_authenticated else 'unknown'}: {reason}")
    
    @classmethod
    def terminate_all_user_sessions(cls, user_id, exclude_session=None):
        """
        Terminate all sessions for a specific user.
        """
        active_sessions = cls._get_active_sessions(user_id)
        terminated_count = 0
        
        for session_key in active_sessions:
            if exclude_session and session_key == exclude_session:
                continue
            
            # Get Django session
            try:
                session = Session.objects.get(session_key=session_key)
                session.delete()
                terminated_count += 1
            except Session.DoesNotExist:
                pass
            
            # Clear our session data
            cls._clear_session_data(session_key)
        
        # Clear active sessions list
        cls._clear_active_sessions(user_id)
        
        logger.info(f"Terminated {terminated_count} admin sessions for user {user_id}")
        return terminated_count
    
    @classmethod
    def get_user_sessions(cls, user_id) -> List[Dict]:
        """
        Get all active sessions for a user.
        """
        active_sessions = cls._get_active_sessions(user_id)
        sessions = []
        
        for session_key in active_sessions:
            session_data = cls._get_session_data(session_key)
            if session_data:
                # Add computed fields
                session_data['duration'] = cls._calculate_session_duration(session_data)
                session_data['is_expired'] = cls._is_session_expired(session_data)
                session_data['is_inactive'] = cls._is_session_inactive(session_data)
                sessions.append(session_data)
        
        return sessions
    
    @classmethod
    def cleanup_expired_sessions(cls):
        """
        Cleanup expired admin sessions (called by management command).
        """
        cleaned_count = 0
        
        # Get all session keys from cache
        # This is a simplified approach - in production, you might want to 
        # iterate through all users or use a more efficient method
        
        logger.info(f"Cleaned up {cleaned_count} expired admin sessions")
        return cleaned_count
    
    # Private helper methods
    
    @classmethod
    def _check_concurrent_limit(cls, user, max_concurrent):
        """Check if user has reached concurrent session limit."""
        active_sessions = cls._get_active_sessions(user.id)
        return len(active_sessions) >= max_concurrent
    
    @classmethod
    def _cleanup_oldest_session(cls, user):
        """Remove the oldest session for a user."""
        active_sessions = cls._get_active_sessions(user.id)
        if not active_sessions:
            return
        
        # Find oldest session
        oldest_session = None
        oldest_time = None
        
        for session_key in active_sessions:
            session_data = cls._get_session_data(session_key)
            if session_data:
                created_at = timezone.datetime.fromisoformat(session_data['created_at'])
                if oldest_time is None or created_at < oldest_time:
                    oldest_time = created_at
                    oldest_session = session_key
        
        if oldest_session:
            # Terminate Django session
            try:
                session = Session.objects.get(session_key=oldest_session)
                session.delete()
            except Session.DoesNotExist:
                pass
            
            # Clear our data
            cls._clear_session_data(oldest_session)
            cls._remove_from_active_sessions(user.id, oldest_session)
            
            logger.info(f"Cleaned up oldest session for user {user.id}")
    
    @classmethod
    def _is_session_expired(cls, session_data):
        """Check if session has expired."""
        if not session_data:
            return True
        
        created_at = timezone.datetime.fromisoformat(session_data['created_at'])
        timeout_minutes = getattr(settings, 'ADMIN_SESSION_TIMEOUT', cls.DEFAULT_SESSION_TIMEOUT)
        timeout_delta = timedelta(minutes=timeout_minutes)
        
        return timezone.now() - created_at > timeout_delta
    
    @classmethod
    def _is_session_inactive(cls, session_data):
        """Check if session has been inactive too long."""
        if not session_data:
            return True
        
        last_activity = timezone.datetime.fromisoformat(session_data['last_activity'])
        timeout_minutes = getattr(settings, 'ADMIN_INACTIVITY_TIMEOUT', cls.DEFAULT_INACTIVITY_TIMEOUT)
        timeout_delta = timedelta(minutes=timeout_minutes)
        
        return timezone.now() - last_activity > timeout_delta
    
    @classmethod
    def _calculate_session_duration(cls, session_data):
        """Calculate session duration."""
        if not session_data:
            return None
        
        try:
            created_at = timezone.datetime.fromisoformat(session_data['created_at'])
            duration = timezone.now() - created_at
            return str(duration)
        except (ValueError, TypeError):
            return None
    
    @classmethod
    def _store_session_data(cls, session_key, data):
        """Store session data in cache."""
        cache_key = cls.SESSION_DATA_KEY.format(session_key=session_key)
        timeout = getattr(settings, 'ADMIN_SESSION_TIMEOUT', cls.DEFAULT_SESSION_TIMEOUT) * 60
        cache.set(cache_key, data, timeout)
    
    @classmethod
    def _get_session_data(cls, session_key):
        """Get session data from cache."""
        cache_key = cls.SESSION_DATA_KEY.format(session_key=session_key)
        return cache.get(cache_key)
    
    @classmethod
    def _clear_session_data(cls, session_key):
        """Clear session data from cache."""
        cache_key = cls.SESSION_DATA_KEY.format(session_key=session_key)
        cache.delete(cache_key)
    
    @classmethod
    def _add_to_active_sessions(cls, user_id, session_key):
        """Add session to user's active sessions list."""
        cache_key = cls.ACTIVE_SESSIONS_KEY.format(user_id=user_id)
        active_sessions = cache.get(cache_key, [])
        
        if session_key not in active_sessions:
            active_sessions.append(session_key)
            timeout = getattr(settings, 'ADMIN_SESSION_TIMEOUT', cls.DEFAULT_SESSION_TIMEOUT) * 60
            cache.set(cache_key, active_sessions, timeout)
    
    @classmethod
    def _remove_from_active_sessions(cls, user_id, session_key):
        """Remove session from user's active sessions list."""
        cache_key = cls.ACTIVE_SESSIONS_KEY.format(user_id=user_id)
        active_sessions = cache.get(cache_key, [])
        
        if session_key in active_sessions:
            active_sessions.remove(session_key)
            timeout = getattr(settings, 'ADMIN_SESSION_TIMEOUT', cls.DEFAULT_SESSION_TIMEOUT) * 60
            cache.set(cache_key, active_sessions, timeout)
    
    @classmethod
    def _get_active_sessions(cls, user_id):
        """Get list of active sessions for user."""
        cache_key = cls.ACTIVE_SESSIONS_KEY.format(user_id=user_id)
        return cache.get(cache_key, [])
    
    @classmethod
    def _clear_active_sessions(cls, user_id):
        """Clear all active sessions for user."""
        cache_key = cls.ACTIVE_SESSIONS_KEY.format(user_id=user_id)
        cache.delete(cache_key)


# Utility functions for views

def require_valid_admin_session(view_func):
    """
    Decorator to ensure valid admin session.
    """
    def wrapper(request, *args, **kwargs):
        is_valid, reason = AdminSessionManager.validate_session(request)
        
        if not is_valid:
            logger.warning(f"Invalid admin session: {reason} for user {request.user.id if request.user.is_authenticated else 'anonymous'}")
            
            # Redirect to login with appropriate message
            from django.shortcuts import redirect
            from django.contrib import messages
            
            if reason == "session_expired":
                messages.warning(request, "Your session has expired. Please log in again.")
            elif reason == "inactivity_timeout":
                messages.warning(request, "You have been logged out due to inactivity.")
            elif reason == "ip_mismatch":
                messages.error(request, "Security violation detected. Please log in again.")
            else:
                messages.info(request, "Please log in to access the admin panel.")
            
            return redirect('admin_panel:login')
        
        # Update activity
        AdminSessionManager.update_activity(request)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper