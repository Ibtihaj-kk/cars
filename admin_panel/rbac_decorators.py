from functools import wraps
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from core.rbac_manager import rbac_manager
from django.shortcuts import redirect

def vendor_permission_required(permission_codename):
    def decorator(func):
        @wraps(func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not rbac_manager.has_permission(request.user, permission_codename):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': 'Insufficient permissions'}, status=403)
                return redirect('admin_panel:dashboard')
            return func(request, *args, **kwargs)
        return wrapper
    return decorator

def can_manage_vendors():
    return vendor_permission_required('business_partners.can_manage_vendors')

def can_review_vendor_applications():
    return vendor_permission_required('business_partners.can_review_applications')

def can_approve_vendors():
    return vendor_permission_required('business_partners.can_approve_vendors')