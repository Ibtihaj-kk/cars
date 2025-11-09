from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from listings.models import VehicleListing, Dealer, ConditionType, ListingStatus
from vehicles.models import Brand, VehicleModel, FuelType, TransmissionType, VehicleCategory
from decimal import Decimal
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate database with dummy car listings data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=25,
            help='Number of car listings to create (default: 25)',
        )

    def handle(self, *args, **options):
        count = options['count']
        
        self.stdout.write(self.style.SUCCESS(f'Creating {count} dummy car listings...'))
        
        # Create or get required data
        self.create_base_data()
        
        # Create dummy listings
        self.create_dummy_listings(count)
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {count} car listings!')
        )

    def create_base_data(self):
        """Create base data like brands, models, fuel types, etc."""
        
        # Create fuel types
        fuel_types_data = [
            'Petrol', 'Diesel', 'Electric', 'Hybrid', 'Plug-in Hybrid'
        ]
        for fuel_name in fuel_types_data:
            FuelType.objects.get_or_create(name=fuel_name)
        
        # Create transmission types
        transmission_data = [
            'Automatic', 'Manual', 'CVT', 'Semi-Automatic'
        ]
        for trans_name in transmission_data:
            TransmissionType.objects.get_or_create(name=trans_name)
        
        # Create vehicle categories
        categories_data = [
            'Sedan', 'SUV', 'Hatchback', 'Coupe', 'Convertible', 
            'Truck', 'Van', 'Wagon', 'Crossover', 'Luxury'
        ]
        for cat_name in categories_data:
            VehicleCategory.objects.get_or_create(name=cat_name)
        
        # Create brands and models
        brands_models = {
            'BMW': ['X5', 'X3', '3 Series', '5 Series', '7 Series', 'X7', 'i4', 'iX'],
            'Mercedes-Benz': ['C-Class', 'E-Class', 'S-Class', 'GLE', 'GLC', 'A-Class', 'CLA'],
            'Audi': ['A4', 'A6', 'Q5', 'Q7', 'Q3', 'A3', 'e-tron GT'],
            'Toyota': ['Camry', 'Corolla', 'RAV4', 'Highlander', 'Prius', 'Land Cruiser'],
            'Honda': ['Civic', 'Accord', 'CR-V', 'Pilot', 'HR-V', 'Insight'],
            'Ford': ['F-150', 'Mustang', 'Explorer', 'Escape', 'Edge', 'Bronco'],
            'Chevrolet': ['Silverado', 'Equinox', 'Malibu', 'Tahoe', 'Camaro', 'Corvette'],
            'Nissan': ['Altima', 'Sentra', 'Rogue', 'Pathfinder', 'Murano', 'Leaf'],
            'Hyundai': ['Elantra', 'Sonata', 'Tucson', 'Santa Fe', 'Genesis', 'Kona'],
            'Kia': ['Optima', 'Forte', 'Sorento', 'Sportage', 'Stinger', 'EV6'],
            'Lexus': ['ES', 'RX', 'NX', 'GX', 'LS', 'LC'],
            'Porsche': ['911', 'Cayenne', 'Macan', 'Panamera', 'Taycan'],
        }
        
        for brand_name, models in brands_models.items():
            brand, _ = Brand.objects.get_or_create(name=brand_name)
            for model_name in models:
                VehicleModel.objects.get_or_create(
                    brand=brand, 
                    name=model_name
                )
        
        # Create dealers
        dealers_data = [
            {
                'name': 'Premium Auto Dubai',
                'address': 'Sheikh Zayed Road, Dubai, UAE',
                'phone': '+971-4-123-4567',
                'email': 'info@premiumautodubai.com',
                'city': 'Dubai',
                'rating': Decimal('4.8'),
                'review_count': 245
            },
            {
                'name': 'Elite Motors Abu Dhabi',
                'address': 'Corniche Road, Abu Dhabi, UAE',
                'phone': '+971-2-987-6543',
                'email': 'sales@elitemotors.ae',
                'city': 'Abu Dhabi',
                'rating': Decimal('4.6'),
                'review_count': 189
            },
            {
                'name': 'Luxury Cars Sharjah',
                'address': 'Al Wahda Street, Sharjah, UAE',
                'phone': '+971-6-555-0123',
                'email': 'contact@luxurycars.ae',
                'city': 'Sharjah',
                'rating': Decimal('4.7'),
                'review_count': 156
            }
        ]
        
        for dealer_data in dealers_data:
            Dealer.objects.get_or_create(
                name=dealer_data['name'],
                defaults=dealer_data
            )
        
        # Create a default user if none exists
        if not User.objects.exists():
            user = User.objects.create_user(
                email='admin@carsportal.com',
                password='admin123',
                is_staff=True,
                is_superuser=True
            )
            self.stdout.write(self.style.SUCCESS("Created admin user: admin@carsportal.com/admin123"))

    def create_dummy_listings(self, count):
        """Create dummy car listings with realistic data and live image URLs."""
        
        # Live HTTPS image URLs from reliable sources
        car_images = [
            'https://images.unsplash.com/photo-1549924231-f129b911e442?w=800&h=600&fit=crop',
            'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=800&h=600&fit=crop',
            'https://images.unsplash.com/photo-1563720223185-11003d516935?w=800&h=600&fit=crop',
            'https://images.unsplash.com/photo-1544636331-e26879cd4d9b?w=800&h=600&fit=crop',
            'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&h=600&fit=crop',
            'https://images.unsplash.com/photo-1502877338535-766e1452684a?w=800&h=600&fit=crop',
            'https://images.unsplash.com/photo-1494976688153-ca3ce29d8df4?w=800&h=600&fit=crop',
            'https://images.unsplash.com/photo-1542362567-b07e54358753?w=800&h=600&fit=crop',
            'https://images.unsplash.com/photo-1555215695-3004980ad54e?w=800&h=600&fit=crop',
            'https://images.unsplash.com/photo-1583121274602-3e2820c69888?w=800&h=600&fit=crop',
            'https://images.unsplash.com/photo-1580273916550-e323be2ae537?w=800&h=600&fit=crop',
            'https://images.unsplash.com/photo-1606664515524-ed2f786a0bd6?w=800&h=600&fit=crop',
            'https://images.unsplash.com/photo-1617814076367-b759c7d7e738?w=800&h=600&fit=crop',
            'https://images.unsplash.com/photo-1618843479313-40f8afb4b4d8?w=800&h=600&fit=crop',
            'https://images.unsplash.com/photo-1619767886558-efdc259cde1a?w=800&h=600&fit=crop',
            'https://images.unsplash.com/photo-1621135802920-133df287f89c?w=800&h=600&fit=crop',
            'https://images.unsplash.com/photo-1627603992476-9e9cd4c8f8c8?w=800&h=600&fit=crop',
            'https://images.unsplash.com/photo-1632294647330-2e0c0b4e7b1a?w=800&h=600&fit=crop',
            'https://images.unsplash.com/photo-1637149962419-0d902ac2e5c4?w=800&h=600&fit=crop',
            'https://images.unsplash.com/photo-1641484535921-0e4b5b6b8b1a?w=800&h=600&fit=crop',
        ]
        
        # Get required objects
        brands = list(Brand.objects.all())
        fuel_types = list(FuelType.objects.all())
        transmissions = list(TransmissionType.objects.all())
        categories = list(VehicleCategory.objects.all())
        dealers = list(Dealer.objects.all())
        users = list(User.objects.all())
        
        cities = ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'Fujairah', 'Ras Al Khaimah', 'Umm Al Quwain']
        colors = ['White', 'Black', 'Silver', 'Gray', 'Blue', 'Red', 'Green', 'Brown', 'Gold', 'Beige']
        conditions = [ConditionType.NEW, ConditionType.USED, ConditionType.CERTIFIED_PRE_OWNED]
        drivetrains = ['fwd', 'rwd', 'awd', '4wd']
        
        for i in range(count):
            # Select random brand and one of its models
            brand = random.choice(brands)
            models = list(brand.models.all())
            if not models:
                continue
            
            model = random.choice(models)
            year = random.randint(2018, 2024)
            
            # Generate realistic data based on brand and model
            is_luxury = brand.name in ['BMW', 'Mercedes-Benz', 'Audi', 'Lexus', 'Porsche']
            base_price = random.randint(25000, 150000) if is_luxury else random.randint(15000, 80000)
            
            # Adjust price based on year
            if year >= 2023:
                price = base_price * random.uniform(1.1, 1.3)
            elif year >= 2021:
                price = base_price * random.uniform(0.9, 1.1)
            else:
                price = base_price * random.uniform(0.6, 0.9)
            
            kilometers = random.randint(0, 150000) if year < 2023 else random.randint(0, 30000)
            
            # Create listing
            listing_data = {
                'title': f'{year} {brand.name} {model.name}',
                'user': random.choice(users),
                'dealer': random.choice(dealers) if random.choice([True, False]) else None,
                'description': f'Excellent condition {year} {brand.name} {model.name}. Well maintained with full service history. Perfect for daily driving or weekend adventures.',
                'price': Decimal(str(round(price, 2))),
                'year': year,
                'make': brand,
                'model': model,
                'trim': random.choice(['Base', 'Premium', 'Sport', 'Luxury', 'Limited']) if random.choice([True, False]) else None,
                'kilometers': kilometers,
                'location_city': random.choice(cities),
                'fuel_type': random.choice(fuel_types),
                'condition': random.choice(conditions),
                'transmission': random.choice(transmissions),
                'exterior_color': random.choice(colors),
                'interior_color': random.choice(colors),
                'body_type': random.choice(categories),
                'engine_size': Decimal(str(round(random.uniform(1.0, 6.0), 1))),
                'horsepower': random.randint(150, 600) if is_luxury else random.randint(120, 400),
                'drivetrain': random.choice(drivetrains),
                'fuel_economy_city': random.randint(15, 35),
                'fuel_economy_highway': random.randint(20, 45),
                'seating_capacity': random.choice([2, 4, 5, 7, 8]),
                'doors': random.choice([2, 4]),
                'status': ListingStatus.PUBLISHED,
                'is_luxury': is_luxury,
                'is_certified': random.choice([True, False]) if year >= 2020 else False,
                'safety_rating': Decimal(str(round(random.uniform(4.0, 5.0), 1))),
            }
            
            # Generate slug
            slug_base = f"{year}-{brand.name.lower()}-{model.name.lower()}"
            slug = slugify(slug_base)
            
            # Ensure unique slug
            counter = 1
            original_slug = slug
            while VehicleListing.objects.filter(slug=slug).exists():
                slug = f"{original_slug}-{counter}"
                counter += 1
            
            listing_data['slug'] = slug
            
            try:
                listing = VehicleListing.objects.create(**listing_data)
                self.stdout.write(f'Created: {listing.title} (ID: {listing.id})')
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating listing {i+1}: {str(e)}')
                )