from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from business_partners.models import BusinessPartner

User = get_user_model()

class MessageStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    SENT = 'sent', 'Sent'
    READ = 'read', 'Read'
    REPLIED = 'replied', 'Replied'
    ARCHIVED = 'archived', 'Archived'

class MessagePriority(models.TextChoices):
    LOW = 'low', 'Low'
    MEDIUM = 'medium', 'Medium'
    HIGH = 'high', 'High'
    URGENT = 'urgent', 'Urgent'

class MessageCategory(models.TextChoices):
    GENERAL = 'general', 'General'
    APPROVAL = 'approval', 'Approval Related'
    PERFORMANCE = 'performance', 'Performance'
    PAYMENT = 'payment', 'Payment'
    TECHNICAL = 'technical', 'Technical Support'
    COMPLAINT = 'complaint', 'Complaint'
    FEEDBACK = 'feedback', 'Feedback'

class AdminMessage(models.Model):
    """Messages between admin and vendors."""
    
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_admin_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_admin_messages')
    business_partner = models.ForeignKey(BusinessPartner, on_delete=models.CASCADE, related_name='admin_messages', null=True, blank=True)
    
    subject = models.CharField(max_length=255)
    content = models.TextField()
    
    status = models.CharField(max_length=20, choices=MessageStatus.choices, default=MessageStatus.DRAFT)
    priority = models.CharField(max_length=20, choices=MessagePriority.choices, default=MessagePriority.MEDIUM)
    category = models.CharField(max_length=20, choices=MessageCategory.choices, default=MessageCategory.GENERAL)
    
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # For threaded conversations
    parent_message = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    
    # Metadata
    attachments = models.JSONField(default=list, blank=True)  # List of attachment URLs
    metadata = models.JSONField(default=dict, blank=True)  # Additional metadata
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'status']),
            models.Index(fields=['business_partner', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.subject} - {self.sender.get_full_name()} to {self.recipient.get_full_name()}"
    
    def mark_as_read(self):
        """Mark message as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.status = MessageStatus.READ
            self.save(update_fields=['is_read', 'read_at', 'status'])
    
    def get_reply_count(self):
        """Get number of replies to this message."""
        return self.replies.count()
    
    def get_conversation_thread(self):
        """Get the entire conversation thread."""
        messages = []
        current = self
        
        # Go up to the root message
        while current.parent_message:
            current = current.parent_message
        
        # Collect all messages in the thread
        def collect_messages(message):
            messages.append(message)
            for reply in message.replies.all().order_by('created_at'):
                collect_messages(reply)
        
        collect_messages(current)
        return messages

class MessageTemplate(models.Model):
    """Predefined message templates for common scenarios."""
    
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=MessageCategory.choices, default=MessageCategory.GENERAL)
    subject = models.CharField(max_length=255)
    content = models.TextField()
    
    # Template variables that can be used
    variables = models.JSONField(default=list, blank=True)  # List of available variables
    
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.category})"
    
    def render_template(self, context):
        """Render template with provided context."""
        from django.template import Template, Context
        
        subject_template = Template(self.subject)
        content_template = Template(self.content)
        
        django_context = Context(context)
        
        return {
            'subject': subject_template.render(django_context),
            'content': content_template.render(django_context)
        }

class VendorNotification(models.Model):
    """System notifications for vendors."""
    
    vendor = models.ForeignKey(BusinessPartner, on_delete=models.CASCADE, related_name='notifications')
    message = models.ForeignKey(AdminMessage, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    
    title = models.CharField(max_length=255)
    content = models.TextField()
    type = models.CharField(max_length=20, choices=MessageCategory.choices, default=MessageCategory.GENERAL)
    
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Action URL if notification requires action
    action_url = models.CharField(max_length=500, null=True, blank=True)
    action_text = models.CharField(max_length=100, null=True, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['vendor', 'is_read']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.vendor.business_name}"
    
    def mark_as_read(self):
        """Mark notification as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def is_expired(self):
        """Check if notification has expired."""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False