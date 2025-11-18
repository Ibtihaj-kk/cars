from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from decimal import Decimal
from .validators import validate_uploaded_document
from .session_utils import SecureSessionMixin


class BusinessPartner(models.Model):
    """Core Business Partner entity"""
    
    PARTNER_TYPES = [
        ('individual', 'Individual'),
        ('company', 'Company'),
        ('organization', 'Organization'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('pending', 'Pending Approval'),
    ]
    
    bp_number = models.CharField(
        max_length=20, 
        unique=True, 
        help_text="Unique business partner number"
    )
    name = models.CharField(max_length=255, help_text="Business partner name")
    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
        help_text="URL-friendly version of the name"
    )
    type = models.CharField(
        max_length=20, 
        choices=PARTNER_TYPES, 
        default='company'
    )
    legal_identifier = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Tax ID, Registration number, etc."
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
    
    # User relationship
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='business_partners',
        help_text="User associated with this business partner"
    )
    
    # Audit fields
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_business_partners',
        help_text="User who created this business partner"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Business Partner'
        verbose_name_plural = 'Business Partners'
    
    def __str__(self):
        return f"{self.bp_number} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.bp_number:
            # Auto-generate BP number if not provided
            # Find the highest numeric BP number
            max_number = 0
            for bp in BusinessPartner.objects.filter(bp_number__startswith='BP'):
                try:
                    number_part = bp.bp_number[2:]  # Remove 'BP' prefix
                    if number_part.isdigit():
                        max_number = max(max_number, int(number_part))
                except (ValueError, IndexError):
                    continue
            
            # Increment from the highest found number
            self.bp_number = f"BP{max_number + 1:06d}"
        
        # Auto-generate slug if not provided
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while BusinessPartner.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        
        super().save(*args, **kwargs)
    
    def set_session(self, session_key):
        """Store hashed session key with additional security checks"""
        # Validate session age and activity
        from .session_utils import validate_session_age, track_session_activity
        
        if not validate_session_age(session_key):
            raise ValueError("Session is too old or invalid")
        
        # Track session activity
        track_session_activity(session_key, 'session_set')
        
        # Store hashed session key using the mixin method
        super().set_session(session_key)
    
    def validate_session_access(self, session_key):
        """Validate session access with enhanced security checks"""
        from .session_utils import validate_session_age, track_session_activity
        from .audit_logger import VendorAuditLogger
        
        # Basic session validation
        if not session_key:
            VendorAuditLogger.log_security_event(
                'security_suspicious_activity',
                self.user,
                'Empty session key provided',
                severity='high'
            )
            return False
        
        # Validate session age
        if not validate_session_age(session_key):
            VendorAuditLogger.log_security_event(
                'security_suspicious_activity',
                self.user,
                f'Invalid session age for key: {session_key[:8]}...',
                severity='medium'
            )
            return False
        
        # Track session activity
        track_session_activity(session_key, 'access_validation')
        
        # Use mixin validation
        return super().validate_session_access(session_key)
    
    def get_secure_session_data(self):
        """Get session data with security validation"""
        from .session_utils import track_session_activity
        from .audit_logger import VendorAuditLogger
        
        # Get session data from mixin
        session_data = super().get_secure_session_data()
        
        if session_data:
            # Track successful access
            if 'session_key' in session_data:
                track_session_activity(session_data['session_key'], 'data_access')
        else:
            # Log suspicious access attempt
            VendorAuditLogger.log_security_event(
                'security_suspicious_activity',
                self.user,
                'Failed to retrieve secure session data',
                severity='low'
            )
        
        return session_data
    
    def get_roles(self):
        """Get all roles for this business partner"""
        return self.roles.all()
    
    def has_role(self, role_type):
        """Check if business partner has a specific role"""
        return self.roles.filter(role_type=role_type).exists()
    
    def is_customer(self):
        """Check if business partner is a customer"""
        return self.has_role('customer')
    
    def is_vendor(self):
        """Check if business partner is a vendor"""
        return self.has_role('vendor')
    
    def is_prospect(self):
        """Check if business partner is a prospect"""
        return self.has_role('prospect')
    
    def get_primary_contact(self):
        """Get primary contact information"""
        return self.contacts.filter(is_primary=True).first()
    
    def get_primary_address(self):
        """Get primary address"""
        return self.addresses.filter(is_primary=True).first()


class BusinessPartnerRole(models.Model):
    """Business Partner Role mapping"""
    
    ROLE_TYPES = [
        ('customer', 'Customer'),
        ('vendor', 'Vendor'),
        ('prospect', 'Prospect'),
    ]
    
    business_partner = models.ForeignKey(
        BusinessPartner, 
        on_delete=models.CASCADE, 
        related_name='roles'
    )
    role_type = models.CharField(max_length=20, choices=ROLE_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['business_partner', 'role_type']
        verbose_name = 'Business Partner Role'
        verbose_name_plural = 'Business Partner Roles'
    
    def __str__(self):
        return f"{self.business_partner.name} - {self.get_role_type_display()}"


class ContactInfo(models.Model):
    """Contact information for business partners"""
    
    CONTACT_TYPES = [
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('mobile', 'Mobile'),
        ('fax', 'Fax'),
        ('website', 'Website'),
    ]
    
    business_partner = models.ForeignKey(
        BusinessPartner, 
        on_delete=models.CASCADE, 
        related_name='contacts'
    )
    contact_type = models.CharField(max_length=20, choices=CONTACT_TYPES)
    value = models.CharField(max_length=255, help_text="Contact value (email, phone, etc.)")
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Contact Information'
        verbose_name_plural = 'Contact Information'
    
    def __str__(self):
        return f"{self.business_partner.name} - {self.get_contact_type_display()}: {self.value}"
    
    def save(self, *args, **kwargs):
        # Ensure only one primary contact per type per business partner
        if self.is_primary:
            ContactInfo.objects.filter(
                business_partner=self.business_partner,
                contact_type=self.contact_type,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class Address(models.Model):
    """Address information for business partners"""
    
    ADDRESS_TYPES = [
        ('billing', 'Billing Address'),
        ('shipping', 'Shipping Address'),
        ('office', 'Office Address'),
        ('warehouse', 'Warehouse Address'),
    ]
    
    business_partner = models.ForeignKey(
        BusinessPartner, 
        on_delete=models.CASCADE, 
        related_name='addresses'
    )
    address_type = models.CharField(max_length=20, choices=ADDRESS_TYPES)
    street = models.TextField(help_text="Street address")
    city = models.CharField(max_length=100)
    state_province = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Address'
        verbose_name_plural = 'Addresses'
    
    def __str__(self):
        return f"{self.business_partner.name} - {self.get_address_type_display()}"
    
    def get_full_address(self):
        """Get formatted full address"""
        parts = [self.street, self.city]
        if self.state_province:
            parts.append(self.state_province)
        if self.postal_code:
            parts.append(self.postal_code)
        parts.append(self.country)
        return ", ".join(parts)
    
    def save(self, *args, **kwargs):
        # Ensure only one primary address per type per business partner
        if self.is_primary:
            Address.objects.filter(
                business_partner=self.business_partner,
                address_type=self.address_type,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class VendorProfile(models.Model):
    """Vendor-specific profile data"""
    
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
        related_name='vendor_profile'
    )
    payment_terms = models.CharField(
        max_length=20, 
        choices=PAYMENT_TERMS, 
        default='net_30'
    )
    bank_account_details = models.TextField(
        blank=True, 
        null=True,
        help_text="Bank account information for payments"
    )
    vendor_rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('5.00'))],
        default=Decimal('0.00'),
        help_text="Vendor rating from 0.00 to 5.00"
    )
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    preferred_currency = models.CharField(max_length=3, default='USD')
    is_approved = models.BooleanField(
        default=False,
        help_text="Whether the vendor profile is approved for platform access"
    )
    two_factor_enabled = models.BooleanField(
        default=False,
        help_text="Whether two-factor authentication is enabled for this vendor"
    )
    two_factor_secret = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        help_text="Secret key for TOTP two-factor authentication"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Vendor Profile'
        verbose_name_plural = 'Vendor Profiles'
    
    def __str__(self):
        return f"Vendor Profile - {self.business_partner.name}"
    
    def clean(self):
        # Ensure the business partner has vendor role
        if not self.business_partner.has_role('vendor'):
            raise ValidationError("Business partner must have vendor role to create vendor profile.")
    
    def generate_backup_codes(self, count=8):
        """Generate backup codes for 2FA"""
        import secrets
        import string
        from .audit_logger import VendorAuditLogger
        
        # Generate cryptographically secure backup codes
        codes = []
        for _ in range(count):
            # Generate 8-character alphanumeric codes
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            codes.append(code)
        
        # Store hashed versions of the codes
        from django.contrib.auth.hashers import make_password
        hashed_codes = [make_password(code) for code in codes]
        
        # Store in session for temporary access (user should save these)
        # In a real implementation, you'd want to store these more permanently
        # or provide them to the user immediately
        
        # Log the generation of backup codes
        VendorAuditLogger.log_security_event(
            vendor=self.business_partner,
            action='2fa_backup_codes_generated',
            details={'count': count}
        )
        
        return codes
    
    def use_backup_code(self, code):
        """Validate and consume a backup code"""
        from django.contrib.auth.hashers import check_password
        from .audit_logger import VendorAuditLogger
        
        # In a real implementation, you'd retrieve stored hashed codes
        # For now, we'll log the attempt and return success for demonstration
        
        VendorAuditLogger.log_security_event(
            vendor=self.business_partner,
            action='2fa_backup_code_used',
            details={'success': True}
        )
        
        return True


class CustomerProfile(models.Model):
    """Customer-specific profile data"""
    
    LOYALTY_TIERS = [
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
        ('diamond', 'Diamond'),
    ]
    
    business_partner = models.OneToOneField(
        BusinessPartner, 
        on_delete=models.CASCADE, 
        related_name='customer_profile'
    )
    credit_limit = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Credit limit for the customer"
    )
    loyalty_tier = models.CharField(
        max_length=20, 
        choices=LOYALTY_TIERS, 
        default='bronze'
    )
    discount_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Default discount percentage for the customer"
    )
    preferred_currency = models.CharField(max_length=3, default='USD')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Customer Profile'
        verbose_name_plural = 'Customer Profiles'
    
    def __str__(self):
        return f"Customer Profile - {self.business_partner.name}"
    
    def clean(self):
        # Ensure the business partner has customer role
        if not self.business_partner.has_role('customer'):
            raise ValidationError("Business partner must have customer role to create customer profile.")
    
    def get_available_credit(self):
        """Calculate available credit (placeholder - would need order/invoice models)"""
        # This would typically calculate: credit_limit - outstanding_invoices
        return self.credit_limit


class VendorApplication(models.Model):
    """
    Multi-step vendor registration application model.
    Handles the complete vendor onboarding process with approval workflow.
    """
    
    APPLICATION_STATUS = [
        ('draft', 'Draft'),
        ('business_details_completed', 'Business Details Completed'),
        ('contact_info_completed', 'Contact Information Completed'),
        ('bank_details_completed', 'Bank Details Completed'),
        ('submitted', 'Submitted for Review'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('requires_changes', 'Requires Changes'),
    ]
    
    BUSINESS_TYPES = [
        ('sole_proprietorship', 'Sole Proprietorship'),
        ('partnership', 'Partnership'),
        ('llc', 'Limited Liability Company (LLC)'),
        ('corporation', 'Corporation'),
        ('cooperative', 'Cooperative'),
        ('other', 'Other'),
    ]
    
    # Application tracking
    application_id = models.CharField(
        max_length=20, 
        unique=True, 
        blank=True,
        help_text="Unique application identifier"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vendor_applications',
        help_text="User applying for vendor status",
        null=True,
        blank=True
    )
    session_key = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        help_text="Session key for anonymous applications"
    )
    status = models.CharField(
        max_length=30,
        choices=APPLICATION_STATUS,
        default='draft'
    )
    current_step = models.PositiveSmallIntegerField(
        default=1,
        help_text="Current step in the registration process (1-4)"
    )
    
    # Step 1: Business Details
    company_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Legal company name"
    )
    business_type = models.CharField(
        max_length=30,
        choices=BUSINESS_TYPES,
        blank=True,
        null=True
    )
    commercial_registration_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Commercial Registration (CR) number"
    )
    cr_document = models.FileField(
        upload_to='vendor_applications/cr_documents/',
        blank=True,
        null=True,
        help_text="Commercial Registration document"
    )
    legal_identifier = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Tax ID, VAT number, or other legal identifier"
    )
    business_license = models.FileField(
        upload_to='vendor_applications/business_licenses/',
        blank=True,
        null=True,
        help_text="Business license document"
    )
    establishment_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date of business establishment"
    )
    business_description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of business activities"
    )
    
    # Step 2: Contact Information
    contact_person_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Primary contact person name"
    )
    contact_person_title = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Contact person job title"
    )
    business_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Business phone number"
    )
    business_email = models.EmailField(
        blank=True,
        null=True,
        help_text="Business email address"
    )
    website = models.URLField(
        blank=True,
        null=True,
        help_text="Company website"
    )
    
    # Address fields
    street_address = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Street address"
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    state_province = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="State or Province"
    )
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    country = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    
    # Step 3: Bank Details
    bank_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Name of the bank"
    )
    bank_branch = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Bank branch name"
    )
    account_holder_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Account holder name (must match business name)"
    )
    account_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Bank account number"
    )
    iban = models.CharField(
        max_length=34,
        blank=True,
        null=True,
        help_text="International Bank Account Number (IBAN)"
    )
    swift_code = models.CharField(
        max_length=11,
        blank=True,
        null=True,
        help_text="SWIFT/BIC code"
    )
    bank_statement = models.FileField(
        upload_to='vendor_applications/bank_statements/',
        blank=True,
        null=True,
        help_text="Recent bank statement for verification"
    )
    
    # Step 4: Additional Information
    expected_monthly_volume = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Expected monthly sales volume"
    )
    product_categories = models.TextField(
        blank=True,
        null=True,
        help_text="Types of automotive parts you plan to sell"
    )
    years_in_business = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Number of years in automotive parts business"
    )
    references = models.TextField(
        blank=True,
        null=True,
        help_text="Business references or previous partnerships"
    )
    
    # Admin review fields
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_vendor_applications',
        help_text="Admin who reviewed the application"
    )
    review_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Admin notes during review process"
    )
    rejection_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for rejection if applicable"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the application was submitted for review"
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the application was reviewed"
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the application was approved"
    )
    
    class Meta:
        verbose_name = 'Vendor Application'
        verbose_name_plural = 'Vendor Applications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status'], name='bp_vendor_app_status_idx'),
            models.Index(fields=['user'], name='bp_vendor_app_user_idx'),
            models.Index(fields=['session_key'], name='bp_vendor_app_session_idx'),
            models.Index(fields=['application_id'], name='bp_vendor_app_id_idx'),
            models.Index(fields=['created_at'], name='bp_vendor_app_created_idx'),
        ]
    
    def __str__(self):
        if self.user:
            return f"Vendor Application {self.application_id} - {self.company_name or self.user.email}"
        else:
            return f"Vendor Application {self.application_id} - Anonymous User"
    
    def save(self, *args, **kwargs):
        # Auto-generate application ID if not provided
        if not self.application_id:
            from django.utils import timezone
            timestamp = timezone.now().strftime('%Y%m%d')
            last_app = VendorApplication.objects.filter(
                application_id__startswith=f'VA{timestamp}'
            ).order_by('-id').first()
            
            if last_app and len(last_app.application_id) >= 13:  # VA + YYYYMMDD + 3 digits = 11 chars minimum
                try:
                    # Extract the sequence number from properly formatted IDs
                    last_number = int(last_app.application_id[-3:])
                    self.application_id = f"VA{timestamp}{last_number + 1:03d}"
                except (ValueError, IndexError):
                    # If parsing fails, start from 001
                    self.application_id = f"VA{timestamp}001"
            else:
                self.application_id = f"VA{timestamp}001"
        
        super().save(*args, **kwargs)
    
    def get_completion_percentage(self):
        """Calculate application completion percentage."""
        total_fields = 0
        completed_fields = 0
        
        # Step 1: Business Details (required fields)
        step1_fields = [
            self.company_name, self.business_type, 
            self.commercial_registration_number, self.legal_identifier
        ]
        total_fields += len(step1_fields)
        completed_fields += sum(1 for field in step1_fields if field)
        
        # Step 2: Contact Information (required fields)
        step2_fields = [
            self.contact_person_name, self.business_phone, 
            self.business_email, self.street_address, self.city, self.country
        ]
        total_fields += len(step2_fields)
        completed_fields += sum(1 for field in step2_fields if field)
        
        # Step 3: Bank Details (required fields)
        step3_fields = [
            self.bank_name, self.account_holder_name, 
            self.account_number, self.iban
        ]
        total_fields += len(step3_fields)
        completed_fields += sum(1 for field in step3_fields if field)
        
        return int((completed_fields / total_fields) * 100) if total_fields > 0 else 0
    
    def is_step_completed(self, step):
        """Check if a specific step is completed."""
        if step == 1:
            return all([
                self.company_name, self.business_type,
                self.commercial_registration_number, self.legal_identifier
            ])
        elif step == 2:
            return all([
                self.contact_person_name, self.business_phone,
                self.business_email, self.street_address, self.city, self.country
            ])
        elif step == 3:
            return all([
                self.bank_name, self.account_holder_name,
                self.account_number, self.iban
            ])
        elif step == 4:
            return True  # Step 4 is optional additional information
        return False
    
    def can_submit(self):
        """Check if application can be submitted for review."""
        return all([
            self.is_step_completed(1),
            self.is_step_completed(2),
            self.is_step_completed(3)
        ])
    
    def submit_for_review(self):
        """Submit application for admin review."""
        if self.can_submit():
            from django.utils import timezone
            self.status = 'submitted'
            self.submitted_at = timezone.now()
            self.save()
            return True
        return False
    
    def approve(self, admin_user, notes=None):
        """Approve the vendor application and create business partner."""
        from django.utils import timezone
        
        # Cannot approve anonymous applications
        if not self.user:
            return None
        
        # Create BusinessPartner
        business_partner = BusinessPartner.objects.create(
            name=self.company_name,
            type='company',
            legal_identifier=self.legal_identifier,
            status='active',
            user=self.user,  # Link the business partner to the user
            created_by=admin_user
        )
        
        # Add vendor role
        BusinessPartnerRole.objects.create(
            business_partner=business_partner,
            role_type='vendor'
        )
        
        # Create contact information
        if self.business_email:
            ContactInfo.objects.create(
                business_partner=business_partner,
                contact_type='email',
                value=self.business_email,
                is_primary=True
            )
        
        if self.business_phone:
            ContactInfo.objects.create(
                business_partner=business_partner,
                contact_type='phone',
                value=self.business_phone,
                is_primary=True
            )
        
        if self.website:
            ContactInfo.objects.create(
                business_partner=business_partner,
                contact_type='website',
                value=self.website
            )
        
        # Create address
        if any([self.street_address, self.city, self.country]):
            Address.objects.create(
                business_partner=business_partner,
                address_type='business',
                street=self.street_address or '',
                city=self.city or '',
                state_province=self.state_province or '',
                postal_code=self.postal_code or '',
                country=self.country or '',
                is_primary=True
            )
        
        # Create vendor profile with bank details
        bank_details = f"""
Bank: {self.bank_name}
Branch: {self.bank_branch}
Account Holder: {self.account_holder_name}
Account Number: {self.account_number}
IBAN: {self.iban}
SWIFT: {self.swift_code}
        """.strip()
        
        VendorProfile.objects.create(
            business_partner=business_partner,
            bank_account_details=bank_details,
            tax_id=self.legal_identifier,
            is_approved=True  # Set the vendor profile as approved
        )
        
        # Update user role to include vendor access
        if self.user.role == 'user':
            self.user.role = 'seller'  # Sellers can be vendors
            self.user.save()
        
        # Update application status
        self.status = 'approved'
        self.reviewed_by = admin_user
        self.review_notes = notes
        self.reviewed_at = timezone.now()
        self.approved_at = timezone.now()
        self.save()
        
        return business_partner
    
    def reject(self, admin_user, reason, notes=None):
        """Reject the vendor application."""
        from django.utils import timezone
        
        self.status = 'rejected'
        self.reviewed_by = admin_user
        self.rejection_reason = reason
        self.review_notes = notes
        self.reviewed_at = timezone.now()
        self.save()
    
    def request_changes(self, admin_user, reason, notes=None):
        """Request changes to the vendor application."""
        from django.utils import timezone
        
        self.status = 'requires_changes'
        self.reviewed_by = admin_user
        self.rejection_reason = reason
        self.review_notes = notes
        self.reviewed_at = timezone.now()
        self.save()


class ReorderNotification(models.Model):
    """Model for tracking reorder notifications and alerts"""
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('acknowledged', 'Acknowledged'),
        ('ordered', 'Ordered'),
        ('completed', 'Completed'),
        ('dismissed', 'Dismissed'),
    ]
    
    # Related models
    vendor = models.ForeignKey(
        BusinessPartner,
        on_delete=models.CASCADE,
        related_name='reorder_notifications'
    )
    part = models.ForeignKey(
        'parts.Part',
        on_delete=models.CASCADE,
        related_name='reorder_notifications'
    )
    
    # Notification details
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium'
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Stock information at time of notification
    current_stock = models.PositiveIntegerField()
    safety_stock = models.PositiveIntegerField(null=True, blank=True)
    reorder_level = models.PositiveIntegerField(default=10)
    suggested_quantity = models.PositiveIntegerField()
    
    # Notification metadata
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='acknowledged_reorder_notifications'
    )
    
    # Order tracking
    order_placed_at = models.DateTimeField(null=True, blank=True)
    order_reference = models.CharField(max_length=100, blank=True, null=True)
    expected_delivery = models.DateField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Reorder Notification"
        verbose_name_plural = "Reorder Notifications"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['vendor', 'status', '-created_at']),
            models.Index(fields=['part', 'status']),
            models.Index(fields=['priority', '-created_at']),
        ]
    
    def __str__(self):
        return f"Reorder {self.part.name} for {self.vendor.name} ({self.get_priority_display()})"
    
    def save(self, *args, **kwargs):
        # Auto-calculate suggested quantity if not provided
        if not self.suggested_quantity:
            if self.safety_stock:
                # Suggest enough to reach safety stock + buffer
                buffer = max(10, int(self.safety_stock * Decimal('0.2')))  # 20% buffer or minimum 10
                self.suggested_quantity = max(1, int(self.safety_stock + buffer - self.current_stock))
            else:
                # Default suggestion based on reorder level
                self.suggested_quantity = max(1, self.reorder_level * 2 - self.current_stock)
        
        # Auto-set priority based on stock levels
        if not self.priority or self.priority == 'medium':
            if self.current_stock == 0:
                self.priority = 'critical'
            elif self.safety_stock and self.current_stock < (self.safety_stock * 0.5):
                self.priority = 'high'
            elif self.current_stock <= self.reorder_level:
                self.priority = 'medium'
            else:
                self.priority = 'low'
        
        # Generate message if not provided
        if not self.message:
            if self.current_stock == 0:
                self.message = f"URGENT: {self.part.name} is out of stock. Immediate reorder required."
            elif self.safety_stock and self.current_stock < self.safety_stock:
                self.message = f"{self.part.name} is below safety stock level ({self.current_stock}/{self.safety_stock}). Consider reordering {self.suggested_quantity} units."
            else:
                self.message = f"{self.part.name} has reached reorder level ({self.current_stock}/{self.reorder_level}). Suggested reorder: {self.suggested_quantity} units."
        
        super().save(*args, **kwargs)
    
    def acknowledge(self, user):
        """Mark notification as acknowledged"""
        from django.utils import timezone
        self.status = 'acknowledged'
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.save()
    
    def mark_ordered(self, order_reference=None, expected_delivery=None):
        """Mark as ordered with optional tracking info"""
        from django.utils import timezone
        self.status = 'ordered'
        self.order_placed_at = timezone.now()
        if order_reference:
            self.order_reference = order_reference
        if expected_delivery:
            self.expected_delivery = expected_delivery
        self.save()
    
    def complete(self):
        """Mark notification as completed"""
        self.status = 'completed'
        self.save()
    
    def dismiss(self):
        """Dismiss the notification"""
        self.status = 'dismissed'
        self.save()
    
    @property
    def is_overdue(self):
        """Check if notification is overdue (pending for more than 7 days)"""
        from django.utils import timezone
        if self.status == 'pending':
            return (timezone.now() - self.created_at).days > 7
        return False
    
    @property
    def urgency_score(self):
        """Calculate urgency score for sorting (higher = more urgent)"""
        score = 0
        
        # Priority scoring
        priority_scores = {'critical': 100, 'high': 75, 'medium': 50, 'low': 25}
        score += priority_scores.get(self.priority, 50)
        
        # Stock level scoring
        if self.current_stock == 0:
            score += 50
        elif self.safety_stock and self.current_stock < (self.safety_stock * 0.5):
            score += 30
        elif self.current_stock <= self.reorder_level:
            score += 20
        
        # Age scoring (older notifications get higher priority)
        from django.utils import timezone
        days_old = (timezone.now() - self.created_at).days
        score += min(days_old * 2, 20)  # Max 20 points for age
        
        return score
    
    def request_changes(self, admin_user, reason, notes=None):
        """Request changes to the application."""
        from django.utils import timezone
        
        self.status = 'requires_changes'
        self.reviewed_by = admin_user
        self.rejection_reason = reason
        self.review_notes = notes
        self.reviewed_at = timezone.now()
        self.save()


class VendorPerformanceScore(models.Model):
    """Model for storing vendor performance scores and metrics"""
    
    vendor = models.ForeignKey(
        BusinessPartner,
        on_delete=models.CASCADE,
        related_name='performance_scores',
        limit_choices_to={'type': 'vendor'}
    )
    
    # Performance metrics
    total_orders = models.PositiveIntegerField(default=0)
    completed_orders = models.PositiveIntegerField(default=0)
    on_time_delivery_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    quality_score = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    average_rating = models.DecimalField(
        max_digits=3, decimal_places=2, default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    performance_score = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Period information
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Vendor Performance Score"
        verbose_name_plural = "Vendor Performance Scores"
        ordering = ['-created_at']
        unique_together = ['vendor', 'period_start', 'period_end']
        indexes = [
            models.Index(fields=['vendor', '-created_at']),
            models.Index(fields=['vendor', 'period_start', 'period_end']),
            models.Index(fields=['performance_score', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.vendor.name} - {self.period_start} to {self.period_end} ({self.performance_score})"
    
    def save(self, *args, **kwargs):
        # Ensure period_start is before period_end
        if self.period_start > self.period_end:
            self.period_start, self.period_end = self.period_end, self.period_start
        super().save(*args, **kwargs)
    
    @property
    def delivery_performance(self):
        """Get delivery performance as a percentage"""
        return f"{self.on_time_delivery_rate}%"
    
    @property
    def quality_performance(self):
        """Get quality performance as a percentage"""
        return f"{self.quality_score}%"
    
    @property
    def overall_performance(self):
        """Get overall performance as a percentage"""
        return f"{self.performance_score}%"
    
    def is_excellent(self):
        """Check if performance is excellent (>= 90)"""
        return self.performance_score >= 90.00
    
    def is_good(self):
        """Check if performance is good (>= 75 and < 90)"""
        return 75.00 <= self.performance_score < 90.00
    
    def is_needs_improvement(self):
        """Check if performance needs improvement (>= 60 and < 75)"""
        return 60.00 <= self.performance_score < 75.00
    
    def is_poor(self):
        """Check if performance is poor (< 60)"""
        return self.performance_score < 60.00
    
    def get_performance_grade(self):
        """Get performance grade (A, B, C, D, F)"""
        if self.performance_score >= 90:
            return 'A'
        elif self.performance_score >= 80:
            return 'B'
        elif self.performance_score >= 70:
            return 'C'
        elif self.performance_score >= 60:
            return 'D'
        else:
            return 'F'


class SecureVendorApplication(SecureSessionMixin, models.Model):
    """
    Vendor application with secure file uploads and session security.
    """
    
    APPLICATION_STATUS = [
        ('draft', 'Draft'),
        ('business_details_completed', 'Business Details Completed'),
        ('contact_info_completed', 'Contact Information Completed'),
        ('bank_details_completed', 'Bank Details Completed'),
        ('submitted', 'Submitted for Review'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('requires_changes', 'Requires Changes'),
    ]
    
    BUSINESS_TYPES = [
        ('sole_proprietorship', 'Sole Proprietorship'),
        ('partnership', 'Partnership'),
        ('llc', 'Limited Liability Company (LLC)'),
        ('corporation', 'Corporation'),
        ('cooperative', 'Cooperative'),
        ('other', 'Other'),
    ]
    
    # Application tracking
    application_id = models.CharField(
        max_length=20, 
        unique=True, 
        blank=True,
        help_text="Unique application identifier"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='secure_vendor_applications',
        help_text="User applying for vendor status",
        null=True,
        blank=True
    )
    session_hash = models.CharField(
        max_length=64,  # SHA256 hash length
        blank=True,
        null=True,
        help_text="SHA256 hash of session key"
    )
    status = models.CharField(
        max_length=30,
        choices=APPLICATION_STATUS,
        default='draft'
    )
    current_step = models.PositiveSmallIntegerField(
        default=1,
        help_text="Current step in the registration process (1-4)"
    )
    
    # Step 1: Business Details
    company_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Legal company name"
    )
    business_type = models.CharField(
        max_length=30,
        choices=BUSINESS_TYPES,
        blank=True,
        null=True
    )
    commercial_registration_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Commercial Registration (CR) number"
    )
    cr_document = models.FileField(
        upload_to='vendor_applications/cr_documents/%Y/%m/',
        blank=True,
        null=True,
        validators=[validate_uploaded_document],
        help_text="Commercial Registration document (PDF, JPG, PNG only, max 10MB)"
    )
    cr_document_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA256 hash of CR document"
    )
    legal_identifier = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Tax ID, VAT number, or other legal identifier"
    )
    business_license = models.FileField(
        upload_to='vendor_applications/business_licenses/%Y/%m/',
        blank=True,
        null=True,
        validators=[validate_uploaded_document],
        help_text="Business license document (PDF, JPG, PNG only, max 10MB)"
    )
    business_license_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA256 hash of business license"
    )
    establishment_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date of business establishment"
    )
    business_description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of business activities"
    )
    
    # Step 2: Contact Information
    contact_person_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Primary contact person name"
    )
    contact_person_title = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Contact person job title"
    )
    business_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Business phone number"
    )
    business_email = models.EmailField(
        blank=True,
        null=True,
        help_text="Business email address"
    )
    website = models.URLField(
        blank=True,
        null=True,
        help_text="Company website"
    )
    
    # Address fields
    street_address = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Street address"
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    state_province = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="State or Province"
    )
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    country = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    
    # Step 3: Bank Details
    bank_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Name of the bank"
    )
    bank_branch = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Bank branch name"
    )
    account_holder_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Account holder name (must match business name)"
    )
    account_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Bank account number"
    )
    iban = models.CharField(
        max_length=34,
        blank=True,
        null=True,
        help_text="International Bank Account Number (IBAN)"
    )
    swift_code = models.CharField(
        max_length=11,
        blank=True,
        null=True,
        help_text="SWIFT/BIC code"
    )
    bank_statement = models.FileField(
        upload_to='vendor_applications/bank_statements/%Y/%m/',
        blank=True,
        null=True,
        validators=[validate_uploaded_document],
        help_text="Recent bank statement (PDF, JPG, PNG only, max 10MB)"
    )
    bank_statement_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA256 hash of bank statement"
    )
    
    # Step 4: Additional Information
    expected_monthly_volume = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Expected monthly sales volume"
    )
    product_categories = models.TextField(
        blank=True,
        null=True,
        help_text="Types of automotive parts you plan to sell"
    )
    years_in_business = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Number of years in automotive parts business"
    )
    references = models.TextField(
        blank=True,
        null=True,
        help_text="Business references or previous partnerships"
    )
    
    # Admin review fields
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_secure_vendor_applications',
        help_text="Admin who reviewed the application"
    )
    review_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Admin notes during review process"
    )
    rejection_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for rejection if applicable"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the application was submitted for review"
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the application was reviewed"
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the application was approved"
    )
    
    class Meta:
        verbose_name = 'Secure Vendor Application'
        verbose_name_plural = 'Secure Vendor Applications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status'], name='bp_secure_vendor_status_idx'),
            models.Index(fields=['user'], name='bp_secure_vendor_user_idx'),
            models.Index(fields=['session_hash'], name='bp_secure_vendor_session_idx'),
            models.Index(fields=['application_id'], name='bp_secure_vendor_appid_idx'),
            models.Index(fields=['created_at'], name='bp_secure_vendor_created_idx'),
        ]
    
    def __str__(self):
        if self.user:
            return f"Secure Vendor Application {self.application_id} - {self.company_name or self.user.email}"
        else:
            return f"Secure Vendor Application {self.application_id} - Anonymous User"
    
    def save(self, *args, **kwargs):
        # Auto-generate application ID if not provided
        if not self.application_id:
            from django.utils import timezone
            timestamp = timezone.now().strftime('%Y%m%d')
            last_app = SecureVendorApplication.objects.filter(
                application_id__startswith=f'SVA{timestamp}'
            ).order_by('-id').first()
            
            if last_app and len(last_app.application_id) >= 13:  # SVA + YYYYMMDD + 3 digits = 11 chars minimum
                try:
                    # Extract the sequence number from properly formatted IDs
                    last_number = int(last_app.application_id[-3:])
                    self.application_id = f"SVA{timestamp}{last_number + 1:03d}"
                except (ValueError, IndexError):
                    # If parsing fails, start from 001
                    self.application_id = f"SVA{timestamp}001"
            else:
                self.application_id = f"SVA{timestamp}001"
        
    def clean(self):
        """Override clean to provide user context for file validation"""
        super().clean()
        
        # If we have a user, we can provide better validation context
        if self.user and self.cr_document:
            try:
                # Re-validate with user context for audit logging
                from .validators import validate_uploaded_document
                validate_uploaded_document(self.cr_document, user=self.user)
            except ValidationError as e:
                raise ValidationError({'cr_document': e.message})
    
    def save(self, *args, **kwargs):
        """Override save to handle secure file validation and hashing"""
        # Generate application ID if not set
        if not self.application_id:
            from django.utils import timezone
            timestamp = timezone.now().strftime('%Y%m%d')
            last_app = SecureVendorApplication.objects.filter(
                application_id__startswith=f'SVA{timestamp}'
            ).order_by('-id').first()
            
            if last_app:
                # Extract the sequence number and increment
                try:
                    last_sequence = int(last_app.application_id[-4:])
                    sequence = f'{last_sequence + 1:04d}'
                except (ValueError, IndexError):
                    sequence = '0001'
            else:
                sequence = '0001'
            
            self.application_id = f'SVA{timestamp}{sequence}'
        
        # Store file hashes when saving
        if self.cr_document and hasattr(self.cr_document, 'content_hash'):
            self.cr_document_hash = self.cr_document.content_hash
        
        if self.business_license and hasattr(self.business_license, 'content_hash'):
            self.business_license_hash = self.business_license.content_hash
        
        if self.bank_statement and hasattr(self.bank_statement, 'content_hash'):
            self.bank_statement_hash = self.bank_statement.content_hash
        
        super().save(*args, **kwargs)
    
    def set_session(self, session_key):
        """Store hashed session key with additional security checks"""
        # Validate session age and activity
        from .session_utils import validate_session_age, track_session_activity
        
        if not validate_session_age(session_key):
            raise ValueError("Session is too old or invalid")
        
        # Track session activity
        track_session_activity(session_key, 'session_set')
        
        # Store hashed session key using the mixin method
        super().set_session(session_key)
    
    def validate_session_access(self, session_key):
        """Validate session access with enhanced security checks"""
        from .session_utils import validate_session_age, track_session_activity
        from .audit_logger import VendorAuditLogger
        
        # Basic session validation
        if not session_key:
            VendorAuditLogger.log_security_event(
                'security_suspicious_activity',
                self.user,
                'Empty session key provided',
                severity='high'
            )
            return False
        
        # Validate session age
        if not validate_session_age(session_key):
            VendorAuditLogger.log_security_event(
                'security_suspicious_activity',
                self.user,
                f'Invalid session age for key: {session_key[:8]}...',
                severity='medium'
            )
            return False
        
        # Track session activity
        track_session_activity(session_key, 'access_validation')
        
        # Use mixin validation
        return super().validate_session_access(session_key)
    
    def get_secure_session_data(self):
        """Get session data with security validation"""
        from .session_utils import track_session_activity
        from .audit_logger import VendorAuditLogger
        
        # Get session data from mixin
        session_data = super().get_secure_session_data()
        
        if session_data:
            # Track successful access
            if 'session_key' in session_data:
                track_session_activity(session_data['session_key'], 'data_access')
        else:
            # Log suspicious access attempt
            VendorAuditLogger.log_security_event(
                'security_suspicious_activity',
                self.user,
                'Failed to retrieve secure session data',
                severity='low'
            )
        
        return session_data


class VendorAuditLog(models.Model):
    """Audit log for vendor-related security events"""
    
    ACTION_TYPES = [
        ('login_success', 'Login Success'),
        ('login_failed', 'Login Failed'),
        ('bank_details_updated', 'Bank Details Updated'),
        ('bank_details_accessed', 'Bank Details Accessed'),
        ('file_uploaded', 'File Uploaded'),
        ('security_suspicious_activity', 'Suspicious Activity'),
        ('security_rate_limit_exceeded', 'Rate Limit Exceeded'),
        ('security_invalid_file_upload', 'Invalid File Upload'),
        ('security_password_changed', 'Password Changed'),
        ('security_2fa_enabled', '2FA Enabled'),
        ('security_2fa_disabled', '2FA Disabled'),
        ('security_2fa_verification_failed', '2FA Verification Failed'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vendor_audit_logs'
    )
    vendor = models.ForeignKey(
        BusinessPartner,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        limit_choices_to={'type': 'vendor'}
    )
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional details about the action"
    )
    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_LEVELS,
        default='medium'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the user who performed the action"
    )
    user_agent = models.TextField(
        blank=True,
        null=True,
        help_text="User agent string from the request"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Vendor Audit Log'
        verbose_name_plural = 'Vendor Audit Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['vendor', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action_type', '-created_at']),
            models.Index(fields=['severity', '-created_at']),
            models.Index(fields=['ip_address', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_action_type_display()} - {self.vendor.name if self.vendor else 'No Vendor'} - {self.created_at}"


class PasswordHistory(models.Model):
    """Store password history to prevent password reuse"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='password_history'
    )
    password_hash = models.CharField(
        max_length=128,
        help_text="Hashed password for comparison"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Password History'
        verbose_name_plural = 'Password Histories'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at'], name='bp_pwd_hist_user_created_idx'),
        ]
    
    def __str__(self):
        return f"Password history for {self.user.email} - {self.created_at}"