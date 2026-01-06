#!/usr/bin/env python
"""
Test script to verify synchronous processing works without Celery/Redis
"""

import os
import sys
import django
import time
from io import BytesIO

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yallamotor_project.settings')
sys.path.insert(0, os.getcwd())

django.setup()

from business_partners.vendor_views import should_process_synchronously, process_import_file_sync
from business_partners.models import BusinessPartner
from users.models import User

def test_sync_processing():
    print("🧪 Testing Synchronous Processing (No Celery/Redis)")
    print("=" * 60)
    
    # Create a test file object
    test_content = """parts_number,category_name,brand_name,manufacturer_part_number,manufacturer_oem_number,material_description,price,quantity
TEST001,Engine Parts,Toyota,12345,67890,Spark Plug,25.50,100
TEST002,Brakes,Bosch,54321,09876,Brake Pad,45.75,50
TEST003,Filters,Mann,11111,22222,Oil Filter,15.25,200
TEST004,Suspension,Monroe,33333,44444,Shock Absorber,89.99,30
TEST005,Electrical,Denso,55555,66666,Alternator,120.00,25"""
    
    file_obj = BytesIO(test_content.encode('utf-8'))
    file_obj.name = 'test_sync.csv'
    file_obj.size = len(test_content)
    
    # Test file size detection
    print(f"📊 File size: {file_obj.size} bytes ({file_obj.size/1024:.2f} KB)")
    
    # Test synchronous decision
    should_sync = should_process_synchronously(file_obj)
    print(f"🔍 Should process synchronously: {should_sync}")
    
    if should_sync:
        print("✅ File qualifies for synchronous processing")
        
        # Get a test business partner
        try:
            user = User.objects.get(email='admin@example.com')
            business_partner = BusinessPartner.objects.filter(user=user).first()
            
            if not business_partner:
                print("⚠️  No business partner found, creating test one...")
                business_partner = BusinessPartner.objects.create(
                    name="Test Vendor",
                    user=user,
                    business_partner_type='vendor'
                )
            
            print(f"👤 Using business partner: {business_partner.name}")
            
            # Test synchronous processing
            print("⏱️  Starting synchronous processing...")
            start_time = time.time()
            
            results = process_import_file_sync(
                import_file=file_obj,
                business_partner=business_partner,
                import_status='published',
                update_existing=False,
                validate_only=False,
                chunk_size=1000
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"✅ Synchronous processing completed in {processing_time:.2f} seconds")
            print(f"📈 Results: {results['created_count']} created, {results['updated_count']} updated, {results['error_count']} errors")
            print(f"📊 Total rows processed: {results['total_rows']}")
            
            # Calculate processing speed
            if results['total_rows'] > 0:
                rows_per_second = results['total_rows'] / processing_time
                print(f"⚡ Processing speed: {rows_per_second:.2f} rows/second")
            
        except Exception as e:
            print(f"❌ Error during testing: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ File should not be processed synchronously (unexpected)")

if __name__ == "__main__":
    test_sync_processing()