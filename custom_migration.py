#!/usr/bin/env python
"""
Custom migration to handle the SaudiCity to City transition
This script will:
1. Create the new Country and City tables manually
2. Migrate data from SaudiCity to City
3. Update foreign key references
4. Drop the old SaudiCity table
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yallamotor_project.settings')
django.setup()

from django.db import connection

def run_custom_migration():
    """Run the custom migration to handle SaudiCity to City transition"""
    print("Starting custom migration from SaudiCity to City...")
    
    with connection.cursor() as cursor:
        # 1. Check if SaudiCity table exists
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
        
        # 2. Check if City table already exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'parts_city'
            )
        """)
        city_exists = cursor.fetchone()[0]
        
        if city_exists:
            print("City table already exists. Migration may have been done.")
            return
        
        print("Creating new Country and City tables...")
        
        # 3. Create Country table
        cursor.execute("""
            CREATE TABLE parts_country (
                code VARCHAR(2) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                name_ar VARCHAR(100),
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # 4. Create City table
        cursor.execute("""
            CREATE TABLE parts_city (
                id BIGSERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                name_ar VARCHAR(100),
                region VARCHAR(100),
                region_ar VARCHAR(100),
                is_active BOOLEAN DEFAULT TRUE,
                country_id VARCHAR(2) REFERENCES parts_country(code)
            )
        """)
        
        # 5. Create unique constraint
        cursor.execute("""
            ALTER TABLE parts_city ADD CONSTRAINT parts_city_country_name_unique 
            UNIQUE (country_id, name)
        """)
        
        # 6. Create indexes
        cursor.execute("CREATE INDEX parts_city_country_id_idx ON parts_city (country_id)")
        
        print("Migrating data from SaudiCity to City...")
        
        # 7. Create Saudi Arabia country
        cursor.execute("""
            INSERT INTO parts_country (code, name, name_ar, is_active)
            VALUES ('SA', 'Saudi Arabia', 'المملكة العربية السعودية', TRUE)
        """)
        
        # 8. Migrate SaudiCity data to City
        cursor.execute("""
            INSERT INTO parts_city (name, name_ar, region, region_ar, is_active, country_id)
            SELECT name, name_ar, region, region_ar, is_active, 'SA'
            FROM parts_saudicity
        """)
        
        # 9. Count migrated records
        cursor.execute("SELECT COUNT(*) FROM parts_city")
        migrated_count = cursor.fetchone()[0]
        print(f"Migrated {migrated_count} cities from SaudiCity to City")
        
        # 10. Update foreign key references
        print("Updating foreign key references...")
        
        # Update cityarea table
        cursor.execute("""
            UPDATE parts_cityarea ca
            SET city_id = c.id
            FROM parts_city c
            WHERE ca.city_id = c.id
        """)
        
        # Update shippingrate table
        cursor.execute("""
            UPDATE parts_shippingrate sr
            SET city_id = c.id
            FROM parts_city c
            WHERE sr.city_id = c.id
        """)
        
        # Update ordershipping table
        cursor.execute("""
            UPDATE parts_ordershipping os
            SET city_id = c.id
            FROM parts_city c
            WHERE os.city_id = c.id
        """)
        
        print("Foreign key references updated successfully")
        
        # 11. Drop the old SaudiCity table
        print("Dropping old SaudiCity table...")
        cursor.execute("DROP TABLE parts_saudicity")
        
        print("Custom migration completed successfully!")

if __name__ == '__main__':
    run_custom_migration()