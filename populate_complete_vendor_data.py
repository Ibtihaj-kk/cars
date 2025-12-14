#!/usr/bin/env python
"""
Comprehensive database population script for YallaMotor
Creates a complete vendor setup with:
- Vendor account (approved, verified, active)
- Car brands and models
- Parts with categories
- Orders against vendor
- Inventory for parts
"""

import os
import django
import random
from decimal import Decimal
from datetime import datetime, timedelta

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yallamotor_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from business_partners.models import BusinessPartner, BusinessPartnerRole, VendorProfile
from vehicles.models import Brand, VehicleModel, FuelType, TransmissionType, VehicleMake, VehicleModelTaxonomy, VehicleVariant
from parts.models import Category, Brand as PartBrand, Part, Inventory, Order, OrderItem
from users.models import UserRole

User = get_user_model()

def create_vendor_with_profile():
    """Create a complete vendor with profile, approved and verified"""
    print("🚀 Creating vendor with complete profile...")
    
    # Create user
    user_data = {
        'email': 'complete.vendor@carsportal.com',
        'password': 'VendorPass123!',
        'role': 'Seller',
        'is_active': True,
        'is_verified': True,
        'first_name': 'Complete',
        'last_name': 'Vendor',
        'phone_number': '+966501234567'
    }
    
    user, created = User.objects.get_or_create(
        email=user_data['email'],
        defaults=user_data
    )
    if created:
        user.set_password(user_data['password'])
        user.save()
        print(f"✅ Created user: {user.email}")
    else:
        print(f"✅ Found existing user: {user.email}")
    
    # Create business partner
    bp_data = {
        'name': 'Complete Auto Parts Co.',
        'type': 'company',
        'status': 'active',
        'legal_identifier': 'CR123456789',
        'user': user
    }
    
    business_partner, created = BusinessPartner.objects.get_or_create(
        user=user,
        name=bp_data['name'],
        defaults=bp_data
    )
    if created:
        print(f"✅ Created business partner: {business_partner.name} (BP: {business_partner.bp_number})")
    else:
        print(f"✅ Found existing business partner: {business_partner.name}")
    
    # Add vendor role
    vendor_role, created = BusinessPartnerRole.objects.get_or_create(
        business_partner=business_partner,
        role_type='vendor'
    )
    if created:
        print(f"✅ Added vendor role to business partner")
    
    # Create vendor profile
    vendor_profile_data = {
        'business_partner': business_partner,
        'is_approved': True
    }
    
    vendor_profile, created = VendorProfile.objects.get_or_create(
        business_partner=business_partner,
        defaults=vendor_profile_data
    )
    if created:
        print(f"✅ Created vendor profile with rating: {vendor_profile.vendor_rating}")
    else:
        print(f"✅ Found existing vendor profile")
    
    return user, business_partner, vendor_profile

def create_vehicle_data():
    """Create vehicle brands and models"""
    print("\n🚗 Creating vehicle brands and models...")
    
    # Create fuel types
    fuel_types = [
        {'name': 'Petrol', 'description': 'Gasoline fuel'},
        {'name': 'Diesel', 'description': 'Diesel fuel'},
        {'name': 'Electric', 'description': 'Electric power'},
        {'name': 'Hybrid', 'description': 'Hybrid electric and fuel'}
    ]
    
    for fuel_data in fuel_types:
        fuel, created = FuelType.objects.get_or_create(
            name=fuel_data['name'],
            defaults=fuel_data
        )
        if created:
            print(f"✅ Created fuel type: {fuel.name}")
    
    # Create transmission types
    transmission_types = [
        {'name': 'Manual', 'description': 'Manual transmission'},
        {'name': 'Automatic', 'description': 'Automatic transmission'},
        {'name': 'CVT', 'description': 'Continuously Variable Transmission'},
        {'name': 'DCT', 'description': 'Dual Clutch Transmission'}
    ]
    
    for trans_data in transmission_types:
        trans, created = TransmissionType.objects.get_or_create(
            name=trans_data['name'],
            defaults=trans_data
        )
        if created:
            print(f"✅ Created transmission type: {trans.name}")
    
    # Vehicle brands and models data
    vehicle_data = {
        'Toyota': ['Camry', 'Corolla', 'RAV4', 'Highlander', 'Tacoma', 'Yaris', 'Avalon'],
        'Honda': ['Civic', 'Accord', 'CR-V', 'Pilot', 'Odyssey', 'Fit', 'HR-V'],
        'Nissan': ['Altima', 'Maxima', 'Rogue', 'Pathfinder', 'Sentra', 'Murano', 'Titan'],
        'Ford': ['F-150', 'Escape', 'Explorer', 'Focus', 'Fusion', 'Edge', 'Mustang'],
        'Chevrolet': ['Silverado', 'Equinox', 'Malibu', 'Tahoe', 'Suburban', 'Traverse', 'Impala'],
        'BMW': ['3 Series', '5 Series', 'X3', 'X5', '7 Series', 'X1', '4 Series'],
        'Mercedes-Benz': ['C-Class', 'E-Class', 'S-Class', 'GLC', 'GLE', 'A-Class', 'GLA'],
        'Audi': ['A4', 'A6', 'Q5', 'Q7', 'A3', 'Q3', 'A8'],
        'Hyundai': ['Elantra', 'Sonata', 'Tucson', 'Santa Fe', 'Kona', 'Palisade', 'Accent'],
        'Kia': ['Optima', 'Sorento', 'Sportage', 'Forte', 'Telluride', 'Rio', 'Stinger']
    }
    
    brands_created = 0
    models_created = 0
    
    for brand_name, model_names in vehicle_data.items():
        # Create brand
        brand, created = Brand.objects.get_or_create(
            name=brand_name,
            defaults={
                'description': f'{brand_name} vehicles and parts',
                'country_of_origin': 'Various',
                'is_active': True
            }
        )
        if created:
            brands_created += 1
            print(f"✅ Created brand: {brand.name}")
        
        # Create models for this brand
        for model_name in model_names:
            model, created = VehicleModel.objects.get_or_create(
                brand=brand,
                name=model_name,
                defaults={
                    'description': f'{brand_name} {model_name} model',
                    'is_active': True
                }
            )
            if created:
                models_created += 1
    
    print(f"✅ Created {brands_created} brands and {models_created} vehicle models")
    return True

def create_vehicle_variants():
    """Create vehicle variants for part compatibility"""
    print("\n🚗 Creating vehicle variants...")
    
    # Create vehicle makes (taxonomy)
    makes_data = [
        'Toyota', 'Honda', 'Nissan', 'Ford', 'Chevrolet',
        'BMW', 'Mercedes-Benz', 'Audi', 'Hyundai', 'Kia'
    ]
    
    variants_created = 0
    
    for make_name in makes_data:
        # Create vehicle make
        make, created = VehicleMake.objects.get_or_create(
            name=make_name,
            defaults={
                'name_arabic': make_name,  # Simplified for now
                'is_active': True
            }
        )
        
        # Create some models for this make
        model_names = [f"{make_name} Model {i}" for i in range(1, 4)]  # 3 models per make
        
        for model_name in model_names:
            model_taxonomy, created = VehicleModelTaxonomy.objects.get_or_create(
                make=make,
                name=model_name,
                defaults={
                    'model_code': f"{make.name[:3].upper()}{model_name.split()[-1]}",
                    'is_active': True
                }
            )
            
            # Create variants for this model (different years, transmissions, fuel types)
            years = [2020, 2021, 2022, 2023]
            transmissions = ['manual', 'automatic', 'cvt']
            fuel_types = ['petrol', 'diesel', 'hybrid']
            
            for year in years:
                for transmission in transmissions[:2]:  # First 2 transmission types
                    for fuel_type in fuel_types[:2]:  # First 2 fuel types
                        variant_name = f"{transmission.title()} {fuel_type.title()}"
                        
                        variant, created = VehicleVariant.objects.get_or_create(
                            model=model_taxonomy,
                            name=variant_name,
                            year=year,
                            defaults={
                                'transmission_type': transmission,
                                'fuel_type': fuel_type,
                                'engine_code': f"ENG-{make.name[:3].upper()}-{year}",
                                'engine_displacement': round(random.uniform(1.5, 3.5), 1),
                                'is_active': True
                            }
                        )
                        
                        if created:
                            variants_created += 1
    
    print(f"✅ Created {variants_created} vehicle variants")
    return True

def create_part_categories():
    """Create part categories"""
    print("\n🔧 Creating part categories...")
    
    categories = [
        'Engine Parts', 'Transmission Parts', 'Brake System', 'Suspension & Steering',
        'Electrical System', 'Air Conditioning', 'Exhaust System', 'Fuel System',
        'Body Parts', 'Interior Parts', 'Lighting', 'Wheels & Tires',
        'Filters', 'Belts & Hoses', 'Sensors', 'Ignition System'
    ]
    
    categories_created = 0
    for category_name in categories:
        category, created = Category.objects.get_or_create(
            name=category_name,
            defaults={
                'description': f'{category_name} for vehicles'
            }
        )
        if created:
            categories_created += 1
    
    print(f"✅ Created {categories_created} part categories")
    return True

def create_part_brands():
    """Create part brands/manufacturers"""
    print("\n🏭 Creating part brands...")
    
    part_brands = [
        'Bosch', 'Denso', 'Magna', 'Continental', 'ZF Friedrichshafen', 'Aisin',
        'Valeo', 'Faurecia', 'Hyundai Mobis', 'Lear Corporation', 'Fiat Chrysler',
        'Johnson Controls', 'Toyota Boshoku', 'Yazaki', 'Bridgestone', 'Michelin',
        'Goodyear', 'Continental Tires', 'Pirelli', 'Hankook'
    ]
    
    brands_created = 0
    for brand_name in part_brands:
        brand, created = PartBrand.objects.get_or_create(
            name=brand_name,
            defaults={
                'description': f'{brand_name} automotive parts manufacturer',
                'is_active': True
            }
        )
        if created:
            brands_created += 1
    
    print(f"✅ Created {brands_created} part brands")
    return True

def create_parts_for_vendor(vendor_profile):
    """Create parts for the vendor"""
    print("\n⚙️ Creating parts for vendor...")
    
    # Get all categories, brands, and vehicle variants
    categories = list(Category.objects.all())
    part_brands = list(PartBrand.objects.all())
    vehicle_variants = list(VehicleVariant.objects.all())
    
    if not all([categories, part_brands, vehicle_variants]):
        print("❌ Missing required data (categories, brands, or vehicle variants)")
        return False
    
    # Sample parts data
    part_names = [
        'Engine Oil Filter', 'Air Filter', 'Fuel Filter', 'Cabin Air Filter',
        'Brake Pads', 'Brake Discs', 'Brake Calipers', 'Brake Lines',
        'Spark Plugs', 'Ignition Coils', 'Distributor Cap', 'Ignition Wires',
        'Alternator', 'Starter Motor', 'Battery', 'Voltage Regulator',
        'Radiator', 'Water Pump', 'Thermostat', 'Cooling Fan',
        'Transmission Filter', 'Clutch Kit', 'Gearbox Oil', 'Drive Shaft',
        'Shock Absorbers', 'Struts', 'Control Arms', 'Ball Joints',
        'Power Steering Pump', 'Steering Rack', 'Tie Rod Ends', 'Steering Column',
        'AC Compressor', 'AC Condenser', 'AC Evaporator', 'AC Filter',
        'Exhaust Manifold', 'Catalytic Converter', 'Muffler', 'Exhaust Pipes',
        'Fuel Pump', 'Fuel Injectors', 'Fuel Tank', 'Throttle Body',
        'Headlights', 'Tail Lights', 'Turn Signals', 'Fog Lights',
        'Bumpers', 'Fenders', 'Doors', 'Hood', 'Trunk Lid', 'Mirrors',
        'Wheels', 'Tires', 'Wheel Bearings', 'Hub Caps'
    ]
    
    parts_created = 0
    target_parts = 50  # Create 50 parts
    
    for i in range(target_parts):
        # Random selection of related data
        category = random.choice(categories)
        part_brand = random.choice(part_brands)
        vehicle_variant = random.choice(vehicle_variants)
        
        # Generate part number using variant info
        part_number = f"PART-{vehicle_variant.model.make.name[:3].upper()}-{vehicle_variant.model.name[:3].upper()}-{str(i+1).zfill(4)}"
        
        # Generate part name
        part_name = random.choice(part_names)
        if i < len(part_names):
            part_name = part_names[i]
        else:
            part_name = f"{random.choice(part_names)} {i+1}"
        
        # Create part
        part_data = {
            'parts_number': part_number,
            'material_description': part_name,
            'material_description_ar': f"{part_name} (Arabic)",
            'base_unit_of_measure': 'EA',
            'gross_weight': Decimal(str(random.uniform(0.1, 15.0))),
            'net_weight': Decimal(str(random.uniform(0.1, 14.5))),
            'size_dimensions': f"{random.randint(5, 50)}x{random.randint(5, 50)}x{random.randint(5, 30)}cm",
            'manufacturer_part_number': f"MPN-{str(i+1).zfill(6)}",
            'manufacturer_oem_number': f"OEM-{str(i+1).zfill(8)}",
            'category': category,
            'brand': part_brand,
            'vendor': vendor_profile.business_partner,
            'price': Decimal(str(random.uniform(10.0, 500.0))),
            'is_active': True
        }
        
        part, created = Part.objects.get_or_create(
            parts_number=part_number,
            defaults=part_data
        )
        
        if created:
            parts_created += 1
            # Add compatible vehicle variants
            compatible_variants = random.sample(vehicle_variants, min(3, len(vehicle_variants)))
            part.vehicle_variants.set(compatible_variants)
        
        # Always update/create inventory for the part (regardless of whether it's new or existing)
        inventory_data = {
            'stock': random.randint(10, 100),  # Ensure stock is available
            'reorder_level': random.randint(5, 20),
            'max_stock_level': random.randint(50, 200),
            'supplier_info': f"Supplier for {part_name}"
        }
        
        inventory, inv_created = Inventory.objects.get_or_create(
            part=part,
            defaults=inventory_data
        )
        
        # If inventory already exists, update the stock level
        if not inv_created:
            inventory.stock = random.randint(10, 100)
            inventory.reorder_level = random.randint(5, 20)
            inventory.max_stock_level = random.randint(50, 200)
            inventory.save()
            print(f"  📦 Updated inventory: {part.material_description} - Stock: {inventory.stock}")
        else:
            print(f"  📦 Created inventory: {part.material_description} - Stock: {inventory.stock}")
    
    print(f"✅ Created {parts_created} parts with inventory")
    return True

def update_out_of_stock_inventory():
    """Update inventory for parts that are out of stock"""
    print("\n📦 Updating out of stock inventory...")
    
    # Find all inventory records with stock <= 0
    out_of_stock = Inventory.objects.filter(stock__lte=0)
    updated_count = 0
    
    for inventory in out_of_stock:
        old_stock = inventory.stock
        inventory.stock = random.randint(10, 100)  # Restock with random amount
        inventory.save()
        updated_count += 1
        print(f"  📦 Restocked {inventory.part.material_description}: {old_stock} → {inventory.stock}")
    
    # Also find parts that don't have inventory records at all
    parts_without_inventory = Part.objects.filter(inventory__isnull=True)
    created_count = 0
    
    for part in parts_without_inventory:
        inventory_data = {
            'stock': random.randint(10, 100),
            'reorder_level': random.randint(5, 20),
            'max_stock_level': random.randint(50, 200),
            'supplier_info': f"Supplier for {part.material_description}"
        }
        
        Inventory.objects.create(part=part, **inventory_data)
        created_count += 1
        print(f"  📦 Created inventory for {part.material_description}: {inventory_data['stock']}")
    
    print(f"✅ Updated {updated_count} out-of-stock items, created {created_count} new inventory records")
    return True

def display_inventory_status(vendor_profile):
    """Display current inventory status for vendor parts"""
    print("\n📊 Current Inventory Status:")
    
    vendor_parts = Part.objects.filter(vendor=vendor_profile.business_partner)
    total_parts = vendor_parts.count()
    
    # Count parts by stock level
    in_stock = Inventory.objects.filter(part__vendor=vendor_profile.business_partner, stock__gt=10).count()
    low_stock = Inventory.objects.filter(part__vendor=vendor_profile.business_partner, stock__gt=0, stock__lte=10).count()
    out_of_stock = Inventory.objects.filter(part__vendor=vendor_profile.business_partner, stock__lte=0).count()
    no_inventory = vendor_parts.filter(inventory__isnull=True).count()
    
    print(f"  📦 Total Parts: {total_parts}")
    print(f"  ✅ In Stock (>10): {in_stock}")
    print(f"  ⚠️  Low Stock (1-10): {low_stock}")
    print(f"  ❌ Out of Stock (0): {out_of_stock}")
    print(f"  📋 No Inventory Record: {no_inventory}")
    
    # Show some examples of out-of-stock items
    if out_of_stock > 0:
        print("\n  ❌ Sample Out-of-Stock Items:")
        out_of_stock_items = Inventory.objects.filter(
            part__vendor=vendor_profile.business_partner, 
            stock__lte=0
        )[:5]
        for item in out_of_stock_items:
            print(f"     • {item.part.material_description}: {item.stock}")
    
    return True

def create_orders_against_vendor(vendor_profile):
    """Create orders for parts from the vendor"""
    print("\n📋 Creating orders against vendor...")
    
    # Get all parts from this vendor
    vendor_parts = Part.objects.filter(vendor=vendor_profile.business_partner)
    
    if not vendor_parts.exists():
        print("❌ No parts found for vendor")
        return False
    
    orders_created = 0
    target_orders = 20  # Create 20 orders
    
    for i in range(target_orders):
        # Create a customer user for the order
        customer_email = f"customer{i+1}@example.com"
        customer, created = User.objects.get_or_create(
            email=customer_email,
            defaults={
                'first_name': f'Customer{i+1}',
                'last_name': 'User',
                'is_active': True,
                'is_verified': True
            }
        )
        if created:
            customer.set_password('CustomerPass123!')
            customer.save()
        
        # Create order
        order_number = f"ORD-{datetime.now().strftime('%Y%m%d')}-{str(i+1).zfill(4)}"
        
        # Select random parts for this order (2-5 parts)
        num_parts = random.randint(2, 5)
        selected_parts = random.sample(list(vendor_parts), min(num_parts, len(vendor_parts)))
        
        # Calculate order total
        total_price = Decimal('0.00')
        shipping_cost = Decimal(str(random.uniform(10.0, 50.0)))
        tax_amount = Decimal(str(random.uniform(5.0, 25.0)))
        
        order_data = {
            'customer': customer,
            'order_number': order_number,
            'total_price': total_price,  # Will be updated after adding items
            'shipping_cost': shipping_cost,
            'tax_amount': tax_amount,
            'status': random.choice(['pending', 'confirmed', 'processing', 'shipped', 'delivered']),
            'payment_method': random.choice(['cash_on_delivery', 'bank_transfer', 'credit_card']),
            'payment_status': random.choice(['pending', 'processing', 'completed']),
            'notes': f"Order for automotive parts - Customer {i+1}"
        }
        
        order, order_created = Order.objects.get_or_create(
            order_number=order_number,
            defaults=order_data
        )
        
        if order_created:
            orders_created += 1
            
            # Add order items
            order_total = Decimal('0.00')
            for part in selected_parts:
                quantity = random.randint(1, 5)
                price = part.price
                
                OrderItem.objects.create(
                    order=order,
                    part=part,
                    quantity=quantity,
                    price=price
                )
                
                order_total += (price * quantity)
                
                # Update inventory (reduce stock)
                try:
                    inventory = Inventory.objects.get(part=part)
                    inventory.stock = max(0, inventory.stock - quantity)
                    inventory.save()
                except Inventory.DoesNotExist:
                    pass
            
            # Update order total
            order.total_price = order_total + shipping_cost + tax_amount
            order.save()
            
            print(f"  📦 Created order: {order.order_number} - {len(selected_parts)} items - Total: {order.total_price}")
    
    print(f"✅ Created {orders_created} orders against vendor")
    return True

def main():
    """Main function to populate all data"""
    print("🎯 Starting comprehensive database population...")
    print("=" * 60)
    
    try:
        # Step 1: Create vendor with complete profile
        user, business_partner, vendor_profile = create_vendor_with_profile()
        
        # Step 2: Create vehicle data (brands and models)
        create_vehicle_data()
        
        # Step 3: Create vehicle variants for part compatibility
        create_vehicle_variants()
        
        # Step 4: Create part categories
        create_part_categories()
        
        # Step 5: Create part brands
        create_part_brands()
        
        # Step 6: Create parts for vendor
        create_parts_for_vendor(vendor_profile)
        
        # Step 7: Display current inventory status
        display_inventory_status(vendor_profile)
        
        # Step 8: Update out of stock inventory
        update_out_of_stock_inventory()
        
        # Step 9: Display updated inventory status
        display_inventory_status(vendor_profile)
        
        # Step 10: Create orders against vendor
        create_orders_against_vendor(vendor_profile)
        
        print("\n" + "=" * 60)
        print("🎉 Database population completed successfully!")
        print(f"📊 Vendor Profile: {business_partner.name}")
        print(f"📊 Business Partner: {business_partner.name} (BP: {business_partner.bp_number})")
        print(f"📊 User: {user.email}")
        print("\n📋 Summary:")
        print(f"   • Brands: {Brand.objects.count()}")
        print(f"   • Vehicle Models: {VehicleModel.objects.count()}")
        print(f"   • Part Categories: {Category.objects.count()}")
        print(f"   • Part Brands: {PartBrand.objects.count()}")
        print(f"   • Parts: {Part.objects.filter(vendor=business_partner).count()}")
        print(f"   • Orders: {Order.objects.filter(items__part__vendor=business_partner).distinct().count()}")
        print(f"   • Inventory Records: {Inventory.objects.filter(part__vendor=business_partner).count()}")
        
        print("\n🔑 Login Credentials:")
        print(f"   Email: {user.email}")
        print(f"   Password: VendorPass123!")
        
    except Exception as e:
        print(f"❌ Error during population: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()