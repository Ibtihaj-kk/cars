"""
HTMX Views for Business Partners/Vendors Module
Server-side rendered views for vendor management and inventory
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import timedelta

from .models import VendorProfile, VendorApplication, BusinessPartner, BusinessPartnerRole, ContactInfo
from .document_models import VendorDocument, DocumentCategory
from parts.models import Part, Order, OrderItem
from vehicles.models import VehicleMake, VehicleModel


# =====================
# VENDOR DASHBOARD
# =====================

@login_required
@require_http_methods(["GET"])
def vendor_dashboard_htmx(request):
    """
    HTMX endpoint for vendor dashboard
    Returns dashboard stats HTML fragment
    """
    vendor_profile = get_object_or_404(VendorProfile, user=request.user)

    # Get statistics
    total_parts = Part.objects.filter(dealer=request.user).count()
    active_parts = Part.objects.filter(dealer=request.user, is_active=True).count()
    low_stock = Part.objects.filter(
        dealer=request.user,
        stock_quantity__lte=5,
        stock_quantity__gt=0
    ).count()
    out_of_stock = Part.objects.filter(
        dealer=request.user,
        stock_quantity=0
    ).count()

    # Recent orders (last 30 days)
    last_30_days = timezone.now() - timedelta(days=30)
    recent_orders = Order.objects.filter(
        items__part__dealer=request.user,
        created_at__gte=last_30_days
    ).distinct()

    monthly_revenue = sum(order.total_amount for order in recent_orders)
    monthly_orders = recent_orders.count()

    # Recent order items
    recent_items = OrderItem.objects.filter(
        part__dealer=request.user
    ).select_related('order', 'part').order_by('-created_at')[:10]

    context = {
        'vendor': vendor_profile,
        'vendor_profile': vendor_profile,
        'is_approved': vendor_profile.is_approved if vendor_profile else False,
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
    # Filter parameters
    status_filter = request.GET.get('status', 'all')
    search = request.GET.get('search', '')

    # Base queryset
    parts = Part.objects.filter(
        dealer=request.user
    ).select_related('make', 'model', 'category')

    # Apply filters
    if status_filter == 'active':
        parts = parts.filter(is_active=True)
    elif status_filter == 'inactive':
        parts = parts.filter(is_active=False)
    elif status_filter == 'low_stock':
        parts = parts.filter(stock_quantity__lte=5, stock_quantity__gt=0)
    elif status_filter == 'out_of_stock':
        parts = parts.filter(stock_quantity=0)

    if search:
        parts = parts.filter(
            Q(name__icontains=search) |
            Q(part_number__icontains=search)
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

    # Get form data
    name = request.POST.get('name')
    part_number = request.POST.get('part_number')
    description = request.POST.get('description')
    price = request.POST.get('price')
    stock_quantity = request.POST.get('stock_quantity')
    make_id = request.POST.get('make')
    model_id = request.POST.get('model')
    category_id = request.POST.get('category')

    # Validation (basic)
    if not all([name, part_number, price, stock_quantity]):
        context = {
            'error': 'All required fields must be filled',
            'part': part,
        }
        return render(request, 'business_partners/htmx/part_form.html', context)

    # Create or update part
    if part:
        part.name = name
        part.part_number = part_number
        part.description = description
        part.price = price
        part.stock_quantity = stock_quantity
        part.make_id = make_id if make_id else None
        part.model_id = model_id if model_id else None
        part.category_id = category_id if category_id else None
        part.save()
        message = 'Part updated successfully'
    else:
        part = Part.objects.create(
            dealer=request.user,
            name=name,
            part_number=part_number,
            description=description,
            price=price,
            stock_quantity=stock_quantity,
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

    part.is_active = not part.is_active
    part.save()

    context = {
        'part': part,
    }

    return render(request, 'business_partners/htmx/inventory_row.html', context)


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
    part.stock_quantity = new_quantity
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
        
        # Handle city (check city_id first as it's a select box now)
        city_id = request.POST.get('city_id', '').strip()
        city = request.POST.get('city', '').strip()
        
        if not city and city_id:
            try:
                from parts.models import SaudiCity
                if city_id.isdigit():
                    city = SaudiCity.objects.get(id=int(city_id)).name
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
                from .utils import get_currency_for_country
                currency = get_currency_for_country(country)
                
                vendor_profile = VendorProfile.objects.create(
                    business_partner=business_partner,
                    user=user,  # Link to Django user account
                    tax_id=tax_id_no,
                    is_approved=False,
                    registration_date=current_time.date(),  # Set registration date
                    created_at=current_time,  # Set creation timestamp
                    updated_at=current_time,   # Set initial update timestamp
                    preferred_currency=currency
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
            
            # Auto-login the user
            from django.contrib.auth import login
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

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
        # Authenticate user
        try:
            user_obj = User.objects.get(email=email)
            username = user_obj.username if user_obj.username else user_obj.email
        except User.DoesNotExist:
            username = email

        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Check if user has vendor profile
            vendor_profile = get_vendor_profile(user)
            
            if vendor_profile:
                # Allow login regardless of approval status
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                
                # Set session expiry based on remember me
                if remember_me:
                    request.session.set_expiry(2592000)  # 30 days
                else:
                    request.session.set_expiry(0)  # Browser session
                
                # Set flag to indicate recent login for middleware
                request.session['_just_logged_in'] = True
                request.session['_login_timestamp'] = timezone.now().isoformat()
                request.session.modified = True
                
                # Force session save to ensure middleware can see it
                request.session.save()
                
                response_data['success'] = True
                response_data['message'] = 'Login successful! Redirecting...'
                print(f"Vendor login successful for user: {user}")
                # Redirect to dashboard regardless of approval status
                response_data['redirect_url'] = '/business-partners/vendor/dashboard/'
                
            else:
                # Authenticated user but no vendor profile (Client/User/Staff/Admin)
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                
                # Set session expiry based on remember me
                if remember_me:
                    request.session.set_expiry(2592000)  # 30 days
                else:
                    request.session.set_expiry(0)  # Browser session
                
                # Set flag to indicate recent login for middleware
                request.session['_just_logged_in'] = True
                request.session['_login_timestamp'] = timezone.now().isoformat()
                request.session.modified = True
                
                # Force session save to ensure middleware can see it
                request.session.save()
                
                response_data['success'] = True
                response_data['message'] = 'Login successful! Redirecting...'
                
                # Determine redirect URL based on role
                if user.is_superuser or user.is_staff:
                    response_data['redirect_url'] = '/admin_panel/' 
                elif user.role == UserRole.CLIENT:
                    response_data['redirect_url'] = '/api/users/dashboard/'  # Redirect clients to user dashboard
                else:
                    response_data['redirect_url'] = '/'  # Default redirect
                    
        else:
            # Authentication failed
            response_data['message'] = 'Invalid email or password'
            response_data['errors']['general'] = 'Invalid credentials. Please try again.'
        print(response_data,'Kuch bhi');
    except Exception as e:
        response_data['message'] = 'Invalid email or password'
        response_data['errors']['general'] = 'Invalid credentials. Please try again.'
    
    return render(request, 'business_partners/htmx/login_response.html', response_data)


@require_http_methods(["GET"])
def vendor_login_status_htmx(request):
    """
    HTMX endpoint to check login status and progress
    Returns login status for progress saving
    """
    from django.contrib.auth import get_user_model
    from .permissions import get_vendor_profile
    
    User = get_user_model()
    
    status_data = {
        'is_authenticated': request.user.is_authenticated,
        'user_email': request.user.email if request.user.is_authenticated else None,
        'is_vendor': False,
        'vendor_status': None,
    }
    
    if request.user.is_authenticated:
        vendor_profile = get_vendor_profile(request.user)
        if vendor_profile:
            status_data['is_vendor'] = True
            status_data['vendor_status'] = vendor_profile.status
            status_data['is_approved'] = vendor_profile.is_approved
    
    return render(request, 'business_partners/htmx/login_status.html', status_data)
