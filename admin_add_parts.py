import os
import django
import random
import sys
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yallamotor_project.settings')
django.setup()

from parts.models import Part, Category, Brand, Inventory
from django.core.files import File
from django.utils.text import slugify
from django.utils import timezone

def print_header(msg):
    print("\n" + "="*60)
    print(f" {msg}")
    print("="*60)

def create_auto_parts():
    print_header("STARTING AUTO PARTS POPULATION")

    # 1. Create Categories
    categories_data = [
        {"name": "Engine Components", "description": "Core engine parts including pistons, valves, and camshafts."},
        {"name": "Braking System", "description": "Brake pads, rotors, calipers, and hydraulic components."},
        {"name": "Suspension & Steering", "description": "Shocks, struts, control arms, and steering racks."},
        {"name": "Electrical & Lighting", "description": "Batteries, alternators, starters, and light assemblies."},
        {"name": "Filters & Fluids", "description": "Oil filters, air filters, and automotive fluids."},
        {"name": "Transmission", "description": "Gearbox components, clutches, and drive shafts."},
        {"name": "Exhaust System", "description": "Mufflers, catalytic converters, and exhaust manifolds."},
        {"name": "Cooling System", "description": "Radiators, water pumps, and thermostats."},
    ]

    print("Creating Categories...")
    categories = {}
    for cat_data in categories_data:
        category, created = Category.objects.get_or_create(
            name=cat_data["name"],
            defaults={"description": cat_data["description"]}
        )
        categories[cat_data["name"]] = category
        status = "Created" if created else "Exists"
        print(f"  - {cat_data['name']} ({status})")

    # 2. Create Brands
    brands_data = [
        {"name": "Bosch", "website": "https://www.bosch-automotive.com"},
        {"name": "Denso", "website": "https://www.denso.com"},
        {"name": "ACDelco", "website": "https://www.acdelco.com"},
        {"name": "Brembo", "website": "https://www.brembo.com"},
        {"name": "Monroe", "website": "https://www.monroe.com"},
        {"name": "Mann-Filter", "website": "https://www.mann-hummel.com"},
        {"name": "NGK", "website": "https://www.ngksparkplugs.com"},
        {"name": "Valeo", "website": "https://www.valeo.com"},
    ]

    print("\nCreating Brands...")
    brands = {}
    for brand_data in brands_data:
        brand, created = Brand.objects.get_or_create(
            name=brand_data["name"],
            defaults={"website": brand_data["website"], "is_active": True}
        )
        brands[brand_data["name"]] = brand
        status = "Created" if created else "Exists"
        print(f"  - {brand_data['name']} ({status})")

    # 3. Define Parts Data with Real Images and Stock Status
    # Stock Status Logic:
    # - In Stock: quantity > 10
    # - Low Stock: 1 <= quantity <= 10
    # - Out of Stock: quantity = 0

    parts_data = [
        # Engine Components
        {
            "name": "High Performance Spark Plug",
            "parts_number": "SP-NGK-001",
            "category": "Engine Components",
            "brand": "NGK",
            "price": "15.50",
            "material_description": "Iridium IX Spark Plug for improved throttle response.",
            "image_url": "https://images.unsplash.com/photo-1635784063228-c3c35247f3f2?q=80&w=1000&auto=format&fit=crop",
            "stock_status": "In Stock",
            "weight": "0.150",
            "dimensions": "10x2x2 cm"
        },
        {
            "name": "TSI Engine Block Assembly",
            "parts_number": "ENG-VW-1400",
            "category": "Engine Components",
            "brand": "Bosch", # Using Bosch as generic OEM supplier here
            "price": "2500.00",
            "material_description": "Complete 1.4L TSI Engine Block assembly, ready for installation.",
            "image_url": "https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?q=80&w=1000&auto=format&fit=crop",
            "stock_status": "Low Stock",
            "weight": "120.000",
            "dimensions": "60x50x50 cm"
        },
        
        # Braking System
        {
            "name": "Ventilated Disc Brake Rotor",
            "parts_number": "BRK-BRE-550",
            "category": "Braking System",
            "brand": "Brembo",
            "price": "120.00",
            "material_description": "High-carbon ventilated disc for superior heat dissipation.",
            "image_url": "https://images.unsplash.com/photo-1489824904134-891ab64532f1?q=80&w=1000&auto=format&fit=crop",
            "stock_status": "In Stock",
            "weight": "8.500",
            "dimensions": "30x30x5 cm"
        },
        {
            "name": "Ceramic Brake Pads (Front Set)",
            "parts_number": "PAD-ACD-202",
            "category": "Braking System",
            "brand": "ACDelco",
            "price": "45.99",
            "material_description": "Ceramic brake pads for quiet braking and low dust.",
            "image_url": "https://images.unsplash.com/photo-1600705722908-bab1e61c0bfe?q=80&w=1000&auto=format&fit=crop",
            "stock_status": "Out of Stock",
            "weight": "2.100",
            "dimensions": "15x10x8 cm"
        },

        # Suspension
        {
            "name": "MacPherson Strut Assembly",
            "parts_number": "SUS-MON-880",
            "category": "Suspension & Steering",
            "brand": "Monroe",
            "price": "185.50",
            "material_description": "Complete strut assembly for smooth ride and handling.",
            "image_url": "https://images.unsplash.com/photo-1487754180451-c456f719a1fc?q=80&w=1000&auto=format&fit=crop",
            "stock_status": "In Stock",
            "weight": "12.500",
            "dimensions": "60x15x15 cm"
        },

        # Electrical
        {
            "name": "12V Automotive Alternator",
            "parts_number": "ELC-VAL-900",
            "category": "Electrical & Lighting",
            "brand": "Valeo",
            "price": "320.00",
            "material_description": "High-output alternator 120A for modern vehicle electronics.",
            "image_url": "https://images.unsplash.com/photo-1619642751034-765dfdf7c58e?q=80&w=1000&auto=format&fit=crop",
            "stock_status": "Low Stock",
            "weight": "5.800",
            "dimensions": "20x18x18 cm"
        },

        # Filters
        {
            "name": "Premium Oil Filter",
            "parts_number": "FIL-MAN-777",
            "category": "Filters & Fluids",
            "brand": "Mann-Filter",
            "price": "12.99",
            "material_description": "High-efficiency oil filter for extended service intervals.",
            "image_url": "https://images.unsplash.com/photo-1517524008697-546b79c2e8dd?q=80&w=1000&auto=format&fit=crop",
            "stock_status": "In Stock",
            "weight": "0.400",
            "dimensions": "10x8x8 cm"
        },
        
        # Cooling
        {
            "name": "Aluminum Radiator",
            "parts_number": "RAD-DEN-404",
            "category": "Cooling System",
            "brand": "Denso",
            "price": "145.00",
            "material_description": "Lightweight aluminum radiator for optimal cooling efficiency.",
            "image_url": "https://images.unsplash.com/photo-1503376763036-066120622c74?q=80&w=1000&auto=format&fit=crop",
            "stock_status": "In Stock",
            "weight": "4.500",
            "dimensions": "70x40x5 cm"
        }
    ]

    print("\nCreating Parts...")
    for item in parts_data:
        # Determine quantity based on stock status
        if item["stock_status"] == "Out of Stock":
            qty = 0
        elif item["stock_status"] == "Low Stock":
            qty = random.randint(1, 10)
        else: # In Stock
            qty = random.randint(15, 100)

        # Get or Create Part
        part, created = Part.objects.get_or_create(
            parts_number=item["parts_number"],
            defaults={
                "material_description": item["material_description"],
                "price": Decimal(item["price"]),
                "quantity": qty,
                "category": categories[item["category"]],
                "brand": brands[item["brand"]],
                "image_url": item["image_url"],
                "base_unit_of_measure": "EA",
                "status": "published",
                "is_active": True,
                "gross_weight": Decimal(item["weight"]),
                "net_weight": Decimal(item["weight"]),
                "size_dimensions": item["dimensions"],
                "reorder_point": Decimal("10.000"), # Threshold for Low Stock
                "safety_stock": Decimal("5.000"),
            }
        )
        
        # Update if exists to ensure data freshness (optional, but good for script re-run)
        if not created:
            part.material_description = item["material_description"]
            part.price = Decimal(item["price"])
            part.quantity = qty
            part.image_url = item["image_url"]
            part.status = "published"
            part.save()
            
        # Create or Update Inventory
        inventory, inv_created = Inventory.objects.get_or_create(
            part=part,
            defaults={
                "stock": qty,
                "reorder_level": 10,
                "max_stock_level": 1000,
                "last_restock_date": timezone.now() if qty > 0 else None,
                "supplier_info": f"Supplier for {item['brand']}"
            }
        )
        
        if not inv_created:
            inventory.stock = qty
            if qty > 0 and inventory.stock == 0:
                inventory.last_restock_date = timezone.now()
            inventory.save()
            
        status_icon = "🔴" if qty == 0 else ("🟡" if qty <= 10 else "🟢")
        print(f"  - {item['name']} ({item['parts_number']})")
        print(f"    Status: {item['stock_status']} {status_icon} (Qty: {qty})")
        print(f"    Price: ${item['price']}")
        print(f"    Image: {item['image_url']}")
        print("")

    print_header("PARTS POPULATION COMPLETED SUCCESSFULLY")
    print("You can now view these parts in the admin panel or frontend.")

if __name__ == "__main__":
    create_auto_parts()
