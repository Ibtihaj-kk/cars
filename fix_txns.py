if __name__ == "__main__":
    import os
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yallamotor_project.settings')
    django.setup()
    
    from finance.models import Transaction, Wallet
    from parts.models import Order
    from business_partners.models import BusinessPartner
    from django.contrib.contenttypes.models import ContentType

    def update_txns():
        try:
            o = Order.objects.get(order_number='ORD6247505')
        except Order.DoesNotExist:
            print("Order ORD6247505 not found")
            return

        txns = Transaction.objects.filter(metadata__order_id=o.id)
        print(f"Found {txns.count()} transactions for Order {o.id}")
        
        # Get vendor wallet
        vendor_bp = BusinessPartner.objects.get(id=1) # Auto Parts
        ct = ContentType.objects.get_for_model(BusinessPartner)
        vendor_wallet = Wallet.objects.get(owner_id=vendor_bp.id, owner_content_type=ct)
        
        for t in txns:
            # Update metadata
            t.metadata['order_number'] = o.order_number
            
            # Link commission to vendor wallet as source
            if t.transaction_type == 'COMMISSION' and not t.source_wallet:
                t.source_wallet = vendor_wallet
                print(f"Linked Commission ID {t.id} to Source Wallet {vendor_wallet.id}")
            
            t.save()
            print(f"Updated ID {t.id} metadata")

    update_txns()
