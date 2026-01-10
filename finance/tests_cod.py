from django.test import TestCase
from django.contrib.auth import get_user_model
from parts.models import Order, OrderItem, Part, Category, Brand
from business_partners.models import BusinessPartner, VendorProfile
from finance.models import Wallet, Transaction
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
            sku='TEST-SKU-123'
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
            price=Decimal('115.00'), # Set Gross Price to 115
            tax_amount=Decimal('15.00')
        )

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
        # Liability = Tax (15) + Commission (10% of 100 = 10) = 25
        self.assertGreater(vendor_wallet.liability_balance, 0, "Vendor liability balance should be greater than 0 for COD")
        self.assertEqual(vendor_wallet.liability_balance, Decimal('25.00'), "Vendor liability balance should be 25.00 (Tax 15 + Commission 10)")
        
        # Verify payment status updated
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'completed', "Order payment status should be 'completed' after delivery of COD order")
