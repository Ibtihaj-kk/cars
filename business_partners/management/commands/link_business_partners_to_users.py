from django.core.management.base import BaseCommand
from django.db import transaction
from business_partners.models import BusinessPartner, VendorApplication


class Command(BaseCommand):
    help = 'Link existing BusinessPartner records with their corresponding users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Find BusinessPartner records without a user
        business_partners_without_user = BusinessPartner.objects.filter(user__isnull=True)
        
        self.stdout.write(f'Found {business_partners_without_user.count()} BusinessPartner records without a user')
        
        updated_count = 0
        
        with transaction.atomic():
            for bp in business_partners_without_user:
                # Try to find the corresponding VendorApplication
                vendor_app = VendorApplication.objects.filter(
                    company_name=bp.name,
                    status='approved'
                ).first()
                
                if vendor_app and vendor_app.user:
                    if dry_run:
                        self.stdout.write(
                            f'Would link BusinessPartner "{bp.name}" (ID: {bp.id}) '
                            f'to User "{vendor_app.user.email}" (ID: {vendor_app.user.id})'
                        )
                    else:
                        bp.user = vendor_app.user
                        bp.save()
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Linked BusinessPartner "{bp.name}" (ID: {bp.id}) '
                                f'to User "{vendor_app.user.email}" (ID: {vendor_app.user.id})'
                            )
                        )
                    updated_count += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Could not find matching VendorApplication for BusinessPartner "{bp.name}" (ID: {bp.id})'
                        )
                    )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would update {updated_count} BusinessPartner records')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully updated {updated_count} BusinessPartner records')
            )