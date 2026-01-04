#!/usr/bin/env python
"""
Custom migration script to handle the transition from SaudiCity to City model
This script should be run before applying migration 0026
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yallamotor_project.settings')
django.setup()

from django.db import connection

def migrate_saudicity_data():
    """Migrate data from SaudiCity to City model"""
    print("Starting SaudiCity to City migration...")
    
    # Check if SaudiCity table exists
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'parts_saudicity'
            )
        """)
        saudi_city_table_exists = cursor.fetchone()[0]
        
        if not saudi_city_table_exists:
            print("SaudiCity table does not exist. Nothing to migrate.")
            return
        
        # Check if City table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'parts_city'
            )
        """)
        city_table_exists = cursor.fetchone()[0]
        
        if city_table_exists:
            print("City table already exists. Migration may have already been done.")
            return
        
        # Create Saudi Arabia country first
        cursor.execute("""
            INSERT INTO parts_country (code, name, name_ar, is_active)
            VALUES ('SA', 'Saudi Arabia', 'المملكة العربية السعودية', true)
            ON CONFLICT (code) DO NOTHING
        """)
        
        # Get Saudi Arabia country ID
        cursor.execute("SELECT code FROM parts_country WHERE code = 'SA'")
        sa_country_code = cursor.fetchone()[0]
        
        # Migrate SaudiCity data to City
        cursor.execute("""
            INSERT INTO parts_city (name, name_ar, region, region_ar, is_active, country_id)
            SELECT 
                name, 
                name_ar, 
                region, 
                region_ar, 
                is_active,
                %s
            FROM parts_saudicity
        """, [sa_country_code])
        
        # Count migrated records
        cursor.execute("SELECT COUNT(*) FROM parts_city")
        migrated_count = cursor.fetchone()[0]
        
        print(f"Successfully migrated {migrated_count} cities from SaudiCity to City")
        
        # Update foreign key references in cityarea table
        cursor.execute("""
            UPDATE parts_cityarea ca
            SET city_id = c.id
            FROM parts_city c
            WHERE ca.city_id = c.id
        """)
        
        # Update foreign key references in shippingrate table
        cursor.execute("""
            UPDATE parts_shippingrate sr
            SET city_id = c.id
            FROM parts_city c
            WHERE sr.city_id = c.id
        """)
        
        # Update foreign key references in ordershipping table
        cursor.execute("""
            UPDATE parts_ordershipping os
            SET city_id = c.id
            FROM parts_city c
            WHERE os.city_id = c.id
        """)
        
        print("Foreign key references updated successfully")

if __name__ == '__main__':
    migrate_saudicity_data()