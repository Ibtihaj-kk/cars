# E-Commerce System Completion & Fix Plan
## YallaMotor Multi-Vendor Auto Parts Platform

**Generated**: November 15, 2025  
**Status**: Comprehensive Analysis Complete  
**Priority**: Critical - Production Readiness

---

## 📊 Executive Summary

### Current State Assessment
After analyzing the entire codebase against the `auto_parts.md` requirements document, here's the comprehensive status:

**Overall Completion**: ~65-70%

| Module | Status | Priority | Est. Time |
|--------|--------|----------|-----------|
| Vendor Management | 85% ✅ | HIGH | 2 weeks |
| Product Catalog | 90% ✅ | MEDIUM | 1 week |
| E-Commerce Engine | 75% ⚠️ | HIGH | 3 weeks |
| Inventory Management | 80% ✅ | MEDIUM | 2 weeks |
| Payment & Commission | 40% ❌ | CRITICAL | 4 weeks |
| Analytics & Reporting | 50% ⚠️ | MEDIUM | 3 weeks |
| Communication System | 45% ⚠️ | MEDIUM | 3 weeks |
| Admin Control Panel | 70% ⚠️ | HIGH | 2 weeks |

---

## 🔍 Detailed Gap Analysis

### 1. CRITICAL ISSUES FOUND ❌

#### Issue 1.1: Payment System Not Implemented
**Location**: `parts/models.py`, `parts/views.py`  
**Severity**: CRITICAL  
**Impact**: Cannot process payments or calculate commissions

**What's Missing**:
- No Payment model
- No payment gateway integration (Stripe/PayPal)
- No commission calculation logic
- No vendor payout system
- No split payment functionality

**Required Models**:
```python
class Payment(models.Model):
    """Missing - needs to be created"""
    order = ForeignKey(Order)
    vendor = ForeignKey(BusinessPartner)
    amount = DecimalField()
    commission_amount = DecimalField()
    net_amount = DecimalField()
    payment_method = CharField()
    transaction_id = CharField()
    gateway_response = JSONField()
    status = CharField()
    
class CommissionRate(models.Model):
    """Missing - needs to be created"""
    vendor = ForeignKey(BusinessPartner, null=True)
    category = ForeignKey(Category, null=True)
    rate_percentage = DecimalField()
    fixed_amount = DecimalField()
    effective_from = DateField()
    
class VendorPayout(models.Model):
    """Missing - needs to be created"""
    vendor = ForeignKey(BusinessPartner)
    period_start = DateField()
    period_end = DateField()
    total_sales = DecimalField()
    commission_deducted = DecimalField()
    payout_amount = DecimalField()
    status = CharField()
```

**Action Required**:
1. Create Payment, CommissionRate, VendorPayout models
2. Implement Stripe payment gateway integration
3. Create commission calculation engine
4. Build payout request and approval workflow

---

#### Issue 1.2: Order Model Missing Payment Fields
**Location**: `parts/models.py` - Line 824  
**Severity**: HIGH  
**Impact**: Cannot track payment status or methods

**What's Missing**:
```python
# Current Order model lacks:
payment_method = CharField()  # Missing
payment_status = CharField()  # Missing
payment_transaction_id = CharField()  # Missing
paid_at = DateTimeField()  # Missing
```

**Action Required**:
1. Add payment tracking fields to Order model
2. Create migration
3. Update order views to handle payment info

---

#### Issue 1.3: Commission System Completely Missing
**Location**: Entire `parts` app  
**Severity**: CRITICAL  
**Impact**: Core business model cannot function

**What's Missing**:
- Commission calculation logic
- Vendor-specific commission rates
- Category-based commission rates
- Commission reporting
- Automated commission deduction
- Payout scheduling

**Action Required**:
1. Create `parts/commission_manager.py`
2. Implement commission calculation algorithms
3. Add commission admin interface
4. Create commission reporting views

---

### 2. HIGH PRIORITY ISSUES ⚠️

#### Issue 2.1: Checkout Flow Incomplete
**Location**: `parts/views.py` - Lines 1476-1650  
**Severity**: HIGH  
**Impact**: Users cannot complete purchases smoothly

**Problems Found**:
1. Multi-step checkout exists but lacks proper state management
2. Payment method selection not integrated with gateways
3. Order confirmation doesn't trigger inventory deduction reliably
4. No order email confirmations
5. Guest checkout has validation gaps

**Current Flow**:
```
Step 1: Order Summary ✅
Step 2: Shipping Info ✅  
Step 3: Payment Method ⚠️ (Not integrated)
Confirmation ⚠️ (Missing email)
```

**Required Fix**:
```python
# parts/views.py - checkout_step3_payment_method needs:
1. Payment gateway initialization
2. Token generation for security
3. Transaction processing
4. Webhook handling for payment confirmation
5. Email notification trigger
6. Inventory deduction on payment success
```

**Action Required**:
1. Complete payment integration in Step 3
2. Add payment webhook endpoint
3. Implement email notification system
4. Add proper error handling
5. Test full checkout flow

---

#### Issue 2.2: Vendor Dashboard Missing Key Features
**Location**: `parts/views.py` - DealerDashboardView (Line 652)  
**Severity**: HIGH  
**Impact**: Vendors cannot effectively manage business

**What's Missing**:
- Real-time sales metrics dashboard
- Product performance analytics
- Customer insights
- Revenue vs commission breakdown
- Payout history and requests
- Performance score tracking

**Current Implementation**:
```python
class DealerDashboardView(DealerAdminRequiredMixin, TemplateView):
    """Basic dashboard - needs enhancement"""
    # Missing: Advanced analytics
    # Missing: Interactive charts
    # Missing: Export functionality
    # Missing: Date range filtering
```

**Action Required**:
1. Create enhanced dashboard with Chart.js
2. Add date range filters
3. Implement export to CSV/PDF
4. Add real-time notifications
5. Create mobile-responsive layout

---

#### Issue 2.3: Admin Control Panel Incomplete
**Location**: `admin_panel` app  
**Severity**: HIGH  
**Impact**: Platform administrators lack oversight tools

**What's Missing**:
- Financial oversight dashboard
- Vendor performance monitoring
- Commission management interface
- Platform-wide analytics
- Dispute resolution tools
- System health monitoring

**Action Required**:
1. Create comprehensive admin dashboard
2. Build vendor approval workflow UI
3. Implement financial reporting
4. Add system monitoring tools
5. Create commission management interface

---

### 3. MEDIUM PRIORITY ISSUES 🔧

#### Issue 3.1: Search Functionality Basic
**Location**: `parts/views.py` - PartListView (Line 69)  
**Severity**: MEDIUM  
**Impact**: Users have difficulty finding products

**Current State**:
- Basic keyword search exists
- Some filters implemented
- No advanced search UI
- No search suggestions
- No recently searched

**Action Required**:
1. Implement Elasticsearch for better search
2. Add autocomplete/suggestions
3. Create advanced filter UI
4. Add search history
5. Implement faceted search

---

#### Issue 3.2: Cart Management Inconsistent
**Location**: `parts/views.py` - Lines 1186-1400  
**Severity**: MEDIUM  
**Impact**: Cart experience could be smoother

**Problems**:
- Session cart for anonymous users
- Database cart for authenticated users
- No smooth migration between states
- Cart count calculation inconsistent
- No cart expiry handling

**Action Required**:
1. Unified cart management system
2. Auto-migrate session cart on login
3. Implement cart expiry
4. Add cart sharing feature
5. Improve cart validation

---

#### Issue 3.3: Wishlist Feature Missing
**Location**: Not implemented  
**Severity**: MEDIUM  
**Impact**: Reduced user engagement

**What's Missing**:
- Wishlist model
- Wishlist views
- Wishlist UI
- Email reminders for wishlist items
- Price drop notifications

**Action Required**:
1. Create Wishlist and WishlistItem models
2. Implement add/remove functionality
3. Create wishlist page UI
4. Add email notification system
5. Implement price tracking

---

#### Issue 3.4: Product Comparison Not Available
**Location**: Not implemented  
**Severity**: MEDIUM  
**Impact**: Users can't compare products easily

**Action Required**:
1. Create comparison session storage
2. Build comparison view
3. Create comparison UI template
4. Add comparison widget
5. Implement print/export comparison

---

#### Issue 3.5: Bulk Operations Limited
**Location**: `parts/views.py` - CSVUploadView (Line 913)  
**Severity**: MEDIUM  
**Impact**: Vendors struggle with large catalogs

**Current State**:
- Basic CSV upload exists
- Limited validation
- No progress tracking
- No bulk edit interface
- No bulk delete

**Action Required**:
1. Enhanced CSV upload with validation
2. Add Excel support
3. Implement bulk edit UI
4. Create bulk operations API
5. Add progress indicators

---

### 4. LOW PRIORITY / NICE-TO-HAVE ✨

#### Issue 4.1: Analytics Dashboard Basic
**Location**: `analytics` app  
**Severity**: LOW  
**Impact**: Limited business intelligence

**Action Required**:
1. Implement advanced charts
2. Add predictive analytics
3. Create custom report builder
4. Implement data export
5. Add scheduled reports

---

#### Issue 4.2: Communication Features Limited
**Location**: `notifications` app  
**Severity**: LOW  
**Impact**: Reduced user engagement

**Action Required**:
1. Implement SMS notifications
2. Add push notifications
3. Create live chat
4. Build knowledge base
5. Implement ticketing system

---

## 🛠️ Implementation Roadmap

### Phase 1: Critical Foundation (Weeks 1-4)
**Goal**: Make platform functional for basic transactions

#### Week 1-2: Payment System
**Tasks**:
1. Create Payment, CommissionRate, VendorPayout models
2. Write migrations
3. Integrate Stripe payment gateway
4. Implement webhook handlers
5. Add payment processing to checkout
6. Test payment flow end-to-end

**Files to Create**:
```
parts/
├── models.py (add Payment, CommissionRate, VendorPayout)
├── payment_gateways.py (NEW)
├── commission_manager.py (NEW)
├── webhooks.py (NEW)
└── migrations/00XX_add_payment_models.py

templates/parts/checkout/
├── payment_methods.html (UPDATE)
└── payment_confirmation.html (NEW)

static/js/
└── payment-integration.js (NEW)
```

**Testing Checklist**:
- [ ] Payment gateway connects successfully
- [ ] Commission calculates correctly
- [ ] Payment splits to vendors
- [ ] Webhooks handle all scenarios
- [ ] Refunds process correctly

---

#### Week 2-3: Enhanced Vendor Dashboard
**Tasks**:
1. Create vendor analytics views
2. Implement interactive charts
3. Add real-time metrics
4. Build payout request system
5. Create mobile-responsive design

**Files to Create**:
```
business_partners/
├── vendor_dashboard_views.py (UPDATE)
├── vendor_analytics_views.py (NEW)
└── vendor_payout_views.py (NEW)

templates/business_partners/
├── vendor_dashboard_enhanced.html (NEW)
├── vendor_analytics.html (NEW)
├── vendor_payout_history.html (NEW)
└── partials/
    ├── sales_chart.html (NEW)
    ├── inventory_alerts.html (NEW)
    └── recent_orders.html (NEW)

static/js/
├── vendor-dashboard.js (NEW)
└── chart-configs.js (NEW)
```

---

#### Week 3-4: Complete Checkout & Order Flow
**Tasks**:
1. Finalize payment integration in checkout
2. Implement email notifications
3. Add order tracking
4. Fix inventory deduction
5. Test guest and authenticated checkout

**Files to Update**:
```
parts/
├── views.py (checkout functions)
├── email_notifications.py (NEW)
└── tasks.py (async email sending)

templates/parts/
├── checkout/ (all templates)
└── emails/
    ├── order_confirmation.html (NEW)
    ├── shipping_update.html (NEW)
    └── payment_receipt.html (NEW)
```

---

### Phase 2: Core Features (Weeks 5-8)
**Goal**: Complete essential e-commerce functionality

#### Week 5-6: Commission Management
**Tasks**:
1. Build commission calculation engine
2. Create commission admin interface
3. Implement payout system
4. Add commission reporting
5. Test commission accuracy

**Files to Create**:
```
parts/
├── commission_manager.py (ENHANCE)
├── payout_manager.py (NEW)
└── commission_reports.py (NEW)

admin_panel/
├── commission_views.py (NEW)
└── payout_approval_views.py (NEW)

templates/admin_panel/
├── commission_management.html (NEW)
├── commission_rates.html (NEW)
└── payout_requests.html (NEW)
```

---

#### Week 6-7: Analytics & Reporting
**Tasks**:
1. Create vendor analytics dashboard
2. Implement admin analytics
3. Build custom report generator
4. Add data export functionality
5. Create scheduled reports

**Files to Create**:
```
analytics/
├── vendor_analytics.py (ENHANCE)
├── platform_analytics.py (NEW)
├── report_generator.py (NEW)
└── export_manager.py (NEW)

templates/analytics/
├── vendor_performance.html (NEW)
├── sales_reports.html (NEW)
└── custom_reports.html (NEW)
```

---

#### Week 7-8: Inventory Management Enhancement
**Tasks**:
1. Implement bulk inventory updates
2. Add inventory forecasting
3. Create reorder automation
4. Build stock alerts system
5. Add supplier management

**Files to Create**:
```
parts/
├── inventory_manager.py (ENHANCE)
├── forecasting.py (NEW)
└── reorder_automation.py (NEW)

templates/parts/
├── bulk_inventory_update.html (NEW)
├── inventory_forecast.html (NEW)
└── reorder_alerts.html (NEW)
```

---

### Phase 3: User Experience (Weeks 9-12)
**Goal**: Enhance usability and add advanced features

#### Week 9: Customer Features
**Tasks**:
1. Implement wishlist
2. Create product comparison
3. Add recently viewed
4. Build Q&A system
5. Implement reviews enhancement

**Files to Create**:
```
parts/
├── models.py (add Wishlist models)
├── wishlist_views.py (NEW)
├── comparison_views.py (NEW)
└── qa_views.py (NEW)

templates/parts/
├── wishlist.html (NEW)
├── compare_products.html (NEW)
└── product_qa.html (NEW)
```

---

#### Week 10: Vendor Tools
**Tasks**:
1. Add advanced product management
2. Implement performance tracking
3. Create store customization
4. Build marketing tools
5. Add customer insights

---

#### Week 11: Platform Features
**Tasks**:
1. Implement advanced search
2. Add email marketing
3. Create loyalty program
4. Build referral system
5. Implement SEO tools

---

#### Week 12: Testing & Optimization
**Tasks**:
1. Performance optimization
2. Security audit
3. Load testing
4. Bug fixes
5. Documentation
6. Deployment preparation

---

## 📋 Immediate Action Items (Next 7 Days)

### Day 1: Assessment & Setup
- [ ] Review all existing code thoroughly
- [ ] Document all bugs found
- [ ] Set up development branch
- [ ] Create detailed task board
- [ ] Estimate accurate timelines

### Day 2-3: Payment Foundation
- [ ] Create Payment model
- [ ] Create CommissionRate model
- [ ] Create VendorPayout model
- [ ] Write migrations
- [ ] Test migrations on dev database

### Day 4-5: Stripe Integration
- [ ] Set up Stripe account
- [ ] Install Stripe SDK
- [ ] Create payment gateway wrapper
- [ ] Implement webhook endpoint
- [ ] Test payment processing

### Day 6-7: Checkout Integration
- [ ] Add payment to Step 3
- [ ] Implement error handling
- [ ] Add loading states
- [ ] Test full checkout flow
- [ ] Fix any blocking issues

---

## 🔧 Code Templates for Quick Start

### 1. Payment Model
```python
# parts/models.py - Add this

class Payment(models.Model):
    """Payment tracking for orders"""
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_METHODS = [
        ('stripe', 'Credit/Debit Card (Stripe)'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash_on_delivery', 'Cash on Delivery'),
    ]
    
    # Relationships
    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE,
        related_name='payments'
    )
    vendor = models.ForeignKey(
        'business_partners.BusinessPartner',
        on_delete=models.PROTECT,
        related_name='payments',
        null=True,
        blank=True,
        help_text="Vendor receiving this payment portion"
    )
    
    # Payment details
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Total payment amount"
    )
    commission_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Commission deducted"
    )
    net_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Net amount to vendor (amount - commission)"
    )
    
    # Payment processing
    payment_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHODS
    )
    transaction_id = models.CharField(
        max_length=255,
        unique=True,
        blank=True,
        null=True,
        help_text="External payment gateway transaction ID"
    )
    gateway_response = models.JSONField(
        blank=True,
        null=True,
        help_text="Full response from payment gateway"
    )
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default='pending'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    
    # Refund tracking
    refund_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    refunded_at = models.DateTimeField(blank=True, null=True)
    refund_reason = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'status']),
            models.Index(fields=['vendor', 'status']),
            models.Index(fields=['transaction_id']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"Payment {self.transaction_id} - {self.order.order_number}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate net amount
        self.net_amount = self.amount - self.commission_amount
        super().save(*args, **kwargs)
    
    @property
    def is_successful(self):
        return self.status == 'completed'
    
    @property
    def commission_percentage(self):
        if self.amount > 0:
            return (self.commission_amount / self.amount) * 100
        return Decimal('0.00')


class CommissionRate(models.Model):
    """Commission rate configuration"""
    
    # Optional specificity
    vendor = models.ForeignKey(
        'business_partners.BusinessPartner',
        on_delete=models.CASCADE,
        related_name='commission_rates',
        null=True,
        blank=True,
        help_text="Vendor-specific rate (leave blank for default)"
    )
    category = models.ForeignKey(
        'parts.Category',
        on_delete=models.CASCADE,
        related_name='commission_rates',
        null=True,
        blank=True,
        help_text="Category-specific rate (leave blank for all categories)"
    )
    
    # Commission configuration
    rate_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('10.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Commission percentage"
    )
    fixed_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Fixed commission amount per transaction"
    )
    
    # Validity period
    effective_from = models.DateField(
        default=timezone.now,
        help_text="Start date for this rate"
    )
    effective_until = models.DateField(
        null=True,
        blank=True,
        help_text="End date (leave blank for ongoing)"
    )
    
    # Metadata
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_commission_rates'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Commission Rate"
        verbose_name_plural = "Commission Rates"
        ordering = ['-effective_from']
        indexes = [
            models.Index(fields=['vendor', 'category', 'effective_from']),
            models.Index(fields=['is_active', 'effective_from']),
        ]
    
    def __str__(self):
        parts = []
        if self.vendor:
            parts.append(f"Vendor: {self.vendor.name}")
        if self.category:
            parts.append(f"Category: {self.category.name}")
        if not parts:
            parts.append("Default Rate")
        return f"{' - '.join(parts)}: {self.rate_percentage}%"
    
    def clean(self):
        # Validate date range
        if self.effective_until and self.effective_until < self.effective_from:
            raise ValidationError("Effective until date must be after effective from date")
    
    def is_currently_effective(self):
        """Check if rate is currently effective"""
        today = timezone.now().date()
        if self.effective_until:
            return self.effective_from <= today <= self.effective_until
        return self.effective_from <= today


class VendorPayout(models.Model):
    """Vendor payout tracking"""
    
    PAYOUT_STATUS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('processing', 'Processing'),
        ('paid', 'Paid'),
        ('rejected', 'Rejected'),
        ('on_hold', 'On Hold'),
    ]
    
    # Relationships
    vendor = models.ForeignKey(
        'business_partners.BusinessPartner',
        on_delete=models.CASCADE,
        related_name='payouts'
    )
    
    # Period information
    period_start = models.DateField(help_text="Payout period start date")
    period_end = models.DateField(help_text="Payout period end date")
    
    # Financial details
    total_sales = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total sales for the period"
    )
    commission_deducted = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total commission deducted"
    )
    payout_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Net amount to be paid to vendor"
    )
    
    # Processing
    status = models.CharField(
        max_length=20,
        choices=PAYOUT_STATUS,
        default='pending'
    )
    payment_method = models.CharField(max_length=50, blank=True)
    transaction_reference = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Bank transfer or payment reference"
    )
    
    # Additional charges/deductions
    adjustment_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Any adjustments (positive or negative)"
    )
    adjustment_reason = models.TextField(blank=True, null=True)
    
    # Admin tracking
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_payouts'
    )
    notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Vendor Payout"
        verbose_name_plural = "Vendor Payouts"
        ordering = ['-created_at']
        unique_together = ['vendor', 'period_start', 'period_end']
        indexes = [
            models.Index(fields=['vendor', 'status']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['period_start', 'period_end']),
        ]
    
    def __str__(self):
        return f"Payout to {self.vendor.name} - {self.period_start} to {self.period_end}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate payout amount
        self.payout_amount = self.total_sales - self.commission_deducted + self.adjustment_amount
        super().save(*args, **kwargs)
    
    def approve(self, approved_by_user):
        """Approve payout for processing"""
        self.status = 'approved'
        self.approved_by = approved_by_user
        self.approved_at = timezone.now()
        self.save()
    
    def mark_as_paid(self, transaction_reference):
        """Mark payout as paid"""
        self.status = 'paid'
        self.transaction_reference = transaction_reference
        self.paid_at = timezone.now()
        self.save()
    
    def reject(self, reason):
        """Reject payout"""
        self.status = 'rejected'
        self.notes = reason
        self.save()
```

### 2. Commission Manager
```python
# parts/commission_manager.py - NEW FILE

from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from .models import Payment, CommissionRate, VendorPayout, Order, OrderItem

class CommissionManager:
    """
    Handles all commission-related calculations and operations.
    Central business logic for commission processing.
    """
    
    @staticmethod
    def get_applicable_commission_rate(vendor, category=None, date=None):
        """
        Get the most specific applicable commission rate.
        
        Priority order:
        1. Vendor + Category specific
        2. Vendor specific (all categories)
        3. Category specific (all vendors)
        4. Platform default
        
        Args:
            vendor: BusinessPartner instance
            category: Category instance (optional)
            date: Date to check (default: today)
        
        Returns:
            CommissionRate instance or None
        """
        if date is None:
            date = timezone.now().date()
        
        # Try vendor + category specific
        if vendor and category:
            rate = CommissionRate.objects.filter(
                vendor=vendor,
                category=category,
                is_active=True,
                effective_from__lte=date
            ).filter(
                models.Q(effective_until__isnull=True) | 
                models.Q(effective_until__gte=date)
            ).order_by('-effective_from').first()
            
            if rate:
                return rate
        
        # Try vendor specific
        if vendor:
            rate = CommissionRate.objects.filter(
                vendor=vendor,
                category__isnull=True,
                is_active=True,
                effective_from__lte=date
            ).filter(
                models.Q(effective_until__isnull=True) | 
                models.Q(effective_until__gte=date)
            ).order_by('-effective_from').first()
            
            if rate:
                return rate
        
        # Try category specific
        if category:
            rate = CommissionRate.objects.filter(
                vendor__isnull=True,
                category=category,
                is_active=True,
                effective_from__lte=date
            ).filter(
                models.Q(effective_until__isnull=True) | 
                models.Q(effective_until__gte=date)
            ).order_by('-effective_from').first()
            
            if rate:
                return rate
        
        # Platform default
        rate = CommissionRate.objects.filter(
            vendor__isnull=True,
            category__isnull=True,
            is_active=True,
            effective_from__lte=date
        ).filter(
            models.Q(effective_until__isnull=True) | 
            models.Q(effective_until__gte=date)
        ).order_by('-effective_from').first()
        
        return rate
    
    @staticmethod
    def calculate_commission(amount, vendor, category=None):
        """
        Calculate commission for a given amount.
        
        Args:
            amount: Transaction amount (Decimal)
            vendor: BusinessPartner instance
            category: Category instance (optional)
        
        Returns:
            Decimal: Commission amount
        """
        rate = CommissionManager.get_applicable_commission_rate(vendor, category)
        
        if not rate:
            # No commission if no rate found
            return Decimal('0.00')
        
        # Calculate percentage-based commission
        commission = amount * (rate.rate_percentage / Decimal('100.00'))
        
        # Add fixed amount if configured
        if rate.fixed_amount:
            commission += rate.fixed_amount
        
        # Ensure commission doesn't exceed amount
        return min(commission, amount)
    
    @staticmethod
    @transaction.atomic
    def process_order_payments(order):
        """
        Process payments for an order, splitting by vendor and calculating commissions.
        
        Args:
            order: Order instance
        
        Returns:
            list: List of created Payment instances
        """
        payments = []
        
        # Group order items by vendor
        from collections import defaultdict
        vendor_items = defaultdict(list)
        
        for item in order.items.select_related('part__vendor', 'part__category'):
            if item.part.vendor:
                vendor_items[item.part.vendor].append(item)
        
        # Create payments for each vendor
        for vendor, items in vendor_items.items():
            # Calculate vendor's portion
            vendor_amount = sum(item.total_price for item in items)
            
            # Calculate total commission for this vendor
            total_commission = Decimal('0.00')
            for item in items:
                commission = CommissionManager.calculate_commission(
                    item.total_price,
                    vendor,
                    item.part.category
                )
                total_commission += commission
            
            # Create payment record
            payment = Payment.objects.create(
                order=order,
                vendor=vendor,
                amount=vendor_amount,
                commission_amount=total_commission,
                net_amount=vendor_amount - total_commission,
                payment_method=order.payment_method if hasattr(order, 'payment_method') else 'unknown',
                status='pending'
            )
            payments.append(payment)
        
        return payments
    
    @staticmethod
    def generate_vendor_payout(vendor, period_start, period_end):
        """
        Generate payout record for a vendor for a given period.
        
        Args:
            vendor: BusinessPartner instance
            period_start: Start date (datetime.date)
            period_end: End date (datetime.date)
        
        Returns:
            VendorPayout instance
        """
        # Get all completed payments for vendor in period
        payments = Payment.objects.filter(
            vendor=vendor,
            status='completed',
            processed_at__date__gte=period_start,
            processed_at__date__lte=period_end
        )
        
        # Calculate totals
        total_sales = sum(p.amount for p in payments)
        total_commission = sum(p.commission_amount for p in payments)
        
        # Create or update payout record
        payout, created = VendorPayout.objects.get_or_create(
            vendor=vendor,
            period_start=period_start,
            period_end=period_end,
            defaults={
                'total_sales': total_sales,
                'commission_deducted': total_commission,
                'payout_amount': total_sales - total_commission,
                'status': 'pending'
            }
        )
        
        if not created:
            # Update existing payout
            payout.total_sales = total_sales
            payout.commission_deducted = total_commission
            payout.payout_amount = total_sales - total_commission
            payout.save()
        
        return payout
    
    @staticmethod
    def get_vendor_commission_summary(vendor, start_date=None, end_date=None):
        """
        Get commission summary for a vendor.
        
        Returns dict with:
        - total_sales
        - total_commission
        - commission_percentage
        - payment_count
        """
        payments_query = Payment.objects.filter(vendor=vendor, status='completed')
        
        if start_date:
            payments_query = payments_query.filter(processed_at__date__gte=start_date)
        if end_date:
            payments_query = payments_query.filter(processed_at__date__lte=end_date)
        
        from django.db.models import Sum, Count, Avg
        
        summary = payments_query.aggregate(
            total_sales=Sum('amount'),
            total_commission=Sum('commission_amount'),
            payment_count=Count('id'),
            avg_commission_pct=Avg('commission_amount') / Avg('amount') * 100
        )
        
        return {
            'total_sales': summary['total_sales'] or Decimal('0.00'),
            'total_commission': summary['total_commission'] or Decimal('0.00'),
            'commission_percentage': summary['avg_commission_pct'] or Decimal('0.00'),
            'payment_count': summary['payment_count'] or 0
        }
```

---

## ✅ Testing Checklist

### Payment System Testing
- [ ] Stripe test mode configured
- [ ] Payment processing successful
- [ ] Commission calculated correctly
- [ ] Payment splits to vendors
- [ ] Webhooks handle all events
- [ ] Failed payments handled gracefully
- [ ] Refunds process correctly
- [ ] Payment history displays correctly

### Checkout Flow Testing
- [ ] Guest checkout works
- [ ] Authenticated checkout works
- [ ] Cart migration on login works
- [ ] Order confirmation emails send
- [ ] Inventory deducts correctly
- [ ] Order status updates properly
- [ ] Multiple vendors handled correctly

### Vendor Dashboard Testing
- [ ] Sales metrics accurate
- [ ] Charts display correctly
- [ ] Payout requests work
- [ ] Product management functional
- [ ] Order management functional
- [ ] Mobile responsive

### Admin Panel Testing
- [ ] Vendor approval workflow works
- [ ] Commission management functional
- [ ] Financial reports accurate
- [ ] Payout approval works
- [ ] System monitoring active

---

## 📚 Documentation Requirements

1. **API Documentation**
   - Payment endpoints
   - Webhook endpoints
   - Commission calculation logic

2. **User Guides**
   - Vendor onboarding guide
   - Product management guide
   - Order fulfillment guide
   - Payout request guide

3. **Admin Guides**
   - Vendor approval process
   - Commission rate management
   - Payout processing
   - Dispute resolution

4. **Developer Documentation**
   - Architecture overview
   - Database schema
   - API integration guide
   - Testing procedures

---

## 🎯 Success Criteria

### Technical
- [ ] All models created and migrated
- [ ] Payment gateway integrated
- [ ] Commission system automated
- [ ] All views functional
- [ ] All templates responsive
- [ ] No critical bugs
- [ ] Performance acceptable (<2s page load)

### Business
- [ ] Vendors can register
- [ ] Vendors can list products
- [ ] Customers can purchase
- [ ] Payments process automatically
- [ ] Commissions calculate correctly
- [ ] Payouts are trackable
- [ ] Admin has oversight

---

**Document Owner**: Development Team  
**Last Updated**: November 15, 2025  
**Next Review**: After Phase 1 Completion
