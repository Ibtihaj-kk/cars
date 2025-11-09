from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from decimal import Decimal
import random
from django.utils import timezone
from datetime import timedelta

from users.models import User, UserProfile, UserRole
from vehicles.models import (
    FuelType, TransmissionType, Brand, VehicleModel, 
    VehicleCategory, VehicleSpecification
)
from listings.models import (
    VehicleListing, ListingStatus
)


class Command(BaseCommand):
    help = 'Create test data for Cars Portal application'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=10,
            help='Number of users to create',
        )
        parser.add_argument(
            '--listings',
            type=int,
            default=20,
            help='Number of listings to create',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting test data creation...'))
        
        # Create basic users
        users = self.create_users()
        self.stdout.write(f'Created {len(users)} users')
        
        # Create vehicle master data
        vehicle_data = self.create_vehicle_master_data()
        self.stdout.write('Created vehicle master data')
        
        # Create vehicle specifications
        specifications = self.create_specifications(vehicle_data)
        self.stdout.write(f'Created {len(specifications)} specifications')
        
        # Create listings
        listings = self.create_listings(users, specifications, options['listings'])
        self.stdout.write(f'Created {len(listings)} listings')
        
        self.stdout.write(self.style.SUCCESS('Test data creation completed!'))
        self.stdout.write('\nTest Accounts:')
        self.stdout.write('Admin: admin@carsportal.com / admin123')
        self.stdout.write('Seller: seller@example.com / seller123')
        self.stdout.write('Client: client@example.com / client123')

    def create_users(self):
        """Create test users."""
        users_data = [
            {
                'email': 'admin@carsportal.com',
                'password': 'admin123',
                'first_name': 'Admin',
                'last_name': 'User',
                'role': UserRole.ADMIN,
                'is_superuser': True,
                'is_staff': True,
                'is_verified': True
            },
            {
                'email': 'seller@example.com',
                'password': 'seller123',
                'first_name': 'Ahmed',
                'last_name': 'Al-Rashid',
                'role': UserRole.SELLER,
                'phone_number': '+971501234567',
                'is_verified': True
            },
            {
                'email': 'client@example.com',
                'password': 'client123',
                'first_name': 'Sarah',
                'last_name': 'Johnson',
                'role': UserRole.CLIENT,
                'phone_number': '+971502345678',
                'is_verified': True
            },
            {
                'email': 'dealer@example.com',
                'password': 'dealer123',
                'first_name': 'Premium',
                'last_name': 'Motors',
                'role': UserRole.SELLER,
                'phone_number': '+971509876543',
                'is_verified': True
            },
            {
                'email': 'buyer@example.com',
                'password': 'buyer123',
                'first_name': 'Khalid',
                'last_name': 'Al-Mansouri',
                'role': UserRole.CLIENT,
                'phone_number': '+971504567890',
                'is_verified': True
            }
        ]
        
        created_users = []
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                email=user_data['email'],
                defaults=user_data
            )
            if created:
                user.set_password(user_data['password'])
                user.save()
                self.stdout.write(f'Created user: {user.email}')
            created_users.append(user)
        
        return created_users

    def create_vehicle_master_data(self):
        """Create vehicle master data."""
        # Fuel Types
        fuel_types_data = [
            {'name': 'Petrol', 'description': 'Gasoline engine'},
            {'name': 'Diesel', 'description': 'Diesel engine'},
            {'name': 'Electric', 'description': 'Electric motor'},
            {'name': 'Hybrid', 'description': 'Hybrid petrol-electric'}
        ]
        
        fuel_types = []
        for data in fuel_types_data:
            fuel_type, created = FuelType.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            fuel_types.append(fuel_type)
        
        # Transmission Types
        transmission_types_data = [
            {'name': 'Automatic', 'description': 'Automatic transmission'},
            {'name': 'Manual', 'description': 'Manual transmission'},
            {'name': 'CVT', 'description': 'Continuously Variable Transmission'}
        ]
        
        transmission_types = []
        for data in transmission_types_data:
            transmission_type, created = TransmissionType.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            transmission_types.append(transmission_type)
        
        # Categories
        categories_data = [
            {'name': 'Sedan', 'description': 'Four-door passenger car'},
            {'name': 'SUV', 'description': 'Sport Utility Vehicle'},
            {'name': 'Hatchback', 'description': 'Compact car with rear door'},
            {'name': 'Coupe', 'description': 'Two-door sports car'}
        ]
        
        categories = []
        for data in categories_data:
            category, created = VehicleCategory.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            categories.append(category)
        
        # Brands
        brands_data = [
            {'name': 'Toyota', 'country_of_origin': 'Japan', 'founded_year': 1937},
            {'name': 'BMW', 'country_of_origin': 'Germany', 'founded_year': 1916},
            {'name': 'Mercedes-Benz', 'country_of_origin': 'Germany', 'founded_year': 1926},
            {'name': 'Honda', 'country_of_origin': 'Japan', 'founded_year': 1948},
            {'name': 'Audi', 'country_of_origin': 'Germany', 'founded_year': 1909}
        ]
        
        brands = []
        for data in brands_data:
            brand, created = Brand.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            brands.append(brand)
        
        # Models
        models_data = [
            {'brand': 'Toyota', 'name': 'Camry'},
            {'brand': 'Toyota', 'name': 'Corolla'},
            {'brand': 'Toyota', 'name': 'RAV4'},
            {'brand': 'BMW', 'name': '3 Series'},
            {'brand': 'BMW', 'name': 'X5'},
            {'brand': 'Mercedes-Benz', 'name': 'C-Class'},
            {'brand': 'Mercedes-Benz', 'name': 'GLC'},
            {'brand': 'Honda', 'name': 'Civic'},
            {'brand': 'Honda', 'name': 'CR-V'},
            {'brand': 'Audi', 'name': 'A4'}
        ]
        
        models = []
        for data in models_data:
            brand = Brand.objects.get(name=data['brand'])
            model, created = VehicleModel.objects.get_or_create(
                brand=brand,
                name=data['name']
            )
            models.append(model)
        
        return {
            'fuel_types': fuel_types,
            'transmission_types': transmission_types,
            'categories': categories,
            'brands': brands,
            'models': models
        }

    def create_specifications(self, vehicle_data):
        """Create vehicle specifications."""
        specifications = []
        years = [2020, 2021, 2022, 2023, 2024]
        
        for model in vehicle_data['models']:
            for year in random.sample(years, random.randint(1, 3)):
                spec_data = {
                    'model': model,
                    'year': year,
                    'category': random.choice(vehicle_data['categories']),
                    'engine_capacity': Decimal(str(round(random.uniform(1.5, 4.0), 1))),
                    'transmission': random.choice(vehicle_data['transmission_types']),
                    'fuel_type': random.choice(vehicle_data['fuel_types']),
                    'horsepower': random.randint(150, 400),
                    'seating_capacity': random.choice([4, 5, 7]),
                    'doors': random.choice([2, 4, 5])
                }
                
                spec, created = VehicleSpecification.objects.get_or_create(
                    model=model,
                    year=year,
                    defaults=spec_data
                )
                specifications.append(spec)
        
        return specifications

    def create_listings(self, users, specifications, count):
        """Create vehicle listings."""
        sellers = [user for user in users if user.role in [UserRole.SELLER, UserRole.ADMIN]]
        cities = ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman']
        colors = ['White', 'Black', 'Silver', 'Blue', 'Red']
        
        listings = []
        for i in range(min(count, len(specifications))):
            spec = specifications[i]
            seller = random.choice(sellers)
            
            # Generate realistic data
            current_year = timezone.now().year
            age = current_year - spec.year
            mileage = max(0, age * random.randint(10000, 20000))
            base_price = random.randint(50000, 300000)
            price = max(base_price * (1 - age * 0.1), base_price * 0.4)
            
            listing_data = {
                'title': f"{spec.model.brand.name} {spec.model.name} {spec.year}",
                'user': seller,
                'description': f"Excellent condition {spec.model.brand.name} {spec.model.name} {spec.year}. Well maintained vehicle.",
                'price': Decimal(str(int(price))),
                'year': spec.year,
                'make': spec.model.brand.name,
                'model': spec.model.name,
                'kilometers': int(mileage),
                'fuel_type': 'gasoline',
                'transmission': 'automatic',
                'color': random.choice(colors),
                'condition': random.choice(['new', 'used']),
                'engine_size': Decimal('2.0'),
                'doors': 4,
                'seats': 5,
                'location_city': random.choice(cities),
                'location_country': 'UAE',
                'status': ListingStatus.PUBLISHED,
                'is_featured': random.choice([True, False]),
            }
            
            listing, created = VehicleListing.objects.get_or_create(
                title=listing_data['title'],
                user=seller,
                defaults=listing_data
            )
            listings.append(listing)
            
            if created:
                self.stdout.write(f'Created listing: {listing.title}')
        
        return listings