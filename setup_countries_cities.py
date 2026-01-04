#!/usr/bin/env python
"""
Script to populate countries and cities for the 6 target countries
"""
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yallamotor_project.settings')
django.setup()

from parts.models import Country, City

def setup_countries_and_cities():
    """Create countries and their major cities"""
    
    # Define countries with their codes and names
    countries_data = [
        {'code': 'AE', 'name': 'United Arab Emirates', 'name_ar': 'الإمارات العربية المتحدة'},
        {'code': 'SA', 'name': 'Saudi Arabia', 'name_ar': 'المملكة العربية السعودية'},
        {'code': 'QA', 'name': 'Qatar', 'name_ar': 'قطر'},
        {'code': 'OM', 'name': 'Oman', 'name_ar': 'سلطنة عمان'},
        {'code': 'BH', 'name': 'Bahrain', 'name_ar': 'مملكة البحرين'},
        {'code': 'PK', 'name': 'Pakistan', 'name_ar': 'باكستان'}
    ]
    
    # Define cities for each country
    cities_data = {
        'AE': [
            'Abu Dhabi', 'Dubai', 'Sharjah', 'Ajman', 'Umm Al Quwain',
            'Ras Al Khaimah', 'Fujairah', 'Al Ain'
        ],
        'SA': [
            'Riyadh', 'Jeddah', 'Mecca', 'Medina', 'Dammam',
            'Khobar', 'Dhahran', 'Taif', 'Tabuk', 'Abha'
        ],
        'QA': [
            'Doha', 'Al Rayyan', 'Al Wakrah', 'Al Khor', 'Umm Salal',
            'Al Daayen', 'Mesaieed'
        ],
        'OM': [
            'Muscat', 'Salalah', 'Sohar', 'Nizwa', 'Sur',
            'Ibri', 'Barka', 'Rustaq'
        ],
        'BH': [
            'Manama', 'Muharraq', 'Riffa', 'Hamad Town', 'Aali',
            'Isa Town', 'Sitra', 'Budaiya'
        ],
        'PK': [
            'Karachi', 'Lahore', 'Islamabad', 'Rawalpindi', 'Faisalabad',
            'Multan', 'Peshawar', 'Quetta', 'Gujranwala', 'Sialkot'
        ]
    }
    
    print("Setting up countries and cities...")
    
    # Create countries
    for country_data in countries_data:
        country, created = Country.objects.get_or_create(
            code=country_data['code'],
            defaults={
                'name': country_data['name'],
                'name_ar': country_data.get('name_ar', ''),
                'is_active': True
            }
        )
        if created:
            print(f"✓ Created country: {country.name}")
        else:
            print(f"✓ Country already exists: {country.name}")
        
        # Create cities for this country
        country_cities = cities_data.get(country_data['code'], [])
        for city_name in country_cities:
            city, created = City.objects.get_or_create(
                country=country,
                name=city_name,
                defaults={'is_active': True}
            )
            if created:
                print(f"  ✓ Created city: {city_name}, {country.name}")
    
    print("✓ Countries and cities setup completed!")

if __name__ == '__main__':
    setup_countries_and_cities()