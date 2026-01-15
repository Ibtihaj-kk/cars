from django.test import TestCase
from django.contrib.auth import get_user_model
from parts.models import Order, OrderItem, Part, Category, Brand
from business_partners.models import BusinessPartner, BusinessPartnerRole, VendorProfile
from finance.models import Wallet, Transaction, CODSettlementRequest
from finance.services import FinanceService
from admin_panel.payment_models import CommissionRule
from decimal import Decimal
from django.contrib.contenttypes.models import ContentType

User = get_user_model()

from django.utils import timezone
from datetime import timedelta

class CODDeliveryTest(TestCase):
    def setUp(self):
        # Create Admin
        self.admin = User.objects.create_superuser(email='admin_test@test.com', password='password')
        
        # Create Vendor
        self.vendor_user = User.objects.create_user(email='vendor_test@test.com', password='password')
        self.vendor = BusinessPartner.objects.create(name='Test Vendor', bp_number='BP-TEST-001')
        self.vendor.user = self.vendor_user
        self.vendor.status = 'active'
        self.vendor.save(update_fields=['user', 'status'])
        BusinessPartnerRole.objects.get_or_create(business_partner=self.vendor, role_type='vendor')
        self.vendor_profile = VendorProfile.objects.create(user=self.vendor_user, business_partner=self.vendor)
        
        # Create Category and Brand
        self.category = Category.objects.create(name='Test Category')
        self.brand = Brand.objects.create(name='Test Brand')

        # Create Part
        self.part = Part.objects.create(
            name='Test Part', 
            material_description='Test Part Description',
            category=self.category,
            brand=self.brand,
            vendor=self.vendor, 
            standard_price=Decimal('100.00'),
            sku='TEST-SKU-123',
            quantity=10
        )
        
        # Create Commission Rule (10%)
        self.rule = CommissionRule.objects.create(
            name='Global 10%',
            commission_type='percentage',
            commission_rate=Decimal('10.00'),
            is_active=True,
            applies_to_all_vendors=True,
            effective_from=timezone.now().date() - timedelta(days=1)
        )

        # Create Order (COD)
        self.order = Order.objects.create(
            order_number='ORD-TEST-123',
            total_price=Decimal('115.00'), # 100 + 15% tax
            tax_amount=Decimal('15.00'),
            payment_method='cash_on_delivery',
            status='pending',
            payment_status='pending'
        )
        self.order_item = OrderItem.objects.create(
            order=self.order,
            part=self.part,
            quantity=1,
            price=Decimal('100.00'),
            tax_amount=Decimal('15.00')
        )
        # Reserve inventory to avoid IntegrityError during delivery
        self.order.reserve_inventory()

    def test_cod_delivery_triggers_finance(self):
        # Mark as delivered
        self.order.status = 'delivered'
        self.order.save()
        
        # Check if Wallet exists and has liability
        vendor_wallet = FinanceService.get_or_create_wallet(self.vendor)
        
        # Verify transaction exists for the item
        order_item_ct = ContentType.objects.get_for_model(self.order_item)
        transactions = Transaction.objects.filter(
            reference_content_type=order_item_ct,
            reference_id=self.order_item.id,
            transaction_type='PAYMENT'
        )
        
        self.assertTrue(transactions.exists(), "Transaction should be created for the order item")
        
        # Verify liability balance increased
        # Liability = Tax (15) ONLY (Commission 10 is sent directly to platform wallet)
        self.assertGreater(vendor_wallet.liability_balance, 0, "Vendor liability balance should be greater than 0 for COD")
        self.assertEqual(vendor_wallet.liability_balance, Decimal('15.00'), "Vendor liability balance should be 15.00 (Tax only)")
        
        # Verify payment status updated
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'completed', "Order payment status should be 'completed' after delivery of COD order")

    def test_cod_delivery_uses_dealer_when_part_vendor_missing(self):
        part_no_vendor = Part.objects.create(
            name='Test Part 2',
            material_description='Test Part Description 2',
            category=self.category,
            brand=self.brand,
            dealer=self.vendor_user,
            standard_price=Decimal('100.00'),
            sku='TEST-SKU-456',
            quantity=10
        )

        order = Order.objects.create(
            order_number='ORD-TEST-456',
            total_price=Decimal('115.00'),
            tax_amount=Decimal('15.00'),
            payment_method='cash_on_delivery',
            status='pending',
            payment_status='pending'
        )
        order_item = OrderItem.objects.create(
            order=order,
            part=part_no_vendor,
            quantity=1,
            price=Decimal('100.00'),
            tax_amount=Decimal('15.00')
        )
        # Reserve inventory to avoid IntegrityError during delivery
        order.reserve_inventory()

        order.status = 'delivered'
        order.save()

        vendor_wallet = FinanceService.get_or_create_wallet(self.vendor)

        order_item_ct = ContentType.objects.get_for_model(order_item)
        transactions = Transaction.objects.filter(
            reference_content_type=order_item_ct,
            reference_id=order_item.id,
            transaction_type='PAYMENT'
        )
        self.assertTrue(transactions.exists(), "Transaction should be created for the order item")
        self.assertEqual(vendor_wallet.liability_balance, Decimal('15.00'))

    def test_cod_settlement_does_not_double_platform_wallet(self):
        platform_wallet = FinanceService.get_platform_wallet()
        self.assertEqual(platform_wallet.available_balance, Decimal('0.00'))

        self.order.status = 'delivered'
        self.order.save()

        vendor_wallet = FinanceService.get_or_create_wallet(self.vendor)
        platform_wallet.refresh_from_db()

        self.assertEqual(vendor_wallet.liability_balance, Decimal('15.00'))
        self.assertEqual(platform_wallet.available_balance, Decimal('25.00'))

        settlement_req = CODSettlementRequest.objects.create(
            vendor=self.vendor,
            wallet=vendor_wallet,
            amount=Decimal('15.00'),
            reference_number='SETTLE-REF-1',
        )

        FinanceService.process_cod_settlement(settlement_req, 'approved', self.admin, '')

        vendor_wallet.refresh_from_db()
        platform_wallet.refresh_from_db()

        self.assertEqual(vendor_wallet.liability_balance, Decimal('0.00'))
        self.assertEqual(platform_wallet.available_balance, Decimal('25.00'))

    def test_vendor_wallet_view_total_earnings_includes_cod_cash(self):
        self.order.status = 'delivered'
        self.order.save()

        self.client.force_login(self.vendor_user)
        response = self.client.get('/finance/vendor/wallet/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('total_earnings', response.context)
        self.assertIn('cod_cash_received', response.context)
        self.assertEqual(response.context['cod_cash_received'], Decimal('90.00'))
        self.assertEqual(response.context['total_earnings'], Decimal('90.00'))
