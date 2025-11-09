from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from business_partners.models import BusinessPartner, BusinessPartnerRole, VendorProfile
from parts.models import Part, Brand, Category, Inventory
from decimal import Decimal
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Create sample inventory data for testing reorder notifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--vendors',
            type=int,
            default=3,
            help='Number of vendors to create'
        )
        parser.add_argument(
            '--parts-per-vendor',
            type=int,
            default=5,
            help='Number of parts per vendor'
        )

    def handle(self, *args, **options):
        vendors_count = options['vendors']
        parts_per_vendor = options['parts_per_vendor']
        
        self.stdout.write(
            self.style.SUCCESS('Creating sample inventory data...')
        )
        
        # Create admin user if not exists
        admin_user, created = User.objects.get_or_create(
            email='admin@example.com',
            defaults={
                'first_name': 'Admin',
                'last_name': 'User',
                'is_staff': True,
                'is_superuser': True,
                'role': 'admin'
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write('Created admin user')
        
        # Create categories if not exist
        categories = []
        category_names = ['Engine Parts', 'Brake System', 'Suspension', 'Electrical', 'Body Parts']
        for name in category_names:
            category, created = Category.objects.get_or_create(
                name=name,
                defaults={'description': f'{name} category'}
            )
            categories.append(category)
            if created:
                self.stdout.write(f'Created category: {name}')
        
        # Create brands if not exist
        brands = []
        brand_names = ['Toyota', 'BMW', 'Mercedes', 'Audi', 'Honda']
        for name in brand_names:
            brand, created = Brand.objects.get_or_create(
                name=name,
                defaults={'description': f'{name} brand'}
            )
            brands.append(brand)
            if created:
                self.stdout.write(f'Created brand: {name}')
        
        # Create vendors
        vendors = []
        for i in range(vendors_count):
            vendor_name = f'Auto Parts Vendor {i+1}'
            
            # Create business partner
            business_partner = BusinessPartner.objects.create(
                name=vendor_name,
                type='company',
                status='active',
                legal_identifier=f'TAX{1000+i}',
                created_by=admin_user
            )
            
            # Add vendor role
            BusinessPartnerRole.objects.create(
                business_partner=business_partner,
                role_type='vendor'
            )
            
            # Create vendor profile
            VendorProfile.objects.create(
                business_partner=business_partner,
                payment_terms='net_30',
                vendor_rating=Decimal('4.5'),
                tax_id=f'TAX{1000+i}',
                preferred_currency='USD'
            )
            
            vendors.append(business_partner)
            self.stdout.write(f'Created vendor: {vendor_name}')
        
        # Create parts with inventory for each vendor
        total_parts = 0
        for vendor in vendors:
            for j in range(parts_per_vendor):
                part_number = f'P{vendor.id:03d}{j+1:03d}'
                part_name = f'Auto Part {part_number}'
                
                # Create part
                part = Part.objects.create(
                    parts_number=part_number,
                    name=part_name,
                    material_description=f'High quality {part_name.lower()}',
                    sku=f'SKU{part_number}',
                    category=random.choice(categories),
                    brand=random.choice(brands),
                    vendor=vendor,
                    price=Decimal(str(random.uniform(10, 500))),
                    quantity=random.randint(0, 100),
                    is_active=True,
                    base_unit_of_measure='EA',
                    dealer=admin_user
                )
                
                # Create inventory with different stock levels for testing
                stock_scenarios = [
                    {'stock': 0, 'reorder_level': 10, 'safety_stock': 5},  # Out of stock
                    {'stock': 3, 'reorder_level': 10, 'safety_stock': 5},  # Below safety stock
                    {'stock': 8, 'reorder_level': 10, 'safety_stock': 5},  # Below reorder level
                    {'stock': 25, 'reorder_level': 10, 'safety_stock': 5}, # Healthy stock
                ]
                
                scenario = random.choice(stock_scenarios)
                
                Inventory.objects.create(
                    part=part,
                    stock=scenario['stock'],
                    reorder_level=scenario['reorder_level'],
                    max_stock_level=50,
                    supplier_info=f'Supplied by {vendor.name}'
                )
                
                total_parts += 1
                
                # Show stock status
                if scenario['stock'] == 0:
                    status = "OUT OF STOCK"
                elif scenario['stock'] < scenario['safety_stock']:
                    status = "BELOW SAFETY STOCK"
                elif scenario['stock'] <= scenario['reorder_level']:
                    status = "NEEDS REORDER"
                else:
                    status = "HEALTHY"
                
                self.stdout.write(
                    f'  Created part: {part_name} (Stock: {scenario["stock"]}) - {status}'
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSample data created successfully!'
                f'\n- {len(vendors)} vendors'
                f'\n- {total_parts} parts with inventory'
                f'\n- {len(categories)} categories'
                f'\n- {len(brands)} brands'
            )
        )
        
        # Show summary of stock levels
        out_of_stock = Inventory.objects.filter(stock=0).count()
        below_safety = Inventory.objects.filter(stock__gt=0, stock__lt=5).count()
        needs_reorder = Inventory.objects.filter(stock__gt=0, stock__lte=10).count() - below_safety
        
        self.stdout.write(
            self.style.WARNING(
                f'\nInventory Summary:'
                f'\n- Out of stock: {out_of_stock} parts'
                f'\n- Below safety stock: {below_safety} parts'
                f'\n- Needs reorder: {needs_reorder} parts'
            )
        )