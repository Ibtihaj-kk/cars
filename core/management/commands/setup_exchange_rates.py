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
        currency_defaults = {
            "USD": {"name": "US Dollar", "symbol": "$", "symbol_position": "left", "decimal_places": 2, "is_base": True},
            "SAR": {"name": "Saudi Riyal", "symbol": "﷼", "symbol_position": "right", "decimal_places": 2},
            "AED": {"name": "UAE Dirham", "symbol": "د.إ", "symbol_position": "right", "decimal_places": 2},
            "QAR": {"name": "Qatari Riyal", "symbol": "ر.ق", "symbol_position": "right", "decimal_places": 2},
            "OMR": {"name": "Omani Rial", "symbol": "ر.ع.", "symbol_position": "right", "decimal_places": 3},
            "BHD": {"name": "Bahraini Dinar", "symbol": ".د.ب", "symbol_position": "right", "decimal_places": 3},
            "PKR": {"name": "Pakistani Rupee", "symbol": "₨", "symbol_position": "left", "decimal_places": 2},
        }

        usd, _ = Currency.objects.get_or_create(
            code="USD",
            defaults={
                **currency_defaults["USD"],
                "is_active": True,
                "thousands_separator": ",",
                "decimal_separator": ".",
            },
        )
        if not usd.is_base:
            usd.is_base = True
            usd.save(update_fields=["is_base"])

        # Current approximate rates (as of December 2024)
        # Source: https://www.xe.com (rates are approximate and should be updated via API in production)
        rates = {
            'SAR': Decimal('3.75'),    # Saudi Riyal (pegged to USD)
            'AED': Decimal('3.67'),    # UAE Dirham (pegged to USD)
            'QAR': Decimal('3.64'),    # Qatari Riyal (pegged to USD)
            'OMR': Decimal('0.385'),   # Omani Rial (pegged to USD)
            'BHD': Decimal('0.376'),   # Bahraini Dinar (pegged to USD)
            'PKR': Decimal('280.0'),   # Pakistani Rupee (fluctuates)
        }
        
        created_count = 0
        updated_count = 0
        
        for code, rate in rates.items():
            defaults = currency_defaults.get(code) or {"name": code, "symbol": code, "symbol_position": "left", "decimal_places": 2}
            currency, _ = Currency.objects.get_or_create(
                code=code,
                defaults={
                    **defaults,
                    "is_active": True,
                    "is_base": False,
                    "thousands_separator": ",",
                    "decimal_separator": ".",
                },
            )
            if not currency.is_active:
                currency.is_active = True
                currency.save(update_fields=["is_active"])

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
