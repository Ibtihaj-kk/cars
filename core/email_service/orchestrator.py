# """
# Email Orchestrator Service

# Central service for handling all email operations in the application.
# Provides unified API for sending emails with queuing, retries, and tracking.
# ""__

import logging
import uuid
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.utils import timezone

from .providers import get_email_provider
from .models import EmailQueue

logger = logging.getLogger(__name__)


def send_email(
    email_type: str,
    to_email: str,
    subject: str,
    template_name: str,
    context: Optional[Dict[str, Any]] = None,
    from_email: Optional[str] = None,
    reply_to: Optional[str] = None,
    cc_emails: Optional[List[str]] = None,
    bcc_emails: Optional[List[str]] = None,
    attachments: Optional[List[Dict[str, Any]]] = None,
    priority: str = 'normal',
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Send an email immediately or queue it for processing.
    
    Args:
        email_type: Type of email (e.g., 'verification', 'welcome', 'notification')
        to_email: Recipient email address
        subject: Email subject
        template_name: Name of the email template
        context: Template context variables
        from_email: Sender email address
        reply_to: Reply-to email address
        cc_emails: List of CC email addresses
        bcc_emails: List of BCC email addresses
        attachments: List of file attachments
        priority: Email priority ('low', 'normal', 'high', 'critical')
        metadata: Additional metadata for tracking
        
    Returns:
        str: Unique message ID for tracking
    """
    message_id = str(uuid.uuid4())
    context = context or {}
    metadata = metadata or {}
    
    # Add default metadata
    metadata.update({
        'message_id': message_id,
        'email_type': email_type,
        'sent_at': timezone.now().isoformat(),
        'app_name': 'CarSyncro'
    })
    
    # Create email queue entry
    email_queue = EmailQueue.objects.create(
        message_id=message_id,
        email_type=email_type,
        to_email=to_email,
        subject=subject,
        template_name=template_name,
        context=context,
        from_email=from_email,
        reply_to=reply_to,
        cc_emails=cc_emails or [],
        bcc_emails=bcc_emails or [],
        attachments=attachments or [],
        priority=priority,
        metadata=metadata,
        status='queued'
    )
    
    # Process immediately based on priority
    if priority in ['high', 'critical']:
        process_email_queue_item(email_queue)
    else:
        # For normal/low priority, they'll be processed by the queue worker
        logger.info(f"Email queued for processing: {message_id}")
    
    return message_id


def send_email_async(
    email_type: str,
    to_email: str,
    subject: str,
    template_name: str,
    context: Optional[Dict[str, Any]] = None,
    **kwargs
) -> str:
    """
    Queue an email for asynchronous processing.
    
    This is the preferred method for non-critical emails to avoid
    blocking the request-response cycle.
    """
    return send_email(email_type, to_email, subject, template_name, context, 
                     priority='normal', **kwargs)


def schedule_email(
    email_type: str,
    to_email: str,
    subject: str,
    template_name: str,
    scheduled_time: timezone.datetime,
    context: Optional[Dict[str, Any]] = None,
    **kwargs
) -> str:
    """
    Schedule an email to be sent at a specific time.
    
    Args:
        scheduled_time: When the email should be sent
        
    Returns:
        str: Unique message ID for tracking
    """
    message_id = str(uuid.uuid4())
    context = context or {}
    
    # Create scheduled email entry
    email_queue = EmailQueue.objects.create(
        message_id=message_id,
        email_type=email_type,
        to_email=to_email,
        subject=subject,
        template_name=template_name,
        context=context,
        scheduled_time=scheduled_time,
        status='scheduled',
        **kwargs
    )
    
    logger.info(f"Email scheduled for {scheduled_time}: {message_id}")
    return message_id


def process_email_queue_item(queue_item: EmailQueue) -> bool:
    """
    Process a single email queue item.
    
    Args:
        queue_item: EmailQueue instance to process
        
    Returns:
        bool: True if email was sent successfully
    """
    try:
        # Update status to processing
        queue_item.status = 'processing'
        queue_item.processing_started_at = timezone.now()
        queue_item.save()
        
        # Get email provider
        provider = get_email_provider()
        
        if not provider.is_configured():
            logger.warning(f"Email provider not configured, skipping: {queue_item.message_id}")
            queue_item.status = 'failed'
            queue_item.error_message = 'Email provider not configured'
            queue_item.save()
            return False
        
        # Render email templates
        from django.template.loader import render_to_string
        
        html_content = render_to_string(
            f'emails/{queue_item.template_name}.html',
            queue_item.context
        )
        
        plain_text_content = render_to_string(
            f'emails/{queue_item.template_name}.txt',
            queue_item.context
        )
        
        # Send email
        success = provider.send(
            to_email=queue_item.to_email,
            subject=queue_item.subject,
            html_content=html_content,
            plain_text_content=plain_text_content,
            from_email=queue_item.from_email,
            reply_to=queue_item.reply_to,
            cc_emails=queue_item.cc_emails,
            bcc_emails=queue_item.bcc_emails,
            attachments=queue_item.attachments,
            metadata=queue_item.metadata
        )
        
        if success:
            queue_item.status = 'sent'
            queue_item.sent_at = timezone.now()
            queue_item.retry_count = 0
            logger.info(f"Email sent successfully: {queue_item.message_id}")
        else:
            queue_item.status = 'failed'
            queue_item.retry_count += 1
            queue_item.error_message = 'Provider send failed'
            logger.error(f"Email failed to send: {queue_item.message_id}")
        
        queue_item.processing_completed_at = timezone.now()
        queue_item.save()
        
        return success
        
    except Exception as e:
        logger.error(f"Error processing email queue item {queue_item.message_id}: {e}")
        
        # Update queue item with error
        queue_item.status = 'failed'
        queue_item.error_message = str(e)
        queue_item.retry_count += 1
        queue_item.processing_completed_at = timezone.now()
        queue_item.save()
        
        return False


def get_email_status(message_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the status of an email by message ID.
    
    Args:
        message_id: Unique message ID
        
    Returns:
        Optional[Dict]: Email status information or None if not found
    """
    try:
        queue_item = EmailQueue.objects.get(message_id=message_id)
        return {
            'message_id': queue_item.message_id,
            'status': queue_item.status,
            'to_email': queue_item.to_email,
            'subject': queue_item.subject,
            'created_at': queue_item.created_at,
            'sent_at': queue_item.sent_at,
            'error_message': queue_item.error_message,
            'retry_count': queue_item.retry_count
        }
    except EmailQueue.DoesNotExist:
        return None


def retry_failed_emails(max_retries: int = 3) -> int:
    """
    Retry failed email queue items.
    
    Args:
        max_retries: Maximum number of retry attempts
        
    Returns:
        int: Number of emails retried
    """
    failed_emails = EmailQueue.objects.filter(
        status='failed',
        retry_count__lt=max_retries
    )
    
    retry_count = 0
    for email in failed_emails:
        if process_email_queue_item(email):
            retry_count += 1
    
    return retry_count