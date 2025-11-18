"""
Signals for business partners app.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from datetime import timedelta
from .models import PasswordHistory
from .audit_logger import VendorAuditLogger
from .models import BusinessPartner


@receiver(post_save, sender=User)
def save_password_history(sender, instance, created, **kwargs):
    """
    Save password history when user password changes.
    This signal should be connected to the User model's password field changes.
    """
    # Check if password was changed (this is a simplified check)
    # In a real implementation, you'd want to check if the password field was actually modified
    if not created and instance.password:
        # Create password history entry
        PasswordHistory.objects.create(
            user=instance,
            password_hash=instance.password
        )
        
        # Log password change for security auditing
        try:
            vendor = BusinessPartner.objects.filter(user=instance, type='vendor').first()
            if vendor:
                VendorAuditLogger.log_security_event(
                    vendor=vendor,
                    action='security_password_changed',
                    details={'source': 'user_password_change'}
                )
        except BusinessPartner.DoesNotExist:
            pass


@receiver(post_save, sender=User)
def check_suspicious_activity(sender, instance, created, **kwargs):
    """
    Monitor for suspicious user activity patterns.
    """
    if created:
        return
    
    # Check for multiple password changes in short time period
    recent_password_changes = PasswordHistory.objects.filter(
        user=instance,
        created_at__gte=timezone.now() - timedelta(hours=1)
    ).count()
    
    if recent_password_changes >= 3:
        # Log suspicious activity
        try:
            vendor = BusinessPartner.objects.filter(user=instance, type='vendor').first()
            if vendor:
                VendorAuditLogger.log_security_event(
                    vendor=vendor,
                    action='security_suspicious_activity',
                    details={
                        'activity_type': 'multiple_password_changes',
                        'changes_in_hour': recent_password_changes
                    },
                    severity='high'
                )
        except BusinessPartner.DoesNotExist:
            pass