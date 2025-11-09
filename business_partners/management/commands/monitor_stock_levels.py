from django.core.management.base import BaseCommand
from django.db.models import Q, F
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from business_partners.models import BusinessPartner, ReorderNotification
from parts.models import Part, Inventory
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Monitor stock levels and generate automated alerts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--vendor-id',
            type=int,
            help='Monitor stock for specific vendor only'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually creating notifications'
        )
        parser.add_argument(
            '--send-emails',
            action='store_true',
            help='Send email notifications for critical alerts'
        )
        parser.add_argument(
            '--critical-only',
            action='store_true',
            help='Only process critical priority notifications'
        )

    def handle(self, *args, **options):
        vendor_id = options.get('vendor_id')
        dry_run = options.get('dry_run', False)
        send_emails = options.get('send_emails', False)
        critical_only = options.get('critical_only', False)
        
        self.stdout.write(
            self.style.SUCCESS('Starting automated stock level monitoring...')
        )
        
        # Get active vendors
        vendors = BusinessPartner.objects.filter(
            roles__role_type='vendor',
            status='active'
        ).distinct()
        
        if vendor_id:
            vendors = vendors.filter(id=vendor_id)
            
        if not vendors.exists():
            self.stdout.write(
                self.style.WARNING('No active vendors found.')
            )
            return
            
        total_alerts_created = 0
        total_emails_sent = 0
        
        for vendor in vendors:
            self.stdout.write(f'\nProcessing vendor: {vendor.name}')
            
            # Monitor stock levels and create notifications
            alerts_created, emails_sent = self.monitor_vendor_stock(
                vendor, dry_run, send_emails, critical_only
            )
            
            total_alerts_created += alerts_created
            total_emails_sent += emails_sent
            
            self.stdout.write(
                f'  Created {alerts_created} alerts, sent {emails_sent} emails'
            )
        
        # Summary
        action = 'Would have' if dry_run else 'Successfully'
        self.stdout.write(
            self.style.SUCCESS(
                f'\n{action} completed stock monitoring:'
                f'\n- {total_alerts_created} alerts created'
                f'\n- {total_emails_sent} emails sent'
            )
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('This was a dry run. No actual changes were made.')
            )

    def monitor_vendor_stock(self, vendor, dry_run, send_emails, critical_only):
        """Monitor stock levels for a specific vendor"""
        alerts_created = 0
        emails_sent = 0
        
        # Get parts with stock issues
        stock_issues = self.identify_stock_issues(vendor)
        
        for part, issue_type, severity in stock_issues:
            # Skip if critical_only and not critical
            if critical_only and severity != 'critical':
                continue
                
            # Check if recent notification exists
            recent_exists = ReorderNotification.objects.filter(
                vendor=vendor,
                part=part,
                status__in=['pending', 'acknowledged'],
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).exists()
            
            if recent_exists:
                continue
                
            # Create notification
            if dry_run:
                self.stdout.write(
                    f'  Would create {severity} alert for: {part.name} '
                    f'(Issue: {issue_type})'
                )
            else:
                notification = self.create_stock_alert(vendor, part, issue_type, severity)
                if notification:
                    alerts_created += 1
                    self.stdout.write(
                        f'  Created {severity} alert for: {part.name}'
                    )
                    
                    # Send email for critical alerts
                    if send_emails and severity == 'critical':
                        if self.send_critical_stock_email(notification):
                            emails_sent += 1
        
        return alerts_created, emails_sent

    def identify_stock_issues(self, vendor):
        """Identify stock issues for vendor parts"""
        issues = []
        
        # Get all active parts for this vendor
        parts = Part.objects.filter(
            vendor=vendor,
            is_active=True
        ).select_related('inventory')
        
        for part in parts:
            inventory = getattr(part, 'inventory', None)
            if not inventory:
                continue
                
            current_stock = inventory.stock
            reorder_level = inventory.reorder_level or 10
            safety_stock = part.safety_stock or 0
            
            # Critical: Out of stock
            if current_stock == 0:
                issues.append((part, 'out_of_stock', 'critical'))
            # Critical: Below safety stock
            elif safety_stock > 0 and current_stock < safety_stock:
                issues.append((part, 'below_safety_stock', 'critical'))
            # High: At or below reorder level
            elif current_stock <= reorder_level:
                issues.append((part, 'at_reorder_level', 'high'))
            # Medium: Approaching reorder level (within 20%)
            elif current_stock <= reorder_level * 1.2:
                issues.append((part, 'approaching_reorder', 'medium'))
        
        return issues

    def create_stock_alert(self, vendor, part, issue_type, severity):
        """Create a stock alert notification"""
        try:
            inventory = getattr(part, 'inventory', None)
            if not inventory:
                return None
                
            # Map severity to priority
            priority_map = {
                'critical': 'critical',
                'high': 'high',
                'medium': 'medium',
                'low': 'low'
            }
            
            notification = ReorderNotification.objects.create(
                vendor=vendor,
                part=part,
                current_stock=inventory.stock,
                safety_stock=part.safety_stock,
                reorder_level=inventory.reorder_level or 10,
                priority=priority_map.get(severity, 'medium'),
                suggested_quantity=self.calculate_suggested_quantity(part, inventory)
            )
            
            # Add custom message based on issue type
            if issue_type == 'out_of_stock':
                notification.message = f"URGENT: {part.name} is completely out of stock. Immediate reorder required."
            elif issue_type == 'below_safety_stock':
                notification.message = f"{part.name} stock ({inventory.stock}) is below safety stock level ({part.safety_stock})."
            elif issue_type == 'at_reorder_level':
                notification.message = f"{part.name} has reached reorder level ({inventory.reorder_level or 10}). Time to reorder."
            elif issue_type == 'approaching_reorder':
                notification.message = f"{part.name} is approaching reorder level. Consider placing order soon."
            
            notification.save()
            return notification
            
        except Exception as e:
            logger.error(f"Error creating stock alert for {part.name}: {str(e)}")
            return None

    def calculate_suggested_quantity(self, part, inventory):
        """Calculate suggested reorder quantity"""
        reorder_level = inventory.reorder_level or 10
        safety_stock = part.safety_stock or 0
        
        # Suggest quantity to reach 3x reorder level or safety stock + 2x reorder level
        if safety_stock > 0:
            target_quantity = max(safety_stock * 2, reorder_level * 2)
        else:
            target_quantity = reorder_level * 3
            
        current_stock = inventory.stock
        suggested = max(target_quantity - current_stock, reorder_level)
        
        # Round up to nearest 10 for practical ordering
        return ((suggested + 9) // 10) * 10

    def send_critical_stock_email(self, notification):
        """Send email notification for critical stock alerts"""
        try:
            subject = f"CRITICAL: Stock Alert for {notification.part.name}"
            
            # Get vendor contacts
            contacts = notification.vendor.contacts.filter(
                is_primary=True,
                contact_type='email'
            ).first()
            
            if not contacts or not contacts.value:
                logger.warning(f"No email contact found for vendor {notification.vendor.name}")
                return False
            
            # Render email template
            html_message = render_to_string('business_partners/emails/critical_stock_alert.html', {
                'notification': notification,
                'vendor': notification.vendor,
                'part': notification.part,
            })
            
            plain_message = strip_tags(html_message)
            
            # Send email
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[contacts.value],
                html_message=html_message,
                fail_silently=False
            )
            
            logger.info(f"Critical stock email sent to {contacts.value} for {notification.part.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending critical stock email: {str(e)}")
            return False