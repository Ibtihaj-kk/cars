"""
Management command to automatically expire listings that have passed their expiry date.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from listings.status_manager import ListingStatusManager


class Command(BaseCommand):
    help = 'Automatically expire listings that have passed their expiry date'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be expired without actually expiring',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Starting listing expiry process at {timezone.now()}"
            )
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )
        
        try:
            if dry_run:
                # Show what would be expired
                from listings.models import VehicleListing, ListingStatus
                
                now = timezone.now()
                expired_listings = VehicleListing.objects.filter(
                    status=ListingStatus.PUBLISHED,
                    expires_at__lt=now
                )
                
                count = expired_listings.count()
                
                if verbose and count > 0:
                    self.stdout.write("Listings that would be expired:")
                    for listing in expired_listings:
                        self.stdout.write(
                            f"  - {listing.title} (ID: {listing.id}, "
                            f"Expires: {listing.expires_at})"
                        )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Would expire {count} listing(s)"
                    )
                )
            else:
                # Actually expire listings
                expired_count = ListingStatusManager.auto_expire_listings()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully expired {expired_count} listing(s)"
                    )
                )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error during expiry process: {e}")
            )
            raise
        
        self.stdout.write(
            self.style.SUCCESS("Listing expiry process completed")
        )