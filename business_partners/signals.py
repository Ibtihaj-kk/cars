"""
Django signals for business partners app.
Handles automatic email notifications for vendor application status changes.
"""

import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist

from .models import VendorApplication
from .email_service import get_vendor_email_service

logger = logging.getLogger('email_notifications')


@receiver(pre_save, sender=VendorApplication)
def capture_old_status(sender, instance, **kwargs):
    """
    Capture the old status before saving to compare with new status.
    This allows us to detect status changes and send appropriate notifications.
    """
    if instance.pk:
        try:
            old_instance = VendorApplication.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except ObjectDoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=VendorApplication)
def send_status_change_notification(sender, instance, created, **kwargs):
    """
    Send email notifications when vendor application status changes.
    
    Triggers notifications for:
    - Application submission (new applications)
    - Application approval
    - Application rejection
    - Changes requested
    """
    try:
        # Get email service
        email_service = get_vendor_email_service()
        
        if created:
            # New application submitted - send confirmation to applicant and notification to admin
            email_service.send_application_submitted_notification(instance)
            email_service.send_admin_new_application_notification(instance)
            logger.info(f"New application notifications sent for {instance.application_id}")
            return
        
        # Get old and new status for existing applications
        old_status = getattr(instance, '_old_status', None)
        new_status = instance.status
        
        # Skip if status hasn't changed
        if old_status == new_status:
            return
        
        # Send appropriate notification based on status change
        email_service.send_status_change_notification(
            application=instance,
            old_status=old_status,
            new_status=new_status
        )
        
        logger.info(
            f"Status change notification processed for application {instance.application_id}: "
            f"{old_status} -> {new_status}"
        )
        
    except Exception as e:
        logger.error(
            f"Failed to send notification for application {instance.application_id}: {e}"
        )


@receiver(post_save, sender=VendorApplication)
def log_application_activity(sender, instance, created, **kwargs):
    """
    Log vendor application activity for audit purposes.
    """
    if created:
        user_info = f"by {instance.user.email}" if instance.user else "anonymously"
        logger.info(f"New vendor application created: {instance.application_id} {user_info}")
    else:
        old_status = getattr(instance, '_old_status', None)
        if old_status and old_status != instance.status:
            logger.info(
                f"Vendor application {instance.application_id} status changed: "
                f"{old_status} -> {instance.status}"
                f"{f' by {instance.reviewed_by.email}' if instance.reviewed_by else ''}"
            )