from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import models, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.conf import settings

from core.email_service.orchestrator import send_email
from .forms import EmployeeInviteForm, EmployeeUpdateForm, RoleForm, RolePermissionForm, VendorLocationForm, InvitationAcceptForm, StorageLocationForm
from .models import VendorEmployee, VendorPagePermission, VendorRole, VendorRolePermission, VendorLocation, StorageLocation
from .utils import get_vendor_context
from .permissions import (
    ensure_default_permissions, 
    ensure_default_roles, 
    user_has_permission,
    vendor_permission_required
)


User = get_user_model()


@login_required
@vendor_permission_required('employees', 'view')
def employee_list(request):
    vendor = get_vendor_context(request.user)
    ensure_default_roles(vendor, request.user)
    
    employees = VendorEmployee.objects.filter(vendor=vendor).select_related('user', 'role').prefetch_related('locations')
    
    # Filtering
    location_id = request.GET.get('location')
    if location_id:
        employees = employees.filter(locations__id=location_id)
        
    locations = VendorLocation.objects.filter(vendor=vendor, is_active=True)
    
    return render(request, 'vendor_employees/employee_list.html', {
        'vendor': vendor,
        'employees': employees,
        'locations': locations,
        'selected_location': int(location_id) if location_id and location_id.isdigit() else None,
        'active_tab': 'employees'
    })


@login_required
@vendor_permission_required('employees', 'create')
def employee_invite(request):
    vendor = get_vendor_context(request.user)
    ensure_default_roles(vendor, request.user)
    if request.method == 'POST':
        form = EmployeeInviteForm(vendor, request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].lower()
            first_name = form.cleaned_data.get('first_name') or ''
            last_name = form.cleaned_data.get('last_name') or ''
            role = form.cleaned_data['role']
            locations = form.cleaned_data.get('locations')
            user = User.objects.filter(email__iexact=email).first()
            if user:
                other_employee = VendorEmployee.objects.filter(user=user).exclude(vendor=vendor).first()
                if other_employee:
                    messages.error(request, 'User already belongs to another vendor.')
                    return redirect('vendor_employees:employee_invite')
                employee, created = VendorEmployee.objects.get_or_create(
                    user=user,
                    vendor=vendor,
                    defaults={
                        'role': role,
                        'invited_by': request.user,
                        'is_active': True
                    }
                )
                if not created:
                    employee.role = role
                    employee.is_active = True
                    employee.save(update_fields=['role', 'is_active', 'updated_at'])
                
                # Set locations
                employee.locations.set(locations)
            else:
                user = User.objects.create(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=True
                )
                user.set_unusable_password()
                user.save(update_fields=['password'])
                employee = VendorEmployee.objects.create(
                    user=user,
                    vendor=vendor,
                    role=role,
                    invited_by=request.user,
                    is_active=True
                )
                employee.locations.set(locations)

            # Send invitation email
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            invitation_url = request.build_absolute_uri(
                f'/business-partners/vendor/employees/accept-invitation/{uid}/{token}/'
            )
            
            location_names = ", ".join([loc.name for loc in locations]) if locations else "No Location"

            send_email(
                email_type='employee_invitation',
                to_email=email,
                subject=f'Invitation to join {vendor.name} on CarSyncro',
                template_name='vendor_employee_invitation',
                context={
                    'first_name': first_name,
                    'vendor_name': vendor.name,
                    'role_name': role.name,
                    'location_name': location_names,
                    'invitation_url': invitation_url,
                },
                priority='high'
            )

            messages.success(request, f'Invitation sent to {email}.')
            return redirect('vendor_employees:employee_list')
    else:
        form = EmployeeInviteForm(vendor)
    return render(request, 'vendor_employees/employee_invite.html', {
        'form': form,
        'vendor': vendor,
        'active_tab': 'employees'
    })


@login_required
@vendor_permission_required('employees', 'edit')
def employee_update(request, employee_id):
    vendor = get_vendor_context(request.user)
    employee = get_object_or_404(VendorEmployee, id=employee_id, vendor=vendor)
    if request.method == 'POST':
        form = EmployeeUpdateForm(vendor, request.POST)
        if form.is_valid():
            employee.role = form.cleaned_data['role']
            employee.is_active = form.cleaned_data.get('is_active', False)
            employee.save(update_fields=['role', 'is_active', 'updated_at'])
            
            # Update locations
            employee.locations.set(form.cleaned_data.get('locations'))
            
            messages.success(request, 'Employee updated successfully.')
            return redirect('vendor_employees:employee_list')
    else:
        form = EmployeeUpdateForm(vendor, initial={
            'role': employee.role,
            'locations': employee.locations.all(),
            'is_active': employee.is_active
        })
    return render(request, 'vendor_employees/employee_update.html', {
        'form': form,
        'employee': employee,
        'vendor': vendor,
        'active_tab': 'employees'
    })


@login_required
@vendor_permission_required('employees', 'delete')
def employee_deactivate(request, employee_id):
    vendor = get_vendor_context(request.user)
    employee = get_object_or_404(VendorEmployee, id=employee_id, vendor=vendor)
    if request.method == 'POST':
        employee.is_active = False
        employee.save(update_fields=['is_active', 'updated_at'])
        messages.success(request, 'Employee deactivated.')
        return redirect('vendor_employees:employee_list')
    return redirect('vendor_employees:employee_list')


@login_required
@vendor_permission_required('roles', 'view')
def role_list(request):
    vendor = get_vendor_context(request.user)
    ensure_default_roles(vendor, request.user)
    roles = VendorRole.objects.filter(vendor=vendor).prefetch_related('permissions')
    return render(request, 'vendor_employees/role_list.html', {
        'vendor': vendor,
        'roles': roles,
        'active_tab': 'roles'
    })


def accept_invitation(request, uidb64, token):
    try:
        from django.utils.http import urlsafe_base64_decode
        from django.utils.encoding import force_str
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        employee = VendorEmployee.objects.filter(user=user, is_active=True).first()
        if not employee:
            messages.error(request, 'Invitation is invalid or has expired.')
            return redirect('business_partners:vendor_login')

        if request.method == 'POST':
            form = InvitationAcceptForm(request.POST)
            if form.is_valid():
                user.first_name = form.cleaned_data['first_name']
                user.last_name = form.cleaned_data['last_name']
                user.set_password(form.cleaned_data['password'])
                
                # Mark as verified since they've accepted the invitation via email
                user.is_verified = True
                user.email_verification_token = None
                user.email_verification_sent_at = None
                
                user.save()
                
                # Mark invitation as accepted
                from django.utils import timezone
                employee.invitation_accepted_at = timezone.now()
                employee.save()
                from django.contrib.auth import login
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                
                messages.success(request, 'Account set up successfully! Welcome to the team.')
                return redirect('business_partners:vendor_dashboard')
        else:
            form = InvitationAcceptForm(initial={    
                'first_name': user.first_name,    
                'last_name': user.last_name,    
            })
        
        return render(request, 'vendor_employees/accept_invitation.html', {
            'form': form,
            'vendor_name': employee.vendor.name,
            'user_email': user.email
        })
    else:
        messages.error(request, 'Invitation link is invalid or has expired.')
        return redirect('business_partners:vendor_login')


@login_required
@vendor_permission_required('roles', 'create')
def role_create(request):
    vendor = get_vendor_context(request.user)
    ensure_default_roles(vendor, request.user)
    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            role = form.save(commit=False)
            role.vendor = vendor
            role.created_by = request.user
            role.save()
            messages.success(request, 'Role created successfully.')
            return redirect('vendor_employees:role_list')
    else:
        form = RoleForm()
    return render(request, 'vendor_employees/role_form.html', {
        'form': form,
        'vendor': vendor,
        'is_edit': False,
        'active_tab': 'roles'
    })


@login_required
@vendor_permission_required('roles', 'edit')
def role_edit(request, role_id):
    vendor = get_vendor_context(request.user)
    role = get_object_or_404(VendorRole, id=role_id, vendor=vendor)
    if request.method == 'POST':
        form = RoleForm(request.POST, instance=role)
        if form.is_valid():
            form.save()
            messages.success(request, 'Role updated successfully.')
            return redirect('vendor_employees:role_list')
    else:
        form = RoleForm(instance=role)
    return render(request, 'vendor_employees/role_form.html', {
        'form': form,
        'role': role,
        'vendor': vendor,
        'is_edit': True,
        'active_tab': 'roles'
    })


@login_required
@vendor_permission_required('roles', 'edit')
def role_permissions(request, role_id):
    vendor = get_vendor_context(request.user)
    role = get_object_or_404(VendorRole, id=role_id, vendor=vendor)
    ensure_default_permissions()
    
    if request.method == 'POST':
        # Get all permissions to process
        all_page_permissions = VendorPagePermission.objects.filter(
            is_active=True
        ).filter(models.Q(vendor__isnull=True) | models.Q(vendor=vendor))
        
        with transaction.atomic():
            # Clear existing permissions (simpler to rebuild than update)
            VendorRolePermission.objects.filter(role=role).delete()
            
            to_create = []
            for perm in all_page_permissions:
                can_view = request.POST.get(f'perm_{perm.id}_view') == 'on'
                can_create = request.POST.get(f'perm_{perm.id}_create') == 'on'
                can_edit = request.POST.get(f'perm_{perm.id}_edit') == 'on'
                can_delete = request.POST.get(f'perm_{perm.id}_delete') == 'on'
                
                if can_view or can_create or can_edit or can_delete:
                    to_create.append(VendorRolePermission(
                        role=role,
                        permission=perm,
                        can_view=can_view,
                        can_create=can_create,
                        can_edit=can_edit,
                        can_delete=can_delete
                    ))
            
            if to_create:
                VendorRolePermission.objects.bulk_create(to_create)
                
            messages.success(request, 'Permissions updated successfully.')
            return redirect('vendor_employees:role_list')
    
    # Prepare data for UI
    all_permissions = VendorPagePermission.objects.filter(
        is_active=True
    ).filter(models.Q(vendor__isnull=True) | models.Q(vendor=vendor))
    
    grouped_permissions = {}
    for perm in all_permissions:
        cat = perm.category or 'General'
        if cat not in grouped_permissions:
            grouped_permissions[cat] = []
        grouped_permissions[cat].append(perm)
    
    # Get existing role permissions
    role_permissions_data = {}
    for rp in VendorRolePermission.objects.filter(role=role):
        # Use string keys for template compatibility
        role_permissions_data[str(rp.permission_id)] = {
            'view': rp.can_view,
            'create': rp.can_create,
            'edit': rp.can_edit,
            'delete': rp.can_delete
        }
    
    # Sort categories
    sorted_categories = sorted(grouped_permissions.keys())
    
    return render(request, 'vendor_employees/role_permissions.html', {
        'role': role,
        'vendor': vendor,
        'grouped_permissions': grouped_permissions,
        'sorted_categories': sorted_categories,
        'role_permissions_data': role_permissions_data,
        'active_tab': 'roles'
    })


@login_required
@vendor_permission_required('locations', 'view')
def location_list(request):
    vendor = get_vendor_context(request.user)
    
    locations = VendorLocation.objects.filter(vendor=vendor).order_by('-is_active', 'name')
    
    return render(request, 'vendor_employees/location_list.html', {
        'locations': locations,
        'vendor': vendor,
        'active_tab': 'locations'
    })


@login_required
@vendor_permission_required('locations', 'create')
def location_create(request):
    vendor = get_vendor_context(request.user)
    
    if request.method == 'POST':
        form = VendorLocationForm(request.POST)
        if form.is_valid():
            location = form.save(commit=False)
            location.vendor = vendor
            location.save()
            messages.success(request, f'Location "{location.name}" created. You can now add storage locations.')
            return redirect('vendor_employees:location_edit', location_id=location.id)
    else:
        form = VendorLocationForm()
    
    return render(request, 'vendor_employees/location_form.html', {
        'form': form,
        'vendor': vendor,
        'title': 'Add Location',
        'active_tab': 'locations'
    })


@login_required
@vendor_permission_required('locations', 'edit')
def location_edit(request, location_id):
    vendor = get_vendor_context(request.user)
    
    location = get_object_or_404(VendorLocation, id=location_id, vendor=vendor)
    
    if request.method == 'POST':
        # Check if we are adding a storage location
        if 'add_storage' in request.POST:
            storage_form = StorageLocationForm(request.POST)
            if storage_form.is_valid():
                storage = storage_form.save(commit=False)
                storage.plant = location
                storage.save()
                messages.success(request, f'Storage Location "{storage.name}" added successfully.')
                return redirect('vendor_employees:location_edit', location_id=location.id)
            else:
                form = VendorLocationForm(instance=location)
                messages.error(request, 'Error adding storage location. Please check the form.')
        # Or updating the location itself
        else:
            form = VendorLocationForm(request.POST, instance=location)
            if form.is_valid():
                form.save()
                messages.success(request, f'Location "{location.name}" updated successfully.')
                return redirect('vendor_employees:location_list')
            storage_form = StorageLocationForm(initial={'is_active': True})
    else:
        form = VendorLocationForm(instance=location)
        storage_form = StorageLocationForm(initial={'is_active': True})
    
    storage_locations = location.storage_locations.all()
    
    return render(request, 'vendor_employees/location_form.html', {
        'form': form,
        'storage_form': storage_form,
        'storage_locations': storage_locations,
        'vendor': vendor,
        'title': f'Edit Location: {location.name}',
        'active_tab': 'locations',
        'is_edit': True
    })


@login_required
@vendor_permission_required('locations', 'edit')
def location_toggle_status(request, location_id):
    vendor = get_vendor_context(request.user)
    
    location = get_object_or_404(VendorLocation, id=location_id, vendor=vendor)
    
    location.is_active = not location.is_active
    location.save()
    
    status = "activated" if location.is_active else "deactivated"
    messages.success(request, f'Location "{location.name}" has been {status}.')
    return redirect('vendor_employees:location_list')

