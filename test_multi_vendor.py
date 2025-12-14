#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yallamotor_project.settings')
django.setup()

from business_partners.models import BusinessPartner
from parts.models import Part, VendorOrderItemStatus, Order, OrderItem
from django.contrib.auth.models import User

def check_test_data():
    print("=== Checking Test Data ===")
    
    # Check vendors
    vendors = BusinessPartner.objects.filter(type='vendor')
    print(f"Vendors found: {vendors.count()}")
    for v in vendors:
        print(f"  ID: {v.id}, Name: {v.name}, Email: {v.user.email if v.user else 'No user'}")
    
    # Check parts
    parts = Part.objects.all()
    print(f"\nParts found: {parts.count()}")
    for p in parts[:5]:
        print(f"  ID: {p.id}, Name: {p.name}, SKU: {p.sku}")
    
    # Check vendor parts (parts with vendor relationships)
    vendor_parts = Part.objects.filter(vendor__isnull=False)
    print(f"\nVendor parts found: {vendor_parts.count()}")
    for part in vendor_parts[:5]:
        print(f"  Vendor: {part.vendor.name}, Part: {part.name}, Price: {part.price}")
    
    # Check orders
    orders = Order.objects.all()
    print(f"\nOrders found: {orders.count()}")
    for o in orders[:3]:
        customer_name = o.customer.username if hasattr(o.customer, 'username') else str(o.customer)
        print(f"  Order ID: {o.id}, Customer: {customer_name}")
        items = OrderItem.objects.filter(order=o)
        print(f"    Items: {items.count()}")
        for item in items:
            print(f"      {item.part.name} x{item.quantity}")

def create_cross_vendor_order():
    print("\n=== Creating Cross-Vendor Order ===")
    
    # Get the first two vendors
    vendors = BusinessPartner.objects.filter(type='vendor')[:2]
    if len(vendors) < 2:
        print("Need at least 2 vendors for cross-vendor order")
        return
    
    vendor1, vendor2 = vendors
    print(f"Using vendors: {vendor1.name} and {vendor2.name}")
    
    # Get parts from each vendor
    vendor1_parts = Part.objects.filter(vendor=vendor1)[:2]
    vendor2_parts = Part.objects.filter(vendor=vendor2)[:2]
    
    if not vendor1_parts or not vendor2_parts:
        print("Need parts from both vendors")
        return
    
    # Create a new order with items from both vendors
    from orders.models import BusinessPartner as Customer
    customer = Customer.objects.filter(type='customer').first()
    if not customer:
        print("No customer found")
        return
    
    order = Order.objects.create(
        customer=customer,
        status='pending',
        total_amount=0
    )
    
    # Add items from both vendors
    total = 0
    for part in vendor1_parts:
        item = OrderItem.objects.create(
            order=order,
            part=part,
            quantity=2,
            unit_price=part.price,
            subtotal=part.price * 2
        )
        total += item.subtotal
        print(f"Added item from {vendor1.name}: {part.name}")
    
    for part in vendor2_parts:
        item = OrderItem.objects.create(
            order=order,
            part=part,
            quantity=1,
            unit_price=part.price,
            subtotal=part.price * 1
        )
        total += item.subtotal
        print(f"Added item from {vendor2.name}: {part.name}")
    
    order.total_amount = total
    order.save()
    
    print(f"Created cross-vendor order {order.id} with total: {total}")
    
    # Create vendor-specific status entries
    for item in OrderItem.objects.filter(order=order):
        # Find the vendor for this item
        if item.part.vendor:
            vendor_status, created = VendorOrderItemStatus.objects.get_or_create(
                order_item=item,
                vendor=item.part.vendor,
                defaults={'status': 'pending'}
            )
            print(f"Created vendor status for {item.part.vendor.name} - {item.part.name}: {vendor_status.status}")
    
    return order

if __name__ == '__main__':
    check_test_data()
    create_cross_vendor_order()