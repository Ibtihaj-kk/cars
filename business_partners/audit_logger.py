"""
Comprehensive audit logging system for vendor management.
"""
import json
import logging
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from django.db import models
from .models import VendorApplication, BusinessPartner
from .document_models import VendorDocument

logger = logging.getLogger('vendor_audit')


class VendorAuditLogger:
    """Centralized audit logger for vendor management operations."""
    
    # Audit action types
    ACTION_VENDOR_APPLICATION_SUBMITTED = 'vendor_application_submitted'
    ACTION_VENDOR_APPLICATION_REVIEWED = 'vendor_application_reviewed'
    ACTION_VENDOR_APPLICATION_APPROVED = 'vendor_application_approved'
    ACTION_VENDOR_APPLICATION_REJECTED = 'vendor_application_rejected'
    ACTION_VENDOR_APPLICATION_STATUS_CHANGED = 'vendor_application_status_changed'
    ACTION_VENDOR_DOCUMENT_UPLOADED = 'vendor_document_uploaded'
    ACTION_VENDOR_DOCUMENT_VERIFIED = 'vendor_document_verified'
    ACTION_VENDOR_DOCUMENT_REJECTED = 'vendor_document_rejected'
    ACTION_VENDOR_DOCUMENT_EXPIRED = 'vendor_document_expired'
    ACTION_VENDOR_PERFORMANCE_CALCULATED = 'vendor_performance_calculated'
    ACTION_VENDOR_PERFORMANCE_UPDATED = 'vendor_performance_updated'
    ACTION_VENDOR_COMPLIANCE_ALERT_CREATED = 'vendor_compliance_alert_created'
    ACTION_VENDOR_COMPLIANCE_ALERT_RESOLVED = 'vendor_compliance_alert_resolved'
    ACTION_VENDOR_STATUS_CHANGED = 'vendor_status_changed'
    ACTION_VENDOR_ROLE_ASSIGNED = 'vendor_role_assigned'
    ACTION_VENDOR_ROLE_REMOVED = 'vendor_role_removed'
    ACTION_VENDOR_DATA_UPDATED = 'vendor_data_updated'
    ACTION_VENDOR_ACCESS_GRANTED = 'vendor_access_granted'
    ACTION_VENDOR_ACCESS_REVOKED = 'vendor_access_revoked'
    ACTION_VENDOR_LOGIN = 'vendor_login'
    ACTION_VENDOR_LOGOUT = 'vendor_logout'
    ACTION_VENDOR_PASSWORD_CHANGED = 'vendor_password_changed'
    ACTION_VENDOR_PROFILE_UPDATED = 'vendor_profile_updated'
    ACTION_VENDOR_SETTINGS_UPDATED = 'vendor_settings_updated'
    ACTION_VENDOR_ANALYTICS_ACCESSED = 'vendor_analytics_accessed'
    ACTION_VENDOR_REPORT_GENERATED = 'vendor_report_generated'
    ACTION_VENDOR_EXPORT_CREATED = 'vendor_export_created'
    ACTION_VENDOR_IMPORT_PROCESSED = 'vendor_import_processed'
    ACTION_VENDOR_BULK_OPERATION = 'vendor_bulk_operation'
    ACTION_VENDOR_COMPLIANCE_CHECK = 'vendor_compliance_check'
    ACTION_VENDOR_PERFORMANCE_REVIEW = 'vendor_performance_review'
    ACTION_VENDOR_RATING_SUBMITTED = 'vendor_rating_submitted'
    ACTION_VENDOR_FEEDBACK_PROVIDED = 'vendor_feedback_provided'
    ACTION_VENDOR_DISPUTE_RAISED = 'vendor_dispute_raised'
    ACTION_VENDOR_DISPUTE_RESOLVED = 'vendor_dispute_resolved'
    ACTION_VENDOR_CONTRACT_CREATED = 'vendor_contract_created'
    ACTION_VENDOR_CONTRACT_UPDATED = 'vendor_contract_updated'
    ACTION_VENDOR_CONTRACT_TERMINATED = 'vendor_contract_terminated'
    ACTION_VENDOR_PAYMENT_PROCESSED = 'vendor_payment_processed'
    ACTION_VENDOR_PAYMENT_FAILED = 'vendor_payment_failed'
    ACTION_VENDOR_COMMISSION_CALCULATED = 'vendor_commission_calculated'
    ACTION_VENDOR_COMMISSION_PAID = 'vendor_commission_paid'
    
    @classmethod
    def log_vendor_action(cls, action_type, user, vendor=None, application=None, 
                         document=None, details=None, ip_address=None, 
                         user_agent=None, success=True, error_message=None):
        """Log a vendor-related action."""
        log_entry = {
            'timestamp': timezone.now().isoformat(),
            'action_type': action_type,
            'user_id': user.id if user else None,
            'username': user.username if user else None,
            'vendor_id': vendor.id if vendor else None,
            'vendor_name': vendor.company_name if vendor else None,
            'application_id': application.id if application else None,
            'document_id': document.id if document else None,
            'details': details or {},
            'ip_address': ip_address,
            'user_agent': user_agent,
            'success': success,
            'error_message': error_message
        }
        
        # Log to structured logger
        if success:
            logger.info(f"Vendor action: {action_type}", extra=log_entry)
        else:
            logger.error(f"Vendor action failed: {action_type}", extra=log_entry)
        
        # Store in database for complex queries
        try:
            VendorAuditLog.objects.create(
                action_type=action_type,
                user=user,
                vendor=vendor,
                vendor_application=application,
                vendor_document=document,
                details=json.dumps(details or {}),
                ip_address=ip_address,
                user_agent=user_agent,
                success=success,
                error_message=error_message
            )
        except Exception as e:
            logger.error(f"Failed to store audit log in database: {str(e)}", extra=log_entry)
    
    @classmethod
    def log_application_submission(cls, user, application, ip_address=None, user_agent=None):
        """Log vendor application submission."""
        details = {
            'company_name': application.company_name,
            'business_type': application.business_type,
            'contact_email': application.contact_email,
            'application_id': application.id
        }
        
        cls.log_vendor_action(
            cls.ACTION_VENDOR_APPLICATION_SUBMITTED,
            user,
            application=application,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @classmethod
    def log_application_review(cls, user, application, old_status, new_status, 
                              notes=None, ip_address=None, user_agent=None):
        """Log vendor application review."""
        details = {
            'application_id': application.id,
            'company_name': application.company_name,
            'old_status': old_status,
            'new_status': new_status,
            'notes': notes
        }
        
        cls.log_vendor_action(
            cls.ACTION_VENDOR_APPLICATION_REVIEWED,
            user,
            application=application,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @classmethod
    def log_application_approval(cls, user, application, ip_address=None, user_agent=None):
        """Log vendor application approval."""
        details = {
            'application_id': application.id,
            'company_name': application.company_name,
            'approval_date': application.reviewed_at.isoformat() if application.reviewed_at else None
        }
        
        cls.log_vendor_action(
            cls.ACTION_VENDOR_APPLICATION_APPROVED,
            user,
            application=application,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @classmethod
    def log_application_rejection(cls, user, application, rejection_reason, 
                                 ip_address=None, user_agent=None):
        """Log vendor application rejection."""
        details = {
            'application_id': application.id,
            'company_name': application.company_name,
            'rejection_reason': rejection_reason,
            'rejection_date': application.reviewed_at.isoformat() if application.reviewed_at else None
        }
        
        cls.log_vendor_action(
            cls.ACTION_VENDOR_APPLICATION_REJECTED,
            user,
            application=application,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @classmethod
    def log_document_upload(cls, user, vendor, document, ip_address=None, user_agent=None):
        """Log vendor document upload."""
        details = {
            'document_id': document.id,
            'document_name': document.document_name,
            'category': document.category.name if document.category else None,
            'file_size': document.file.size if document.file else None,
            'file_type': document.file.name.split('.')[-1] if document.file else None
        }
        
        cls.log_vendor_action(
            cls.ACTION_VENDOR_DOCUMENT_UPLOADED,
            user,
            vendor=vendor,
            document=document,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @classmethod
    def log_document_verification(cls, user, vendor, document, ip_address=None, user_agent=None):
        """Log vendor document verification."""
        details = {
            'document_id': document.id,
            'document_name': document.document_name,
            'category': document.category.name if document.category else None,
            'verification_date': document.verified_at.isoformat() if document.verified_at else None
        }
        
        cls.log_vendor_action(
            cls.ACTION_VENDOR_DOCUMENT_VERIFIED,
            user,
            vendor=vendor,
            document=document,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @classmethod
    def log_performance_calculation(cls, user, vendor, score_data, ip_address=None, user_agent=None):
        """Log vendor performance calculation."""
        details = {
            'vendor_id': vendor.id,
            'vendor_name': vendor.company_name,
            'score': score_data.get('overall_score'),
            'tier': score_data.get('tier'),
            'period_start': score_data.get('period_start'),
            'period_end': score_data.get('period_end')
        }
        
        cls.log_vendor_action(
            cls.ACTION_VENDOR_PERFORMANCE_CALCULATED,
            user,
            vendor=vendor,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @classmethod
    def log_vendor_status_change(cls, user, vendor, old_status, new_status, 
                                reason=None, ip_address=None, user_agent=None):
        """Log vendor status change."""
        details = {
            'vendor_id': vendor.id,
            'vendor_name': vendor.company_name,
            'old_status': old_status,
            'new_status': new_status,
            'reason': reason
        }
        
        cls.log_vendor_action(
            cls.ACTION_VENDOR_STATUS_CHANGED,
            user,
            vendor=vendor,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @classmethod
    def log_compliance_alert(cls, user, vendor, alert_type, severity, 
                            description, ip_address=None, user_agent=None):
        """Log vendor compliance alert."""
        details = {
            'vendor_id': vendor.id,
            'vendor_name': vendor.company_name,
            'alert_type': alert_type,
            'severity': severity,
            'description': description
        }
        
        cls.log_vendor_action(
            cls.ACTION_VENDOR_COMPLIANCE_ALERT_CREATED,
            user,
            vendor=vendor,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @classmethod
    def log_analytics_access(cls, user, analytics_type, filters=None, 
                           ip_address=None, user_agent=None):
        """Log vendor analytics access."""
        details = {
            'analytics_type': analytics_type,
            'filters': filters or {},
            'access_time': timezone.now().isoformat()
        }
        
        cls.log_vendor_action(
            cls.ACTION_VENDOR_ANALYTICS_ACCESSED,
            user,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @classmethod
    def log_bulk_operation(cls, user, operation_type, affected_count, 
                          details=None, ip_address=None, user_agent=None, success=True):
        """Log vendor bulk operation."""
        operation_details = {
            'operation_type': operation_type,
            'affected_count': affected_count,
            'details': details or {}
        }
        
        cls.log_vendor_action(
            cls.ACTION_VENDOR_BULK_OPERATION,
            user,
            details=operation_details,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success
        )


class VendorAuditLog(models.Model):
    """Database model for storing vendor audit logs."""
    
    ACTION_TYPES = [
        (getattr(VendorAuditLogger, attr), attr.replace('ACTION_VENDOR_', '').lower().replace('_', ' '))
        for attr in dir(VendorAuditLogger) 
        if attr.startswith('ACTION_VENDOR_')
    ]
    
    action_type = models.CharField(max_length=100, choices=ACTION_TYPES)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    vendor = models.ForeignKey(BusinessPartner, on_delete=models.SET_NULL, null=True, blank=True)
    vendor_application = models.ForeignKey(VendorApplication, on_delete=models.SET_NULL, null=True, blank=True)
    vendor_document = models.ForeignKey(VendorDocument, on_delete=models.SET_NULL, null=True, blank=True)
    
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action_type', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['vendor', 'created_at']),
            models.Index(fields=['success', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.action_type} by {self.user} at {self.created_at}"
    
    @property
    def action_display(self):
        """Get human-readable action name."""
        return dict(self.ACTION_TYPES).get(self.action_type, self.action_type)