"""
HTMX Views for Parts Module
Server-side rendered views that return HTML fragments for HTMX
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from django.db.models import Q, Sum
from django.contrib import messages

from .models import Part, PartCategory, Order, OrderItem, Cart, CartItem
# from vehicles.models import Make, Model  # Disabled - vehicles app not in INSTALLED_APPS


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
        stock_quantity__gt=0
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
        stock_quantity__gt=0
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
    payment_method = request.POST.get('payment_method', 'cod')
    
    # Calculate totals
    subtotal = sum(item.part.standard_price * item.quantity for item in cart_items)
    
    # Calculate tax based on item classification
    tax_amount = Decimal('0.00')
    order_items_data = []
    
    for item in cart_items:
        item_tax_rate = Decimal('0.15') # Default
        if hasattr(item.part, 'tax_classification_material'):
            classification = item.part.tax_classification_material
            if classification == 'VAT_5':
                item_tax_rate = Decimal('0.05')
            elif classification in ['ZERO', 'EXEMPT']:
                item_tax_rate = Decimal('0.00')
            elif classification == 'VAT_15':
                item_tax_rate = Decimal('0.15')
        
        item_price = item.part.standard_price
        item_total = item_price * item.quantity
        item_tax = item_total * item_tax_rate
        tax_amount += item_tax
        
        order_items_data.append({
            'part': item.part,
            'quantity': item.quantity,
            'price': item_price,
            'tax_amount': item_tax
        })

    shipping_cost = Decimal('0.00') # Free shipping or calculate
    grand_total = subtotal + tax_amount + shipping_cost

    try:
        with transaction.atomic():
            # Create order
            order = Order.objects.create(
                customer=request.user,
                total_price=grand_total,
                shipping_cost=shipping_cost,
                tax_amount=tax_amount,
                status='pending',
                payment_method=payment_method,
                payment_status='pending'
            )

            # Create order items
            for item_data in order_items_data:
                OrderItem.objects.create(
                    order=order,
                    part=item_data['part'],
                    quantity=item_data['quantity'],
                    price=item_data['price'],
                    tax_amount=item_data['tax_amount']
                )
                
            # Subtract inventory using the model method which handles both Inventory and Part models
            # Phase 1: Reserve inventory
            order.reserve_inventory()
            
            # Phase 2: Finalize inventory
            # For COD/Bank Transfer we finalize immediately as there's no online payment step.
            # For online payments (credit_card, paypal), finalize_inventory will be called 
            # via signals when payment_status changes to 'completed'.
            if payment_method in ['cash_on_delivery', 'bank_transfer']:
                order.finalize_inventory()

            # Record Financial Transactions
            FinanceService.record_order_payment(order, payment_method=payment_method)
            
            # Create Shipping Info
            city = None
            if city_id:
                try:
                    city = City.objects.get(id=city_id)
                except City.DoesNotExist:
                    pass
            
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
