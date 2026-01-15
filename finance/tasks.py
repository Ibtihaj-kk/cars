from celery import shared_task
from .services import FinanceService

@shared_task
def process_escrow_releases():
    """
    Periodic task to release funds from escrow to available balance.
    """
    count = FinanceService.release_matured_escrow_entries()
    return f"Released {count} escrow entries."
