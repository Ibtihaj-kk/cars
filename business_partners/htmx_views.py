"""
HTMX Views for Business Partners/Vendors Module
Server-side rendered views for vendor management and inventory
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, HttpResponseForbidden
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import timedelta

from .models import VendorProfile, VendorApplication, BusinessPartner, BusinessPartnerRole, ContactInfo
from .document_models import VendorDocument, DocumentCategory
from parts.models import Part, Order, OrderItem
from vehicles.models import VehicleMake, VehicleModel
from vendor_employees.models import VendorLocation, StorageLocation


# =====================
# VENDOR DASHBOARD
# =====================

from .utils import get_vendor_profile
from vendor_employees.utils import get_vendor_context
from parts.models import Part, Order, OrderItem

@login_required
@require_http_methods(["GET"])
def vendor_dashboard_htmx(request):
    """
    HTMX endpoint for vendor dashboard
    Returns dashboard stats HTML fragment
    """
    business_partner = get_vendor_context(request.user)
    if not business_partner:
        return HttpResponseForbidden("Vendor access not found.")

    vendor_profile = getattr(business_partner, 'vendor_profile', None)

    # Base queryset for parts
    parts_queryset = Part.objects.filter(vendor=business_partner)
    
    # Location-based filtering for vendor employees
    vendor_employee = getattr(request.user, 'vendor_employee', None)
    if vendor_employee and vendor_employee.is_active:
        employee_locations = vendor_employee.locations.filter(is_active=True).values_list('name', flat=True)
        if employee_locations:
            parts_queryset = parts_queryset.filter(
                Q(plant__in=employee_locations) | 
                Q(storage_location__in=employee_locations) | 
                Q(warehouse_number__in=employee_locations)
            )
        else:
            parts_queryset = parts_queryset.none()

    # Get statistics
    total_parts = parts_queryset.count()
    active_parts = parts_queryset.filter(is_active=True).count()
    low_stock = parts_queryset.filter(
        quantity__lte=5,
        quantity__gt=0
    ).count()
    out_of_stock = parts_queryset.filter(
        quantity=0
    ).count()

    # Recent orders (last 30 days)
    last_30_days = timezone.now() - timedelta(days=30)
    
    # Get all orders that contain items from this vendor's parts (filtered by location if needed)
    recent_orders = Order.objects.filter(
        items__part__in=parts_queryset,
        created_at__gte=last_30_days
    ).distinct()

    monthly_revenue = sum(order.total_price for order in recent_orders)
    monthly_orders = recent_orders.count()

    # Recent order items
    recent_items = OrderItem.objects.filter(
        part__in=parts_queryset
    ).select_related('order', 'part').order_by('-created_at')[:10]

    # Verification status
    verification_deadline = vendor_profile.get_verification_deadline() if vendor_profile else None
    remaining_time = vendor_profile.get_remaining_verification_time() if vendor_profile else None
    is_verification_expired = vendor_profile.is_verification_expired if vendor_profile else False
    is_email_verified = request.user.is_verified or not request.user.requires_email_verification

    context = {
        'vendor': business_partner,
        'vendor_profile': vendor_profile,
        'is_approved': vendor_profile.is_approved if vendor_profile else False,
        'verification_deadline': verification_deadline,
        'remaining_time': remaining_time,
        'is_verification_expired': is_verification_expired,
        'is_email_verified': is_email_verified,
        'total_parts': total_parts,
        'active_parts': active_parts,
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'monthly_revenue': monthly_revenue,
        'monthly_orders': monthly_orders,
        'recent_items': recent_items,
    }

    return render(request, 'business_partners/htmx/dashboard.html', context)


# =====================
# VENDOR INVENTORY
# =====================

@login_required
@require_http_methods(["GET"])
def vendor_inventory_htmx(request):
    """
    HTMX endpoint for vendor inventory list
    Returns inventory HTML fragment
    """
    business_partner = get_vendor_context(request.user)
    if not business_partner:
        return HttpResponseForbidden("Vendor access not found.")

    # Filter parameters
    status_filter = request.GET.get('status', 'all')
    search = request.GET.get('search', '')

    # Base queryset
    parts = Part.objects.filter(
        vendor=business_partner
    ).select_related('make', 'model', 'category')

    # Location-based filtering for vendor employees
    vendor_employee = getattr(request.user, 'vendor_employee', None)
    if vendor_employee and vendor_employee.is_active:
        employee_locations = vendor_employee.locations.filter(is_active=True).values_list('name', flat=True)
        if employee_locations:
            parts = parts.filter(
                Q(plant__in=employee_locations) | 
                Q(storage_location__in=employee_locations) | 
                Q(warehouse_number__in=employee_locations)
            )
        else:
            parts = parts.none()

    # Apply filters
    if status_filter == 'active':
        parts = parts.filter(is_active=True)
    elif status_filter == 'inactive':
        parts = parts.filter(is_active=False)
    elif status_filter == 'low_stock':
        parts = parts.filter(quantity__lte=5, quantity__gt=0)
    elif status_filter == 'out_of_stock':
        parts = parts.filter(quantity=0)

    if search:
        parts = parts.filter(
            Q(name__icontains=search) |
            Q(parts_number__icontains=search)
        )

    parts = parts.order_by('-created_at')

    context = {
        'parts': parts,
        'status_filter': status_filter,
    }

    return render(request, 'business_partners/htmx/inventory_list.html', context)


@login_required
@require_http_methods(["GET"])
def vendor_part_form_htmx(request, part_id=None):
    """
    HTMX endpoint for part add/edit form
    Returns form HTML fragment
    """
    part = None
    if part_id:
        part = get_object_or_404(Part, id=part_id, dealer=request.user)
        
        # Location-based access control for vendor employees
        vendor_employee = getattr(request.user, 'vendor_employee', None)
        if vendor_employee and vendor_employee.is_active:
            employee_locations = vendor_employee.locations.filter(is_active=True).values_list('name', flat=True)
            if employee_locations:
                if not (part.plant in employee_locations or 
                        part.storage_location in employee_locations or 
                        part.warehouse_number in employee_locations):
                    return HttpResponseForbidden("You don't have permission to access this part's location.")
            else:
                return HttpResponseForbidden("You don't have access to any locations.")

    makes = VehicleMake.objects.all().order_by('name')
    models = VehicleModel.objects.all().order_by('name') if part else []

    context = {
        'part': part,
        'makes': makes,
        'models': models,
    }

    return render(request, 'business_partners/htmx/part_form.html', context)


@login_required
@require_http_methods(["POST"])
def vendor_save_part_htmx(request, part_id=None):
    """
    HTMX endpoint to save part (add/edit)
    Returns success message or form with errors
    """
    part = None
    if part_id:
        part = get_object_or_404(Part, id=part_id, dealer=request.user)

        # Location-based access control for vendor employees
        vendor_employee = getattr(request.user, 'vendor_employee', None)
        if vendor_employee and vendor_employee.is_active:
            employee_locations = vendor_employee.locations.filter(is_active=True).values_list('name', flat=True)
            if employee_locations:
                if not (part.plant in employee_locations or 
                        part.storage_location in employee_locations or 
                        part.warehouse_number in employee_locations):
                    return HttpResponseForbidden("You don't have permission to modify this part's location.")
            else:
                return HttpResponseForbidden("You don't have access to any locations.")

    # Get form data
    name = request.POST.get('name')
    parts_number = request.POST.get('parts_number')
    description = request.POST.get('description')
    price = request.POST.get('price')
    quantity = request.POST.get('quantity')
    make_id = request.POST.get('make')
    model_id = request.POST.get('model')
    category_id = request.POST.get('category')

    # Validation (basic)
    if not all([name, parts_number, price, quantity]):
        context = {
            'error': 'All required fields must be filled',
            'part': part,
        }
        return render(request, 'business_partners/htmx/part_form.html', context)

    # Create or update part
    if part:
        part.name = name
        part.parts_number = parts_number
        part.description = description
        part.price = price
        part.quantity = quantity
        part.make_id = make_id if make_id else None
        part.model_id = model_id if model_id else None
        part.category_id = category_id if category_id else None
        part.save()
        message = 'Part updated successfully'
    else:
        part = Part.objects.create(
            dealer=request.user,
            name=name,
            parts_number=parts_number,
            description=description,
            price=price,
            quantity=quantity,
            make_id=make_id if make_id else None,
            model_id=model_id if model_id else None,
            category_id=category_id if category_id else None,
        )
        message = 'Part added successfully'

    context = {
        'message': message,
        'part': part,
    }

    return render(request, 'business_partners/htmx/part_success.html', context)


@login_required
@require_http_methods(["POST"])
def vendor_toggle_part_status_htmx(request, part_id):
    """
    HTMX endpoint to toggle part active status
    Returns updated part row HTML fragment
    """
    part = get_object_or_404(Part, id=part_id, dealer=request.user)

    # Location-based access control for vendor employees
    vendor_employee = getattr(request.user, 'vendor_employee', None)
    if vendor_employee and vendor_employee.is_active:
        employee_locations = vendor_employee.locations.filter(is_active=True).values_list('name', flat=True)
        if employee_locations:
            if not (part.plant in employee_locations or 
                    part.storage_location in employee_locations or 
                    part.warehouse_number in employee_locations):
                return HttpResponseForbidden("You don't have permission to modify this part's location.")
        else:
            return HttpResponseForbidden("You don't have access to any locations.")

    part.is_active = not part.is_active
    part.save()

    context = {
        'part': part,
    }

    return render(request, 'business_partners/htmx/inventory_row.html', context)


@login_required
@require_http_methods(["GET"])
def get_storage_locations(request):
    """
    AJAX endpoint to fetch storage locations for a given plant
    """
    plant_id = request.GET.get('plant_id')
    if not plant_id:
        return HttpResponse('<option value="">Select Storage Location</option>')
    
    storage_locations = StorageLocation.objects.filter(plant_id=plant_id, is_active=True).order_by('name')
    
    options = ['<option value="">Select Storage Location</option>']
    for loc in storage_locations:
        options.append(f'<option value="{loc.id}">{loc.name}</option>')
    
    return HttpResponse(''.join(options))


@login_required
@require_http_methods(["GET"])
def get_warehouses(request):
    """
    AJAX endpoint to fetch warehouses for a given plant
    """
    plant_id = request.GET.get('plant_id')
    if not plant_id:
        return HttpResponse('<option value="">Select Warehouse Number</option>')

    warehouses = StorageLocation.objects.filter(plant_id=plant_id, is_active=True).order_by('name')

    options = ['<option value="">Select Warehouse Number</option>']
    for wh in warehouses:
        options.append(f'<option value="{wh.id}">{wh.name}</option>')

    return HttpResponse(''.join(options))


@login_required
@require_http_methods(["DELETE"])
def vendor_delete_part_htmx(request, part_id):
    """
    HTMX endpoint to delete part
    Returns empty response
    """
    part = get_object_or_404(Part, id=part_id, dealer=request.user)
    part.delete()

    return HttpResponse('')


@login_required
@require_http_methods(["POST"])
def vendor_update_stock_htmx(request, part_id):
    """
    HTMX endpoint to update part stock quantity
    Returns updated stock display HTML fragment
    """
    part = get_object_or_404(Part, id=part_id, dealer=request.user)

    new_quantity = int(request.POST.get('quantity', 0))
    part.quantity = new_quantity
    part.save()

    context = {
        'part': part,
    }

    return render(request, 'business_partners/htmx/stock_display.html', context)


# =====================
# VENDOR ORDERS
# =====================

@login_required
@require_http_methods(["GET"])
def vendor_orders_htmx(request):
    """
    HTMX endpoint for vendor orders list
    Returns orders HTML fragment
    """
    status_filter = request.GET.get('status', 'all')

    # Get orders containing vendor's parts
    orders = Order.objects.filter(
        items__part__dealer=request.user
    ).distinct().select_related('user').prefetch_related('items__part')

    # Apply status filter
    if status_filter != 'all':
        orders = orders.filter(status=status_filter)

    orders = orders.order_by('-created_at')

    context = {
        'orders': orders,
        'status_filter': status_filter,
    }

    return render(request, 'business_partners/htmx/orders_list.html', context)


@login_required
@require_http_methods(["GET"])
def vendor_order_detail_htmx(request, order_id):
    """
    HTMX endpoint for vendor order detail
    Returns order detail HTML fragment (only items from this vendor)
    """
    order = get_object_or_404(Order, id=order_id)

    # Get only this vendor's items from the order
    order_items = OrderItem.objects.filter(
        order=order,
        part__dealer=request.user
    ).select_related('part')

    if not order_items.exists():
        return HttpResponse('No items from your inventory in this order')

    context = {
        'order': order,
        'order_items': order_items,
    }

    return render(request, 'business_partners/htmx/order_detail.html', context)


@login_required
@require_http_methods(["POST"])
def vendor_update_order_status_htmx(request, order_id):
    """
    HTMX endpoint to update order status
    Returns updated order row HTML fragment
    """
    order = get_object_or_404(Order, id=order_id)

    # Verify vendor has items in this order
    has_items = OrderItem.objects.filter(
        order=order,
        part__dealer=request.user
    ).exists()

    if not has_items:
        return HttpResponse('Unauthorized', status=403)

    new_status = request.POST.get('status')
    if new_status in dict(Order.STATUS_CHOICES):
        order.status = new_status
        order.save()

    context = {
        'order': order,
    }

    return render(request, 'business_partners/htmx/order_row.html', context)


# =====================
# VENDOR ANALYTICS
# =====================

@login_required
@require_http_methods(["GET"])
def vendor_analytics_htmx(request):
    """
    HTMX endpoint for vendor analytics
    Returns analytics HTML fragment
    """
    period = int(request.GET.get('period', 30))  # days
    start_date = timezone.now() - timedelta(days=period)

    # Orders in period
    orders = Order.objects.filter(
        items__part__dealer=request.user,
        created_at__gte=start_date
    ).distinct()

    total_revenue = sum(order.total_amount for order in orders)
    total_orders = orders.count()
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

    # Top selling parts
    top_parts = Part.objects.filter(
        dealer=request.user,
        orderitem__order__created_at__gte=start_date
    ).annotate(
        total_sold=Sum('orderitem__quantity')
    ).order_by('-total_sold')[:10]

    # Inventory value
    total_inventory_value = Part.objects.filter(
        dealer=request.user,
        is_active=True
    ).aggregate(
        total=Sum('price')
    )['total'] or 0

    context = {
        'period': period,
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'avg_order_value': avg_order_value,
        'top_parts': top_parts,
        'total_inventory_value': total_inventory_value,
    }

    return render(request, 'business_partners/htmx/analytics.html', context)


# =====================
# VENDOR REGISTRATION
# =====================

@require_http_methods(["GET"])
def vendor_registration_form_htmx(request):
    """
    HTMX endpoint for vendor registration form
    Returns registration form HTML fragment
    """
    return render(request, 'business_partners/htmx/registration_form.html')


@require_http_methods(["POST"])
def vendor_registration_validate_htmx(request):
    """
    HTMX endpoint for real-time vendor registration validation
    Validates individual form fields and returns validation feedback
    """
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError
    import re
    
    field_name = None
    field_value = None
    errors = {}
    
    # Determine which field is being validated
    if 'business_email' in request.POST:
        field_name = 'business_email'
        field_value = request.POST.get('business_email', '').strip()
        
        if not field_value:
            errors['business_email'] = 'Business email is required'
        else:
            # More permissive email validation
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, field_value):
                errors['business_email'] = 'Please enter a valid email address (e.g., user@domain.com)'
            
            # Check if email already exists
            from django.contrib.auth import get_user_model
            User = get_user_model()
            if User.objects.filter(email=field_value).exists():
                errors['business_email'] = 'This email is already registered'
                
    elif 'business_name' in request.POST:
        field_name = 'business_name'
        field_value = request.POST.get('business_name', '').strip()
        
        if not field_value:
            errors['business_name'] = 'Business name is required'
        elif len(field_value) < 3:
            errors['business_name'] = 'Business name must be at least 3 characters'
            
    elif 'username' in request.POST:
        field_name = 'username'
        field_value = request.POST.get('username', '').strip()
        
        if not field_value:
            errors['username'] = 'Username is required'
        elif len(field_value) < 4:
            errors['username'] = 'Username must be at least 4 characters'
        elif not re.match(r'^[a-zA-Z0-9_]+$', field_value):
            errors['username'] = 'Username can only contain letters, numbers, and underscores'
        else:
            # Check if username already exists
            from django.contrib.auth import get_user_model
            User = get_user_model()
            if User.objects.filter(username=field_value).exists():
                errors['username'] = 'This username is already taken'
                
    elif 'password' in request.POST:
        field_name = 'password'
        field_value = request.POST.get('password', '')
        
        if not field_value:
            errors['password'] = 'Password is required'
        elif len(field_value) < 8:
            errors['password'] = 'Password must be at least 8 characters'
        elif not re.search(r'[A-Z]', field_value):
            errors['password'] = 'Password must contain at least one uppercase letter'
        elif not re.search(r'[a-z]', field_value):
            errors['password'] = 'Password must contain at least one lowercase letter'
        elif not re.search(r'\d', field_value):
            errors['password'] = 'Password must contain at least one number'
            
    elif 'confirm_password' in request.POST:
        field_name = 'confirm_password'
        field_value = request.POST.get('confirm_password', '')
        password = request.POST.get('password', '')
        
        if not field_value:
            errors['confirm_password'] = 'Please confirm your password'
        elif field_value != password:
            errors['confirm_password'] = 'Passwords do not match'
            
    elif 'business_phone' in request.POST:
        field_name = 'business_phone'
        field_value = request.POST.get('business_phone', '').strip()
        
        if not field_value:
            errors['business_phone'] = 'Business phone is required'
        elif not re.match(r'^\+?[\d\s\-\(\)]{10,}$', field_value):
            errors['business_phone'] = 'Please enter a valid phone number'
            
    elif 'commercial_register_no' in request.POST:
        field_name = 'commercial_register_no'
        field_value = request.POST.get('commercial_register_no', '').strip()
        
        if not field_value:
            errors['commercial_register_no'] = 'Commercial register number is required'
        elif len(field_value) < 5:
            errors['commercial_register_no'] = 'Commercial register number must be at least 5 characters'
            
    elif 'tax_id_no' in request.POST:
        field_name = 'tax_id_no'
        field_value = request.POST.get('tax_id_no', '').strip()
        
        if not field_value:
            errors['tax_id_no'] = 'Tax ID number is required'
        elif len(field_value) < 5:
            errors['tax_id_no'] = 'Tax ID number must be at least 5 characters'
            
    elif 'address' in request.POST:
        field_name = 'address'
        field_value = request.POST.get('address', '').strip()
        
        if not field_value:
            errors['address'] = 'Address is required'
        elif len(field_value) < 10:
            errors['address'] = 'Please enter a complete address'
            
    elif 'city' in request.POST:
        field_name = 'city'
        field_value = request.POST.get('city', '').strip()
        
        if not field_value:
            errors['city'] = 'City is required'
        elif len(field_value) < 2:
            errors['city'] = 'Please enter a valid city name'
            
    elif 'city_id' in request.POST:
        field_name = 'city_id'
        field_value = request.POST.get('city_id', '').strip()
        
        if not field_value:
            errors['city'] = 'City is required'  # Use 'city' for consistency with main validation
        elif not field_value.isdigit():
            errors['city'] = 'Please select a valid city'  # Use 'city' for consistency with main validation
            
    elif 'country' in request.POST:
        field_name = 'country'
        field_value = request.POST.get('country', '').strip()
        
        if not field_value:
            errors['country'] = 'Country is required'
        elif field_value == '':
            errors['country'] = 'Please select a country'
            
    elif 'subscription_plan' in request.POST:
        field_name = 'subscription_plan'
        field_value = request.POST.get('subscription_plan', '').strip()
        
        if not field_value:
            errors['subscription_plan'] = 'Subscription plan is required'
        elif field_value not in ['basic', 'professional', 'enterprise']:
            errors['subscription_plan'] = 'Please select a valid subscription plan'
            
    elif 'selected_services' in request.POST:
        field_name = 'selected_services'
        field_value = request.POST.get('selected_services', '').strip()
        
        if not field_value or field_value == '[]':
            errors['selected_services'] = 'Please select at least one service'
        else:
            try:
                import json
                services = json.loads(field_value)
                if not isinstance(services, list) or len(services) == 0:
                    errors['selected_services'] = 'Please select at least one service'
            except json.JSONDecodeError:
                errors['selected_services'] = 'Invalid services selection'
    
    context = {
        'field': field_name,
        'value': field_value,
        'errors': errors,
        'is_valid': len(errors) == 0
    }
    
    return render(request, 'business_partners/htmx/registration_validation.html', context)


@require_http_methods(["POST"])
def vendor_registration_validate_step_htmx(request, step_number):
    """
    HTMX endpoint for validating entire steps in vendor registration
    Validates all required fields for a specific step before allowing navigation
    """
    from django.core.exceptions import ValidationError
    from django.contrib.auth import get_user_model
    import re
    
    User = get_user_model()
    errors = {}
    step_valid = True
    
    if step_number == 1:
        # Step 1: Account Creation (Business Email & Password)
        business_email = request.POST.get('business_email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        if not business_email:
            errors['business_email'] = 'Business email is required'
            step_valid = False
        else:
            # Email validation
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, business_email):
                errors['business_email'] = 'Please enter a valid email address'
                step_valid = False
            elif User.objects.filter(email=business_email).exists():
                errors['business_email'] = 'This email is already registered'
                step_valid = False
        
        if not password:
            errors['password'] = 'Password is required'
            step_valid = False
        elif len(password) < 8:
            errors['password'] = 'Password must be at least 8 characters'
            step_valid = False
        elif not re.search(r'[A-Z]', password):
            errors['password'] = 'Password must contain at least one uppercase letter'
            step_valid = False
        elif not re.search(r'[a-z]', password):
            errors['password'] = 'Password must contain at least one lowercase letter'
            step_valid = False
        elif not re.search(r'\d', password):
            errors['password'] = 'Password must contain at least one number'
            step_valid = False
            
        if password != confirm_password:
            errors['confirm_password'] = 'Passwords do not match'
            step_valid = False
    
    elif step_number == 2:
        # Step 2: Business Details
        business_name = request.POST.get('business_name', '').strip()
        country = request.POST.get('country', '').strip()
        city = request.POST.get('city_id', '').strip()
        address = request.POST.get('address', '').strip()
        business_phone = request.POST.get('business_phone', '').strip()
        commercial_register_no = request.POST.get('commercial_register_no', '').strip()
        tax_id_no = request.POST.get('tax_id_no', '').strip()
        
        if not business_name:
            errors['business_name'] = 'Business name is required'
            step_valid = False
        elif len(business_name) < 3:
            errors['business_name'] = 'Business name must be at least 3 characters'
            step_valid = False
            
        if not country:
            errors['country'] = 'Country is required'
            step_valid = False
            
        if not city:
            errors['city'] = 'City is required'
            step_valid = False
            
        if not address:
            errors['address'] = 'Address is required'
            step_valid = False
            
        if not business_phone:
            errors['business_phone'] = 'Business phone is required'
            step_valid = False
        elif not re.match(r'^\+?[\d\s\-\(\)]{7,}$', business_phone):
            errors['business_phone'] = 'Please enter a valid phone number'
            step_valid = False
            
        if not commercial_register_no:
            errors['commercial_register_no'] = 'Commercial Register Number is required'
            step_valid = False
            
        if not tax_id_no:
            errors['tax_id_no'] = 'Tax ID number is required'
            step_valid = False
            
        # Note: File validation is handled client-side and during final submission
        # HTMX step validation doesn't include files in the request
    
    elif step_number == 3:
        # Step 3: Subscription Plan
        subscription_plan = request.POST.get('subscription_plan', '').strip()
        
        if not subscription_plan:
            errors['subscription_plan'] = 'Subscription plan is required'
            step_valid = False
        elif subscription_plan not in ['basic', 'professional', 'enterprise']:
            errors['subscription_plan'] = 'Please select a valid subscription plan'
            step_valid = False
    
    elif step_number == 4:
        # Step 4: Final Step (Services and Terms)
        selected_services = request.POST.getlist('selected_services', [])
        terms_accepted = request.POST.get('terms_accepted', '') == 'on'
        
        if not selected_services or len(selected_services) == 0:
            errors['selected_services'] = 'Please select at least one service'
            step_valid = False
            
        if not terms_accepted:
            errors['terms_accepted'] = 'You must accept the Terms & Conditions'
            step_valid = False
    
    context = {
        'step_number': step_number,
        'errors': errors,
        'is_valid': step_valid,
        'success': step_valid
    }
    
    return render(request, 'business_partners/htmx/step_validation.html', context)


@require_http_methods(["POST"])
def vendor_submit_application_htmx(request):
    """
    HTMX endpoint to submit vendor application
    Returns success message HTML fragment
    """
    # Create vendor application
    application = VendorApplication.objects.create(
        business_name=request.POST.get('business_name'),
        contact_name=request.POST.get('contact_name'),
        email=request.POST.get('email'),
        phone=request.POST.get('phone'),
        business_address=request.POST.get('business_address'),
        business_type=request.POST.get('business_type', 'retail'),
        tax_id=request.POST.get('tax_id', ''),
        status='pending',
    )

    context = {
        'application': application,
    }

    return render(request, 'business_partners/htmx/application_success.html', context)


@require_http_methods(["POST"])
def vendor_registration_submit_htmx(request):
    """
    HTMX endpoint for vendor registration submission
    Creates user account, vendor profile, and handles file uploads
    """
    from django.contrib.auth import get_user_model
    from django.db import transaction
    from .models import BusinessPartner, BusinessPartnerRole, ContactInfo, VendorProfile, VendorApplication
    from .document_models import VendorDocument, DocumentCategory
    import uuid
    import json
    
    User = get_user_model()
    
    response_data = {
        'success': False,
        'message': '',
        'errors': {},
        'redirect_url': None
    }
    
    try:
        # Extract form data
        business_email = request.POST.get('business_email', '').strip()
        business_name = request.POST.get('business_name', '').strip()
        address = request.POST.get('address', '').strip()
        selected_currency = request.POST.get('currency', '').strip()
        
        # Handle city (check city_id first as it's a select box now)
        city_id = request.POST.get('city_id', '').strip()
        city = request.POST.get('city', '').strip()
        
        if not city and city_id:
            try:
                from parts.models import City
                if city_id.isdigit():
                    city = City.objects.get(id=int(city_id)).name
            except Exception:
                pass
                
        country = request.POST.get('country', '').strip()
        phone_type = request.POST.get('phone_type', 'mobile').strip()
        business_phone = request.POST.get('business_phone', '').strip()
        commercial_register_no = request.POST.get('commercial_register_no', '').strip()
        tax_id_no = request.POST.get('tax_id_no', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        subscription_plan = request.POST.get('subscription_plan', 'starter')
        
        # Handle selected services (supports both JSON string and standard form list)
        selected_services_raw = request.POST.get('selected_services')
        services = request.POST.getlist('selected_services')
        
        # If getlist returned nothing or it looks like a JSON string, try parsing
        if not services and selected_services_raw:
            try:
                import json
                parsed_services = json.loads(selected_services_raw)
                if isinstance(parsed_services, list):
                    services = parsed_services
                else:
                    services = [selected_services_raw]
            except json.JSONDecodeError:
                services = [selected_services_raw]
        
        # Validate required fields
        required_fields = {
            'business_email': 'Business email',
            'business_name': 'Business name',
            'address': 'Address',
            'city': 'City',
            'country': 'Country',
            'business_phone': 'Business phone',
            'commercial_register_no': 'Commercial register number',
            'tax_id_no': 'Tax ID number',
            'password': 'Password',
            'confirm_password': 'Confirm password'
        }
        
        for field_key, field_label in required_fields.items():
            if not locals().get(field_key):
                response_data['errors'][field_key] = f'{field_label} is required'
                
        # Validate file uploads
        if 'commercial_register_file' not in request.FILES:
            response_data['errors']['commercial_register_file'] = 'Commercial Register file is required'
            
        if 'tax_certificate_file' not in request.FILES:
            response_data['errors']['tax_certificate_file'] = 'Tax Certificate file is required'
        
        # Validate services selection
        if not services or len(services) == 0:
            response_data['errors']['selected_services'] = 'Please select at least one service'
        
        # Validate password match
        if password != confirm_password:
            response_data['errors']['confirm_password'] = 'Passwords do not match'
        
        # Validate email uniqueness
        if User.objects.filter(email=business_email).exists():
            response_data['errors']['business_email'] = 'This email is already registered'
        
        # Check for validation errors
        if response_data['errors']:
            return render(request, 'business_partners/htmx/registration_response.html', response_data)
        
        # Create user and vendor profile in transaction
        try:
            with transaction.atomic():
                # Create user account with current timestamp
                from django.utils import timezone
                current_time = timezone.now()
                
                # Create user account with current timestamp (using email as username for custom User model)
                user = User.objects.create_user(
                    email=business_email,  # Use email as username since it's the USERNAME_FIELD
                    password=password,
                    first_name=business_name[:30],  # Use business name as first name since username field is removed
                    last_name='',  # Empty last name for vendor accounts
                    is_active=True,  # Set user as active
                    is_staff=False,  # Not a staff member
                    is_superuser=False,  # Not a superuser
                    date_joined=current_time  # Set registration timestamp
                )
                
                # Create BusinessPartner with enhanced details and timestamps
                # Note: We use save() to trigger auto-generation of BP number
                business_partner = BusinessPartner(
                    name=business_name,
                    slug=f'vendor-{business_email.split("@")[0]}',  # Use email prefix for slug
                    type='company',
                    status='pending',
                    legal_identifier=tax_id_no,  # Store tax ID as legal identifier
                    user=user,  # Link to the created user account
                    created_by=user
                )
                business_partner.save() # This generates the BP number (BPxxxxxx)
                
                # Create vendor role
                BusinessPartnerRole.objects.create(
                    business_partner=business_partner,
                    role_type='vendor'
                )
                
                # Create ContactInfo
                ContactInfo.objects.create(
                    business_partner=business_partner,
                    contact_type='email',
                    value=business_email,
                    is_primary=True
                )
                
                ContactInfo.objects.create(
                    business_partner=business_partner,
                    contact_type='phone',
                    value=f"{phone_type}: {business_phone}",
                    is_primary=True
                )
                
                # Create vendor profile with enhanced details and timestamps
                # Use the currency selected by the vendor during registration
                vendor_profile = VendorProfile.objects.create(
                    business_partner=business_partner,
                    user=user,  # Link to Django user account
                    tax_id=tax_id_no,
                    is_approved=False,
                    registration_date=current_time.date(),  # Set registration date
                    created_at=current_time,  # Set creation timestamp
                    updated_at=current_time,   # Set initial update timestamp
                    preferred_currency=selected_currency
                )
                
                # Handle file uploads
                # Get or create document categories for commercial register and tax certificate
                commercial_register_category, _ = DocumentCategory.objects.get_or_create(
                    name='Commercial Register',
                    defaults={
                        'description': 'Commercial registration document for vendors',
                        'required': True,
                        'verification_required': True
                    }
                )
                
                tax_certificate_category, _ = DocumentCategory.objects.get_or_create(
                    name='Tax Certificate',
                    defaults={
                        'description': 'Tax certificate document for vendors',
                        'required': True,
                        'verification_required': True
                    }
                )
                
                if 'commercial_register_file' in request.FILES:
                    cr_file = request.FILES['commercial_register_file']
                    VendorDocument.objects.create(
                        business_partner=business_partner,
                        category=commercial_register_category,
                        title='Commercial Register',
                        file=cr_file,
                        uploaded_by=None
                    )
                    
                if 'tax_certificate_file' in request.FILES:
                    tax_file = request.FILES['tax_certificate_file']
                    VendorDocument.objects.create(
                        business_partner=business_partner,
                        category=tax_certificate_category,
                        title='Tax Certificate',
                        file=tax_file,
                        uploaded_by=None
                    )
                
                # Handle Vendor Application (Find existing or create new)
                # Check for existing anonymous application in session
                session_key = request.session.session_key
                application = None
                
                if session_key:
                    # Find the most recent anonymous application for this session
                    application = VendorApplication.objects.filter(
                        session_key=session_key, 
                        user__isnull=True
                    ).order_by('-updated_at').first()
                
                if not application:
                    # Fallback: Check by email to avoid duplicates
                    application = VendorApplication.objects.filter(
                        business_email=business_email, 
                        user__isnull=True
                    ).order_by('-created_at').first()
                
                if application:
                    # Update existing application
                    application.user = user
                    application.company_name = business_name
                    application.contact_person_name = business_name # Use business name as contact person since username is removed
                    application.business_email = business_email
                    application.business_phone = business_phone
                    application.street_address = address
                    application.city = city
                    application.country = country
                    application.business_type = 'other'
                    application.legal_identifier = tax_id_no
                    application.status = 'submitted'
                    application.current_step = 4
                    application.submitted_at = current_time
                    application.save()
                else:
                    # Create new vendor application if none exists
                    application = VendorApplication.objects.create(
                        user=user,
                        company_name=business_name,
                        contact_person_name=business_name, # Use business name as contact person since username is removed
                        business_email=business_email,
                        business_phone=business_phone,
                        street_address=address,
                        city=city,
                        country=country,
                        business_type='other',
                        legal_identifier=tax_id_no,
                        status='submitted',
                        current_step=4,
                        submitted_at=current_time
                    )
                
                # No need to call create_provisional_profile() as we manually created the full profile above
                # application.create_provisional_profile()
            
            # Auto-login the user with CentralizedAuthenticationService
            from core.authentication import CentralizedAuthenticationService
            auth_service = CentralizedAuthenticationService()
            auth_service.establish_secure_session(request, user, backend='django.contrib.auth.backends.ModelBackend')

            response_data['success'] = True
            response_data['message'] = 'Registration successful.'
            # Redirect to dashboard
            response_data['redirect_url'] = '/business-partners/vendor/dashboard/'
            
        except Exception as e:
            response_data['message'] = f'Registration failed: {str(e)}'
            response_data['errors']['general'] = 'An error occurred during registration. Please try again.'
        
        return render(request, 'business_partners/htmx/registration_response.html', response_data)
    
    except Exception as e:
        response_data['message'] = f'Registration failed: {str(e)}'
        response_data['errors']['general'] = 'An error occurred during registration. Please try again.'
    
    return render(request, 'business_partners/htmx/registration_response.html', response_data)


# =====================
# VENDOR LOGIN HTMX
# =====================

@require_http_methods(["GET"])
def vendor_login_form_htmx(request):
    """
    HTMX endpoint for vendor login form
    Returns login form HTML fragment with real-time validation
    """
    from .auth_forms import VendorLoginForm
    
    form = VendorLoginForm()
    context = {
        'form': form,
        'show_password_reset': True,
        'show_remember_me': True,
    }
    
    return render(request, 'business_partners/htmx/vendor_login_form.html', context)


@require_http_methods(["POST"])
def vendor_login_validate_htmx(request):
    """
    HTMX endpoint for real-time login validation
    Validates email format and returns validation feedback
    """
    from .auth_forms import VendorLoginForm
    
    # Get field data from HTMX request
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '').strip()
    
    field_name = ''
    field_value = ''
    errors = {}
    
    # Validate email field
    if 'email' in request.POST:
        field_name = 'email'
        field_value = email
        # Basic email format validation
        import re
        if not email:
            errors['email'] = 'Email is required'
        elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            errors['email'] = 'Please enter a valid email address'
    
    # Validate password field
    elif 'password' in request.POST:
        field_name = 'password'
        field_value = password
        if not password:
            errors['password'] = 'Password is required'
        elif len(password) < 6:
            errors['password'] = 'Password must be at least 6 characters'
    
    context = {
        'field': field_name,
        'value': field_value,
        'errors': errors,
        'is_valid': len(errors) == 0
    }
    
    return render(request, 'business_partners/htmx/login_validation.html', context)


@require_http_methods(["POST"])
def vendor_login_submit_htmx(request):
    """
    HTMX endpoint for vendor login submission
    Handles login with AJAX response and progress saving
    """
    from django.contrib.auth import authenticate, login
    from django.contrib.auth import get_user_model
    from .permissions import get_vendor_profile
    from users.models import UserRole
    
    User = get_user_model()
    
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '')
    remember_me = request.POST.get('remember_me', 'false') == 'true'
    
    # Clear any previous login errors from session
    if hasattr(request, 'session'):
        request.session.pop('login_error', None)
    
    # Initialize response data
    response_data = {
        'success': False,
        'message': '',
        'redirect_url': None,
        'errors': {}
    }
    
    # Validate inputs
    if not email:
        response_data['errors']['email'] = 'Email is required'
    if not password:
        response_data['errors']['password'] = 'Password is required'
    
    if response_data['errors']:
        return render(request, 'business_partners/htmx/login_response.html', response_data)
    
    try:
        # Use centralized authentication service
        from core.authentication import CentralizedAuthenticationService
        auth_service = CentralizedAuthenticationService()
        
        # Authenticate user through unified system
        user, redirect_url = auth_service.authenticate_user(
            request, email, password, remember_me
        )
        
        if user is not None:
            # Check if user has vendor profile
            vendor_profile = get_vendor_profile(user)
            
            if vendor_profile:
                # Vendor login successful
                response_data['success'] = True
                response_data['message'] = 'Login successful! Redirecting...'
                # Prefer the redirect_url from auth_service, but fallback to vendor dashboard
                response_data['redirect_url'] = redirect_url if redirect_url and 'dashboard' in redirect_url else '/business-partners/vendor/dashboard/'
            else:
                # Non-vendor login (e.g. admin or regular user)
                response_data['success'] = True
                response_data['message'] = 'Login successful! Redirecting...'
                response_data['redirect_url'] = redirect_url or '/'
        else:
            # Authentication failed
            error_msg = redirect_url or 'Invalid email or password'
            response_data['message'] = error_msg
            response_data['errors']['general'] = error_msg
            
            # Store error in session so the status polling endpoint can catch it
            if hasattr(request, 'session'):
                request.session['login_error'] = error_msg
            
    except Exception as e:
        response_data['message'] = 'Authentication error'
        response_data['errors']['general'] = f'Error: {str(e)}'
    
    return render(request, 'business_partners/htmx/login_response.html', response_data)


@require_http_methods(["GET"])
def vendor_login_status_htmx(request):
    """
    HTMX endpoint to check login status and progress
    Returns login status for progress saving
    """
    from django.http import JsonResponse
    from django.contrib.auth import get_user_model
    from .permissions import get_vendor_profile
    from django.contrib.sessions.exceptions import SessionInterrupted
    
    User = get_user_model()
    
    status_data = {
        'is_authenticated': False,
        'user_email': None,
        'is_vendor': False,
        'vendor_status': None,
        'status': 'pending',
        'redirect_url': None
    }
    
    try:
        # Check authentication status
        status_data['is_authenticated'] = request.user.is_authenticated
        if request.user.is_authenticated:
            status_data['user_email'] = request.user.email
            
            # Determine correct redirect URL based on role
            from core.role_routing_engine import RoleResolver
            resolver = RoleResolver()
            redirect_url = resolver.get_role_based_redirect(request.user)
            status_data['redirect_url'] = redirect_url

            vendor_profile = get_vendor_profile(request.user)
            if vendor_profile:
                status_data['is_vendor'] = True
                # Use approval_state as the status field for VendorProfile
                status_data['vendor_status'] = vendor_profile.approval_state
                # Also check legacy is_approved field for backward compatibility
                is_approved = vendor_profile.approval_state == 'APPROVED' or getattr(vendor_profile, 'is_approved', False)
                status_data['is_approved'] = is_approved
                
                # Determine redirect URL based on status
                status_data['status'] = 'complete'
                # Already set redirect_url above, but ensure it's vendor dashboard if they are a vendor
                if not status_data['redirect_url'] or 'vendor' not in status_data['redirect_url']:
                    status_data['redirect_url'] = '/business-partners/vendor/dashboard/'
            else:
                # Regular user logged in
                status_data['status'] = 'complete'
                # redirect_url already set by resolver above
                
        # Check for login error in session
        if hasattr(request, 'session'):
            try:
                login_error = request.session.get('login_error')
                if login_error:
                    status_data['status'] = 'error'
                    status_data['message'] = login_error
                    # Clear it so we don't keep returning error
                    request.session.pop('login_error', None)
            except Exception:
                pass

    except SessionInterrupted:
        # Handle concurrent session cycling (e.g. during login)
        status_data['status'] = 'pending'
        status_data['is_authenticated'] = False
    except Exception as e:
        import logging
        logger = logging.getLogger('django')
        logger.error(f"Error in vendor_login_status_htmx: {str(e)}")
        status_data['status'] = 'pending'
            
    response = JsonResponse(status_data)
    
    # CRITICAL: Prevent HTMX polling from ever sending a session cookie.
    # This prevents the "unauthenticated poll" from overwriting the "authenticated login" cookie.
    if hasattr(request, 'session'):
        request.session.modified = False
    
    # Force removal of set-cookie header for this polling endpoint
    if 'Set-Cookie' in response:
        del response['Set-Cookie']
        
    return response
