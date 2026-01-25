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
        # ('company', 'Company'),
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
    logo = models.ImageField(
        upload_to='vendor_logos/', 
        blank=True, 
        null=True, 
        help_text="Business logo"
    )
    description = models.TextField(
        blank=True, 
        null=True, 
        help_text="Business description"
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
    
    @property
    def business_name(self):
        """Alias for name to maintain compatibility with legacy code/templates"""
        return self.name

    def __str__(self):
        return f"{self.bp_number} - {self.name}"

    def get_country_code(self):
        """Get the 2-letter country code for this business partner."""
        # Try to get from primary office address first
        primary_address = self.addresses.filter(address_type='office', is_primary=True).first()
        if not primary_address:
            primary_address = self.addresses.filter(address_type='office').first()
        if not primary_address:
            primary_address = self.addresses.filter(is_primary=True).first()
        if not primary_address:
            primary_address = self.addresses.first()
        
        if primary_address:
            country_name = primary_address.country.strip()
            # If it's already a 2-letter code, return it
            if len(country_name) == 2:
                return country_name.upper()
            
            # Try to find in Country model
            # Import inside method to avoid circular dependency
            from parts.models import Country
            country = Country.objects.filter(name__iexact=country_name).first()
            if country:
                return country.code.upper()
        
        # Fallback to Saudi Arabia as it's the default in many places
        return 'SA'
    
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
    
    BUSINESS_TYPES = [
        ('sole_proprietorship', 'Sole Proprietorship'),
        ('partnership', 'Partnership'),
        ('llc', 'Limited Liability Company (LLC)'),
        ('corporation', 'Corporation'),
        ('cooperative', 'Cooperative'),
        ('other', 'Other'),
    ]
    
    business_partner = models.OneToOneField(
        BusinessPartner, 
        on_delete=models.CASCADE, 
        related_name='vendor_profile'
    )
    
    # User relationship for direct vendor-user mapping
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='vendor_profiles',
        help_text="User account associated with this vendor profile"
    )
    
    # Business Details
    business_structure = models.CharField(
        max_length=30,
        choices=BUSINESS_TYPES,
        blank=True,
        null=True
    )
    establishment_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date of business establishment"
    )
    
    # Contact Person
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
    
    # Financial Details
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
    swift_code = models.CharField(
        max_length=11,
        blank=True,
        null=True,
        help_text="SWIFT/BIC code"
    )
    vendor_code = models.CharField(max_length=50, blank=True, null=True)
    tax_number = models.CharField(max_length=50, blank=True, null=True)
    bank_account_number = models.CharField(max_length=50, blank=True, null=True)
    bank_account_holder_name = models.CharField(max_length=255, blank=True, null=True, help_text="Name of the bank account holder")
    bank_routing_number = models.CharField(max_length=50, blank=True, null=True)
    bank_name = models.CharField(max_length=200, blank=True, null=True)
    iban = models.CharField(max_length=50, blank=True, null=True, help_text="International Bank Account Number")
    
    # Bank Verification status
    bank_details_verified = models.BooleanField(
        default=False,
        help_text="Whether bank details have been verified by an admin"
    )
    bank_verification_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When bank details were verified"
    )
    bank_verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_vendor_banks',
        help_text="Admin who verified the bank details"
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
    
    # Documents
    cr_document = models.FileField(
        upload_to='vendor_documents/cr_documents/',
        blank=True,
        null=True,
        help_text="Commercial Registration document"
    )
    business_license = models.FileField(
        upload_to='vendor_documents/business_licenses/',
        blank=True,
        null=True,
        help_text="Business license document"
    )
    bank_statement = models.FileField(
        upload_to='vendor_documents/bank_statements/',
        blank=True,
        null=True,
        help_text="Recent bank statement"
    )
    
    # Additional Required Documents
    vat_certificate = models.FileField(
        upload_to='vendor_documents/vat_certificates/',
        blank=True,
        null=True,
        help_text="VAT registration certificate"
    )
    commercial_invoice_sample = models.FileField(
        upload_to='vendor_documents/commercial_invoices/',
        blank=True,
        null=True,
        help_text="Sample commercial invoice"
    )
    company_profile = models.FileField(
        upload_to='vendor_documents/company_profiles/',
        blank=True,
        null=True,
        help_text="Company profile or brochure"
    )
    quality_certificate = models.FileField(
        upload_to='vendor_documents/quality_certificates/',
        blank=True,
        null=True,
        help_text="ISO or quality management certificate"
    )
    insurance_certificate = models.FileField(
        upload_to='vendor_documents/insurance_certificates/',
        blank=True,
        null=True,
        help_text="Business insurance certificate"
    )
    import_export_license = models.FileField(
        upload_to='vendor_documents/import_export_licenses/',
        blank=True,
        null=True,
        help_text="Import/export license (if applicable)"
    )
    supplier_certification = models.FileField(
        upload_to='vendor_documents/supplier_certifications/',
        blank=True,
        null=True,
        help_text="Manufacturer authorization or supplier certification"
    )
    
    # Additional Info
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
        help_text="Types of automotive parts you sell"
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
    
    # Vendor approval state machine - ISO 27001 compliant approval workflow
    approval_state = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending Review'),
            ('UNDER_REVIEW', 'Under Review'),
            ('REQUIRES_CHANGES', 'Requires Changes'),
            ('APPROVED', 'Approved'),
            ('REJECTED', 'Rejected'),
            ('SUSPENDED', 'Suspended'),
            ('REVOKED', 'Revoked'),
        ],
        default='PENDING',
        help_text="ISO 27001 compliant vendor approval state"
    )
    
    # Legacy field for backward compatibility
    is_approved = models.BooleanField(
        default=False,
        help_text="Legacy field - use approval_state instead"
    )
    registration_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date when the vendor was registered on the platform"
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
    backup_codes = models.TextField(blank=True, null=True)
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
        
        # Bank detail validation
        bank_fields = [
            self.bank_name, self.bank_account_number, 
            self.bank_routing_number, self.iban, self.swift_code
        ]
        if any(bank_fields) and not self.bank_account_holder_name:
            raise ValidationError({
                'bank_account_holder_name': "Bank account holder name is required if other bank details are provided."
            })
    
    def generate_backup_codes(self, count=10):
        import json
        import secrets
        import string

        codes = []
        for _ in range(count):
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            codes.append(code)

        self.backup_codes = json.dumps(codes)
        self.save(update_fields=['backup_codes'])

        return codes
    
    def use_backup_code(self, code):
        import json

        if not self.backup_codes:
            return False

        try:
            codes = json.loads(self.backup_codes)
        except Exception:
            codes = []

        if code not in codes:
            return False

        codes = [c for c in codes if c != code]
        self.backup_codes = json.dumps(codes)
        self.save(update_fields=['backup_codes'])

        return True
    
    def get_profile_completion_percentage(self):
        """Calculate profile completion percentage based on required fields"""
        # Define required fields for profile completion
        required_fields = [
            'business_structure',
            'establishment_date',
            'contact_person_name',
            'contact_person_title',
            'payment_terms',
            'bank_account_details',
            'swift_code',
            'tax_id',
            'preferred_currency',
            'expected_monthly_volume',
            'product_categories',
            'years_in_business',
        ]
        
        # Define required documents for profile completion
        required_documents = [
            'cr_document',
            'business_license',
            'vat_certificate',
        ]
        
        # Count completed fields
        completed_fields = 0
        for field in required_fields:
            field_value = getattr(self, field, None)
            if field_value is not None and field_value != '':
                completed_fields += 1
        
        # Count completed documents
        completed_documents = 0
        for doc_field in required_documents:
            doc_value = getattr(self, doc_field, None)
            if doc_value:  # Check if file exists
                completed_documents += 1
        
        # Check for documents in VendorDocument model (from registration)
        try:
            from business_partners.document_models import VendorDocument
            vendor_docs = VendorDocument.objects.filter(
                business_partner=self.business_partner,
                status='verified'
            ).values_list('category__name', flat=True)
            
            # Map VendorDocument categories to our required documents
            doc_mapping = {
                'Commercial Register': 'cr_document',
                'Tax Certificate': 'cr_document',  # Tax certificate counts as CR document
            }
            
            for category_name in vendor_docs:
                if category_name in doc_mapping:
                    mapped_field = doc_mapping[category_name]
                    if mapped_field in required_documents:
                        # Check if we don't already have this document in VendorProfile
                        if not getattr(self, mapped_field, None):
                            completed_documents += 1
        except ImportError:
            pass
        
        # Calculate total completion (70% for fields, 30% for documents)
        field_completion = (completed_fields / len(required_fields)) * 70
        document_completion = (completed_documents / len(required_documents)) * 30
        total_completion = field_completion + document_completion
        
        return round(total_completion, 1)

    def get_verification_deadline(self):
        """Get the 3-day verification deadline from profile creation."""
        from datetime import timedelta
        return self.created_at + timedelta(days=3)

    @property
    def is_verification_expired(self):
        """Check if the 3-day verification period has expired."""
        from django.utils import timezone
        if self.approval_state == 'APPROVED':
            return False
        return timezone.now() > self.get_verification_deadline()

    def get_remaining_verification_time(self):
        """Get remaining time for verification."""
        from django.utils import timezone
        if self.approval_state == 'APPROVED':
            return None
        deadline = self.get_verification_deadline()
        now = timezone.now()
        if now > deadline:
            return None
        return deadline - now
    
    def save(self, *args, **kwargs):
        """Override save to sync approval state and log bank detail changes"""
        # Sync approval_state with legacy is_approved for backward compatibility
        if self.approval_state == 'APPROVED':
            self.is_approved = True
        else:
            self.is_approved = False
        
        # Detect bank detail changes for audit logging
        if self.pk:
            try:
                old_instance = VendorProfile.objects.get(pk=self.pk)
                bank_fields = [
                    'bank_name', 'bank_account_number', 'bank_account_holder_name',
                    'bank_routing_number', 'iban', 'swift_code'
                ]
                
                changed_fields = {}
                for field in bank_fields:
                    old_val = getattr(old_instance, field)
                    new_val = getattr(self, field)
                    if old_val != new_val:
                        changed_fields[field] = {'old': str(old_val), 'new': str(new_val)}
                
                if changed_fields:
                    from .audit_logger import VendorAuditLogger
                    # Reset verification if bank details change
                    if not any(f in kwargs.get('update_fields', []) for f in ['bank_details_verified']):
                        self.bank_details_verified = False
                        self.bank_verification_date = None
                        self.bank_verified_by = None
                    
                    VendorAuditLogger.log_vendor_action(
                        action_type='bank_details_updated',
                        user=kwargs.get('user'), # We might need to pass user to save()
                        vendor=self.business_partner,
                        details={'changed_fields': changed_fields}
                    )
            except VendorProfile.DoesNotExist:
                pass

        super().save(*args, **kwargs)
    
    def get_approval_state(self):
        """Get current approval state from state machine"""
        from core.vendor_access_controller import VendorAccessController
        controller = VendorAccessController()
        return controller.get_current_state(self)
    
    def transition_approval_state(self, new_state, reason=None, performed_by=None):
        """Transition to a new approval state"""
        from core.vendor_access_controller import VendorAccessController
        controller = VendorAccessController()
        return controller.transition_state(self, new_state, reason, performed_by)
    
    def can_access_feature(self, feature_name):
        """Check if vendor can access specific feature based on approval state"""
        from core.vendor_access_controller import VendorAccessController
        controller = VendorAccessController()
        return controller.can_access_feature(self, feature_name)
    
    def get_available_actions(self):
        """Get available state transition actions"""
        from core.vendor_access_controller import VendorAccessController
        controller = VendorAccessController()
        return controller.get_available_actions(self)
    
    def get_approval_history(self):
        """Get approval state transition history"""
        from core.vendor_access_controller import VendorAccessController
        controller = VendorAccessController()
        return controller.get_state_history(self)


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
        if self.application_id:
            super().save(*args, **kwargs)
            return

        from django.utils import timezone
        from django.db import transaction, IntegrityError

        timestamp = timezone.now().strftime('%Y%m%d')
        prefix = f'VA{timestamp}'

        for _ in range(5):
            try:
                with transaction.atomic():
                    last_app = (
                        VendorApplication.objects.select_for_update()
                        .filter(application_id__startswith=prefix)
                        .order_by('-application_id')
                        .first()
                    )

                    if last_app:
                        try:
                            last_number = int((last_app.application_id or '')[-3:])
                            candidate = f"{prefix}{last_number + 1:03d}"
                        except (ValueError, IndexError, TypeError):
                            candidate = f"{prefix}001"
                    else:
                        candidate = f"{prefix}001"

                    self.application_id = candidate
                    super().save(*args, **kwargs)
                    return
            except IntegrityError:
                self.application_id = None
        raise IntegrityError('Could not generate a unique application_id')
    
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
    
    def create_provisional_profile(self):
        """Create provisional BusinessPartner and VendorProfile for immediate access."""
        if not self.user:
            return None
            
        # Get or Create BusinessPartner
        business_partner = BusinessPartner.objects.filter(user=self.user).first()
        
        if not business_partner:
            # Create BusinessPartner
            business_partner = BusinessPartner.objects.create(
                name=self.company_name,
                type='company',
                legal_identifier=self.legal_identifier,
                status='active', # Set active so they can access system
                user=self.user,
                created_by=self.user
            )
        else:
            # Ensure it is active
            if business_partner.status != 'active':
                business_partner.status = 'active'
                business_partner.save(update_fields=['status'])
        
        # Add vendor role if not exists
        BusinessPartnerRole.objects.get_or_create(
            business_partner=business_partner,
            role_type='vendor'
        )
        
        # Create contact information
        if self.business_email:
            ContactInfo.objects.get_or_create(
                business_partner=business_partner,
                contact_type='email',
                value=self.business_email,
                defaults={'is_primary': True}
            )
        
        if self.business_phone:
            ContactInfo.objects.get_or_create(
                business_partner=business_partner,
                contact_type='phone',
                value=self.business_phone,
                defaults={'is_primary': True}
            )
        
        if self.website:
            ContactInfo.objects.get_or_create(
                business_partner=business_partner,
                contact_type='website',
                value=self.website
            )
        
        # Create address
        if any([self.street_address, self.city, self.country]):
            if not Address.objects.filter(business_partner=business_partner, address_type='office').exists():
                Address.objects.create(
                    business_partner=business_partner,
                    address_type='office',
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
        
        from .utils import get_currency_for_country
        currency = get_currency_for_country(self.country)

        VendorProfile.objects.update_or_create(
            business_partner=business_partner,
            defaults={
                'user': self.user,
                'bank_account_details': bank_details,
                'tax_id': self.legal_identifier,
                'is_approved': False, # Not approved yet
                'preferred_currency': currency
            }
        )
        
        # Update user role
        if hasattr(self.user, 'role') and self.user.role == 'user':
            self.user.role = 'seller'
            self.user.save()
            
        return business_partner

    def submit_for_review(self):
        """Submit application for admin review."""
        if self.can_submit():
            from django.utils import timezone
            self.status = 'submitted'
            self.submitted_at = timezone.now()
            self.save()
            
            # Create provisional profile for immediate access
            self.create_provisional_profile()
            
            # Notify admins
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                from django.contrib.auth import get_user_model
                
                User = get_user_model()
                admin_emails = list(User.objects.filter(is_superuser=True).exclude(email='').values_list('email', flat=True))
                
                if admin_emails:
                    subject = f'New Vendor Application: {self.company_name}'
                    message = f"""
A new vendor application has been submitted.

Company: {self.company_name}
Contact: {self.contact_person_name}
Email: {self.business_email}
Date: {self.submitted_at}

Please review the application in the admin panel.
                    """.strip()
                    
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        admin_emails,
                        fail_silently=True,
                    )
            except Exception as e:
                print(f"Failed to send admin notification: {e}")
            
            return True
        return False
    
    def approve(self, admin_user, notes=None):
        """Approve the vendor application and create business partner."""
        from django.utils import timezone
        
        # Cannot approve anonymous applications
        if not self.user:
            return None
        
        # Ensure BusinessPartner and VendorProfile exist using the robust method
        business_partner = self.create_provisional_profile()
            
        # Update VendorProfile approval status
        if hasattr(business_partner, 'vendor_profile'):
            business_partner.vendor_profile.is_approved = True
            business_partner.vendor_profile.approval_state = 'APPROVED'
            business_partner.vendor_profile.save()
            
        # Update application status
        self.status = 'approved'
        self.reviewed_by = admin_user
        self.review_notes = notes
        self.reviewed_at = timezone.now()
        self.approved_at = timezone.now()
        self.save()
        
        # Send welcome email using centralized email service
        if self.user and self.user.email:
            try:
                from core.email_service.orchestrator import send_email
                from django.conf import settings
                
                email_id = send_email(
                    email_type='vendor_approval',
                    to_email=self.user.email,
                    subject='Welcome to CarSyncro - Application Approved',
                    template_name='vendor_application_approved',
                    context={
                        'contact_person_name': self.contact_person_name,
                        'company_name': self.company_name,
                        'login_url': f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}/business-partners/vendor/login/",
                        'dashboard_url': f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}/vendor/dashboard/"
                    },
                    priority='high'
                )
                
                # Log successful email queuing
                import logging
                logger = logging.getLogger('email_notifications')
                logger.info(f"Vendor approval email queued for {self.user.email} with ID: {email_id}")
                
            except Exception as e:
                # Log the error but don't fail the approval
                import logging
                logger = logging.getLogger('email_notifications')
                logger.error(f"Failed to queue vendor approval email for {self.user.email}: {e}")
                
                # Fallback to direct sending if orchestrator fails
                try:
                    subject = 'Welcome to CarSyncro - Application Approved'
                    message = f"""
Dear {self.contact_person_name},

Congratulations! Your vendor application for {self.company_name} has been approved.

You now have full access to your vendor dashboard, including:
- Adding products and services
- Order management
- Payment settings
- Promotional tools

You can log in here: {getattr(settings, 'SITE_URL', 'http://localhost:8000')}/business-partners/vendor/login/

Best regards,
CarSyncro Team
                    """.strip()
                    
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [self.user.email],
                        fail_silently=True,
                    )
                except Exception as fallback_error:
                    logger.error(f"Fallback email sending also failed for {self.user.email}: {fallback_error}")
        
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
        
        # Notify vendor using centralized email service
        if self.user and self.user.email:
            try:
                from core.email_service.orchestrator import send_email
                from django.conf import settings
                
                email_id = send_email(
                    email_type='vendor_rejection',
                    to_email=self.user.email,
                    subject='Vendor Application Status - CarSyncro',
                    template_name='vendor_application_rejected',
                    context={
                        'contact_person_name': self.contact_person_name,
                        'company_name': self.company_name,
                        'rejection_reason': reason,
                        'additional_notes': notes if notes else '',
                        'support_url': f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}/support/",
                        'reapply_url': f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}/business-partners/registration/reapply/"
                    },
                    priority='medium'
                )
                
                # Log successful email queuing
                import logging
                logger = logging.getLogger('email_notifications')
                logger.info(f"Vendor rejection email queued for {self.user.email} with ID: {email_id}")
                
            except Exception as e:
                # Log the error but don't fail the rejection
                import logging
                logger = logging.getLogger('email_notifications')
                logger.error(f"Failed to queue vendor rejection email for {self.user.email}: {e}")
                
                # Fallback to direct sending if orchestrator fails
                try:
                    subject = 'Update on your Vendor Application - CarSyncro'
                    message = f"""
Dear {self.contact_person_name},

Your vendor application for {self.company_name} has been reviewed.
Unfortunately, we cannot approve your application at this time.

Reason:
{reason}

{f"Additional Notes: {notes}" if notes else ""}

Please contact support if you have any questions.

Best regards,
CarSyncro Team
                    """.strip()
                    
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [self.user.email],
                        fail_silently=True,
                    )
                except Exception as fallback_error:
                    logger.error(f"Fallback email sending also failed for {self.user.email}: {fallback_error}")
    
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
        ('pending', 'Pending'),
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
    vendor_profile = models.ForeignKey(
        VendorProfile,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='secure_vendor_applications',
    )
    application_reference = models.CharField(max_length=50, blank=True, null=True)
    encrypted_data = models.JSONField(blank=True, null=True, default=dict)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
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

    def validate_ip_address(self, ip_address):
        if not self.ip_address or not ip_address:
            return False
        return self.ip_address == ip_address

    def validate_user_agent(self, user_agent):
        if not self.user_agent or not user_agent:
            return False
        return self.user_agent == user_agent

    def check_session_integrity(self, ip_address, user_agent):
        return self.validate_ip_address(ip_address) and self.validate_user_agent(user_agent)
    
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


