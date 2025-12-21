"""
Management command to setup initial exchange rates for Middle East currencies
"""
from django.core.management.base import BaseCommand
from core.models import Currency, ExchangeRate
from decimal import Decimal
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Setup initial exchange rates for Middle East currencies'

    def handle(self, *args, **options):
        # Get USD as base currency
        try:
            usd = Currency.objects.get(code='USD', is_base=True)
        except Currency.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('USD base currency not found. Please load currencies first.')
            )
            return
        
        # Current approximate rates (as of December 2024)
        # Source: https://www.xe.com (rates are approximate and should be updated via API in production)
        rates = {
            'SAR': Decimal('3.75'),    # Saudi Riyal (pegged to USD)
            'AED': Decimal('3.67'),    # UAE Dirham (pegged to USD)
            'QAR': Decimal('3.64'),    # Qatari Riyal (pegged to USD)
            'KWD': Decimal('0.307'),   # Kuwaiti Dinar
            'OMR': Decimal('0.385'),   # Omani Rial (pegged to USD)
            'BHD': Decimal('0.376'),   # Bahraini Dinar (pegged to USD)
            'EGP': Decimal('48.85'),   # Egyptian Pound (fluctuates)
            'JOD': Decimal('0.709'),   # Jordanian Dinar (pegged to USD)
        }
        
        created_count = 0
        updated_count = 0
        
        for code, rate in rates.items():
            try:
                currency = Currency.objects.get(code=code)
                
                # Check if rate already exists
                existing = ExchangeRate.objects.filter(
                    base_currency=usd,
                    target_currency=currency,
                    is_active=True,
                    valid_to__isnull=True
                ).first()
                
                if existing:
                    self.stdout.write(
                        self.style.WARNING(f'Rate already exists: 1 USD = {existing.rate} {code}, skipping')
                    )
                    continue
                
                # Create new exchange rate
                ExchangeRate.objects.create(
                    base_currency=usd,
                    target_currency=currency,
                    rate=rate,
                    is_active=True,
                    source='manual'
                )
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created rate: 1 USD = {rate} {code}')
                )
                
            except Currency.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'✗ Currency {code} not found, skipping')
                )
        
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} exchange rates')
        )
        
        if created_count > 0:
            self.stdout.write('')
            self.stdout.write('Next steps:')
            self.stdout.write('  1. Update Part model to use multi-currency')
            self.stdout.write('  2. Add CurrencyMiddleware to settings.py')
            self.stdout.write('  3. Update templates to display prices in user currency')
            self.stdout.write('  4. Setup automatic exchange rate updates (Celery task)')
