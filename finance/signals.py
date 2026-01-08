from django.db.models.signals import post_save
from django.dispatch import receiver
from parts.models import Order
from subscriptions.models import SubscriptionPayment
from .services import FinanceService

@receiver(post_save, sender=Order)
def handle_order_payment_signal(sender, instance, created, **kwargs):
    """
    Listens for Order status changes and triggers financial recording.
    """
    # If payment status is marked as completed, record it in finance
    if instance.payment_status == 'completed':
        # Check if we already recorded this to avoid duplicates
        # In a real double-entry system, the Transaction table serves as the check
        from .models import Transaction
        from django.contrib.contenttypes.models import ContentType
        
        # We check if any Transaction exists for this order items
        # (This is a simplified check; in production, we'd use a unique constraint or idempotency key)
        order_item_ct = ContentType.objects.get_for_model(instance.items.first()) if instance.items.exists() else None
        if order_item_ct:
            exists = Transaction.objects.filter(
                reference_content_type=order_item_ct,
                reference_id__in=instance.items.values_list('id', flat=True),
                transaction_type='PAYMENT'
            ).exists()
            
            if not exists:
                FinanceService.record_order_payment(
                    instance, 
                    payment_method='cod' if instance.payment_method == 'cash_on_delivery' else 'online'
                )

@receiver(post_save, sender=SubscriptionPayment)
def handle_subscription_payment_signal(sender, instance, created, **kwargs):
    """
    Listens for SubscriptionPayment successes and triggers financial recording.
    """
    if instance.is_successful:
        from .models import Transaction
        from django.contrib.contenttypes.models import ContentType
        
        ct = ContentType.objects.get_for_model(instance)
        exists = Transaction.objects.filter(
            reference_content_type=ct,
            reference_id=instance.id,
            transaction_type='SUBSCRIPTION'
        ).exists()
        
        if not exists:
            FinanceService.record_subscription_payment(instance)
