"""
RBAC Permission Definitions
Pre-defined permissions for the system
"""
from .rbac_models import Permission


def create_system_permissions():
    """Create system-wide permissions."""
    permissions = [
        # User Management Permissions
        {
            'codename': 'users.view_user',
            'name': 'View Users',
            'description': 'Can view user profiles and information',
            'module': 'users',
            'action': 'view'
        },
        {
            'codename': 'users.create_user',
            'name': 'Create Users',
            'description': 'Can create new user accounts',
            'module': 'users',
            'action': 'create'
        },
        {
            'codename': 'users.update_user',
            'name': 'Update Users',
            'description': 'Can update user information',
            'module': 'users',
            'action': 'update'
        },
        {
            'codename': 'users.delete_user',
            'name': 'Delete Users',
            'description': 'Can delete user accounts',
            'module': 'users',
            'action': 'delete'
        },
        {
            'codename': 'users.manage_user_roles',
            'name': 'Manage User Roles',
            'description': 'Can assign and revoke user roles',
            'module': 'users',
            'action': 'manage'
        },
        {
            'codename': 'users.view_audit_logs',
            'name': 'View Audit Logs',
            'description': 'Can view user audit logs',
            'module': 'users',
            'action': 'audit'
        },
        
        # Business Partner Permissions
        {
            'codename': 'business_partners.view_partner',
            'name': 'View Business Partners',
            'description': 'Can view business partner information',
            'module': 'business_partners',
            'action': 'view'
        },
        {
            'codename': 'business_partners.create_partner',
            'name': 'Create Business Partners',
            'description': 'Can create new business partners',
            'module': 'business_partners',
            'action': 'create'
        },
        {
            'codename': 'business_partners.update_partner',
            'name': 'Update Business Partners',
            'description': 'Can update business partner information',
            'module': 'business_partners',
            'action': 'update'
        },
        {
            'codename': 'business_partners.delete_partner',
            'name': 'Delete Business Partners',
            'description': 'Can delete business partners',
            'module': 'business_partners',
            'action': 'delete'
        },
        {
            'codename': 'business_partners.approve_vendor',
            'name': 'Approve Vendors',
            'description': 'Can approve vendor applications',
            'module': 'business_partners',
            'action': 'approve'
        },
        {
            'codename': 'business_partners.reject_vendor',
            'name': 'Reject Vendors',
            'description': 'Can reject vendor applications',
            'module': 'business_partners',
            'action': 'reject'
        },
        {
            'codename': 'business_partners.view_vendor_applications',
            'name': 'View Vendor Applications',
            'description': 'Can view vendor applications',
            'module': 'business_partners',
            'action': 'view'
        },
        {
            'codename': 'business_partners.manage_vendor_documents',
            'name': 'Manage Vendor Documents',
            'description': 'Can manage vendor documents',
            'module': 'business_partners',
            'action': 'manage'
        },
        
        # Parts Management Permissions
        {
            'codename': 'parts.view_part',
            'name': 'View Parts',
            'description': 'Can view parts information',
            'module': 'parts',
            'action': 'view'
        },
        {
            'codename': 'parts.create_part',
            'name': 'Create Parts',
            'description': 'Can create new parts',
            'module': 'parts',
            'action': 'create'
        },
        {
            'codename': 'parts.update_part',
            'name': 'Update Parts',
            'description': 'Can update parts information',
            'module': 'parts',
            'action': 'update'
        },
        {
            'codename': 'parts.delete_part',
            'name': 'Delete Parts',
            'description': 'Can delete parts',
            'module': 'parts',
            'action': 'delete'
        },
        {
            'codename': 'parts.import_parts',
            'name': 'Import Parts',
            'description': 'Can import parts data',
            'module': 'parts',
            'action': 'import'
        },
        {
            'codename': 'parts.export_parts',
            'name': 'Export Parts',
            'description': 'Can export parts data',
            'module': 'parts',
            'action': 'export'
        },
        {
            'codename': 'parts.manage_categories',
            'name': 'Manage Categories',
            'description': 'Can manage part categories',
            'module': 'parts',
            'action': 'manage'
        },
        {
            'codename': 'parts.manage_brands',
            'name': 'Manage Brands',
            'description': 'Can manage part brands',
            'module': 'parts',
            'action': 'manage'
        },
        
        # Inventory Permissions
        {
            'codename': 'inventory.view_inventory',
            'name': 'View Inventory',
            'description': 'Can view inventory levels',
            'module': 'inventory',
            'action': 'view'
        },
        {
            'codename': 'inventory.update_inventory',
            'name': 'Update Inventory',
            'description': 'Can update inventory levels',
            'module': 'inventory',
            'action': 'update'
        },
        {
            'codename': 'inventory.manage_stock_alerts',
            'name': 'Manage Stock Alerts',
            'description': 'Can manage stock alert settings',
            'module': 'inventory',
            'action': 'manage'
        },
        {
            'codename': 'inventory.view_stock_monitoring',
            'name': 'View Stock Monitoring',
            'description': 'Can view stock monitoring dashboard',
            'module': 'inventory',
            'action': 'view'
        },
        
        # Order Permissions
        {
            'codename': 'orders.view_order',
            'name': 'View Orders',
            'description': 'Can view orders',
            'module': 'orders',
            'action': 'view'
        },
        {
            'codename': 'orders.create_order',
            'name': 'Create Orders',
            'description': 'Can create new orders',
            'module': 'orders',
            'action': 'create'
        },
        {
            'codename': 'orders.update_order',
            'name': 'Update Orders',
            'description': 'Can update order information',
            'module': 'orders',
            'action': 'update'
        },
        {
            'codename': 'orders.approve_order',
            'name': 'Approve Orders',
            'description': 'Can approve orders',
            'module': 'orders',
            'action': 'approve'
        },
        {
            'codename': 'orders.cancel_order',
            'name': 'Cancel Orders',
            'description': 'Can cancel orders',
            'module': 'orders',
            'action': 'reject'
        },
        
        # Analytics Permissions
        {
            'codename': 'analytics.view_dashboard',
            'name': 'View Analytics Dashboard',
            'description': 'Can view analytics dashboard',
            'module': 'analytics',
            'action': 'view'
        },
        {
            'codename': 'analytics.view_sales_reports',
            'name': 'View Sales Reports',
            'description': 'Can view sales reports',
            'module': 'analytics',
            'action': 'view'
        },
        {
            'codename': 'analytics.view_revenue_reports',
            'name': 'View Revenue Reports',
            'description': 'Can view revenue reports',
            'module': 'analytics',
            'action': 'view'
        },
        {
            'codename': 'analytics.export_reports',
            'name': 'Export Reports',
            'description': 'Can export analytics reports',
            'module': 'analytics',
            'action': 'export'
        },
        {
            'codename': 'analytics.configure_reports',
            'name': 'Configure Reports',
            'description': 'Can configure analytics reports',
            'module': 'analytics',
            'action': 'configure'
        },
        
        # Admin Permissions
        {
            'codename': 'admin.view_admin_panel',
            'name': 'View Admin Panel',
            'description': 'Can access admin panel',
            'module': 'admin',
            'action': 'view'
        },
        {
            'codename': 'admin.manage_settings',
            'name': 'Manage Settings',
            'description': 'Can manage system settings',
            'module': 'admin',
            'action': 'configure'
        },
        {
            'codename': 'admin.view_system_logs',
            'name': 'View System Logs',
            'description': 'Can view system logs',
            'module': 'admin',
            'action': 'view'
        },
        {
            'codename': 'admin.manage_users',
            'name': 'Manage Users',
            'description': 'Can manage system users',
            'module': 'admin',
            'action': 'manage'
        },
        {
            'codename': 'admin.manage_roles',
            'name': 'Manage Roles',
            'description': 'Can manage user roles and permissions',
            'module': 'admin',
            'action': 'manage'
        },
        
        # System Permissions
        {
            'codename': 'system.api_access',
            'name': 'API Access',
            'description': 'Can access system APIs',
            'module': 'system',
            'action': 'view'
        },
        {
            'codename': 'system.perform_maintenance',
            'name': 'Perform Maintenance',
            'description': 'Can perform system maintenance',
            'module': 'system',
            'action': 'configure'
        },
        {
            'codename': 'system.view_monitoring',
            'name': 'View System Monitoring',
            'description': 'Can view system monitoring',
            'module': 'system',
            'action': 'view'
        },
    ]
    
    created_permissions = []
    for perm_data in permissions:
        perm, created = Permission.objects.get_or_create(
            codename=perm_data['codename'],
            defaults=perm_data
        )
        if created:
            created_permissions.append(perm)
        else:
            # Update existing permission
            for key, value in perm_data.items():
                if key != 'codename':
                    setattr(perm, key, value)
            perm.save()
    
    return created_permissions


def create_system_roles():
    """Create pre-defined system roles."""
    roles = [
        {
            'name': 'System Administrator',
            'role_type': 'admin',
            'description': 'Full system access with all permissions',
            'is_system': True,
        },
        {
            'name': 'Staff Member',
            'role_type': 'staff',
            'description': 'General staff with limited admin access',
            'is_system': True,
        },
        {
            'name': 'Vendor Administrator',
            'role_type': 'vendor_admin',
            'description': 'Vendor with full administrative privileges',
            'is_system': True,
        },
        {
            'name': 'Vendor Manager',
            'role_type': 'vendor_manager',
            'description': 'Vendor with management capabilities',
            'is_system': True,
        },
        {
            'name': 'Vendor User',
            'role_type': 'vendor_user',
            'description': 'Regular vendor user with basic access',
            'is_system': True,
        },
        {
            'name': 'Customer',
            'role_type': 'customer',
            'description': 'Customer with limited access',
            'is_system': True,
        },
        {
            'name': 'Analyst',
            'role_type': 'analyst',
            'description': 'User with analytics and reporting access',
            'is_system': True,
        },
        {
            'name': 'Auditor',
            'role_type': 'auditor',
            'description': 'User with audit log access',
            'is_system': True,
        },
    ]
    
    created_roles = []
    for role_data in roles:
        role, created = Role.objects.get_or_create(
            name=role_data['name'],
            defaults=role_data
        )
        if created:
            created_roles.append(role)
    
    return created_roles


def assign_role_permissions():
    """Assign permissions to system roles."""
    from .rbac_models import Role
    
    # System Administrator - All permissions
    admin_role = Role.objects.get(name='System Administrator')
    all_permissions = Permission.objects.all()
    admin_role.permissions.set(all_permissions)
    
    # Staff Member - Limited admin permissions
    staff_role = Role.objects.get(name='Staff Member')
    staff_permissions = Permission.objects.filter(
        module__in=['users', 'business_partners', 'parts', 'inventory', 'orders', 'analytics'],
        action__in=['view', 'update']
    )
    staff_role.permissions.set(staff_permissions)
    
    # Vendor Administrator - Vendor-specific permissions
    vendor_admin_role = Role.objects.get(name='Vendor Administrator')
    vendor_admin_permissions = Permission.objects.filter(
        module__in=['business_partners', 'parts', 'inventory', 'orders', 'analytics'],
        action__in=['view', 'create', 'update', 'manage']
    )
    vendor_admin_role.permissions.set(vendor_admin_permissions)
    
    # Vendor Manager - Limited vendor permissions
    vendor_manager_role = Role.objects.get(name='Vendor Manager')
    vendor_manager_permissions = Permission.objects.filter(
        module__in=['business_partners', 'parts', 'inventory', 'orders'],
        action__in=['view', 'create', 'update']
    )
    vendor_manager_role.permissions.set(vendor_manager_permissions)
    
    # Vendor User - Basic vendor permissions
    vendor_user_role = Role.objects.get(name='Vendor User')
    vendor_user_permissions = Permission.objects.filter(
        module__in=['parts', 'inventory'],
        action__in=['view', 'update']
    )
    vendor_user_role.permissions.set(vendor_user_permissions)
    
    # Customer - Limited viewing permissions
    customer_role = Role.objects.get(name='Customer')
    customer_permissions = Permission.objects.filter(
        module__in=['parts'],
        action='view'
    )
    customer_role.permissions.set(customer_permissions)
    
    # Analyst - Analytics permissions
    analyst_role = Role.objects.get(name='Analyst')
    analyst_permissions = Permission.objects.filter(
        module__in=['analytics', 'business_partners', 'parts', 'orders'],
        action__in=['view', 'export']
    )
    analyst_role.permissions.set(analyst_permissions)
    
    # Auditor - Audit permissions
    auditor_role = Role.objects.get(name='Auditor')
    auditor_permissions = Permission.objects.filter(
        module__in=['users', 'system'],
        action__in=['view', 'audit']
    )
    auditor_role.permissions.set(auditor_permissions)


def initialize_rbac_system():
    """Initialize the complete RBAC system."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Create permissions
    created_permissions = create_system_permissions()
    print(f"Created {len(created_permissions)} system permissions")
    
    # Create roles
    created_roles = create_system_roles()
    print(f"Created {len(created_roles)} system roles")
    
    # Assign permissions to roles
    assign_role_permissions()
    print("Assigned permissions to system roles")
    
    return {
        'permissions_created': len(created_permissions),
        'roles_created': len(created_roles),
        'total_permissions': Permission.objects.count(),
        'total_roles': Role.objects.count()
    }