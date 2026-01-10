from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from finance.models import EscrowEntry, Wallet, Transaction, FinancialAuditLog
from finance.services import FinanceService
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Releases matured escrow entries to vendor available balance'

    def handle(self, *args, **options):
        now = timezone.now()
        matured_entries = EscrowEntry.objects.filter(
            release_date__lte=now,
            is_released=False
        ).select_related('wallet')

        if not matured_entries.exists():
            self.stdout.write(self.style.SUCCESS('No matured escrow entries found.'))
            return

        total_settled = 0
        count = 0

        for entry in matured_entries:
            try:
                with transaction.atomic():
                    wallet = entry.wallet
                    amount = entry.amount
                    
                    # Update balances
                    wallet.escrow_balance -= amount
                    wallet.available_balance += amount
                    wallet.save()
                    
                    # Mark as released
                    entry.is_released = True
                    entry.save()
                    
                    # Log the movement in Transaction
                    Transaction.objects.create(
                        source_wallet=wallet, # Showing movement from escrow part of wallet
                        destination_wallet=wallet, # To available part
                        amount_base=amount,
                        amount_display=amount,
                        exchange_rate=Decimal('1.000000'),
                        currency=wallet.currency,
                        transaction_type='ESCROW_RELEASE',
                        reference=entry.transaction.reference,
                        metadata={'escrow_entry_id': entry.id, 'reason': 'Escrow Maturity Release', 'reference_text': f"Escrow Release for {entry.transaction.reference}"}
                    )
                    
                    # Log high-level audit action
                    FinanceService.log_action(
                        action_type='ESCROW_RELEASED',
                        user=None, # System automated
                        wallet=wallet,
                        amount=amount,
                        details={
                            'escrow_entry_id': entry.id,
                            'original_transaction': entry.transaction.id
                        }
                    )
                    
                    count += 1
                    total_settled += amount
                    
            except Exception as e:
                logger.error(f"Failed to settle escrow entry {entry.id}: {str(e)}")
                self.stdout.write(self.style.ERROR(f"Failed to settle escrow entry {entry.id}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f'Successfully settled {count} entries totalling {total_settled} {wallet.currency}'))
