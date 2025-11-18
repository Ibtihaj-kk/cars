"""
Vendor audit logging utilities.
"""
import logging
from django.contrib.auth.models import User
from django.utils import timezone
from .models import BusinessPartner


logger = logging.getLogger('vendor_audit')


class VendorAuditLogger:
    """Centralized vendor audit logging"""
    
    @staticmethod
    def log_vendor_action(action_type, user, vendor, details=None):
        """
        Log vendor-related actions for security auditing.
        
        Args:
            action_type: Type of action (e.g., 'bank_details_updated', 'login_failed')
            user: User who performed the action
            vendor: BusinessPartner instance
            details: Additional details as dict
        """
        log_entry = {
            'timestamp': timezone.now().isoformat(),
            'action_type': action_type,
            'user_id': user.id if user else None,
            'user_email': user.email if user else None,
            'vendor_id': vendor.id if vendor else None,
            'vendor_name': vendor.name if vendor else None,
            'details': details or {},
            'ip_address': None,  # Will be set by middleware
            'user_agent': None,    # Will be set by middleware
        }
        
        # Log to security audit logger
        logger.info(f"VENDOR_AUDIT: {log_entry}")
        
        # Store in database for querying
        from .models import VendorAuditLog
        VendorAuditLog.objects.create(
            action_type=action_type,
            user=user,
            vendor=vendor,
            details=details or {},
            ip_address=log_entry['ip_address'],
            user_agent=log_entry['user_agent']
        )
    
    @staticmethod
    def log_login_attempt(username, success, vendor=None, ip_address=None, user_agent=None, failure_reason=None):
        """Log login attempts"""
        action_type = 'login_success' if success else 'login_failed'
        details = {
            'username': username,
            'failure_reason': failure_reason,
        }
        
        # Try to get user if login was successful
        user = None
        if success:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                pass
        
        VendorAuditLogger.log_vendor_action(
            action_type=action_type,
            user=user,
            vendor=vendor,
            details=details
        )
    
    @staticmethod
    def log_bank_details_access(user, vendor, accessed_fields):
        """Log bank details access for compliance"""
        VendorAuditLogger.log_vendor_action(
            action_type='bank_details_accessed',
            user=user,
            vendor=vendor,
            details={'accessed_fields': accessed_fields}
        )
    
    @staticmethod
    def log_file_upload(user, vendor, file_type, file_name, file_hash):
        """Log file uploads for security monitoring"""
        VendorAuditLogger.log_vendor_action(
            action_type='file_uploaded',
            user=user,
            vendor=vendor,
            details={
                'file_type': file_type,
                'file_name': file_name,
                'file_hash': file_hash,
                'file_size': None  # Will be set by upload handler
            }
        )
    
    @staticmethod
    def log_security_event(user, vendor, event_type, severity='medium', details=None):
        """Log security-related events"""
        VendorAuditLogger.log_vendor_action(
            action_type=f'security_{event_type}',
            user=user,
            vendor=vendor,
            details={
                'severity': severity,
                **(details or {})
            }
        )
    
    @staticmethod
    def log_rate_limit_exceeded(user, operation_type, ip_address=None, user_agent=None):
        """Log rate limit violations for security monitoring"""
        vendor = None
        if hasattr(user, 'vendorprofile'):
            vendor = user.vendorprofile.business_partner
        
        VendorAuditLogger.log_vendor_action(
            action_type='rate_limit_exceeded',
            user=user,
            vendor=vendor,
            details={
                'operation_type': operation_type,
                'ip_address': ip_address,
                'user_agent': user_agent
            }
        )
    
    @staticmethod
    def log_file_upload_validation(user, filename, file_size, file_hash, validation_result, error_message=None):
        """Log file upload validation results"""
        vendor = None
        if hasattr(user, 'vendorprofile'):
            vendor = user.vendorprofile.business_partner
        
        details = {
            'filename': filename,
            'file_size': file_size,
            'file_hash': file_hash,
            'validation_result': validation_result
        }
        
        if error_message:
            details['error_message'] = error_message
        
        VendorAuditLogger.log_vendor_action(
            action_type='file_upload_validation',
            user=user,
            vendor=vendor,
            details=details
        )