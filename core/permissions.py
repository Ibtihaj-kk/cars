from rest_framework import permissions


class IsAdminUser(permissions.BasePermission):
    """Allow access only to admin users."""
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)


class IsAdminUserOrReadOnly(permissions.BasePermission):
    """Allow read-only access to all users, but write access only to admin users."""
    
    def has_permission(self, request, view):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to admin users
        return bool(request.user and request.user.is_staff)


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Allow read-only access to all users, but write access only to the owner."""
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner
        return obj.user == request.user


class IsOwnerOrAdmin(permissions.BasePermission):
    """Allow access only to the owner or admin users."""
    
    def has_object_permission(self, request, view, obj):
        # Admin users can access any object
        if request.user and request.user.is_staff:
            return True
        
        # Owner can access their own objects
        return hasattr(obj, 'user') and obj.user == request.user


class IsOwner(permissions.BasePermission):
    """Allow access only to the owner."""
    
    def has_object_permission(self, request, view, obj):
        # Owner can access their own objects
        return hasattr(obj, 'user') and obj.user == request.user