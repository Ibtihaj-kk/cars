from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import random
from datetime import datetime, timedelta

from business_partners.models import BusinessPartner, VendorApplication, VendorProfile
from parts.models import Part, Category, Brand
from orders.models import Order, OrderItem, OrderStatus
from inventory.models import InventoryTransaction, TransactionType

User = get_user_model()


class Command(BaseCommand):
    help = 'Create comprehensive test data for vendor dashboard testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--vendor-email',
            type=str,
            default='testvendor@example.com',
            help='Email for the test vendor account'
        )
        parser.add_argument(
            '--parts-count',
            type=int,
            default=15,
            help='Number of parts to create for the vendor'
        )
        parser.add_argument(
            '--orders-count',
            type=int,
            default=8,
            help='Number of orders to create'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting vendor test data creation...'))
        
        vendor_email = options['vendor_email']
        parts_count = options['parts_count']
        orders_count = options['orders_count']
        
        # Create or get vendor user
        vendor_user = self.create_vendor_user(vendor_email)
        
        # Create vendor business partner and profile
        vendor_partner, vendor_profile = self.create_vendor_profile(vendor_user)
        
        # Create part categories and brands
        categories, brands = self.create_part_master_data()
        
        # Create parts for vendor
        parts = self.create_vendor_parts(vendor_partner, categories, brands, parts_count)
        
        # Create inventory transactions
        self.create_inventory_transactions(parts)
        
        # Create orders
        orders = self.create_orders(vendor_partner, parts, orders_count)
        
        # Create sales data
        self.create_sales_data(orders)
        
        # Create low stock alerts
        self.create_low_stock_alerts(vendor_partner)
        
        self.stdout.write(self.style.SUCCESS(f"""
Vendor Test Data Creation Completed!

📊 Summary:
✅ Vendor User: {vendor_email}
✅ Business Partner: {vendor_partner.bp_number} - {vendor_partner.name}
✅ Parts Created: {len(parts)}
✅ Orders Created: {len(orders)}
✅ Inventory Transactions: Created for all parts
✅ Sales Data: Generated for all orders

🎯 Test Scenarios Created:
- High-value parts with low stock
- Popular parts with multiple orders
- Parts with recent sales activity
- Low stock alerts for critical items
- Orders in various statuses (pending, processing, completed)

🔑 Login Details:
Email: {vendor_email}
Password: vendor123

📱 Dashboard URLs to Test:
- Vendor Dashboard: /vendor/dashboard/
- Parts List: /vendor/parts/
- Orders List: /vendor/orders/
- Inventory: /vendor/inventory/
        """))

    def create_vendor_user(self, email):
        """Create or get vendor user."""
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': 'Test',
                'last_name': 'Vendor',
                'phone_number': '+971501234567',
                'is_active': True,
                'is_verified': True
            }
        )
        
        if created:
            user.set_password('vendor123')
            user.save()
            self.stdout.write(f'✅ Created vendor user: {email}')
        else:
            self.stdout.write(f'✅ Found existing vendor user: {email}')
        
        return user

    def create_vendor_profile(self, user):
        """Create vendor business partner and profile."""
        # Create Business Partner
        partner, created = BusinessPartner.objects.get_or_create(
            bp_number='BP999999',
            defaults={
                'name': 'Test Vendor Company',
                'type': 'company',
                'legal_identifier': 'TEST123456',
                'status': 'active',
                'user': user
            }
        )
        
        if created:
            self.stdout.write(f'✅ Created business partner: {partner.bp_number}')
        
        # Create Vendor Profile
        profile, created = VendorProfile.objects.get_or_create(
            user=user,
            defaults={
                'business_partner': partner,
                'company_name': 'Test Vendor Company',
                'business_type': 'trading',
                'commercial_registration_number': 'CR123456',
                'status': 'approved'
            }
        )
        
        if created:
            self.stdout.write(f'✅ Created vendor profile for {user.email}')
        
        return partner, profile

    def create_part_master_data(self):
        """Create part categories and brands."""
        # Categories
        categories_data = [
            {'name': 'Engine Parts', 'description': 'Engine components and accessories'},
            {'name': 'Brake System', 'description': 'Brake pads, rotors, and related components'},
            {'name': 'Suspension', 'description': 'Shocks, struts, and suspension parts'},
            {'name': 'Electrical', 'description': 'Batteries, alternators, and electrical components'},
            {'name': 'Filters', 'description': 'Oil, air, and fuel filters'},
            {'name': 'Body Parts', 'description': 'Exterior body components'},
            {'name': 'Interior Parts', 'description': 'Interior accessories and components'}
        ]
        
        categories = []
        for data in categories_data:
            category, created = Category.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            categories.append(category)
        
        # Brands
        brands_data = [
            {'name': 'Toyota Genuine', 'description': 'Original Toyota parts'},
            {'name': 'Bosch', 'description': 'German automotive parts'},
            {'name': 'Denso', 'description': 'Japanese automotive components'},
            {'name': 'Mahle', 'description': 'Engine components and filters'},
            {'name': 'Sachs', 'description': 'Suspension and clutch components'},
            {'name': 'ATE', 'description': 'Brake system components'},
            {'name': 'Hella', 'description': 'Lighting and electrical components'}
        ]
        
        brands = []
        for data in brands_data:
            brand, created = Brand.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            brands.append(brand)
        
        self.stdout.write(f'✅ Created {len(categories)} categories and {len(brands)} brands')
        return categories, brands

    def create_vendor_parts(self, vendor_partner, categories, brands, count):
        """Create test parts for vendor."""
        parts_data = [
            # Engine Parts
            {'parts_number': 'ENG-001', 'material_description': 'Toyota Camry 2.5L Engine Oil Filter', 'category': 'Filters', 'brand': 'Toyota Genuine', 'price': 45, 'quantity': 25},
            {'parts_number': 'ENG-002', 'material_description': 'Bosch Spark Plug Set - 4 Pieces', 'category': 'Engine Parts', 'brand': 'Bosch', 'price': 120, 'quantity': 15},
            {'parts_number': 'ENG-003', 'material_description': 'Mahle Air Filter Element', 'category': 'Filters', 'brand': 'Mahle', 'price': 35, 'quantity': 30},
            
            # Brake System
            {'parts_number': 'BRK-001', 'material_description': 'Front Brake Pads - Toyota RAV4', 'category': 'Brake System', 'brand': 'Toyota Genuine', 'price': 180, 'quantity': 12},
            {'parts_number': 'BRK-002', 'material_description': 'ATE Rear Brake Disc Rotors - Pair', 'category': 'Brake System', 'brand': 'ATE', 'price': 280, 'quantity': 8},
            {'parts_number': 'BRK-003', 'material_description': 'Bosch Brake Fluid - 1 Liter', 'category': 'Brake System', 'brand': 'Bosch', 'price': 25, 'quantity': 50},
            
            # Suspension
            {'parts_number': 'SUS-001', 'material_description': 'Front Shock Absorbers - Toyota Land Cruiser', 'category': 'Suspension', 'brand': 'Sachs', 'price': 450, 'quantity': 6},
            {'parts_number': 'SUS-002', 'material_description': 'Rear Coil Springs - BMW X5', 'category': 'Suspension', 'brand': 'Bosch', 'price': 320, 'quantity': 4},
            
            # Electrical
            {'parts_number': 'ELE-001', 'material_description': '12V Car Battery - 70Ah', 'category': 'Electrical', 'brand': 'Bosch', 'price': 350, 'quantity': 10},
            {'parts_number': 'ELE-002', 'material_description': 'Headlight Bulb - H7 Halogen', 'category': 'Electrical', 'brand': 'Hella', 'price': 45, 'quantity': 20},
            
            # Body Parts
            {'parts_number': 'BOD-001', 'material_description': 'Front Bumper Grille - Toyota Corolla', 'category': 'Body Parts', 'brand': 'Toyota Genuine', 'price': 220, 'quantity': 3},
            {'parts_number': 'BOD-002', 'material_description': 'Side Mirror - Power Adjustable', 'category': 'Body Parts', 'brand': 'Denso', 'price': 180, 'quantity': 7},
            
            # Interior
            {'parts_number': 'INT-001', 'material_description': 'Floor Mats Set - 4 Pieces', 'category': 'Interior Parts', 'brand': 'Toyota Genuine', 'price': 120, 'quantity': 12},
            {'parts_number': 'INT-002', 'material_description': 'Car Seat Covers - Leather', 'category': 'Interior Parts', 'brand': 'Bosch', 'price': 280, 'quantity': 5}
        ]
        
        parts = []
        for i, data in enumerate(parts_data[:count]):
            category_obj = next(c for c in categories if c.name == data['category'])
            brand_obj = next(b for b in brands if b.name == data['brand'])
            
            part, created = Part.objects.get_or_create(
                parts_number=data['parts_number'],
                vendor=vendor_partner,
                defaults={
                    'material_description': data['material_description'],
                    'category': category_obj,
                    'brand': brand_obj,
                    'price': Decimal(str(data['price'])),
                    'quantity': data['quantity'],
                    'safety_stock': random.randint(2, 8),
                    'reorder_point': random.randint(5, 15),
                    'material_group': f"GRP-{i+1:03d}",
                    'abc_indicator': random.choice(['A', 'B', 'C']),
                    'base_unit_of_measure': 'EA',
                    'is_active': True,
                    'manufacturer_part_number': f"MFG-{data['parts_number']}",
                    'manufacturer_oem_number': f"OEM-{data['parts_number']}",
                    'gross_weight': Decimal(str(random.uniform(0.5, 5.0))),
                    'net_weight': Decimal(str(random.uniform(0.3, 4.5))),
                    'size_dimensions': f"{random.randint(10, 50)}x{random.randint(10, 50)}x{random.randint(5, 20)} cm"
                }
            )
            
            if created:
                self.stdout.write(f'✅ Created part: {part.parts_number} - {part.material_description}')
            parts.append(part)
        
        return parts

    def create_inventory_transactions(self, parts):
        """Create inventory transactions for parts."""
        transaction_types = [TransactionType.IN, TransactionType.OUT, TransactionType.ADJUSTMENT]
        
        for part in parts:
            # Create 3-5 transactions per part
            for i in range(random.randint(3, 5)):
                transaction_type = random.choice(transaction_types)
                quantity = random.randint(1, 10)
                
                if transaction_type == TransactionType.OUT:
                    quantity = -quantity
                elif transaction_type == TransactionType.ADJUSTMENT:
                    quantity = random.randint(-5, 5)
                
                InventoryTransaction.objects.create(
                    part=part,
                    transaction_type=transaction_type,
                    quantity=quantity,
                    reference_number=f"TXN-{part.parts_number}-{i+1}",
                    notes=f"Test transaction {i+1} for {part.material_description}",
                    created_at=timezone.now() - timedelta(days=random.randint(1, 30))
                )
        
        self.stdout.write(f'✅ Created inventory transactions for {len(parts)} parts')

    def create_orders(self, vendor_partner, parts, count):
        """Create orders for vendor parts."""
        customers = self.create_test_customers()
        orders = []
        
        order_statuses = [
            OrderStatus.PENDING,
            OrderStatus.PROCESSING,
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
            OrderStatus.COMPLETED
        ]
        
        for i in range(count):
            customer = random.choice(customers)
            status = random.choice(order_statuses)
            
            # Create order
            order = Order.objects.create(
                order_number=f"ORD-VEN-{i+1:04d}",
                customer=customer,
                vendor=vendor_partner,
                status=status,
                total_amount=Decimal('0'),
                shipping_address=f"Test Address {i+1}, Dubai, UAE",
                notes=f"Test order {i+1} for vendor dashboard testing"
            )
            
            # Add order items
            total_amount = Decimal('0')
            num_items = random.randint(1, 4)
            selected_parts = random.sample(parts, min(num_items, len(parts)))
            
            for part in selected_parts:
                quantity = random.randint(1, 5)
                unit_price = part.price
                subtotal = unit_price * quantity
                
                OrderItem.objects.create(
                    order=order,
                    part=part,
                    quantity=quantity,
                    unit_price=unit_price,
                    subtotal=subtotal
                )
                
                total_amount += subtotal
            
            # Update order total
            order.total_amount = total_amount
            order.save()
            
            orders.append(order)
            self.stdout.write(f'✅ Created order: {order.order_number} - {customer.first_name} {customer.last_name} - {status}')
        
        return orders

    def create_test_customers(self):
        """Create test customers."""
        customers_data = [
            {'email': 'customer1@example.com', 'first_name': 'Ahmed', 'last_name': 'Mohammed'},
            {'email': 'customer2@example.com', 'first_name': 'Fatima', 'last_name': 'Al-Rashid'},
            {'email': 'customer3@example.com', 'first_name': 'Khalid', 'last_name': 'Al-Mansouri'},
            {'email': 'customer4@example.com', 'first_name': 'Sarah', 'last_name': 'Johnson'},
            {'email': 'customer5@example.com', 'first_name': 'Mohammed', 'last_name': 'Al-Hajri'}
        ]
        
        customers = []
        for data in customers_data:
            customer, created = User.objects.get_or_create(
                email=data['email'],
                defaults={
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'is_active': True,
                    'is_verified': True
                }
            )
            customers.append(customer)
        
        return customers

    def create_sales_data(self, orders):
        """Create sales analytics data."""
        # Group orders by month for sales trends
        monthly_sales = {}
        
        for order in orders:
            month_key = order.created_at.strftime('%Y-%m')
            if month_key not in monthly_sales:
                monthly_sales[month_key] = {
                    'total_sales': Decimal('0'),
                    'order_count': 0
                }
            
            monthly_sales[month_key]['total_sales'] += order.total_amount
            monthly_sales[month_key]['order_count'] += 1
        
        self.stdout.write(f'✅ Created sales data for {len(monthly_sales)} months')
        
        # Create some recent high-value sales
        recent_orders = random.sample(orders, min(3, len(orders)))
        for order in recent_orders:
            order.created_at = timezone.now() - timedelta(days=random.randint(1, 7))
            order.save()
        
        return monthly_sales

    def create_low_stock_alerts(self, vendor_partner):
        """Create low stock alerts for testing."""
        low_stock_parts = Part.objects.filter(
            vendor=vendor_partner,
            quantity__lte=10
        ).order_by('quantity')[:5]
        
        # Simulate low stock alerts by creating inventory transactions that bring stock low
        for part in low_stock_parts:
            if part.quantity > 2:
                # Create a large outgoing transaction
                InventoryTransaction.objects.create(
                    part=part,
                    transaction_type='OUT',
                    quantity=-(part.quantity - 1),  # Reduce to 1 unit
                    reference_number=f"ALERT-{part.parts_number}",
                    notes=f"Low stock alert simulation for {part.material_description}",
                    created_at=timezone.now() - timedelta(hours=random.randint(1, 24))
                )
                
                # Update part quantity
                part.quantity = 1
                part.save()
        
        self.stdout.write(f'✅ Created low stock alerts for {len(low_stock_parts)} parts')