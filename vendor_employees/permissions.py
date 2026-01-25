from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from .models import VendorEmployee, VendorPagePermission, VendorRole, VendorRolePermission
from .utils import get_vendor_context

DEFAULT_PAGE_PERMISSIONS = [
    {'code': 'dashboard', 'name': 'Dashboard Overview', 'category': 'General'},
    {'code': 'parts', 'name': 'Parts & Inventory', 'category': 'Inventory'},
    {'code': 'orders', 'name': 'Orders & Sales', 'category': 'Sales'},
    {'code': 'employees', 'name': 'Employees', 'category': 'Team Management'},
    {'code': 'roles', 'name': 'Roles', 'category': 'Team Management'},
    {'code': 'locations', 'name': 'Locations', 'category': 'Team Management'},
    {'code': 'vehicles', 'name': 'Vehicles', 'category': 'Inventory'},
    {'code': 'leads', 'name': 'Leads', 'category': 'Sales'},
    {'code': 'finance', 'name': 'Finance & Payments', 'category': 'General'},
    {'code': 'reports', 'name': 'Reports & Analytics', 'category': 'General'},
    {'code': 'settings', 'name': 'Vendor Settings', 'category': 'General'},
]

DEFAULT_ROLE_DEFINITIONS = [
    {
        'name': 'Owner',
        'description': 'Full access to all modules',
        'permissions': [
            {'code': 'dashboard', 'actions': ['view']},
            {'code': 'parts', 'actions': ['view', 'create', 'edit', 'delete']},
            {'code': 'orders', 'actions': ['view', 'create', 'edit', 'delete']},
            {'code': 'employees', 'actions': ['view', 'create', 'edit', 'delete']},
            {'code': 'roles', 'actions': ['view', 'create', 'edit', 'delete']},
            {'code': 'locations', 'actions': ['view', 'create', 'edit', 'delete']},
            {'code': 'vehicles', 'actions': ['view', 'create', 'edit', 'delete']},
            {'code': 'leads', 'actions': ['view', 'create', 'edit', 'delete']},
            {'code': 'finance', 'actions': ['view', 'create', 'edit', 'delete']},
            {'code': 'reports', 'actions': ['view']},
            {'code': 'settings', 'actions': ['view', 'edit']},
        ],
    },
    {
        'name': 'Manager',
        'description': 'Manage team and inventory',
        'permissions': [
            {'code': 'dashboard', 'actions': ['view']},
            {'code': 'parts', 'actions': ['view', 'create', 'edit']},
            {'code': 'orders', 'actions': ['view', 'create', 'edit']},
            {'code': 'employees', 'actions': ['view', 'create', 'edit']},
            {'code': 'roles', 'actions': ['view']},
            {'code': 'locations', 'actions': ['view', 'create', 'edit']},
            {'code': 'vehicles', 'actions': ['view', 'create', 'edit', 'delete']},
            {'code': 'leads', 'actions': ['view', 'create', 'edit']},
            {'code': 'finance', 'actions': ['view']},
            {'code': 'reports', 'actions': ['view']},
        ],
    },
    {
        'name': 'Viewer',
        'description': 'Read-only access',
        'permissions': [
            {'code': 'dashboard', 'actions': ['view']},
            {'code': 'parts', 'actions': ['view']},
            {'code': 'orders', 'actions': ['view']},
            {'code': 'employees', 'actions': ['view']},
            {'code': 'roles', 'actions': ['view']},
            {'code': 'locations', 'actions': ['view']},
            {'code': 'vehicles', 'actions': ['view']},
            {'code': 'leads', 'actions': ['view']},
            {'code': 'reports', 'actions': ['view']},
        ],
    },
]


def ensure_default_permissions():
    codes = [item['code'] for item in DEFAULT_PAGE_PERMISSIONS]
    existing = set(
        VendorPagePermission.objects.filter(vendor__isnull=True, code__in=codes).values_list('code', flat=True)
    )
    to_create = [
        VendorPagePermission(
            code=item['code'],
            name=item['name'],
            category=item['category']
        )
        for item in DEFAULT_PAGE_PERMISSIONS
        if item['code'] not in existing
    ]
    if to_create:
        VendorPagePermission.objects.bulk_create(to_create)


def ensure_default_roles(vendor, created_by=None):
    ensure_default_permissions()
    permissions_by_code = {
        permission.code: permission
        for permission in VendorPagePermission.objects.filter(vendor__isnull=True, is_active=True)
    }
    for definition in DEFAULT_ROLE_DEFINITIONS:
        role, created = VendorRole.objects.get_or_create(
            vendor=vendor,
            name=definition['name'],
            defaults={
                'description': definition['description'],
                'is_system': True,
                'created_by': created_by
            }
        )
        if created or VendorRolePermission.objects.filter(role=role).count() == 0:
            to_create = []
            for perm_def in definition['permissions']:
                code = perm_def['code']
                if code in permissions_by_code:
                    actions = perm_def['actions']
                    to_create.append(VendorRolePermission(
                        role=role,
                        permission=permissions_by_code[code],
                        can_view='view' in actions,
                        can_create='create' in actions,
                        can_edit='edit' in actions,
                        can_delete='delete' in actions
                    ))
            if to_create:
                VendorRolePermission.objects.bulk_create(to_create)


def is_vendor_master(user, vendor):
    if not vendor:
        return False
    return vendor.user_id == user.id


def user_has_permission(user, vendor, code, action='view'):
    if user.is_staff or user.is_superuser:
        return True
    if is_vendor_master(user, vendor):
        return True
    employee = VendorEmployee.objects.select_related('role').filter(
        user=user,
        vendor=vendor,
        is_active=True
    ).first()
    if not employee or not employee.role_id:
        return False
    
    return VendorRolePermission.objects.filter(
        role=employee.role,
        permission__code=code,
        permission__is_active=True,
        **{f'can_{action}': True}
    ).exists()


def vendor_permission_required(permission_code, action='view'):
    """
    Decorator for views that checks if the user has a specific vendor permission.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            
            vendor = get_vendor_context(request.user)
            if not vendor:
                messages.error(request, "You don't have vendor access.")
                return redirect('users:user-dashboard')
            
            if not user_has_permission(request.user, vendor, permission_code, action):
                messages.error(request, f"You don't have permission to {action} {permission_code}.")
                # Redirect to dashboard if they don't have permission
                return redirect('business_partners:vendor_dashboard')
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


class VendorPermissionRequiredMixin:
    """
    Mixin for class-based views that checks if the user has a specific vendor permission.
    """
    vendor_permission_code = None
    vendor_permission_action = 'view'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        vendor = get_vendor_context(request.user)
        if not vendor:
            messages.error(request, "You don't have vendor access.")
            return redirect('users:user-dashboard')
        
        if self.vendor_permission_code and not user_has_permission(
            request.user, vendor, self.vendor_permission_code, self.vendor_permission_action
        ):
            messages.error(request, f"You don't have permission to {self.vendor_permission_action} {self.vendor_permission_code}.")
            return redirect('business_partners:vendor_dashboard')
        
        return super().dispatch(request, *args, **kwargs)
