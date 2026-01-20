# """
# Email Provider Abstraction Layer
# """
# Provides unified interface for different email service providers.
# Allows easy switching between providers without changing business logic.
# ""__

from .base import EmailProvider
from .sendgrid_adapter import SendGridProvider
from .console_adapter import ConsoleProvider
from .smtp_adapter import SMTPProvider

def get_email_provider():
    """
    Get the configured email provider based on settings.
    
    Returns:
        EmailProvider: Configured email provider instance
    """
    from django.conf import settings
    
    # Try to get from EMAIL_SERVICE_CONFIG first
    config = getattr(settings, 'EMAIL_SERVICE_CONFIG', {})
    provider_name = config.get('PROVIDER')
    
    # Fallback to top-level setting
    if not provider_name:
        provider_name = getattr(settings, 'EMAIL_PROVIDER', 'console')
    
    provider_name = provider_name.lower()
    
    if provider_name == 'sendgrid':
        return SendGridProvider()
    elif provider_name == 'smtp':
        return SMTPProvider()
    else:
        # Default to console for development
        return ConsoleProvider()

__all__ = [
    'EmailProvider',
    'SendGridProvider', 
    'ConsoleProvider',
    'SMTPProvider',
    'get_email_provider'
]