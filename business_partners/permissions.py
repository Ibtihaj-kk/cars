"""
Permission classes for business partners and vendor access control.
"""
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from rest_framework import permissions
from django.db.models import Q
from .models import BusinessPartner, VendorProfile
from .utils import get_business_partner_for_user
from vendor_employees.utils import get_vendor_context

User = get_user_model()


class VendorRequiredMixin(UserPassesTestMixin):
    """
    Mixin to ensure only approved vendors can access the view.
    """
    
    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        
        # Admin/staff always have access
        if user.is_staff or user.is_superuser:
            return True
        
        # Check if user has vendor access
        return self.has_vendor_access(user)
    
    def has_vendor_access(self, user):
        """Check if user has vendor access (as master or employee)."""
        return get_vendor_context(user) is not None
    
    def handle_no_permission(self):
        messages.error(self.request, "You don't have vendor access. Please apply for vendor status first.")
        return redirect('vendor_registration_step1')


class VendorPartOwnerMixin(VendorRequiredMixin):
    """
    Mixin to ensure vendor can only access their own parts.
    Includes location-based check for vendor employees.
    """
    
    def get_object(self, queryset=None):
        """Override to ensure vendor can only access their own parts."""
        obj = super().get_object(queryset)
        
        # Admin/staff can access all parts
        if self.request.user.is_staff or self.request.user.is_superuser:
            return obj
        
        # Check if vendor owns this part
        if hasattr(obj, 'vendor'):
            business_partner = get_vendor_context(self.request.user)
            if not business_partner:
                raise PermissionDenied("Vendor access required.")
            if obj.vendor != business_partner:
                raise PermissionDenied("You can only access your own parts.")
            
            # Location-based check for vendor employees
            vendor_employee = getattr(self.request.user, 'vendor_employee', None)
            if vendor_employee and vendor_employee.is_active:
                employee_locations = vendor_employee.locations.filter(is_active=True).values_list('name', flat=True)
                if employee_locations:
                    if not (obj.plant in employee_locations or 
                            obj.storage_location in employee_locations or 
                            obj.warehouse_number in employee_locations):
                        raise PermissionDenied("You don't have permission to access this part's location.")
                else:
                    raise PermissionDenied("You don't have access to any locations.")
        
        return obj


def vendor_required(view_func):
    """
    Decorator for function-based views requiring vendor access.
    """
    def check_vendor_permissions(user):
        if not user.is_authenticated:
            return False
        
        # Admin/staff always have access
        if user.is_staff or user.is_superuser:
            return True
        
        # Check if user has vendor access (as master or employee)
        return get_vendor_context(user) is not None
    
    return user_passes_test(check_vendor_permissions, login_url='business_partners:vendor_login')(view_func)


def vendor_part_owner_required(view_func):
    """
    Decorator for function-based views requiring vendor to own the part.
    This should be used with views that take a part_id parameter.
    Includes location-based check for vendor employees.
    """
    def wrapper(request, part_id, *args, **kwargs):
        from parts.models import Part
        from django.shortcuts import get_object_or_404
        
        # Get the part
        part = get_object_or_404(Part, id=part_id)
        
        # Admin/staff can access all parts
        if request.user.is_staff or request.user.is_superuser:
            return view_func(request, part_id, *args, **kwargs)
        
        # Check if vendor owns this part
        if hasattr(part, 'vendor') and part.vendor:
            business_partner = get_vendor_context(request.user)
            if not business_partner:
                messages.error(request, "Vendor access required.")
                return redirect('vendor_registration_step1')
            
            if part.vendor != business_partner:
                messages.error(request, "You can only access your own parts.")
                return redirect('vendor_parts_list')
            
            # Location-based check for vendor employees
            vendor_employee = getattr(request.user, 'vendor_employee', None)
            if vendor_employee and vendor_employee.is_active:
                employee_locations = vendor_employee.locations.filter(is_active=True).values_list('name', flat=True)
                if employee_locations:
                    if not (part.plant in employee_locations or 
                            part.storage_location in employee_locations or 
                            part.warehouse_number in employee_locations):
                        messages.error(request, "You don't have permission to access this part's location.")
                        return redirect('vendor_inventory_list')
                else:
                    messages.error(request, "You don't have access to any locations.")
                    return redirect('vendor_inventory_list')
        
        return view_func(request, part_id, *args, **kwargs)
    
    return vendor_required(wrapper)


# REST Framework Permissions

class IsVendorOrAdmin(permissions.BasePermission):
    """
    Permission class for DRF views - allows access to vendors and admins.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin/staff always have access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Check if user has vendor access
        business_partner = get_business_partner_for_user(request.user)
        if business_partner:
            return business_partner.roles.filter(role_type='vendor').exists()
        return False


class IsVendorPartOwnerOrAdmin(permissions.BasePermission):
    """
    Permission class for DRF views - allows access only to part owners and admins.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin/staff always have access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Check if user has vendor access
        business_partner = get_business_partner_for_user(request.user)
        if business_partner:
            return business_partner.roles.filter(role_type='vendor').exists()
        return False
    
    def has_object_permission(self, request, view, obj):
        # Admin/staff can access all objects
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Check if vendor owns this part
        if hasattr(obj, 'vendor') and obj.vendor:
            business_partner = get_business_partner_for_user(request.user)
            if business_partner:
                return obj.vendor == business_partner
        return False
        
        return False


class IsVendorProfileOwnerOrAdmin(permissions.BasePermission):
    """
    Permission class for vendor profile access.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin/staff always have access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Check if user has vendor access
        business_partner = get_business_partner_for_user(request.user)
        if business_partner:
            return business_partner.roles.filter(role_type='vendor').exists()
        return False
    
    def has_object_permission(self, request, view, obj):
        # Admin/staff can access all profiles
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Check if user owns this vendor profile
        if hasattr(obj, 'business_partner'):
            business_partner = get_business_partner_for_user(request.user)
            if business_partner:
                return obj.business_partner == business_partner
        return False
        
        return False


class IsVendorManager(permissions.BasePermission):
    """
    Permission class for vendor management operations.
    Allows access to users who can manage vendor applications and vendor profiles.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin/staff always have access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Check if user has vendor management permissions
        # This would typically check for specific permissions in your RBAC system
        # For now, we'll check if user has any business partner with vendor role
        business_partner = get_business_partner_for_user(request.user)
        if business_partner:
            return business_partner.roles.filter(role_type='vendor').exists()
        return False
    
    def has_object_permission(self, request, view, obj):
        # Admin/staff can access all objects
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # For vendor applications and business partners, check ownership
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # For vendor profiles, check if user owns the business partner
        if hasattr(obj, 'business_partner'):
            business_partner = get_business_partner_for_user(request.user)
            if business_partner:
                return obj.business_partner == business_partner
        return False


def get_vendor_profile(user):
    """
    Helper function to get vendor profile for a user.
    Returns None if user doesn't have vendor access.
    Handles both vendor masters and vendor employees.
    """
    if not user or not user.is_authenticated:
        return None
    
    # Try getting vendor context (this handles both master and employee)
    vendor = get_vendor_context(user)
    if vendor:
        try:
            return vendor.vendor_profile
        except (VendorProfile.DoesNotExist, AttributeError):
            return None
            
    return None


def user_has_vendor_access(user):
    """
    Helper function to check if user has vendor access (as master or employee).
    """
    if not user or not user.is_authenticated:
        return False
    
    # Admin/staff always have access
    if user.is_staff or user.is_superuser:
        return True
    
    # Check if user has vendor access (as master or employee)
    return get_vendor_context(user) is not None