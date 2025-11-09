from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal


class PaymentStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'
    REFUNDED = 'refunded', 'Refunded'
    CANCELLED = 'cancelled', 'Cancelled'


class PaymentMethod(models.TextChoices):
    BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
    CREDIT_CARD = 'credit_card', 'Credit Card'
    PAYPAL = 'paypal', 'PayPal'
    STRIPE = 'stripe', 'Stripe'
    CHECK = 'check', 'Check'
    CASH = 'cash', 'Cash'


class CommissionType(models.TextChoices):
    PERCENTAGE = 'percentage', 'Percentage'
    FIXED_AMOUNT = 'fixed_amount', 'Fixed Amount'
    TIERED = 'tiered', 'Tiered'


class VendorPayment(models.Model):
    """Model for tracking vendor payments and commissions."""
    
    vendor = models.ForeignKey('vendors.Vendor', on_delete=models.CASCADE, related_name='payments')
    payment_reference = models.CharField(max_length=100, unique=True)
    
    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Commission details
    commission_type = models.CharField(max_length=20, choices=CommissionType.choices, default=CommissionType.PERCENTAGE)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    
    # Payment method and status
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.BANK_TRANSFER)
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    
    # Related listings (for commission calculation)
    related_listings = models.ManyToManyField('listings.Listing', blank=True, related_name='payments')
    
    # Payment dates
    payment_date = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # Additional information
    notes = models.TextField(blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    bank_reference = models.CharField(max_length=100, blank=True)
    
    # System fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['vendor', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['payment_date', '-created_at']),
        ]
    
    def __str__(self):
        return f"Payment {self.payment_reference} - {self.vendor.business_name}"
    
    def save(self, *args, **kwargs):
        # Calculate net amount (amount - commission)
        self.net_amount = self.amount - self.commission_amount
        
        # Generate payment reference if not provided
        if not self.payment_reference:
            import uuid
            self.payment_reference = f"PAY-{uuid.uuid4().hex[:8].upper()}"
        
        super().save(*args, **kwargs)


class CommissionRule(models.Model):
    """Model for commission rules and tiers."""
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    commission_type = models.CharField(max_length=20, choices=CommissionType.choices, default=CommissionType.PERCENTAGE)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    fixed_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Tiered commission rules
    min_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    max_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Applicability
    is_active = models.BooleanField(default=True)
    applies_to_all_vendors = models.BooleanField(default=True)
    specific_vendors = models.ManyToManyField('vendors.Vendor', blank=True, related_name='commission_rules')
    
    # Date range
    effective_from = models.DateField(default=timezone.now)
    effective_to = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Commission Rules"
    
    def __str__(self):
        return f"{self.name} - {self.commission_rate}%"


class PaymentBatch(models.Model):
    """Model for batch payment processing."""
    
    batch_reference = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Batch details
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_commission = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Number of payments
    total_payments = models.IntegerField(default=0)
    processed_payments = models.IntegerField(default=0)
    failed_payments = models.IntegerField(default=0)
    
    # Status and dates
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processing_completed_at = models.DateTimeField(null=True, blank=True)
    
    # Related payments
    payments = models.ManyToManyField(VendorPayment, blank=True, related_name='batches')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Payment Batches"
    
    def __str__(self):
        return f"Batch {self.batch_reference} - {self.name}"
    
    def save(self, *args, **kwargs):
        # Generate batch reference if not provided
        if not self.batch_reference:
            import uuid
            self.batch_reference = f"BATCH-{uuid.uuid4().hex[:8].upper()}"
        
        super().save(*args, **kwargs)


class PaymentHistory(models.Model):
    """Model for tracking payment history and audit trail."""
    
    payment = models.ForeignKey(VendorPayment, on_delete=models.CASCADE, related_name='history')
    
    # Status change
    old_status = models.CharField(max_length=20, choices=PaymentStatus.choices)
    new_status = models.CharField(max_length=20, choices=PaymentStatus.choices)
    
    # Additional information
    notes = models.TextField(blank=True)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Payment Histories"
    
    def __str__(self):
        return f"{self.payment.payment_reference}: {self.old_status} → {self.new_status}"


class VendorBalance(models.Model):
    """Model for tracking vendor account balances."""
    
    vendor = models.OneToOneField('vendors.Vendor', on_delete=models.CASCADE, related_name='balance')
    
    # Current balance
    current_balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    pending_balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_earned = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Last payment information
    last_payment_date = models.DateTimeField(null=True, blank=True)
    last_payment_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # System fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Vendor Balances"
    
    def __str__(self):
        return f"{self.vendor.business_name} - Balance: ${self.current_balance}"
    
    def update_balance(self):
        """Update vendor balance based on payments."""
        completed_payments = self.vendor.payments.filter(status='completed')
        self.total_paid = completed_payments.aggregate(total=models.Sum('net_amount'))['total'] or Decimal('0.00')
        self.current_balance = self.total_earned - self.total_paid
        self.save()