from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class NotificationType(models.TextChoices):
    SYSTEM = 'system', 'System Notification'
    INQUIRY = 'inquiry', 'Inquiry Notification'
    LISTING = 'listing', 'Listing Notification'
    REVIEW = 'review', 'Review Notification'
    MESSAGE = 'message', 'Message Notification'
    SUBSCRIPTION = 'subscription', 'Subscription Notification'
    ACCOUNT = 'account', 'Account Notification'


class NotificationPriority(models.TextChoices):
    LOW = 'low', 'Low'
    MEDIUM = 'medium', 'Medium'
    HIGH = 'high', 'High'


class Notification(models.Model):
    """Model for user notifications."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices)
    title = models.CharField(max_length=255)
    message = models.TextField()
    priority = models.CharField(max_length=10, choices=NotificationPriority.choices, default=NotificationPriority.MEDIUM)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Generic relation to the object this notification is about
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, blank=True, null=True)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Action URL for the notification
    action_url = models.CharField(max_length=255, blank=True, null=True)
    
    # Additional data as JSON
    data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} for {self.user.email}"
    
    def mark_as_read(self):
        from django.utils import timezone
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at'])


class NotificationPreference(models.Model):
    """Model for user notification preferences."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preferences')
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    
    # Specific notification type preferences
    system_notifications = models.BooleanField(default=True)
    inquiry_notifications = models.BooleanField(default=True)
    listing_notifications = models.BooleanField(default=True)
    review_notifications = models.BooleanField(default=True)
    message_notifications = models.BooleanField(default=True)
    subscription_notifications = models.BooleanField(default=True)
    account_notifications = models.BooleanField(default=True)
    
    # Marketing preferences
    marketing_emails = models.BooleanField(default=True)
    newsletter_subscription = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'
    
    def __str__(self):
        return f"Notification preferences for {self.user.email}"


class DeviceToken(models.Model):
    """Model for storing user device tokens for push notifications."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='device_tokens')
    token = models.CharField(max_length=255, unique=True)
    device_type = models.CharField(max_length=20)  # e.g., 'ios', 'android', 'web'
    device_name = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'token']
    
    def __str__(self):
        return f"{self.device_type} token for {self.user.email}"
