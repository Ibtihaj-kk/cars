"""
Vendor-specific views for part management.
Provides vendors with comprehensive access to manage their parts with all Excel fields.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.core.paginator import Paginator
from finance.models import Wallet, Transaction, EscrowEntry
from admin_panel.payment_models import VendorBalance, VendorPayment, PaymentStatus
from parts.models import Part, Order, OrderItem
from django.db.models import Q, Count, Sum, Avg, F, Case, When, Min, Max
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import json
import csv
import os
import io
from io import StringIO
import openpyxl

from .models import BusinessPartner, VendorProfile, ReorderNotification
from .permissions import get_vendor_profile
from vendor_employees.utils import get_vendor_context


def estimate_record_count(file_obj):
    """
    Estimate number of records in file without loading everything.
    Returns approximate record count for processing mode decision.
    """
    if not hasattr(file_obj, 'name'):
        return 1000  # Default estimate for unknown files
    
    file_name = getattr(file_obj, 'name', '')
    ext = os.path.splitext(file_name)[1].lower()
    
    try:
        if ext == '.csv':
            # Sample first 1000 lines to estimate CSV record count
            file_obj.seek(0)
            sample_lines = 1000
            line_count = 0
            
            # Try to detect encoding
            raw_data = file_obj.read(10000)
            file_obj.seek(0)
            
            # Use simple line counting for estimation
            for _ in file_obj:
                line_count += 1
                if line_count >= sample_lines:
                    break
            
            file_obj.seek(0)
            return max(0, line_count - 1)  # Subtract header row
            
        elif ext in ['.xlsx', '.xls']:
            # Excel row count estimation
            file_obj.seek(0)
            if ext == '.xlsx':
                workbook = openpyxl.load_workbook(file_obj, read_only=True)
            else:
                # For .xls files, we'll use a simpler approach
                workbook = openpyxl.load_workbook(file_obj, read_only=True)
            
            worksheet = workbook.active
            row_count = worksheet.max_row - 1  # Subtract header row
            workbook.close()
            file_obj.seek(0)
            return max(0, row_count)
            
        else:
            # Unknown file type, use file size estimation
            file_size_mb = file_obj.size / (1024 * 1024)
            # Estimate ~1000 records per MB for typical CSV data
            return int(file_size_mb * 1000)
            
    except Exception:
        # Fallback estimation based on file size
        file_size_mb = file_obj.size / (1024 * 1024)
        return int(file_size_mb * 1000)


def should_process_synchronously(file_obj, max_sync_records=10000, max_sync_size_mb=2):
    """
    Determine if file should be processed synchronously based on size and record count.
    """
    file_size_mb = file_obj.size / (1024 * 1024)
    
    # If file is very small, process synchronously
    if file_size_mb <= 0.1:  # Less than 100KB
        return True
    
    # If file exceeds size threshold, process asynchronously
    if file_size_mb > max_sync_size_mb:
        return False
    
    # Estimate record count for medium-sized files
    estimated_records = estimate_record_count(file_obj)
    
    # Process synchronously if within record limit
    return estimated_records <= max_sync_records


def process_import_file_sync(import_file, business_partner, import_status, update_existing, validate_only, chunk_size=5000, user=None):
    """
    Synchronous version of process_import_file for small batches.
    Processes file immediately and returns results.
    """
    from parts.models import BulkUploadLog
    
    # Create upload log for tracking
    upload_log = BulkUploadLog.objects.create(
        user=user or (business_partner.user if hasattr(business_partner, 'user') else None),
        file_name=getattr(import_file, 'name', 'import.csv'),
        file_size=import_file.size,
        status='processing',
        success_message='Processing synchronously'
    )
    
    try:
        # Process using the existing function
        results = process_import_file(
            import_file=import_file,
            business_partner=business_partner,
            import_status=import_status,
            update_existing=update_existing,
            validate_only=validate_only,
            upload_log_id=upload_log.id,
            chunk_size=chunk_size,
            user=user
        )
        
        # Update upload log with results
        upload_log.status = 'completed' if results['error_count'] == 0 else 'partial'
        upload_log.total_records = results['total_rows']
        upload_log.successful_records = results['created_count'] + results['updated_count']
        upload_log.failed_records = results['error_count']
        upload_log.success_message = (
            f'Synchronous processing complete: '
            f'{upload_log.successful_records} processed, '
            f'{upload_log.failed_records} errors'
        )
        upload_log.completed_at = timezone.now()
        upload_log.save()
        
        return results
        
    except Exception as e:
        # Handle any processing errors
        upload_log.status = 'failed'
        upload_log.success_message = f'Synchronous processing failed: {str(e)}'
        upload_log.completed_at = timezone.now()
        upload_log.save()
        
        # Re-raise the exception for proper error handling
        raise
from admin_panel.payment_models import VendorBalance, VendorPayment, PaymentStatus, PaymentBatch, CommissionRule
from .forms import (
    VendorPartForm, 
    VendorPartSearchForm, 
    VendorPartBulkUpdateForm,
    VendorPartBulkImportForm,
    VendorPartExportForm
)
from parts.models import Part, Category, Brand
from .permissions import (
    vendor_required, 
    vendor_part_owner_required, 
    get_vendor_profile,
    user_has_vendor_access
)


def get_vendor_profile_legacy(user):
    """Legacy function - use get_vendor_profile from permissions instead"""
    return get_vendor_profile(user)


@vendor_required
@login_required
def vendor_dashboard(request):
    """
    Main vendor dashboard with overview of parts, orders, and analytics.
    """
    business_partner = get_vendor_context(request.user)
    
    # Check if vendor context exists (master or employee)
    if not business_partner:
        messages.error(request, 'Vendor access not found. Please contact support.')
        return redirect('business_partners:vendor_registration_start')
    
    # Get vendor profile for approval status check
    # Vendor masters have it directly, employees have it via business_partner
    vendor_profile = getattr(business_partner, 'vendor_profile', None)
    
    # Get parts statistics
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

    total_parts = parts_queryset.count()
    active_parts = parts_queryset.filter(is_active=True).count()
    featured_parts = parts_queryset.filter(is_featured=True).count()
    out_of_stock = parts_queryset.filter(quantity=0, is_active=True).count()
    low_stock = parts_queryset.filter(quantity__gt=0, quantity__lte=10, is_active=True).count()
    
    # Enhanced inventory statistics
    below_safety_stock = parts_queryset.filter(
        safety_stock__isnull=False,
        quantity__lt=F('safety_stock'),
        is_active=True
    ).count()
    
    # Calculate reorder recommendations
    needs_reorder = parts_queryset.filter(
        Q(quantity=0) |  # Out of stock
        Q(quantity__gt=0, quantity__lte=10) |  # Low stock
        Q(safety_stock__isnull=False, quantity__lt=F('safety_stock')),  # Below safety stock
        is_active=True
    ).count()
    
    # Get recent parts
    recent_parts = parts_queryset.order_by('-created_at')[:5]
    
    # Get top categories
    top_categories = (
        parts_queryset
        .values('category__name')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )
    
    # Calculate total inventory value (corrected calculation)
    total_value = parts_queryset.aggregate(
        total=Sum(F('standard_price') * F('quantity'))
    )['total'] or 0
    
    # Get average price
    avg_price = parts_queryset.aggregate(avg=Avg('standard_price'))['avg'] or 0
    
    # Get inventory health metrics
    total_active_parts = parts_queryset.filter(is_active=True).count()
    healthy_stock_count = total_active_parts - out_of_stock - low_stock - below_safety_stock
    
    # Calculate inventory health percentage
    inventory_health = (healthy_stock_count / total_active_parts * 100) if total_active_parts > 0 else 100
    
    # Determine health status text
    if inventory_health >= 95:
        health_status = 'Excellent'
    elif inventory_health >= 85:
        health_status = 'Good'
    elif inventory_health >= 70:
        health_status = 'Fair'
    else:
        health_status = 'Poor'
    
    # Get recent reorder notifications
    notifications_queryset = ReorderNotification.objects.filter(vendor=business_partner)
    
    # Apply location filtering to notifications if user is a vendor employee
    if vendor_employee and vendor_employee.is_active:
        employee_locations = vendor_employee.locations.filter(is_active=True).values_list('name', flat=True)
        if employee_locations:
            notifications_queryset = notifications_queryset.filter(
                Q(part__plant__in=employee_locations) | 
                Q(part__storage_location__in=employee_locations) | 
                Q(part__warehouse_number__in=employee_locations)
            )
        else:
            notifications_queryset = notifications_queryset.none()

    recent_notifications = notifications_queryset.filter(
        status__in=['pending', 'acknowledged']
    ).select_related('part').order_by('-created_at')[:5]
    
    # Get critical notifications count
    critical_notifications = notifications_queryset.filter(
        priority='critical',
        status__in=['pending', 'acknowledged']
    ).count()
    
    # Get overdue notifications (older than 7 days)
    overdue_notifications = notifications_queryset.filter(
        status='pending',
        created_at__lt=timezone.now() - timedelta(days=7)
    ).count()
    
    # Calculate order and sales statistics
    # Get all orders that contain items from this vendor's parts
    from parts.models import Order, OrderItem
    
    today = timezone.now()
    
    # Get order items for this vendor's parts
    vendor_order_items = OrderItem.objects.filter(
        part__vendor=business_partner,
        order__status__in=['confirmed', 'processing', 'shipped', 'delivered']
    )
    
    # Location-based filtering for vendor employees (Orders and Sales)
    if vendor_employee and vendor_employee.is_active:
        employee_locations = vendor_employee.locations.filter(is_active=True).values_list('name', flat=True)
        if employee_locations:
            vendor_order_items = vendor_order_items.filter(
                Q(part__plant__in=employee_locations) | 
                Q(part__storage_location__in=employee_locations) | 
                Q(part__warehouse_number__in=employee_locations)
            )
        else:
            vendor_order_items = vendor_order_items.none()
    
    # Total orders count
    total_orders = vendor_order_items.values('order').distinct().count()
    
    # Calculate order growth (vs last week)
    last_week = today - timedelta(days=7)
    previous_week = today - timedelta(days=14)
    
    orders_this_week = vendor_order_items.filter(
        order__created_at__gte=last_week
    ).values('order').distinct().count()
    
    orders_last_week = vendor_order_items.filter(
        order__created_at__gte=previous_week,
        order__created_at__lt=last_week
    ).values('order').distinct().count()
    
    if orders_last_week > 0:
        order_growth = ((orders_this_week - orders_last_week) / orders_last_week) * 100
    else:
        order_growth = 100 if orders_this_week > 0 else 0
    
    # Monthly sales calculation (last 30 days)
    last_30_days = timezone.now() - timedelta(days=30)
    previous_30_days = timezone.now() - timedelta(days=60)
    
    monthly_sales_data = vendor_order_items.filter(
        order__created_at__gte=last_30_days
    ).aggregate(
        total_sales=Sum(F('price') * F('quantity'))
    )
    
    prev_monthly_sales_data = vendor_order_items.filter(
        order__created_at__gte=previous_30_days,
        order__created_at__lt=last_30_days
    ).aggregate(
        total_sales=Sum(F('price') * F('quantity'))
    )
    
    monthly_sales = monthly_sales_data['total_sales'] or 0
    prev_monthly_sales = prev_monthly_sales_data['total_sales'] or 0
    
    if prev_monthly_sales > 0:
        sales_growth = ((float(monthly_sales) - float(prev_monthly_sales)) / float(prev_monthly_sales)) * 100
    else:
        sales_growth = 100 if monthly_sales > 0 else 0
    
    # Format monthly sales for display (e.g., 1.2M)
    if monthly_sales >= 1000000:
        monthly_sales_display = f"{monthly_sales / 1000000:.1f}M"
    elif monthly_sales >= 1000:
        monthly_sales_display = f"{monthly_sales / 1000:.0f}K"
    else:
        monthly_sales_display = f"{monthly_sales:.0f}"

    # Calculate Pending Actions (Orders needing attention + Critical notifications)
    pending_orders_count = vendor_order_items.filter(
        order__status__in=['confirmed', 'processing']
    ).values('order').distinct().count()
    
    pending_actions = pending_orders_count + critical_notifications

    # Format Inventory Value
    if total_value >= 1000000:
        total_value_display = f"{total_value / 1000000:.1f}M"
    elif total_value >= 1000:
        total_value_display = f"{total_value / 1000:.0f}K"
    else:
        total_value_display = f"{total_value:.0f}"

    # Revenue Chart Data (Last 6 months)
    revenue_labels = []
    revenue_data = []
    
    for i in range(6):
        month_target = today.month - i
        year_target = today.year
        if month_target <= 0:
            month_target += 12
            year_target -= 1
            
        # Get data for this month
        monthly_revenue = vendor_order_items.filter(
            order__created_at__year=year_target,
            order__created_at__month=month_target
        ).aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0
        
        # Add to lists (prepend because we are going backwards)
        # Create a date object safely
        import datetime as dt
        month_name = dt.date(year_target, month_target, 1).strftime('%b')
        revenue_labels.insert(0, month_name)
        revenue_data.insert(0, float(monthly_revenue))

    # Fulfillment Stats
    delivered_count = vendor_order_items.filter(order__status='delivered').values('order').distinct().count()
    pending_processing_count = vendor_order_items.filter(order__status__in=['confirmed', 'processing']).values('order').distinct().count()
    total_fulfillment = delivered_count + pending_processing_count

    # Customer Stats
    User = get_user_model()
    total_customers = User.objects.filter(
        orders__items__part__vendor=business_partner
    ).distinct().count()

    # Finance Stats for Tiles
    vendor_ct = ContentType.objects.get_for_model(BusinessPartner)
    wallet, _ = Wallet.objects.get_or_create(
        owner_content_type=vendor_ct,
        owner_id=business_partner.id,
        defaults={'currency': vendor_profile.preferred_currency or 'USD'}
    )

    # Tax Payable calculation (from vendor_finance_dashboard)
    tax_payable = Decimal('0.00')
    orders_last_30_days = Order.objects.filter(
        items__part__vendor=business_partner,
        created_at__gte=today - timedelta(days=30)
    ).distinct()
    
    per_order_totals = orders_last_30_days.values('id', 'total_price', 'shipping_cost', 'tax_amount')
    for order_info in per_order_totals:
        vendor_total = OrderItem.objects.filter(
            order_id=order_info['id'], 
            part__vendor=business_partner
        ).aggregate(total=Sum(F('quantity') * F('price')))['total'] or Decimal('0.00')
        
        order_total = order_info['total_price'] or Decimal('0.00')
        if order_total > 0:
            ratio = vendor_total / order_total
            tax_payable += (order_info['tax_amount'] or Decimal('0.00')) * ratio

    # Profile completion percentage
    profile_completion_percentage = vendor_profile.get_profile_completion_percentage()

    # Verification status
    verification_deadline = vendor_profile.get_verification_deadline()
    remaining_time = vendor_profile.get_remaining_verification_time()
    is_verification_expired = vendor_profile.is_verification_expired
    is_email_verified = request.user.is_verified or not request.user.requires_email_verification

    context = {
        'vendor_profile': vendor_profile,
        'business_partner': business_partner,
        'wallet': wallet,
        'tax_payable': tax_payable,
        'verification_deadline': verification_deadline,
        'remaining_time': remaining_time,
        'is_verification_expired': is_verification_expired,
        'is_email_verified': is_email_verified,
        'stats': {
            'total_parts': total_parts,
            'active_parts': active_parts,
            'featured_parts': featured_parts,
            'out_of_stock': out_of_stock,
            'low_stock': low_stock,
            'below_safety_stock': below_safety_stock,
            'needs_reorder': needs_reorder,
            'total_value': total_value,
            'total_value_raw': total_value,
            'total_value_display': total_value_display,
            'avg_price': avg_price,
            'inventory_health': inventory_health,
            'inventory_health_percentage': round(inventory_health, 1),
            'health_status': health_status,
            'healthy_stock_count': healthy_stock_count,
            'critical_notifications': critical_notifications,
            'overdue_notifications': overdue_notifications,
            'total_orders': total_orders,
            'order_growth': round(order_growth, 1),
            'monthly_sales': monthly_sales_display,
            'monthly_sales_raw': monthly_sales,
            'sales_growth': round(sales_growth, 1),
            'pending_actions': pending_actions,
            'revenue_labels': json.dumps(revenue_labels),
            'revenue_data': json.dumps(revenue_data),
            'delivered_count': delivered_count,
            'pending_processing_count': pending_processing_count,
            'total_fulfillment': total_fulfillment,
            'total_customers': total_customers,
            'wallet_balance': wallet.available_balance,
            'liability_balance': wallet.liability_balance,
        },
        'recent_notifications': recent_notifications,
        'recent_parts': recent_parts,
        'top_categories': top_categories,
        'vendor_profile': vendor_profile,
        'is_approved': vendor_profile.is_approved if vendor_profile else False,
        'profile_completion_percentage': profile_completion_percentage,
    }
    
    return render(request, 'vendors/dashboard.html', context)


@vendor_required
@login_required
def vendor_finance_dashboard(request):
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'Vendor profile not found.')
        return redirect('business_partners:vendor_registration_single')

    business_partner = vendor_profile.business_partner

    vendor_ct = ContentType.objects.get_for_model(BusinessPartner)
    wallet, created = Wallet.objects.get_or_create(
        owner_content_type=vendor_ct,
        owner_id=business_partner.id,
        defaults={'currency': vendor_profile.preferred_currency or 'USD'}
    )

    try:
        FinanceService.sync_legacy_vendor_payments(vendor=business_partner, limit=None)
    except Exception:
        pass

    # Get or create legacy vendor balance for backward compatibility
    vendor_balance, created = VendorBalance.objects.get_or_create(
        vendor=business_partner,
        defaults={
            'current_balance': Decimal('0.00'),
            'pending_balance': Decimal('0.00'),
            'total_earned': Decimal('0.00'),
            'total_paid': Decimal('0.00')
        }
    )

    # Recalculate Legacy Balances to prevent double-counting
    order_item_ct = ContentType.objects.get_for_model(OrderItem)
    
    legacy_total_earned = OrderItem.objects.filter(
        part__vendor=business_partner,
        order__status='delivered'
    ).exclude(
        id__in=Transaction.objects.filter(
            reference_content_type=order_item_ct,
            destination_wallet=wallet
        ).values_list('reference_id', flat=True)
    ).aggregate(
        total=Sum(F('price') * F('quantity'))
    )['total'] or Decimal('0.00')

    pending_clearance_amount = OrderItem.objects.filter(
        part__vendor=business_partner,
        order__status__in=['confirmed', 'processing', 'shipped']
    ).exclude(
        id__in=Transaction.objects.filter(
            reference_content_type=order_item_ct,
            destination_wallet=wallet
        ).values_list('reference_id', flat=True)
    ).aggregate(
        total=Sum(F('price') * F('quantity'))
    )['total'] or Decimal('0.00')

    vendor_balance.total_earned = legacy_total_earned
    vendor_balance.pending_balance = pending_clearance_amount
    vendor_balance.update_balance()

    now = timezone.now()
    last_30_days = now - timedelta(days=30)

    # Use Wallet and Transactions for data
    # Combine legacy and unified data for stats
    legacy_cash_received = VendorPayment.objects.filter(
        vendor=business_partner,
        status=PaymentStatus.COMPLETED,
        created_at__gte=last_30_days
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    unified_cash_received = Transaction.objects.filter(
        destination_wallet=wallet,
        created_at__gte=last_30_days,
        transaction_type='PAYMENT'
    ).aggregate(total=Sum('amount_base'))['total'] or Decimal('0.00')

    cash_received = legacy_cash_received + unified_cash_received

    marketplace_commission = Transaction.objects.filter(
        source_wallet=wallet,
        created_at__gte=last_30_days,
        transaction_type='COMMISSION'
    ).aggregate(total=Sum('amount_base'))['total'] or Decimal('0.00')

    # Note: Legacy system didn't track commission separately in VendorPayment, 
    # so we rely on unified Transactions for this metric.

    base_orders = Order.objects.filter(items__part__vendor=business_partner).distinct()

    open_invoices = base_orders.exclude(
        payment_status='completed'
    ).exclude(
        status__in=['cancelled', 'refunded']
    ).count()

    refund_amount = Transaction.objects.filter(
        source_wallet=wallet,
        created_at__gte=last_30_days,
        transaction_type='REFUND'
    ).aggregate(total=Sum('amount_base'))['total'] or Decimal('0.00')

    orders_last_30_days = base_orders.filter(
        Q(status='delivered') | Q(payment_status='completed'),
        created_at__gte=last_30_days,
    )

    tax_payable = Decimal('0.00')
    total_tax_collected = Decimal('0.00')
    shipping_cost = Decimal('0.00')

    # All-time tax collection (only delivered or paid orders)
    total_tax_collected = OrderItem.objects.filter(
        part__vendor=business_partner
    ).filter(
        Q(order__status='delivered') | Q(order__payment_status='completed')
    ).aggregate(total=Sum('tax_amount'))['total'] or Decimal('0.00')

    per_order_totals = orders_last_30_days.values(
        'id',
        'total_price',
        'shipping_cost',
        'tax_amount',
    ).annotate(
        vendor_items_total=Sum(
            'items__quantity',
            filter=Q(items__part__vendor=business_partner)
        ) * F('items__price') # Note: This might need fix if Sum doesn't handle F correctly
    )
    # Correction for the Sum/F logic
    per_order_totals = orders_last_30_days.values('id', 'total_price', 'shipping_cost', 'tax_amount')
    
    for order_info in per_order_totals:
        vendor_total = OrderItem.objects.filter(
            order_id=order_info['id'], 
            part__vendor=business_partner
        ).aggregate(total=Sum(F('quantity') * F('price')))['total'] or Decimal('0.00')
        
        order_total = order_info['total_price'] or Decimal('0.00')
        if order_total > 0:
            ratio = vendor_total / order_total
            tax_payable += (order_info['tax_amount'] or Decimal('0.00')) * ratio
            shipping_cost += (order_info['shipping_cost'] or Decimal('0.00')) * ratio

    # Fetch raw transactions first
    raw_transactions = Transaction.objects.filter(
        Q(source_wallet=wallet) | Q(destination_wallet=wallet)
    ).order_by('-created_at')[:30] # Fetch more to allow for consolidation

    # Group order-related transactions to match the requested UI columns
    consolidated_transactions = []
    processed_items = set()

    item_ct = ContentType.objects.get_for_model(OrderItem)

    for tx in raw_transactions:
        # Check if it's an order-related transaction (PAYMENT or COMMISSION)
        if tx.transaction_type in ['PAYMENT', 'COMMISSION'] and tx.reference_id and tx.reference_content_type == item_ct:
            item_id = tx.reference_id
            if item_id in processed_items:
                continue
            
            # Find both PAYMENT and COMMISSION for this specific item
            item_txs = Transaction.objects.filter(
                reference_content_type=item_ct,
                reference_id=item_id
            )
            
            payment_tx = item_txs.filter(transaction_type='PAYMENT').first()
            commission_tx = item_txs.filter(transaction_type='COMMISSION').first()
            
            # Extract values
            order_num = tx.order_number or "N/A"
            date = tx.created_at
            
            # Settlement Amount (what vendor actually gets)
            amount_settled = payment_tx.amount_base if payment_tx else Decimal('0.00')
            
            # Commission and Tax (usually in COMMISSION transaction metadata)
            commission_val = Decimal('0.00')
            tax_val = Decimal('0.00')
            
            if commission_tx:
                # Platform Revenue = Commission + Tax (if not VAT registered)
                # But we stored detailed breakdown in metadata in services.py
                try:
                    commission_val = Decimal(str(commission_tx.metadata.get('commission', '0.00')))
                    tax_val = Decimal(str(commission_tx.metadata.get('tax', '0.00')))
                except (ValueError, TypeError):
                    pass
            
            # Order Amount = Settled + Commission + Tax? 
            # Actually item.total_price is best if available
            order_amount = Decimal('0.00')
            if payment_tx and payment_tx.reference:
                try:
                    order_amount = payment_tx.reference.total_price
                except:
                    order_amount = amount_settled + commission_val + tax_val
            else:
                order_amount = amount_settled + commission_val + tax_val

            consolidated_transactions.append({
                'id': tx.id,
                'order_number': order_num,
                'date': date,
                'order_amount': order_amount,
                'tax': tax_val,
                'commission': -commission_val, # Negative as shown in image
                'amount_settled': amount_settled,
                'status': tx.status,
                'is_settlement': True
            })
            processed_items.add(item_id)
        else:
            # Other transaction types (Payouts, Refunds, etc.)
            consolidated_transactions.append({
                'id': tx.id,
                'order_number': tx.order_number or 'N/A',
                'date': tx.created_at,
                'order_amount': tx.amount_base if tx.transaction_type == 'REFUND' else Decimal('0.00'),
                'tax': Decimal('0.00'),
                'commission': Decimal('0.00'),
                'amount_settled': tx.amount_base if tx.destination_wallet == wallet else -tx.amount_base,
                'status': tx.status,
                'is_settlement': False,
                'type_display': tx.get_transaction_type_display()
            })

    recent_transactions = consolidated_transactions[:20]

    escrow_entries = wallet.escrow_entries.filter(is_released=False).order_by('release_date')

    pending_processing_count = base_orders.filter(
        status__in=['confirmed', 'processing']
    ).count()

    available_balance = wallet.available_balance or Decimal('0.00')
    escrow_balance = wallet.escrow_balance or Decimal('0.00')
    liability_balance = wallet.liability_balance or Decimal('0.00')

    context = {
        'wallet': wallet,
        'vendor_balance': vendor_balance,
        'available_balance': available_balance,
        'escrow_balance': escrow_balance,
        'liability_balance': liability_balance,
        'escrow_entries': escrow_entries,
        'vendor_profile': vendor_profile,
        'business_partner': business_partner,
        'is_approved': vendor_profile.is_approved,
        'cash_received': cash_received,
        'open_invoices': open_invoices,
        'tax_payable': tax_payable,
        'total_tax_collected': total_tax_collected,
        'shipping_cost': shipping_cost,
        'marketplace_commission': marketplace_commission,
        'refund_amount': refund_amount,
        'recent_transactions': recent_transactions,
        'stats': {
            'pending_processing_count': pending_processing_count,
            'critical_notifications': 0,
        },
    }

    return render(request, 'vendors/finance/dashboard.html', context)


@vendor_required
@login_required
def vendor_settlement_statements(request):
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'Vendor profile not found.')
        return redirect('business_partners:vendor_registration_single')

    business_partner = vendor_profile.business_partner

    selected_year = request.GET.get('year')
    selected_month = request.GET.get('month')

    batches_qs = PaymentBatch.objects.filter(
        payments__vendor=business_partner
    ).distinct()

    years = list(batches_qs.dates('created_at', 'year', order='DESC'))

    if selected_year and selected_year.isdigit():
        batches_qs = batches_qs.filter(created_at__year=int(selected_year))

    months_qs = batches_qs
    if selected_month and selected_month.isdigit():
        month_int = int(selected_month)
        if 1 <= month_int <= 12:
            batches_qs = batches_qs.filter(created_at__month=month_int)
            months_qs = months_qs.filter(created_at__month=month_int)

    available_month_dates = list(months_qs.dates('created_at', 'month', order='DESC'))
    available_months = [{'value': d.month, 'label': d.strftime('%B')} for d in available_month_dates]

    annotated_batches = batches_qs.annotate(
        vendor_total_sales=Sum(
            'payments__amount',
            filter=Q(payments__vendor=business_partner)
        ),
        vendor_net_payout=Sum(
            'payments__net_amount',
            filter=Q(payments__vendor=business_partner)
        ),
        vendor_period_start_payment=Min(
            'payments__payment_date',
            filter=Q(payments__vendor=business_partner)
        ),
        vendor_period_end_payment=Max(
            'payments__payment_date',
            filter=Q(payments__vendor=business_partner)
        ),
        vendor_period_start_created=Min(
            'payments__created_at',
            filter=Q(payments__vendor=business_partner)
        ),
        vendor_period_end_created=Max(
            'payments__created_at',
            filter=Q(payments__vendor=business_partner)
        ),
    ).order_by('-created_at')

    statements = []
    for batch in annotated_batches:
        start_date = (
            batch.vendor_period_start_payment
            or batch.vendor_period_start_created
            or batch.created_at
        )
        end_date = (
            batch.vendor_period_end_payment
            or batch.vendor_period_end_created
            or batch.processing_completed_at
            or batch.updated_at
            or batch.created_at
        )
        statements.append({
            'id': batch.id,
            'reference': batch.batch_reference,
            'start_date': start_date,
            'end_date': end_date,
            'total_sales': batch.vendor_total_sales or Decimal('0.00'),
            'net_payout': batch.vendor_net_payout or Decimal('0.00'),
            'status': batch.status,
            'status_display': batch.get_status_display(),
        })

    pending_processing_count = 0
    try:
        pending_processing_count = Order.objects.filter(
            items__part__vendor=business_partner,
            status__in=['confirmed', 'processing']
        ).distinct().count()
    except Exception:
        pending_processing_count = 0

    context = {
        'vendor_profile': vendor_profile,
        'business_partner': business_partner,
        'is_approved': vendor_profile.is_approved,
        'years': years,
        'months': available_months,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'statements': statements,
        'stats': {
            'pending_processing_count': pending_processing_count,
            'critical_notifications': 0,
        },
    }

    return render(request, 'vendors/finance/settlement.html', context)


@vendor_required
@login_required
def vendor_settlement_download_csv(request, batch_id):
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'Vendor profile not found.')
        return redirect('business_partners:vendor_registration_single')

    business_partner = vendor_profile.business_partner
    batch = get_object_or_404(
        PaymentBatch.objects.filter(payments__vendor=business_partner).distinct(),
        id=batch_id
    )

    payments = batch.payments.filter(vendor=business_partner).order_by('-created_at')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{batch.batch_reference}-statement.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Payment Reference',
        'Created At',
        'Payment Date',
        'Amount',
        'Commission',
        'Net Amount',
        'Status',
    ])

    for p in payments:
        writer.writerow([
            p.payment_reference,
            p.created_at.isoformat() if p.created_at else '',
            p.payment_date.isoformat() if p.payment_date else '',
            str(p.amount),
            str(p.commission_amount),
            str(p.net_amount),
            p.get_status_display(),
        ])

    return response


@vendor_required
@login_required
def vendor_payout_tracking(request):
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'Vendor profile not found.')
        return redirect('business_partners:vendor_registration_single')

    business_partner = vendor_profile.business_partner

    payment_terms_days = {
        'net_15': 15,
        'net_30': 30,
        'net_45': 45,
        'net_60': 60,
        'cod': 0,
        'prepaid': 0,
    }.get(vendor_profile.payment_terms, 30)

    # Structured bank details
    bank_name = vendor_profile.bank_name or ''
    account_number = vendor_profile.bank_account_number or ''
    iban = vendor_profile.iban or ''
    
    account_source = account_number or iban
    bank_account_display = '—'
    if account_source:
        last4 = ''.join(ch for ch in account_source if ch.isalnum())[-4:]
        if last4:
            prefix = bank_name or 'Bank'
            bank_account_display = f'{prefix} **** {last4}'
            if vendor_profile.bank_details_verified:
                bank_account_display += ' (Verified)'

    # Get Wallet
    vendor_ct = ContentType.objects.get_for_model(business_partner)
    wallet, created = Wallet.objects.get_or_create(
        owner_content_type=vendor_ct,
        owner_id=business_partner.id,
        defaults={'currency': 'USD'}
    )

    # Get or create legacy vendor balance for backward compatibility
    vendor_balance, created = VendorBalance.objects.get_or_create(
        vendor=business_partner,
        defaults={
            'current_balance': Decimal('0.00'),
            'pending_balance': Decimal('0.00'),
            'total_earned': Decimal('0.00'),
            'total_paid': Decimal('0.00')
        }
    )

    # Get Payouts from both legacy and new systems
    legacy_payouts_qs = VendorPayment.objects.filter(vendor=business_partner).order_by('-created_at')
    new_payouts_qs = Transaction.objects.filter(
        source_wallet=wallet, 
        transaction_type='PAYOUT'
    ).order_by('-created_at')

    # Normalize and merge payouts for display
    merged_payouts = []
    
    # Add legacy payouts
    for lp in legacy_payouts_qs:
        merged_payouts.append({
            'id': lp.id,
            'date': lp.payment_date or lp.processed_at or lp.created_at,
            'reference': lp.payment_reference,
            'amount': lp.net_amount,
            'method': lp.get_payment_method_display(),
            'status': lp.status,
            'status_display': lp.get_status_display(),
            'is_unified': False,
            'notes': lp.notes
        })
        
    # Add unified payouts
    for ut in new_payouts_qs:
        merged_payouts.append({
            'id': ut.id,
            'date': ut.created_at,
            'reference': f"TRX-{ut.id}",
            'amount': ut.amount_base,
            'method': ut.metadata.get('payment_method', 'Wallet Transfer'),
            'status': 'completed', # Unified transactions in this list are assumed completed
            'status_display': 'Completed',
            'is_unified': True,
            'notes': ut.metadata.get('reason', 'Payout')
        })
        
    # Sort merged list by date descending
    merged_payouts.sort(key=lambda x: x['date'], reverse=True)
    
    last_payout = legacy_payouts_qs.filter(status=PaymentStatus.COMPLETED).order_by(
        '-payment_date',
        '-processed_at',
        '-created_at',
    ).first()
    
    # Check if there's a newer payout in Transactions
    last_new_payout = new_payouts_qs.first()
    
    last_payout_amount = Decimal('0.00')
    last_payout_date = None
    
    if last_new_payout and (not last_payout or last_new_payout.created_at > (last_payout.payment_date or last_payout.processed_at or last_payout.created_at)):
        last_payout_amount = last_new_payout.amount_base
        last_payout_date = last_new_payout.created_at
    elif last_payout:
        last_payout_amount = last_payout.net_amount
        last_payout_date = last_payout.payment_date or last_payout.processed_at or last_payout.created_at

    pending_statuses = [PaymentStatus.PENDING, PaymentStatus.PROCESSING]
    pending_payments = list(
        legacy_payouts_qs.filter(status__in=pending_statuses).order_by('due_date', 'created_at')[:250]
    )

    today = timezone.now().date()
    computed_due_dates = []
    for p in pending_payments:
        if p.due_date:
            computed_due_dates.append((p.id, p.due_date))
        elif p.created_at:
            computed_due_dates.append((p.id, (p.created_at.date() + timedelta(days=payment_terms_days))))

    next_payout_date = None
    if computed_due_dates:
        next_payout_date = min(d for _, d in computed_due_dates)

    next_payout_estimated_amount = Decimal('0.00')
    if next_payout_date:
        next_due_payment_ids = {
            pid for pid, d in computed_due_dates if d == next_payout_date
        }
        for p in pending_payments:
            if p.id in next_due_payment_ids:
                next_payout_estimated_amount += (p.net_amount or Decimal('0.00'))

    pending_balance = wallet.escrow_balance or Decimal('0.00')
    
    clearing_in_days = None
    if next_payout_date:
        clearing_in_days = (next_payout_date - today).days

    payouts_page_size = 20
    paginator = Paginator(merged_payouts, payouts_page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    pending_processing_count = 0
    try:
        from parts.models import Order
        pending_processing_count = Order.objects.filter(
            items__part__vendor=business_partner,
            status__in=['confirmed', 'processing']
        ).distinct().count()
    except Exception:
        pending_processing_count = 0

    context = {
        'vendor_profile': vendor_profile,
        'business_partner': business_partner,
        'wallet': wallet,
        'is_approved': vendor_profile.is_approved,
        'next_payout_date': next_payout_date,
        'next_payout_estimated_amount': next_payout_estimated_amount,
        'last_payout_amount': last_payout_amount,
        'last_payout_date': last_payout_date,
        'pending_balance': pending_balance,
        'clearing_in_days': clearing_in_days,
        'bank_account_display': bank_account_display,
        'payouts': page_obj,
        'stats': {
            'pending_processing_count': pending_processing_count,
            'critical_notifications': 0,
        },
    }

    return render(request, 'vendors/finance/payouts.html', context)


@vendor_required
@login_required
def vendor_commission_breakdown(request):
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'Vendor profile not found.')
        return redirect('business_partners:vendor_registration_single')

    business_partner = vendor_profile.business_partner

    today = timezone.now().date()
    rules_qs = CommissionRule.objects.filter(
        is_active=True,
        effective_from__lte=today,
    ).filter(
        Q(effective_to__isnull=True) | Q(effective_to__gte=today)
    ).filter(
        Q(applies_to_all_vendors=True) | Q(specific_vendors=business_partner)
    ).distinct().order_by('-created_at')

    current_plan_name = 'Standard'
    current_plan_summary = 'No active commission rule configured.'
    current_plan_rule = rules_qs.first()
    if current_plan_rule:
        current_plan_name = current_plan_rule.name or 'Standard'
        if current_plan_rule.commission_type == 'percentage':
            current_plan_summary = f'{current_plan_rule.commission_rate}% commission'
        elif current_plan_rule.commission_type == 'fixed_amount':
            current_plan_summary = f'Fixed commission: {current_plan_rule.fixed_amount}'
        else:
            current_plan_summary = 'Tiered commission'

    # Get Wallet
    vendor_ct = ContentType.objects.get_for_model(business_partner)
    wallet, created = Wallet.objects.get_or_create(
        owner_content_type=vendor_ct,
        owner_id=business_partner.id,
        defaults={'currency': 'USD'}
    )

    payments_qs = VendorPayment.objects.filter(vendor=business_partner).order_by('-created_at')

    lookback_days = 90
    since = timezone.now() - timedelta(days=lookback_days)
    
    # Legacy totals
    payments_recent = payments_qs.filter(created_at__gte=since)
    legacy_totals = payments_recent.aggregate(
        total_sales=Sum('amount'),
        total_commission=Sum('commission_amount'),
    )
    
    # New totals from Transaction model
    # Commission is usually a separate transaction or metadata in a PAYMENT transaction.
    # Based on our migration, we often create a COMMISSION transaction.
    unified_commissions_qs = Transaction.objects.filter(
        source_wallet=wallet,
        transaction_type='COMMISSION',
        created_at__gte=since
    ).select_related('reference_content_type').order_by('-created_at')
    
    new_commission_total = Decimal('0.00')
    new_sales_total = Decimal('0.00')
    
    # Process unified transactions for accurate totals
    unified_data = []
    for uc in unified_commissions_qs:
        # 1. Get Commission Amount (actual commission, not including tax if combined in amount_base)
        comm_val = Decimal(str(uc.metadata.get('commission', uc.amount_base)))
        new_commission_total += comm_val
        
        # 2. Get Sales Amount (Gross Sale)
        sales_val = Decimal('0.00')
        if uc.reference and hasattr(uc.reference, 'total_price'):
            # OrderItem.total_price is usually net of tax in this model, 
            # so we add tax_amount if available to get the gross sale.
            sales_val = uc.reference.total_price
            if hasattr(uc.reference, 'tax_amount'):
                sales_val += uc.reference.tax_amount
        else:
            # Fallback reconstruction
            try:
                # Find the related PAYMENT transaction
                payment_tx = Transaction.objects.filter(
                    transaction_type='PAYMENT',
                    reference_content_type=uc.reference_content_type,
                    reference_id=uc.reference_id
                ).first()
                
                tax_val = Decimal(str(uc.metadata.get('tax', '0.00')))
                payout_val = payment_tx.amount_base if payment_tx else Decimal('0.00')
                
                # Metadata check for VAT registration (stored in PAYMENT metadata)
                is_vat = False
                if payment_tx and payment_tx.metadata.get('is_vat_registered'):
                    is_vat = True
                
                # Gross = (Payout - Tax if is_vat else Payout) + Commission + Tax
                if is_vat:
                    sales_val = (payout_val - tax_val) + comm_val + tax_val
                else:
                    sales_val = payout_val + comm_val + tax_val
            except Exception:
                # Last resort fallback to metadata
                sales_val = Decimal(str(uc.metadata.get('original_amount', uc.amount_base)))
        
        new_sales_total += sales_val
        
        # Store for merged_commissions list to avoid re-calculating
        unified_data.append({
            'uc': uc,
            'sales_val': sales_val,
            'comm_val': comm_val
        })

    total_sales = (legacy_totals.get('total_sales') or Decimal('0.00')) + new_sales_total
    total_commission = (legacy_totals.get('total_commission') or Decimal('0.00')) + new_commission_total
    
    # Normalize and merge commissions for display
    merged_commissions = []
    
    # Add legacy commissions (from VendorPayment)
    for lp in payments_recent:
        merged_commissions.append({
            'date': lp.created_at,
            'reference': lp.payment_reference,
            'amount': lp.amount,
            'commission_amount': lp.commission_amount,
            'net_amount': lp.net_amount,
            'commission_type': lp.commission_type,
            'commission_rate': lp.commission_rate,
            'is_unified': False
        })
        
    # Add unified commissions
    for ud in unified_data:
        uc = ud['uc']
        sales_amount = ud['sales_val']
        comm_amount = ud['comm_val']
        
        # Try to get order number for reference
        reference = uc.metadata.get('order_number')
        if not reference:
            reference = f"TRX-{uc.id}"
            
        merged_commissions.append({
            'date': uc.created_at,
            'reference': reference,
            'amount': sales_amount,
            'commission_amount': comm_amount,
            'net_amount': sales_amount - comm_amount,
            'commission_type': uc.metadata.get('commission_type', 'percentage'),
            'commission_rate': uc.metadata.get('commission_rate', Decimal('0.00')),
            'is_unified': True
        })
        
    # Sort merged list by date descending
    merged_commissions.sort(key=lambda x: x['date'], reverse=True)
    
    effective_rate = Decimal('0.00')
    if total_sales > 0:
        effective_rate = (total_commission / total_sales) * Decimal('100')

    paginator = Paginator(merged_commissions, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    pending_processing_count = 0
    try:
        from parts.models import Order
        pending_processing_count = Order.objects.filter(
            items__part__vendor=business_partner,
            status__in=['confirmed', 'processing']
        ).distinct().count()
    except Exception:
        pending_processing_count = 0

    context = {
        'vendor_profile': vendor_profile,
        'business_partner': business_partner,
        'wallet': wallet,
        'is_approved': vendor_profile.is_approved,
        'current_plan_name': current_plan_name,
        'current_plan_summary': current_plan_summary,
        'commission_rules': rules_qs[:10],
        'payments': page_obj,
        'lookback_days': lookback_days,
        'total_sales': total_sales,
        'total_commission': total_commission,
        'effective_rate': effective_rate,
        'stats': {
            'pending_processing_count': pending_processing_count,
            'critical_notifications': 0,
        },
    }

    return render(request, 'vendors/finance/comissions.html', context)


@vendor_required
@login_required
def vendor_tax_summary(request):
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'Vendor profile not found.')
        return redirect('business_partners:vendor_registration_single')

    business_partner = vendor_profile.business_partner

    if request.method == 'POST':
        tax_id = (request.POST.get('tax_id') or '').strip()
        vendor_profile.tax_id = tax_id or None
        vendor_profile.save(update_fields=['tax_id'])
        messages.success(request, 'Tax settings updated.')
        return redirect('business_partners:vendor_tax_summary')

    from parts.models import Order

    now = timezone.now()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    base_orders = Order.objects.filter(items__part__vendor=business_partner).distinct()
    orders_in_period = base_orders.filter(
        Q(status='delivered') | Q(payment_status='completed'),
        created_at__gte=period_start,
    )

    sales_tax_payable = Decimal('0.00')
    
    # Sorting logic
    sort_param = request.GET.get('sort', '-created_at')
    allowed_sorts = {
        'order_number': 'order_number',
        '-order_number': '-order_number',
        'created_at': 'created_at',
        '-created_at': '-created_at',
        'total_price': 'total_price',
        '-total_price': '-total_price',
        'tax_amount': 'tax_amount',
        '-tax_amount': '-tax_amount',
    }
    order_by = allowed_sorts.get(sort_param, '-created_at')

    per_order_totals_query = orders_in_period.annotate(
        vendor_items_total=Sum(
            F('items__quantity') * F('items__price'),
            filter=Q(items__part__vendor=business_partner)
        ),
        vendor_count=Count('items__part__vendor', distinct=True)
    ).order_by(order_by)

    order_tax_details = []
    for order in per_order_totals_query:
        order_total = order.total_price or Decimal('0.00')
        vendor_total = order.vendor_items_total or Decimal('0.00')
        
        # Skip if no value for this vendor
        if vendor_total <= 0:
            continue
        
        # Determine tax share
        # If vendor is the only one in the order, they take the full tax
        if order.vendor_count == 1:
            vendor_share_tax = order.tax_amount or Decimal('0.00')
        else:
            # Proportional calculation for multi-vendor orders
            # Use ratio of vendor items to order total (excluding shipping if possible, but total_price is easier)
            if order_total > 0:
                ratio = vendor_total / order_total
                vendor_share_tax = (order.tax_amount or Decimal('0.00')) * ratio
            else:
                vendor_share_tax = Decimal('0.00')
        
        sales_tax_payable += vendor_share_tax
        
        order_tax_details.append({
            'id': order.id,
            'order_number': order.order_number,
            'created_at': order.created_at,
            'total_price': order_total,
            'tax_amount': order.tax_amount or Decimal('0.00'),
            'vendor_items_total': vendor_total,
            'vendor_share_tax': vendor_share_tax,
        })

    # Pagination
    paginator = Paginator(order_tax_details, 10)  # 10 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    withholding_tax_payable = Decimal('0.00')
    total_payable = sales_tax_payable + withholding_tax_payable

    from .document_models import VendorDocument

    tax_certificate_doc = (
        VendorDocument.objects.filter(
            business_partner=business_partner,
            category__name__iexact='Tax Certificate',
        )
        .order_by('-uploaded_at')
        .first()
    )
    tax_certificate_file = tax_certificate_doc.file if tax_certificate_doc else None
    vat_certificate_file = getattr(vendor_profile, 'vat_certificate', None)

    pending_processing_count = 0
    try:
        pending_processing_count = Order.objects.filter(
            items__part__vendor=business_partner,
            status__in=['confirmed', 'processing']
        ).distinct().count()
    except Exception:
        pending_processing_count = 0

    context = {
        'vendor_profile': vendor_profile,
        'business_partner': business_partner,
        'is_approved': vendor_profile.is_approved,
        'tax_period_label': now.strftime('%B %Y'),
        'sales_tax_payable': sales_tax_payable,
        'withholding_tax_payable': withholding_tax_payable,
        'total_tax_payable': total_payable,
        'page_obj': page_obj,
        'current_sort': sort_param,
        'has_tax_certificate': bool(tax_certificate_file or vat_certificate_file),
        'stats': {
            'pending_processing_count': pending_processing_count,
            'critical_notifications': 0,
        },
    }

    return render(request, 'vendors/finance/taxes.html', context)


@vendor_required
@login_required
def vendor_tax_certificate_download(request):
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'Vendor profile not found.')
        return redirect('business_partners:vendor_registration_single')

    business_partner = vendor_profile.business_partner

    from .document_models import VendorDocument

    tax_certificate_doc = (
        VendorDocument.objects.filter(
            business_partner=business_partner,
            category__name__iexact='Tax Certificate',
        )
        .order_by('-uploaded_at')
        .first()
    )

    if tax_certificate_doc and tax_certificate_doc.file:
        file_field = tax_certificate_doc.file
    else:
        file_field = getattr(vendor_profile, 'vat_certificate', None)

    if not file_field:
        messages.error(request, 'No tax certificate uploaded.')
        return redirect('business_partners:vendor_tax_summary')

    filename = (file_field.name or '').rsplit('/', 1)[-1] or 'tax-certificate'
    return FileResponse(file_field.open('rb'), as_attachment=True, filename=filename)


@vendor_required
@login_required
def vendor_finance_ledger(request):
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'Vendor profile not found.')
        return redirect('business_partners:vendor_registration_single')

    business_partner = vendor_profile.business_partner
    
    # Get or create vendor wallet (Unified Model)
    vendor_ct = ContentType.objects.get_for_model(business_partner)
    wallet, created = Wallet.objects.get_or_create(
        owner_content_type=vendor_ct,
        owner_id=business_partner.id,
        defaults={'currency': 'USD'}
    )

    # Get or create legacy balance
    vendor_balance, created = VendorBalance.objects.get_or_create(
        vendor=business_partner,
        defaults={'current_balance': Decimal('0.00'), 'total_earned': Decimal('0.00'), 'total_paid': Decimal('0.00')}
    )

    # Recalculate Legacy Total Earned (Delivered Orders NOT in Unified Transactions)
    # This prevents double-counting of earnings that have already been migrated to the unified system.
    order_item_ct = ContentType.objects.get_for_model(OrderItem)
    
    legacy_total_earned = OrderItem.objects.filter(
        part__vendor=business_partner,
        order__status='delivered'
    ).exclude(
        id__in=Transaction.objects.filter(
            reference_content_type=order_item_ct,
            destination_wallet=wallet
        ).values_list('reference_id', flat=True)
    ).aggregate(
        total=Sum(F('price') * F('quantity'))
    )['total'] or Decimal('0.00')

    # Update legacy balance object for this request
    vendor_balance.total_earned = legacy_total_earned
    vendor_balance.update_balance()

    # Get legacy payouts
    legacy_payouts = VendorPayment.objects.filter(
        vendor=business_partner,
        status=PaymentStatus.COMPLETED
    ).order_by('created_at')

    # Get unified transactions
    transactions_qs = Transaction.objects.filter(
        Q(source_wallet=wallet) | Q(destination_wallet=wallet)
    ).order_by('created_at')

    ledger_rows = []
    running_balance = Decimal('0.00')
    
    # 1. Add Legacy Opening Balance (if any)
    # If total_earned > 0 but we don't have individual transaction records, 
    # we can show a "Legacy Earnings" entry.
    if vendor_balance.total_earned > 0:
        running_balance += vendor_balance.total_earned
        ledger_rows.append({
            'date': vendor_balance.created_at or business_partner.created_at,
            'type': 'legacy_earnings',
            'label': 'Legacy Earnings',
            'description': 'Historical earnings from legacy system',
            'debit': None,
            'credit': vendor_balance.total_earned,
            'balance': running_balance,
            'reference': "LEGACY-EARN"
        })

    # 2. Add Legacy Payouts
    for lp in legacy_payouts:
        debit = lp.net_amount
        running_balance -= debit
        ledger_rows.append({
            'date': lp.payment_date or lp.processed_at or lp.created_at,
            'type': 'payout',
            'label': 'Legacy Payout',
            'description': lp.notes or f"Payout ({lp.get_payment_method_display()})",
            'debit': debit,
            'credit': None,
            'balance': running_balance,
            'reference': lp.payment_reference
        })

    # 3. Add Unified Transactions
    for tx in transactions_qs:
        is_credit = tx.destination_wallet == wallet
        credit = tx.amount_base if is_credit else Decimal('0.00')
        debit = tx.amount_base if not is_credit else Decimal('0.00')
        
        running_balance += credit
        running_balance -= debit
        
        ledger_rows.append({
            'date': tx.created_at,
            'type': tx.transaction_type.lower(),
            'label': tx.get_transaction_type_display(),
            'description': tx.metadata.get('reason') or tx.get_transaction_type_display(),
            'debit': debit if debit > 0 else None,
            'credit': credit if credit > 0 else None,
            'balance': running_balance,
            'reference': f"TRX-{tx.id}"
        })

    ledger_rows.reverse()  # Show newest first

    paginator = Paginator(ledger_rows, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    pending_processing_count = 0
    try:
        from parts.models import Order
        pending_processing_count = Order.objects.filter(
            items__part__vendor=business_partner,
            status__in=['confirmed', 'processing']
        ).distinct().count()
    except Exception:
        pending_processing_count = 0

    context = {
        'vendor_profile': vendor_profile,
        'business_partner': business_partner,
        'wallet': wallet,
        'is_approved': vendor_profile.is_approved,
        'ledger_rows': page_obj,
        'stats': {
            'pending_processing_count': pending_processing_count,
            'critical_notifications': 0,
        },
    }

    return render(request, 'vendors/finance/ledger.html', context)


@vendor_required
@login_required
def vendor_finance_ledger_export_csv(request):
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'Vendor profile not found.')
        return redirect('business_partners:vendor_registration_single')

    business_partner = vendor_profile.business_partner
    
    # Get or create vendor wallet (Unified Model)
    vendor_ct = ContentType.objects.get_for_model(business_partner)
    wallet, created = Wallet.objects.get_or_create(
        owner_content_type=vendor_ct,
        owner_id=business_partner.id,
        defaults={'currency': 'USD'}
    )

    # Get or create legacy balance
    vendor_balance, created = VendorBalance.objects.get_or_create(
        vendor=business_partner,
        defaults={'current_balance': Decimal('0.00'), 'total_earned': Decimal('0.00'), 'total_paid': Decimal('0.00')}
    )

    # Recalculate Legacy Total Earned (Delivered Orders NOT in Unified Transactions)
    order_item_ct = ContentType.objects.get_for_model(OrderItem)
    
    legacy_total_earned = OrderItem.objects.filter(
        part__vendor=business_partner,
        order__status='delivered'
    ).exclude(
        id__in=Transaction.objects.filter(
            reference_content_type=order_item_ct,
            destination_wallet=wallet
        ).values_list('reference_id', flat=True)
    ).aggregate(
        total=Sum(F('price') * F('quantity'))
    )['total'] or Decimal('0.00')

    # Update legacy balance object for this request
    vendor_balance.total_earned = legacy_total_earned
    vendor_balance.update_balance()

    # Get legacy payouts
    legacy_payouts = VendorPayment.objects.filter(
        vendor=business_partner,
        status=PaymentStatus.COMPLETED
    ).order_by('created_at')

    # Get unified transactions
    transactions_qs = Transaction.objects.filter(
        Q(source_wallet=wallet) | Q(destination_wallet=wallet)
    ).order_by('created_at')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="vendor-ledger-{business_partner.id}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Reference', 'Type', 'Description', 'Debit', 'Credit', 'Balance'])

    running_balance = Decimal('0.00')

    # 1. Add Legacy Opening Balance (if any)
    if vendor_balance.total_earned > 0:
        running_balance += vendor_balance.total_earned
        writer.writerow([
            (vendor_balance.created_at or business_partner.created_at).isoformat(),
            "LEGACY-EARN",
            "Legacy Earnings",
            "Historical earnings from legacy system",
            '',
            str(vendor_balance.total_earned),
            str(running_balance)
        ])

    # 2. Add Legacy Payouts
    for lp in legacy_payouts:
        debit = lp.net_amount
        running_balance -= debit
        writer.writerow([
            (lp.payment_date or lp.processed_at or lp.created_at).isoformat(),
            lp.payment_reference,
            "Legacy Payout",
            lp.notes or f"Payout ({lp.get_payment_method_display()})",
            str(debit),
            '',
            str(running_balance)
        ])

    # 3. Add Unified Transactions
    for tx in transactions_qs:
        is_credit = tx.destination_wallet == wallet
        credit = tx.amount_base if is_credit else Decimal('0.00')
        debit = tx.amount_base if not is_credit else Decimal('0.00')
        
        running_balance += credit
        running_balance -= debit
        
        writer.writerow([
            tx.created_at.isoformat(),
            f"TRX-{tx.id}",
            tx.get_transaction_type_display(),
            tx.metadata.get('reason') or tx.get_transaction_type_display(),
            str(debit) if debit > 0 else '',
            str(credit) if credit > 0 else '',
            str(running_balance),
        ])

    return response


@vendor_required
@login_required
def vendor_bank_setup(request):
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'Vendor profile not found.')
        return redirect('business_partners:vendor_registration_single')

    existing = {
        'bank_name': vendor_profile.bank_name or '',
        'bank_branch': vendor_profile.bank_routing_number or '',
        'account_holder_name': vendor_profile.bank_account_holder_name or '',
        'account_number': vendor_profile.bank_account_number or '',
        'iban': vendor_profile.iban or '',
        'swift_code': vendor_profile.swift_code or '',
    }

    if request.method == 'POST':
        bank_name = (request.POST.get('bank_name') or '').strip() or None
        bank_branch = (request.POST.get('bank_branch') or '').strip() or None
        account_holder_name = (request.POST.get('account_holder_name') or '').strip() or None
        account_number = (request.POST.get('account_number') or '').strip() or None
        iban = (request.POST.get('iban') or '').strip() or None
        swift_code = (request.POST.get('swift_code') or '').strip() or None

        existing_values = {
            'bank_name': vendor_profile.bank_name,
            'bank_branch': vendor_profile.bank_routing_number,
            'account_holder_name': vendor_profile.bank_account_holder_name,
            'account_number': vendor_profile.bank_account_number,
            'iban': vendor_profile.iban,
            'swift_code': vendor_profile.swift_code,
        }

        new_values = {
            'bank_name': bank_name,
            'bank_branch': bank_branch,
            'account_holder_name': account_holder_name,
            'account_number': account_number,
            'iban': iban,
            'swift_code': swift_code,
        }

        changed = existing_values != new_values

        vendor_profile.bank_name = bank_name
        vendor_profile.bank_routing_number = bank_branch
        vendor_profile.bank_account_holder_name = account_holder_name
        vendor_profile.bank_account_number = account_number
        vendor_profile.iban = iban
        vendor_profile.swift_code = swift_code

        lines = []
        if account_holder_name:
            lines.append(f'Account Holder: {account_holder_name}')
        if bank_name:
            lines.append(f'Bank: {bank_name}')
        if bank_branch:
            lines.append(f'Branch: {bank_branch}')
        if account_number:
            lines.append(f'Account Number: {account_number}')
        if iban:
            lines.append(f'IBAN: {iban}')
        if swift_code:
            lines.append(f'SWIFT: {swift_code}')

        vendor_profile.bank_account_details = '\n'.join(lines) if lines else None

        update_fields = [
            'bank_name',
            'bank_routing_number',
            'bank_account_holder_name',
            'bank_account_number',
            'iban',
            'swift_code',
            'bank_account_details',
        ]

        if changed:
            vendor_profile.bank_details_verified = False
            vendor_profile.bank_verification_date = None
            vendor_profile.bank_verified_by = None
            update_fields.extend(['bank_details_verified', 'bank_verification_date', 'bank_verified_by'])

        vendor_profile.save(update_fields=update_fields)
        messages.success(request, 'Bank details saved.')
        return redirect('business_partners:vendor_bank_setup')

    pending_processing_count = 0
    try:
        from parts.models import Order
        pending_processing_count = Order.objects.filter(
            items__part__vendor=vendor_profile.business_partner,
            status__in=['confirmed', 'processing']
        ).distinct().count()
    except Exception:
        pending_processing_count = 0

    context = {
        'vendor_profile': vendor_profile,
        'business_partner': vendor_profile.business_partner,
        'is_approved': vendor_profile.is_approved,
        'bank_form': existing,
        'bank_options': [
            'Habib Bank Limited (HBL)',
            'United Bank Limited (UBL)',
            'Meezan Bank',
            'Bank Alfalah',
        ],
        'stats': {
            'pending_processing_count': pending_processing_count,
            'critical_notifications': 0,
        },
    }

    return render(request, 'vendors/finance/bank_setup.html', context)


@vendor_required
@login_required
def vendor_earnings(request):
    """
    Vendor earnings and wallet page.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'Vendor profile not found.')
        return redirect('business_partners:vendor_registration_single')
    
    business_partner = vendor_profile.business_partner
    
    # Get or create vendor wallet (Unified Finance)
    vendor_ct = ContentType.objects.get_for_model(BusinessPartner)
    wallet, created = Wallet.objects.get_or_create(
        owner_content_type=vendor_ct,
        owner_id=business_partner.id,
        defaults={'currency': vendor_profile.preferred_currency or 'USD'}
    )

    # Get or create legacy vendor balance for backward compatibility
    vendor_balance, created = VendorBalance.objects.get_or_create(
        vendor=business_partner,
        defaults={
            'current_balance': Decimal('0.00'),
            'pending_balance': Decimal('0.00'),
            'total_earned': Decimal('0.00'),
            'total_paid': Decimal('0.00')
        }
    )
    
    # Recalculate Legacy Total Earned (Delivered Orders NOT in Unified Transactions)
    order_item_ct = ContentType.objects.get_for_model(OrderItem)
    
    legacy_total_earned = OrderItem.objects.filter(
        part__vendor=business_partner,
        order__status='delivered'
    ).exclude(
        id__in=Transaction.objects.filter(
            reference_content_type=order_item_ct,
            destination_wallet=wallet
        ).values_list('reference_id', flat=True)
    ).aggregate(
        total=Sum(F('price') * F('quantity'))
    )['total'] or Decimal('0.00')

    # Calculate Pending Clearance (Orders confirmed/processing/shipped but not yet delivered)
    # Only for orders NOT in Unified Transactions
    pending_clearance_amount = OrderItem.objects.filter(
        part__vendor=business_partner,
        order__status__in=['confirmed', 'processing', 'shipped']
    ).exclude(
        id__in=Transaction.objects.filter(
            reference_content_type=order_item_ct,
            destination_wallet=wallet
        ).values_list('reference_id', flat=True)
    ).aggregate(
        total=Sum(F('price') * F('quantity'))
    )['total'] or Decimal('0.00')

    # Update Legacy Vendor Balance
    vendor_balance.total_earned = legacy_total_earned
    vendor_balance.pending_balance = pending_clearance_amount
    vendor_balance.update_balance() 
    
    # Get recent transactions (Combined legacy and unified)
    legacy_payments = VendorPayment.objects.filter(
        vendor=business_partner
    ).order_by('-created_at')[:10]

    unified_transactions = Transaction.objects.filter(
        Q(source_wallet=wallet) | Q(destination_wallet=wallet)
    ).order_by('-created_at')[:10]

    # Normalize and merge transactions for display
    merged_transactions = []
    
    for lp in legacy_payments:
        merged_transactions.append({
            'date': lp.created_at,
            'reference': lp.payment_reference,
            'notes': lp.notes or f"Legacy Payout ({lp.get_payment_method_display()})",
            'type': 'payout', 
            'amount': -lp.amount, # Payouts are negative for the vendor balance
            'status': lp.status,
            'is_unified': False
        })

    for ut in unified_transactions:
        # Determine if it's a credit or debit for the vendor
        is_credit = ut.destination_wallet == wallet
        amount = ut.amount_base if is_credit else -ut.amount_base
        
        merged_transactions.append({
            'date': ut.created_at,
            'reference': f"TRX-{ut.id}",
            'notes': f"{ut.get_transaction_type_display()}",
            'type': ut.transaction_type.lower(),
            'amount': amount,
            'status': 'completed', 
            'is_unified': True
        })

    # Sort merged list by date descending
    merged_transactions.sort(key=lambda x: x['date'], reverse=True)
    merged_transactions = merged_transactions[:10] # Keep top 10

    # Combined stats for template
    payout_sum = Transaction.objects.filter(
        source_wallet=wallet,
        transaction_type='PAYOUT'
    ).aggregate(total=Sum('amount_base'))['total'] or Decimal('0.00')
    
    total_withdrawn = (vendor_balance.total_paid or Decimal('0.00')) + payout_sum

    available_balance = wallet.available_balance or Decimal('0.00')

    # Chart Data: Last 6 months revenue
    revenue_labels = []
    revenue_data = []
    today = timezone.now()
    
    for i in range(6):
        month_target = today.month - i
        year_target = today.year
        if month_target <= 0:
            month_target += 12
            year_target -= 1
            
        # Get data for this month (Earnings/Payments)
        # Combine legacy payments and unified transactions
        legacy_monthly = VendorPayment.objects.filter(
            vendor=business_partner,
            status=PaymentStatus.COMPLETED,
            created_at__year=year_target,
            created_at__month=month_target
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        unified_monthly = Transaction.objects.filter(
            destination_wallet=wallet,
            transaction_type='PAYMENT',
            created_at__year=year_target,
            created_at__month=month_target
        ).aggregate(total=Sum('amount_base'))['total'] or Decimal('0.00')

        total_monthly = legacy_monthly + unified_monthly
        
        import datetime as dt
        month_name = dt.date(year_target, month_target, 1).strftime('%b')
        revenue_labels.insert(0, month_name)
        revenue_data.insert(0, float(total_monthly))

    context = {
        'vendor_profile': vendor_profile,
        'business_partner': business_partner,
        'wallet': wallet,
        'vendor_balance': vendor_balance,
        'available_balance': available_balance,
        'total_withdrawn': total_withdrawn,
        'pending_clearance': pending_clearance_amount,
        'recent_transactions': merged_transactions,
        'revenue_labels': json.dumps(revenue_labels),
        'revenue_data': json.dumps(revenue_data),
        'is_approved': vendor_profile.is_approved,
    }
    
    return render(request, 'vendors/earnings.html', context)


@vendor_required
@login_required
def vendor_invoices(request):
    """
    Vendor invoices management page.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'Vendor profile not found.')
        return redirect('business_partners:vendor_registration_single')
    
    business_partner = vendor_profile.business_partner
    
    # Import Order here to avoid circular imports if any
    from parts.models import Order, OrderItem
    
    # Get all orders containing items from this vendor
    # We treat these Orders as "Invoices" for the purpose of this view
    orders = Order.objects.filter(
        items__part__vendor=business_partner
    ).distinct().order_by('-created_at')

    try:
        from core.models import ExchangeRate
        from decimal import Decimal as D
    except Exception:
        ExchangeRate = None
        D = Decimal

    def _unit_price_usd(order_item):
        original_currency_code = (getattr(order_item, 'original_currency_code', None) or getattr(order_item.part, 'original_currency', None) or 'USD').upper()
        if getattr(order_item, 'vendor_currency_amount', None):
            vendor_amount = order_item.vendor_currency_amount
            if getattr(order_item, 'locked_exchange_rate', None):
                if original_currency_code == 'USD':
                    return vendor_amount
                return vendor_amount * order_item.locked_exchange_rate
            if original_currency_code == 'USD':
                return vendor_amount
            if ExchangeRate:
                return vendor_amount * D(str(ExchangeRate.get_current_rate(original_currency_code, 'USD')))
            return order_item.price

        if original_currency_code == 'USD':
            return order_item.part.standard_price
        if ExchangeRate:
            return order_item.part.standard_price * D(str(ExchangeRate.get_current_rate(original_currency_code, 'USD')))
        return order_item.price

    def _tax_rate(order_item):
        from parts.views import _get_country_standard_tax_rate, _get_item_tax_rate
        
        # Try to get country code from order's shipping info
        country_code = None
        shipping_info = getattr(order_item.order, 'shipping_info', None)
        if shipping_info and getattr(shipping_info, 'city', None):
            try:
                country_code = shipping_info.city.country.code
            except Exception:
                pass
        
        country_standard_rate = _get_country_standard_tax_rate(country_code)
        return _get_item_tax_rate(order_item.part, country_standard_rate, dest_country_code=country_code)

    def _sum_items_usd(items_qs):
        total = Decimal('0.00')
        for item in items_qs:
            line_subtotal = (_unit_price_usd(item) or Decimal('0.00')) * item.quantity
            item_tax = getattr(item, 'tax_amount', None)
            if item_tax is None:
                item_tax = line_subtotal * _tax_rate(item)
            total += line_subtotal + item_tax
        return total
    
    # --- Statistics ---
    
    # Total Due: Orders that are not paid yet (payment_status != completed)
    # This might be simplistic, but it's a starting point.
    total_due = _sum_items_usd(
        OrderItem.objects.filter(
            part__vendor=business_partner
        ).exclude(order__payment_status='completed').select_related('part')
    )
    
    # Paid (This Month): Orders paid in the current month
    today = timezone.now()
    paid_this_month = _sum_items_usd(
        OrderItem.objects.filter(
            part__vendor=business_partner,
            order__payment_status='completed',
            order__updated_at__year=today.year,
            order__updated_at__month=today.month
        ).select_related('part')
    )
    
    # Overdue: For now, let's assume 'failed' payments or pending for > 30 days are "overdue"
    # Or just use a placeholder if business logic is not defined
    overdue_date = today - timedelta(days=30)
    overdue_amount = _sum_items_usd(
        OrderItem.objects.filter(
            part__vendor=business_partner,
            order__payment_status='pending',
            order__created_at__lt=overdue_date
        ).select_related('part')
    )
    
    # --- Filtering ---
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(customer__first_name__icontains=search_query) |
            Q(customer__last_name__icontains=search_query) |
            Q(customer__email__icontains=search_query) |
            Q(guest_name__icontains=search_query) |
            Q(guest_email__icontains=search_query)
        )
    
    if status_filter:
        if status_filter == 'Paid':
            orders = orders.filter(payment_status='completed')
        elif status_filter == 'Pending':
            orders = orders.filter(payment_status='pending')
        elif status_filter == 'Overdue':
            orders = orders.filter(payment_status='pending', created_at__lt=overdue_date)
            
    if date_filter:
        try:
            date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
            orders = orders.filter(created_at__date=date_obj)
        except (ValueError, NameError):
            pass

    # --- Pagination ---
    paginator = Paginator(orders, 10) # 10 invoices per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    for invoice in page_obj:
        invoice.vendor_total = _sum_items_usd(
            OrderItem.objects.filter(
                order=invoice,
                part__vendor=business_partner
            ).select_related('part')
        )
    
    context = {
        'vendor_profile': vendor_profile,
        'invoices': page_obj,
        'stats': {
            'total_due': total_due,
            'paid_this_month': paid_this_month,
            'overdue': overdue_amount,
        },
        'search_query': search_query,
        'status_filter': status_filter,
        'date_filter': date_filter,
    }
    
    return render(request, 'vendors/invoices.html', context)


@vendor_required
def vendor_parts_list(request):
    """
    List all parts for the vendor with advanced filtering and search.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    business_partner = vendor_profile.business_partner
    
    # Get all vendor's parts
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
    
    # Initialize search form
    search_form = VendorPartSearchForm(request.GET or None)
    
    # Apply filters
    if search_form.is_valid():
        # Basic search
        search_query = search_form.cleaned_data.get('search')
        if search_query:
            parts_queryset = parts_queryset.filter(
                Q(parts_number__icontains=search_query) |
                Q(material_description__icontains=search_query) |
                Q(material_description_ar__icontains=search_query) |
                Q(manufacturer_part_number__icontains=search_query) |
                Q(manufacturer_oem_number__icontains=search_query)
            )
        
        # Category filter
        category = search_form.cleaned_data.get('category')
        if category:
            parts_queryset = parts_queryset.filter(category=category)
        
        # Brand filter
        brand = search_form.cleaned_data.get('brand')
        if brand:
            parts_queryset = parts_queryset.filter(brand=brand)
        
        # Status filters
        is_active = search_form.cleaned_data.get('is_active')
        if is_active == 'true':
            parts_queryset = parts_queryset.filter(is_active=True)
        elif is_active == 'false':
            parts_queryset = parts_queryset.filter(is_active=False)
        
        is_featured = search_form.cleaned_data.get('is_featured')
        if is_featured == 'true':
            parts_queryset = parts_queryset.filter(is_featured=True)
        elif is_featured == 'false':
            parts_queryset = parts_queryset.filter(is_featured=False)
        
        # Stock status filter
        stock_status = search_form.cleaned_data.get('stock_status')
        if stock_status == 'in_stock':
            parts_queryset = parts_queryset.filter(quantity__gt=10)
        elif stock_status == 'low_stock':
            parts_queryset = parts_queryset.filter(quantity__gt=0, quantity__lte=10)
        elif stock_status == 'out_of_stock':
            parts_queryset = parts_queryset.filter(quantity=0)
        
        # Price range
        min_price = search_form.cleaned_data.get('min_price')
        if min_price:
            parts_queryset = parts_queryset.filter(price__gte=min_price)
        
        max_price = search_form.cleaned_data.get('max_price')
        if max_price:
            parts_queryset = parts_queryset.filter(price__lte=max_price)
        
        # Vendor-specific filters
        material_type = search_form.cleaned_data.get('material_type')
        if material_type:
            parts_queryset = parts_queryset.filter(material_type__icontains=material_type)
        
        plant = search_form.cleaned_data.get('plant')
        if plant:
            parts_queryset = parts_queryset.filter(plant__icontains=plant)
        
        material_group = search_form.cleaned_data.get('material_group')
        if material_group:
            parts_queryset = parts_queryset.filter(material_group__icontains=material_group)
        
        abc_indicator = search_form.cleaned_data.get('abc_indicator')
        if abc_indicator:
            parts_queryset = parts_queryset.filter(abc_indicator=abc_indicator)
        
        # Sorting
        sort_by = search_form.cleaned_data.get('sort_by')
        if sort_by:
            parts_queryset = parts_queryset.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(parts_queryset, 25)  # Show 25 parts per page
    page_number = request.GET.get('page')
    parts = paginator.get_page(page_number)
    
    # Calculate inventory statistics
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
    
    # Calculate dead stock (parts not sold for 30+ days)
    # This is a bit expensive, so we might want to optimize or cache it
    # For now, simply count parts with no recent transactions if needed, 
    # or just use the filtered queryset count if 'dead_stock' filter is active
    
    # Get categories for filters
    categories = parts_queryset.values('category__id', 'category__name').distinct().order_by('category__name')

    context = {
        'parts': parts,
        'search_form': search_form,
        'vendor_profile': vendor_profile,
        'total_parts': parts_queryset.count(),
        'total_value': total_value,
        'stock_stats': stock_stats,
        'categories': categories,
        'search_query': search_form.cleaned_data.get('search') if search_form.is_valid() else '',
        'category_filter': search_form.cleaned_data.get('category').id if search_form.is_valid() and search_form.cleaned_data.get('category') else '',
        'stock_status': search_form.cleaned_data.get('stock_status') if search_form.is_valid() else '',
    }
    
    # Check if this is an HTMX request
    if request.headers.get('HX-Request'):
        return render(request, 'vendors/inventory_table.html', context)
        
    return render(request, 'business_partners/vendor_parts_list_standardized.html', context)


@vendor_required
def vendor_part_create(request):
    """
    Create a new part for the vendor with access to all Excel fields.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    business_partner = vendor_profile.business_partner
    
    if request.method == 'POST':
        form = VendorPartForm(request.POST, request.FILES, vendor=business_partner, user=request.user)
        if form.is_valid():
            part = form.save()
            messages.success(request, f'Part "{part.parts_number}" created successfully.')
            return redirect('business_partners:vendor_parts_list')
    else:
        form = VendorPartForm(vendor=business_partner, user=request.user)
    
    context = {
        'form': form,
        'vendor_profile': vendor_profile,
        'action': 'Create',
    }
    
    return render(request, 'business_partners/vendor_part_form_standardized.html', context)


@vendor_part_owner_required
def vendor_part_edit(request, part_id):
    """
    Edit an existing part for the vendor with access to all Excel fields.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    business_partner = vendor_profile.business_partner
    
    # Get the part and ensure it belongs to this vendor
    part = get_object_or_404(Part, id=part_id, vendor=business_partner)
    
    if request.method == 'POST':
        form = VendorPartForm(request.POST, request.FILES, instance=part, vendor=business_partner, user=request.user)
        if form.is_valid():
            part = form.save()
            messages.success(request, f'Part "{part.parts_number}" updated successfully.')
            return redirect('business_partners:vendor_parts_list')
    else:
        form = VendorPartForm(instance=part, vendor=business_partner, user=request.user)
    
    context = {
        'form': form,
        'part': part,
        'vendor_profile': vendor_profile,
        'action': 'Edit',
        'is_edit': True,
        'action_url': request.path,
    }
    
    return render(request, 'vendors/edit_part.html', context)


@vendor_part_owner_required
def vendor_part_detail(request, part_id):
    """
    View detailed information about a specific part.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    business_partner = vendor_profile.business_partner
    
    # Get the part and ensure it belongs to this vendor
    part = get_object_or_404(Part, id=part_id, vendor=business_partner)
    
    # Get categorized fields based on user permissions
    visible_fields = part.get_fields_for_user(request.user)
    can_edit = part.can_user_edit(request.user)
    
    context = {
        'part': part,
        'visible_fields': visible_fields,
        'can_edit': can_edit,
        'vendor_profile': vendor_profile,
    }
    
    return render(request, 'business_partners/vendor_part_detail_standardized.html', context)


@vendor_part_owner_required
@require_http_methods(["POST"])
def vendor_part_delete(request, part_id):
    """
    Delete a part (AJAX endpoint).
    Permission checking is handled by the decorator.
    """
    try:
        part = get_object_or_404(Part, id=part_id)
        part_number = part.parts_number
        part.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Part "{part_number}" deleted successfully.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@vendor_required
def vendor_parts_bulk_update(request):
    """
    Bulk update multiple parts at once.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    business_partner = vendor_profile.business_partner
    
    if request.method == 'POST':
        form = VendorPartBulkUpdateForm(request.POST)
        part_ids = request.POST.getlist('selected_parts')
        
        if form.is_valid() and part_ids:
            # Get selected parts that belong to this vendor
            parts = Part.objects.filter(id__in=part_ids, vendor=business_partner)
            
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
            
            if not parts.exists():
                messages.error(request, 'No valid parts selected.')
                return redirect('business_partners:vendor_parts_list')
            
            updated_count = 0
            
            with transaction.atomic():
                for part in parts:
                    updated = False
                    
                    # Price adjustments
                    price_type = form.cleaned_data.get('price_adjustment_type')
                    price_value = form.cleaned_data.get('price_adjustment_value')
                    
                    if price_type and price_value:
                        if price_type == 'percentage_increase':
                            part.price = part.price * (1 + price_value / 100)
                            updated = True
                        elif price_type == 'percentage_decrease':
                            part.price = part.price * (1 - price_value / 100)
                            updated = True
                        elif price_type == 'fixed_amount_increase':
                            part.price = part.price + price_value
                            updated = True
                        elif price_type == 'fixed_amount_decrease':
                            part.price = max(Decimal('0.01'), part.price - price_value)
                            updated = True
                        elif price_type == 'set_price':
                            part.price = price_value
                            updated = True
                    
                    # Quantity adjustments
                    quantity_type = form.cleaned_data.get('quantity_adjustment_type')
                    quantity_value = form.cleaned_data.get('quantity_adjustment_value')
                    
                    if quantity_type and quantity_value is not None:
                        if quantity_type == 'add':
                            part.quantity = part.quantity + quantity_value
                            updated = True
                        elif quantity_type == 'subtract':
                            part.quantity = max(0, part.quantity - quantity_value)
                            updated = True
                        elif quantity_type == 'set':
                            part.quantity = quantity_value
                            updated = True
                    
                    # Status updates
                    active_status = form.cleaned_data.get('set_active_status')
                    if active_status:
                        part.is_active = active_status == 'true'
                        updated = True
                    
                    featured_status = form.cleaned_data.get('set_featured_status')
                    if featured_status:
                        part.is_featured = featured_status == 'true'
                        updated = True
                    
                    # Vendor-specific updates
                    material_type = form.cleaned_data.get('update_material_type')
                    if material_type:
                        part.material_type = material_type
                        updated = True
                    
                    plant = form.cleaned_data.get('update_plant')
                    if plant:
                        part.plant = plant
                        updated = True
                    
                    material_group = form.cleaned_data.get('update_material_group')
                    if material_group:
                        part.material_group = material_group
                        updated = True
                    
                    if updated:
                        part.save()
                        updated_count += 1
            
            messages.success(request, f'Successfully updated {updated_count} parts.')
            return redirect('business_partners:vendor_parts_list')
        else:
            if not part_ids:
                messages.error(request, 'No parts selected for bulk update.')
            else:
                messages.error(request, 'Please correct the errors in the form.')
    else:
        form = VendorPartBulkUpdateForm()
    
    context = {
        'form': form,
        'vendor_profile': vendor_profile,
    }
    
    return render(request, 'business_partners/vendor_parts_bulk_update.html', context)


@login_required
def vendor_parts_export_csv(request):
    """
    Export vendor's parts to CSV with all Excel fields.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    business_partner = vendor_profile.business_partner
    
    # Get all vendor's parts
    parts = Part.objects.filter(vendor=business_partner)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="vendor_parts_{business_partner.name}.csv"'
    
    writer = csv.writer(response)
    
    # Write header row with all Excel fields
    header = [
        'Parts Number', 'Material Description', 'Material Description (AR)',
        'Base Unit of Measure', 'Gross Weight', 'Net Weight', 'Size Dimensions',
        'Manufacturer Part Number', 'Manufacturer OEM Number',
        'Material Type', 'Plant', 'Storage Location', 'Warehouse Number',
        'Material Group', 'Division', 'Minimum Order Quantity', 'Old Material Number',
        'Expiration XCHPF', 'External Material Group', 'ABC Indicator',
        'Safety Stock', 'Minimum Safety Stock', 'Planned Delivery Time (Days)',
        'Goods Receipt Processing Time (Days)', 'Valuation Class', 'Price Unit (PEINH)',
        'Moving Average Price', 'Category', 'Brand', 'Price', 'Quantity',
        'Warranty Period', 'Is Active', 'Is Featured', 'Created At', 'Updated At'
    ]
    writer.writerow(header)
    
    # Write data rows
    for part in parts:
        row = [
            part.parts_number or '',
            part.material_description or '',
            part.material_description_ar or '',
            part.base_unit_of_measure or '',
            part.gross_weight or '',
            part.net_weight or '',
            part.size_dimensions or '',
            part.manufacturer_part_number or '',
            part.manufacturer_oem_number or '',
            part.material_type or '',
            part.plant or '',
            part.storage_location or '',
            part.warehouse_number or '',
            part.material_group or '',
            part.division or '',
            part.minimum_order_quantity or '',
            part.old_material_number or '',
            part.expiration_xchpf or '',
            part.external_material_group or '',
            part.abc_indicator or '',
            part.safety_stock or '',
            part.minimum_safety_stock or '',
            part.planned_delivery_time_days or '',
            part.goods_receipt_processing_time_days or '',
            part.valuation_class or '',
            part.price_unit_peinh or '',
            part.moving_average_price or '',
            part.category.name if part.category else '',
            part.brand.name if part.brand else '',
            part.price or '',
            part.quantity or '',
            part.warranty_period or '',
            'Yes' if part.is_active else 'No',
            'Yes' if part.is_featured else 'No',
            part.created_at.strftime('%Y-%m-%d %H:%M:%S') if part.created_at else '',
            part.updated_at.strftime('%Y-%m-%d %H:%M:%S') if part.updated_at else '',
        ]
        writer.writerow(row)


@vendor_required
@require_http_methods(["POST"])
def vendor_parts_bulk_action(request):
    """
    Handle AJAX bulk actions on vendor parts from the parts list.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        return JsonResponse({'success': False, 'error': 'Access denied'})
    
    business_partner = vendor_profile.business_partner
    
    try:
        part_ids = request.POST.getlist('part_ids')
        action = request.POST.get('action')
        
        if not part_ids:
            return JsonResponse({'success': False, 'error': 'No parts selected'})
        
        # Get selected parts that belong to this vendor
        parts = Part.objects.filter(id__in=part_ids, vendor=business_partner)
        
        if not parts.exists():
            return JsonResponse({'success': False, 'error': 'No valid parts found'})
        
        updated_count = 0
        
        with transaction.atomic():
            if action == 'activate':
                parts.update(is_active=True)
                updated_count = parts.count()
                message = f'Activated {updated_count} parts'
                
            elif action == 'deactivate':
                parts.update(is_active=False)
                updated_count = parts.count()
                message = f'Deactivated {updated_count} parts'

            elif action == 'publish':
                parts.update(status='published')
                updated_count = parts.count()
                message = f'Published {updated_count} parts'

            elif action == 'draft':
                parts.update(status='draft')
                updated_count = parts.count()
                message = f'Set {updated_count} parts to draft'

            elif action == 'archive':
                parts.update(status='archived')
                updated_count = parts.count()
                message = f'Archived {updated_count} parts'

            elif action == 'feature':
                parts.update(is_featured=True)
                updated_count = parts.count()
                message = f'Featured {updated_count} parts'
                
            elif action == 'unfeature':
                parts.update(is_featured=False)
                updated_count = parts.count()
                message = f'Removed featured status from {updated_count} parts'
                
            elif action == 'delete':
                updated_count = parts.count()
                parts.delete()
                message = f'Deleted {updated_count} parts'
                
            elif action == 'update_price':
                # Price update with percentage
                percentage = float(request.POST.get('percentage', 0))
                if percentage != 0:
                    for part in parts:
                        adjustment_factor = Decimal(str(1 + (percentage / 100)))
                        part.price = part.price * adjustment_factor
                        part.save()
                        updated_count += 1
                    message = f'Updated prices for {updated_count} parts by {percentage}%'
                else:
                    return JsonResponse({'success': False, 'error': 'Invalid percentage value'})
                    
            elif action == 'update_stock':
                # Stock update
                stock_action = request.POST.get('stock_action', 'set')
                quantity = int(request.POST.get('quantity', 0))
                
                for part in parts:
                    if stock_action == 'set':
                        part.quantity = quantity
                    elif stock_action == 'add':
                        part.quantity += quantity
                    elif stock_action == 'subtract':
                        part.quantity = max(0, part.quantity - quantity)
                    part.save()
                    updated_count += 1
                    
                message = f'Updated stock for {updated_count} parts'
                
            else:
                return JsonResponse({'success': False, 'error': 'Invalid action'})
        
        return JsonResponse({
            'success': True,
            'message': message,
            'updated_count': updated_count
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def vendor_store_front(request, vendor_slug):
    """
    Public view for vendor store front - displays vendor information and their parts.
    Uses the same design patterns as the main parts catalog.
    """
    from parts.models import Part
    from parts.views import get_cached_categories, get_cached_brands
    from parts.forms import PartSearchForm
    from django.core.paginator import Paginator
    
    # Get vendor by slug
    try:
        vendor = BusinessPartner.objects.select_related('vendor_profile').get(
            slug=vendor_slug,
            roles__role_type='vendor',
            status='active'
        )
    except BusinessPartner.DoesNotExist:
        messages.error(request, 'Vendor not found.')
        return redirect('parts:part_list')
    
    # Get vendor's parts with same filtering as main catalog
    queryset = Part.objects.filter(
        vendor=vendor,
        is_active=True,
        status='published'
    ).select_related(
        'category', 'brand', 'dealer', 'inventory'
    ).prefetch_related(
        'reviews', 'cart_items'
    ).annotate(
        annotated_review_count=Count('reviews', filter=Q(reviews__is_approved=True)),
        avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True)),
        total_sales=Count('order_items')
    )
    
    # Apply same filters as main parts list
    search_query = request.GET.get('search')
    if search_query:
        queryset = queryset.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(sku__icontains=search_query) |
            Q(brand__name__icontains=search_query) |
            Q(parts_number__icontains=search_query) |
            Q(material_description__icontains=search_query) |
            Q(manufacturer_part_number__icontains=search_query)
        )
    
    # Category filter
    category_id = request.GET.get('category')
    if category_id:
        queryset = queryset.filter(category_id=category_id)
    
    categories = request.GET.getlist('categories')
    if categories:
        queryset = queryset.filter(category_id__in=categories)
    
    # Brand filter
    brand_id = request.GET.get('brand')
    if brand_id:
        queryset = queryset.filter(brand_id=brand_id)
    
    brands = request.GET.getlist('brands')
    if brands:
        queryset = queryset.filter(brand_id__in=brands)
    
    # Price range filter
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        queryset = queryset.filter(price__gte=min_price)
    if max_price:
        queryset = queryset.filter(price__lte=max_price)
    
    # Stock filter
    stock_filter = request.GET.get('stock_availability')
    if stock_filter == 'in_stock':
        queryset = queryset.filter(quantity__gt=0)
    elif stock_filter == 'pre_order':
        queryset = queryset.filter(quantity=0, is_active=True)
    
    # Legacy stock filters
    in_stock = request.GET.get('in_stock')
    if in_stock == 'true':
        queryset = queryset.filter(quantity__gt=0)
    
    # Featured filter
    featured = request.GET.get('featured')
    if featured == 'true':
        queryset = queryset.filter(is_featured=True)
    
    # Minimum rating filter
    min_rating = request.GET.get('min_rating')
    if min_rating:
        queryset = queryset.filter(avg_rating__gte=min_rating)
    
    # Sorting
    sort_by = request.GET.get('sort', '-created_at')
    if sort_by in ['name', '-name', 'price', '-price', 'created_at', '-created_at']:
        queryset = queryset.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(queryset, 12)
    page_number = request.GET.get('page')
    parts = paginator.get_page(page_number)
    
    # HTMX partial response for filtering
    if request.headers.get('HX-Request'):
        return render(request, 'parts/partials/parts_results.html', {'parts': parts})
    
    context = {
        'vendor': vendor,
        'parts': parts,
        'search_form': PartSearchForm(request.GET),
        'categories': get_cached_categories(),
        'brands': get_cached_brands(),
        'total_parts': queryset.count(),
        'view_type': 'vendor_store',  # For template conditionals
    }
    
    return render(request, 'business_partners/vendor_store_front.html', context)


@login_required
def vendor_reorder_notifications(request):
    """
    Display reorder notifications for the vendor.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    business_partner = vendor_profile.business_partner
    
    # Get filter parameters
    status_filter = request.GET.get('status', 'pending')
    priority_filter = request.GET.get('priority', '')
    
    # Base queryset
    notifications = ReorderNotification.objects.filter(
        vendor=business_partner
    ).select_related('part', 'acknowledged_by').order_by('-urgency_score', '-created_at')
    
    # Apply filters
    if status_filter and status_filter != 'all':
        notifications = notifications.filter(status=status_filter)
    
    if priority_filter and priority_filter != 'all':
        notifications = notifications.filter(priority=priority_filter)
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get statistics
    stats = {
        'total': ReorderNotification.objects.filter(vendor=business_partner).count(),
        'pending': ReorderNotification.objects.filter(vendor=business_partner, status='pending').count(),
        'acknowledged': ReorderNotification.objects.filter(vendor=business_partner, status='acknowledged').count(),
        'ordered': ReorderNotification.objects.filter(vendor=business_partner, status='ordered').count(),
        'critical': ReorderNotification.objects.filter(vendor=business_partner, priority='critical', status__in=['pending', 'acknowledged']).count(),
        'overdue': ReorderNotification.objects.filter(
            vendor=business_partner,
            status='pending',
            created_at__lt=timezone.now() - timedelta(days=7)
        ).count(),
    }
    
    context = {
        'vendor_profile': vendor_profile,
        'notifications': page_obj,
        'stats': stats,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'status_choices': ReorderNotification.STATUS_CHOICES,
        'priority_choices': ReorderNotification.PRIORITY_CHOICES,
    }
    
    return render(request, 'business_partners/vendor_reorder_notifications.html', context)


@login_required
@require_http_methods(["POST"])
def vendor_reorder_notification_action(request, notification_id):
    """
    Handle actions on reorder notifications (acknowledge, mark ordered, dismiss, etc.).
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        return JsonResponse({'success': False, 'error': 'Access denied'})
    
    business_partner = vendor_profile.business_partner
    
    try:
        notification = ReorderNotification.objects.get(
            id=notification_id,
            vendor=business_partner
        )
    except ReorderNotification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'})
    
    action = request.POST.get('action')
    
    if action == 'acknowledge':
        notification.acknowledge(request.user)
        return JsonResponse({
            'success': True,
            'message': 'Notification acknowledged',
            'new_status': notification.get_status_display()
        })
    
    elif action == 'mark_ordered':
        order_reference = request.POST.get('order_reference', '')
        expected_delivery = request.POST.get('expected_delivery')
        
        # Parse expected delivery date if provided
        expected_delivery_date = None
        if expected_delivery:
            try:
                from datetime import datetime
                expected_delivery_date = datetime.strptime(expected_delivery, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'success': False, 'error': 'Invalid date format'})
        
        notification.mark_ordered(order_reference, expected_delivery_date)
        return JsonResponse({
            'success': True,
            'message': 'Notification marked as ordered',
            'new_status': notification.get_status_display()
        })
    
    elif action == 'complete':
        notification.complete()
        return JsonResponse({
            'success': True,
            'message': 'Notification completed',
            'new_status': notification.get_status_display()
        })
    
    elif action == 'dismiss':
        notification.dismiss()
        return JsonResponse({
            'success': True,
            'message': 'Notification dismissed',
            'new_status': notification.get_status_display()
        })
    
    else:
        return JsonResponse({'success': False, 'error': 'Invalid action'})


@login_required
@require_http_methods(["POST"])
def vendor_bulk_reorder_action(request):
    """
    Handle bulk actions on multiple reorder notifications.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        return JsonResponse({'success': False, 'error': 'Access denied'})
    
    business_partner = vendor_profile.business_partner
    
    notification_ids = request.POST.getlist('notification_ids')
    action = request.POST.get('action')
    
    if not notification_ids:
        return JsonResponse({'success': False, 'error': 'No notifications selected'})
    
    # Get notifications
    notifications = ReorderNotification.objects.filter(
        id__in=notification_ids,
        vendor=business_partner
    )
    
    if not notifications.exists():
        return JsonResponse({'success': False, 'error': 'No valid notifications found'})
    
    count = 0
    
    if action == 'acknowledge':
        for notification in notifications:
            if notification.status == 'pending':
                notification.acknowledge(request.user)
                count += 1
    
    elif action == 'dismiss':
        for notification in notifications:
            if notification.status in ['pending', 'acknowledged']:
                notification.dismiss()
                count += 1
    
    else:
        return JsonResponse({'success': False, 'error': 'Invalid action'})
    
    return JsonResponse({
        'success': True,
        'message': f'{count} notifications {action}d successfully'
    })


@login_required
def vendor_reorder_notification_detail(request, notification_id):
    """
    Display detailed view of a reorder notification.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    business_partner = vendor_profile.business_partner
    
    try:
        notification = ReorderNotification.objects.select_related(
            'part', 'part__category', 'part__brand', 'acknowledged_by'
        ).get(
            id=notification_id,
            vendor=business_partner
        )
    except ReorderNotification.DoesNotExist:
        messages.error(request, 'Notification not found.')
        return redirect('business_partners:vendor_reorder_notifications')
    
    # Get part inventory information
    inventory = getattr(notification.part, 'inventory', None)
    
    # Get recent notifications for this part
    recent_notifications = ReorderNotification.objects.filter(
        part=notification.part,
        vendor=business_partner
    ).exclude(id=notification.id).order_by('-created_at')[:5]
    
    context = {
        'vendor_profile': vendor_profile,
        'notification': notification,
        'inventory': inventory,
        'recent_notifications': recent_notifications,
    }
    
    return render(request, 'business_partners/vendor_reorder_notification_detail.html', context)


@login_required
def vendor_inventory_alerts(request):
    """
    Show inventory alerts for low stock and out of stock items.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    business_partner = vendor_profile.business_partner
    
    # Get parts with stock issues
    out_of_stock = Part.objects.filter(vendor=business_partner, quantity=0, is_active=True)
    low_stock = Part.objects.filter(
        vendor=business_partner, 
        quantity__gt=0, 
        quantity__lte=10, 
        is_active=True
    )
    
    # Get parts below safety stock
    below_safety_stock = Part.objects.filter(
        vendor=business_partner,
        safety_stock__isnull=False,
        quantity__lt=models.F('safety_stock'),
        is_active=True
    )
    
    context = {
        'vendor_profile': vendor_profile,
        'out_of_stock': out_of_stock,
        'low_stock': low_stock,
        'below_safety_stock': below_safety_stock,
    }
    
    return render(request, 'business_partners/vendor_inventory_alerts.html', context)


@vendor_required
@login_required
def vendor_parts_import_template(request):
    """
    Generate a CSV template for bulk part import.
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="vendor_parts_import_template.csv"'
    
    writer = csv.writer(response)
    # Headers based on requested fields and order
    headers = [
        'Part Number',
        'Manufacturer Part Number',
        'OEM Number',
        'Material Description',
        'Arabic Description',
        'Category',
        'Make(Brand)',
        'PurChase Price',
        'Retail Price',
        'Whole Sale Price',
        'Base Unit',
        'Quantity',
        'Plant',
        'Warehouse',
        'Bin',
        'Safety Stock',
        'Reorder Point',
        'Active',
        'Featured',
        'Gross Weight',
        'Net Weight',
        'Dimensions',
        'Image URL',
    ]
    writer.writerow(headers)
    
    # Add a sample row
    writer.writerow([
        'PART-001',
        'MFG-123',
        'OEM-456',
        'Brake Pad Front',
        'تيل فرامل أمامي',
        'Brakes',
        'Toyota',
        '100.00',
        '150.00',
        '120.00',
        'EA',
        '50',
        'PLANT1',
        'WH01',
        'BIN-A1',
        '10',
        '5',
        'Yes',
        'No',
        '1.5',
        '1.4',
        '20x10x5',
        'https://example.com/image.jpg'
    ])
    
    return response


@login_required
def vendor_parts_import(request):
    """
    Handle bulk import of vendor parts from CSV/Excel files.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'You do not have vendor access.'}, status=403)
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    business_partner = vendor_profile.business_partner
    
    if request.method == 'POST':
        form = VendorPartBulkImportForm(request.POST, request.FILES)
        
        # Handle AJAX requests for invalid forms
        if not form.is_valid() and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            errors = {}
            for field, field_errors in form.errors.items():
                errors[field] = [str(error) for error in field_errors]
            
            return JsonResponse({
                'success': False,
                'message': 'Form validation failed',
                'errors': errors
            }, status=400)
        
        if form.is_valid():
            import_file = form.cleaned_data['file']
            import_status = form.cleaned_data.get('import_status') or 'published'
            update_existing = form.cleaned_data['update_existing']
            validate_only = form.cleaned_data['validate_only']
            chunk_size = form.cleaned_data.get('chunk_size') or 5000
            
            try:
                if validate_only:
                    with transaction.atomic():
                        results = process_import_file(
                            import_file,
                            business_partner,
                            import_status,
                            update_existing,
                            validate_only=True,
                            user=request.user
                        )
                        
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return JsonResponse({
                                'success': True,
                                'message': f'Validation complete. {results["valid_count"]} valid rows, {results["error_count"]} errors.',
                                'results': results
                            })
                        
                        messages.info(
                            request,
                            f'Validation complete. {results["valid_count"]} valid rows, {results["error_count"]} errors.',
                        )
                        transaction.set_rollback(True)

                    request.session['import_results'] = results
                    if results.get('error_count', 0) > 0:
                        return redirect('business_partners:vendor_parts_import_results')
                    return redirect('business_partners:vendor_parts_import')

                # Force synchronous processing to avoid Celery/Redis issues
                # Synchronous processing for all batches
                results = process_import_file_sync(
                    import_file=import_file,
                    business_partner=business_partner,
                    import_status=import_status,
                    update_existing=update_existing,
                    validate_only=False,
                    chunk_size=chunk_size,
                    user=request.user
                )
                
                # Store results in session for results page
                request.session['import_results'] = results
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    messages.success(request, f'Import completed! {results["created_count"]} created, {results["updated_count"]} updated, {results["error_count"]} errors.')
                    return JsonResponse({
                        'success': True,
                        'message': f'Import completed! {results["created_count"]} created, {results["updated_count"]} updated, {results["error_count"]} errors.',
                        'results': results
                    })
                
                messages.success(request, 
                    f'Import completed! {results["created_count"]} created, '
                    f'{results["updated_count"]} updated, {results["error_count"]} errors.'
                )
                if results.get('error_count', 0) > 0:
                    return redirect('business_partners:vendor_parts_import_results')
                return redirect('business_partners:vendor_parts_import')
                
            except Exception as e:
                import traceback
                print(traceback.format_exc())
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': f'System Error during import: {str(e)}'
                    }, status=500)
                
                messages.error(request, f'System Error during import: {str(e)}')
    else:
        form = VendorPartBulkImportForm()
    
    from parts.models import BulkUploadLog
    recent_uploads = BulkUploadLog.objects.filter(user=request.user).order_by('-uploaded_at')[:10]

    context = {
        'vendor_profile': vendor_profile,
        'form': form,
        'recent_uploads': recent_uploads,
    }

    # Add results from session if available (for success cases)
    results = request.session.get('import_results')
    if results:
        context['results'] = results
        # Clear results from session so they don't persist on refresh
        del request.session['import_results']

    return render(request, 'business_partners/bulk_import.html', context)


@login_required
def vendor_parts_import_results(request):
    """
    Display results of the bulk import operation.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    job_id = request.GET.get('job')
    if job_id:
        from parts.models import BulkUploadLog
        from django.utils import timezone

        upload_log = BulkUploadLog.objects.filter(id=job_id, user=request.user).first()
        if not upload_log:
            messages.warning(request, 'Import job not found.')
            return redirect('business_partners:vendor_parts_import')

        error_lines = []
        if upload_log.error_log:
            error_lines = [line for line in upload_log.error_log.splitlines() if line][:200]

        job_age_seconds = 0
        if upload_log.uploaded_at:
            job_age_seconds = int((timezone.now() - upload_log.uploaded_at).total_seconds())

        job_queued_too_long = False
        if upload_log.status == 'processing':
            msg = (upload_log.success_message or '').strip()
            if msg.startswith('Queued') and job_age_seconds >= 180:
                job_queued_too_long = True

        context = {
            'vendor_profile': vendor_profile,
            'job': upload_log,
            'job_errors': error_lines,
            'job_age_seconds': job_age_seconds,
            'job_queued_too_long': job_queued_too_long,
        }
        return render(request, 'business_partners/vendor_parts_import_results.html', context)

    results = request.session.get('import_results', {})
    if not results:
        messages.warning(request, 'No import results found.')
        return redirect('business_partners:vendor_parts_import')

    if 'import_results' in request.session:
        del request.session['import_results']

    context = {
        'vendor_profile': vendor_profile,
        'results': results,
    }

    return render(request, 'business_partners/vendor_parts_import_results.html', context)


@login_required
def vendor_parts_export(request):
    """
    Handle export of vendor parts to CSV/Excel files.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    business_partner = vendor_profile.business_partner
    
    if request.method == 'POST':
        form = VendorPartExportForm(request.POST)
        if form.is_valid():
            export_format = form.cleaned_data['export_format']
            include_inactive = form.cleaned_data['include_inactive']
            include_images = form.cleaned_data['include_images']
            date_from = form.cleaned_data['date_from']
            date_to = form.cleaned_data['date_to']
            
            # Build queryset
            queryset = Part.objects.filter(vendor=business_partner)
            
            if not include_inactive:
                queryset = queryset.filter(is_active=True)
            
            if date_from:
                queryset = queryset.filter(created_at__gte=date_from)
            
            if date_to:
                queryset = queryset.filter(created_at__lte=date_to)
            
            # Generate export file
            if export_format == 'csv':
                return generate_csv_export(queryset, include_images)
            else:
                return generate_excel_export(queryset, include_images)
    else:
        form = VendorPartExportForm()
    
    context = {
        'vendor_profile': vendor_profile,
        'form': form,
    }
    
    return render(request, 'business_partners/vendor_parts_export.html', context)


def process_import_file(
    import_file,
    business_partner,
    import_status,
    update_existing,
    validate_only,
    *,
    upload_log_id=None,
    chunk_size=5000,
    user=None,
):
    """
    Process CSV or Excel import file and create/update parts with comprehensive validation.
    """
    import csv
    import io
    from decimal import Decimal, InvalidOperation
    from django.utils.dateparse import parse_date
    from django.utils import timezone
    from django.core.validators import URLValidator
    from django.core.exceptions import ValidationError
    import hashlib
    import os
    from django.utils.text import slugify
    
    results = {
        'total_rows': 0,
        'valid_count': 0,
        'error_count': 0,
        'created_count': 0,
        'updated_count': 0,
        'errors': [],
        'warnings': [],
        'field_errors': {},  # Track errors by field type
        'validation_summary': {}
    }
    
    # Define field validation rules
    REQUIRED_FIELDS = [
        'parts_number',
        'category_name',
        'brand_name',
        'manufacturer_part_number',
        'manufacturer_oem_number',
        'plant',
    ]
    VALIDATION_FIELDS = set(REQUIRED_FIELDS)
    
    # Map Excel/CSV headers to model fields
    HEADER_MAPPINGS = {
        'Part Number': 'parts_number',
        'Part No': 'parts_number',
        'Manufacturer Part Number': 'manufacturer_part_number',
        'MPN': 'manufacturer_part_number',
        'OEM Number': 'manufacturer_oem_number',
        'OEM': 'manufacturer_oem_number',
        'Material Description': 'material_description',
        'Description': 'material_description',
        'Arabic Description': 'material_description_ar',
        'Category': 'category_name',
        'Make': 'brand_name',
        'Make(Brand)': 'brand_name',
        'Brand': 'brand_name',
        'Purchase Price': 'moving_average_price',
        'PurChase Price': 'moving_average_price',
        'Retail Price': 'standard_price',
        'Whole Sale Price': 'price',
        'Wholesale Price': 'price',
        'Price': 'price',
        'Base Unit': 'base_unit_of_measure',
        'Unit': 'base_unit_of_measure',
        'UOM': 'base_unit_of_measure',
        'Quantity': 'quantity',
        'Qty': 'quantity',
        'Stock': 'quantity',
        'Plant': 'plant',
        'Storage Location': 'storage_location',
        'Storage Loc': 'storage_location',
        'Location': 'storage_location',
        'Warehouse': 'warehouse_number',
        'Warehouse Number': 'warehouse_number',
        'Bin': 'storage_bin',
        'Safety Stock': 'safety_stock',
        'Reorder Point': 'reorder_point',
        'Active': 'is_active',
        'Featured': 'is_featured',
        'Gross Weight': 'gross_weight',
        'Weight': 'gross_weight',
        'Net Weight': 'net_weight',
        'Dimensions': 'size_dimensions',
        'Size': 'size_dimensions',
        'Image URL': 'image_url',
        'Image': 'image_url',
    }
    
    FIELD_MAPPINGS = {
        'parts_number': 'parts_number',
        'material_description': 'material_description',
        'material_description_ar': 'material_description_ar',
        'image_url': 'image_url',
        'size_dimensions': 'size_dimensions',
        'price': 'price',
        'moving_average_price': 'moving_average_price',
        'standard_price': 'standard_price',
        'storage_location': 'storage_location',
        'warehouse_number': 'warehouse_number',
    }
    
    NUMERIC_FIELDS = {
        'price': {'min': 0, 'max': 99999999.99, 'decimal_places': 2},
        'standard_price': {'min': 0, 'max': 99999999.99, 'decimal_places': 2},
        'moving_average_price': {'min': 0, 'max': 99999999.99, 'decimal_places': 2},
        'quantity': {'min': 0, 'max': 9999999, 'decimal_places': 0},
        'safety_stock': {'min': 0, 'max': 9999999, 'decimal_places': 3},
        'reorder_point': {'min': 0, 'max': 9999999, 'decimal_places': 3},
        'gross_weight': {'min': 0, 'max': 99999.999, 'decimal_places': 3},
        'net_weight': {'min': 0, 'max': 99999.999, 'decimal_places': 3},
        'minimum_safety_stock': {'min': 0, 'max': 9999999, 'decimal_places': 3},
        'minimum_order_quantity': {'min': 0, 'max': 9999999, 'decimal_places': 3},
        'planned_delivery_time_days': {'min': 0, 'max': 365, 'decimal_places': 0},
        'goods_receipt_processing_time_days': {'min': 0, 'max': 30, 'decimal_places': 0},
        'warranty_period': {'min': 0, 'max': 120, 'decimal_places': 0},
        'price_unit_peinh': {'min': 1, 'max': 99999, 'decimal_places': 0}
    }
    
    STRING_FIELDS = {
        'parts_number': {'max_length': 50},
        'material_description': {'max_length': 200},
        'material_description_ar': {'max_length': 200},
        'base_unit_of_measure': {'max_length': 10},
        'size_dimensions': {'max_length': 100},
        'manufacturer_part_number': {'max_length': 40},
        'manufacturer_oem_number': {'max_length': 50},
        'material_type': {'max_length': 50},
        'plant': {'max_length': 100},
        'storage_location': {'max_length': 100},
        'warehouse_number': {'max_length': 100},
        'storage_bin': {'max_length': 20},
        'material_group': {'max_length': 20},
        'division': {'max_length': 10},
        'old_material_number': {'max_length': 50},
        'external_material_group': {'max_length': 20},
        'abc_indicator': {'max_length': 1, 'choices': ['A', 'B', 'C']},
        'mrp_type': {'max_length': 10},
        'mrp_group': {'max_length': 10},
        'mrp_controller': {'max_length': 10},
        'valuation_class': {'max_length': 10},
        'price_control_indicator': {'max_length': 1},
        'storage_location_code': {'max_length': 10}
    }
    
    BOOLEAN_FIELDS = ['is_active', 'is_featured']
    DATE_FIELDS = ['expiration_xchpf']
    URL_FIELDS = ['image_url']

    def validate_field(field_name, value, row_num):
        """Validate individual field with comprehensive rules"""
        errors = []
        
        if not value or (isinstance(value, str) and not value.strip()):
            if field_name in REQUIRED_FIELDS:
                errors.append(f"Row {row_num}: {field_name} is required")
            return errors, None
        
        # Clean string value
        if isinstance(value, str):
            value = value.strip()
        
        # Validate string fields
        if field_name in STRING_FIELDS:
            rules = STRING_FIELDS[field_name]
            if len(str(value)) > rules['max_length']:
                errors.append(f"Row {row_num}: {field_name} exceeds maximum length of {rules['max_length']} characters")
            
            if 'choices' in rules and value not in rules['choices']:
                errors.append(f"Row {row_num}: {field_name} must be one of: {', '.join(rules['choices'])}")
        
        # Validate numeric fields
        elif field_name in NUMERIC_FIELDS:
            rules = NUMERIC_FIELDS[field_name]
            try:
                decimal_value = Decimal(str(value))
                if decimal_value < rules['min'] or decimal_value > rules['max']:
                    errors.append(f"Row {row_num}: {field_name} must be between {rules['min']} and {rules['max']}")
                
                # Check decimal places
                if rules['decimal_places'] == 0 and decimal_value != int(decimal_value):
                    errors.append(f"Row {row_num}: {field_name} must be a whole number")
                
                value = decimal_value
            except (InvalidOperation, ValueError):
                errors.append(f"Row {row_num}: {field_name} must be a valid number")
                return errors, None
        
        # Validate boolean fields
        elif field_name in BOOLEAN_FIELDS:
            if isinstance(value, str):
                value_lower = value.lower()
                if value_lower in ['yes', 'true', '1', 'y', 'on']:
                    value = True
                elif value_lower in ['no', 'false', '0', 'n', 'off', '']:
                    value = False
                else:
                    errors.append(f"Row {row_num}: {field_name} must be TRUE/FALSE, YES/NO, or 1/0")
                    return errors, None
        
        # Validate date fields
        elif field_name in DATE_FIELDS:
            try:
                parsed_date = parse_date(str(value))
                if not parsed_date:
                    errors.append(f"Row {row_num}: {field_name} must be in YYYY-MM-DD format")
                    return errors, None
                value = parsed_date
            except (ValueError, TypeError):
                errors.append(f"Row {row_num}: {field_name} must be a valid date in YYYY-MM-DD format")
                return errors, None
        
        # Validate URL fields
        elif field_name in URL_FIELDS:
            validator = URLValidator()
            try:
                validator(value)
            except ValidationError:
                errors.append(f"Row {row_num}: {field_name} must be a valid URL")
        
        return errors, value

    def normalize_row(row):
        normalized_row = {}
        for key, value in row.items():
            if key is None:
                continue

            key_str = str(key).strip()
            mapped_key = None

            if key_str in HEADER_MAPPINGS:
                mapped_key = HEADER_MAPPINGS[key_str]
            else:
                for header, field in HEADER_MAPPINGS.items():
                    if header.lower() == key_str.lower():
                        mapped_key = field
                        break

            if not mapped_key:
                clean_key = key_str.lower().replace(' ', '_')
                all_known_fields = (
                    set(REQUIRED_FIELDS)
                    | set(NUMERIC_FIELDS.keys())
                    | set(STRING_FIELDS.keys())
                    | set(BOOLEAN_FIELDS)
                    | set(DATE_FIELDS)
                    | set(URL_FIELDS)
                )

                if clean_key in all_known_fields:
                    mapped_key = clean_key
                else:
                    mapped_key = key_str

            normalized_row[mapped_key] = value

        return normalized_row

    def coerce_optional_value(field_name, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
        if field_name in NUMERIC_FIELDS:
            rules = NUMERIC_FIELDS[field_name]
            try:
                decimal_value = Decimal(str(value))
            except (InvalidOperation, ValueError):
                return None
            if rules['decimal_places'] == 0:
                try:
                    return int(decimal_value)
                except Exception:
                    return None
            return decimal_value
        if field_name in BOOLEAN_FIELDS:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                value_lower = value.lower()
                if value_lower in ['yes', 'true', '1', 'y', 'on']:
                    return True
                if value_lower in ['no', 'false', '0', 'n', 'off', '']:
                    return False
            return None
        if isinstance(value, str):
            return value
        return value

    def iter_normalized_rows(file_obj):
        file_name = getattr(file_obj, 'name', '') or ''
        ext = os.path.splitext(file_name)[1].lower().lstrip('.')

        base_file = getattr(file_obj, 'file', file_obj)
        try:
            base_file.seek(0)
        except Exception:
            pass

        if ext == 'csv':
            text_stream = io.TextIOWrapper(base_file, encoding='utf-8-sig', newline='')
            reader = csv.DictReader(text_stream)
            for row in reader:
                yield normalize_row(row)
            return

        if ext == 'xlsx':
            try:
                import openpyxl
            except ImportError:
                raise Exception("openpyxl library is required for Excel file processing")

            workbook = openpyxl.load_workbook(base_file, read_only=True, data_only=True)
            worksheet = workbook.active

            header_row = next(worksheet.iter_rows(min_row=1, max_row=1, values_only=True), None)
            headers = [h for h in (header_row or [])]

            for values in worksheet.iter_rows(min_row=2, values_only=True):
                row_dict = dict(zip(headers, values))
                yield normalize_row(row_dict)
            return

        raise Exception("Unsupported file format. Please use CSV or XLSX files.")

    def make_part_slug(vendor_id, parts_number):
        base = slugify(f'{vendor_id}-{parts_number}')
        digest = hashlib.md5(f'{vendor_id}:{parts_number}'.encode('utf-8'), usedforsecurity=False).hexdigest()[:10]
        if not base:
            base = digest
        slug = f'{base}-{digest}'
        return slug[:250]

    def add_limited(target_list, new_items, limit):
        if not new_items or len(target_list) >= limit:
            return
        remaining = limit - len(target_list)
        target_list.extend(new_items[:remaining])

    try:
        for field in REQUIRED_FIELDS + list(NUMERIC_FIELDS.keys()) + list(STRING_FIELDS.keys()) + BOOLEAN_FIELDS + DATE_FIELDS + URL_FIELDS:
            results['field_errors'][field] = 0
        
        category_cache = {}
        brand_cache = {}

        buffered_rows = []
        max_errors_to_keep = 1000
        max_warnings_to_keep = 1000
        try:
            chunk_size = int(chunk_size)
        except Exception:
            chunk_size = 5000
        if chunk_size < 500:
            chunk_size = 500
        if chunk_size > 50000:
            chunk_size = 50000

        upload_log = None
        if upload_log_id:
            try:
                from parts.models import BulkUploadLog

                upload_log = BulkUploadLog.objects.filter(id=upload_log_id).first()
            except Exception:
                upload_log = None

        # Pre-fetch locations for validation
        vendor_employee = None
        employee_locations_dict = {} # {plant_name_or_id: [storage_location_name_or_id, ...]}
        
        if user:
            vendor_employee = getattr(user, 'vendor_employee', None)
            if vendor_employee and vendor_employee.is_active:
                from vendor_employees.models import VendorLocation, StorageLocation
                assigned_locations = vendor_employee.locations.filter(is_active=True).prefetch_related('storage_locations')
                for loc in assigned_locations:
                    # Map by both ID and Name for flexible matching
                    storage_locs = [str(sl.id) for sl in loc.storage_locations.filter(is_active=True)] + \
                                  [sl.name for sl in loc.storage_locations.filter(is_active=True)]
                    
                    employee_locations_dict[str(loc.id)] = storage_locs
                    employee_locations_dict[loc.name] = storage_locs
            else:
                # If not an employee, but a master vendor, we might still want to validate locations 
                # belong to the business partner.
                from vendor_employees.models import VendorLocation, StorageLocation
                all_vendor_locations = VendorLocation.objects.filter(vendor=business_partner, is_active=True).prefetch_related('storage_locations')
                for loc in all_vendor_locations:
                    storage_locs = [str(sl.id) for sl in loc.storage_locations.filter(is_active=True)] + \
                                  [sl.name for sl in loc.storage_locations.filter(is_active=True)]
                    employee_locations_dict[str(loc.id)] = storage_locs
                    employee_locations_dict[loc.name] = storage_locs

        def flush_buffer():
            if not buffered_rows or validate_only:
                buffered_rows.clear()
                return

            try:
                parts_numbers = [item['validated_data']['parts_number'] for item in buffered_rows if item['validated_data'].get('parts_number')]
                existing_by_parts_number = {}
                if parts_numbers:
                    for p in Part.objects.filter(vendor=business_partner, parts_number__in=parts_numbers):
                        existing_by_parts_number[p.parts_number] = p

                to_create = []
                to_update = []
                update_fields = set()

                for item in buffered_rows:
                    row_num = item['row_num']
                    validated_data = item['validated_data']

                    parts_number = validated_data.get('parts_number')
                    if not parts_number:
                        continue

                    existing_part = existing_by_parts_number.get(parts_number)
                    if existing_part and not update_existing:
                        add_limited(results['warnings'], [f"Row {row_num}: Part {parts_number} already exists (skipped)"], max_warnings_to_keep)
                        continue

                    status_value = validated_data.get('status')
                    if status_value not in ['draft', 'published', 'archived']:
                        validated_data['status'] = 'published'

                    if existing_part:
                        for key, value in validated_data.items():
                            if key in ['id', 'vendor', 'parts_number', 'slug']:
                                continue
                            setattr(existing_part, key, value)
                            update_fields.add(key)
                        existing_part.updated_at = timezone.now()
                        update_fields.add('updated_at')
                        to_update.append(existing_part)
                        results['updated_count'] += 1
                    else:
                        material_desc = validated_data.get('material_description') or ''
                        validated_data.setdefault('name', material_desc)
                        validated_data.setdefault('sku', parts_number)
                        validated_data.setdefault('description', material_desc)
                        validated_data['slug'] = make_part_slug(business_partner.id, parts_number)
                        to_create.append(Part(**validated_data))
                        results['created_count'] += 1

                if to_create:
                    Part.objects.bulk_create(to_create, batch_size=min(len(to_create), chunk_size))
                if to_update and update_fields:
                    Part.objects.bulk_update(to_update, fields=sorted(update_fields), batch_size=min(len(to_update), chunk_size))

                buffered_rows.clear()
                if upload_log:
                    BulkUploadLog.objects.filter(id=upload_log.id).update(
                        total_records=results['total_rows'],
                        successful_records=results['created_count'] + results['updated_count'],
                        failed_records=results['error_count'],
                        success_message=f'Writing ({results["created_count"] + results["updated_count"]} saved)',
                    )
            
            except Exception as e:
                # Handle errors in the final batch processing
                error_msg = f"Error processing final batch: {str(e)}"
                add_limited(results['errors'], [error_msg], max_errors_to_keep)
                results['error_count'] += 1
                
                # Try to process rows individually to identify the problematic row
                for item in buffered_rows:
                    try:
                        row_num = item['row_num']
                        validated_data = item['validated_data']
                        
                        parts_number = validated_data.get('parts_number')
                        if not parts_number:
                            continue
                        
                        # Try to create/update individual part
                        existing_part = Part.objects.filter(vendor=business_partner, parts_number=parts_number).first()
                        
                        if existing_part and not update_existing:
                            add_limited(results['warnings'], [f"Row {row_num}: Part {parts_number} already exists (skipped)"], max_warnings_to_keep)
                            continue
                        
                        if existing_part:
                            for key, value in validated_data.items():
                                if key in ['id', 'vendor', 'parts_number', 'slug']:
                                    continue
                                setattr(existing_part, key, value)
                            existing_part.updated_at = timezone.now()
                            existing_part.save()
                            results['updated_count'] += 1
                        else:
                            material_desc = validated_data.get('material_description') or ''
                            validated_data.setdefault('name', material_desc)
                            validated_data.setdefault('sku', parts_number)
                            validated_data.setdefault('description', material_desc)
                            validated_data['slug'] = make_part_slug(business_partner.id, parts_number)
                            Part.objects.create(**validated_data)
                            results['created_count'] += 1
                            
                    except Exception as row_error:
                        error_msg = f"Row {row_num}: Failed to process - {str(row_error)}"
                        add_limited(results['errors'], [error_msg], max_errors_to_keep)
                        results['error_count'] += 1
                
                buffered_rows.clear()

        for row_num, row in enumerate(iter_normalized_rows(import_file), start=2):
            row_errors = []
            row_warnings = []
            validated_data = {}
            
            try:
                results['total_rows'] += 1
                if upload_log and (results['total_rows'] % 200 == 0):
                    try:
                        from parts.models import BulkUploadLog

                        BulkUploadLog.objects.filter(id=upload_log.id).update(
                            total_records=results['total_rows'],
                            successful_records=results['created_count'] + results['updated_count'],
                            failed_records=results['error_count'],
                            success_message=f'Validating ({results["total_rows"]} rows)',
                        )
                    except Exception:
                        pass

                # Validate all fields
                for field_name, raw_value in row.items():
                    if not field_name:
                        continue
                    if field_name in VALIDATION_FIELDS:
                        field_errors, validated_value = validate_field(field_name, raw_value, row_num)
                        row_errors.extend(field_errors)

                        if field_errors:
                            results['field_errors'][field_name] = results['field_errors'].get(field_name, 0) + len(field_errors)

                        if validated_value is not None:
                            mapped_field = FIELD_MAPPINGS.get(field_name, field_name)
                            validated_data[mapped_field] = validated_value
                        continue

                    coerced_value = coerce_optional_value(field_name, raw_value)
                    if coerced_value is not None:
                        mapped_field = FIELD_MAPPINGS.get(field_name, field_name)
                        validated_data[mapped_field] = coerced_value
                
                # Special validation for required fields missing from the file
                for required_field in REQUIRED_FIELDS:
                    if required_field not in row:
                        row_errors.append(f"Row {row_num}: {required_field} is required")
                        results['field_errors'][required_field] = results['field_errors'].get(required_field, 0) + 1
                
                # Validate category and brand existence
                if 'category_name' in validated_data:
                    category_val = validated_data['category_name']
                    cache_key = str(category_val).strip().lower()
                    if cache_key not in category_cache:
                        category = Category.objects.filter(name__iexact=category_val).first()
                        # If multiple categories exist with same name (unlikely but possible), 
                        # we should try to be as exact as possible.
                        if not category:
                            # Fallback to a more broad search or handle error
                            category = Category.objects.filter(name__icontains=category_val).first()
                        category_cache[cache_key] = category
                    category = category_cache[cache_key]
                    if category:
                        validated_data['category'] = category
                        del validated_data['category_name']
                    else:
                        row_errors.append(f"Row {row_num}: Category '{validated_data['category_name']}' not found")
                        results['field_errors']['category_name'] = results['field_errors'].get('category_name', 0) + 1
                
                if 'brand_name' in validated_data:
                    brand_val = validated_data['brand_name']
                    cache_key = str(brand_val).strip().lower()
                    if cache_key not in brand_cache:
                        brand_cache[cache_key] = Brand.objects.filter(name__iexact=brand_val).first()
                    brand = brand_cache[cache_key]
                    if brand:
                        validated_data['brand'] = brand
                        del validated_data['brand_name']
                    else:
                        row_errors.append(f"Row {row_num}: Brand '{validated_data['brand_name']}' not found")
                        results['field_errors']['brand_name'] = results['field_errors'].get('brand_name', 0) + 1
                
                # Validate Plant and Storage Location assignments
                if employee_locations_dict:
                    plant_val = str(validated_data.get('plant', '')).strip()
                    storage_loc_val = str(validated_data.get('storage_location', '')).strip()
                    
                    if plant_val:
                        if plant_val not in employee_locations_dict:
                            row_errors.append(f"Row {row_num}: Plant '{plant_val}' is not assigned to you")
                        else:
                            # Plant is valid, check storage location or warehouse number
                            allowed_storage_locs = employee_locations_dict[plant_val]
                            
                            # Check if either storage_location OR warehouse_number matches assigned locations
                            # (User mentioned warehouse_number/storage_location both are same)
                            location_matched = False
                            
                            if storage_loc_val and storage_loc_val in allowed_storage_locs:
                                location_matched = True
                            
                            warehouse_val = str(validated_data.get('warehouse_number', '')).strip()
                            if not location_matched and warehouse_val and warehouse_val in allowed_storage_locs:
                                location_matched = True
                            
                            # If neither matches and we have values, it's an error
                            if (storage_loc_val or warehouse_val) and not location_matched:
                                if storage_loc_val:
                                    row_errors.append(f"Row {row_num}: Storage Location '{storage_loc_val}' is not assigned to you for Plant '{plant_val}'")
                                if warehouse_val:
                                    row_errors.append(f"Row {row_num}: Warehouse Number '{warehouse_val}' is not assigned to you for Plant '{plant_val}'")
                elif user:
                    # If user is provided but no locations found (e.g., employee with no assigned locations)
                    row_errors.append(f"Row {row_num}: You do not have any locations assigned to perform this upload")
                
                # Business logic validations
                if 'safety_stock' in validated_data and 'quantity' in validated_data:
                    if validated_data['safety_stock'] > validated_data['quantity']:
                        row_warnings.append(f"Row {row_num}: Safety stock is higher than current quantity")
                
                if 'reorder_point' in validated_data and 'safety_stock' in validated_data:
                    if validated_data['reorder_point'] < validated_data['safety_stock']:
                        row_warnings.append(f"Row {row_num}: Reorder point should be higher than safety stock")
                
                # Add vendor to validated data
                validated_data['vendor'] = business_partner
                validated_data['original_currency'] = getattr(getattr(business_partner, 'vendor_profile', None), 'preferred_currency', None) or 'USD'
                if import_status in ['draft', 'published', 'archived']:
                    validated_data['status'] = import_status
                
                # If there are errors, skip this row
                if row_errors:
                    add_limited(results['errors'], row_errors, max_errors_to_keep)
                    results['error_count'] += 1
                    continue
                
                # Add warnings to results
                if row_warnings:
                    add_limited(results['warnings'], row_warnings, max_warnings_to_keep)

                results['valid_count'] += 1
                buffered_rows.append({'row_num': row_num, 'validated_data': validated_data})
                if len(buffered_rows) >= chunk_size:
                    flush_buffer()
                
            except Exception as e:
                error_msg = f"Row {row_num}: Unexpected error - {str(e)}"
                add_limited(results['errors'], [error_msg], max_errors_to_keep)
                results['error_count'] += 1

        flush_buffer()
        if upload_log:
            from parts.models import BulkUploadLog

            BulkUploadLog.objects.filter(id=upload_log.id).update(
                total_records=results['total_rows'],
                successful_records=results['created_count'] + results['updated_count'],
                failed_records=results['error_count'],
                success_message=f'Done (created {results["created_count"]}, updated {results["updated_count"]})',
            )
        
        # Generate validation summary
        results['validation_summary'] = {
            'total_processed': results['total_rows'],
            'success_rate': (results['valid_count'] / results['total_rows'] * 100) if results['total_rows'] > 0 else 0,
            'most_common_errors': sorted(results['field_errors'].items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    except Exception as e:
        results['errors'].append(f"File processing error: {str(e)}")
        results['error_count'] += 1
    
    return results


def generate_excel_export(queryset, include_images):
    """
    Generate Excel export of parts data.
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill
        from django.http import HttpResponse
        import io
        
        # Create workbook and worksheet
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = "Vendor Parts"
        
        # Define headers
        headers = [
            'Part Number', 'Name', 'Description', 'Material Type', 'Plant',
            'Material Group', 'Purchasing Group', 'Base Unit of Measure',
            'Purchase Order Unit', 'Order Unit', 'Numerator for Conversion',
            'Denominator for Conversion', 'Gross Weight', 'Net Weight',
            'Weight Unit', 'Volume', 'Volume Unit', 'Size/Dimensions',
            'EAN/UPC', 'Manufacturer Part Number', 'Old Material Number',
            'Planned Delivery Time (Days)', 'Goods Receipt Processing Time (Days)',
            'Valuation Class', 'Price Unit (PEINH)', 'Moving Average Price',
            'Category', 'Brand', 'Price', 'Quantity', 'Safety Stock',
            'Reorder Point', 'Warranty Period', 'Active', 'Featured',
            'Created At', 'Updated At'
        ]
        
        if include_images:
            headers.append('Image URL')
        
        # Add headers to worksheet
        for col, header in enumerate(headers, 1):
            cell = worksheet.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
        
        # Add data rows
        for row_num, part in enumerate(queryset, 2):
            data = [
                part.parts_number,
                part.material_description,
                part.description or '',
                part.material_type or '',
                part.plant or '',
                part.material_group or '',
                part.purchasing_group or '',
                part.base_unit_of_measure or '',
                part.purchase_order_unit or '',
                part.order_unit or '',
                part.numerator_for_conversion or '',
                part.denominator_for_conversion or '',
                part.gross_weight or '',
                part.net_weight or '',
                part.weight_unit or '',
                part.volume or '',
                part.volume_unit or '',
                part.size_dimensions or '',
                part.ean_upc or '',
                part.manufacturer_part_number or '',
                part.old_material_number or '',
                part.planned_delivery_time_days or '',
                part.goods_receipt_processing_time_days or '',
                part.valuation_class or '',
                part.price_unit_peinh or '',
                part.moving_average_price or '',
                part.category.name if part.category else '',
                part.brand.name if part.brand else '',
                float(part.price) if part.price else '',
                int(part.quantity) if part.quantity else '',
                int(part.safety_stock) if part.safety_stock else '',
                int(part.reorder_point) if part.reorder_point else '',
                part.warranty_period or '',
                'Yes' if part.is_active else 'No',
                'Yes' if part.is_featured else 'No',
                part.created_at.strftime('%Y-%m-%d %H:%M:%S') if part.created_at else '',
                part.updated_at.strftime('%Y-%m-%d %H:%M:%S') if part.updated_at else '',
            ]
            
            if include_images:
                image_url = part.image.url if part.image else ''
                data.append(image_url)
            
            for col, value in enumerate(data, 1):
                worksheet.cell(row=row_num, column=col, value=value)
        
        # Auto-adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
        
        # Save to response
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="vendor_parts_export.xlsx"'
        
        # Save workbook to response
        workbook.save(response)
        return response
        
    except ImportError:
        # Fallback to CSV if openpyxl is not available
        return generate_csv_export(queryset, include_images)


def generate_csv_export(queryset, include_images):
    """
    Generate CSV export of parts data (enhanced version of existing function).
    """
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="vendor_parts_export.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    headers = [
        'Part Number', 'Name', 'Description', 'Material Type', 'Plant',
        'Material Group', 'Purchasing Group', 'Base Unit of Measure',
        'Purchase Order Unit', 'Order Unit', 'Numerator for Conversion',
        'Denominator for Conversion', 'Gross Weight', 'Net Weight',
        'Weight Unit', 'Volume', 'Volume Unit', 'Size/Dimensions',
        'EAN/UPC', 'Manufacturer Part Number', 'Old Material Number',
        'Planned Delivery Time (Days)', 'Goods Receipt Processing Time (Days)',
        'Valuation Class', 'Price Unit (PEINH)', 'Moving Average Price',
        'Category', 'Brand', 'Price', 'Quantity', 'Safety Stock',
        'Reorder Point', 'Warranty Period', 'Active', 'Featured',
        'Created At', 'Updated At'
    ]
    
    if include_images:
        headers.append('Image URL')
    
    writer.writerow(headers)
    
    # Write data rows
    for part in queryset:
        row = [
            part.part_number,
            part.name,
            part.description or '',
            part.material_type or '',
            part.plant or '',
            part.material_group or '',
            part.purchasing_group or '',
            part.base_unit_of_measure or '',
            part.purchase_order_unit or '',
            part.order_unit or '',
            part.numerator_for_conversion or '',
            part.denominator_for_conversion or '',
            part.gross_weight or '',
            part.net_weight or '',
            part.weight_unit or '',
            part.volume or '',
            part.volume_unit or '',
            part.size_dimensions or '',
            part.ean_upc or '',
            part.manufacturer_part_number or '',
            part.old_material_number or '',
            part.planned_delivery_time_days or '',
            part.goods_receipt_processing_time_days or '',
            part.valuation_class or '',
            part.price_unit_peinh or '',
            part.moving_average_price or '',
            part.category.name if part.category else '',
            part.brand.name if part.brand else '',
            part.price or '',
            part.quantity or '',
            part.safety_stock or '',
            part.reorder_point or '',
            part.warranty_period or '',
            'Yes' if part.is_active else 'No',
            'Yes' if part.is_featured else 'No',
            part.created_at.strftime('%Y-%m-%d %H:%M:%S') if part.created_at else '',
            part.updated_at.strftime('%Y-%m-%d %H:%M:%S') if part.updated_at else '',
        ]
        
        if include_images:
            image_url = part.image.url if part.image else ''
            row.append(image_url)
        
        writer.writerow(row)
    
    return response
