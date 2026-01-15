from decimal import Decimal
from django.db import transaction, models
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from .models import Wallet, Transaction, EscrowEntry, FinancialAuditLog, CODSettlementRequest
from admin_panel.payment_models import CommissionRule
from business_partners.models import BusinessPartner
from django.contrib.auth import get_user_model
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class FinanceService:
    @staticmethod
    def _reference_kwargs(reference_obj):
        if not reference_obj:
            return {}
        content_type = ContentType.objects.get_for_model(reference_obj)
        return {
            'reference_content_type': content_type,
            'reference_id': reference_obj.id,
        }

    @staticmethod
    def _normalize_payment_method(payment_method):
        if not payment_method:
            return 'online'
        normalized = str(payment_method).strip().lower()
        if normalized in {'cod', 'cash_on_delivery', 'cash-on-delivery'}:
            return 'cod'
        return normalized

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

    @staticmethod
    def log_action(action_type, user, wallet=None, amount=None, details=None):
        """Logs a high-level financial action for auditing"""
        FinancialAuditLog.objects.create(
            action_type=action_type,
            user=user,
            wallet=wallet,
            amount=amount,
            details=details or {}
        )

    @classmethod
    @transaction.atomic
    def record_payout(cls, vendor, amount, reference=None, processed_by=None):
        """
        Records a payout to a vendor, deducting from available balance.
        """
        wallet = cls.get_or_create_wallet(vendor)
        
        if wallet.available_balance < amount:
            raise ValueError(f"Insufficient funds for payout. Available: {wallet.available_balance}, Requested: {amount}")
            
        wallet.available_balance -= amount
        wallet.save()
        
        # Create Transaction
        metadata = {'vendor_id': vendor.id}
        if isinstance(reference, str):
            metadata['description'] = reference
            reference_obj = None
        else:
            reference_obj = reference

        transaction_obj = Transaction.objects.create(
            source_wallet=wallet,
            destination_wallet=None, # External payout
            amount_base=amount,
            amount_display=amount,
            exchange_rate=Decimal('1.000000'),
            currency='USD',
            transaction_type='PAYOUT',
            status='pending',
            metadata=metadata,
            **cls._reference_kwargs(reference_obj)
        )
        
        # Log high-level audit action
        cls.log_action(
            action_type='PAYOUT_PROCESSED',
            user=processed_by,
            wallet=wallet,
            amount=amount,
            details={
                'transaction_id': transaction_obj.id,
                'vendor_name': vendor.business_name,
                'reference': reference
            }
        )
        return True

    @classmethod
    @transaction.atomic
    def sync_legacy_vendor_payments(cls, vendor=None, limit=5000):
        from admin_panel.payment_models import PaymentStatus, VendorPayment

        payments_qs = VendorPayment.objects.filter(status=PaymentStatus.COMPLETED).select_related('vendor').order_by('id')
        if vendor is not None:
            payments_qs = payments_qs.filter(vendor=vendor)

        if limit is not None:
            payments = list(payments_qs[: int(limit)])
        else:
            payments = list(payments_qs)

        if not payments:
            return 0

        payment_ct = ContentType.objects.get_for_model(VendorPayment)
        payment_ids = [p.id for p in payments]
        existing_ids = set(
            Transaction.objects.filter(
                reference_content_type=payment_ct,
                reference_id__in=payment_ids,
                transaction_type='PAYOUT',
            ).values_list('reference_id', flat=True)
        )

        to_create = []
        for payment in payments:
            if payment.id in existing_ids:
                continue
            wallet = cls.get_or_create_wallet(payment.vendor)
            created_at = payment.payment_date or payment.processed_at or payment.created_at
            to_create.append(
                Transaction(
                    source_wallet=wallet,
                    destination_wallet=None,
                    amount_base=payment.net_amount,
                    amount_display=payment.net_amount,
                    exchange_rate=Decimal('1.000000'),
                    currency=wallet.currency,
                    transaction_type='PAYOUT',
                    status='completed',
                    reference_content_type=payment_ct,
                    reference_id=payment.id,
                    metadata={
                        'legacy': True,
                        'payment_reference': payment.payment_reference,
                        'payment_method': payment.payment_method,
                        'gross_amount': str(payment.amount),
                        'commission_amount': str(payment.commission_amount),
                        'net_amount': str(payment.net_amount),
                    },
                    created_at=created_at,
                )
            )

        if not to_create:
            return 0

        Transaction.objects.bulk_create(to_create, batch_size=500)
        return len(to_create)

    @classmethod
    @transaction.atomic
    def record_order_payment(cls, order, payment_method='online'):
        """
        Records an order payment, handles commissions, taxes, and escrow.
        """
        payment_method = cls._normalize_payment_method(payment_method or getattr(order, 'payment_method', None))
        # 1. Get Wallets
        platform_wallet = None
        try:
            platform_wallet = cls.get_platform_wallet()
        except ValueError:
            platform_wallet = None
        
        # We process each item in the order because they might belong to different vendors
        from .models import Transaction
        from django.contrib.contenttypes.models import ContentType
        
        from decimal import Decimal as D

        for item in order.items.all():
            if item.total_price <= 0:
                continue # Skip zero price items or errors
                
            # Check if this item has already been processed to avoid double-entry
            item_ct = ContentType.objects.get_for_model(item)
            if Transaction.objects.filter(
                reference_content_type=item_ct, 
                reference_id=item.id,
                transaction_type__in=['PAYMENT', 'COMMISSION']
            ).exists():
                continue

            vendor = item.part.vendor
            if not vendor:
                dealer_user = getattr(item.part, 'dealer', None)
                if dealer_user:
                    vendor = (
                        BusinessPartner.objects.filter(user=dealer_user, roles__role_type='vendor')
                        .distinct()
                        .first()
                    ) or BusinessPartner.objects.filter(user=dealer_user).first()
            if not vendor:
                continue

            vendor_wallet = cls.get_or_create_wallet(vendor)
            
            # 1. Get amounts in USD (Base Currency)
            item_price_usd = item.price
            item_tax_usd = getattr(item, 'tax_amount', D('0.00'))
            
            # Use locked metadata if available (for new orders)
            if hasattr(item, 'original_currency_code') and item.original_currency_code and item.original_currency_code != 'USD':
                # If we have a locked rate, use it to ensure we have the correct USD amount
                # item.price should already be in USD if views.py worked correctly
                # but we can verify or use vendor_currency_amount * locked_exchange_rate
                if item.locked_exchange_rate and item.vendor_currency_amount:
                    item_price_usd = (item.vendor_currency_amount * item.locked_exchange_rate).quantize(D('0.01'))
                    # Tax might need conversion too if it was stored in vendor currency (unlikely but safe)
                    # For now assume item_tax_usd is already in USD as per views.py fix
            elif item.price * item.quantity < order.total_price * D('0.5') and order.total_price > D('20.00'):
                # Heuristic for legacy orders (like ORD8190047)
                # If item price is much lower than order total, it's likely BHD stored as USD
                # 1 BHD = 2.66 USD (1/0.376)
                item_price_usd = (item.price * D('1.000000') / D('0.376000')).quantize(D('0.01'))
                item_tax_usd = (item_tax_usd * D('1.000000') / D('0.376000')).quantize(D('0.01'))
            
            total_item_price_usd = item_price_usd * item.quantity
            net_amount_usd = total_item_price_usd
            
            # 2. Calculate Commission on NET amount (excluding tax)
            commission_rule = cls._get_active_commission_rule(vendor, net_amount_usd)
            commission_amount = cls._calculate_commission(net_amount_usd, commission_rule)
            
            # Security: Commission should never exceed 50% of net amount
            max_commission = net_amount_usd * D('0.50')
            if commission_amount > max_commission:
                commission_amount = max_commission.quantize(D('0.01'))
            
            # 3. Calculate Vendor Payout (net + vendor tax if applicable)
            vendor_payout_amount = net_amount_usd - commission_amount
            
            # If vendor is NOT VAT registered, platform keeps the tax
            is_vat_registered = False
            try:
                if hasattr(vendor, 'vendor_profile') and vendor.vendor_profile.tax_id:
                    is_vat_registered = True
            except:
                pass
                
            if is_vat_registered:
                vendor_payout_amount += item_tax_usd
            
            # 3. Create Transactions (Double-Entry)
            txn_vendor = Transaction.objects.create(
                destination_wallet=vendor_wallet,
                amount_base=vendor_payout_amount,
                amount_display=vendor_payout_amount,
                exchange_rate=D('1.000000'),
                currency='USD',
                transaction_type='PAYMENT',
                metadata={
                    'order_id': order.id, 
                    'order_number': order.order_number,
                    'tax_included': item_tax_usd > 0,
                    'is_vat_registered': is_vat_registered
                },
                **cls._reference_kwargs(item)
            )
            
            platform_revenue = commission_amount
            if not is_vat_registered:
                platform_revenue += item_tax_usd

            if payment_method == 'cod':
                # For COD orders, the vendor collects the full amount.
                # They owe the platform the commission and (if not VAT registered) the tax.
                # Both are tracked in platform_revenue.
                vendor_wallet.liability_balance += platform_revenue
            else:
                # Online payment: Money is in platform hands, vendor gets net in Escrow
                vendor_wallet.escrow_balance += vendor_payout_amount
                cls._create_escrow_entry(vendor_wallet, txn_vendor, vendor_payout_amount, vendor)

            vendor_wallet.save()

            # Commission & Tax to Platform
            if platform_wallet:
                Transaction.objects.create(
                    source_wallet=vendor_wallet, # Link to vendor for transparency
                    destination_wallet=platform_wallet,
                    amount_base=platform_revenue,
                    amount_display=platform_revenue,
                    exchange_rate=Decimal('1.000000'),
                    currency='USD',
                    transaction_type='COMMISSION',
                    metadata={
                        'order_id': order.id, 
                        'order_number': order.order_number,
                        'vendor_id': vendor.id, 
                        'commission': str(commission_amount), 
                        'tax': str(item_tax_usd)
                    },
                    **cls._reference_kwargs(item)
                )
                platform_wallet.available_balance += platform_revenue
                platform_wallet.save()

            # Audit log for each order item payment
            cls.log_action(
                action_type='ORDER_PAYMENT_PROCESSED',
                user=None, # System automated
                wallet=vendor_wallet,
                amount=vendor_payout_amount,
                details={
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'item_id': item.id,
                    'payout_amount': str(vendor_payout_amount),
                    'tax_amount': str(item_tax_usd),
                    'commission': str(commission_amount),
                    'payment_method': payment_method
                }
            )

    @classmethod
    @transaction.atomic
    def process_cod_settlement(cls, settlement_request, status, admin_user, admin_notes=''):
        """
        Processes a COD settlement request from a vendor.
        If approved, reduces the vendor's liability balance.
        """
        
        if settlement_request.status != 'pending':
            raise ValueError("This settlement request has already been processed.")
        
        if status == 'approved':
            wallet = settlement_request.wallet
            amount = settlement_request.amount
            
            cls.settle_cod_payment(
                vendor=settlement_request.vendor,
                amount_to_settle=amount,
                reference_obj=settlement_request,
                reference_number=settlement_request.reference_number,
            )
            
            # Log high-level audit action
            cls.log_action(
                action_type='COD_SETTLEMENT_APPROVED',
                user=admin_user,
                wallet=wallet,
                amount=amount,
                details={
                    'settlement_request_id': settlement_request.id,
                    'reference_number': settlement_request.reference_number
                }
            )

        settlement_request.status = status
        settlement_request.admin_notes = admin_notes
        settlement_request.processed_by = admin_user
        settlement_request.processed_at = timezone.now()
        settlement_request.save(update_fields=['status', 'admin_notes', 'processed_by', 'processed_at', 'updated_at'])
            
        return settlement_request

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
        elif rule.commission_type == 'fixed_amount':
            return rule.fixed_amount
        elif rule.commission_type == 'tiered':
            # Progressive tiered calculation
            total_commission = Decimal('0.00')
            remaining_amount = amount
            
            tiers = rule.tiers.all().order_by('min_amount')
            if not tiers.exists():
                # Fallback to rule's own rate if no tiers defined
                return (amount * rule.commission_rate / 100).quantize(Decimal('0.01'))
                
            for tier in tiers:
                if remaining_amount <= 0:
                    break
                    
                tier_min = tier.min_amount
                tier_max = tier.max_amount
                
                # Calculate how much of the amount falls into this tier
                if tier_max:
                    tier_size = tier_max - tier_min
                    amount_in_tier = min(remaining_amount, tier_size)
                else:
                    # Last tier (no max)
                    amount_in_tier = remaining_amount
                
                if amount_in_tier > 0:
                    tier_commission = (amount_in_tier * tier.commission_rate / 100) + tier.fixed_amount
                    total_commission += tier_commission
                    remaining_amount -= amount_in_tier
                    
            return total_commission.quantize(Decimal('0.01'))
            
        return Decimal('0.00')

    @classmethod
    @transaction.atomic
    def release_escrow_for_order(cls, order):
        """
        Sets the release date for escrow entries when an order is delivered.
        """
        from .models import Transaction, EscrowEntry
        from django.contrib.contenttypes.models import ContentType
        
        if not order.items.exists():
            return
            
        order_item_ct = ContentType.objects.get_for_model(order.items.first())
        
        # Find all pending escrow entries for this order's items
        escrow_entries = EscrowEntry.objects.filter(
            transaction__reference_content_type=order_item_ct,
            transaction__reference_id__in=order.items.values_list('id', flat=True),
            is_released=False
        )
        
        # Update release date to 3 days from NOW (Delivery date + return window)
        new_release_date = timezone.now() + timezone.timedelta(days=3)
        for entry in escrow_entries:
            entry.release_date = new_release_date
            entry.save()
            
        return escrow_entries

    @classmethod
    @transaction.atomic
    def trigger_delivery_settlement(cls, order):
        """
        Triggers financial settlement when an order is marked as delivered.
        Specifically handles COD payment recording and escrow release.
        """
        # 1. Handle COD recording
        if order.payment_method == 'cash_on_delivery':
            # Check if already recorded to avoid duplicates
            from .models import Transaction
            from django.contrib.contenttypes.models import ContentType
            
            if order.items.exists():
                order_item_ct = ContentType.objects.get_for_model(order.items.first())
                exists = Transaction.objects.filter(
                    reference_content_type=order_item_ct,
                    reference_id__in=order.items.values_list('id', flat=True),
                    transaction_type='PAYMENT'
                ).exists()

                if not exists:
                    cls.record_order_payment(order, payment_method='cod')
                
                # Always update payment status on delivery for COD if not already completed
                if order.payment_status != 'completed':
                    order.payment_status = 'completed'
                    order.save(update_fields=['payment_status'])

        # 2. Handle Escrow Release Countdown (for online payments)
        cls.release_escrow_for_order(order)

    @classmethod
    @transaction.atomic
    def settle_cod_payment(cls, vendor, amount_to_settle, reference_obj=None, reference_number=None):
        """
        MasterAdmin confirms that vendor has handed over COD cash.
        """
        vendor_wallet = cls.get_or_create_wallet(vendor)
        platform_wallet = None
        try:
            platform_wallet = cls.get_platform_wallet()
        except ValueError:
            platform_wallet = None

        if vendor_wallet.liability_balance < amount_to_settle:
            raise ValueError("Settlement amount exceeds vendor liability.")

        # Record Transaction
        Transaction.objects.create(
            source_wallet=vendor_wallet,
            destination_wallet=platform_wallet,
            amount_base=amount_to_settle,
            amount_display=amount_to_settle,
            exchange_rate=Decimal('1.000000'),
            currency=vendor_wallet.currency,
            transaction_type='COD_SETTLEMENT',
            metadata={'reference_number': reference_number} if reference_number else {},
            **cls._reference_kwargs(reference_obj)
        )

        # Update Balances
        vendor_wallet.liability_balance -= amount_to_settle
        vendor_wallet.save()

    @classmethod
    @transaction.atomic
    def reverse_transaction(cls, transaction_id, reason="Refund"):
        """
        Reverses a specific transaction (Refund/Cancellation).
        """
        original_txn = Transaction.objects.select_for_update().get(id=transaction_id)
        
        if original_txn.status == 'reversed':
            return original_txn # Already reversed
            
        # 1. Create a Reversal Transaction (Negative Entry)
        reversal_txn = Transaction.objects.create(
            source_wallet=original_txn.destination_wallet,
            destination_wallet=original_txn.source_wallet,
            amount_base=original_txn.amount_base,
            amount_display=original_txn.amount_display,
            exchange_rate=original_txn.exchange_rate,
            currency=original_txn.currency,
            transaction_type='REFUND',
            reference_content_type=original_txn.reference_content_type,
            reference_id=original_txn.reference_id,
            metadata={'original_transaction_id': original_txn.id, 'reason': reason}
        )
        
        # 2. Update Balances
        if original_txn.destination_wallet:
            # If it was a payment to vendor, check if it's still in escrow
            wallet = original_txn.destination_wallet
            escrow_entry = EscrowEntry.objects.filter(transaction=original_txn, is_released=False).first()
            
            if escrow_entry:
                wallet.escrow_balance -= original_txn.amount_base
                # We don't delete the entry, we just mark it as released
                # For now, marking as released prevents it from being matured
                escrow_entry.is_released = True 
                escrow_entry.save()
            else:
                wallet.available_balance -= original_txn.amount_base
            
            wallet.save()
            
        if original_txn.source_wallet:
            wallet = original_txn.source_wallet
            wallet.available_balance += original_txn.amount_base
            wallet.save()
            
        # 3. Mark original as reversed
        original_txn.status = 'reversed'
        original_txn.save()
        return reversal_txn

    @staticmethod
    def _create_escrow_entry(wallet, transaction, amount, vendor):
        # Set a placeholder release date far in the future (e.g., 1 year)
        # It will be updated to (Delivery Date + 3 days) once order is delivered
        release_date = timezone.now() + timezone.timedelta(days=365)
        
        return EscrowEntry.objects.create(
            wallet=wallet,
            transaction=transaction,
            amount=amount,
            release_date=release_date
        )

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
            metadata={'subscription_id': subscription_payment.subscription.id},
            **cls._reference_kwargs(subscription_payment)
        )
        
        platform_wallet.available_balance += subscription_payment.amount
        platform_wallet.save()

    @classmethod
    @transaction.atomic
    def release_matured_escrow_entries(cls, now=None):
        now = now or timezone.now()
        matured_entries = (
            EscrowEntry.objects.select_for_update()
            .filter(release_date__lte=now, is_released=False)
            .select_related('wallet', 'transaction')
        )

        count = 0
        for entry in matured_entries:
            try:
                cls._release_single_escrow_entry(entry)
                count += 1
            except Exception:
                logger.exception("Failed to release escrow entry %s", entry.id)
        return count

    @classmethod
    def _release_single_escrow_entry(cls, entry):
        entry.refresh_from_db()
        if entry.is_released:
            return False

        wallet = Wallet.objects.select_for_update().get(id=entry.wallet_id)
        amount = entry.amount

        wallet.escrow_balance -= amount
        wallet.available_balance += amount
        wallet.save(update_fields=['escrow_balance', 'available_balance', 'updated_at'])

        entry.is_released = True
        entry.save(update_fields=['is_released'])

        Transaction.objects.create(
            source_wallet=wallet,
            destination_wallet=wallet,
            amount_base=amount,
            amount_display=amount,
            exchange_rate=Decimal('1.000000'),
            currency=wallet.currency,
            transaction_type='ESCROW_RELEASE',
            metadata={'escrow_entry_id': entry.id, 'reason': 'Escrow Maturity Release'},
            reference_content_type=entry.transaction.reference_content_type,
            reference_id=entry.transaction.reference_id,
        )

        cls.log_action(
            action_type='ESCROW_RELEASED',
            user=None,
            wallet=wallet,
            amount=amount,
            details={'escrow_entry_id': entry.id, 'original_transaction': entry.transaction_id},
        )

        return True
