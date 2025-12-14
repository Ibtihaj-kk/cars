#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yallamotor_project.settings')
django.setup()

from business_partners.models import BusinessPartner
from django.contrib.auth.models import User

def create_second_vendor():
    print("=== Creating Second Vendor ===")
    
    # Create a new user for the second vendor
    user2, created = User.objects.get_or_create(
        username='vendor2',
        defaults={
            'email': 'vendor2@example.com',
            'first_name': 'Second',
            'last_name': 'Vendor'
        }
    )
    
    if created:
        user2.set_password('vendor123')
        user2.save()
        print(f"Created user: {user2.username}")
    else:
        print(f"Found existing user: {user2.username}")
    
    # Create a new BusinessPartner for the second vendor
    partner2, created = BusinessPartner.objects.get_or_create(
        bp_number='BP999998',  # Different BP number
        defaults={
            'name': 'Second Test Vendor Company',
            'type': 'company',
            'legal_identifier': 'TEST123457',
            'status': 'active',
            'user': user2
        }
    )
    
    if created:
        print(f"Created business partner: {partner2.name} ({partner2.bp_number})")
    else:
        print(f"Found existing business partner: {partner2.name} ({partner2.bp_number})")
    
    # Check all vendors
    vendors = BusinessPartner.objects.filter(type='company')  # Assuming vendors are companies
    print(f"\nTotal vendors found: {vendors.count()}")
    for v in vendors:
        print(f"  BP: {v.bp_number}, Name: {v.name}, User: {v.user.username if v.user else 'No user'}")

if __name__ == '__main__':
    create_second_vendor()