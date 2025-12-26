"""
Signals for business partners app.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from .models import PasswordHistory
from .audit_logger import VendorAuditLogger
from .models import BusinessPartner

UserModel = get_user_model()

@receiver(pre_save, sender=UserModel)
def capture_previous_password(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        previous = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    instance._previous_password_hash = previous.password


@receiver(post_save, sender=UserModel)
def save_password_history(sender, instance, created, **kwargs):
    if created:
        if instance.password:
            PasswordHistory.objects.create(
                user=instance,
                password_hash=instance.password
            )
        return

    previous_password_hash = getattr(instance, '_previous_password_hash', None)
    if not previous_password_hash or previous_password_hash == instance.password:
        return

    PasswordHistory.objects.create(
        user=instance,
        password_hash=previous_password_hash
    )

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

    recent_password_changes = PasswordHistory.objects.filter(
        user=instance,
        created_at__gte=timezone.now() - timedelta(hours=1)
    ).count()

    if recent_password_changes < 3:
        return

    try:
        vendor = BusinessPartner.objects.filter(user=instance, type='vendor').first()
        if vendor:
            VendorAuditLogger.log_security_event(
                user=instance,
                vendor=vendor,
                event_type='suspicious_activity',
                details={
                    'activity_type': 'multiple_password_changes',
                    'changes_in_hour': recent_password_changes
                },
                severity='high'
            )
    except BusinessPartner.DoesNotExist:
        pass
