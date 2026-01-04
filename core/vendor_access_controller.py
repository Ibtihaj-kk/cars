"""
ISO 27001 Compliant Vendor Access Controller
Enterprise-grade vendor approval state machine with granular access control
"""
import logging
from enum import Enum, auto
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger('security')


class VendorApprovalState(Enum):
    """ISO 27001 compliant vendor approval states"""
    PENDING = auto()           # Application submitted, under initial review
    UNDER_REVIEW = auto()      # Detailed review in progress
    REQUIRES_CHANGES = auto()  # Additional information/documents needed
    APPROVED = auto()          # Fully approved, full access granted
    REJECTED = auto()          # Application rejected
    SUSPENDED = auto()        # Temporarily suspended
    REVOKED = auto()          # Permanently revoked


class VendorAccessController:
    """NIST-compliant vendor access control with state-based permissions"""
    
    # ISO 27001 compliant access control matrix
    ACCESS_CONTROL_MATRIX = {
        VendorApprovalState.PENDING: {
            'access_level': 'limited',
            'allowed_actions': [
                'view_application_status',
                'upload_documents',
                'edit_contact_info',
                'complete_registration_steps',
                'communicate_with_support'
            ],
            'dashboard_access': 'registration_dashboard',
            'description': 'Application submitted, awaiting initial review'
        },
        VendorApprovalState.UNDER_REVIEW: {
            'access_level': 'restricted',
            'allowed_actions': [
                'view_application_status',
                'view_submitted_documents',
                'communicate_with_support',
                'respond_to_queries'
            ],
            'dashboard_access': 'status_dashboard',
            'description': 'Detailed review in progress'
        },
        VendorApprovalState.REQUIRES_CHANGES: {
            'access_level': 'corrective',
            'allowed_actions': [
                'view_application_status',
                'view_review_comments',
                'upload_requested_documents',
                'edit_business_details',
                'resubmit_application',
                'communicate_with_support'
            ],
            'dashboard_access': 'correction_dashboard',
            'description': 'Additional information/documents required'
        },
        VendorApprovalState.APPROVED: {
            'access_level': 'full',
            'allowed_actions': [
                'manage_listings',
                'process_orders',
                'access_reports',
                'manage_inventory',
                'view_financial_reports',
                'update_business_profile',
                'manage_documents',
                'communicate_with_customers'
            ],
            'dashboard_access': 'vendor_dashboard',
            'description': 'Fully approved with full access privileges'
        },
        VendorApprovalState.REJECTED: {
            'access_level': 'none',
            'allowed_actions': [
                'view_rejection_reasons',
                'appeal_decision',
                'contact_support'
            ],
            'dashboard_access': 'rejection_dashboard',
            'description': 'Application rejected'
        },
        VendorApprovalState.SUSPENDED: {
            'access_level': 'emergency',
            'allowed_actions': [
                'view_suspension_reasons',
                'contact_support',
                'appeal_suspension'
            ],
            'dashboard_access': 'suspended_dashboard',
            'description': 'Temporarily suspended pending investigation'
        },
        VendorApprovalState.REVOKED: {
            'access_level': 'terminated',
            'allowed_actions': [
                'view_revocation_reasons',
                'contact_support'
            ],
            'dashboard_access': 'revoked_dashboard',
            'description': 'Vendor privileges permanently revoked'
        }
    }
    
    # ISO 27001 compliant state transition rules
    STATE_TRANSITIONS = {
        VendorApprovalState.PENDING: [
            VendorApprovalState.UNDER_REVIEW,
            VendorApprovalState.REQUIRES_CHANGES,
            VendorApprovalState.REJECTED
        ],
        VendorApprovalState.UNDER_REVIEW: [
            VendorApprovalState.APPROVED,
            VendorApprovalState.REQUIRES_CHANGES,
            VendorApprovalState.REJECTED
        ],
        VendorApprovalState.REQUIRES_CHANGES: [
            VendorApprovalState.PENDING,
            VendorApprovalState.UNDER_REVIEW,
            VendorApprovalState.REJECTED
        ],
        VendorApprovalState.APPROVED: [
            VendorApprovalState.SUSPENDED,
            VendorApprovalState.REVOKED
        ],
        VendorApprovalState.SUSPENDED: [
            VendorApprovalState.APPROVED,
            VendorApprovalState.REVOKED
        ],
        VendorApprovalState.REJECTED: [
            VendorApprovalState.APPEALED
        ]
    }
    
    def __init__(self):
        self.audit_logger = None  # Will be injected
    
    def check_vendor_access(self, user, required_action):
        """
        Check if vendor has access to perform specific action
        Implements principle of least privilege
        """
        if not user or not user.is_authenticated:
            return False
        
        # Super admin bypass with audit logging
        if user.is_superuser:
            self._log_super_admin_access(user, required_action)
            return True
        
        # Get vendor profile and approval status
        vendor_profile = self._get_vendor_profile(user)
        if not vendor_profile:
            return False
        
        approval_state = vendor_profile.approval_status
        state_config = self.ACCESS_CONTROL_MATRIX.get(approval_state, {})
        
        # Check if action is allowed in current state
        allowed_actions = state_config.get('allowed_actions', [])
        
        return required_action in allowed_actions
    
    def get_vendor_dashboard_url(self, user):
        """Get appropriate dashboard URL based on vendor approval state"""
        vendor_profile = self._get_vendor_profile(user)
        if not vendor_profile:
            return None
        
        approval_state = vendor_profile.approval_status
        state_config = self.ACCESS_CONTROL_MATRIX.get(approval_state, {})
        
        return state_config.get('dashboard_access')
    
    def can_transition_state(self, current_state, target_state):
        """Check if state transition is valid"""
        allowed_transitions = self.STATE_TRANSITIONS.get(current_state, [])
        return target_state in allowed_transitions
    
    def transition_vendor_state(self, vendor_profile, target_state, reason, actor):
        """
        Perform secure state transition with audit trail
        """
        current_state = vendor_profile.approval_status
        
        if not self.can_transition_state(current_state, target_state):
            raise InvalidStateTransitionError(
                f"Invalid state transition from {current_state} to {target_state}"
            )
        
        # Perform state transition
        vendor_profile.approval_status = target_state
        vendor_profile.approval_status_changed = timezone.now()
        vendor_profile.save()
        
        # Log state transition for audit purposes
        self._log_state_transition(
            vendor_profile, current_state, target_state, reason, actor
        )
        
        # Trigger state-specific actions
        self._handle_state_transition(vendor_profile, current_state, target_state)
        
        return True
    
    def get_vendor_access_level(self, user):
        """Get vendor's current access level"""
        vendor_profile = self._get_vendor_profile(user)
        if not vendor_profile:
            return 'none'
        
        approval_state = vendor_profile.approval_status
        state_config = self.ACCESS_CONTROL_MATRIX.get(approval_state, {})
        
        return state_config.get('access_level', 'none')
    
    def get_available_actions(self, user):
        """Get all actions available to vendor in current state"""
        vendor_profile = self._get_vendor_profile(user)
        if not vendor_profile:
            return []
        
        approval_state = vendor_profile.approval_status
        state_config = self.ACCESS_CONTROL_MATRIX.get(approval_state, {})
        
        return state_config.get('allowed_actions', [])
    
    def _get_vendor_profile(self, user):
        """Get vendor profile with error handling"""
        try:
            if hasattr(user, 'vendor_profile'):
                return user.vendor_profile
            return None
        except Exception as e:
            logger.error(f"Error getting vendor profile: {str(e)}")
            return None
    
    def _log_state_transition(self, vendor_profile, from_state, to_state, reason, actor):
        """Log state transition for audit purposes"""
        if self.audit_logger:
            self.audit_logger.log_vendor_state_transition(
                vendor_profile, from_state, to_state, reason, actor
            )
    
    def _handle_state_transition(self, vendor_profile, from_state, to_state):
        """Handle state-specific transition actions"""
        # Notify vendor of state change
        self._notify_vendor_state_change(vendor_profile, from_state, to_state)
        
        # Update cache and session if needed
        self._update_access_cache(vendor_profile)
        
        # Trigger workflow actions based on state
        if to_state == VendorApprovalState.APPROVED:
            self._handle_approval(vendor_profile)
        elif to_state == VendorApprovalState.REJECTED:
            self._handle_rejection(vendor_profile)
        elif to_state == VendorApprovalState.SUSPENDED:
            self._handle_suspension(vendor_profile)
    
    def _notify_vendor_state_change(self, vendor_profile, from_state, to_state):
        """Notify vendor of state change"""
        # Implementation depends on your notification system
        pass
    
    def _update_access_cache(self, vendor_profile):
        """Update access control cache"""
        cache_key = f"vendor_access:{vendor_profile.id}"
        cache.set(cache_key, vendor_profile.approval_status, 3600)  # 1 hour cache
    
    def _handle_approval(self, vendor_profile):
        """Handle vendor approval actions"""
        # Activate vendor account
        # Send welcome package
        # Grant full access permissions
        pass
    
    def _handle_rejection(self, vendor_profile):
        """Handle vendor rejection actions"""
        # Deactivate vendor account
        # Send rejection notice
        # Remove access permissions
        pass
    
    def _handle_suspension(self, vendor_profile):
        """Handle vendor suspension actions"""
        # Temporarily disable access
        # Notify vendor of suspension
        # Preserve data for investigation
        pass
    
    def _log_super_admin_access(self, user, action):
        """Log super admin access for audit purposes"""
        if self.audit_logger:
            self.audit_logger.log_super_admin_access(user, action)


class InvalidStateTransitionError(Exception):
    """Exception for invalid state transitions"""
    pass


# Utility functions for easy access
def vendor_has_access(user, action):
    """Check if vendor has access to specific action"""
    controller = VendorAccessController()
    return controller.check_vendor_access(user, action)


def get_vendor_dashboard(user):
    """Get vendor dashboard URL"""
    controller = VendorAccessController()
    return controller.get_vendor_dashboard_url(user)


def can_vendor_perform(user, action):
    """Check if vendor can perform specific action"""
    return vendor_has_access(user, action)


def require_vendor_access(action):
    """Decorator to require vendor access to specific action"""
    def decorator(view_func):
        def wrapped_view(request, *args, **kwargs):
            if not vendor_has_access(request.user, action):
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied("Insufficient vendor access privileges")
            
            return view_func(request, *args, **kwargs)
        
        return wrapped_view
    return decorator