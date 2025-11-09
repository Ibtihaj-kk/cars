"""
Email service for sending dealer notifications when new inquiries are created.
"""
import logging
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from typing import Optional

logger = logging.getLogger(__name__)


class DealerNotificationEmailService:
    """Service for sending email notifications to dealers about new inquiries."""
    
    @staticmethod
    def send_new_inquiry_notification(inquiry) -> bool:
        """
        Send email notification to dealer when a new inquiry is created.
        
        Args:
            inquiry: ListingInquiry instance
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Get dealer information
            dealer = inquiry.listing.user
            listing = inquiry.listing
            inquirer = inquiry.user
            
            # Prepare email context
            context = {
                'dealer_name': dealer.get_full_name() or dealer.email,
                'listing_title': listing.title,
                'listing_url': f"{settings.FRONTEND_URL}/listings/{listing.slug}/",
                'user_name': inquirer.get_full_name() if inquirer else inquiry.name,
                'user_message': inquiry.message,
                'inquiry_type': inquiry.get_inquiry_type_display(),
                'inquiry_date': inquiry.created_at.strftime('%B %d, %Y at %I:%M %p'),
                'contact_email': inquirer.email if inquirer else inquiry.email,
                'contact_phone': inquiry.phone if inquiry.phone else 'Not provided',
                'frontend_url': settings.FRONTEND_URL,
            }
            
            # Render email templates
            subject = f"New Inquiry on Your Vehicle Listing - {listing.title}"
            html_message = render_to_string('emails/dealer_inquiry_notification.html', context)
            plain_message = render_to_string('emails/dealer_inquiry_notification.txt', context)
            
            # Send email
            success = send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[dealer.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            if success:
                logger.info(
                    f"Dealer notification email sent successfully to {dealer.email} "
                    f"for inquiry {inquiry.id} on listing {listing.id}"
                )
                return True
            else:
                logger.warning(
                    f"Failed to send dealer notification email to {dealer.email} "
                    f"for inquiry {inquiry.id} on listing {listing.id}"
                )
                return False
                
        except Exception as e:
            logger.error(
                f"Error sending dealer notification email for inquiry {inquiry.id}: {str(e)}",
                exc_info=True
            )
            return False
    
    @staticmethod
    def should_send_notification(inquiry) -> bool:
        """
        Check if notification should be sent for this inquiry.
        
        Args:
            inquiry: ListingInquiry instance
            
        Returns:
            bool: True if notification should be sent, False otherwise
        """
        try:
            # Check if email notifications are enabled globally
            if not getattr(settings, 'ENABLE_INQUIRY_EMAIL_NOTIFICATIONS', True):
                return False
            
            # Check if dealer has email notifications enabled
            dealer = inquiry.listing.user
            if hasattr(dealer, 'notification_preferences'):
                prefs = dealer.notification_preferences
                if not prefs.email_notifications or not prefs.inquiry_notifications:
                    return False
            
            # Check if dealer email is valid
            if not dealer.email:
                logger.warning(f"Dealer {dealer.id} has no email address for inquiry notification")
                return False
            
            # Check if listing is published
            if inquiry.listing.status != 'published':
                logger.info(f"Skipping notification for non-published listing {inquiry.listing.id} (status: {inquiry.listing.status})")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking notification eligibility for inquiry {inquiry.id}: {str(e)}")
            return False