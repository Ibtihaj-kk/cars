# """
# Centralized Email Service for CarSyncro

# Provides unified email sending capabilities across the entire application
# with support for multiple providers, queuing, and advanced features.
# ""__

from .orchestrator import send_email, send_email_async, schedule_email
from .providers import get_email_provider
from .models import EmailQueue, EmailTemplate

__all__ = [
    'send_email',
    'send_email_async', 
    'schedule_email',
    'get_email_provider',
    'EmailQueue',
    'EmailTemplate'
]