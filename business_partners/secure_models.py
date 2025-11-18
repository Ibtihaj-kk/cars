"""
Secure models with encrypted fields for sensitive data.
Replace the existing VendorProfile with this secure version.
"""
from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django_cryptography.fields import encrypt
from decimal import Decimal
from .models import BusinessPartner


class SecureVendorProfile(models.Model):
    """
    Vendor profile with encrypted sensitive data.
    
    MIGRATION REQUIRED:
    1. Create this model
    2. Migrate data from VendorProfile
    3. Delete old VendorProfile
    4. Rename this to VendorProfile
    """
    
    PAYMENT_TERMS = [
        ('net_15', 'Net 15 days'),
        ('net_30', 'Net 30 days'),
        ('net_45', 'Net 45 days'),
        ('net_60', 'Net 60 days'),
        ('cod', 'Cash on Delivery'),
        ('prepaid', 'Prepaid'),
    ]
    
    business_partner = models.OneToOneField(
        BusinessPartner, 
        on_delete=models.CASCADE, 
        related_name='secure_vendor_profile'
    )
    payment_terms = models.CharField(
        max_length=20, 
        choices=PAYMENT_TERMS, 
        default='net_30'
    )
    
    # 🔒 ENCRYPTED FIELDS
    bank_name = encrypt(models.CharField(
        max_length=200, 
        blank=True,
        help_text="Bank name (encrypted)"
    ))
    bank_branch = encrypt(models.CharField(
        max_length=200, 
        blank=True,
        help_text="Bank branch (encrypted)"
    ))
    account_holder_name = encrypt(models.CharField(
        max_length=200, 
        blank=True,
        help_text="Account holder name (encrypted)"
    ))
    account_number = encrypt(models.CharField(
        max_length=50, 
        blank=True,
        help_text="Bank account number (encrypted)"
    ))
    iban = encrypt(models.CharField(
        max_length=34, 
        blank=True,
        help_text="IBAN (encrypted)"
    ))
    swift_code = encrypt(models.CharField(
        max_length=11, 
        blank=True,
        help_text="SWIFT/BIC code (encrypted)"
    ))
    tax_id = encrypt(models.CharField(
        max_length=50, 
        blank=True,
        help_text="Tax ID (encrypted)"
    ))
    
    # Non-encrypted fields
    vendor_rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('5.00'))],
        default=Decimal('0.00'),
        help_text="Vendor rating from 0.00 to 5.00"
    )
    preferred_currency = models.CharField(max_length=3, default='USD')
    is_approved = models.BooleanField(
        default=False,
        help_text="Whether the vendor profile is approved"
    )
    two_factor_enabled = models.BooleanField(
        default=False,
        help_text="Whether 2FA is enabled"
    )
    two_factor_required = models.BooleanField(
        default=True,
        help_text="Whether 2FA is required (enforced)"
    )
    two_factor_verified_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When 2FA was last verified"
    )
    
    # Audit fields
    last_bank_details_updated = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When bank details were last updated"
    )
    last_bank_details_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bank_details_updates',
        help_text="Who last updated bank details"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Secure Vendor Profile'
        verbose_name_plural = 'Secure Vendor Profiles'
        permissions = [
            ("view_bank_details", "Can view bank details"),
            ("edit_bank_details", "Can edit bank details"),
        ]
    
    def __str__(self):
        return f"Secure Vendor Profile - {self.business_partner.name}"
    
    def get_masked_account_number(self):
        """Return masked account number for display"""
        if not self.account_number:
            return "Not provided"
        decrypted = str(self.account_number)
        if len(decrypted) < 4:
            return "****"
        return f"****{decrypted[-4:]}"
    
    def get_masked_iban(self):
        """Return masked IBAN for display"""
        if not self.iban:
            return "Not provided"
        decrypted = str(self.iban)
        if len(decrypted) < 4:
            return "****"
        return f"****{decrypted[-4:]}"
    
    def update_bank_details(self, user, **kwargs):
        """Update bank details with audit trail"""
        from django.utils import timezone
        
        for field, value in kwargs.items():
            if hasattr(self, field):
                setattr(self, field, value)
        
        self.last_bank_details_updated = timezone.now()
        self.last_bank_details_updated_by = user
        self.save()
        
        # Log the change
        from .audit_logger import VendorAuditLogger
        VendorAuditLogger.log_vendor_action(
            action_type='bank_details_updated',
            user=user,
            vendor=self.business_partner,
            details={'fields_updated': list(kwargs.keys())}
        )
    
    def requires_2fa_setup(self):
        """Check if 2FA setup is required"""
        return self.two_factor_required and not self.two_factor_enabled
    
    def can_access_platform(self):
        """Check if vendor can access the platform"""
        if not self.is_approved:
            return False
        if self.two_factor_required and not self.two_factor_enabled:
            return False
        return True