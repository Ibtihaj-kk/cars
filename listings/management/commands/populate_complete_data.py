from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from listings.models import VehicleListing, ListingImage, Dealer
from vehicles.models import Brand, VehicleModel, FuelType, TransmissionType, VehicleCategory
from decimal import Decimal
import random
import os
from django.conf import settings
from django.core.files import File
from django.utils.text import slugify

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate database with complete car data including dealers and detailed vehicle listings'

    def handle(self, *args, **options):
        self.stdout.write('Starting to populate complete car data...')
        
        # Create or get superuser
        user, created = User.objects.get_or_create(
            email='admin@carsportal.com',
            defaults={
                'is_staff': True,
                'is_superuser': True,
                'is_active': True
            }
        )
        if created:
            user.set_password('admin123')
            user.save()
            self.stdout.write('Created admin user')

        # Create fuel types
        fuel_types_data = [
            {'name': 'Gasoline', 'slug': 'gasoline'},
            {'name': 'Diesel', 'slug': 'diesel'},
            {'name': 'Electric', 'slug': 'electric'},
            {'name': 'Hybrid', 'slug': 'hybrid'},
            {'name': 'Plug-in Hybrid', 'slug': 'plug-in-hybrid'},
        ]
        
        for fuel_data in fuel_types_data:
            fuel_type, created = FuelType.objects.get_or_create(
                name=fuel_data['name'],
                defaults={'slug': fuel_data['slug']}
            )
            if created:
                self.stdout.write(f'Created fuel type: {fuel_type.name}')

        # Create transmission types
        transmission_data = [
            {'name': 'Automatic', 'slug': 'automatic'},
            {'name': 'Manual', 'slug': 'manual'},
            {'name': 'CVT', 'slug': 'cvt'},
            {'name': 'Semi-Automatic', 'slug': 'semi-automatic'},
        ]
        
        for trans_data in transmission_data:
            transmission, created = TransmissionType.objects.get_or_create(
                name=trans_data['name'],
                defaults={'slug': trans_data['slug']}
            )
            if created:
                self.stdout.write(f'Created transmission: {transmission.name}')

        # Create vehicle categories
        categories_data = [
            {'name': 'Sedan', 'slug': 'sedan'},
            {'name': 'SUV', 'slug': 'suv'},
            {'name': 'Hatchback', 'slug': 'hatchback'},
            {'name': 'Coupe', 'slug': 'coupe'},
            {'name': 'Convertible', 'slug': 'convertible'},
            {'name': 'Truck', 'slug': 'truck'},
            {'name': 'Wagon', 'slug': 'wagon'},
        ]
        
        for cat_data in categories_data:
            category, created = VehicleCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={'slug': cat_data['slug']}
            )
            if created:
                self.stdout.write(f'Created category: {category.name}')

        # Create brands
        brands_data = [
            {'name': 'Toyota', 'slug': 'toyota'},
            {'name': 'BMW', 'slug': 'bmw'},
            {'name': 'Mercedes-Benz', 'slug': 'mercedes-benz'},
            {'name': 'Audi', 'slug': 'audi'},
            {'name': 'Honda', 'slug': 'honda'},
            {'name': 'Nissan', 'slug': 'nissan'},
            {'name': 'Ford', 'slug': 'ford'},
            {'name': 'Chevrolet', 'slug': 'chevrolet'},
        ]
        
        for brand_data in brands_data:
            brand, created = Brand.objects.get_or_create(
                name=brand_data['name'],
                defaults={'slug': brand_data['slug']}
            )
            if created:
                self.stdout.write(f'Created brand: {brand.name}')

        # Create vehicle models
        models_data = [
            {'brand': 'Toyota', 'name': 'Camry', 'slug': 'camry'},
            {'brand': 'Toyota', 'name': 'Corolla', 'slug': 'corolla'},
            {'brand': 'Toyota', 'name': 'RAV4', 'slug': 'rav4'},
            {'brand': 'BMW', 'name': 'X5', 'slug': 'x5'},
            {'brand': 'BMW', 'name': '3 Series', 'slug': '3-series'},
            {'brand': 'BMW', 'name': 'X3', 'slug': 'x3'},
            {'brand': 'Mercedes-Benz', 'name': 'C-Class', 'slug': 'c-class'},
            {'brand': 'Mercedes-Benz', 'name': 'E-Class', 'slug': 'e-class'},
            {'brand': 'Audi', 'name': 'A4', 'slug': 'a4'},
            {'brand': 'Audi', 'name': 'Q5', 'slug': 'q5'},
            {'brand': 'Honda', 'name': 'Civic', 'slug': 'civic'},
            {'brand': 'Honda', 'name': 'Accord', 'slug': 'accord'},
        ]
        
        for model_data in models_data:
            brand = Brand.objects.get(name=model_data['brand'])
            model, created = VehicleModel.objects.get_or_create(
                brand=brand,
                name=model_data['name'],
                defaults={'slug': model_data['slug']}
            )
            if created:
                self.stdout.write(f'Created model: {brand.name} {model.name}')

        # Create dealers
        dealers_data = [
            {
                'name': 'Premium Auto Dubai',
                'address': 'Sheikh Zayed Road, Dubai, UAE',
                'phone': '+971-4-123-4567',
                'email': 'info@premiumautodubai.com',
                'city': 'Dubai',
                'country': 'UAE',
                'rating': Decimal('4.8'),
                'review_count': 245,
            },
            {
                'name': 'Elite Motors Abu Dhabi',
                'address': 'Corniche Road, Abu Dhabi, UAE',
                'phone': '+971-2-987-6543',
                'email': 'sales@elitemotors.ae',
                'city': 'Abu Dhabi',
                'country': 'UAE',
                'rating': Decimal('4.6'),
                'review_count': 189,
            },
            {
                'name': 'Luxury Cars Sharjah',
                'address': 'Al Wahda Street, Sharjah, UAE',
                'phone': '+971-6-555-0123',
                'email': 'contact@luxurycars.ae',
                'city': 'Sharjah',
                'country': 'UAE',
                'rating': Decimal('4.7'),
                'review_count': 156,
            },
        ]
        
        for dealer_data in dealers_data:
            dealer, created = Dealer.objects.get_or_create(
                name=dealer_data['name'],
                defaults=dealer_data
            )
            if created:
                self.stdout.write(f'Created dealer: {dealer.name}')

        # Create detailed vehicle listings
        listings_data = [
            {
                'title': '2022 Toyota Camry XLE - Premium Sedan',
                'brand': 'Toyota',
                'model': 'Camry',
                'year': 2022,
                'trim': 'XLE Premium',
                'price': Decimal('89500'),
                'original_price': Decimal('95000'),
                'estimated_monthly_payment': Decimal('1250'),
                'kilometers': 15000,
                'mileage': 9320,
                'location': 'Dubai, UAE',
                'stock_number': 'TC2022001',
                'condition': 'used',
                'fuel_type': 'Gasoline',
                'transmission': 'Automatic',
                'body_type': 'Sedan',
                'exterior_color': 'Pearl White',
                'interior_color': 'Black Leather',
                'engine_type': '2.5L 4-Cylinder',
                'engine_size': Decimal('2.5'),
                'horsepower': 203,
                'torque': 184,
                'drivetrain': 'fwd',
                'fuel_economy_city': 28,
                'fuel_economy_highway': 39,
                'acceleration_0_60': Decimal('8.4'),
                'top_speed': 115,
                'towing_capacity': 1000,
                'curb_weight': 3340,
                'safety_rating': Decimal('4.5'),
                'seating_capacity': 5,
                'doors': 4,
                'is_luxury': False,
                'is_certified': True,
                'dealer': 'Premium Auto Dubai',
                'description': 'Immaculate 2022 Toyota Camry XLE in pristine condition. This premium sedan features advanced safety systems, premium interior materials, and excellent fuel economy. Perfect for daily commuting and long drives.',
            },
            {
                'title': '2021 BMW X5 xDrive40i - Luxury SUV',
                'brand': 'BMW',
                'model': 'X5',
                'year': 2021,
                'trim': 'xDrive40i Sports Activity',
                'price': Decimal('245000'),
                'original_price': Decimal('265000'),
                'estimated_monthly_payment': Decimal('3200'),
                'kilometers': 22000,
                'mileage': 13670,
                'location': 'Abu Dhabi, UAE',
                'stock_number': 'BX2021002',
                'condition': 'used',
                'fuel_type': 'Gasoline',
                'transmission': 'Automatic',
                'body_type': 'SUV',
                'exterior_color': 'Alpine White',
                'interior_color': 'Cognac Leather',
                'engine_type': '3.0L Twin-Turbo I6',
                'engine_size': Decimal('3.0'),
                'horsepower': 335,
                'torque': 330,
                'drivetrain': 'awd',
                'fuel_economy_city': 20,
                'fuel_economy_highway': 26,
                'acceleration_0_60': Decimal('5.8'),
                'top_speed': 130,
                'towing_capacity': 7200,
                'curb_weight': 4922,
                'safety_rating': Decimal('4.8'),
                'seating_capacity': 7,
                'doors': 5,
                'is_luxury': True,
                'is_certified': True,
                'dealer': 'Elite Motors Abu Dhabi',
                'description': 'Stunning BMW X5 xDrive40i with premium features and exceptional performance. This luxury SUV combines comfort, technology, and capability in one impressive package.',
            },
            {
                'title': '2020 Mercedes-Benz C-Class C300 - Executive Sedan',
                'brand': 'Mercedes-Benz',
                'model': 'C-Class',
                'year': 2020,
                'trim': 'C300 4MATIC',
                'price': Decimal('165000'),
                'original_price': Decimal('175000'),
                'estimated_monthly_payment': Decimal('2100'),
                'kilometers': 35000,
                'mileage': 21748,
                'location': 'Sharjah, UAE',
                'stock_number': 'MC2020003',
                'condition': 'used',
                'fuel_type': 'Gasoline',
                'transmission': 'Automatic',
                'body_type': 'Sedan',
                'exterior_color': 'Obsidian Black',
                'interior_color': 'Beige Leather',
                'engine_type': '2.0L Turbo 4-Cylinder',
                'engine_size': Decimal('2.0'),
                'horsepower': 255,
                'torque': 273,
                'drivetrain': 'awd',
                'fuel_economy_city': 22,
                'fuel_economy_highway': 31,
                'acceleration_0_60': Decimal('6.0'),
                'top_speed': 130,
                'towing_capacity': 3500,
                'curb_weight': 3814,
                'safety_rating': Decimal('4.7'),
                'seating_capacity': 5,
                'doors': 4,
                'is_luxury': True,
                'is_certified': False,
                'dealer': 'Luxury Cars Sharjah',
                'description': 'Elegant Mercedes-Benz C-Class C300 with sophisticated styling and advanced technology. This executive sedan offers the perfect blend of luxury and performance.',
            },
            {
                'title': '2023 Audi Q5 Premium Plus - Compact Luxury SUV',
                'brand': 'Audi',
                'model': 'Q5',
                'year': 2023,
                'trim': 'Premium Plus',
                'price': Decimal('195000'),
                'original_price': Decimal('205000'),
                'estimated_monthly_payment': Decimal('2650'),
                'kilometers': 8000,
                'mileage': 4971,
                'location': 'Dubai, UAE',
                'stock_number': 'AQ2023004',
                'condition': 'used',
                'fuel_type': 'Gasoline',
                'transmission': 'Automatic',
                'body_type': 'SUV',
                'exterior_color': 'Glacier White',
                'interior_color': 'Black Leather',
                'engine_type': '2.0L TFSI Turbo',
                'engine_size': Decimal('2.0'),
                'horsepower': 261,
                'torque': 273,
                'drivetrain': 'awd',
                'fuel_economy_city': 23,
                'fuel_economy_highway': 28,
                'acceleration_0_60': Decimal('5.9'),
                'top_speed': 130,
                'towing_capacity': 4400,
                'curb_weight': 4045,
                'safety_rating': Decimal('4.6'),
                'seating_capacity': 5,
                'doors': 5,
                'is_luxury': True,
                'is_certified': True,
                'dealer': 'Premium Auto Dubai',
                'description': 'Nearly new Audi Q5 Premium Plus with cutting-edge technology and refined luxury. This compact SUV delivers exceptional driving dynamics and premium comfort.',
            },
            {
                'title': '2019 Honda Civic Sport - Reliable Compact Car',
                'brand': 'Honda',
                'model': 'Civic',
                'year': 2019,
                'trim': 'Sport',
                'price': Decimal('65000'),
                'original_price': Decimal('70000'),
                'estimated_monthly_payment': Decimal('950'),
                'kilometers': 45000,
                'mileage': 27962,
                'location': 'Dubai, UAE',
                'stock_number': 'HC2019005',
                'condition': 'used',
                'fuel_type': 'Gasoline',
                'transmission': 'Manual',
                'body_type': 'Hatchback',
                'exterior_color': 'Rallye Red',
                'interior_color': 'Black Cloth',
                'engine_type': '2.0L 4-Cylinder',
                'engine_size': Decimal('2.0'),
                'horsepower': 158,
                'torque': 138,
                'drivetrain': 'fwd',
                'fuel_economy_city': 25,
                'fuel_economy_highway': 36,
                'acceleration_0_60': Decimal('8.2'),
                'top_speed': 115,
                'towing_capacity': 1000,
                'curb_weight': 2906,
                'safety_rating': Decimal('4.3'),
                'seating_capacity': 5,
                'doors': 5,
                'is_luxury': False,
                'is_certified': False,
                'dealer': 'Premium Auto Dubai',
                'description': 'Sporty Honda Civic Sport with excellent reliability and fuel efficiency. Perfect first car or daily commuter with proven Honda quality and dependability.',
            },
        ]

        for listing_data in listings_data:
            # Get related objects
            brand = Brand.objects.get(name=listing_data['brand'])
            model = VehicleModel.objects.get(brand=brand, name=listing_data['model'])
            fuel_type = FuelType.objects.get(name=listing_data['fuel_type'])
            transmission = TransmissionType.objects.get(name=listing_data['transmission'])
            body_type = VehicleCategory.objects.get(name=listing_data['body_type'])
            dealer = Dealer.objects.get(name=listing_data['dealer'])
            
            # Create listing
            listing, created = VehicleListing.objects.get_or_create(
                title=listing_data['title'],
                defaults={
                    'slug': slugify(listing_data['title']),
                    'user': user,
                    'dealer': dealer,
                    'description': listing_data['description'],
                    'price': listing_data['price'],
                    'original_price': listing_data['original_price'],
                    'estimated_monthly_payment': listing_data['estimated_monthly_payment'],
                    'year': listing_data['year'],
                    'make': brand,
                    'model': model,
                    'trim': listing_data['trim'],
                    'kilometers': listing_data['kilometers'],
                    'mileage': listing_data['mileage'],
                    'location': listing_data['location'],
                    'stock_number': listing_data['stock_number'],
                    'fuel_type': fuel_type,
                    'condition': listing_data['condition'],
                    'transmission': transmission,
                    'is_luxury': listing_data['is_luxury'],
                    'is_certified': listing_data['is_certified'],
                    'exterior_color': listing_data['exterior_color'],
                    'interior_color': listing_data['interior_color'],
                    'body_type': body_type,
                    'engine_type': listing_data['engine_type'],
                    'engine_size': listing_data['engine_size'],
                    'horsepower': listing_data['horsepower'],
                    'torque': listing_data['torque'],
                    'drivetrain': listing_data['drivetrain'],
                    'fuel_economy_city': listing_data['fuel_economy_city'],
                    'fuel_economy_highway': listing_data['fuel_economy_highway'],
                    'acceleration_0_60': listing_data['acceleration_0_60'],
                    'top_speed': listing_data['top_speed'],
                    'towing_capacity': listing_data['towing_capacity'],
                    'curb_weight': listing_data['curb_weight'],
                    'safety_rating': listing_data['safety_rating'],
                    'seating_capacity': listing_data['seating_capacity'],
                    'doors': listing_data['doors'],
                    'status': 'published',
                    'is_featured': True,
                }
            )
            
            if created:
                self.stdout.write(f'Created listing: {listing.title}')
                
                # Add car images based on make and model
                self.add_car_images(listing, brand.name, model.name)

        self.stdout.write(
            self.style.SUCCESS('Successfully populated database with complete car data!')
        )
        self.stdout.write(f'Created {VehicleListing.objects.count()} vehicle listings')
        self.stdout.write(f'Created {Dealer.objects.count()} dealers')
        self.stdout.write(f'Created {Brand.objects.count()} brands')
        self.stdout.write(f'Created {VehicleModel.objects.count()} vehicle models')
    
    def add_car_images(self, listing, brand_name, model_name):
        """Add car images to the listing based on brand and model."""
        # Map car images to specific makes and models
        image_mapping = {
            ('Toyota', 'Camry'): 'toyota_camry_2022.svg',
            ('BMW', 'X5'): 'bmw_x5_2021.svg',
            ('Mercedes-Benz', 'C-Class'): 'mercedes_c_class_2020.svg',
            ('Audi', 'Q5'): 'audi_q5_2023.svg',
            ('Honda', 'Civic'): 'honda_civic_2019.svg',
        }
        
        # Get the appropriate image file
        image_filename = image_mapping.get((brand_name, model_name))
        if not image_filename:
            # Use a default image if no specific mapping exists
            image_filename = 'toyota_camry_2022.svg'
        
        # Path to the image file
        image_path = os.path.join(settings.BASE_DIR, 'media', 'cars', image_filename)
        
        if os.path.exists(image_path):
            try:
                with open(image_path, 'rb') as img_file:
                    # Create ListingImage instance
                    listing_image = ListingImage(
                        listing=listing,
                        is_primary=True,
                        caption=f'{brand_name} {model_name} - Main Image',
                        order=0
                    )
                    listing_image.image.save(
                        image_filename,
                        File(img_file),
                        save=True
                    )
                    self.stdout.write(f'Added image for {listing.title}')
            except Exception as e:
                self.stdout.write(f'Error adding image for {listing.title}: {str(e)}')
        else:
            self.stdout.write(f'Image file not found: {image_path}')