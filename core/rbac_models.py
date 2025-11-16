"""
Role-Based Access Control (RBAC) Models
Comprehensive permission system for fine-grained access control
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
import uuid

User = get_user_model()


class Permission(models.Model):
    """Custom permission model for RBAC system."""
    
    codename = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text="Associated Django model (optional)",
        related_name='core_permissions'
    )
    module = models.CharField(
        max_length=50,
        choices=[
            ('users', 'Users'),
            ('business_partners', 'Business Partners'),
            ('parts', 'Parts'),
            ('inventory', 'Inventory'),
            ('orders', 'Orders'),
            ('analytics', 'Analytics'),
            ('admin', 'Admin'),
            ('system', 'System'),
        ],
        help_text="Module this permission belongs to"
    )
    action = models.CharField(
        max_length=50,
        choices=[
            ('view', 'View'),
            ('create', 'Create'),
            ('update', 'Update'),
            ('delete', 'Delete'),
            ('manage', 'Manage'),
            ('approve', 'Approve'),
            ('reject', 'Reject'),
            ('export', 'Export'),
            ('import', 'Import'),
            ('configure', 'Configure'),
            ('audit', 'Audit'),
        ],
        help_text="Action this permission allows"
    )
    is_system = models.BooleanField(default=False, help_text="System permission that cannot be deleted")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['module', 'action', 'name']
        indexes = [
            models.Index(fields=['module', 'action']),
            models.Index(fields=['content_type']),
        ]
    
    def __str__(self):
        return f"{self.module}.{self.action}: {self.name}"


class Role(models.Model):
    """Role model for grouping permissions."""
    
    ROLE_TYPES = [
        ('admin', 'Administrator'),
        ('staff', 'Staff Member'),
        ('vendor_admin', 'Vendor Administrator'),
        ('vendor_manager', 'Vendor Manager'),
        ('vendor_user', 'Vendor User'),
        ('customer', 'Customer'),
        ('analyst', 'Analyst'),
        ('auditor', 'Auditor'),
        ('custom', 'Custom Role'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    role_type = models.CharField(max_length=20, choices=ROLE_TYPES, default='custom')
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, through='RolePermission', blank=True)
    is_system = models.BooleanField(default=False, help_text="System role that cannot be deleted")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_roles'
    )
    
    class Meta:
        ordering = ['role_type', 'name']
        indexes = [
            models.Index(fields=['role_type', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_role_type_display()})"
    
    def has_permission(self, permission_codename):
        """Check if role has a specific permission."""
        return self.permissions.filter(codename=permission_codename).exists()
    
    def get_permission_list(self):
        """Get all permissions for this role."""
        return list(self.permissions.all())


class RolePermission(models.Model):
    """Through model for Role-Permission relationship with additional metadata."""
    
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='granted_role_permissions'
    )
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['role', 'permission']
        indexes = [
            models.Index(fields=['role', 'permission']),
            models.Index(fields=['expires_at']),
        ]


class UserRoleAssignment(models.Model):
    """User-Role assignment with temporal support."""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='role_assignments')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_assignments')
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assigned_roles'
    )
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    context_scope = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Contextual scope for role (e.g., specific vendor, department, etc.)"
    )
    
    class Meta:
        unique_together = ['user', 'role']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['role', 'is_active']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.role.name}"
    
    def is_expired(self):
        """Check if role assignment has expired."""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False


class UserPermission(models.Model):
    """Direct user permissions (overrides role permissions)."""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='direct_permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='granted_direct_permissions'
    )
    is_grant = models.BooleanField(
        default=True,
        help_text="True for grant, False for explicit deny"
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    reason = models.TextField(blank=True, help_text="Reason for direct permission")
    
    class Meta:
        unique_together = ['user', 'permission']
        indexes = [
            models.Index(fields=['user', 'permission']),
            models.Index(fields=['expires_at']),
        ]


class PermissionAuditLog(models.Model):
    """Audit log for permission-related actions."""
    
    ACTION_TYPES = [
        ('permission_created', 'Permission Created'),
        ('permission_updated', 'Permission Updated'),
        ('permission_deleted', 'Permission Deleted'),
        ('role_created', 'Role Created'),
        ('role_updated', 'Role Updated'),
        ('role_deleted', 'Role Deleted'),
        ('role_permission_granted', 'Permission Granted to Role'),
        ('role_permission_revoked', 'Permission Revoked from Role'),
        ('user_role_assigned', 'Role Assigned to User'),
        ('user_role_revoked', 'Role Revoked from User'),
        ('user_permission_granted', 'Direct Permission Granted'),
        ('user_permission_revoked', 'Direct Permission Revoked'),
        ('permission_check', 'Permission Check Performed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.CharField(max_length=30, choices=ACTION_TYPES)
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='permission_audit_logs'
    )
    target_user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='target_permission_audit_logs'
    )
    role = models.ForeignKey(
        Role, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='audit_logs'
    )
    permission = models.ForeignKey(
        Permission, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='audit_logs'
    )
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['target_user', '-timestamp']),
            models.Index(fields=['role', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.timestamp}"
    
    @classmethod
    def log_action(cls, action, user=None, target_user=None, role=None, 
                   permission=None, details=None, request=None, success=True, 
                   error_message=None):
        """Create a permission audit log entry."""
        log_data = {
            'action': action,
            'user': user,
            'target_user': target_user,
            'role': role,
            'permission': permission,
            'details': details or {},
            'success': success,
            'error_message': error_message,
        }
        
        if request:
            log_data['ip_address'] = cls.get_client_ip(request)
            log_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        
        return cls.objects.create(**log_data)
    
    @staticmethod
    def get_client_ip(request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip