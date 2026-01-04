#!/usr/bin/env python
"""
Script to create required currencies for the multi-currency system
"""
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yallamotor_project.settings')
django.setup()

from core.models import Currency

def create_currencies():
    """Create all required currencies"""
    
    # Create base USD currency
    usd, created = Currency.objects.get_or_create(
        code='USD',
        defaults={
            'name': 'US Dollar',
            'symbol': '$',
            'symbol_position': 'left',
            'decimal_places': 2,
            'thousands_separator': ',',
            'decimal_separator': '.',
            'is_active': True,
            'is_base': True
        }
    )
    print(f'USD: {"Created" if created else "Exists"}')

    # Create the 6 target currencies
    currencies_to_create = [
        ('AED', 'UAE Dirham', 'د.إ', 'right'),
        ('SAR', 'Saudi Riyal', '﷼', 'right'),
        ('QAR', 'Qatari Riyal', '﷼', 'right'),
        ('OMR', 'Omani Rial', 'ر.ع.', 'right'),
        ('BHD', 'Bahraini Dinar', '.د.ب', 'right'),
        ('PKR', 'Pakistani Rupee', '₨', 'left')
    ]

    for code, name, symbol, position in currencies_to_create:
        currency, created = Currency.objects.get_or_create(
            code=code,
            defaults={
                'name': name,
                'symbol': symbol,
                'symbol_position': position,
                'decimal_places': 2,
                'thousands_separator': ',',
                'decimal_separator': '.',
                'is_active': True,
                'is_base': False
            }
        )
        print(f'{code}: {"Created" if created else "Exists"}')

    print('\nAll currencies created successfully!')

if __name__ == '__main__':
    create_currencies()