# """
# Email Verification Handler

# Handles email verification workflows including 3-day verification logic
# and account blocking for unverified users.
# """

import logging
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model

from ..orchestrator import send_email
from ..models import EmailQueue

logger = logging.getLogger(__name__)
User = get_user_model()


class EmailVerificationHandler:
    """Handler for email verification workflows."""
    
    def __init__(self):
        self.orchestrator = send_email
    
    def send_verification_email(self, user, request=None):
        """
        Send email verification email to user.
        
        Args:
            user: User instance to send verification to
            request: Optional HttpRequest for building absolute URLs
        """
        try:
            # Generate verification token if not exists
            if not user.email_verification_token:
                user.generate_email_verification_token()
            
            # Build verification URL
            verification_url = self._build_verification_url(user, request)
            
            # Prepare email context
            context = {
                'user_name': user.first_name or user.email,
                'verification_url': verification_url,
                'expiration_hours': 72,  # 3 days
                'support_email': 'support@carsyncro.com',
                'company_name': 'CarSyncro',
            }
            
            # Queue verification email with high priority
            email_id = send_email(
                email_type='verification',
                to_email=user.email,
                template_name='email_verification',
                context=context,
                priority='high'
            )
            
            logger.info(f"Verification email queued for user {user.email}: {email_id}")
            return email_id
            
        except Exception as e:
            logger.error(f"Failed to send verification email to {user.email}: {e}")
            raise
    
    def _build_verification_url(self, user, request=None):
        """Build absolute verification URL."""
        if request:
            base_url = request.build_absolute_uri('/')
        else:
            # Fallback to settings or default
            from django.conf import settings
            base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        
        return f"{base_url.rstrip('/')}/verify-email/{user.email_verification_token}/"
    
    def check_verification_expiry(self):
        """
        Check all unverified users and block accounts that exceeded 3-day limit.
        Returns count of blocked users.
        """
        blocked_count = 0
        
        # Find users who haven't verified within 3 days
        expiry_time = timezone.now() - timedelta(days=3)
        unverified_users = User.objects.filter(
            is_verified=False,
            email_verification_sent_at__lte=expiry_time,
            is_active=True  # Only check active users
        )
        
        for user in unverified_users:
            try:
                self._block_unverified_user(user)
                blocked_count += 1
                logger.warning(f"Blocked unverified user {user.email} after 3 days")
            except Exception as e:
                logger.error(f"Failed to block unverified user {user.email}: {e}")
        
        return blocked_count
    
    def _block_unverified_user(self, user):
        """Block user account and send notification."""
        # Deactivate account
        user.is_active = False
        user.save(update_fields=['is_active'])
        
        # Send account blocked notification
        context = {
            'user': user,
            'blocked_at': timezone.now(),
            'support_email': 'support@carsyncro.com',
            'company_name': 'CarSyncro',
        }
        
        send_email(
            email_type='account_blocked',
            to_email=user.email,
            template_name='account_blocked_unverified',
            context=context,
            priority='normal'
        )
    
    def resend_verification_email(self, user, request=None):
        """
        Resend verification email with new token.
        
        Args:
            user: User instance
            request: Optional HttpRequest
        """
        # Generate new token
        user.generate_email_verification_token()
        
        # Send new verification email
        return self.send_verification_email(user, request)
    
    def verify_email_token(self, token):
        """
        Verify email token and activate user account.
        
        Args:
            token: Verification token from URL
            
        Returns:
            User instance if verified, None if invalid
        """
        try:
            user = User.objects.get(
                email_verification_token=token,
                is_verified=False
            )
            
            # Check if token is expired (optional additional check)
            if user.email_verification_sent_at:
                token_age = timezone.now() - user.email_verification_sent_at
                if token_age > timedelta(days=7):  # Token expires after 7 days
                    logger.warning(f"Expired verification token for user {user.email}")
                    return None
            
            # Mark user as verified
            user.is_verified = True
            user.email_verification_token = None
            user.save(update_fields=['is_verified', 'email_verification_token'])
            
            # Send welcome email
            self._send_welcome_email(user)
            
            logger.info(f"User {user.email} successfully verified email")
            return user
            
        except User.DoesNotExist:
            logger.warning(f"Invalid verification token: {token}")
            return None
        except Exception as e:
            logger.error(f"Error verifying token {token}: {e}")
            return None
    
    def _send_welcome_email(self, user):
        """Send welcome email after successful verification."""
        context = {
            'user': user,
            'login_url': '/login/',
            'support_email': 'support@carsyncro.com',
            'company_name': 'CarSyncro',
        }
        
        send_email(
            email_type='welcome',
            to_email=user.email,
            template_name='welcome_email',
            context=context,
            priority='normal'
        )
    
    def get_verification_stats(self):
        """Get statistics about email verification status."""
        total_users = User.objects.count()
        verified_users = User.objects.filter(is_verified=True).count()
        unverified_active = User.objects.filter(
            is_verified=False, 
            is_active=True
        ).count()
        
        # Users approaching 3-day limit (2.5+ days)
        warning_threshold = timezone.now() - timedelta(hours=66)  # 2.75 days
        approaching_limit = User.objects.filter(
            is_verified=False,
            is_active=True,
            email_verification_sent_at__lte=warning_threshold
        ).count()
        
        return {
            'total_users': total_users,
            'verified_users': verified_users,
            'unverified_active': unverified_active,
            'approaching_limit': approaching_limit,
            'verification_rate': (verified_users / total_users * 100) if total_users > 0 else 0
        }


# Global instance for easy access
verification_handler = EmailVerificationHandler()
