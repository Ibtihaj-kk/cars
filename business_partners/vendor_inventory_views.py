"""
Vendor Inventory Management Views
Comprehensive inventory CRUD operations for vendor portal
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, F, Sum, Count, Case, When, Value
from django.db import transaction
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.utils import timezone
from django.db.models import Exists, OuterRef
from datetime import datetime, timedelta
import csv
import io

from parts.models import Part, Inventory, InventoryTransaction, OrderItem, Brand, Category
from business_partners.models import VendorProfile, BusinessPartner
from business_partners.permissions import get_vendor_profile, vendor_required
from parts.forms import InventoryForm, PartForm
from .forms import VendorPartForm
from .catalog_models import CatalogItem


@login_required
@vendor_required
def vendor_inventory_overview(request):
    """
    Overview page for vendor inventory features.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    business_partner = vendor_profile.business_partner
    
    # Calculate statistics
    # 1. Order Amount (Total Revenue from confirmed/delivered orders)
    order_items = OrderItem.objects.filter(
        part__vendor=business_partner,
        order__status__in=['confirmed', 'processing', 'shipped', 'delivered']
    )
    
    total_revenue = order_items.aggregate(
        total=Sum(F('price') * F('quantity'))
    )['total'] or 0
    
    # 2. Order Units (Total units sold)
    total_units = order_items.aggregate(total=Sum('quantity'))['total'] or 0
    
    # 3. Monthly Sales (Revenue last 30 days)
    last_30_days = timezone.now() - timedelta(days=30)
    monthly_sales = order_items.filter(
        order__created_at__gte=last_30_days
    ).aggregate(
        total=Sum(F('price') * F('quantity'))
    )['total'] or 0
    
    # 4. Inventory Value (Current stock value)
    inventory_value = Part.objects.filter(
        vendor=business_partner
    ).aggregate(
        total=Sum(F('price') * F('quantity'))
    )['total'] or 0
    
    context = {
        'vendor_profile': vendor_profile,
        'business_partner': business_partner,
        'stats': {
            'total_revenue': total_revenue,
            'total_units': total_units,
            'monthly_sales': monthly_sales,
            'inventory_value': inventory_value,
        }
    }
    return render(request, 'vendors/inventory_feature.html', context)


@login_required
@vendor_required
def vendor_inventory_list(request):
    """
    Main vendor inventory dashboard with comprehensive filtering and analytics.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    business_partner = vendor_profile.business_partner
    
    # Get all vendor parts with inventory data
    parts_queryset = Part.objects.filter(vendor=business_partner).select_related('inventory', 'category', 'brand')
    
    # Apply filters
    search_query = request.GET.get('search', '')
    if search_query:
        parts_queryset = parts_queryset.filter(
            Q(parts_number__icontains=search_query) |
            Q(material_description__icontains=search_query) |
            Q(manufacturer_part_number__icontains=search_query) |
            Q(manufacturer_oem_number__icontains=search_query)
        )
    
    # Stock status filter
    stock_status = request.GET.get('stock_status', '')
    if stock_status:
        if stock_status == 'in_stock':
            parts_queryset = parts_queryset.filter(quantity__gt=10)
        elif stock_status == 'low_stock':
            parts_queryset = parts_queryset.filter(quantity__gt=0, quantity__lte=10)
        elif stock_status == 'out_of_stock':
            parts_queryset = parts_queryset.filter(quantity=0)
        elif stock_status == 'below_safety':
            parts_queryset = parts_queryset.filter(
                safety_stock__isnull=False,
                quantity__lt=F('safety_stock')
            )
        elif stock_status == 'dead_stock':
            one_month_ago = timezone.now() - timedelta(days=30)
            recent_sale_exists = InventoryTransaction.objects.filter(
                inventory__part_id=OuterRef('pk'),
                transaction_type='sale',
                timestamp__gte=one_month_ago,
            )
            parts_queryset = parts_queryset.filter(quantity__gt=0).annotate(
                has_recent_sale=Exists(recent_sale_exists)
            ).filter(has_recent_sale=False)
    
    # Category filter
    category_filter = request.GET.get('category', '')
    if category_filter:
        parts_queryset = parts_queryset.filter(category_id=category_filter)
    
    # Brand filter
    brand_filter = request.GET.get('brand', '')
    if brand_filter:
        parts_queryset = parts_queryset.filter(brand_id=brand_filter)
    
    # Price range filter
    price_min = request.GET.get('price_min', '')
    price_max = request.GET.get('price_max', '')
    if price_min:
        parts_queryset = parts_queryset.filter(price__gte=price_min)
    if price_max:
        parts_queryset = parts_queryset.filter(price__lte=price_max)
    
    # Sorting
    sort_by = request.GET.get('sort', '-created_at')
    valid_sort_fields = [
        'parts_number', '-parts_number',
        'material_description', '-material_description',
        'price', '-price',
        'quantity', '-quantity',
        'created_at', '-created_at',
        'updated_at', '-updated_at'
    ]
    if sort_by in valid_sort_fields:
        parts_queryset = parts_queryset.order_by(sort_by)
    else:
        sort_by = '-created_at'
        parts_queryset = parts_queryset.order_by(sort_by)
    
    per_page = 25
    per_page_raw = request.GET.get('per_page')
    if per_page_raw:
        try:
            per_page_candidate = int(per_page_raw)
        except (TypeError, ValueError):
            per_page_candidate = None

        if per_page_candidate in {10, 25, 50, 100}:
            per_page = per_page_candidate
    
    try:
        limit = int(request.GET.get('limit') or per_page)
    except (TypeError, ValueError):
        limit = per_page
    if limit not in {10, 25, 50, 100}:
        limit = per_page
    per_page = limit

    try:
        offset = int(request.GET.get('offset') or 0)
    except (TypeError, ValueError):
        offset = 0
    if offset < 0:
        offset = 0
    
    # Calculate inventory statistics
    total_parts = parts_queryset.count()
    total_value = parts_queryset.aggregate(
        total=Sum(F('price') * F('quantity'))
    )['total'] or 0
    
    # Stock status breakdown
    stock_stats = parts_queryset.aggregate(
        in_stock=Count(Case(When(quantity__gt=10, then=1))),
        low_stock=Count(Case(When(quantity__gt=0, quantity__lte=10, then=1))),
        out_of_stock=Count(Case(When(quantity=0, then=1))),
        below_safety=Count(Case(
            When(safety_stock__isnull=False, quantity__lt=F('safety_stock'), then=1)
        ))
    )
    
    one_month_ago = timezone.now() - timedelta(days=30)
    recent_sale_exists = InventoryTransaction.objects.filter(
        inventory__part_id=OuterRef('pk'),
        transaction_type='sale',
        timestamp__gte=one_month_ago,
    )
    dead_stock_count = parts_queryset.filter(quantity__gt=0).annotate(
        has_recent_sale=Exists(recent_sale_exists)
    ).filter(has_recent_sale=False).count()
    stock_stats['dead_stock'] = dead_stock_count
    
    # Get categories and brands for filters
    categories = parts_queryset.values('category__id', 'category__name').distinct().order_by('category__name')
    brands = parts_queryset.values('brand__id', 'brand__name').distinct().order_by('brand__name')

    if offset >= total_parts and total_parts > 0:
        offset = max(((total_parts - 1) // per_page) * per_page, 0)

    parts = list(parts_queryset[offset:offset + per_page])
    start_index = 0
    end_index = 0
    if total_parts > 0:
        start_index = offset + 1
        end_index = min(offset + len(parts), total_parts)

    total_pages = 1
    if per_page > 0:
        total_pages = max((total_parts + per_page - 1) // per_page, 1)
    current_page = (offset // per_page) + 1 if per_page > 0 else 1
    has_previous = offset > 0
    has_next = (offset + per_page) < total_parts
    prev_offset = max(offset - per_page, 0)
    next_offset = offset + per_page

    preserved_params = request.GET.copy()
    preserved_params.pop('offset', None)
    preserved_params.pop('page', None)
    preserved_params['per_page'] = str(per_page)
    preserved_params['limit'] = str(per_page)
    base_querystring = preserved_params.urlencode()
    
    context = {
        'vendor_profile': vendor_profile,
        'business_partner': business_partner,
        'parts': parts,
        'total_parts': total_parts,
        'total_value': total_value,
        'stock_stats': stock_stats,
        'incoming_stock': 0,  # Placeholder for incoming stock
        'categories': categories,
        'brands': brands,
        'search_query': search_query,
        'stock_status': stock_status,
        'category_filter': category_filter,
        'brand_filter': brand_filter,
        'price_min': price_min,
        'price_max': price_max,
        'sort_by': sort_by,
        'per_page': per_page,
        'offset': offset,
        'limit': per_page,
        'start_index': start_index,
        'end_index': end_index,
        'current_page': current_page,
        'total_pages': total_pages,
        'has_previous': has_previous,
        'has_next': has_next,
        'prev_offset': prev_offset,
        'next_offset': next_offset,
        'base_querystring': base_querystring,
    }
    
    # Check if this is an HTMX request
    if request.headers.get('HX-Request'):
        return render(request, 'vendors/inventory_management_table.html', context)
    
    return render(request, 'vendors/inventory_management.html', context)


@login_required
@vendor_required
def vendor_inventory_detail(request, part_id):
    """
    Detailed view of a specific part's inventory with transaction history.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    business_partner = vendor_profile.business_partner
    
    # Get the part and ensure it belongs to this vendor
    part = get_object_or_404(Part, id=part_id, vendor=business_partner)
    
    # Get or create inventory record
    inventory, created = Inventory.objects.get_or_create(
        part=part,
        defaults={
            'stock': part.quantity,
            'reorder_level': 10,
            'last_restock_date': timezone.now() if part.quantity > 0 else None,
        }
    )
    
    # Get recent inventory transactions
    recent_transactions = InventoryTransaction.objects.filter(
        inventory=inventory
    ).select_related('order', 'created_by').order_by('-timestamp')[:50]
    
    # Calculate inventory metrics
    total_sold = InventoryTransaction.objects.filter(
        inventory=inventory,
        transaction_type='sale'
    ).aggregate(total=Sum('quantity_change'))['total'] or 0
    
    total_restocked = InventoryTransaction.objects.filter(
        inventory=inventory,
        transaction_type='restock'
    ).aggregate(total=Sum('quantity_change'))['total'] or 0
    
    # Get monthly transaction summary for the last 6 months
    six_months_ago = timezone.now() - timedelta(days=180)
    monthly_summary = InventoryTransaction.objects.filter(
        inventory=inventory,
        timestamp__gte=six_months_ago
    ).extra(
        select={'month': "TO_CHAR(timestamp, 'YYYY-MM')"}
    ).values('month', 'transaction_type').annotate(
        total_quantity=Sum('quantity_change'),
        transaction_count=Count('id')
    ).order_by('month', 'transaction_type')
    
    context = {
        'vendor_profile': vendor_profile,
        'business_partner': business_partner,
        'part': part,
        'inventory': inventory,
        'recent_transactions': recent_transactions,
        'total_sold': abs(total_sold),  # Make positive for display
        'total_restocked': total_restocked,
        'monthly_summary': monthly_summary,
        'created': created,
    }
    
    return render(request, 'business_partners/vendor_inventory_detail.html', context)


@login_required
@vendor_required
def vendor_inventory_update(request, part_id):
    """
    Update inventory levels for a specific part.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    business_partner = vendor_profile.business_partner
    
    # Get the part and ensure it belongs to this vendor
    part = get_object_or_404(Part, id=part_id, vendor=business_partner)
    
    # Get or create inventory record
    inventory, created = Inventory.objects.get_or_create(
        part=part,
        defaults={
            'stock': part.quantity,
            'reorder_level': 10,
            'last_restock_date': timezone.now() if part.quantity > 0 else None,
        }
    )
    
    if request.method == 'POST':
        form = InventoryForm(request.POST, instance=inventory)
        if form.is_valid():
            # Track the change
            old_stock = inventory.stock
            new_stock = form.cleaned_data['stock']
            
            # Save the inventory update
            inventory = form.save(commit=False)
            
            # Update the part quantity to match inventory
            if old_stock != new_stock:
                part.quantity = new_stock
                part.save()
                
                # Create inventory transaction record
                if old_stock != new_stock:
                    InventoryTransaction.objects.create(
                        inventory=inventory,
                        transaction_type='adjustment',
                        quantity_change=new_stock - old_stock,
                        previous_quantity=old_stock,
                        new_quantity=new_stock,
                        created_by=request.user,
                        notes=f"Manual inventory adjustment by {request.user.email}"
                    )
            
            inventory.save()
            
            messages.success(request, f'Inventory updated successfully for {part.material_description}.')
            return redirect('business_partners:vendor_inventory_detail', part_id=part.id)
    else:
        form = InventoryForm(instance=inventory)
    
    context = {
        'vendor_profile': vendor_profile,
        'business_partner': business_partner,
        'part': part,
        'inventory': inventory,
        'form': form,
        'created': created,
    }
    
    return render(request, 'business_partners/vendor_inventory_update.html', context)


@login_required
@vendor_required
def vendor_inventory_bulk_update(request):
    """
    Bulk update inventory levels for multiple parts.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    business_partner = vendor_profile.business_partner
    
    if request.method == 'POST':
        # Get the selected parts and new quantities
        part_ids = request.POST.getlist('part_ids')
        quantities = request.POST.getlist('quantities')
        
        if not part_ids or not quantities:
            messages.error(request, 'No parts selected for update.')
            return redirect('business_partners:vendor_inventory_list')
        
        updated_count = 0
        error_count = 0
        
        with transaction.atomic():
            for part_id, new_quantity in zip(part_ids, quantities):
                try:
                    part = Part.objects.get(id=part_id, vendor=business_partner)
                    new_quantity = int(new_quantity)
                    
                    if new_quantity < 0:
                        messages.warning(request, f'Invalid quantity for {part.material_description}.')
                        error_count += 1
                        continue
                    
                    # Get or create inventory record
                    inventory, created = Inventory.objects.get_or_create(
                        part=part,
                        defaults={
                            'stock': part.quantity,
                            'reorder_level': 10,
                        }
                    )
                    
                    # Track the change
                    old_stock = inventory.stock
                    
                    # Update both part quantity and inventory stock
                    if old_stock != new_quantity:
                        part.quantity = new_quantity
                        part.save()
                        
                        inventory.stock = new_quantity
                        if new_quantity > old_stock:
                            inventory.last_restock_date = timezone.now()
                        inventory.save()
                        
                        # Create inventory transaction record
                        InventoryTransaction.objects.create(
                            inventory=inventory,
                            transaction_type='adjustment',
                            quantity_change=new_quantity - old_stock,
                            previous_quantity=old_stock,
                            new_quantity=new_quantity,
                            created_by=request.user,
                            notes=f"Bulk inventory update by {request.user.email}"
                        )
                    
                    updated_count += 1
                    
                except (Part.DoesNotExist, ValueError) as e:
                    messages.warning(request, f'Error updating part {part_id}: {str(e)}')
                    error_count += 1
        
        if updated_count > 0:
            messages.success(request, f'Successfully updated {updated_count} parts.')
        
        if error_count > 0:
            messages.warning(request, f'{error_count} parts could not be updated.')
        
        return redirect('business_partners:vendor_inventory_list')
    
    # If not POST, redirect to list view
    return redirect('business_partners:vendor_inventory_list')


@login_required
@vendor_required
def vendor_inventory_adjustment(request, part_id):
    """
    Quick inventory adjustment (add/remove stock) with reason tracking.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    business_partner = vendor_profile.business_partner
    
    # Get the part and ensure it belongs to this vendor
    part = get_object_or_404(Part, id=part_id, vendor=business_partner)
    
    # Get or create inventory record
    inventory, created = Inventory.objects.get_or_create(
        part=part,
        defaults={
            'stock': part.quantity,
            'reorder_level': 10,
        }
    )
    
    if request.method == 'POST':
        adjustment_type = request.POST.get('adjustment_type')
        quantity = request.POST.get('quantity')
        reason = request.POST.get('reason', '')
        
        if not adjustment_type or not quantity:
            messages.error(request, 'Please provide all required fields.')
            return redirect('business_partners:vendor_inventory_detail', part_id=part.id)
        
        try:
            quantity = int(quantity)
            if quantity <= 0:
                messages.error(request, 'Quantity must be positive.')
                return redirect('business_partners:vendor_inventory_detail', part_id=part.id)
            
            old_stock = inventory.stock
            
            if adjustment_type == 'add':
                new_stock = old_stock + quantity
                transaction_type = 'restock'
            elif adjustment_type == 'remove':
                if quantity > old_stock:
                    messages.error(request, 'Cannot remove more stock than available.')
                    return redirect('business_partners:vendor_inventory_detail', part_id=part.id)
                new_stock = old_stock - quantity
                transaction_type = 'adjustment'
            else:
                messages.error(request, 'Invalid adjustment type.')
                return redirect('business_partners:vendor_inventory_detail', part_id=part.id)
            
            # Update both part quantity and inventory stock
            part.quantity = new_stock
            part.save()
            
            inventory.stock = new_stock
            if adjustment_type == 'add':
                inventory.last_restock_date = timezone.now()
            inventory.save()
            
            # Create inventory transaction record
            InventoryTransaction.objects.create(
                inventory=inventory,
                transaction_type=transaction_type,
                quantity_change=quantity if adjustment_type == 'add' else -quantity,
                previous_quantity=old_stock,
                new_quantity=new_stock,
                created_by=request.user,
                notes=f"Manual adjustment: {reason}"
            )
            
            messages.success(request, f'Inventory adjusted successfully. New stock level: {new_stock}')
            
        except ValueError:
            messages.error(request, 'Invalid quantity provided.')
        
        # Check for next parameter to redirect back to list if needed
        next_url = request.POST.get('next')
        if next_url:
            return redirect(next_url)
            
        return redirect('business_partners:vendor_inventory_detail', part_id=part.id)
    
    # If not POST, redirect to detail view
    return redirect('business_partners:vendor_inventory_detail', part_id=part.id)


@login_required
@vendor_required
def vendor_inventory_export(request):
    """
    Export vendor inventory data to CSV or Excel format.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    business_partner = vendor_profile.business_partner
    
    # Get filtered data based on request parameters
    parts_queryset = Part.objects.filter(vendor=business_partner).select_related('inventory', 'category', 'brand')
    
    # Apply same filters as list view
    search_query = request.GET.get('search', '')
    if search_query:
        parts_queryset = parts_queryset.filter(
            Q(parts_number__icontains=search_query) |
            Q(material_description__icontains=search_query)
        )
    
    stock_status = request.GET.get('stock_status', '')
    if stock_status:
        if stock_status == 'in_stock':
            parts_queryset = parts_queryset.filter(quantity__gt=10)
        elif stock_status == 'low_stock':
            parts_queryset = parts_queryset.filter(quantity__gt=0, quantity__lte=10)
        elif stock_status == 'out_of_stock':
            parts_queryset = parts_queryset.filter(quantity=0)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="inventory_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'Parts Number', 'Description', 'Category', 'Brand', 
        'Current Stock', 'Reorder Level', 'Safety Stock',
        'Price', 'Total Value', 'Stock Status', 'Last Restock Date'
    ])
    
    # Write data rows
    for part in parts_queryset:
        inventory = getattr(part, 'inventory', None)
        stock_status = 'In Stock'
        if part.quantity == 0:
            stock_status = 'Out of Stock'
        elif part.quantity <= 10:
            stock_status = 'Low Stock'
        elif part.safety_stock and part.quantity < part.safety_stock:
            stock_status = 'Below Safety'
        
        writer.writerow([
            part.parts_number,
            part.material_description,
            part.category.name if part.category else '',
            part.brand.name if part.brand else '',
            part.quantity,
            inventory.reorder_level if inventory else 10,
            part.safety_stock or '',
            part.price or 0,
            (part.price or 0) * part.quantity,
            stock_status,
            inventory.last_restock_date.strftime('%Y-%m-%d') if inventory and inventory.last_restock_date else ''
        ])
    
    return response


@login_required
@vendor_required
def vendor_inventory_api(request, part_id):
    """
    API endpoint for quick inventory updates (AJAX).
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        return JsonResponse({'error': 'Vendor access required'}, status=403)
    
    business_partner = vendor_profile.business_partner
    
    # Get the part and ensure it belongs to this vendor
    try:
        part = Part.objects.get(id=part_id, vendor=business_partner)
    except Part.DoesNotExist:
        return JsonResponse({'error': 'Part not found'}, status=404)
    
    if request.method == 'POST':
        try:
            # Get or create inventory record
            inventory, created = Inventory.objects.get_or_create(
                part=part,
                defaults={
                    'stock': part.quantity,
                    'reorder_level': 10,
                }
            )
            
            # Get new quantity from request
            new_quantity = int(request.POST.get('quantity', part.quantity))
            
            if new_quantity < 0:
                return JsonResponse({'error': 'Quantity cannot be negative'}, status=400)
            
            old_stock = inventory.stock
            
            # Update both part quantity and inventory stock
            if old_stock != new_quantity:
                part.quantity = new_quantity
                part.save()
                
                inventory.stock = new_quantity
                if new_quantity > old_stock:
                    inventory.last_restock_date = timezone.now()
                inventory.save()
                
                # Create inventory transaction record
                InventoryTransaction.objects.create(
                    inventory=inventory,
                    transaction_type='adjustment',
                    quantity_change=new_quantity - old_stock,
                    previous_quantity=old_stock,
                    new_quantity=new_quantity,
                    created_by=request.user,
                    notes="Quick update via API"
                )
            
            return JsonResponse({
                'success': True,
                'new_quantity': new_quantity,
                'stock_status': 'In Stock' if new_quantity > 10 else 'Low Stock' if new_quantity > 0 else 'Out of Stock'
            })
            
        except ValueError:
            return JsonResponse({'error': 'Invalid quantity'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    # GET request - return current inventory data
    inventory = getattr(part, 'inventory', None)
    return JsonResponse({
        'part_id': part.id,
        'parts_number': part.parts_number,
        'description': part.material_description,
        'current_quantity': part.quantity,
        'reorder_level': inventory.reorder_level if inventory else 10,
        'stock_status': 'In Stock' if part.quantity > 10 else 'Low Stock' if part.quantity > 0 else 'Out of Stock'
    })


@login_required
@vendor_required
def vendor_inventory_alerts_json(request):
    """
    API endpoint for inventory alerts (AJAX).
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        return JsonResponse({'error': 'Vendor access required'}, status=403)
    
    business_partner = vendor_profile.business_partner
    
    # Get parts with stock issues
    out_of_stock = Part.objects.filter(vendor=business_partner, quantity=0, is_active=True).count()
    low_stock = Part.objects.filter(
        vendor=business_partner, 
        quantity__gt=0, 
        quantity__lte=10, 
        is_active=True
    ).count()
    
    below_safety_stock = Part.objects.filter(
        vendor=business_partner,
        safety_stock__isnull=False,
        quantity__lt=F('safety_stock'),
        is_active=True
    ).count()
    
    total_alerts = out_of_stock + low_stock + below_safety_stock
    return JsonResponse({
        'total_alerts': total_alerts,
        'out_of_stock': out_of_stock,
        'low_stock': low_stock,
        'below_safety_stock': below_safety_stock,
        'has_alerts': total_alerts > 0
    })


@login_required
@vendor_required
def add_part(request):
    """
    View for vendors to add new parts with draft/publish functionality.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    business_partner = vendor_profile.business_partner
    vendor_catalog_items = list(
        CatalogItem.objects.filter(vendor=business_partner)
        .order_by('part_number')
        .values('part_number', 'description', 'make', 'model', 'year', 'trim', 'engine')
    )
    
    if request.method == 'POST':
        post_data = request.POST.copy()
        brand_text = (post_data.get('brand_text') or '').strip()
        if brand_text and not post_data.get('brand'):
            brand_obj, _ = Brand.objects.get_or_create(name=brand_text)
            post_data['brand'] = str(brand_obj.pk)

        material_description = (post_data.get('material_description') or '').strip()
        parts_number = (post_data.get('parts_number') or '').strip()
        if not material_description and parts_number:
            catalog_item = CatalogItem.objects.filter(vendor=business_partner, part_number=parts_number).first()
            if catalog_item and catalog_item.description:
                post_data['material_description'] = catalog_item.description

        form = VendorPartForm(post_data, request.FILES, vendor=business_partner)
        if form.is_valid():
            part = form.save(commit=False)
            part.vendor = business_partner
            part.save()
            
            # Create inventory record for the new part
            # Use inventory_threshold from form if available, else default to 10
            reorder_level = form.cleaned_data.get('inventory_threshold') or 10
            
            Inventory.objects.create(
                part=part,
                stock=part.quantity,
                reorder_level=reorder_level,
                last_restock_date=timezone.now() if part.quantity > 0 else None
            )
            
            if part.status == 'draft':
                messages.success(request, f'Part "{part.material_description}" saved as draft successfully.')
                return redirect('business_partners:vendor_inventory_list')
            else:
                messages.success(request, f'Part "{part.material_description}" published successfully.')
                return redirect('business_partners:vendor_inventory_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = VendorPartForm(vendor=business_partner)
    
    return render(request, 'vendors/add_part.html', {
        'form': form,
        'vendor_profile': vendor_profile,
        'vendor_catalog_items': vendor_catalog_items,
    })


@login_required
@vendor_required
def add_part_htmx(request):
    """
    HTMX-compatible API endpoint for adding new parts.
    Returns HTML partial with validation errors or triggers redirect on success.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        return HttpResponse("You do not have vendor access.", status=403)
    
    business_partner = vendor_profile.business_partner
    vendor_catalog_items = list(
        CatalogItem.objects.filter(vendor=business_partner)
        .order_by('part_number')
        .values('part_number', 'description', 'make', 'model', 'year', 'trim', 'engine')
    )
    
    if request.method == 'POST':
        post_data = request.POST.copy()
        brand_text = (post_data.get('brand_text') or '').strip()
        if brand_text and not post_data.get('brand'):
            brand_obj, _ = Brand.objects.get_or_create(name=brand_text)
            post_data['brand'] = str(brand_obj.pk)

        material_description = (post_data.get('material_description') or '').strip()
        parts_number = (post_data.get('parts_number') or '').strip()
        if not material_description and parts_number:
            catalog_item = CatalogItem.objects.filter(vendor=business_partner, part_number=parts_number).first()
            if catalog_item and catalog_item.description:
                post_data['material_description'] = catalog_item.description

        form = VendorPartForm(post_data, request.FILES, vendor=business_partner)
        if form.is_valid():
            part = form.save(commit=False)
            part.vendor = business_partner
            part.save()
            
            # Create inventory record for the new part
            reorder_level = form.cleaned_data.get('inventory_threshold') or 10
            
            Inventory.objects.create(
                part=part,
                stock=part.quantity,
                reorder_level=reorder_level,
                last_restock_date=timezone.now() if part.quantity > 0 else None
            )
            
            # Success message
            msg = f'Part "{part.material_description}" saved successfully.'
            messages.success(request, msg)
            
            # Return empty response with HX-Redirect header to redirect client
            response = HttpResponse()
            response['HX-Redirect'] = reverse('business_partners:vendor_inventory_list')
            return response
        else:
            # Return form with errors rendered as HTML partial
            return render(request, 'vendors/partials/part_form.html', {
                'form': form,
                'vendor_profile': vendor_profile,
                'vendor_catalog_items': vendor_catalog_items,
            })
    
    return HttpResponse("Invalid request method.", status=405)


@login_required
@vendor_required
@require_http_methods(["POST"])
def vendor_part_status_update(request, part_id):
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    business_partner = vendor_profile.business_partner
    new_status = request.POST.get('status')
    
    if new_status not in ['draft', 'published', 'archived']:
        messages.error(request, 'Invalid status.')
        return redirect(request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('business_partners:vendor_inventory_list'))
    
    part = get_object_or_404(Part, id=part_id, vendor=business_partner)
    
    if part.status != new_status:
        part.status = new_status
        part.save(update_fields=['status', 'updated_at'])
    
    messages.success(request, f'Part "{part.material_description}" status updated to {new_status}.')
    return redirect(request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('business_partners:vendor_inventory_list'))


@login_required
@vendor_required
@require_http_methods(["POST"])
def vendor_parts_bulk_status_update(request):
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    business_partner = vendor_profile.business_partner
    new_status = request.POST.get('status')
    part_ids = request.POST.getlist('part_ids')
    
    if new_status not in ['draft', 'published', 'archived']:
        messages.error(request, 'Invalid status.')
        return redirect(request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('business_partners:vendor_inventory_list'))
    
    if not part_ids:
        messages.error(request, 'No parts selected.')
        return redirect(request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('business_partners:vendor_inventory_list'))
    
    parts = Part.objects.filter(id__in=part_ids, vendor=business_partner)
    updated_count = parts.update(status=new_status)
    
    messages.success(request, f'Updated status to {new_status} for {updated_count} parts.')
    return redirect(request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('business_partners:vendor_inventory_list'))


@login_required
@vendor_required
@require_http_methods(["DELETE"])
def vendor_inventory_delete_htmx(request, part_id):
    """
    HTMX endpoint to delete a part from inventory/catalog.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        return HttpResponse("Unauthorized", status=403)
    
    business_partner = vendor_profile.business_partner
    
    # Get the part and ensure it belongs to this vendor
    part = get_object_or_404(Part, id=part_id, vendor=business_partner)
    
    # Delete the part
    part.delete()
    
    # Return empty response to remove the row
    return HttpResponse("")


@login_required
@vendor_required
def vendor_catalog_management(request):
    """
    Catalog management view for vendors.
    Similar to inventory list but uses the inventory.html template.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    business_partner = vendor_profile.business_partner
    
    catalog_queryset = CatalogItem.objects.filter(vendor=business_partner).select_related('category').prefetch_related('images')
    
    # Apply filters
    search_query = request.GET.get('search', '')
    if search_query:
        catalog_queryset = catalog_queryset.filter(
            Q(part_number__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(make__icontains=search_query) |
            Q(model__icontains=search_query) |
            Q(trim__icontains=search_query) |
            Q(engine__icontains=search_query)
        )

    category_filter = request.GET.get('category', '').strip()
    if category_filter:
        try:
            catalog_queryset = catalog_queryset.filter(category_id=int(category_filter))
        except ValueError:
            pass

    make_filter = request.GET.get('make', '').strip()
    if make_filter:
        catalog_queryset = catalog_queryset.filter(make__iexact=make_filter)

    model_filter = request.GET.get('model', '').strip()
    if model_filter:
        catalog_queryset = catalog_queryset.filter(model__iexact=model_filter)

    year_filter = request.GET.get('year', '').strip()
    if year_filter:
        try:
            catalog_queryset = catalog_queryset.filter(year=int(year_filter))
        except ValueError:
            pass

    catalog_queryset = catalog_queryset.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(catalog_queryset, 25)
    page_number = request.GET.get('page')
    catalog_items = paginator.get_page(page_number)

    base_queryset = CatalogItem.objects.filter(vendor=business_partner).select_related('category')
    makes = base_queryset.values_list('make', flat=True).distinct().order_by('make')
    models = (
        base_queryset.filter(make__iexact=make_filter)
        .exclude(model__isnull=True)
        .values_list('model', flat=True).distinct().order_by('model')
        if make_filter
        else base_queryset.exclude(model__isnull=True).values_list('model', flat=True).distinct().order_by('model')
    )
    years = (
        base_queryset.filter(make__iexact=make_filter, model__iexact=model_filter)
        .exclude(year__isnull=True)
        .values_list('year', flat=True).distinct().order_by('-year')
        if make_filter and model_filter
        else base_queryset.exclude(year__isnull=True).values_list('year', flat=True).distinct().order_by('-year')
    )

    total_items = catalog_queryset.count()
    categories = Category.objects.filter(vendor_catalog_items__vendor=business_partner).distinct().order_by('name')
    category_count = base_queryset.exclude(category__isnull=True).values('category').distinct().count()
    make_count = base_queryset.values('make').distinct().count()
    model_count = base_queryset.values('model').distinct().count()
    year_count = base_queryset.exclude(year__isnull=True).values('year').distinct().count()
    
    context = {
        'vendor_profile': vendor_profile,
        'business_partner': business_partner,
        'catalog_items': catalog_items,
        'parts': catalog_items,
        'total_items': total_items,
        'total_parts': total_items,
        'total_skus': total_items,
        'categories': categories,
        'category_count': category_count,
        'make_count': make_count,
        'model_count': model_count,
        'year_count': year_count,
        'makes': makes,
        'models': models,
        'years': years,
        'search_query': search_query,
        'category_filter': category_filter,
        'make_filter': make_filter,
        'model_filter': model_filter,
        'year_filter': year_filter,
    }
    
    return render(request, 'vendors/catalog_management.html', context)
