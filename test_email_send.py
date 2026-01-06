#!/usr/bin/env python
"""
Test script to send email using our robust email orchestrator system
"""

import os
import sys
import django

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yallamotor_project.settings')
django.setup()

from core.email_service.orchestrator import send_email, send_email_async
from django.conf import settings

def test_email_system():
    """Test the email system by sending a test email"""
    print("🧪 Testing Email System...")
    print(f"Email Provider: {getattr(settings, 'EMAIL_PROVIDER', 'Not set')}")
    print(f"EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'Not set')}")
    print(f"EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', 'Not set')}")
    print(f"EMAIL_HOST_USER: {getattr(settings, 'EMAIL_HOST_USER', 'Not set')}")
    
    # Test email details
    test_email = "ibtihaj@corporatedock.com"
    
    print(f"\n📧 Sending test email to: {test_email}")
    
    try:
        # Send test email using orchestrator
        email_id = send_email(
            email_type='test',
            to_email=test_email,
            subject='Test Email from CarSyncro Robust System',
            template_name='test_email',
            context={
                'message': 'This is a test email sent through our robust centralized email system!',
                'system_info': 'Dependency-free email system with queue management and retry logic'
            },
            priority='high'
        )
        
        print(f"✅ Email queued successfully!")
        print(f"📨 Email ID: {email_id}")
        print(f"📊 Email should be processed by the queue system shortly")
        
        return True
        
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        print(f"Error type: {type(e).__name__}")
        
        # Try fallback direct sending
        try:
            print("\n🔄 Attempting fallback direct email sending...")
            
            from django.core.mail import send_mail
            
            send_mail(
                'Test Email - Fallback Direct Send',
                'This is a fallback test email sent directly (not through queue).',
                settings.DEFAULT_FROM_EMAIL,
                [test_email],
                fail_silently=False,
            )
            
            print("✅ Fallback direct email sent successfully!")
            return True
            
        except Exception as fallback_error:
            print(f"❌ Fallback also failed: {fallback_error}")
            return False

if __name__ == "__main__":
    success = test_email_system()
    
    if success:
        print("\n🎉 Email system test completed successfully!")
        print("Check your email inbox and also check the email queue in admin panel.")
    else:
        print("\n💥 Email system test failed!")
        print("Please check your email configuration in .env file.")
        sys.exit(1)