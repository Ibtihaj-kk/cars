from decimal import Decimal
from django.db import transaction, models
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from .models import Wallet, Transaction, EscrowEntry
from admin_panel.payment_models import CommissionRule
from business_partners.models import BusinessPartner
from django.contrib.auth import get_user_model

User = get_user_model()

class FinanceService:
    @staticmethod
    def get_or_create_wallet(owner):
        """
        Gets or creates a wallet for a BusinessPartner or User.
        """
        content_type = ContentType.objects.get_for_model(owner)
        wallet, created = Wallet.objects.get_or_create(
            owner_content_type=content_type,
            owner_id=owner.id,
            defaults={'currency': 'USD'} # Default base currency
        )
        return wallet

    @staticmethod
    def get_platform_wallet():
        """
        Returns the MasterAdmin/Platform wallet.
        """
        # Assuming the first superuser is the MasterAdmin platform owner
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            raise ValueError("No MasterAdmin user found to own the platform wallet.")
        return FinanceService.get_or_create_wallet(admin_user)

    @classmethod
    @transaction.atomic
    def record_order_payment(cls, order, payment_method='online'):
        """
        Records an order payment, handles commissions, and escrow.
        """
        # 1. Get Wallets
        platform_wallet = cls.get_platform_wallet()
        
        # We process each item in the order because they might belong to different vendors
        for item in order.items.all():
            vendor = item.part.vendor
            vendor_wallet = cls.get_or_create_wallet(vendor)
            
            # 2. Calculate Commission
            commission_rule = cls._get_active_commission_rule(vendor, item.total_price)
            commission_amount = cls._calculate_commission(item.total_price, commission_rule)
            vendor_amount = item.total_price - commission_amount
            
            # 3. Create Transactions (Double-Entry)
            # Transaction: Customer -> Platform (Total)
            # Transaction: Platform -> Vendor (Net)
            # Transaction: Platform -> Revenue (Commission)
            
            # For simplicity in this robust model, we record the split directly:
            
            # Net to Vendor (Escrow or Liability if COD)
            txn_vendor = Transaction.objects.create(
                destination_wallet=vendor_wallet,
                amount_base=vendor_amount,
                amount_display=vendor_amount, # Assuming base for now
                exchange_rate=Decimal('1.000000'),
                currency='USD',
                transaction_type='PAYMENT',
                reference=item,
                metadata={'order_id': order.id}
            )
            
            if payment_method == 'cod':
                # Vendor has the cash, so it's a liability they owe the platform
                vendor_wallet.liability_balance += item.total_price
                # We still record the commission we ARE OWED
                vendor_wallet.available_balance -= commission_amount
            else:
                # Online payment: Money is in platform hands, vendor gets it in Escrow
                vendor_wallet.escrow_balance += vendor_amount
                # Create Escrow Entry for release
                cls._create_escrow_entry(vendor_wallet, txn_vendor, vendor_amount, vendor)

            vendor_wallet.save()

            # Commission to Platform
            Transaction.objects.create(
                destination_wallet=platform_wallet,
                amount_base=commission_amount,
                amount_display=commission_amount,
                exchange_rate=Decimal('1.000000'),
                currency='USD',
                transaction_type='COMMISSION',
                reference=item,
                metadata={'order_id': order.id, 'vendor_id': vendor.id}
            )
            platform_wallet.available_balance += commission_amount
            platform_wallet.save()

    @staticmethod
    def _get_active_commission_rule(vendor, amount):
        """
        Finds the most specific active commission rule for a vendor.
        """
        now = timezone.now().date()
        rules = CommissionRule.objects.filter(
            is_active=True,
            effective_from__lte=now
        ).filter(
            models.Q(effective_to__isnull=True) | models.Q(effective_to__gte=now)
        ).filter(
            models.Q(min_amount__lte=amount),
            models.Q(max_amount__isnull=True) | models.Q(max_amount__gte=amount)
        )

        # Priority 1: Specific Vendor rules
        specific_rule = rules.filter(specific_vendors=vendor).first()
        if specific_rule:
            return specific_rule
        
        # Priority 2: Global rules
        global_rule = rules.filter(applies_to_all_vendors=True).first()
        return global_rule

    @staticmethod
    def _calculate_commission(amount, rule):
        if not rule:
            return Decimal('0.00')
        
        if rule.commission_type == 'percentage':
            return (amount * rule.commission_rate / 100).quantize(Decimal('0.01'))
        elif rule.commission_type == 'fixed':
            return rule.fixed_amount
        return Decimal('0.00')

    @staticmethod
    def _create_escrow_entry(wallet, transaction, amount, vendor):
        # Determine release date (Dynamic Policy)
        # For now, default to 7 days. In future, fetch from vendor.settlement_policy
        days_to_release = 7 
        release_date = timezone.now() + timezone.timedelta(days=days_to_release)
        
        EscrowEntry.objects.create(
            wallet=wallet,
            transaction=transaction,
            amount=amount,
            release_date=release_date
        )

    @classmethod
    @transaction.atomic
    def settle_cod_payment(cls, vendor, amount_to_settle):
        """
        MasterAdmin confirms that vendor has handed over COD cash.
        """
        vendor_wallet = cls.get_or_create_wallet(vendor)
        platform_wallet = cls.get_platform_wallet()

        if vendor_wallet.liability_balance < amount_to_settle:
            raise ValueError("Settlement amount exceeds vendor liability.")

        # Record Transaction
        Transaction.objects.create(
            source_wallet=vendor_wallet,
            destination_wallet=platform_wallet,
            amount_base=amount_to_settle,
            amount_display=amount_to_settle,
            exchange_rate=Decimal('1.000000'),
            currency='USD',
            transaction_type='COD_SETTLEMENT'
        )

        # Update Balances
        vendor_wallet.liability_balance -= amount_to_settle
        vendor_wallet.save()
        
        # Platform now has the real cash
        platform_wallet.available_balance += amount_to_settle
        platform_wallet.save()

    @classmethod
    @transaction.atomic
    def record_subscription_payment(cls, subscription_payment):
        """
        Records a subscription payment to platform revenue.
        """
        user = subscription_payment.subscription.user
        platform_wallet = cls.get_platform_wallet()
        
        # We don't necessarily need a user wallet for subscriptions unless they have a "Wallet Balance"
        # For now, we record it as direct Platform Revenue
        
        Transaction.objects.create(
            destination_wallet=platform_wallet,
            amount_base=subscription_payment.amount,
            amount_display=subscription_payment.amount,
            exchange_rate=Decimal('1.000000'),
            currency='USD',
            transaction_type='SUBSCRIPTION',
            reference=subscription_payment,
            metadata={'subscription_id': subscription_payment.subscription.id}
        )
        
        platform_wallet.available_balance += subscription_payment.amount
        platform_wallet.save()
