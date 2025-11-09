from rest_framework import permissions


class IsInquiryOwnerOrListingOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of an inquiry or listing owners to access it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any authenticated user who is either:
        # - The inquiry sender (obj.user)
        # - The listing owner (obj.listing.user)
        if request.method in permissions.SAFE_METHODS:
            return (
                obj.user == request.user or 
                obj.listing.user == request.user
            )

        # Write permissions are only allowed to the listing owner for status updates
        # or the inquiry sender for their own inquiries
        if hasattr(obj, 'listing'):
            return (
                obj.user == request.user or 
                obj.listing.user == request.user
            )
        
        return False


class IsListingOwner(permissions.BasePermission):
    """
    Custom permission to only allow listing owners to manage inquiries for their listings.
    """

    def has_object_permission(self, request, view, obj):
        # Check if the user owns the listing associated with the inquiry
        if hasattr(obj, 'listing'):
            return obj.listing.user == request.user
        elif hasattr(obj, 'inquiry'):
            # For responses and test drives
            return obj.inquiry.listing.user == request.user
        
        return False


class IsResponseOwnerOrInquiryParticipant(permissions.BasePermission):
    """
    Custom permission for inquiry responses.
    """

    def has_object_permission(self, request, view, obj):
        # Allow access to:
        # - The response author
        # - The inquiry sender
        # - The listing owner
        return (
            obj.responder == request.user or
            obj.inquiry.user == request.user or
            obj.inquiry.listing.user == request.user
        )


class CanCreateInquiry(permissions.BasePermission):
    """
    Permission to check if user can create inquiries.
    """

    def has_permission(self, request, view):
        # Authenticated users can create inquiries
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Users can only edit their own inquiries
        return obj.user == request.user


class CanManageTestDrive(permissions.BasePermission):
    """
    Permission for test drive management.
    """

    def has_object_permission(self, request, view, obj):
        # Allow access to:
        # - The inquiry sender (for viewing their test drive requests)
        # - The listing owner (for managing test drive requests)
        return (
            obj.inquiry.user == request.user or
            obj.inquiry.listing.user == request.user
        )


class IsDealerRole(permissions.BasePermission):
    """
    Custom permission to only allow users with dealer role.
    """

    def has_permission(self, request, view):
        # Check if user is authenticated and has dealer role
        from users.models import UserRole
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == UserRole.SELLER
        )