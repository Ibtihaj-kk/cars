from django.core.management.base import BaseCommand
from django.db.models import Q, F
from django.utils import timezone
from datetime import timedelta
from business_partners.models import BusinessPartner, ReorderNotification
from parts.models import Part


class Command(BaseCommand):
    help = 'Generate reorder notifications for parts that need restocking'

    def add_arguments(self, parser):
        parser.add_argument(
            '--vendor-id',
            type=int,
            help='Generate notifications for specific vendor only'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating notifications'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force generation even if recent notifications exist'
        )

    def handle(self, *args, **options):
        vendor_id = options.get('vendor_id')
        dry_run = options.get('dry_run', False)
        force = options.get('force', False)
        
        self.stdout.write(
            self.style.SUCCESS('Starting reorder notification generation...')
        )
        
        # Get vendors to process
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
            
        total_notifications = 0
        
        for vendor in vendors:
            self.stdout.write(f'\nProcessing vendor: {vendor.name}')
            
            # Get parts that need reordering
            parts_needing_reorder = self.get_parts_needing_reorder(vendor)
            
            if not parts_needing_reorder:
                self.stdout.write('  No parts need reordering.')
                continue
                
            vendor_notifications = 0
            
            for part in parts_needing_reorder:
                # Check if recent notification already exists (unless forced)
                if not force:
                    recent_notification = ReorderNotification.objects.filter(
                        vendor=vendor,
                        part=part,
                        status__in=['pending', 'acknowledged'],
                        created_at__gte=timezone.now() - timedelta(days=7)
                    ).exists()
                    
                    if recent_notification:
                        self.stdout.write(
                            f'  Skipping {part.name} - recent notification exists'
                        )
                        continue
                
                # Get inventory info
                inventory = getattr(part, 'inventory', None)
                current_stock = inventory.stock if inventory else 0
                safety_stock = part.safety_stock if part.safety_stock else None
                reorder_level = inventory.reorder_level if inventory else 10
                
                if dry_run:
                    self.stdout.write(
                        f'  Would create notification for: {part.name} '
                        f'(Stock: {current_stock}, Reorder Level: {reorder_level})'
                    )
                else:
                    # Create notification
                    notification = ReorderNotification.objects.create(
                        vendor=vendor,
                        part=part,
                        current_stock=current_stock,
                        safety_stock=safety_stock,
                        reorder_level=reorder_level,
                        suggested_quantity=0  # Will be auto-calculated in save()
                    )
                    
                    self.stdout.write(
                        f'  Created {notification.get_priority_display().lower()} '
                        f'priority notification for: {part.name}'
                    )
                
                vendor_notifications += 1
                total_notifications += 1
            
            if vendor_notifications > 0:
                self.stdout.write(
                    f'  Generated {vendor_notifications} notifications for {vendor.name}'
                )
        
        action = 'Would generate' if dry_run else 'Generated'
        self.stdout.write(
            self.style.SUCCESS(
                f'\n{action} {total_notifications} reorder notifications total.'
            )
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('This was a dry run. Use --force to actually create notifications.')
            )

    def get_parts_needing_reorder(self, vendor):
        """Get parts that need reordering for a specific vendor"""
        
        # Get parts associated with this vendor that are active
        vendor_parts = Part.objects.filter(
            vendor=vendor,
            is_active=True
        ).select_related('inventory')
        
        parts_needing_reorder = []
        
        for part in vendor_parts:
            inventory = getattr(part, 'inventory', None)
            
            if not inventory:
                continue
                
            current_stock = inventory.stock
            reorder_level = inventory.reorder_level or 10
            safety_stock = part.safety_stock  # Use Part's safety_stock field
            
            # Check if reorder is needed
            needs_reorder = False
            
            # Critical: Out of stock
            if current_stock == 0:
                needs_reorder = True
            # High priority: Below safety stock
            elif safety_stock and current_stock < safety_stock:
                needs_reorder = True
            # Medium priority: At or below reorder level
            elif current_stock <= reorder_level:
                needs_reorder = True
            
            if needs_reorder:
                parts_needing_reorder.append(part)
        
        return parts_needing_reorder