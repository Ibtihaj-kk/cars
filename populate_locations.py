import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yallamotor_project.settings')
django.setup()

from parts.models import SaudiCity, CityArea

def populate_locations():
    print("Starting location population...")

    # Data structure: City Name -> (Region, [Areas])
    cities_data = {
        "Riyadh": ("Central", [
            "Al-Malaz", "Al-Olaya", "Al-Murabba", "King Fahd District", "Al-Sahafa",
            "Al-Nakheel", "Al-Wurud", "Al-Hamra", "Al-Sulaimaniyah", "Al-Qadisiyah"
        ]),
        "Jeddah": ("Western", [
            "Al-Balad", "Al-Hamra", "Al-Rawdah", "Al-Zahra", "Al-Salamah",
            "Al-Marwah", "Al-Sharafiyah", "Al-Baghdadiyah", "Al-Ruwais", "Al-Aziziyah"
        ]),
        "Mecca": ("Western", [
            "Al-Haram", "Al-Aziziyah", "Al-Rusaifah", "Al-Kakiyah", "Al-Hindawiyah",
            "Al-Utaibiyah", "Ajyad", "Al-Ghassalah", "Al-Khadra", "Al-Taneem"
        ]),
        "Medina": ("Western", [
            "Al-Haram", "Al-Anbariyah", "Al-Iskan", "Qurban", "Al-Khalil",
            "Al-Uyun", "Al-Hijrah", "Al-Azhar", "Al-Jubailah", "Al-Rawabeh"
        ]),
        "Dammam": ("Eastern", [
            "Al-Faisaliyah", "Al-Shati", "Al-Mazruiyah", "Al-Adamah", "Al-Jalawiyah",
            "Al-Badiyah", "Al-Manar", "Ash Shulah", "Al-Noor", "Al-Anoud"
        ]),
        "Khobar": ("Eastern", [
            "Al-Aqrabiyah", "Al-Olaya", "Al-Thuqbah", "Al-Bandariyah", "Al-Hizam",
            "Corniche", "Al-Yarmouk", "Al-Khuzama", "Al-Dana", "Al-Jisr"
        ]),
        "Dhahran": ("Eastern", [
            "KFUPM", "Aramco", "Al-Doha", "Al-Khobar Road", "Aviation District",
            "Dhahran Hills", "Al-Murjan", "Sunset Beach", "Golf Course"
        ]),
        "Abha": ("Southern", []),
        "Khamis Mushait": ("Southern", []),
        "Taif": ("Western", []),
        "Jizan": ("Southern", []),
        "Najran": ("Southern", []),
        "Tabuk": ("Northern", []),
        "Hail": ("Northern", []),
        "Al Bahah": ("Southern", []),
        "Arar": ("Northern", []),
        "Sakaka": ("Northern", []),
        "Al Jawf": ("Northern", []),
        "Yanbu": ("Western", []),
        "Rabigh": ("Western", []),
        "Al Qunfudhah": ("Western", []),
        "Bisha": ("Southern", []),
        "Qatif": ("Eastern", []),
        "Hofuf": ("Eastern", []),
        "Al Hasa": ("Eastern", [])
    }

    cities_created = 0
    areas_created = 0

    for city_name, (region, areas) in cities_data.items():
        # Create or get city
        city, created = SaudiCity.objects.get_or_create(
            name=city_name,
            defaults={
                'region': region,
                'is_active': True
            }
        )
        
        if created:
            cities_created += 1
            print(f"Created city: {city_name}")
        else:
            # Update region if needed
            if city.region != region:
                city.region = region
                city.save()
                print(f"Updated region for: {city_name}")

        # Create areas
        for area_name in areas:
            area, area_created = CityArea.objects.get_or_create(
                city=city,
                name=area_name,
                defaults={
                    'is_active': True
                }
            )
            if area_created:
                areas_created += 1
                # print(f"  Created area: {area_name}")

    print(f"\nPopulation complete!")
    print(f"Total Cities Created: {cities_created}")
    print(f"Total Areas Created: {areas_created}")
    print(f"Total Cities in DB: {SaudiCity.objects.count()}")
    print(f"Total Areas in DB: {CityArea.objects.count()}")

if __name__ == '__main__':
    populate_locations()
