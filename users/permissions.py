from rest_framework import permissions
from .models import User, UserRole


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission to only allow owners of an object or admins to edit it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        
        # Write permissions are only allowed to the owner or admin
        if hasattr(obj, 'user'):
            return obj.user == request.user or request.user.role == UserRole.ADMIN
        
        return obj == request.user or request.user.role == UserRole.ADMIN


class IsAdminOrStaff(permissions.BasePermission):
    """
    Permission to only allow admin or staff users.
    """
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role in [UserRole.ADMIN, UserRole.STAFF]
        )


class IsAdmin(permissions.BasePermission):
    """
    Permission to only allow admin users.
    """
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role == UserRole.ADMIN
        )


class IsSeller(permissions.BasePermission):
    """
    Permission to only allow seller users.
    """
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role == UserRole.SELLER
        )


class IsBuyer(permissions.BasePermission):
    """
    Permission to only allow buyer users.
    """
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role == UserRole.CLIENT
        )


class IsSellerOrAdmin(permissions.BasePermission):
    """
    Permission to allow seller or admin users.
    """
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role in [UserRole.SELLER, UserRole.ADMIN]
        )


class IsActiveUser(permissions.BasePermission):
    """
    Permission to only allow active users (not banned, suspended, or deleted).
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Check if user is deleted, banned, or suspended
        if request.user.is_deleted:
            return False
        
        if request.user.is_banned:
            # Check if ban has expired
            if not request.user.is_ban_expired():
                return False
        
        if request.user.is_suspended:
            # Check if suspension has expired
            if not request.user.is_suspension_expired():
                return False
        
        return True


class CanManageUsers(permissions.BasePermission):
    """
    Permission for users who can manage other users (admin and staff).
    """
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role in [UserRole.ADMIN, UserRole.STAFF] and
            not request.user.is_deleted and
            not request.user.is_banned and
            not request.user.is_suspended
        )


class CanViewAuditLogs(permissions.BasePermission):
    """
    Permission for users who can view audit logs (admin only).
    """
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role == UserRole.ADMIN and
            not request.user.is_deleted and
            not request.user.is_banned and
            not request.user.is_suspended
        )