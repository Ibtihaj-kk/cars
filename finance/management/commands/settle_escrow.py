from django.core.management.base import BaseCommand
from django.utils import timezone
from finance.models import EscrowEntry
from finance.services import FinanceService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Releases matured escrow entries to vendor available balance'

    def handle(self, *args, **options):
        now = timezone.now()
        matured_entries = EscrowEntry.objects.filter(
            release_date__lte=now,
            is_released=False
        )

        if not matured_entries.exists():
            self.stdout.write(self.style.SUCCESS('No matured escrow entries found.'))
            return

        try:
            count = FinanceService.release_matured_escrow_entries(now=now)
        except Exception as e:
            logger.error("Escrow settlement failed: %s", str(e))
            self.stdout.write(self.style.ERROR(f"Escrow settlement failed: {str(e)}"))
            return

        self.stdout.write(self.style.SUCCESS(f'Successfully settled {count} entries.'))
