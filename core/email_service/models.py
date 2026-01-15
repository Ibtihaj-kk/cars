"""
Email Service Models

Database models for email queuing, tracking, and templates.
"""

import uuid
from django.db import models
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder


class EmailQueue(models.Model):
    """Model for queuing and tracking email delivery."""
    
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('scheduled', 'Scheduled'),
        ('processing', 'Processing'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    message_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    email_type = models.CharField(max_length=50, help_text="Type of email (e.g., verification, welcome)")
    
    # Recipient information
    to_email = models.EmailField()
    cc_emails = models.JSONField(default=list, blank=True)
    bcc_emails = models.JSONField(default=list, blank=True)
    
    # Email content
    subject = models.CharField(max_length=255)
    template_name = models.CharField(max_length=100, help_text="Name of the email template")
    context = models.JSONField(encoder=DjangoJSONEncoder, default=dict, blank=True)
    
    # Sender information
    from_email = models.EmailField(null=True, blank=True)
    reply_to = models.EmailField(null=True, blank=True)
    
    # Attachments
    attachments = models.JSONField(default=list, blank=True, help_text="List of attachment metadata")
    
    # Scheduling and priority
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    scheduled_time = models.DateTimeField(null=True, blank=True)
    
    # Status tracking
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='queued')
    retry_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processing_completed_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    metadata = models.JSONField(encoder=DjangoJSONEncoder, default=dict, blank=True)
    
    class Meta:
        db_table = 'email_queue'
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['created_at']),
            models.Index(fields=['to_email']),
            models.Index(fields=['email_type']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.email_type} to {self.to_email} ({self.status})"
    
    def can_retry(self, max_retries=3):
        """Check if this email can be retried."""
        return self.status == 'failed' and self.retry_count < max_retries
    
    def is_expired(self, expiration_hours=72):
        """Check if this email queue item has expired."""
        if self.status in ['sent', 'cancelled']:
            return False
        
        age = timezone.now() - self.created_at
        return age.total_seconds() > expiration_hours * 3600


class EmailTemplate(models.Model):
    """Model for storing email templates with versioning."""
    
    TEMPLATE_TYPES = [
        ('html', 'HTML'),
        ('text', 'Plain Text'),
        ('both', 'Both'),
    ]
    
    name = models.CharField(max_length=100, unique=True, help_text="Template identifier")
    description = models.TextField(blank=True)
    subject_template = models.CharField(max_length=255, help_text="Subject template (supports variables)")
    
    # Template content
    html_content = models.TextField(blank=True, help_text="HTML template content")
    text_content = models.TextField(blank=True, help_text="Plain text template content")
    
    # Template configuration
    template_type = models.CharField(max_length=10, choices=TEMPLATE_TYPES, default='both')
    is_active = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)
    
    # Default context variables
    default_context = models.JSONField(encoder=DjangoJSONEncoder, default=dict, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'email_templates'
        unique_together = ['name', 'version']
        ordering = ['name', '-version']
    
    def __str__(self):
        return f"{self.name} (v{self.version})"
    
    def render_subject(self, context=None):
        """Render the subject template with context."""
        from django.template import Template, Context
        
        context = {**self.default_context, **(context or {})}
        template = Template(self.subject_template)
        return template.render(Context(context))
    
    def render_content(self, context=None, content_type='html'):
        """Render the template content with context."""
        from django.template import Template, Context
        
        context = {**self.default_context, **(context or {})}
        
        if content_type == 'html':
            template = Template(self.html_content)
        else:
            template = Template(self.text_content)
            
        return template.render(Context(context))


class EmailAnalytics(models.Model):
    """Model for tracking email delivery analytics."""
    
    EVENT_TYPES = [
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('opened', 'Opened'),
        ('clicked', 'Clicked'),
        ('bounced', 'Bounced'),
        ('complained', 'Complained'),
        ('unsubscribed', 'Unsubscribed'),
    ]
    
    message_id = models.UUIDField()
    event_type = models.CharField(max_length=15, choices=EVENT_TYPES)
    event_data = models.JSONField(encoder=DjangoJSONEncoder, default=dict, blank=True)
    
    # Provider information
    provider = models.CharField(max_length=50, blank=True)
    provider_message_id = models.CharField(max_length=255, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'email_analytics'
        indexes = [
            models.Index(fields=['message_id']),
            models.Index(fields=['event_type']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.event_type} for {self.message_id}"
