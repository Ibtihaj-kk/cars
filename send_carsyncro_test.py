#!/usr/bin/env python
import os
import sys
import django

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yallamotor_project.settings')
django.setup()

from core.email_service.orchestrator import send_email

# Send test email with CarSyncro branding
email_id = send_email(
    email_type='test',
    to_email='ibtihaj555@outlook.com',
    subject='Test Email from CarSyncro Robust System',
    template_name='test_email',
    context={
        'message': 'This is a test email sent through our robust centralized email system!',
        'system_info': 'CarSyncro - Dependency-free email system with queue management and retry logic',
        'company_name': 'CarSyncro'
    },
    priority='high'
)

print(f'Email queued with ID: {email_id}')
print('Email should be processed shortly. Check the email queue for status.')