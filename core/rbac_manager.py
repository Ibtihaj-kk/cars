"""
Role-Based Access Control (RBAC) Manager
Handles permission checking and role management
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone
from .rbac_models import (
    Permission, Role, UserRoleAssignment, UserPermission, 
    RolePermission, PermissionAuditLog
)
import logging

logger = logging.getLogger('rbac')
User = get_user_model()


class RBACManager:
    """Central manager for RBAC operations."""
    
    CACHE_PREFIX = 'rbac'
    CACHE_TIMEOUT = 300  # 5 minutes
    
    def __init__(self):
        self._permission_cache = {}
    
    def _get_cache_key(self, user_id, permission_codename):
        """Generate cache key for user permission."""
        return f"{self.CACHE_PREFIX}:user:{user_id}:perm:{permission_codename}"
    
    def _get_role_cache_key(self, user_id):
        """Generate cache key for user roles."""
        return f"{self.CACHE_PREFIX}:user:{user_id}:roles"
    
    def clear_user_cache(self, user_id):
        """Clear all cached permissions for a user."""
        cache_key_pattern = f"{self.CACHE_PREFIX}:user:{user_id}:*"
        cache.delete_pattern(cache_key_pattern)
        logger.info(f"Cleared RBAC cache for user {user_id}")
    
    def get_user_permissions(self, user):
        """Get all effective permissions for a user (role + direct)."""
        if not user or not user.is_authenticated:
            return set()
        
        # Get permissions from active roles
        role_perms = self._get_role_permissions(user)
        
        # Get direct permissions (overrides)
        direct_perms = self._get_direct_permissions(user)
        
        # Apply direct permission overrides
        effective_perms = role_perms.copy()
        
        for perm_codename, is_grant in direct_perms.items():
            if is_grant:
                effective_perms.add(perm_codename)
            else:
                effective_perms.discard(perm_codename)
        
        return effective_perms
    
    def _get_role_permissions(self, user):
        """Get permissions from user's active role assignments."""
        permissions = set()
        
        # Get active role assignments
        role_assignments = UserRoleAssignment.objects.filter(
            user=user,
            is_active=True
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        )
        
        for assignment in role_assignments:
            role_perms = RolePermission.objects.filter(
                role=assignment.role,
                is_active=True
            ).filter(
                Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
            ).select_related('permission')
            
            for role_perm in role_perms:
                permissions.add(role_perm.permission.codename)
        
        return permissions
    
    def _get_direct_permissions(self, user):
        """Get direct user permissions (overrides)."""
        permissions = {}
        
        direct_perms = UserPermission.objects.filter(
            user=user
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        ).select_related('permission')
        
        for perm in direct_perms:
            permissions[perm.permission.codename] = perm.is_grant
        
        return permissions
    
    def has_permission(self, user, permission_codename, use_cache=True):
        """Check if user has a specific permission."""
        if not user or not user.is_authenticated:
            return False
        
        # Superusers have all permissions
        if user.is_superuser:
            return True
        
        # Check cache first
        if use_cache:
            cache_key = self._get_cache_key(user.id, permission_codename)
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
        
        # Get effective permissions
        user_permissions = self.get_user_permissions(user)
        has_perm = permission_codename in user_permissions
        
        # Cache the result
        if use_cache:
            cache.set(cache_key, has_perm, self.CACHE_TIMEOUT)
        
        # Log permission check
        PermissionAuditLog.log_action(
            action='permission_check',
            user=user,
            permission=Permission.objects.filter(codename=permission_codename).first(),
            details={
                'permission_codename': permission_codename,
                'result': has_perm,
                'cached': use_cache
            },
            success=has_perm
        )
        
        return has_perm
    
    def has_module_permission(self, user, module):
        """Check if user has any permission in a module."""
        if not user or not user.is_authenticated:
            return False
        
        if user.is_superuser:
            return True
        
        user_permissions = self.get_user_permissions(user)
        module_perms = Permission.objects.filter(
            module=module,
            codename__in=user_permissions
        ).exists()
        
        return module_perms
    
    def has_object_permission(self, user, permission_codename, obj):
        """Check object-level permission (with context awareness)."""
        if not user or not user.is_authenticated:
            return False
        
        if user.is_superuser:
            return True
        
        # Basic permission check
        if not self.has_permission(user, permission_codename):
            return False
        
        # Get user's role assignments with context
        role_assignments = UserRoleAssignment.objects.filter(
            user=user,
            is_active=True
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        )
        
        # Check contextual scope
        for assignment in role_assignments:
            context = assignment.context_scope or {}
            
            # Example: Check if user has vendor-specific access
            if hasattr(obj, 'vendor_id') and 'vendor_id' in context:
                if obj.vendor_id == context['vendor_id']:
                    return True
            
            # Example: Check department-based access
            if hasattr(obj, 'department_id') and 'department_id' in context:
                if obj.department_id == context['department_id']:
                    return True
        
        return True
    
    def assign_role(self, user, role, assigned_by=None, expires_at=None, context_scope=None):
        """Assign a role to a user."""
        try:
            assignment, created = UserRoleAssignment.objects.get_or_create(
                user=user,
                role=role,
                defaults={
                    'assigned_by': assigned_by,
                    'expires_at': expires_at,
                    'context_scope': context_scope or {}
                }
            )
            
            if not created:
                # Update existing assignment
                assignment.is_active = True
                assignment.assigned_by = assigned_by
                assignment.expires_at = expires_at
                assignment.context_scope = context_scope or {}
                assignment.save()
            
            # Clear user's permission cache
            self.clear_user_cache(user.id)
            
            # Log the action
            PermissionAuditLog.log_action(
                action='user_role_assigned',
                user=assigned_by,
                target_user=user,
                role=role,
                details={
                    'expires_at': expires_at.isoformat() if expires_at else None,
                    'context_scope': context_scope
                }
            )
            
            logger.info(f"Role '{role.name}' assigned to user {user.email}")
            return assignment
            
        except Exception as e:
            logger.error(f"Error assigning role to user {user.email}: {str(e)}")
            raise
    
    def revoke_role(self, user, role, revoked_by=None):
        """Revoke a role from a user."""
        try:
            assignment = UserRoleAssignment.objects.filter(
                user=user,
                role=role,
                is_active=True
            ).first()
            
            if assignment:
                assignment.is_active = False
                assignment.save()
                
                # Clear user's permission cache
                self.clear_user_cache(user.id)
                
                # Log the action
                PermissionAuditLog.log_action(
                    action='user_role_revoked',
                    user=revoked_by,
                    target_user=user,
                    role=role
                )
                
                logger.info(f"Role '{role.name}' revoked from user {user.email}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error revoking role from user {user.email}: {str(e)}")
            raise
    
    def grant_permission(self, user, permission, granted_by=None, expires_at=None, reason=None):
        """Grant a direct permission to a user."""
        try:
            user_perm, created = UserPermission.objects.get_or_create(
                user=user,
                permission=permission,
                defaults={
                    'granted_by': granted_by,
                    'expires_at': expires_at,
                    'reason': reason,
                    'is_grant': True
                }
            )
            
            if not created:
                user_perm.is_grant = True
                user_perm.granted_by = granted_by
                user_perm.expires_at = expires_at
                user_perm.reason = reason
                user_perm.save()
            
            # Clear user's permission cache
            self.clear_user_cache(user.id)
            
            # Log the action
            PermissionAuditLog.log_action(
                action='user_permission_granted',
                user=granted_by,
                target_user=user,
                permission=permission,
                details={
                    'expires_at': expires_at.isoformat() if expires_at else None,
                    'reason': reason
                }
            )
            
            logger.info(f"Permission '{permission.codename}' granted to user {user.email}")
            return user_perm
            
        except Exception as e:
            logger.error(f"Error granting permission to user {user.email}: {str(e)}")
            raise
    
    def revoke_permission(self, user, permission, revoked_by=None):
        """Revoke a direct permission from a user."""
        try:
            user_perm = UserPermission.objects.filter(
                user=user,
                permission=permission
            ).first()
            
            if user_perm:
                user_perm.is_grant = False
                user_perm.save()
                
                # Clear user's permission cache
                self.clear_user_cache(user.id)
                
                # Log the action
                PermissionAuditLog.log_action(
                    action='user_permission_revoked',
                    user=revoked_by,
                    target_user=user,
                    permission=permission
                )
                
                logger.info(f"Permission '{permission.codename}' revoked from user {user.email}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error revoking permission from user {user.email}: {str(e)}")
            raise


# Global RBAC manager instance
rbac_manager = RBACManager()