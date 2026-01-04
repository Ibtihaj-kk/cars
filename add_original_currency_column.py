#!/usr/bin/env python
"""
Script to manually add original_currency column to parts_part table
"""
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yallamotor_project.settings')
django.setup()

from django.db import connection

def add_original_currency_column():
    """Manually add original_currency column to parts_part table"""
    try:
        with connection.cursor() as cursor:
            # Check if column already exists
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'parts_part' AND column_name = 'original_currency'")
            if cursor.fetchone():
                print('✓ original_currency column already exists!')
                return True
            
            # Add the column
            print('Adding original_currency column to parts_part table...')
            cursor.execute("ALTER TABLE parts_part ADD COLUMN original_currency VARCHAR(3) DEFAULT 'USD'")
            print('✓ original_currency column added successfully!')
            return True
            
    except Exception as e:
        print(f'✗ Error adding column: {e}')
        return False

if __name__ == '__main__':
    add_original_currency_column()