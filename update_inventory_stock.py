#!/usr/bin/env python
"""
Standalone script to update inventory stock levels for existing parts.
This script ensures all parts have adequate stock levels and updates out-of-stock items.
"""

import os
import django
import random
from decimal import Decimal

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yallamotor_project.settings')
django.setup()

from parts.models import Part, Inventory
from business_partners.models import BusinessPartner, VendorProfile

def update_all_inventory(min_stock=10, max_stock=100):
    """
    Update all inventory records to ensure adequate stock levels.
    
    Args:
        min_stock: Minimum stock level to set (default: 10)
        max_stock: Maximum stock level to set (default: 100)
    """
    print("🔄 Starting inventory update process...")
    
    # Get all parts that have inventory records
    all_inventory = Inventory.objects.all()
    updated_count = 0
    
    for inventory in all_inventory:
        if inventory.stock <= 0:
            old_stock = inventory.stock
            new_stock = random.randint(min_stock, max_stock)
            inventory.stock = new_stock
            inventory.save()
            updated_count += 1
            print(f"  📦 Restocked {inventory.part.material_description}: {old_stock} → {new_stock}")
    
    print(f"✅ Updated {updated_count} inventory records with zero or negative stock")
    
    # Handle parts without inventory records
    parts_without_inventory = Part.objects.filter(inventory__isnull=True)
    created_count = 0
    
    for part in parts_without_inventory:
        inventory_data = {
            'stock': random.randint(min_stock, max_stock),
            'reorder_level': random.randint(5, 20),
            'max_stock_level': random.randint(50, 200),
            'supplier_info': f"Supplier for {part.material_description}"
        }
        
        Inventory.objects.create(part=part, **inventory_data)
        created_count += 1
        print(f"  📦 Created inventory for {part.material_description}: {inventory_data['stock']}")
    
    print(f"✅ Created {created_count} new inventory records")
    return updated_count + created_count

def update_vendor_inventory(vendor_business_partner, min_stock=10, max_stock=100):
    """
    Update inventory for a specific vendor's parts.
    
    Args:
        vendor_business_partner: BusinessPartner instance of the vendor
        min_stock: Minimum stock level to set (default: 10)
        max_stock: Maximum stock level to set (default: 100)
    """
    print(f"🔄 Updating inventory for vendor: {vendor_business_partner.name}")
    
    # Get all parts for this vendor
    vendor_parts = Part.objects.filter(vendor=vendor_business_partner)
    
    updated_count = 0
    created_count = 0
    
    for part in vendor_parts:
        # Check if inventory exists
        try:
            inventory = Inventory.objects.get(part=part)
            if inventory.stock <= 0:
                old_stock = inventory.stock
                new_stock = random.randint(min_stock, max_stock)
                inventory.stock = new_stock
                inventory.save()
                updated_count += 1
                print(f"  📦 Restocked {part.material_description}: {old_stock} → {new_stock}")
        except Inventory.DoesNotExist:
            # Create new inventory record
            inventory_data = {
                'stock': random.randint(min_stock, max_stock),
                'reorder_level': random.randint(5, 20),
                'max_stock_level': random.randint(50, 200),
                'supplier_info': f"Supplier for {part.material_description}"
            }
            
            Inventory.objects.create(part=part, **inventory_data)
            created_count += 1
            print(f"  📦 Created inventory for {part.material_description}: {inventory_data['stock']}")
    
    print(f"✅ Updated {updated_count} inventory records, created {created_count} new records")
    return updated_count + created_count

def display_inventory_summary():
    """Display a summary of current inventory status"""
    print("\n📊 Current Inventory Summary:")
    
    total_parts = Part.objects.count()
    total_inventory = Inventory.objects.count()
    
    # Stock level breakdown
    in_stock = Inventory.objects.filter(stock__gt=10).count()
    low_stock = Inventory.objects.filter(stock__gt=0, stock__lte=10).count()
    out_of_stock = Inventory.objects.filter(stock__lte=0).count()
    no_inventory = Part.objects.filter(inventory__isnull=True).count()
    
    print(f"  📦 Total Parts: {total_parts}")
    print(f"  📋 Parts with Inventory: {total_inventory}")
    print(f"  ✅ Well Stocked (>10): {in_stock}")
    print(f"  ⚠️  Low Stock (1-10): {low_stock}")
    print(f"  ❌ Out of Stock (≤0): {out_of_stock}")
    print(f"  📋 No Inventory Record: {no_inventory}")
    
    # Vendor-specific breakdown
    print("\n📊 Vendor-Specific Inventory:")
    vendors = VendorProfile.objects.filter(is_approved=True)
    
    for vendor in vendors:
        vendor_parts = Part.objects.filter(vendor=vendor.business_partner)
        vendor_inventory = Inventory.objects.filter(part__vendor=vendor.business_partner)
        out_of_stock_count = vendor_inventory.filter(stock__lte=0).count()
        
        print(f"  🏪 {vendor.business_partner.name}:")
        print(f"     Parts: {vendor_parts.count()}")
        print(f"     Inventory Records: {vendor_inventory.count()}")
        print(f"     Out of Stock: {out_of_stock_count}")

def main():
    """Main function to run inventory updates"""
    print("🎯 Inventory Stock Update Script")
    print("=" * 50)
    
    # Display current status
    display_inventory_summary()
    
    # Option 1: Update all inventory
    print("\n1️⃣ Update all inventory across all vendors")
    all_updated = update_all_inventory(min_stock=15, max_stock=120)
    
    # Option 2: Update specific vendor inventory (if you have a preferred vendor)
    print("\n2️⃣ Update inventory for specific vendors")
    approved_vendors = VendorProfile.objects.filter(is_approved=True)
    
    if approved_vendors.exists():
        for vendor in approved_vendors:
            vendor_updated = update_vendor_inventory(
                vendor.business_partner, 
                min_stock=15, 
                max_stock=120
            )
    
    # Display final status
    print("\n" + "=" * 50)
    print("✅ Inventory Update Complete!")
    display_inventory_summary()
    
    print(f"\n📋 Summary:")
    print(f"   • Total parts processed: {all_updated}")
    print(f"   • All parts now have adequate stock levels")
    print(f"   • No parts should be out of stock")

if __name__ == "__main__":
    main()