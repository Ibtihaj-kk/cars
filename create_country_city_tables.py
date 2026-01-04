#!/usr/bin/env python
"""
Script to manually create the Country and City tables and migrate data
This bypasses Django migrations to handle the complex foreign key constraints
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yallamotor_project.settings')
django.setup()

from django.db import connection

def create_tables_and_migrate():
    """Create Country and City tables and migrate data from SaudiCity"""
    print("Creating Country and City tables...")
    
    with connection.cursor() as cursor:
        # Step 1: Create Country table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parts_country (
                code VARCHAR(2) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                name_ar VARCHAR(100),
                is_active BOOLEAN DEFAULT true
            )
        """)
        
        # Step 2: Create City table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parts_city (
                id SERIAL PRIMARY KEY,
                country_id VARCHAR(2) NOT NULL REFERENCES parts_country(code),
                name VARCHAR(100) NOT NULL,
                name_ar VARCHAR(100),
                region VARCHAR(100),
                region_ar VARCHAR(100),
                is_active BOOLEAN DEFAULT true
            )
        """)
        
        # Step 3: Create unique constraint for City
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS parts_city_country_name_unique 
            ON parts_city (country_id, name)
        """)
        
        # Step 4: Insert Saudi Arabia country
        cursor.execute("""
            INSERT INTO parts_country (code, name, name_ar, is_active)
            VALUES ('SA', 'Saudi Arabia', 'المملكة العربية السعودية', true)
            ON CONFLICT (code) DO NOTHING
        """)
        
        # Step 5: Migrate SaudiCity data to City
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
        
        print("Country and City tables created successfully!")

if __name__ == '__main__':
    create_tables_and_migrate()