import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yallamotor_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from business_partners.models import BusinessPartner, VendorProfile, VendorApplication, SecureVendorApplication, BusinessPartnerRole, ContactInfo, Address
from django.db import connection

User = get_user_model()

print("Starting data cleanup...")

# 0. Clean up orphaned M2M tables that might block deletion
print("Cleaning up parts_part_vehicle_variants table...")
with connection.cursor() as cursor:
    try:
        # Check if table exists first to avoid errors if it doesn't
        cursor.execute("SELECT to_regclass('parts_part_vehicle_variants');")
        if cursor.fetchone()[0]:
            cursor.execute("DELETE FROM parts_part_vehicle_variants;")
            print("Deleted rows from parts_part_vehicle_variants.")
        else:
            print("Table parts_part_vehicle_variants does not exist.")
    except Exception as e:
        print(f"Error clearing parts_part_vehicle_variants: {e}")

try:
    # 1. Delete Vendor Profiles
    count = VendorProfile.objects.count()
    print(f"Deleting {count} VendorProfiles...")
    VendorProfile.objects.all().delete()
except Exception as e:
    print(f"Error deleting VendorProfiles: {e}")

try:
    # 2. Delete BusinessPartnerRoles
    count = BusinessPartnerRole.objects.count()
    print(f"Deleting {count} BusinessPartnerRoles...")
    BusinessPartnerRole.objects.all().delete()
except Exception as e:
    print(f"Error deleting BusinessPartnerRoles: {e}")

try:
    # 3. Delete ContactInfos
    count = ContactInfo.objects.count()
    print(f"Deleting {count} ContactInfos...")
    ContactInfo.objects.all().delete()
except Exception as e:
    print(f"Error deleting ContactInfos: {e}")

try:
    # 4. Delete Addresses
    count = Address.objects.count()
    print(f"Deleting {count} Addresses...")
    Address.objects.all().delete()
except Exception as e:
    print(f"Error deleting Addresses: {e}")

try:
    # 5. Delete VendorApplications
    count = VendorApplication.objects.count()
    print(f"Deleting {count} VendorApplications...")
    VendorApplication.objects.all().delete()
except Exception as e:
    print(f"Error deleting VendorApplications: {e}")

try:
    # 6. Delete SecureVendorApplications
    count = SecureVendorApplication.objects.count()
    print(f"Deleting {count} SecureVendorApplications...")
    SecureVendorApplication.objects.all().delete()
except Exception as e:
    print(f"Error deleting SecureVendorApplications: {e}")

try:
    # 7. Delete BusinessPartners
    count = BusinessPartner.objects.count()
    print(f"Deleting {count} BusinessPartners...")
    BusinessPartner.objects.all().delete()
except Exception as e:
    print(f"Error deleting BusinessPartners: {e}")

try:
    # 8. Delete Users (including soft-deleted)
    if hasattr(User.objects, 'all_with_deleted'):
        qs = User.objects.all_with_deleted()
    else:
        qs = User.objects.all()
    
    count = qs.count()
    print(f"Deleting {count} Users...")
    qs.delete()
except Exception as e:
    print(f"Error deleting Users: {e}")

print("Cleanup complete.")
