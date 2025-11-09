"""
Email service for vendor application notifications.
Handles all email communications related to vendor registration and approval workflow.
"""

import logging
from datetime import datetime
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from django.contrib.sites.models import Site
from django.utils.html import strip_tags

logger = logging.getLogger('email_notifications')


class VendorApplicationEmailService:
    """
    Service class for handling vendor application email notifications.
    Provides methods for sending various types of emails throughout the vendor approval workflow.
    """
    
    def __init__(self):
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@carsportal.com')
        self.site_domain = self._get_site_domain()
    
    def _get_site_domain(self):
        """Get the current site domain for URL generation."""
        try:
            site = Site.objects.get_current()
            return f"https://{site.domain}"
        except:
            return getattr(settings, 'FRONTEND_URL', 'https://carsportal.com')
    
    def _get_base_context(self, application):
        """Get base context variables used in all email templates."""
        return {
            'application': application,
            'current_year': datetime.now().year,
            'site_domain': self.site_domain,
            'status_url': f"{self.site_domain}/business-partners/registration/status/",
            'dashboard_url': f"{self.site_domain}/vendor/dashboard/",
            'parts_url': f"{self.site_domain}/vendor/parts/",
            'support_url': f"{self.site_domain}/support/",
            'vendor_guide_url': f"{self.site_domain}/resources/vendor-guide/",
            'api_docs_url': f"{self.site_domain}/api/docs/",
            'reapply_url': f"{self.site_domain}/business-partners/registration/reapply/",
            'edit_application_url': f"{self.site_domain}/business-partners/registration/step1/",
        }
    
    def _send_email(self, subject, html_template, text_template, recipient_email, context):
        """
        Send email with both HTML and text versions.
        
        Args:
            subject (str): Email subject
            html_template (str): Path to HTML template
            text_template (str): Path to text template
            recipient_email (str): Recipient email address
            context (dict): Template context variables
        """
        # Check if vendor email notifications are enabled
        if not getattr(settings, 'ENABLE_VENDOR_EMAIL_NOTIFICATIONS', True):
            logger.info(f"Vendor email notifications disabled, skipping email to {recipient_email}")
            return True
        
        try:
            # Render HTML content
            html_content = render_to_string(html_template, context)
            
            # Render text content
            text_content = render_to_string(text_template, context)
            
            # Send email
            send_mail(
                subject=subject,
                message=text_content,
                from_email=self.from_email,
                recipient_list=[recipient_email],
                html_message=html_content,
                fail_silently=False,
            )
            
            logger.info(f"Vendor application email sent successfully to {recipient_email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send vendor application email to {recipient_email}: {e}")
            return False
    
    def send_application_submitted_notification(self, application):
        """
        Send notification when vendor application is submitted for review.
        
        Args:
            application: VendorApplication instance
        """
        if not application.business_email:
            logger.warning(f"No email address for application {application.application_id}")
            return False
        
        subject = f"Cars Portal - Vendor Application Submitted (ID: {application.application_id})"
        context = self._get_base_context(application)
        
        return self._send_email(
            subject=subject,
            html_template='emails/vendor_application_submitted.html',
            text_template='emails/vendor_application_submitted.txt',
            recipient_email=application.business_email,
            context=context
        )
    
    def send_application_approved_notification(self, application, vendor_profile=None):
        """
        Send notification when vendor application is approved.
        
        Args:
            application: VendorApplication instance
            vendor_profile: VendorProfile instance (optional)
        """
        if not application.business_email:
            logger.warning(f"No email address for application {application.application_id}")
            return False
        
        subject = f"🎉 Congratulations! Your Cars Portal Vendor Application is Approved"
        context = self._get_base_context(application)
        
        # Add vendor profile to context if available
        if vendor_profile:
            context['vendor_profile'] = vendor_profile
        
        return self._send_email(
            subject=subject,
            html_template='emails/vendor_application_approved.html',
            text_template='emails/vendor_application_approved.txt',
            recipient_email=application.business_email,
            context=context
        )
    
    def send_application_rejected_notification(self, application):
        """
        Send notification when vendor application is rejected.
        
        Args:
            application: VendorApplication instance
        """
        if not application.business_email:
            logger.warning(f"No email address for application {application.application_id}")
            return False
        
        subject = f"Cars Portal - Vendor Application Status Update (ID: {application.application_id})"
        context = self._get_base_context(application)
        
        return self._send_email(
            subject=subject,
            html_template='emails/vendor_application_rejected.html',
            text_template='emails/vendor_application_rejected.txt',
            recipient_email=application.business_email,
            context=context
        )
    
    def send_changes_requested_notification(self, application):
        """
        Send notification when changes are requested for vendor application.
        
        Args:
            application: VendorApplication instance
        """
        if not application.business_email:
            logger.warning(f"No email address for application {application.application_id}")
            return False
        
        subject = f"⚠️ Action Required - Cars Portal Vendor Application (ID: {application.application_id})"
        context = self._get_base_context(application)
        
        return self._send_email(
            subject=subject,
            html_template='emails/vendor_application_changes_requested.html',
            text_template='emails/vendor_application_changes_requested.txt',
            recipient_email=application.business_email,
            context=context
        )
    
    def send_admin_new_application_notification(self, application):
        """
        Send notification to admin users about new vendor application.
        
        Args:
            application (VendorApplication): The vendor application instance
        """
        # Get admin emails from settings
        admin_emails = getattr(settings, 'VENDOR_ADMIN_EMAILS', [])
        
        # If no admin emails configured, get staff users
        if not admin_emails:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admin_emails = list(User.objects.filter(is_staff=True).values_list('email', flat=True))
        
        if not admin_emails:
            logger.warning("No admin emails configured for vendor application notifications")
            return False
        
        context = {
            'application': application,
            'company_name': application.company_name,
            'business_type': application.get_business_type_display(),
            'application_id': application.application_id,
            'submission_date': application.created_at,
            'applicant_email': application.user.email,
            'review_url': f"{settings.SITE_URL}/admin/business-partners/review/{application.application_id}/",
        }
        
        subject = f"New Vendor Application: {application.company_name}"
        
        # Send to all admin emails
        success_count = 0
        for admin_email in admin_emails:
            if self._send_email(
                subject=subject,
                html_template='emails/admin_new_vendor_application.html',
                text_template='emails/admin_new_vendor_application.txt',
                recipient_email=admin_email,
                context=context
            ):
                success_count += 1
        
        logger.info(f"Admin notification sent to {success_count}/{len(admin_emails)} recipients")
        return success_count > 0
    
    def _get_admin_notification_emails(self):
        """Get list of admin emails for notifications."""
        # You can customize this to get admin emails from settings or database
        admin_emails = getattr(settings, 'VENDOR_ADMIN_EMAILS', [])
        
        if not admin_emails:
            # Fallback to superuser emails
            from users.models import User
            admin_emails = list(
                User.objects.filter(is_superuser=True, is_active=True)
                .values_list('email', flat=True)
            )
        
        return admin_emails
    
    def _send_admin_notification_email(self, subject, admin_email, context):
        """Send notification email to admin."""
        try:
            # Simple admin notification template
            message = f"""
New Vendor Application Submitted

Application Details:
- Application ID: {context['application'].application_id}
- Company Name: {context['application'].company_name}
- Business Type: {context['application'].get_business_type_display()}
- Contact Person: {context['application'].contact_person_name}
- Email: {context['application'].business_email}
- Phone: {context['application'].business_phone}
- Submitted: {context['application'].updated_at}

Review Application: {context['admin_review_url']}
Admin Dashboard: {context['admin_dashboard_url']}

This is an automated notification from Cars Portal Vendor Management System.
            """
            
            send_mail(
                subject=subject,
                message=message.strip(),
                from_email=self.from_email,
                recipient_list=[admin_email],
                fail_silently=False,
            )
            
            logger.info(f"Admin notification sent successfully to {admin_email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send admin notification to {admin_email}: {e}")
            return False
    
    def send_status_change_notification(self, application, old_status, new_status):
        """
        Send appropriate notification based on status change.
        
        Args:
            application: VendorApplication instance
            old_status: Previous status
            new_status: New status
        """
        if new_status == 'submitted' and old_status != 'submitted':
            # Application submitted for review
            self.send_application_submitted_notification(application)
            self.send_admin_new_application_notification(application)
        
        elif new_status == 'approved':
            # Application approved
            self.send_application_approved_notification(application)
        
        elif new_status == 'rejected':
            # Application rejected
            self.send_application_rejected_notification(application)
        
        elif new_status == 'requires_changes':
            # Changes requested
            self.send_changes_requested_notification(application)


# Convenience function for easy import
def get_vendor_email_service():
    """Get instance of VendorApplicationEmailService."""
    return VendorApplicationEmailService()