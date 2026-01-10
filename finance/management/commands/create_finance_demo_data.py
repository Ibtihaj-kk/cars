from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import random
from finance.models import Wallet, Transaction, EscrowEntry, CODSettlementRequest, FinancialAuditLog
from finance.services import FinanceService
from business_partners.models import BusinessPartner
from parts.models import Order, OrderItem, Part
from admin_panel.payment_models import CommissionRule

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate the database with demo finance data for testing.'

    def handle(self, *args, **options):
        self.stdout.write('Cleaning up existing demo data...')
        # Delete only demo data to avoid nuking the whole DB
        Order.objects.filter(order_number__startswith='ORD-').delete()
        CODSettlementRequest.objects.all().delete()
        Transaction.objects.all().delete()
        EscrowEntry.objects.all().delete()
        FinancialAuditLog.objects.all().delete()
        CommissionRule.objects.all().delete()
        
        # Reset wallet balances for demo users
        Wallet.objects.all().update(
            available_balance=Decimal('0.00'),
            escrow_balance=Decimal('0.00'),
            liability_balance=Decimal('0.00')
        )
        
        self.stdout.write('Creating finance demo data...')

        # 1. Get or verify users
        emails = {
            'admin': 'admin@carsyncro.com',
            'vendor': 'ibtihaj555@outlook.com',
            'user': 'kaimikhurramkaimi@gmail.com'
        }
        
        users = {}
        for role, email in emails.items():
            user = User.objects.filter(email=email).first()
            if not user:
                self.stdout.write(self.style.ERROR(f'User {email} not found. Skipping.'))
                continue
            users[role] = user

        if 'vendor' not in users:
            self.stdout.write(self.style.ERROR('Vendor user not found. Aborting.'))
            return

        vendor_bp = BusinessPartner.objects.filter(user=users['vendor']).first()
        if not vendor_bp:
            self.stdout.write(self.style.ERROR('Vendor BusinessPartner not found. Aborting.'))
            return

        # 2. Ensure Wallets exist
        admin_wallet = FinanceService.get_or_create_wallet(users['admin'])
        vendor_wallet = FinanceService.get_or_create_wallet(vendor_bp)
        user_wallet = FinanceService.get_or_create_wallet(users['user'])

        self.stdout.write(self.style.SUCCESS('Wallets verified/created.'))

        # 3. Create a Default Commission Rule (10%)
        CommissionRule.objects.create(
            name='Default 10% Commission',
            commission_type='percentage',
            commission_rate=Decimal('10.00'),
            is_active=True,
            applies_to_all_vendors=True,
            effective_from=timezone.now().date()
        )
        self.stdout.write(self.style.SUCCESS('Default commission rule created.'))

        # 4. Create Demo Orders and Transactions
        parts = Part.objects.filter(vendor=vendor_bp)[:5]
        if not parts.exists():
            parts = Part.objects.all()[:5]
            if not parts.exists():
                self.stdout.write(self.style.ERROR('No parts in system. Cannot create orders.'))
                return

        # Scenario A: Completed Online Payment (Direct to Available if delivered)
        self.stdout.write('Creating Online Payment scenario...')
        order_online = Order.objects.create(
            customer=users['user'],
            order_number=f'ORD-ONLINE-{random.randint(1000, 9999)}',
            status='delivered',
            total_price=Decimal('500.00'),
            payment_method='credit_card',
            payment_status='completed'
        )
        for part in parts[:2]:
            OrderItem.objects.create(
                order=order_online,
                part=part,
                quantity=1,
                price=Decimal('250.00')
            )
        FinanceService.record_order_payment(order_online, payment_method='online')
        
        # Refresh vendor_wallet to get latest balances after payment processing
        vendor_wallet.refresh_from_db()
        
        # Make one escrow entry due for settlement (from Scenario A)
        escrow_entries = EscrowEntry.objects.filter(wallet=vendor_wallet, is_released=False)
        if escrow_entries.exists():
            entry = escrow_entries.first()
            entry.release_date = timezone.now() - timezone.timedelta(days=1)
            entry.save()
            self.stdout.write(f'Updated escrow entry {entry.id} to be due for settlement.')

        # Scenario B: COD Payment (Creates Liability)
        self.stdout.write('Creating COD scenario...')
        order_cod = Order.objects.create(
            customer=users['user'],
            order_number=f'ORD-COD-{random.randint(1000, 9999)}',
            status='delivered',
            total_price=Decimal('300.00'),
            payment_method='cash_on_delivery',
            payment_status='completed'
        )
        for part in parts[2:3]:
            OrderItem.objects.create(
                order=order_cod,
                part=part,
                quantity=1,
                price=Decimal('300.00')
            )
        FinanceService.record_order_payment(order_cod, payment_method='cash_on_delivery')

        # Scenario C: Pending Escrow (Order confirmed but not delivered)
        self.stdout.write('Creating Escrow scenario...')
        order_escrow = Order.objects.create(
            customer=users['user'],
            order_number=f'ORD-ESCROW-{random.randint(1000, 9999)}',
            status='confirmed',
            total_price=Decimal('1000.00'),
            payment_method='credit_card',
            payment_status='completed'
        )
        OrderItem.objects.create(
            order=order_escrow,
            part=parts[0],
            quantity=2,
            price=Decimal('500.00')
        )
        FinanceService.record_order_payment(order_escrow, payment_method='online')

        # 5. Create a COD Settlement Request
        self.stdout.write('Creating COD Settlement Request...')
        CODSettlementRequest.objects.create(
            vendor=vendor_bp,
            wallet=vendor_wallet,
            amount=Decimal('50.00'),
            reference_number='REF123456',
            status='pending'
        )

        # 6. Create some manual adjustments/audit logs
        self.stdout.write('Creating manual adjustments...')
        
        # Refresh vendor_wallet to get latest balances before manual adjustment
        vendor_wallet.refresh_from_db()
        
        FinanceService.log_action(
            action_type='BALANCE_ADJUSTMENT',
            user=users['admin'],
            wallet=vendor_wallet,
            amount=Decimal('10.00'),
            details={'reason': 'Bonus for high performance'}
        )
        
        vendor_wallet.available_balance += Decimal('10.00')
        vendor_wallet.save()

        self.stdout.write(self.style.SUCCESS('Successfully created finance demo data.'))
