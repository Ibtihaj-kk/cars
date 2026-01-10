from django.db import models
from django.conf import settings
from decimal import Decimal
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator

class Wallet(models.Model):
    """
    Virtual Wallet for any entity (Vendor, MasterAdmin, or Platform Escrow).
    """
    # Links to BusinessPartner or Platform User
    owner_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    owner_id = models.PositiveIntegerField()
    owner = GenericForeignKey('owner_content_type', 'owner_id')
    
    # Balance Buckets
    available_balance = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    escrow_balance = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    liability_balance = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    ) # Specifically for COD
    
    currency = models.CharField(max_length=3, default='USD') # Base Calculation Currency
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('owner_content_type', 'owner_id')
        indexes = [
            models.Index(fields=['owner_content_type', 'owner_id']),
        ]

    def __str__(self):
        return f"Wallet for {self.owner} ({self.currency})"

class Transaction(models.Model):
    """
    The Immutable Ledger. Every financial event is a record here.
    """
    TYPES = (
        ('PAYMENT', 'Order Payment'),
        ('COMMISSION', 'Platform Commission'),
        ('PAYOUT', 'Vendor Payout'),
        ('REFUND', 'Customer Refund'),
        ('COD_SETTLEMENT', 'COD Cash Reconciliation'),
        ('SUBSCRIPTION', 'Vendor Subscription Fee'),
        ('ESCROW_RELEASE', 'Escrow Release to Available'),
        ('ADJUSTMENT', 'Manual Admin Adjustment'),
    )

    source_wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='debits', null=True, blank=True)
    destination_wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='credits', null=True, blank=True)
    
    amount_base = models.DecimalField(max_digits=15, decimal_places=2) # e.g. USD
    amount_display = models.DecimalField(max_digits=15, decimal_places=2) # e.g. SAR
    exchange_rate = models.DecimalField(max_digits=12, decimal_places=6)
    currency = models.CharField(max_length=3) # The display currency (SAR, AED, etc.)
    
    transaction_type = models.CharField(max_length=20, choices=TYPES)
    status = models.CharField(max_length=20, default='completed', choices=(
        ('completed', 'Completed'),
        ('reversed', 'Reversed'),
        ('failed', 'Failed'),
    ))
    
    # Generic link to Order, Subscription, or RefundRequest
    reference_content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    reference_id = models.PositiveIntegerField(null=True, blank=True)
    reference = GenericForeignKey('reference_content_type', 'reference_id')
    
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.transaction_type} - {self.amount_base} {self.currency}"

    @property
    def order_number(self):
        """Helper to get order number from metadata or reference."""
        if 'order_number' in self.metadata:
            return self.metadata['order_number']
        
        # Try to get from reference (OrderItem or Order)
        if self.reference:
            if hasattr(self.reference, 'order'):
                return self.reference.order.order_number
            if hasattr(self.reference, 'order_number'):
                return self.reference.order_number
        return None

class EscrowEntry(models.Model):
    """
    Tracks money waiting to be released to the Vendor's available balance.
    """
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='escrow_entries')
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    release_date = models.DateTimeField()
    is_released = models.BooleanField(default=False)
    
    class Meta:
        verbose_name_plural = "Escrow Entries"
        ordering = ['release_date']
        indexes = [
            models.Index(fields=['release_date', 'is_released']),
        ]

    def __str__(self):
        return f"Escrow {self.amount} for {self.wallet.owner} (Release: {self.release_date})"


class CODSettlementRequest(models.Model):
    """
    Request from a Vendor to settle their COD Liability.
    Vendor collects cash from customers, and must 'pay back' the platform
    to clear their liability balance.
    """
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('approved', 'Approved & Settled'),
        ('rejected', 'Rejected'),
    )
    
    vendor = models.ForeignKey('business_partners.BusinessPartner', on_delete=models.CASCADE, related_name='cod_settlements')
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    
    # Proof of payment (Bank deposit slip, etc.)
    evidence_image = models.ImageField(upload_to='finance/cod_proofs/', null=True, blank=True)
    reference_number = models.CharField(max_length=100, help_text="Bank transaction ID or Receipt number")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "COD Settlement Request"

    def __str__(self):
        return f"COD Settle Request - {self.vendor.business_name} - {self.amount}"


class FinancialAuditLog(models.Model):
    """
    Audit log for high-level financial operations and administrative changes.
    """
    ACTION_TYPES = (
        ('BALANCE_ADJUSTMENT', 'Manual Balance Adjustment'),
        ('COMMISSION_RULE_CHANGE', 'Commission Rule Change'),
        ('PAYOUT_PROCESSED', 'Payout Processed'),
        ('BATCH_PROCESSED', 'Payment Batch Processed'),
        ('COD_SETTLEMENT_APPROVED', 'COD Settlement Approved'),
        ('ESCROW_RELEASED', 'Escrow Released'),
        ('ORDER_PAYMENT_PROCESSED', 'Order Payment Processed'),
    )
    
    action_type = models.CharField(max_length=30, choices=ACTION_TYPES)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    wallet = models.ForeignKey(Wallet, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Details of the change
    details = models.JSONField(default=dict, blank=True)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.action_type} by {self.user} at {self.created_at}"
