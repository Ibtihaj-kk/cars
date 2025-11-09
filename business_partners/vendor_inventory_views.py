"""
Vendor Inventory Management Views
Comprehensive inventory CRUD operations for vendor portal
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, F, Sum, Count, Case, When, Value
from django.db import transaction
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import datetime, timedelta
import csv
import io

from parts.models import Part, Inventory, InventoryTransaction
from business_partners.models import VendorProfile, BusinessPartner
from business_partners.permissions import get_vendor_profile, vendor_required
from parts.forms import InventoryForm


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
    
    # Pagination
    paginator = Paginator(parts_queryset, 25)
    page_number = request.GET.get('page')
    parts = paginator.get_page(page_number)
    
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
    
    # Get categories and brands for filters
    categories = parts_queryset.values('category__id', 'category__name').distinct().order_by('category__name')
    brands = parts_queryset.values('brand__id', 'brand__name').distinct().order_by('brand__name')
    
    context = {
        'vendor_profile': vendor_profile,
        'business_partner': business_partner,
        'parts': parts,
        'total_parts': total_parts,
        'total_value': total_value,
        'stock_stats': stock_stats,
        'categories': categories,
        'brands': brands,
        'search_query': search_query,
        'stock_status': stock_status,
        'category_filter': category_filter,
        'brand_filter': brand_filter,
        'price_min': price_min,
        'price_max': price_max,
        'sort_by': sort_by,
    }
    
    return render(request, 'business_partners/vendor_inventory_list.html', context)


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