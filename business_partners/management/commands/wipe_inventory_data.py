import random
import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from business_partners.models import BusinessPartner
from parts.models import Brand, Category, Inventory, InventoryTransaction, Part


User = get_user_model()


class Command(BaseCommand):
    help = 'Wipe vendor inventory data and optionally seed test parts/inventory'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str)
        parser.add_argument('--user-id', type=int)
        parser.add_argument('--vendor-id', type=int)
        parser.add_argument('--all-vendors-for-user', action='store_true', default=False)
        parser.add_argument('--delete-parts', action='store_true', default=False)
        parser.add_argument('--create-parts', type=int, default=0)
        parser.add_argument('--min-stock', type=int, default=0)
        parser.add_argument('--max-stock', type=int, default=100)
        parser.add_argument('--price-min', type=str, default='10.00')
        parser.add_argument('--price-max', type=str, default='500.00')
        parser.add_argument('--status', type=str, default='published')
        parser.add_argument('--seed', type=int)
        parser.add_argument('--dry-run', action='store_true', default=False)

    def handle(self, *args, **options):
        email = options.get('email')
        user_id = options.get('user_id')
        vendor_id = options.get('vendor_id')
        all_vendors_for_user = bool(options.get('all_vendors_for_user'))
        delete_parts = bool(options.get('delete_parts'))
        create_parts = int(options.get('create_parts') or 0)
        min_stock = int(options.get('min_stock') or 0)
        max_stock = int(options.get('max_stock') or 0)
        status = (options.get('status') or 'published').strip()
        dry_run = bool(options.get('dry_run'))
        seed = options.get('seed')

        try:
            price_min = Decimal(str(options.get('price_min') or '10.00'))
            price_max = Decimal(str(options.get('price_max') or '500.00'))
        except Exception as e:
            raise CommandError(f'Invalid price range: {e}')

        if min_stock < 0:
            min_stock = 0
        if max_stock < min_stock:
            max_stock = min_stock
        if price_min <= 0:
            price_min = Decimal('0.01')
        if price_max < price_min:
            price_max = price_min

        if seed is not None:
            random.seed(int(seed))

        vendors = []
        if vendor_id:
            vendor = BusinessPartner.objects.filter(id=vendor_id).first()
            if not vendor:
                raise CommandError('Vendor not found')
            vendors = [vendor]
        else:
            user = None
            if user_id:
                user = User.objects.filter(id=user_id).first()
            elif email:
                user = User.objects.filter(email=email).first()
            if not user:
                raise CommandError('User not found. Provide --email or --user-id or --vendor-id')

            qs = BusinessPartner.objects.filter(user=user, status='active', roles__role_type='vendor').distinct()
            if not qs.exists():
                raise CommandError('No active vendor business partner found for user')
            vendors = list(qs) if all_vendors_for_user else [qs.first()]

        categories = list(Category.objects.all()[:200])
        if not categories:
            categories = [Category.objects.create(name='Test Category', description='Test Category')]
        brands = list(Brand.objects.all()[:200])
        if not brands:
            brands = [Brand.objects.create(name='Test Brand', description='Test Brand')]

        allowed_statuses = {'draft', 'published', 'archived'}
        if status not in allowed_statuses:
            status = 'published'

        self.stdout.write(self.style.WARNING(f'Target vendors: {len(vendors)}'))
        if dry_run:
            self.stdout.write(self.style.WARNING('Dry-run enabled: no changes will be committed'))

        summary = []
        with transaction.atomic():
            for vendor in vendors:
                parts_qs = Part.objects.filter(vendor=vendor)
                part_ids = list(parts_qs.values_list('id', flat=True))

                tx_qs = InventoryTransaction.objects.filter(inventory__part__vendor=vendor)
                inv_qs = Inventory.objects.filter(part__vendor=vendor)

                tx_count = tx_qs.count()
                inv_count = inv_qs.count()
                part_count = parts_qs.count()

                if not dry_run:
                    tx_qs.delete()
                    inv_qs.delete()
                    if delete_parts:
                        parts_qs.delete()

                created_parts = []
                if create_parts > 0:
                    if dry_run:
                        created_count = create_parts
                    else:
                        to_create = []
                        for i in range(create_parts):
                            part_number = f'TEST-{vendor.id}-{uuid.uuid4().hex[:10]}-{i}'
                            material_description = f'Test Part {part_number}'
                            chosen_price = price_min + (price_max - price_min) * Decimal(str(random.random()))
                            chosen_stock = random.randint(min_stock, max_stock)
                            slug = slugify(f'{vendor.id}-{part_number}-{uuid.uuid4().hex[:8]}')
                            to_create.append(
                                Part(
                                    vendor=vendor,
                                    parts_number=part_number,
                                    material_description=material_description,
                                    base_unit_of_measure='EA',
                                    category=random.choice(categories),
                                    brand=random.choice(brands),
                                    price=chosen_price.quantize(Decimal('0.01')),
                                    quantity=chosen_stock,
                                    status=status,
                                    is_active=True,
                                    sku=part_number,
                                    name=material_description,
                                    description=material_description,
                                    slug=slug,
                                )
                            )
                        created_parts = Part.objects.bulk_create(to_create, batch_size=2000)
                        created_count = len(created_parts)
                else:
                    created_count = 0

                final_parts_qs = Part.objects.filter(vendor=vendor).only('id', 'quantity')
                final_parts = list(final_parts_qs)
                if dry_run:
                    inv_created_count = len(final_parts)
                else:
                    inv_to_create = []
                    for p in final_parts:
                        inv_to_create.append(
                            Inventory(
                                part_id=p.id,
                                stock=int(p.quantity or 0),
                                reorder_level=10,
                            )
                        )
                    Inventory.objects.bulk_create(inv_to_create, batch_size=5000)
                    inv_created_count = len(inv_to_create)

                summary.append(
                    {
                        'vendor_id': vendor.id,
                        'vendor_name': getattr(vendor, 'name', str(vendor.id)),
                        'deleted_transactions': tx_count,
                        'deleted_inventories': inv_count,
                        'deleted_parts': part_count if delete_parts else 0,
                        'created_parts': created_count,
                        'created_inventories': inv_created_count,
                    }
                )

            if dry_run:
                transaction.set_rollback(True)

        for item in summary:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Vendor {item['vendor_id']} ({item['vendor_name']}): "
                    f"tx -{item['deleted_transactions']}, inv -{item['deleted_inventories']}, "
                    f"parts -{item['deleted_parts']}, parts +{item['created_parts']}, inv +{item['created_inventories']}"
                )
            )

