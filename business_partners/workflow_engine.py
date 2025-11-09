"""
Enhanced Vendor Workflow Engine with State Machine Implementation
Provides comprehensive vendor lifecycle management with approval escalation paths
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from enum import Enum
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class VendorStatus(Enum):
    """Enhanced vendor lifecycle states"""
    # Initial Application States
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    REQUIRES_INFO = "requires_info"
    
    # Approval Outcomes
    APPROVED = "approved"
    REJECTED = "rejected"
    
    # Active Vendor States
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ON_PROBATION = "on_probation"
    
    # Termination States
    TERMINATED = "terminated"
    VOLUNTARILY_INACTIVE = "voluntarily_inactive"


class VendorWorkflowState(models.Model):
    """State machine for vendor lifecycle management"""
    
    STATUS_CHOICES = [
        (VendorStatus.PENDING.value, 'Pending Initial Review'),
        (VendorStatus.UNDER_REVIEW.value, 'Under Administrative Review'),
        (VendorStatus.REQUIRES_INFO.value, 'Requires Additional Information'),
        (VendorStatus.APPROVED.value, 'Application Approved'),
        (VendorStatus.REJECTED.value, 'Application Rejected'),
        (VendorStatus.ACTIVE.value, 'Active Vendor'),
        (VendorStatus.SUSPENDED.value, 'Suspended by Admin'),
        (VendorStatus.ON_PROBATION.value, 'On Performance Probation'),
        (VendorStatus.TERMINATED.value, 'Contract Terminated'),
        (VendorStatus.VOLUNTARILY_INACTIVE.value, 'Voluntarily Inactive'),
    ]
    
    vendor_application = models.OneToOneField(
        'VendorApplication',
        on_delete=models.CASCADE,
        related_name='workflow_state'
    )
    current_status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=VendorStatus.PENDING.value
    )
    previous_status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        blank=True,
        null=True
    )
    
    # Escalation tracking
    escalation_level = models.PositiveSmallIntegerField(
        default=0,
        help_text="Escalation level for borderline cases"
    )
    escalation_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for escalation"
    )
    escalated_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='escalated_vendor_reviews',
        help_text="User who is handling escalated case"
    )
    
    # Performance metrics
    performance_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        help_text="Performance score (0-100)"
    )
    compliance_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        help_text="Compliance score (0-100)"
    )
    
    # Timestamps
    status_changed_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Vendor Workflow State"
        verbose_name_plural = "Vendor Workflow States"
        indexes = [
            models.Index(fields=['current_status', 'escalation_level']),
            models.Index(fields=['performance_score', 'compliance_score']),
        ]
    
    def __str__(self):
        return f"{self.vendor_application.application_id} - {self.get_current_status_display()}"
    
    def can_transition_to(self, new_status):
        """Check if transition to new status is valid"""
        valid_transitions = {
            VendorStatus.PENDING.value: [
                VendorStatus.UNDER_REVIEW.value,
                VendorStatus.REQUIRES_INFO.value,
                VendorStatus.REJECTED.value
            ],
            VendorStatus.UNDER_REVIEW.value: [
                VendorStatus.APPROVED.value,
                VendorStatus.REJECTED.value,
                VendorStatus.REQUIRES_INFO.value,
                VendorStatus.PENDING.value  # Can send back for re-review
            ],
            VendorStatus.REQUIRES_INFO.value: [
                VendorStatus.PENDING.value,
                VendorStatus.UNDER_REVIEW.value
            ],
            VendorStatus.APPROVED.value: [
                VendorStatus.ACTIVE.value,
                VendorStatus.ON_PROBATION.value,
                VendorStatus.SUSPENDED.value
            ],
            VendorStatus.ACTIVE.value: [
                VendorStatus.SUSPENDED.value,
                VendorStatus.ON_PROBATION.value,
                VendorStatus.VOLUNTARILY_INACTIVE.value
            ],
            VendorStatus.ON_PROBATION.value: [
                VendorStatus.ACTIVE.value,
                VendorStatus.SUSPENDED.value,
                VendorStatus.TERMINATED.value
            ],
            VendorStatus.SUSPENDED.value: [
                VendorStatus.ACTIVE.value,
                VendorStatus.TERMINATED.value,
                VendorStatus.VOLUNTARILY_INACTIVE.value
            ],
            VendorStatus.VOLUNTARILY_INACTIVE.value: [
                VendorStatus.ACTIVE.value,
                VendorStatus.TERMINATED.value
            ]
        }
        
        return new_status in valid_transitions.get(self.current_status, [])
    
    def transition_to(self, new_status, user=None, reason=None, notes=None):
        """Transition to new status with validation and logging"""
        if not self.can_transition_to(new_status):
            raise ValidationError(
                f"Invalid transition from {self.current_status} to {new_status}"
            )
        
        # Log the transition
        self.previous_status = self.current_status
        self.current_status = new_status
        self.status_changed_at = timezone.now()
        
        # Create audit log entry
        VendorWorkflowAuditLog.objects.create(
            workflow_state=self,
            from_status=self.previous_status,
            to_status=new_status,
            performed_by=user,
            reason=reason,
            notes=notes
        )
        
        self.save()
        
        logger.info(
            f"Vendor {self.vendor_application.application_id} transitioned "
            f"from {self.previous_status} to {new_status} by {user}"
        )
        
        return True
    
    def escalate_case(self, user, reason, level=1):
        """Escalate vendor case for additional review"""
        self.escalation_level = level
        self.escalation_reason = reason
        self.escalated_to = user
        self.save()
        
        # Create audit log for escalation
        VendorWorkflowAuditLog.objects.create(
            workflow_state=self,
            from_status=self.current_status,
            to_status=self.current_status,
            performed_by=user,
            reason=f"ESCALATED: {reason}",
            notes=f"Escalated to level {level}"
        )
        
        logger.warning(
            f"Vendor case {self.vendor_application.application_id} "
            f"escalated to level {level} by {user}: {reason}"
        )
    
    def calculate_performance_metrics(self):
        """Calculate performance and compliance scores"""
        # This would integrate with actual performance data
        # Placeholder implementation
        vendor = self.vendor_application
        
        # Calculate performance score based on:
        # - Order fulfillment rate
        # - Customer satisfaction ratings
        # - On-time delivery rate
        # - Product quality metrics
        
        # Calculate compliance score based on:
        # - Document completeness
        # - Policy adherence
        # - Regulatory compliance
        
        self.performance_score = 85.0  # Placeholder
        self.compliance_score = 90.0     # Placeholder
        self.save()
        
        return self.performance_score, self.compliance_score


class VendorWorkflowAuditLog(models.Model):
    """Comprehensive audit log for all vendor workflow actions"""
    
    workflow_state = models.ForeignKey(
        VendorWorkflowState,
        on_delete=models.CASCADE,
        related_name='audit_logs'
    )
    from_status = models.CharField(max_length=30, blank=True, null=True)
    to_status = models.CharField(max_length=30, blank=True, null=True)
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vendor_workflow_actions'
    )
    action_type = models.CharField(
        max_length=50,
        choices=[
            ('status_change', 'Status Change'),
            ('escalation', 'Case Escalation'),
            ('review', 'Review Action'),
            ('compliance_check', 'Compliance Check'),
            ('performance_update', 'Performance Update'),
        ],
        default='status_change'
    )
    reason = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Vendor Workflow Audit Log"
        verbose_name_plural = "Vendor Workflow Audit Logs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['workflow_state', 'created_at']),
            models.Index(fields=['performed_by', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.workflow_state} - {self.action_type} at {self.created_at}"


class VendorComplianceCheck(models.Model):
    """Automated compliance checking system"""
    
    CHECK_TYPES = [
        ('document_verification', 'Document Verification'),
        ('business_license', 'Business License Validation'),
        ('tax_id_verification', 'Tax ID Verification'),
        ('bank_account_validation', 'Bank Account Validation'),
        ('reference_check', 'Reference Check'),
        ('performance_review', 'Performance Review'),
        ('policy_compliance', 'Policy Compliance'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    workflow_state = models.ForeignKey(
        VendorWorkflowState,
        on_delete=models.CASCADE,
        related_name='compliance_checks'
    )
    check_type = models.CharField(max_length=30, choices=CHECK_TYPES)
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    
    # Check results
    is_passed = models.BooleanField(default=False)
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    details = models.JSONField(
        default=dict,
        help_text="Detailed check results and findings"
    )
    
    # Manual override
    manually_overridden = models.BooleanField(default=False)
    override_reason = models.TextField(blank=True, null=True)
    overridden_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='overridden_compliance_checks'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Vendor Compliance Check"
        verbose_name_plural = "Vendor Compliance Checks"
        unique_together = ['workflow_state', 'check_type']
        indexes = [
            models.Index(fields=['workflow_state', 'check_type']),
            models.Index(fields=['is_passed', 'priority']),
        ]
    
    def __str__(self):
        return f"{self.workflow_state} - {self.get_check_type_display()}"
    
    def perform_check(self):
        """Execute the compliance check"""
        try:
            # Document verification check
            if self.check_type == 'document_verification':
                self.score = self._check_document_completeness()
            
            # Business license validation
            elif self.check_type == 'business_license':
                self.score = self._check_business_license()
            
            # Tax ID verification
            elif self.check_type == 'tax_id_verification':
                self.score = self._check_tax_id()
            
            # Bank account validation
            elif self.check_type == 'bank_account_validation':
                self.score = self._check_bank_details()
            
            # Performance review
            elif self.check_type == 'performance_review':
                self.score = self._check_performance_metrics()
            
            # Policy compliance
            elif self.check_type == 'policy_compliance':
                self.score = self._check_policy_compliance()
            
            self.is_passed = self.score >= 70.0  # 70% pass threshold
            self.completed_at = timezone.now()
            self.save()
            
            # Update workflow compliance score
            self.workflow_state.calculate_performance_metrics()
            
            return self.is_passed
            
        except Exception as e:
            logger.error(f"Compliance check failed for {self}: {str(e)}")
            self.details['error'] = str(e)
            self.save()
            return False
    
    def _check_document_completeness(self):
        """Check if all required documents are uploaded"""
        application = self.workflow_state.vendor_application
        
        required_docs = [
            application.cr_document,
            application.business_license,
            application.bank_statement
        ]
        
        uploaded_docs = sum(1 for doc in required_docs if doc)
        score = (uploaded_docs / len(required_docs)) * 100
        
        self.details = {
            'uploaded_documents': uploaded_docs,
            'total_required': len(required_docs),
            'missing_documents': [
                doc_name for doc_name, doc in zip(
                    ['CR Document', 'Business License', 'Bank Statement'],
                    required_docs
                ) if not doc
            ]
        }
        
        return score
    
    def _check_business_license(self):
        """Validate business license information"""
        application = self.workflow_state.vendor_application
        
        score = 0
        checks = []
        
        if application.commercial_registration_number:
            score += 30
            checks.append("Commercial registration number provided")
        
        if application.business_license:
            score += 40
            checks.append("Business license document uploaded")
        
        if application.legal_identifier:
            score += 30
            checks.append("Legal identifier (Tax ID) provided")
        
        self.details = {
            'score_breakdown': checks,
            'total_score': score
        }
        
        return score
    
    def _check_tax_id(self):
        """Validate tax ID format and uniqueness"""
        application = self.workflow_state.vendor_application
        
        if not application.legal_identifier:
            self.details = {'error': 'No tax ID provided'}
            return 0
        
        # Basic format validation (would integrate with tax authority APIs)
        tax_id = application.legal_identifier
        is_valid_format = len(tax_id) >= 8 and tax_id.isalnum()
        
        # Check for duplicates in approved vendors
        from .models import VendorApplication
        duplicate_count = VendorApplication.objects.filter(
            legal_identifier=tax_id,
            status='approved'
        ).exclude(id=application.id).count()
        
        score = 100 if is_valid_format and duplicate_count == 0 else 50
        
        self.details = {
            'tax_id_format_valid': is_valid_format,
            'duplicate_count': duplicate_count,
            'tax_id_length': len(tax_id)
        }
        
        return score
    
    def _check_bank_details(self):
        """Validate bank account information"""
        application = self.workflow_state.vendor_application
        
        score = 0
        checks = []
        
        if application.bank_name:
            score += 20
            checks.append("Bank name provided")
        
        if application.account_holder_name:
            score += 20
            checks.append("Account holder name provided")
        
        if application.account_number:
            score += 20
            checks.append("Account number provided")
        
        if application.iban:
            # Basic IBAN validation
            if len(application.iban) >= 15:
                score += 20
                checks.append("Valid IBAN format")
        
        if application.swift_code:
            score += 20
            checks.append("SWIFT code provided")
        
        self.details = {
            'score_breakdown': checks,
            'total_score': score
        }
        
        return score
    
    def _check_performance_metrics(self):
        """Check vendor performance metrics"""
        # Placeholder - would integrate with actual performance data
        score = 85.0  # Default score
        
        self.details = {
            'fulfillment_rate': 95.0,
            'customer_satisfaction': 4.2,
            'on_time_delivery': 88.0,
            'quality_score': 92.0
        }
        
        return score
    
    def _check_policy_compliance(self):
        """Check adherence to platform policies"""
        # Placeholder - would check against policy database
        score = 90.0  # Default score
        
        self.details = {
            'terms_accepted': True,
            'privacy_policy_accepted': True,
            'vendor_agreement_signed': True,
            'compliance_training_completed': True
        }
        
        return score


class VendorPriorityQueue(models.Model):
    """Priority queue system for vendor applications requiring attention"""
    
    PRIORITY_LEVELS = [
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
        (4, 'Critical'),
        (5, 'Urgent'),
    ]
    
    QUEUE_TYPES = [
        ('new_application', 'New Application'),
        ('escalated_review', 'Escalated Review'),
        ('compliance_issue', 'Compliance Issue'),
        ('performance_review', 'Performance Review'),
        ('renewal_required', 'Renewal Required'),
    ]
    
    workflow_state = models.ForeignKey(
        VendorWorkflowState,
        on_delete=models.CASCADE,
        related_name='priority_queue_entries'
    )
    queue_type = models.CharField(max_length=20, choices=QUEUE_TYPES)
    priority = models.PositiveSmallIntegerField(
        choices=PRIORITY_LEVELS,
        default=3
    )
    
    # Flagging reasons
    flag_reason = models.TextField(
        help_text="Reason for flagging this application"
    )
    auto_flagged = models.BooleanField(
        default=True,
        help_text="Whether this was auto-flagged by the system"
    )
    
    # Assignment and tracking
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_vendor_reviews'
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    
    # Status tracking
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_vendor_reviews'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Vendor Priority Queue"
        verbose_name_plural = "Vendor Priority Queues"
        ordering = ['-priority', 'created_at']
        indexes = [
            models.Index(fields=['queue_type', 'priority', 'is_resolved']),
            models.Index(fields=['assigned_to', 'is_resolved']),
        ]
    
    def __str__(self):
        return f"{self.workflow_state} - {self.get_queue_type_display()} (P{self.priority})"
    
    def assign_to_user(self, user):
        """Assign this queue item to a user"""
        self.assigned_to = user
        self.assigned_at = timezone.now()
        self.save()
        
        logger.info(
            f"Vendor review {self.workflow_state.vendor_application.application_id} "
            f"assigned to {user}"
        )
    
    def resolve(self, user, resolution_notes=None):
        """Mark this queue item as resolved"""
        self.is_resolved = True
        self.resolved_at = timezone.now()
        self.resolved_by = user
        
        if resolution_notes:
            self.flag_reason += f"\n\nResolution: {resolution_notes}"
        
        self.save()
        
        logger.info(
            f"Vendor review {self.workflow_state.vendor_application.application_id} "
            f"resolved by {user}"
        )