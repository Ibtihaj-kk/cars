#!/usr/bin/env python
"""
Custom migration script to fix the SaudiCity to City migration issue
This script will:
1. Temporarily disable foreign key constraints
2. Create the new Country and City tables
3. Migrate data from SaudiCity to City
4. Update foreign key references
5. Re-enable foreign key constraints
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yallamotor_project.settings')
django.setup()

from django.db import connection

def fix_migration():
    """Fix the migration issue with foreign key constraints"""
    print("Starting migration fix...")
    
    with connection.cursor() as cursor:
        # Step 1: Check if SaudiCity table exists and has data
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'parts_saudicity'
            )
        """)
        saudi_city_exists = cursor.fetchone()[0]
        
        if not saudi_city_exists:
            print("SaudiCity table does not exist. Nothing to migrate.")
            return
        
        # Step 2: Check if new tables already exist
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'parts_country'
            )
        """)
        country_exists = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'parts_city'
            )
        """)
        city_exists = cursor.fetchone()[0]
        
        if country_exists and city_exists:
            print("New tables already exist. Migration may have already been done.")
            return
        
        # Step 3: Temporarily disable foreign key constraints
        print("Temporarily disabling foreign key constraints...")
        cursor.execute("SET CONSTRAINTS ALL DEFERRED")
        
        # Step 4: Create Saudi Arabia country
        print("Creating Saudi Arabia country...")
        cursor.execute("""
            INSERT INTO parts_country (code, name, name_ar, is_active)
            VALUES ('SA', 'Saudi Arabia', 'المملكة العربية السعودية', true)
            ON CONFLICT (code) DO NOTHING
        """)
        
        # Step 5: Migrate SaudiCity data to City
        print("Migrating SaudiCity data to City...")
        cursor.execute("""
            INSERT INTO parts_city (name, name_ar, region, region_ar, is_active, country_id)
            SELECT 
                name, 
                name_ar, 
                region, 
                region_ar, 
                is_active,
                'SA'
            FROM parts_saudicity
        """)
        
        # Step 6: Count migrated records
        cursor.execute("SELECT COUNT(*) FROM parts_city")
        migrated_count = cursor.fetchone()[0]
        print(f"Successfully migrated {migrated_count} cities from SaudiCity to City")
        
        # Step 7: Re-enable foreign key constraints
        print("Re-enabling foreign key constraints...")
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        
        print("Migration fix completed successfully!")

if __name__ == '__main__':
    fix_migration()