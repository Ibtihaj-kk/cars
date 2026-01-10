from django.db.models.signals import post_save
from django.dispatch import receiver
from parts.models import Order
from subscriptions.models import SubscriptionPayment
from .services import FinanceService

print("FINANCE SIGNALS LOADED")

@receiver(post_save, sender=Order)
def handle_order_payment_signal(sender, instance, created, **kwargs):
    """
    Listens for Order status changes and triggers financial recording.
    """
    print(f"SIGNAL TRIGGERED for Order {instance.order_number}, status: {instance.status}, payment_status: {instance.payment_status}")
    # 1. Handle Successful Payment
    if instance.payment_status == 'completed':
        # Finalize inventory deduction if it hasn't been done yet
        # (This handles the Phase 2 of the 2-phase commit for online payments)
        # Note: finalize_inventory is idempotent and safe to call multiple times if needed, 
        # but here we call it when payment is officially confirmed.
        instance.finalize_inventory()

        # Check if we already recorded this to avoid duplicates
        from .models import Transaction
        from django.contrib.contenttypes.models import ContentType
        
        if not instance.items.exists():
            return

        order_item_ct = ContentType.objects.get_for_model(instance.items.first())
        
        # Check for each item individually for robustness
        for item in instance.items.all():
            exists = Transaction.objects.filter(
                reference_content_type=order_item_ct,
                reference_id=item.id,
                transaction_type='PAYMENT'
            ).exists()
            
            if not exists:
                # We need to call record_order_payment but it currently processes all items
                # Let's adjust the logic to handle the whole order if not partially recorded
                FinanceService.record_order_payment(
                    instance, 
                    payment_method='cod' if instance.payment_method == 'cash_on_delivery' else 'online'
                )
                break # record_order_payment processes all items, so we break after first trigger

    # 2. Handle Order Cancellation/Refund
    if instance.status == 'cancelled' or instance.payment_status == 'refunded':
        from .models import Transaction
        from django.contrib.contenttypes.models import ContentType
        
        if not instance.items.exists():
            return
            
        order_item_ct = ContentType.objects.get_for_model(instance.items.first())
        
        # Find all transactions related to this order items and reverse them
        txns_to_reverse = Transaction.objects.filter(
            reference_content_type=order_item_ct,
            reference_id__in=instance.items.values_list('id', flat=True),
            status='completed'
        )
        
        for txn in txns_to_reverse:
            FinanceService.reverse_transaction(txn.id, reason=f"Order {instance.status}")

    # 3. Handle Order Delivery (Trigger Escrow/COD Settlement)
    if instance.status == 'delivered':
        FinanceService.trigger_delivery_settlement(instance)

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
