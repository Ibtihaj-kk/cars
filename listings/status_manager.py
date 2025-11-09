"""
Status management system for vehicle listings with workflow controls.
"""
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction
from .models import VehicleListing, ListingStatus


class ListingStatusManager:
    """Manages status transitions and workflow for vehicle listings."""
    
    # Define allowed status transitions
    ALLOWED_TRANSITIONS = {
        ListingStatus.DRAFT: [ListingStatus.PENDING_REVIEW, ListingStatus.PUBLISHED],
        ListingStatus.PENDING_REVIEW: [ListingStatus.PUBLISHED, ListingStatus.REJECTED, ListingStatus.DRAFT],
        ListingStatus.PUBLISHED: [ListingStatus.SOLD, ListingStatus.EXPIRED, ListingStatus.SUSPENDED, ListingStatus.DRAFT],
        ListingStatus.REJECTED: [ListingStatus.DRAFT, ListingStatus.PENDING_REVIEW],
        ListingStatus.SOLD: [ListingStatus.PUBLISHED],  # Allow republishing if sale falls through
        ListingStatus.EXPIRED: [ListingStatus.PUBLISHED, ListingStatus.DRAFT],
        ListingStatus.SUSPENDED: [ListingStatus.PUBLISHED, ListingStatus.DRAFT],
    }
    
    # Status descriptions for user feedback
    STATUS_DESCRIPTIONS = {
        ListingStatus.DRAFT: "Listing is being prepared and not visible to public",
        ListingStatus.PENDING_REVIEW: "Listing is under review by administrators",
        ListingStatus.PUBLISHED: "Listing is live and visible to public",
        ListingStatus.REJECTED: "Listing was rejected and needs modifications",
        ListingStatus.SOLD: "Vehicle has been sold",
        ListingStatus.EXPIRED: "Listing has expired and is no longer active",
        ListingStatus.SUSPENDED: "Listing has been suspended by administrators",
    }
    
    @classmethod
    def can_transition(cls, from_status, to_status):
        """Check if a status transition is allowed."""
        return to_status in cls.ALLOWED_TRANSITIONS.get(from_status, [])
    
    @classmethod
    def get_allowed_transitions(cls, current_status):
        """Get all allowed transitions from current status."""
        return cls.ALLOWED_TRANSITIONS.get(current_status, [])
    
    @classmethod
    def get_status_description(cls, status):
        """Get description for a status."""
        return cls.STATUS_DESCRIPTIONS.get(status, "Unknown status")
    
    @classmethod
    @transaction.atomic
    def change_status(cls, listing, new_status, user=None, reason=None):
        """
        Change listing status with validation and logging.
        
        Args:
            listing: VehicleListing instance
            new_status: New status to transition to
            user: User making the change (optional)
            reason: Reason for status change (optional)
            
        Returns:
            bool: True if status changed successfully
            
        Raises:
            ValidationError: If transition is not allowed
        """
        if not isinstance(listing, VehicleListing):
            raise ValueError("listing must be a VehicleListing instance")
        
        current_status = listing.status
        
        # Check if transition is allowed
        if not cls.can_transition(current_status, new_status):
            allowed = cls.get_allowed_transitions(current_status)
            raise ValidationError(
                f"Cannot transition from {current_status} to {new_status}. "
                f"Allowed transitions: {allowed}"
            )
        
        # Validate specific transition requirements
        cls._validate_transition_requirements(listing, new_status, reason)
        
        # Update listing status
        old_status = listing.status
        listing.status = new_status
        
        # Handle status-specific logic
        cls._handle_status_change_logic(listing, old_status, new_status)
        
        # Save the listing
        listing.save(update_fields=['status', 'published_at', 'rejection_reason'])
        
        # Log the status change
        cls._log_status_change(listing, old_status, new_status, user, reason)
        
        return True
    
    @classmethod
    def _validate_transition_requirements(cls, listing, new_status, reason):
        """Validate specific requirements for status transitions."""
        
        if new_status == ListingStatus.PUBLISHED:
            # Validate listing is complete before publishing
            if not listing.title or not listing.description:
                raise ValidationError("Title and description are required for publishing")
            
            if not listing.price or listing.price <= 0:
                raise ValidationError("Valid price is required for publishing")
            
            if not listing.make or not listing.model:
                raise ValidationError("Vehicle make and model are required for publishing")
        
        elif new_status == ListingStatus.REJECTED:
            # Rejection requires a reason
            if not reason:
                raise ValidationError("Rejection reason is required")
        
        elif new_status == ListingStatus.SOLD:
            # Only published listings can be marked as sold
            if listing.status != ListingStatus.PUBLISHED:
                raise ValidationError("Only published listings can be marked as sold")
    
    @classmethod
    def _handle_status_change_logic(cls, listing, old_status, new_status):
        """Handle status-specific logic during transitions."""
        
        if new_status == ListingStatus.PUBLISHED:
            # Set published timestamp
            if not listing.published_at:
                listing.published_at = timezone.now()
            
            # Clear rejection reason if previously rejected
            if old_status == ListingStatus.REJECTED:
                listing.rejection_reason = None
        
        elif new_status == ListingStatus.REJECTED:
            # Clear published timestamp
            listing.published_at = None
        
        elif new_status == ListingStatus.DRAFT:
            # Clear published timestamp and rejection reason
            listing.published_at = None
            listing.rejection_reason = None
    
    @classmethod
    def _log_status_change(cls, listing, old_status, new_status, user, reason):
        """Log status changes for audit trail."""
        # Import here to avoid circular imports
        from .models import ListingStatusLog
        
        try:
            ListingStatusLog.objects.create(
                listing=listing,
                old_status=old_status,
                new_status=new_status,
                changed_by=user,
                reason=reason or f"Status changed from {old_status} to {new_status}",
                timestamp=timezone.now()
            )
        except Exception as e:
            # Log the error but don't fail the status change
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to log status change: {e}")
    
    @classmethod
    def auto_expire_listings(cls):
        """
        Auto-expire published listings that have passed their expiry date.
        This method should be called by a scheduled task.
        """
        from django.db.models import Q
        
        now = timezone.now()
        expired_listings = VehicleListing.objects.filter(
            status=ListingStatus.PUBLISHED,
            expires_at__lt=now
        )
        
        expired_count = 0
        for listing in expired_listings:
            try:
                cls.change_status(
                    listing, 
                    ListingStatus.EXPIRED, 
                    reason="Automatically expired"
                )
                expired_count += 1
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to expire listing {listing.id}: {e}")
        
        return expired_count
    
    @classmethod
    def get_status_statistics(cls):
        """Get statistics about listing statuses."""
        from django.db.models import Count
        
        stats = VehicleListing.objects.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        return {stat['status']: stat['count'] for stat in stats}
    
    @classmethod
    def bulk_status_change(cls, listing_ids, new_status, user=None, reason=None):
        """
        Change status for multiple listings.
        
        Returns:
            dict: Results with success and failure counts
        """
        results = {
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        listings = VehicleListing.objects.filter(id__in=listing_ids)
        
        for listing in listings:
            try:
                cls.change_status(listing, new_status, user, reason)
                results['success'] += 1
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'listing_id': listing.id,
                    'error': str(e)
                })
        
        return results


class ListingWorkflowMixin:
    """Mixin to add workflow methods to VehicleListing model."""
    
    def can_transition_to(self, status):
        """Check if this listing can transition to the given status."""
        return ListingStatusManager.can_transition(self.status, status)
    
    def get_allowed_transitions(self):
        """Get allowed status transitions for this listing."""
        return ListingStatusManager.get_allowed_transitions(self.status)
    
    def change_status(self, new_status, user=None, reason=None):
        """Change status of this listing."""
        return ListingStatusManager.change_status(self, new_status, user, reason)
    
    def publish(self, user=None):
        """Publish this listing."""
        return self.change_status(ListingStatus.PUBLISHED, user)
    
    def reject(self, reason, user=None):
        """Reject this listing with a reason."""
        return self.change_status(ListingStatus.REJECTED, user, reason)
    
    def mark_as_sold(self, user=None):
        """Mark this listing as sold."""
        return self.change_status(ListingStatus.SOLD, user)
    
    def suspend(self, reason, user=None):
        """Suspend this listing."""
        return self.change_status(ListingStatus.SUSPENDED, user, reason)
    
    @property
    def is_editable(self):
        """Check if listing can be edited in current status."""
        return self.status in [ListingStatus.DRAFT, ListingStatus.REJECTED]
    
    @property
    def is_public(self):
        """Check if listing is visible to public."""
        return self.status == ListingStatus.PUBLISHED
    
    @property
    def needs_review(self):
        """Check if listing needs admin review."""
        return self.status == ListingStatus.PENDING_REVIEW