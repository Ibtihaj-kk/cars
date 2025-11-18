"""
Secure session handling utilities.
"""
import hashlib
import secrets
import time
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone


def hash_session_key(session_key):
    """Hash session key for secure storage"""
    # Add salt to prevent rainbow table attacks
    salt = getattr(settings, 'SESSION_SALT', 'default_session_salt')
    return hashlib.sha256(f"{session_key}{salt}".encode()).hexdigest()


def generate_secure_token(length=32):
    """Generate a cryptographically secure token"""
    return secrets.token_urlsafe(length)


def validate_session_age(session_key, max_age_seconds=3600):
    """
    Validate that a session is not too old.
    
    Args:
        session_key: The session key to validate
        max_age_seconds: Maximum age in seconds (default: 1 hour)
    
    Returns:
        bool: True if session is valid and not too old
    """
    try:
        session = Session.objects.get(session_key=session_key)
        # Check if session has expired
        if session.expire_date < timezone.now():
            return False
        
        # Check session age
        session_data = session.get_decoded()
        created_at = session_data.get('_session_created_at', 0)
        current_time = time.time()
        
        if current_time - created_at > max_age_seconds:
            return False
            
        return True
    except Session.DoesNotExist:
        return False


def track_session_activity(session_key, action):
    """
    Track session activity for security monitoring.
    
    Args:
        session_key: The session key
        action: The action being performed
    """
    cache_key = f"session_activity_{session_key}"
    activity_data = cache.get(cache_key, {
        'actions': [],
        'suspicious_count': 0,
        'last_activity': time.time()
    })
    
    # Add current action
    activity_data['actions'].append({
        'action': action,
        'timestamp': time.time()
    })
    
    # Keep only last 100 actions
    activity_data['actions'] = activity_data['actions'][-100:]
    activity_data['last_activity'] = time.time()
    
    # Check for suspicious patterns
    if _detect_suspicious_activity(activity_data['actions']):
        activity_data['suspicious_count'] += 1
    
    # Store in cache for 24 hours
    cache.set(cache_key, activity_data, 86400)
    
    return activity_data


def _detect_suspicious_activity(actions):
    """
    Detect suspicious activity patterns in session actions.
    
    Args:
        actions: List of action dictionaries
    
    Returns:
        bool: True if suspicious activity detected
    """
    if len(actions) < 5:
        return False
    
    # Check for rapid sequential actions (potential bot)
    recent_actions = actions[-10:]
    if len(recent_actions) >= 5:
        time_diffs = []
        for i in range(1, len(recent_actions)):
            time_diffs.append(recent_actions[i]['timestamp'] - recent_actions[i-1]['timestamp'])
        
        # If average time between actions is less than 0.5 seconds, suspicious
        if time_diffs and sum(time_diffs) / len(time_diffs) < 0.5:
            return True
    
    # Check for repeated failed actions
    failed_actions = [a for a in actions[-20:] if 'failed' in a['action']]
    if len(failed_actions) > 10:
        return True
    
    return False


def verify_session_key(session_key, stored_hash):
    """Verify session key against stored hash"""
    return hash_session_key(session_key) == stored_hash


class SecureSessionMixin:
    """Mixin for models that need to store session references with enhanced security"""
    
    def set_session(self, session_key):
        """Store hashed session key with additional security checks"""
        # Validate session age and activity
        if not validate_session_age(session_key):
            raise ValueError("Session is too old or invalid")
        
        # Track session activity
        track_session_activity(session_key, 'session_set')
        
        # Store hashed session key
        self.session_hash = hash_session_key(session_key)
        self.save()
    
    def verify_session(self, session_key):
        """Verify session key matches stored hash with security checks"""
        if not hasattr(self, 'session_hash') or not self.session_hash:
            return False
        
        # Validate session age
        if not validate_session_age(session_key):
            return False
        
        # Track verification attempt
        track_session_activity(session_key, 'session_verify')
        
        # Verify against stored hash
        return verify_session_key(session_key, self.session_hash)
    
    def clear_session(self):
        """Clear session hash and track activity"""
        if hasattr(self, 'session_hash') and self.session_hash:
            # Try to track the clearing activity
            try:
                # We can't get the original session key, but we can log the action
                track_session_activity('unknown', 'session_cleared')
            except:
                pass  # Don't fail if we can't track
        
        self.session_hash = None
        self.save()
    
    def is_session_suspicious(self, session_key):
        """Check if session shows suspicious activity patterns"""
        activity_data = track_session_activity(session_key, 'suspicious_check')
        return activity_data.get('suspicious_count', 0) > 3
    
    def get_session_activity_summary(self, session_key):
        """Get activity summary for a session"""
        return track_session_activity(session_key, 'summary_request')