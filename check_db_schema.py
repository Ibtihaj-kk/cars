#!/usr/bin/env python
"""
Script to check if original_currency column exists in parts_part table
"""
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yallamotor_project.settings')
django.setup()

from django.db import connection

def check_original_currency_column():
    """Check if original_currency column exists"""
    with connection.cursor() as cursor:
        # For PostgreSQL
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'parts_part'")
        columns = [row[0] for row in cursor.fetchall()]
        
        print('Parts table columns:')
        for col in sorted(columns):
            print(f'  - {col}')
        
        # Check if original_currency exists
        if 'original_currency' in columns:
            print('\n✓ original_currency column exists!')
            return True
        else:
            print('\n✗ original_currency column is missing!')
            return False

if __name__ == '__main__':
    check_original_currency_column()