from finance.models import Transaction, Wallet
from parts.models import Order
from business_partners.models import BusinessPartner
from django.contrib.contenttypes.models import ContentType

def check_order_details():
    order_number = 'ORD6247505'
    vendor_email = 'ibtihaj555@outlook.com'
    
    print(f"Investigating Order: {order_number}")
    try:
        order = Order.objects.get(order_number=order_number)
    except Order.DoesNotExist:
        print("Order not found.")
        return

    print(f"Order Status: {order.status}")
    print(f"Payment Method: {order.payment_method}")
    print(f"Payment Status: {order.payment_status}")
    
    # Check transactions for this order
    txns = Transaction.objects.filter(metadata__order_id=order.id)
    print(f"\nFound {txns.count()} transactions for this order:")
    for t in txns:
        owner = t.destination_wallet.owner if t.destination_wallet else "None"
        print(f" - ID: {t.id}, Type: {t.transaction_type}, Amount: {t.amount_display}, Dest: {owner}")

    # Check vendor wallet
    print(f"\nInvestigating Vendor: {vendor_email}")
    bp = BusinessPartner.objects.filter(user__email=vendor_email).first()
    if not bp:
        print("BusinessPartner not found for this email.")
        return
    
    print(f"BusinessPartner: {bp.name} (ID: {bp.id})")
    
    vendor_ct = ContentType.objects.get_for_model(BusinessPartner)
    wallet = Wallet.objects.filter(owner_content_type=vendor_ct, owner_id=bp.id).first()
    
    if not wallet:
        print("Wallet not found for vendor.")
    else:
        print(f"Wallet ID: {wallet.id}")
        print(f"Liability Balance: {wallet.liability_balance}")
        print(f"Available Balance: {wallet.available_balance}")
        print(f"Escrow Balance: {wallet.escrow_balance}")
        
        # Check all transactions for this wallet
        wallet_txns = Transaction.objects.filter(destination_wallet=wallet)
        print(f"\nFound {wallet_txns.count()} transactions for this vendor wallet:")
        for t in wallet_txns:
            print(f" - ID: {t.id}, Type: {t.transaction_type}, Amount: {t.amount_display}, Created: {t.created_at}")

check_order_details()
