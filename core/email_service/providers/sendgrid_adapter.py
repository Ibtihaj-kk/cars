# """
# SendGrid Email Provider Adapter

# SendGrid integration for professional email delivery with high deliverability.
# ""__

import logging
from typing import List, Optional, Dict, Any
from django.conf import settings
from .base import EmailProvider

logger = logging.getLogger(__name__)


class SendGridProvider(EmailProvider):
    """SendGrid email provider implementation."""
    
    def __init__(self):
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@carsyncro.com')
        self.api_key = getattr(settings, 'SENDGRID_API_KEY', None)
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of SendGrid client."""
        if self._client is None and self.api_key:
            try:
                from sendgrid import SendGridAPIClient
                self._client = SendGridAPIClient(api_key=self.api_key)
            except ImportError:
                logger.error("SendGrid package not installed. Run: pip install sendgrid")
                self._client = None
        return self._client
    
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
        Send email using SendGrid API.
        """
        if not self.is_configured():
            logger.error("SendGrid not configured properly")
            return False
        
        try:
            from sendgrid.helpers.mail import Mail, Email, To, Content, Cc, Bcc, Attachment
            
            # Create email message
            from_addr = Email(from_email or self.from_email)
            to_addr = To(to_email)
            
            # Create content
            html_content_obj = Content("text/html", html_content)
            plain_content_obj = Content("text/plain", plain_text_content)
            
            # Build mail object
            mail = Mail(from_addr, to_addr, subject, plain_content_obj)
            mail.add_content(html_content_obj)
            
            # Add CC emails
            if cc_emails:
                for cc_email in cc_emails:
                    mail.add_cc(Cc(cc_email))
            
            # Add BCC emails
            if bcc_emails:
                for bcc_email in bcc_emails:
                    mail.add_bcc(Bcc(bcc_email))
            
            # Add reply-to
            if reply_to:
                mail.reply_to = Email(reply_to)
            
            # Add attachments
            if attachments:
                for attachment in attachments:
                    file_attachment = Attachment()
                    file_attachment.file_content = attachment.get('content', '')
                    file_attachment.file_type = attachment.get('content_type', 'application/octet-stream')
                    file_attachment.file_name = attachment.get('filename', 'attachment')
                    file_attachment.disposition = 'attachment'
                    mail.add_attachment(file_attachment)
            
            # Add metadata for tracking
            if metadata:
                mail.custom_args = metadata
            
            # Send email
            client = self._get_client()
            response = client.send(mail)
            
            if response.status_code in [200, 202]:
                logger.info(f"Email sent successfully to {to_email} via SendGrid")
                return True
            else:
                logger.error(f"SendGrid API error: {response.status_code} - {response.body}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send email via SendGrid: {e}")
            return False
    
    def get_provider_name(self) -> str:
        return "sendgrid"
    
    def is_configured(self) -> bool:
        """Check if SendGrid is properly configured."""
        if not self.api_key:
            logger.warning("SendGrid API key not configured")
            return False
        
        # Check if sendgrid package is available
        try:
            import sendgrid
            return True
        except ImportError:
            logger.warning("SendGrid package not installed")
            return False