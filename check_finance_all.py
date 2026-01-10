from parts.models import Order
from finance.models import Wallet, Transaction
from django.contrib.auth import get_user_model

def check_all_finance():
    print("Checking all delivered orders...")
    delivered_orders = Order.objects.filter(status='delivered')
    print(f"Found {delivered_orders.count()} delivered orders.")
    
    for order in delivered_orders:
        print(f"\nOrder: {order.order_number}")
        print(f"Customer: {order.customer_email or order.guest_email}")
        print(f"Payment Method: {order.payment_method}")
        
        # Check for transactions
        txns = Transaction.objects.filter(metadata__order_id=order.id)
        print(f"Transactions for this order: {txns.count()}")
        for t in txns:
            print(f"  - {t.transaction_type}: {t.amount_display} {t.currency} (To: {t.destination_wallet.owner if t.destination_wallet else 'None'})")

    print("\nChecking wallets with liability balance > 0:")
    wallets = Wallet.objects.filter(liability_balance__gt=0)
    for w in wallets:
        print(f"Wallet for {w.owner}: Liability = {w.liability_balance}")

if __name__ == "__main__":
    check_all_finance()
