# """
# SMTP Email Provider

# Fallback email provider using Django's built-in SMTP functionality.
# Useful for local development or when external providers are unavailable.
# ""__

import logging
from typing import List, Optional, Dict, Any
from django.conf import settings
from django.core.mail import send_mail as django_send_mail
from .base import EmailProvider

logger = logging.getLogger(__name__)


class SMTPProvider(EmailProvider):
    """SMTP email provider using Django's built-in functionality."""
    
    def __init__(self):
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@localhost')
    
    def send(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        plain_text_content: str,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send email using Django's SMTP backend.
        """
        sender = from_email or self.from_email
        recipient_list = [to_email]
        
        # Add CC emails to recipient list (Django SMTP doesn't support separate CC)
        if cc_emails:
            recipient_list.extend(cc_emails)
        
        # Add BCC emails to recipient list
        if bcc_emails:
            recipient_list.extend(bcc_emails)
        
        try:
            # Note: Django's send_mail doesn't natively support:
            # - Separate CC/BCC handling (they all go in recipient_list)
            # - Attachments via simple send_mail
            # - Reply-to headers
            # For advanced features, we'd need to use EmailMessage class
            
            result = django_send_mail(
                subject=subject,
                message=plain_text_content,
                from_email=sender,
                recipient_list=recipient_list,
                html_message=html_content,
                fail_silently=False,
            )
            
            if result == 1:  # 1 means email was sent successfully
                logger.info(f"Email sent successfully to {to_email} via SMTP")
                return True
            else:
                logger.warning(f"SMTP send returned {result} for {to_email}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send email via SMTP: {e}")
            return False
    
    def get_provider_name(self) -> str:
        return "smtp"
    
    def is_configured(self) -> bool:
        """Check if SMTP is properly configured in Django settings."""
        # Check basic email settings
        email_backend = getattr(settings, 'EMAIL_BACKEND', '')
        email_host = getattr(settings, 'EMAIL_HOST', '')
        
        if not email_backend or 'smtp' not in email_backend.lower():
            logger.warning("SMTP email backend not configured")
            return False
        
        if not email_host:
            logger.warning("EMAIL_HOST not configured for SMTP")
            return False
            
        return True