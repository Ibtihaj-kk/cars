from celery import shared_task
from django.utils import timezone
from django.db import transaction
from .models import EscrowEntry, Transaction
from .services import FinanceService

@shared_task
def process_escrow_releases():
    """
    Periodic task to release funds from escrow to available balance.
    """
    now = timezone.now()
    # Find all unreleased entries whose release date has passed
    pending_releases = EscrowEntry.objects.filter(
        is_released=False,
        release_date__lte=now
    )
    
    count = 0
    for entry in pending_releases:
        with transaction.atomic():
            wallet = entry.wallet
            
            # Move funds in the wallet
            wallet.escrow_balance -= entry.amount
            wallet.available_balance += entry.amount
            wallet.save()
            
            # Mark entry as released
            entry.is_released = True
            entry.save()
            
            # Optional: Record a transaction for the release (internal movement)
            Transaction.objects.create(
                source_wallet=wallet, # From its own escrow bucket
                destination_wallet=wallet, # To its own available bucket
                amount_base=entry.amount,
                amount_display=entry.amount,
                exchange_rate=1.0,
                currency=wallet.currency,
                transaction_type='ADJUSTMENT',
                metadata={'reason': 'Escrow Release', 'escrow_entry_id': entry.id}
            )
            count += 1
            
    return f"Released {count} escrow entries."
