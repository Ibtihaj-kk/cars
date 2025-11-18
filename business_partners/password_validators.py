"""
Custom password validators for enhanced security.
"""
import re
import requests
import hashlib
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class StrongPasswordValidator:
    """
    Validates that passwords meet strong security requirements:
    - At least 12 characters
    - Contains uppercase, lowercase, numbers, and special characters
    - Not similar to username or email
    - Not a common breached password
    """
    
    def __init__(self, min_length=12):
        self.min_length = min_length
    
    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                _("Password must be at least %(min_length)d characters long."),
                code='password_too_short',
                params={'min_length': self.min_length}
            )
        
        # Check for uppercase letters
        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                _("Password must contain at least one uppercase letter."),
                code='password_no_upper',
            )
        
        # Check for lowercase letters
        if not re.search(r'[a-z]', password):
            raise ValidationError(
                _("Password must contain at least one lowercase letter."),
                code='password_no_lower',
            )
        
        # Check for numbers
        if not re.search(r'[0-9]', password):
            raise ValidationError(
                _("Password must contain at least one number."),
                code='password_no_number',
            )
        
        # Check for special characters
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError(
                _("Password must contain at least one special character."),
                code='password_no_special',
            )
        
        # Check for similarity to username/email
        if user:
            if user.username.lower() in password.lower():
                raise ValidationError(
                    _("Password is too similar to the username."),
                    code='password_too_similar',
                )
            
            if user.email and user.email.split('@')[0].lower() in password.lower():
                raise ValidationError(
                    _("Password is too similar to the email address."),
                    code='password_too_similar',
                )
        
        # Check against common password patterns
        common_patterns = [
            r'123+',  # Sequential numbers
            r'abc+',  # Sequential letters
            r'qwe+',  # Keyboard patterns
            r'password',  # Common words
            r'admin',  # Common admin terms
            r'welcome',  # Common welcome terms
        ]
        
        for pattern in common_patterns:
            if re.search(pattern, password, re.IGNORECASE):
                raise ValidationError(
                    _("Password contains common patterns and is not secure."),
                    code='password_too_common',
                )
        
        # Check if password has been breached using Have I Been Pwned API
        if self.is_breached_password(password):
            raise ValidationError(
                _("This password has been exposed in data breaches and should not be used."),
                code='password_breached',
            )
    
    def is_breached_password(self, password):
        """
        Check if password has been breached using Have I Been Pwned API.
        Uses k-anonymity to only send first 5 characters of SHA1 hash.
        """
        try:
            # Generate SHA1 hash of password
            sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
            prefix = sha1_hash[:5]
            suffix = sha1_hash[5:]
            
            # Make API request with k-anonymity
            response = requests.get(
                f'https://api.pwnedpasswords.com/range/{prefix}',
                timeout=5,
                headers={'User-Agent': 'Cars-Portal-Security-Check'}
            )
            
            if response.status_code == 200:
                # Check if our suffix is in the response
                for line in response.text.splitlines():
                    if line.startswith(suffix):
                        return True
                
                return False
            else:
                # If API is unavailable, don't block password creation
                return False
                
        except (requests.RequestException, TimeoutError):
            # If API is unavailable, don't block password creation
            return False
    
    def get_help_text(self):
        return _(
            "Your password must be at least 12 characters long and contain "
            "uppercase letters, lowercase letters, numbers, and special characters. "
            "It should not contain common patterns or be similar to your username/email."
        )


class PasswordHistoryValidator:
    """
    Validates that passwords haven't been used recently.
    Requires a password history model to track previous passwords.
    """
    
    def __init__(self, history_count=5):
        self.history_count = history_count
    
    def validate(self, password, user=None):
        if not user:
            return
        
        # Check recent password history
        from .models import PasswordHistory
        recent_passwords = PasswordHistory.objects.filter(
            user=user
        ).order_by('-created_at')[:self.history_count]
        
        from django.contrib.auth.hashers import check_password
        for history_entry in recent_passwords:
            if check_password(password, history_entry.password_hash):
                raise ValidationError(
                    _("You cannot reuse a password from your recent password history."),
                    code='password_reused',
                )
    
    def get_help_text(self):
        return _(
            "Your password cannot be the same as any of your last %(history_count)d passwords."
        ) % {'history_count': self.history_count}