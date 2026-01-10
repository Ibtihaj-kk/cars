import os
import django
import sys
from decimal import Decimal
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yallamotor_project.settings')
django.setup()

from finance.models import Wallet, CODSettlementRequest, Transaction
from business_partners.models import BusinessPartner, VendorProfile
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from admin_panel.payment_models import PaymentBatch, VendorPayment, PaymentStatus

User = get_user_model()

def verify_flows():
    print("Starting integration verification using Client...")
    
    # 1. Setup users
    vendor_user = User.objects.get(email='ibtihaj555@outlook.com')
    admin_user = User.objects.get(email='admin@carsyncro.com')
    vendor = BusinessPartner.objects.get(user=vendor_user)
    
    # 2. Get wallet and check liability
    vendor_ct = ContentType.objects.get_for_model(vendor)
    wallet = Wallet.objects.get(owner_content_type=vendor_ct, owner_id=vendor.id)
    print(f"Vendor Liability Balance: {wallet.liability_balance}")
    
    if wallet.liability_balance <= 0:
        print("Increasing liability for testing...")
        wallet.liability_balance = Decimal('100.00')
        wallet.save()

    client = Client()

    # 3. Simulate Vendor Submitting COD Settlement via UI View
    print("\n--- Simulating Vendor Settlement Submission ---")
    client.force_login(vendor_user)
    
    # Create a dummy image
    image_content = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b'
    uploaded_file = SimpleUploadedFile('receipt.gif', image_content, content_type='image/gif')
    
    url = reverse('finance:submit_cod_settlement')
    response = client.post(url, {
        'amount': '50.00',
        'reference_number': 'TEST-REF-CLIENT-123',
        'evidence_image': uploaded_file
    })
    
    if response.status_code == 302:
        print("Submission Successful (Redirected)")
        settlement_req = CODSettlementRequest.objects.filter(reference_number='TEST-REF-CLIENT-123').first()
        if settlement_req:
            print(f"Created Request ID: {settlement_req.id}, Amount: {settlement_req.amount}")
        else:
            print("FAILED: Settlement request not found in DB")
            return
    else:
        print(f"FAILED: Submission view returned status {response.status_code}")
        return

    # 4. Simulate Admin Approving Settlement via UI View
    print("\n--- Simulating Admin Settlement Approval ---")
    client.force_login(admin_user)
    
    url = reverse('admin_panel:finance_cod_settlements')
    response = client.post(url, {
        'request_id': settlement_req.id,
        'action': 'approved',
        'notes': 'Verified payment proof via automated test.'
    })
    
    if response.status_code == 302:
        print("Approval Successful (Redirected)")
        
        # Verify DB changes
        settlement_req.refresh_from_db()
        wallet.refresh_from_db()
        
        print(f"New Request Status: {settlement_req.status}")
        print(f"New Wallet Liability: {wallet.liability_balance}")
        
        if settlement_req.status == 'approved' and wallet.liability_balance <= Decimal('50.00'):
            print("VERIFICATION SUCCESS: Liability reduced correctly.")
        else:
            print("VERIFICATION FAILED: Liability or status incorrect.")
            
        # Check transaction record
        tx = Transaction.objects.filter(transaction_type='COD_SETTLEMENT', reference_id=settlement_req.id).first()
        if tx:
            print(f"Created Transaction: {tx.id}, Amount: {tx.amount_base}")
        else:
            print("FAILED: No transaction record created.")
    else:
        print(f"FAILED: Admin approval view returned status {response.status_code}")

    # 5. Simulate Payout Request
    print("\n--- Simulating Payout Request ---")
    client.force_login(vendor_user)
    
    # Refresh objects from DB
    vendor = BusinessPartner.objects.filter(user=vendor_user).first()
    if not vendor:
        print("FAILED: Vendor BusinessPartner not found")
        return
    
    vendor_ct = ContentType.objects.get_for_model(vendor)
    wallet = Wallet.objects.get(owner_content_type=vendor_ct, owner_id=vendor.id)
    print(f"Wallet ID: {wallet.id}, balance before update: {wallet.available_balance}")
    
    # Ensure available balance
    wallet.available_balance = Decimal('500.00')
    wallet.save()
    wallet.refresh_from_db()
    print(f"Wallet ID: {wallet.id}, balance after update: {wallet.available_balance}")
    
    # Ensure bank details are on the profile
    profile, created = VendorProfile.objects.get_or_create(business_partner=vendor)
    profile.bank_name = "Test Bank"
    profile.bank_account_number = "123456789"
    profile.save()
    
    print(f"Set Available Balance: {wallet.available_balance}")
    print(f"Bank Details Set: {profile.bank_name}, {profile.bank_account_number}")
    
    url = reverse('finance:request_payout')
    import json
    response = client.post(url, data=json.dumps({'amount': '100.00'}), content_type='application/json')
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print(f"Payout Request Successful: {data.get('message')}")
            wallet.refresh_from_db()
            print(f"New Available Balance: {wallet.available_balance}")
            
            # Check for PENDING payout transaction
            tx = Transaction.objects.filter(source_wallet=wallet, transaction_type='PAYOUT', status='pending').first()
            if tx:
                print(f"Created Pending Payout Transaction: {tx.id}, Amount: {tx.amount_base}")
            else:
                print("FAILED: No pending payout transaction record created.")
        else:
            print(f"FAILED: Payout request logic error: {data.get('message')}")
    else:
        print(f"FAILED: Payout request view returned status {response.status_code}")

    print("\n--- Verifying Vendor Finance Pages & Actions ---")
    client.force_login(vendor_user)
    finance_pages = [
        ('business_partners:vendor_finance_dashboard', {}),
        ('business_partners:vendor_settlement_statements', {}),
        ('business_partners:vendor_payout_tracking', {}),
        ('business_partners:vendor_commission_breakdown', {}),
        ('business_partners:vendor_tax_summary', {}),
        ('business_partners:vendor_finance_ledger', {}),
        ('business_partners:vendor_bank_setup', {}),
        ('finance:submit_cod_settlement', {}),
    ]

    for name, kwargs in finance_pages:
        url = reverse(name, kwargs=kwargs)
        resp = client.get(url)
        if resp.status_code not in (200, 302):
            print(f"FAILED: GET {name} -> {resp.status_code}")
            return
        print(f"OK: GET {name} -> {resp.status_code}")

    bank_url = reverse('business_partners:vendor_bank_setup')
    resp = client.post(bank_url, {
        'bank_name': 'Habib Bank Limited (HBL)',
        'bank_branch': 'Main Branch',
        'account_holder_name': 'Test Holder',
        'account_number': '1234567890',
        'iban': 'PK36HABB0000000000000000',
        'swift_code': 'HABORPKAXXX',
    })
    if resp.status_code != 302:
        print(f"FAILED: Bank setup POST -> {resp.status_code}")
        return
    print("OK: Bank setup POST -> 302")

    tax_url = reverse('business_partners:vendor_tax_summary')
    resp = client.post(tax_url, {'tax_id': 'TEST-TRN-123'})
    if resp.status_code != 302:
        print(f"FAILED: Tax settings POST -> {resp.status_code}")
        return
    print("OK: Tax settings POST -> 302")

    ledger_export_url = reverse('business_partners:vendor_finance_ledger_export_csv')
    resp = client.get(ledger_export_url)
    if resp.status_code != 200:
        print(f"FAILED: Ledger export GET -> {resp.status_code}")
        return
    print("OK: Ledger export GET -> 200")

    batch = PaymentBatch.objects.create(
        batch_reference='TEST-BATCH-CLIENT-001',
        name='Test Batch',
        description='Integration test batch',
        status=PaymentStatus.COMPLETED,
        created_by=admin_user,
    )
    payment = VendorPayment.objects.create(
        vendor=vendor,
        amount=Decimal('120.00'),
        commission_amount=Decimal('20.00'),
        notes='Test payment',
        status=PaymentStatus.COMPLETED,
        created_by=admin_user,
    )
    batch.payments.add(payment)

    stmt_url = reverse('business_partners:vendor_settlement_download_csv', kwargs={'batch_id': batch.id})
    resp = client.get(stmt_url)
    if resp.status_code != 200:
        print(f"FAILED: Statement download CSV -> {resp.status_code}")
        return
    print("OK: Statement download CSV -> 200")

if __name__ == "__main__":
    verify_flows()
