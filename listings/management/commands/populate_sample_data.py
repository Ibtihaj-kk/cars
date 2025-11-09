from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from listings.models import VehicleListing, ListingStatus
from decimal import Decimal
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate database with sample vehicle listings'

    def handle(self, *args, **options):
        # Create sample users if they don't exist
        sample_users = []
        for i in range(3):
            email = f'seller{i+1}@carsportal.com'
            if not User.objects.filter(email=email).exists():
                user = User.objects.create_user(
                    email=email,
                    password='password123',
                    first_name=f'Seller{i+1}',
                    last_name='User',
                    role='seller',
                    is_verified=True
                )
                sample_users.append(user)
                self.stdout.write(f'Created user: {email}')
            else:
                sample_users.append(User.objects.get(email=email))

        # Sample vehicle data
        vehicles = [
            {
                'title': '2020 Toyota Camry - Excellent Condition',
                'year': 2020,
                'make': 'Toyota',
                'model': 'Camry',
                'price': Decimal('25000.00'),
                'kilometers': 45000,
                'fuel_type': 'gasoline',
                'transmission': 'automatic',
                'condition': 'excellent',
                'color': 'Silver',
                'doors': 4,
                'seats': 5,
                'engine_size': Decimal('2.5'),
                'description': 'Well-maintained Toyota Camry with full service history. Perfect for daily commuting.',
                'location_city': 'Dubai',
                'location_state': 'Dubai',
                'location_country': 'UAE'
            },
            {
                'title': '2019 BMW X5 - Luxury SUV',
                'year': 2019,
                'make': 'BMW',
                'model': 'X5',
                'price': Decimal('55000.00'),
                'kilometers': 32000,
                'fuel_type': 'gasoline',
                'transmission': 'automatic',
                'condition': 'excellent',
                'color': 'Black',
                'doors': 5,
                'seats': 7,
                'engine_size': Decimal('3.0'),
                'description': 'Premium BMW X5 with all luxury features. Perfect family SUV.',
                'location_city': 'Abu Dhabi',
                'location_state': 'Abu Dhabi',
                'location_country': 'UAE'
            },
            {
                'title': '2021 Honda Civic - Low Mileage',
                'year': 2021,
                'make': 'Honda',
                'model': 'Civic',
                'price': Decimal('22000.00'),
                'kilometers': 15000,
                'fuel_type': 'gasoline',
                'transmission': 'manual',
                'condition': 'excellent',
                'color': 'White',
                'doors': 4,
                'seats': 5,
                'engine_size': Decimal('1.5'),
                'description': 'Nearly new Honda Civic with very low mileage. Great fuel economy.',
                'location_city': 'Sharjah',
                'location_state': 'Sharjah',
                'location_country': 'UAE'
            },
            {
                'title': '2018 Mercedes C-Class - Premium Sedan',
                'year': 2018,
                'make': 'Mercedes-Benz',
                'model': 'C-Class',
                'price': Decimal('35000.00'),
                'kilometers': 55000,
                'fuel_type': 'gasoline',
                'transmission': 'automatic',
                'condition': 'good',
                'color': 'Blue',
                'doors': 4,
                'seats': 5,
                'engine_size': Decimal('2.0'),
                'description': 'Elegant Mercedes C-Class with premium interior and advanced features.',
                'location_city': 'Dubai',
                'location_state': 'Dubai',
                'location_country': 'UAE'
            },
            {
                'title': '2022 Nissan Patrol - 4WD SUV',
                'year': 2022,
                'make': 'Nissan',
                'model': 'Patrol',
                'price': Decimal('65000.00'),
                'kilometers': 8000,
                'fuel_type': 'gasoline',
                'transmission': 'automatic',
                'condition': 'excellent',
                'color': 'Red',
                'doors': 5,
                'seats': 8,
                'engine_size': Decimal('5.6'),
                'description': 'Powerful Nissan Patrol perfect for desert adventures and family trips.',
                'location_city': 'Dubai',
                'location_state': 'Dubai',
                'location_country': 'UAE'
            }
        ]

        # Create sample listings
        created_count = 0
        for i, vehicle_data in enumerate(vehicles):
            user = sample_users[i % len(sample_users)]
            
            # Check if listing already exists
            if not VehicleListing.objects.filter(title=vehicle_data['title']).exists():
                listing = VehicleListing.objects.create(
                user=user,
                status=ListingStatus.PUBLISHED,
                **vehicle_data
            )
                created_count += 1
                self.stdout.write(f'Created listing: {listing.title}')

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} sample listings')
        )