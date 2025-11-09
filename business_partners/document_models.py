from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.utils import timezone
import uuid

User = get_user_model()


class DocumentCategory(models.Model):
    """Categories for vendor documents"""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    required = models.BooleanField(default=False)
    allowed_extensions = models.CharField(
        max_length=200, 
        help_text="Comma-separated list of allowed file extensions (e.g., pdf,jpg,png)",
        default="pdf,jpg,jpeg,png,doc,docx"
    )
    max_file_size = models.PositiveIntegerField(
        default=10,
        help_text="Maximum file size in MB"
    )
    expiry_required = models.BooleanField(
        default=False,
        help_text="Whether documents in this category require expiry dates"
    )
    verification_required = models.BooleanField(
        default=False,
        help_text="Whether documents in this category require manual verification"
    )
    
    class Meta:
        verbose_name = "Document Category"
        verbose_name_plural = "Document Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_allowed_extensions_list(self):
        """Return allowed extensions as a list"""
        return [ext.strip().lower() for ext in self.allowed_extensions.split(',')]


class VendorDocument(models.Model):
    """Documents uploaded by vendors for verification"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
        ('needs_renewal', 'Needs Renewal'),
    ]
    
    # Identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document_number = models.CharField(max_length=50, unique=True, editable=False)
    
    # Relationships
    vendor_application = models.ForeignKey(
        'VendorApplication',
        on_delete=models.CASCADE,
        related_name='documents',
        null=True,
        blank=True,
        help_text="Associated vendor application (if applicable)"
    )
    business_partner = models.ForeignKey(
        'BusinessPartner',
        on_delete=models.CASCADE,
        related_name='vendor_documents',
        null=True,
        blank=True,
        help_text="Associated business partner (for approved vendors)"
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_vendor_documents'
    )
    
    # Document details
    category = models.ForeignKey(
        DocumentCategory,
        on_delete=models.PROTECT,
        related_name='vendor_documents'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # File handling
    file = models.FileField(
        upload_to='vendor_documents/%Y/%m/',
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'])
        ]
    )
    file_size = models.PositiveIntegerField(editable=False)  # in bytes
    file_hash = models.CharField(max_length=64, editable=False)  # SHA-256 hash
    
    # Status and verification
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Expiry tracking
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    
    # Verification details
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_vendor_documents'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True)
    
    # Rejection details
    rejected_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rejected_vendor_documents'
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Vendor Document"
        verbose_name_plural = "Vendor Documents"
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['business_partner', 'category', 'status']),
            models.Index(fields=['vendor_application', 'status']),
            models.Index(fields=['status', 'expiry_date']),
            models.Index(fields=['uploaded_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(vendor_application__isnull=False) | models.Q(business_partner__isnull=False),
                name='vendor_document_must_have_application_or_partner'
            )
        ]
    
    def __str__(self):
        return f"{self.title} - {self.business_partner or self.vendor_application}"
    
    def save(self, *args, **kwargs):
        # Generate document number if not set
        if not self.document_number:
            self.document_number = self.generate_document_number()
        
        # Calculate file size and hash if file is present
        if self.file and not self.file_size:
            self.file_size = self.file.size
            self.file_hash = self.calculate_file_hash()
        
        super().save(*args, **kwargs)
    
    def generate_document_number(self):
        """Generate a unique document number"""
        from django.utils import timezone
        year = timezone.now().year
        count = VendorDocument.objects.filter(
            uploaded_at__year=year
        ).count() + 1
        return f"VDOC-{year}-{count:06d}"
    
    def calculate_file_hash(self):
        """Calculate SHA-256 hash of the file"""
        import hashlib
        if self.file:
            hash_sha256 = hashlib.sha256()
            for chunk in self.file.chunks():
                hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        return ""
    
    @property
    def is_expired(self):
        """Check if document is expired"""
        if self.expiry_date:
            from django.utils import timezone
            return timezone.now().date() > self.expiry_date
        return False
    
    @property
    def days_until_expiry(self):
        """Get days until expiry"""
        if self.expiry_date:
            from django.utils import timezone
            delta = self.expiry_date - timezone.now().date()
            return delta.days
        return None
    
    @property
    def file_size_mb(self):
        """Get file size in MB"""
        return round(self.file_size / (1024 * 1024), 2) if self.file_size else 0
    
    def verify(self, user, notes=None):
        """Mark document as verified"""
        from django.utils import timezone
        self.status = 'verified'
        self.verified_by = user
        self.verified_at = timezone.now()
        self.verification_notes = notes or ""
        self.save()
    
    def reject(self, user, reason):
        """Reject the document"""
        from django.utils import timezone
        self.status = 'rejected'
        self.rejected_by = user
        self.rejected_at = timezone.now()
        self.rejection_reason = reason
        self.save()
    
    def mark_expired(self):
        """Mark document as expired"""
        self.status = 'expired'
        self.save()
    
    def mark_needs_renewal(self):
        """Mark document as needing renewal"""
        self.status = 'needs_renewal'
        self.save()


class DocumentVerificationQueue(models.Model):
    """Queue for documents pending manual verification"""
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    document = models.OneToOneField(
        VendorDocument,
        on_delete=models.CASCADE,
        related_name='verification_queue'
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium'
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_document_verifications'
    )
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Document Verification Queue"
        verbose_name_plural = "Document Verification Queues"
        ordering = ['-priority', 'created_at']
        indexes = [
            models.Index(fields=['priority', 'created_at']),
            models.Index(fields=['assigned_to', 'completed_at']),
        ]
    
    def __str__(self):
        return f"Verification Queue: {self.document.title} ({self.get_priority_display()})"
    
    def assign_to_user(self, user):
        """Assign document verification to a user"""
        from django.utils import timezone
        self.assigned_to = user
        self.assigned_at = timezone.now()
        self.save()
    
    def complete_verification(self):
        """Mark verification as completed"""
        from django.utils import timezone
        self.completed_at = timezone.now()
        self.save()


class DocumentAuditLog(models.Model):
    """Audit log for all document-related actions"""
    
    ACTION_CHOICES = [
        ('uploaded', 'Document Uploaded'),
        ('viewed', 'Document Viewed'),
        ('downloaded', 'Document Downloaded'),
        ('verified', 'Document Verified'),
        ('rejected', 'Document Rejected'),
        ('expired', 'Document Expired'),
        ('renewed', 'Document Renewed'),
        ('deleted', 'Document Deleted'),
        ('assigned', 'Verification Assigned'),
        ('unassigned', 'Verification Unassigned'),
    ]
    
    document = models.ForeignKey(
        VendorDocument,
        on_delete=models.CASCADE,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='document_audit_actions'
    )
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Document Audit Log"
        verbose_name_plural = "Document Audit Logs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['document', 'action', '-created_at']),
            models.Index(fields=['performed_by', '-created_at']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.document.title} by {self.performed_by}"
    
    @classmethod
    def log_action(cls, document, action, user=None, details=None, ip_address=None, user_agent=None):
        """Log a document action"""
        return cls.objects.create(
            document=document,
            action=action,
            performed_by=user,
            details=details or "",
            ip_address=ip_address,
            user_agent=user_agent or ""
        )