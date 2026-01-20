"""
HTMX Views for Parts Module
Server-side rendered views that return HTML fragments for HTMX
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from django.db import transaction
from django.db.models import Q, Sum
from django.contrib import messages
from django.utils import timezone

from finance.services import FinanceService
from .models import Part, PartCategory, Order, OrderItem, Cart, CartItem, City, CityArea, OrderShipping
# from vehicles.models import Make, Model  # Disabled - vehicles app not in INSTALLED_APPS
from decimal import Decimal


def _percent_str_to_rate(value):
    try:
        return (Decimal(str(value)) / Decimal('100')).quantize(Decimal('0.0001'))
    except Exception:
        return None


def _get_country_standard_tax_rate(country_code):
    from admin_panel.models import AdminSetting

    country_code = (country_code or '').strip().upper()
    keys_to_try = []
    if country_code:
        country_variants = {country_code, country_code.lower()}
        for cc in country_variants:
            keys_to_try.extend([
                f'tax_{cc}_standard',
                f'tax_{cc}_vat_standard',
                f'tax_{cc}_vat',
                f'tax_{cc}',
            ])
    keys_to_try.extend([
        'tax_standard',
        'tax_vat_standard',
        'tax_vat',
    ])

    for key in keys_to_try:
        setting = AdminSetting.objects.filter(key=key).only('value').first()
        if not setting:
            continue
        rate = _percent_str_to_rate(setting.value)
        if rate is not None:
            return rate
    return Decimal('0.15')


def _get_item_tax_rate(part, country_standard_rate, dest_country_code=None):
    """
    Calculate tax rate for a specific part.
    VAT is only applied if the vendor and destination country are the same.
    """
    if dest_country_code and part.vendor:
        vendor_country_code = part.vendor.get_country_code()
        if vendor_country_code != dest_country_code:
            return Decimal('0.00')

    tax_classification = getattr(part, 'tax_classification_material', None)
    if tax_classification == 'VAT_5':
        return Decimal('0.05')
    if tax_classification in ('ZERO', 'EXEMPT'):
        return Decimal('0.00')
    if tax_classification == 'VAT_15':
        return country_standard_rate
    return country_standard_rate


# =====================
# PARTS CATALOG VIEWS
# =====================

@require_http_methods(["GET"])
def parts_list_htmx(request):
    """
    HTMX endpoint for parts listing with filters
    Returns HTML fragment with parts grid
    """
    # Get filter parameters
    search = request.GET.get('search', '')
    make_id = request.GET.get('make', '')
    model_id = request.GET.get('model', '')
    category_id = request.GET.get('category', '')
    price_min = request.GET.get('price_min', '')
    price_max = request.GET.get('price_max', '')
    sort_by = request.GET.get('sort', '-created_at')

    # Base queryset
    parts = Part.objects.filter(
        is_active=True,
        quantity__gt=0
    ).select_related('dealer', 'make', 'model', 'category')

    # Apply filters
    if search:
        parts = parts.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(part_number__icontains=search)
        )

    if make_id:
        parts = parts.filter(make_id=make_id)

    if model_id:
        parts = parts.filter(model_id=model_id)

    if category_id:
        parts = parts.filter(category_id=category_id)

    if price_min:
        parts = parts.filter(standard_price__gte=price_min)

    if price_max:
        parts = parts.filter(standard_price__lte=price_max)

    # Apply sorting
    # Map template sort values to model fields
    sort_mapping = {
        'price': 'standard_price',
        '-price': '-standard_price',
        'name': 'name',
        '-name': '-name',
        'created_at': 'created_at',
        '-created_at': '-created_at'
    }

    if sort_by in sort_mapping:
        parts = parts.order_by(sort_mapping[sort_by])
    else:
        parts = parts.order_by(sort_by)

    # Pagination
    page = int(request.GET.get('page', 1))
    per_page = 20
    start = (page - 1) * per_page
    end = start + per_page

    parts_page = parts[start:end]
    has_more = parts.count() > end

    context = {
        'parts': parts_page,
        'has_more': has_more,
        'next_page': page + 1,
    }

    return render(request, 'parts/htmx/parts_list.html', context)


@require_http_methods(["GET"])
def part_detail_htmx(request, part_id):
    """
    HTMX endpoint for part details
    Returns HTML fragment with part information
    """
    part = get_object_or_404(
        Part.objects.select_related('dealer', 'make', 'model', 'category'),
        id=part_id,
        is_active=True
    )

    # Related parts
    related_parts = Part.objects.filter(
        category=part.category,
        is_active=True,
        quantity__gt=0
    ).exclude(id=part.id)[:4]

    context = {
        'part': part,
        'related_parts': related_parts,
    }

    return render(request, 'parts/htmx/part_detail.html', context)


# =====================
# SHOPPING CART VIEWS
# =====================

@login_required
@require_http_methods(["POST"])
def add_to_cart_htmx(request, part_id):
    """
    HTMX endpoint to add item to cart
    Returns updated cart HTML fragment
    """
    part = get_object_or_404(Part, id=part_id, is_active=True)
    quantity = int(request.POST.get('quantity', 1))

    if quantity < 1:
        return HttpResponse('<span class="text-danger">Invalid quantity</span>')

    # Check stock availability
    available_stock = part.quantity
    if quantity > available_stock:
        context = {
            'cart_count': Cart.objects.filter(user=request.user, is_active=True).first().items.aggregate(total=Sum('quantity'))['total'] or 0,
            'message': f'Error: Only {available_stock} items available.',
            'message_type': 'error'
        }
        return render(request, 'parts/htmx/cart_badge.html', context)

    # Get or create cart
    cart, created = Cart.objects.get_or_create(
        user=request.user,
        is_active=True
    )

    # Check if adding this quantity exceeds stock (considering existing cart item)
    current_cart_quantity = 0
    cart_item = CartItem.objects.filter(cart=cart, part=part).first()
    if cart_item:
        current_cart_quantity = cart_item.quantity

    if current_cart_quantity + quantity > available_stock:
         context = {
            'cart_count': cart.items.aggregate(total=Sum('quantity'))['total'] or 0,
            'message': f'Error: Only {available_stock} items available (You have {current_cart_quantity} in cart).',
            'message_type': 'error'
        }
         return render(request, 'parts/htmx/cart_badge.html', context)

    # Add or update cart item
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        part=part,
        defaults={'quantity': quantity}
    )

    if not created:
        cart_item.quantity += quantity
        cart_item.save()
    
    # Lock exchange rate for 15 minutes (Amazon-style soft lock)
    cart_item.lock_exchange_rate()
    cart.refresh_rate_locks()

    # Get updated cart
    cart_items = CartItem.objects.filter(cart=cart).select_related('part')
    cart_count = sum(item.quantity for item in cart_items)

    context = {
        'cart_count': cart_count,
        'message': f'{part.name} added to cart',
        'message_type': 'success'
    }

    return render(request, 'parts/htmx/cart_badge.html', context)


@login_required
@require_http_methods(["GET"])
def cart_view_htmx(request):
    """
    HTMX endpoint for shopping cart
    Returns cart items HTML fragment
    """
    try:
        cart = Cart.objects.get(user=request.user, is_active=True)
        cart_items = CartItem.objects.filter(cart=cart).select_related('part')
    except Cart.DoesNotExist:
        cart_items = []

    # Calculate totals
    subtotal = sum(item.part.price * item.quantity for item in cart_items)
    tax = subtotal * 0.05  # 5% tax
    shipping = 0  # Free shipping or calculate
    total = subtotal + tax + shipping

    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'tax': tax,
        'shipping': shipping,
        'total': total,
    }

    return render(request, 'parts/htmx/cart_detail.html', context)


@login_required
@require_http_methods(["POST"])
def update_cart_item_htmx(request, item_id):
    """
    HTMX endpoint to update cart item quantity
    Returns updated cart item HTML fragment
    """
    cart_item = get_object_or_404(
        CartItem.objects.select_related('part'),
        id=item_id,
        cart__user=request.user
    )

    quantity = int(request.POST.get('quantity', 1))

    if quantity > 0:
        # Check stock
        if quantity > cart_item.part.quantity:
            quantity = cart_item.part.quantity
            
        cart_item.quantity = quantity
        cart_item.save()
    else:
        cart_item.delete()

    # Recalculate cart totals
    cart_items = CartItem.objects.filter(
        cart=cart_item.cart
    ).select_related('part')

    subtotal = sum(item.part.price * item.quantity for item in cart_items)

    context = {
        'cart_item': cart_item if quantity > 0 else None,
        'subtotal': subtotal,
    }

    return render(request, 'parts/htmx/cart_item.html', context)


@login_required
@require_http_methods(["DELETE"])
def remove_cart_item_htmx(request, item_id):
    """
    HTMX endpoint to remove item from cart
    Returns empty response with swap OOB for cart update
    """
    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )

    cart_item.delete()

    # Return empty response - HTMX will remove the element
    return HttpResponse('')


# =====================
# CHECKOUT VIEWS
# =====================

@login_required
@require_http_methods(["GET"])
def checkout_htmx(request):
    """
    HTMX endpoint for checkout page
    Returns checkout form HTML fragment
    """
    try:
        cart = Cart.objects.get(user=request.user, is_active=True)
        cart_items = CartItem.objects.filter(cart=cart).select_related('part')
    except Cart.DoesNotExist:
        return redirect('parts:cart')

    if not cart_items:
        return redirect('parts:cart')

    # Calculate totals
    subtotal = sum(item.part.price * item.quantity for item in cart_items)
    tax = subtotal * 0.05
    shipping = 0
    total = subtotal + tax + shipping

    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'tax': tax,
        'shipping': shipping,
        'total': total,
        'user': request.user,
    }

    return render(request, 'parts/htmx/checkout.html', context)


@login_required
@require_http_methods(["POST"])
def place_order_htmx(request):
    """
    HTMX endpoint to place order
    Returns order confirmation HTML fragment
    """
    try:
        cart = Cart.objects.get(user=request.user, is_active=True)
        cart_items = CartItem.objects.filter(cart=cart).select_related('part')
    except Cart.DoesNotExist:
        return redirect('parts:cart')

    if not cart_items:
        return redirect('parts:cart')

    # Extract form data
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    email = request.POST.get('email', '').strip()
    phone = request.POST.get('phone', '').strip()
    address = request.POST.get('address', '').strip()
    city_id = request.POST.get('city', '')
    city_area_id = request.POST.get('area', '')
    payment_method_input = (request.POST.get('payment_method') or 'cod').strip()
    if payment_method_input in ['cod', 'cash_on_delivery']:
        order_payment_method = 'cash_on_delivery'
        finance_payment_method = 'cod'
    else:
        order_payment_method = payment_method_input
        finance_payment_method = payment_method_input

    city = None
    if city_id:
        try:
            city = City.objects.select_related('country').get(id=city_id)
        except City.DoesNotExist:
            city = None
    country_code = getattr(getattr(city, 'country', None), 'code', None) if city else None
    country_standard_rate = _get_country_standard_tax_rate(country_code)
    
    # Calculate totals
    subtotal = Decimal('0.00')
    for item in cart_items:
        original_price = item.part.standard_price
        if original_price is None:
            original_price = getattr(item.part, 'price', Decimal('0.00'))
        if original_price is None:
            original_price = Decimal('0.00')
        subtotal += original_price * item.quantity
    
    # Calculate tax based on item classification
    from core.models import ExchangeRate
    tax_amount = Decimal('0.00')
    order_items_data = []
    
    for item in cart_items:
        item_tax_rate = _get_item_tax_rate(item.part, country_standard_rate, dest_country_code=country_code)
        
        # IMPORTANT: Convert price to USD (Base Currency) for storage
        original_price = item.part.standard_price
        if original_price is None:
            original_price = getattr(item.part, 'price', Decimal('0.00'))
        if original_price is None:
            original_price = Decimal('0.00')
            
        original_currency = getattr(item.part, 'original_currency', 'USD') or 'USD'
        
        item_price_usd = original_price
        locked_rate = Decimal('1.000000')
        
        if original_currency != 'USD':
            locked_rate = Decimal(str(ExchangeRate.get_current_rate(original_currency, 'USD')))
            item_price_usd = (original_price * locked_rate).quantize(Decimal('0.01'))
        
        item_total_usd = item_price_usd * item.quantity
        item_tax_usd = (item_total_usd * item_tax_rate).quantize(Decimal('0.01'))
        tax_amount += item_tax_usd # Accumulate tax in USD
        
        order_items_data.append({
            'part': item.part,
            'quantity': item.quantity,
            'price': item_price_usd,
            'tax_amount': item_tax_usd,
            'locked_rate': locked_rate,
            'original_price': original_price,
            'original_currency': original_currency
        })

    shipping_cost = Decimal('0.00') # Free shipping or calculate
    # Recalculate grand total in USD
    subtotal_usd = sum(d['price'] * d['quantity'] for d in order_items_data)
    grand_total = subtotal_usd + tax_amount + shipping_cost

    try:
        with transaction.atomic():
            # Create order
            order = Order.objects.create(
                customer=request.user,
                total_price=grand_total,
                shipping_cost=shipping_cost,
                tax_amount=tax_amount,
                status='pending',
                payment_method=order_payment_method,
                payment_status='pending'
            )

            # Create order items
            for item_data in order_items_data:
                OrderItem.objects.create(
                    order=order,
                    part=item_data['part'],
                    quantity=item_data['quantity'],
                    price=item_data['price'],
                    tax_amount=item_data['tax_amount'],
                    locked_exchange_rate=item_data['locked_rate'],
                    vendor_currency_amount=item_data['original_price'],
                    original_currency_code=item_data['original_currency']
                )
            
            # Lock exchange rates on the order
            order.exchange_rate_locked_at = timezone.now()
            order.exchange_rate_valid_until = timezone.now() + timezone.timedelta(hours=24)
            order.save()
                
            # Subtract inventory using the model method which handles both Inventory and Part models
            # Phase 1: Reserve inventory
            order.reserve_inventory()
            
            # Phase 2: Finalize inventory
            # For COD/Bank Transfer we finalize immediately as there's no online payment step.
            # For online payments (credit_card, paypal), finalize_inventory will be called 
            # via signals when payment_status changes to 'completed'.
            if order_payment_method in ['cash_on_delivery', 'bank_transfer']:
                order.finalize_inventory()

            # Record Financial Transactions
            FinanceService.record_order_payment(order, payment_method=finance_payment_method)
            
            # Create Shipping Info
            city_area = None
            if city_area_id:
                try:
                    city_area = CityArea.objects.get(id=city_area_id)
                except CityArea.DoesNotExist:
                    pass
            
            OrderShipping.objects.create(
                order=order,
                contact_name=f"{first_name} {last_name}".strip(),
                mobile_number=phone,
                city=city,
                city_area=city_area,
                address=address,
                shipping_cost=shipping_cost
            )

            # Clear cart properly
            cart.items.all().delete()
            # We don't mark it inactive here if we want to keep it for future use, 
            # but usually checkout clears the current active cart.
            # cart.is_active = False
            # cart.save()

            context = {
                'order': order,
            }

            return render(request, 'parts/htmx/order_confirmation.html', context)
            
    except Exception as e:
        # If stock runs out or any other error occurs during checkout
        return render(request, 'parts/htmx/error_message.html', {'message': str(e)})


# =====================
# ORDERS VIEWS
# =====================

@login_required
@require_http_methods(["GET"])
def orders_list_htmx(request):
    """
    HTMX endpoint for user's orders list
    Returns orders HTML fragment
    """
    orders = Order.objects.filter(
        user=request.user
    ).prefetch_related('items__part').order_by('-created_at')

    context = {
        'orders': orders,
    }

    return render(request, 'parts/htmx/orders_list.html', context)


@login_required
@require_http_methods(["GET"])
def order_detail_htmx(request, order_id):
    """
    HTMX endpoint for order details
    Returns order detail HTML fragment
    """
    order = get_object_or_404(
        Order.objects.prefetch_related('items__part'),
        id=order_id,
        user=request.user
    )

    context = {
        'order': order,
    }

    return render(request, 'parts/htmx/order_detail.html', context)


# =====================
# FILTER HELPERS
# =====================

@require_http_methods(["GET"])
def get_models_by_make_htmx(request, make_id):
    """
    HTMX endpoint to get models for a make
    Returns select options HTML fragment
    """
    models = Model.objects.filter(make_id=make_id).order_by('name')

    context = {
        'models': models,
    }

    return render(request, 'parts/htmx/model_options.html', context)


@require_http_methods(["GET"])
def get_categories_htmx(request):
    """
    HTMX endpoint to get all categories
    Returns categories HTML fragment
    """
    categories = PartCategory.objects.all().order_by('name')

    context = {
        'categories': categories,
    }

    return render(request, 'parts/htmx/category_list.html', context)
