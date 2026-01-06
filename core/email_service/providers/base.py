# """
# Base Email Provider Interface

# Defines the contract that all email providers must implement.
# This allows for easy swapping of email providers without changing business logic.
# ""__

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class EmailProvider(ABC):
    # """Abstract base class for all email providers."""
    
    @abstractmethod
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
        Send an email through the provider.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            plain_text_content: Plain text content of the email
            from_email: Sender email address (uses default if None)
            reply_to: Reply-to email address
            cc_emails: List of CC email addresses
            bcc_emails: List of BCC email addresses
            attachments: List of attachment dictionaries
            metadata: Additional metadata for tracking
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the name of the email provider.
        
        Returns:
            str: Provider name (e.g., 'sendgrid', 'smtp', 'console')
        """
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """
        Check if the provider is properly configured.
        
        Returns:
            bool: True if provider is configured and ready to use
        """
        pass
    
    def validate_email(self, email: str) -> bool:
        """
        Validate an email address format.
        
        Args:
            email: Email address to validate
            
        Returns:
            bool: True if email format is valid
        """
        import re
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_regex, email))