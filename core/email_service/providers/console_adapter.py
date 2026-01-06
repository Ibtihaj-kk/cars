# """
# Console Email Provider

# Development provider that logs emails to console instead of sending them.
# Useful for testing and development environments.
# ""__

import logging
from typing import List, Optional, Dict, Any
from .base import EmailProvider

logger = logging.getLogger(__name__)


class ConsoleProvider(EmailProvider):
    """Email provider that logs to console for development."""
    
    def __init__(self):
        self.from_email = "noreply@localhost"
    
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
        Log email to console instead of sending.
        """
        sender = from_email or self.from_email
        
        logger.info(f"\n{'='*60}")
        logger.info(f"CONSOLE EMAIL (Not actually sent)")
        logger.info(f"{'='*60}")
        logger.info(f"From: {sender}")
        logger.info(f"To: {to_email}")
        if cc_emails:
            logger.info(f"CC: {', '.join(cc_emails)}")
        if bcc_emails:
            logger.info(f"BCC: {', '.join(bcc_emails)}")
        logger.info(f"Subject: {subject}")
        logger.info(f"\nPlain Text Content:")
        logger.info(f"{'-'*40}")
        logger.info(plain_text_content)
        logger.info(f"\nHTML Content:")
        logger.info(f"{'-'*40}")
        logger.info(html_content)
        
        if attachments:
            logger.info(f"\nAttachments: {len(attachments)}")
            for att in attachments:
                logger.info(f"  - {att.get('filename', 'unnamed')} ({att.get('content_type', 'unknown')})")
        
        if metadata:
            logger.info(f"\nMetadata: {metadata}")
        
        logger.info(f"{'='*60}\n")
        
        return True
    
    def get_provider_name(self) -> str:
        return "console"
    
    def is_configured(self) -> bool:
        return True