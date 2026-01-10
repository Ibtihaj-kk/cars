from parts.models import Order
from finance.models import Wallet, Transaction
from django.contrib.auth import get_user_model

def check_order_finance():
    User = get_user_model()
    guest_email = 'kaimikhurramkaimi@gmail.com'
    vendor_email = 'ibtihaj555@outlook.com'
    
    order = Order.objects.filter(guest_email=guest_email).first()
    if not order:
        order = Order.objects.filter(customer__email=guest_email).first()
        
    if not order:
        print(f"Order for {guest_email} not found.")
        return

    print(f"Order: {order.order_number}")
    print(f"Status: {order.status}")
    print(f"Payment Method: {order.payment_method}")
    print(f"Payment Status: {order.payment_status}")
    
    vendor_user = User.objects.filter(email=vendor_email).first()
    if vendor_user:
        print(f"Vendor User found: {vendor_user.email}")
        try:
            vendor_partner = vendor_user.vendor_profile.business_partner
            print(f"Vendor Partner: {vendor_partner.name}")
            wallet = Wallet.objects.filter(owner=vendor_partner).first()
            if wallet:
                print(f"Wallet Liability Balance: {wallet.liability_balance}")
                print(f"Wallet Available Balance: {wallet.available_balance}")
                
                txns = Transaction.objects.filter(destination_wallet=wallet)
                print(f"Transactions to vendor wallet: {txns.count()}")
                for t in txns:
                    print(f"  - {t.transaction_type}: {t.amount_display} {t.currency} (Status: {t.status})")
            else:
                print("No wallet found for vendor.")
        except Exception as e:
            print(f"Error checking vendor wallet: {e}")
    else:
        print(f"Vendor User {vendor_email} not found.")

if __name__ == "__main__":
    check_order_finance()
