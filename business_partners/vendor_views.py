"""
Vendor-specific views for part management.
Provides vendors with comprehensive access to manage their parts with all Excel fields.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
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
from io import StringIO

from .models import BusinessPartner, VendorProfile, ReorderNotification
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
    vendor_profile = get_vendor_profile(request.user)
    
    # Check if vendor profile exists
    if not vendor_profile:
        messages.error(request, 'Vendor profile not found. Please contact support.')
        return redirect('business_partners:vendor_registration_single')
    
    # Get vendor's business partner
    business_partner = vendor_profile.business_partner
    
    # Check if business partner exists
    if not business_partner:
        messages.error(request, 'Business partner not found. Please contact support.')
        return redirect('business_partners:vendor_registration_start')
    
    # Get parts statistics
    parts_queryset = Part.objects.filter(vendor=business_partner)
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
        total=Sum(F('price') * F('quantity'))
    )['total'] or 0
    
    # Get average price
    avg_price = parts_queryset.aggregate(avg=Avg('price'))['avg'] or 0
    
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
    recent_notifications = ReorderNotification.objects.filter(
        vendor=business_partner,
        status__in=['pending', 'acknowledged']
    ).select_related('part').order_by('-created_at')[:5]
    
    # Get critical notifications count
    critical_notifications = ReorderNotification.objects.filter(
        vendor=business_partner,
        priority='critical',
        status__in=['pending', 'acknowledged']
    ).count()
    
    # Get overdue notifications (older than 7 days)
    overdue_notifications = ReorderNotification.objects.filter(
        vendor=business_partner,
        status='pending',
        created_at__lt=timezone.now() - timedelta(days=7)
    ).count()
    
    # Calculate order and sales statistics
    # Get all orders that contain items from this vendor's parts
    from parts.models import Order, OrderItem
    
    # Get order items for this vendor's parts
    vendor_order_items = OrderItem.objects.filter(
        part__vendor=business_partner,
        order__status__in=['confirmed', 'processing', 'shipped', 'delivered']
    )
    
    # Total orders count
    total_orders = vendor_order_items.values('order').distinct().count()
    
    # Monthly sales calculation (last 30 days)
    last_30_days = timezone.now() - timedelta(days=30)
    monthly_sales_data = vendor_order_items.filter(
        order__created_at__gte=last_30_days
    ).aggregate(
        total_sales=Sum(F('price') * F('quantity'))
    )
    
    monthly_sales = monthly_sales_data['total_sales'] or 0
    
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
    today = timezone.now()
    
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

    # Profile completion percentage
    profile_completion_percentage = vendor_profile.get_profile_completion_percentage()

    context = {
        'vendor_profile': vendor_profile,
        'business_partner': business_partner,
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
            'monthly_sales': monthly_sales_display,
            'monthly_sales_raw': monthly_sales,
            'pending_actions': pending_actions,
            'revenue_labels': json.dumps(revenue_labels),
            'revenue_data': json.dumps(revenue_data),
            'delivered_count': delivered_count,
            'pending_processing_count': pending_processing_count,
            'total_fulfillment': total_fulfillment,
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

    from parts.models import Order, VendorOrderItemStatus

    now = timezone.now()
    last_30_days = now - timedelta(days=30)

    cash_received = VendorPayment.objects.filter(
        vendor=business_partner,
        status=PaymentStatus.COMPLETED,
        created_at__gte=last_30_days,
    ).aggregate(total=Sum('net_amount'))['total'] or Decimal('0.00')

    marketplace_commission = VendorPayment.objects.filter(
        vendor=business_partner,
        status=PaymentStatus.COMPLETED,
        created_at__gte=last_30_days,
    ).aggregate(total=Sum('commission_amount'))['total'] or Decimal('0.00')

    base_orders = Order.objects.filter(items__part__vendor=business_partner).distinct()

    open_invoices = base_orders.exclude(
        payment_status='completed'
    ).exclude(
        status__in=['cancelled', 'refunded']
    ).count()

    refundable_statuses = VendorOrderItemStatus.objects.filter(
        vendor=business_partner,
        status='refunded',
        updated_at__gte=last_30_days,
    )
    refund_amount = refundable_statuses.aggregate(
        total=Sum(F('order_item__quantity') * F('order_item__price'))
    )['total'] or Decimal('0.00')

    orders_last_30_days = base_orders.filter(
        created_at__gte=last_30_days,
        status__in=['confirmed', 'processing', 'shipped', 'delivered']
    )

    tax_payable = Decimal('0.00')
    shipping_cost = Decimal('0.00')

    per_order_totals = orders_last_30_days.values(
        'id',
        'total_price',
        'shipping_cost',
        'tax_amount',
    ).annotate(
        vendor_items_total=Sum(
            F('items__quantity') * F('items__price'),
            filter=Q(items__part__vendor=business_partner)
        )
    )

    for row in per_order_totals:
        order_total = row.get('total_price') or Decimal('0.00')
        vendor_total = row.get('vendor_items_total') or Decimal('0.00')
        if order_total <= 0 or vendor_total <= 0:
            continue
        ratio = vendor_total / order_total
        tax_payable += (row.get('tax_amount') or Decimal('0.00')) * ratio
        shipping_cost += (row.get('shipping_cost') or Decimal('0.00')) * ratio

    recent_transactions = VendorPayment.objects.filter(
        vendor=business_partner
    ).order_by('-created_at')[:10]

    pending_processing_count = base_orders.filter(
        status__in=['confirmed', 'processing']
    ).count()

    context = {
        'vendor_profile': vendor_profile,
        'business_partner': business_partner,
        'is_approved': vendor_profile.is_approved,
        'cash_received': cash_received,
        'open_invoices': open_invoices,
        'tax_payable': tax_payable,
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

    bank_details = (vendor_profile.bank_account_details or '').splitlines()
    bank_name = ''
    account_number = ''
    iban = ''
    for raw_line in bank_details:
        line = raw_line.strip()
        if not line:
            continue
        if line.lower().startswith('bank:'):
            bank_name = line.split(':', 1)[1].strip()
        elif line.lower().startswith('account number:'):
            account_number = line.split(':', 1)[1].strip()
        elif line.lower().startswith('iban:'):
            iban = line.split(':', 1)[1].strip()

    account_source = account_number or iban
    bank_account_display = '—'
    if account_source:
        last4 = ''.join(ch for ch in account_source if ch.isalnum())[-4:]
        if last4:
            prefix = bank_name or 'Bank'
            bank_account_display = f'{prefix} **** {last4}'

    payouts_qs = VendorPayment.objects.filter(vendor=business_partner).order_by('-created_at')

    last_payout = payouts_qs.filter(status=PaymentStatus.COMPLETED).order_by(
        '-payment_date',
        '-processed_at',
        '-created_at',
    ).first()
    last_payout_amount = last_payout.net_amount if last_payout else Decimal('0.00')
    last_payout_date = None
    if last_payout:
        last_payout_date = last_payout.payment_date or last_payout.processed_at or last_payout.created_at

    pending_statuses = [PaymentStatus.PENDING, PaymentStatus.PROCESSING]
    pending_payments = list(
        payouts_qs.filter(status__in=pending_statuses).order_by('due_date', 'created_at')[:250]
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

    pending_balance = sum((p.net_amount or Decimal('0.00')) for p in pending_payments) if pending_payments else Decimal('0.00')
    clearing_in_days = None
    if next_payout_date:
        clearing_in_days = (next_payout_date - today).days

    payouts_page_size = 20
    paginator = Paginator(payouts_qs, payouts_page_size)
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

    payments_qs = VendorPayment.objects.filter(vendor=business_partner).order_by('-created_at')

    lookback_days = 90
    since = timezone.now() - timedelta(days=lookback_days)
    payments_recent = payments_qs.filter(created_at__gte=since)

    totals = payments_recent.aggregate(
        total_sales=Sum('amount'),
        total_commission=Sum('commission_amount'),
    )
    total_sales = totals.get('total_sales') or Decimal('0.00')
    total_commission = totals.get('total_commission') or Decimal('0.00')
    effective_rate = Decimal('0.00')
    if total_sales > 0:
        effective_rate = (total_commission / total_sales) * Decimal('100')

    paginator = Paginator(payments_recent, 25)
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
        created_at__gte=period_start,
        status__in=['confirmed', 'processing', 'shipped', 'delivered'],
    )

    sales_tax_payable = Decimal('0.00')
    per_order_totals = orders_in_period.values(
        'id',
        'total_price',
        'tax_amount',
    ).annotate(
        vendor_items_total=Sum(
            F('items__quantity') * F('items__price'),
            filter=Q(items__part__vendor=business_partner)
        )
    )

    for row in per_order_totals:
        order_total = row.get('total_price') or Decimal('0.00')
        vendor_total = row.get('vendor_items_total') or Decimal('0.00')
        if order_total <= 0 or vendor_total <= 0:
            continue
        ratio = vendor_total / order_total
        sales_tax_payable += (row.get('tax_amount') or Decimal('0.00')) * ratio

    withholding_tax_payable = Decimal('0.00')
    total_payable = sales_tax_payable + withholding_tax_payable

    tax_certificate = (
        getattr(vendor_profile, 'tax_certificate', None)
        or getattr(vendor_profile, 'vat_certificate', None)
    )

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
        'has_tax_certificate': bool(tax_certificate),
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

    certificate = (
        getattr(vendor_profile, 'tax_certificate', None)
        or getattr(vendor_profile, 'vat_certificate', None)
    )
    if not certificate:
        messages.error(request, 'No tax certificate uploaded.')
        return redirect('business_partners:vendor_tax_summary')

    filename = (certificate.name or '').rsplit('/', 1)[-1] or 'tax-certificate'
    return FileResponse(certificate.open('rb'), as_attachment=True, filename=filename)


@vendor_required
@login_required
def vendor_finance_ledger(request):
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'Vendor profile not found.')
        return redirect('business_partners:vendor_registration_single')

    business_partner = vendor_profile.business_partner

    payments = VendorPayment.objects.filter(vendor=business_partner).order_by('created_at')

    ledger_rows = []
    for p in payments:
        created_at = p.created_at or timezone.now()
        if (p.amount or Decimal('0.00')) > 0:
            ledger_rows.append({
                'sort_dt': created_at,
                'seq': 0,
                'date': created_at,
                'type': 'sale',
                'label': 'Sale',
                'description': f'{p.payment_reference} revenue',
                'debit': None,
                'credit': p.amount,
            })

        if (p.commission_amount or Decimal('0.00')) > 0:
            ledger_rows.append({
                'sort_dt': created_at,
                'seq': 1,
                'date': created_at,
                'type': 'fee',
                'label': 'Fee',
                'description': f'Commission ({p.payment_reference})',
                'debit': p.commission_amount,
                'credit': None,
            })

        if p.status == PaymentStatus.COMPLETED and (p.net_amount or Decimal('0.00')) > 0:
            payout_dt = p.payment_date or p.processed_at or p.created_at or timezone.now()
            ledger_rows.append({
                'sort_dt': payout_dt,
                'seq': 2,
                'date': payout_dt,
                'type': 'payout',
                'label': 'Payout',
                'description': f'Payout ({p.payment_reference})',
                'debit': p.net_amount,
                'credit': None,
            })

    ledger_rows.sort(key=lambda r: (r['sort_dt'], r['seq']))

    running_balance = Decimal('0.00')
    for row in ledger_rows:
        credit = row['credit'] or Decimal('0.00')
        debit = row['debit'] or Decimal('0.00')
        running_balance += credit
        running_balance -= debit
        row['balance'] = running_balance

    ledger_rows.reverse()

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

    payments = VendorPayment.objects.filter(vendor=business_partner).order_by('created_at')

    ledger_rows = []
    for p in payments:
        created_at = p.created_at or timezone.now()
        if (p.amount or Decimal('0.00')) > 0:
            ledger_rows.append((created_at, 0, created_at, 'Sale', f'{p.payment_reference} revenue', None, p.amount))

        if (p.commission_amount or Decimal('0.00')) > 0:
            ledger_rows.append((created_at, 1, created_at, 'Fee', f'Commission ({p.payment_reference})', p.commission_amount, None))

        if p.status == PaymentStatus.COMPLETED and (p.net_amount or Decimal('0.00')) > 0:
            payout_dt = p.payment_date or p.processed_at or p.created_at or timezone.now()
            ledger_rows.append((payout_dt, 2, payout_dt, 'Payout', f'Payout ({p.payment_reference})', p.net_amount, None))

    ledger_rows.sort(key=lambda r: (r[0], r[1]))

    running_balance = Decimal('0.00')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="vendor-ledger-{business_partner.id}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Type', 'Description', 'Debit', 'Credit', 'Balance'])

    for _, __, dt, label, desc, debit, credit in ledger_rows:
        running_balance += (credit or Decimal('0.00'))
        running_balance -= (debit or Decimal('0.00'))
        writer.writerow([
            dt.isoformat() if dt else '',
            label,
            desc,
            str(debit or ''),
            str(credit or ''),
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

    def parse_bank_details(raw_text):
        parsed = {
            'account_holder': '',
            'bank_name': '',
            'branch_code': '',
            'iban': '',
        }
        for raw_line in (raw_text or '').splitlines():
            line = raw_line.strip()
            if not line:
                continue
            lower = line.lower()
            if lower.startswith('account holder:'):
                parsed['account_holder'] = line.split(':', 1)[1].strip()
            elif lower.startswith('bank:'):
                parsed['bank_name'] = line.split(':', 1)[1].strip()
            elif lower.startswith('branch code:'):
                parsed['branch_code'] = line.split(':', 1)[1].strip()
            elif lower.startswith('iban:'):
                parsed['iban'] = line.split(':', 1)[1].strip()
        return parsed

    existing = parse_bank_details(vendor_profile.bank_account_details)

    if request.method == 'POST':
        account_holder = (request.POST.get('account_holder') or '').strip()
        bank_name = (request.POST.get('bank_name') or '').strip()
        branch_code = (request.POST.get('branch_code') or '').strip()
        iban = (request.POST.get('iban') or '').strip()

        lines = []
        if account_holder:
            lines.append(f'Account Holder: {account_holder}')
        if bank_name:
            lines.append(f'Bank: {bank_name}')
        if branch_code:
            lines.append(f'Branch Code: {branch_code}')
        if iban:
            lines.append(f'IBAN: {iban}')

        vendor_profile.bank_account_details = '\n'.join(lines) if lines else None
        vendor_profile.save(update_fields=['bank_account_details'])
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
    
    # Get or create vendor balance
    vendor_balance, created = VendorBalance.objects.get_or_create(
        vendor=business_partner,
        defaults={
            'current_balance': Decimal('0.00'),
            'pending_balance': Decimal('0.00'),
            'total_earned': Decimal('0.00'),
            'total_paid': Decimal('0.00')
        }
    )
    
    # Calculate Total Earned (Lifetime Sales from Delivered Orders)
    from parts.models import OrderItem
    total_earned = OrderItem.objects.filter(
        part__vendor=business_partner,
        order__status='delivered'
    ).aggregate(
        total=Sum(F('price') * F('quantity'))
    )['total'] or Decimal('0.00')

    # Update Vendor Balance
    vendor_balance.total_earned = total_earned
    vendor_balance.update_balance() # Saves and updates current_balance including total_paid
    
    # Calculate Pending Clearance (Orders confirmed/processing/shipped but not yet delivered)
    # These are potential earnings that are "in flight"
    pending_clearance_amount = OrderItem.objects.filter(
        part__vendor=business_partner,
        order__status__in=['confirmed', 'processing', 'shipped']
    ).aggregate(
        total=Sum(F('price') * F('quantity'))
    )['total'] or Decimal('0.00')
    
    # Get recent transactions (payments)
    recent_transactions = VendorPayment.objects.filter(
        vendor=business_partner
    ).order_by('-created_at')[:10]
    
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
        monthly_earnings = VendorPayment.objects.filter(
            vendor=business_partner,
            status=PaymentStatus.COMPLETED,
            created_at__year=year_target,
            created_at__month=month_target
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Or alternatively, use Order revenue for the chart if preferred:
        # monthly_earnings = OrderItem.objects.filter(...)
        
        import datetime as dt
        month_name = dt.date(year_target, month_target, 1).strftime('%b')
        revenue_labels.insert(0, month_name)
        revenue_data.insert(0, float(monthly_earnings))

    context = {
        'vendor_profile': vendor_profile,
        'business_partner': business_partner,
        'vendor_balance': vendor_balance,
        'pending_clearance': pending_clearance_amount,
        'recent_transactions': recent_transactions,
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
    from parts.models import Order
    
    # Get all orders containing items from this vendor
    # We treat these Orders as "Invoices" for the purpose of this view
    orders = Order.objects.filter(
        items__part__vendor=business_partner
    ).distinct().order_by('-created_at')
    
    # --- Statistics ---
    
    # Total Due: Orders that are not paid yet (payment_status != completed)
    # This might be simplistic, but it's a starting point.
    total_due = orders.exclude(
        payment_status='completed'
    ).aggregate(total=Sum('total_price'))['total'] or 0
    
    # Paid (This Month): Orders paid in the current month
    today = timezone.now()
    paid_this_month = orders.filter(
        payment_status='completed',
        updated_at__year=today.year,
        updated_at__month=today.month
    ).aggregate(total=Sum('total_price'))['total'] or 0
    
    # Overdue: For now, let's assume 'failed' payments or pending for > 30 days are "overdue"
    # Or just use a placeholder if business logic is not defined
    overdue_date = today - timedelta(days=30)
    overdue_amount = orders.filter(
        payment_status='pending',
        created_at__lt=overdue_date
    ).aggregate(total=Sum('total_price'))['total'] or 0
    
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
        form = VendorPartForm(request.POST, request.FILES, vendor=business_partner)
        if form.is_valid():
            part = form.save()
            messages.success(request, f'Part "{part.parts_number}" created successfully.')
            return redirect('business_partners:vendor_parts_list')
    else:
        form = VendorPartForm(vendor=business_partner)
    
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
        form = VendorPartForm(request.POST, request.FILES, instance=part, vendor=business_partner)
        if form.is_valid():
            part = form.save()
            messages.success(request, f'Part "{part.parts_number}" updated successfully.')
            return redirect('business_partners:vendor_parts_list')
    else:
        form = VendorPartForm(instance=part, vendor=business_partner)
    
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


@login_required
def vendor_responsive_test(request):
    """Test responsive design for vendor dashboard navigation and footer."""
    return render(request, 'business_partners/vendor_responsive_test.html')
    



@vendor_required
def vendor_crud_test(request):
    """
    Comprehensive CRUD system test page for vendors.
    Tests all CRUD operations with validation and AJAX functionality.
    """
    vendor_profile = get_vendor_profile(request.user)
    
    context = {
        'vendor_profile': vendor_profile,
        'business_partner': vendor_profile.business_partner,
    }
    
    return render(request, 'business_partners/vendor_crud_test.html', context)


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


@login_required
def vendor_parts_import(request):
    """
    Handle bulk import of vendor parts from CSV/Excel files.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    business_partner = vendor_profile.business_partner
    
    if request.method == 'POST':
        form = VendorPartBulkImportForm(request.POST, request.FILES)
        if form.is_valid():
            import_file = form.cleaned_data['file']
            import_status = form.cleaned_data.get('import_status') or 'published'
            update_existing = form.cleaned_data['update_existing']
            validate_only = form.cleaned_data['validate_only']
            
            try:
                # Use transaction to ensure data integrity
                with transaction.atomic():
                    # Process the import file
                    results = process_import_file(
                        import_file, 
                        business_partner, 
                        import_status,
                        update_existing, 
                        validate_only
                    )
                    
                    # If validation only or critical errors occurred, rollback
                    if validate_only:
                        messages.info(request, f'Validation complete. {results["valid_count"]} valid rows, {results["error_count"]} errors.')
                        transaction.set_rollback(True)
                    elif results['error_count'] > 0 and results['created_count'] == 0 and results['updated_count'] == 0:
                        # If everything failed, treat as error but don't rollback (nothing happened anyway)
                        messages.error(request, f'Import failed. {results["error_count"]} errors found. No parts were imported.')
                    else:
                        if results['error_count'] > 0:
                            messages.warning(request, f'Import completed with errors. {results["created_count"]} created, {results["updated_count"]} updated, {results["error_count"]} failed.')
                        else:
                            messages.success(request, f'Import success! {results["created_count"]} parts created, {results["updated_count"]} parts updated.')
                
                # Store results in session for display
                request.session['import_results'] = results
                return redirect('business_partners:vendor_parts_import_results')
                
            except Exception as e:
                import traceback
                print(traceback.format_exc())
                messages.error(request, f'System Error during import: {str(e)}')
    else:
        form = VendorPartBulkImportForm()
    
    context = {
        'vendor_profile': vendor_profile,
        'form': form,
    }
    
    return render(request, 'business_partners/vendor_parts_import.html', context)


@login_required
def vendor_parts_import_results(request):
    """
    Display results of the bulk import operation.
    """
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    results = request.session.get('import_results', {})
    if not results:
        messages.warning(request, 'No import results found.')
        return redirect('business_partners:vendor_parts_import')
    
    # Clear results from session
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


def process_import_file(import_file, business_partner, import_status, update_existing, validate_only):
    """
    Process CSV or Excel import file and create/update parts with comprehensive validation.
    """
    import csv
    import io
    from decimal import Decimal, InvalidOperation
    from django.utils.dateparse import parse_date
    from django.core.validators import URLValidator
    from django.core.exceptions import ValidationError
    from vehicles.models import VehicleVariant
    
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
    REQUIRED_FIELDS = ['parts_number', 'material_description', 'base_unit_of_measure', 'category_name', 'brand_name', 'price']
    
    # Map Excel/CSV headers to model fields
    HEADER_MAPPINGS = {
        'Part Number': 'parts_number',
        'Part No': 'parts_number',
        'Material Description': 'material_description',
        'Description': 'material_description',  # Alias
        'Arabic Description': 'material_description_ar',
        'Category': 'category_name',
        'Brand': 'brand_name',
        'Price': 'price',
        'Quantity': 'quantity',
        'Qty': 'quantity',
        'Stock': 'quantity',  # Alias
        'Base Unit': 'base_unit_of_measure',
        'Unit': 'base_unit_of_measure',  # Alias
        'UOM': 'base_unit_of_measure',
        'Image URL': 'image_url',
        'Image': 'image_url',
        'Compatible Vehicles': 'vehicle_variants',
        'Vehicles': 'vehicle_variants',  # Alias
        'Manufacturer Part Number': 'manufacturer_part_number',
        'MPN': 'manufacturer_part_number',
        'OEM Number': 'manufacturer_oem_number',
        'OEM': 'manufacturer_oem_number',
        'Weight': 'gross_weight',
        'Gross Weight': 'gross_weight',
        'Net Weight': 'net_weight',
        'Dimensions': 'size_dimensions',
        'Size': 'size_dimensions',
        'Safety Stock': 'safety_stock',
        'Reorder Point': 'reorder_point',
        'Active': 'is_active',
        'Featured': 'is_featured'
    }
    
    FIELD_MAPPINGS = {
        'parts_number': 'parts_number',
        'material_description': 'material_description',
        'material_description_ar': 'material_description_ar',
        'vehicle_variants': 'compatible_vehicles',
        'image_url': 'image_url'
    }
    
    NUMERIC_FIELDS = {
        'price': {'min': 0, 'max': 999999.99, 'decimal_places': 2},
        'quantity': {'min': 0, 'max': 999999, 'decimal_places': 0},
        'safety_stock': {'min': 0, 'max': 999999, 'decimal_places': 0},
        'minimum_safety_stock': {'min': 0, 'max': 999999, 'decimal_places': 0},
        'reorder_point': {'min': 0, 'max': 999999, 'decimal_places': 0},
        'minimum_order_quantity': {'min': 1, 'max': 999999, 'decimal_places': 0},
        'gross_weight': {'min': 0, 'max': 99999.999, 'decimal_places': 3},
        'net_weight': {'min': 0, 'max': 99999.999, 'decimal_places': 3},
        'planned_delivery_time_days': {'min': 0, 'max': 365, 'decimal_places': 0},
        'goods_receipt_processing_time_days': {'min': 0, 'max': 30, 'decimal_places': 0},
        'warranty_period': {'min': 0, 'max': 120, 'decimal_places': 0},
        'standard_price': {'min': 0, 'max': 999999.99, 'decimal_places': 2},
        'moving_average_price': {'min': 0, 'max': 999999.99, 'decimal_places': 2},
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
        'plant': {'max_length': 50},
        'storage_location': {'max_length': 50},
        'warehouse_number': {'max_length': 50},
        'storage_bin': {'max_length': 50},
        'material_group': {'max_length': 50},
        'division': {'max_length': 50},
        'old_material_number': {'max_length': 50},
        'external_material_group': {'max_length': 50},
        'abc_indicator': {'max_length': 1, 'choices': ['A', 'B', 'C']},
        'mrp_type': {'max_length': 10},
        'mrp_group': {'max_length': 10},
        'mrp_controller': {'max_length': 10},
        'valuation_class': {'max_length': 50},
        'price_control_indicator': {'max_length': 10},
        'storage_location_code': {'max_length': 50}
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

    def validate_vehicle_variants(variants_str, row_num):
        """Validate vehicle variants field"""
        errors = []
        valid_variants = []
        
        if not variants_str or not variants_str.strip():
            return errors, valid_variants
        
        # Split by comma and clean
        variant_names = [v.strip() for v in variants_str.split(',') if v.strip()]
        
        for variant_name in variant_names:
            try:
                # Use filter().first() instead of get() to handle duplicates gracefully
                variant = VehicleVariant.objects.filter(name__iexact=variant_name).first()
                if variant:
                    valid_variants.append(variant)
                else:
                    # If exact match fails, try partial match or log error
                    # For now, we'll treat it as not found to be safe
                    errors.append(f"Row {row_num}: Vehicle variant '{variant_name}' not found in system")
            except Exception as e:
                errors.append(f"Row {row_num}: Error validating variant '{variant_name}': {str(e)}")
        
        return errors, valid_variants

    try:
        # Determine file type and read data
        file_extension = import_file.name.lower().split('.')[-1]
        
        if file_extension == 'csv':
            # Handle CSV file
            file_content = import_file.read().decode('utf-8-sig')  # Handle BOM
            csv_reader = csv.DictReader(io.StringIO(file_content))
            rows = list(csv_reader)
        elif file_extension in ['xlsx', 'xls']:
            # Handle Excel file
            try:
                import openpyxl
                workbook = openpyxl.load_workbook(import_file)
                worksheet = workbook.active
                
                # Get headers from first row
                headers = [cell.value for cell in worksheet[1]]
                
                # Get data rows
                rows = []
                for row in worksheet.iter_rows(min_row=2, values_only=True):
                    row_dict = dict(zip(headers, row))
                    rows.append(row_dict)
            except ImportError:
                raise Exception("openpyxl library is required for Excel file processing")
        else:
            raise Exception("Unsupported file format. Please use CSV or Excel files.")
        
        results['total_rows'] = len(rows)
        
        # Normalize headers in rows
        normalized_rows = []
        for row in rows:
            normalized_row = {}
            for key, value in row.items():
                if key is None: continue
                
                # Check if key matches a mapping (case insensitive)
                key_str = str(key).strip()
                mapped_key = None
                
                # Try direct match
                if key_str in HEADER_MAPPINGS:
                    mapped_key = HEADER_MAPPINGS[key_str]
                # Try case-insensitive match
                else:
                    for header, field in HEADER_MAPPINGS.items():
                        if header.lower() == key_str.lower():
                            mapped_key = field
                            break
                
                # If no mapping found, check if it matches a field name directly
                if not mapped_key:
                    # Clean the key to snake_case
                    clean_key = key_str.lower().replace(' ', '_')
                    
                    # Check if it's a known field
                    all_known_fields = set(REQUIRED_FIELDS) | set(NUMERIC_FIELDS.keys()) | set(STRING_FIELDS.keys()) | set(BOOLEAN_FIELDS) | set(DATE_FIELDS) | set(URL_FIELDS)
                    
                    if clean_key in all_known_fields:
                        mapped_key = clean_key
                    else:
                        mapped_key = key_str # Keep original if unknown
                
                normalized_row[mapped_key] = value
            normalized_rows.append(normalized_row)
        
        rows = normalized_rows
        
        # Initialize field error tracking
        for field in REQUIRED_FIELDS + list(NUMERIC_FIELDS.keys()) + list(STRING_FIELDS.keys()) + BOOLEAN_FIELDS + DATE_FIELDS + URL_FIELDS:
            results['field_errors'][field] = 0
        
        for row_num, row in enumerate(rows, start=2):
            row_errors = []
            row_warnings = []
            validated_data = {}
            
            try:
                # Validate all fields
                for field_name, raw_value in row.items():
                    if field_name and raw_value is not None:
                        field_errors, validated_value = validate_field(field_name, raw_value, row_num)
                        row_errors.extend(field_errors)
                        
                        if field_errors:
                            results['field_errors'][field_name] = results['field_errors'].get(field_name, 0) + len(field_errors)
                        
                        if validated_value is not None:
                            # Map field names
                            mapped_field = FIELD_MAPPINGS.get(field_name, field_name)
                            validated_data[mapped_field] = validated_value
                
                # Special validation for required fields
                for required_field in REQUIRED_FIELDS:
                    if required_field not in row or not row[required_field]:
                        row_errors.append(f"Row {row_num}: {required_field} is required")
                        results['field_errors'][required_field] = results['field_errors'].get(required_field, 0) + 1
                
                # Validate vehicle variants
                if 'vehicle_variants' in row:
                    variant_errors, valid_variants = validate_vehicle_variants(row['vehicle_variants'], row_num)
                    row_errors.extend(variant_errors)
                    if valid_variants:
                        validated_data['compatible_vehicles'] = valid_variants
                
                # Validate category and brand existence
                if 'category_name' in validated_data:
                    try:
                        category_val = validated_data['category_name']
                        # Try exact match first
                        try:
                            category = Category.objects.filter(name__iexact=category_val).first()
                            if not category:
                                raise Category.DoesNotExist
                        except Category.DoesNotExist:
                            # Try contains if exact fails? No, safer to be strict or fallback to default
                            raise Category.DoesNotExist
                            
                        validated_data['category'] = category
                        del validated_data['category_name']
                    except Category.DoesNotExist:
                        row_errors.append(f"Row {row_num}: Category '{validated_data['category_name']}' not found")
                        results['field_errors']['category_name'] = results['field_errors'].get('category_name', 0) + 1
                
                if 'brand_name' in validated_data:
                    try:
                        brand_val = validated_data['brand_name']
                        try:
                            brand = Brand.objects.filter(name__iexact=brand_val).first()
                            if not brand:
                                raise Brand.DoesNotExist
                        except Brand.DoesNotExist:
                            raise Brand.DoesNotExist
                            
                        validated_data['brand'] = brand
                        del validated_data['brand_name']
                    except Brand.DoesNotExist:
                        row_errors.append(f"Row {row_num}: Brand '{validated_data['brand_name']}' not found")
                        results['field_errors']['brand_name'] = results['field_errors'].get('brand_name', 0) + 1
                
                # Check for duplicate part number
                if 'parts_number' in validated_data:
                    existing_part = None
                    # Filter by parts_number AND vendor to allow different vendors to sell the same part number
                    existing_parts = Part.objects.filter(
                        parts_number=validated_data['parts_number'],
                        vendor=business_partner
                    )
                    if existing_parts.exists():
                        existing_part = existing_parts.first()
                    
                    if existing_part and not update_existing:
                        row_warnings.append(f"Row {row_num}: Part {validated_data['parts_number']} already exists (skipped)")
                        continue
                
                # Business logic validations
                if 'safety_stock' in validated_data and 'quantity' in validated_data:
                    if validated_data['safety_stock'] > validated_data['quantity']:
                        row_warnings.append(f"Row {row_num}: Safety stock is higher than current quantity")
                
                if 'reorder_point' in validated_data and 'safety_stock' in validated_data:
                    if validated_data['reorder_point'] < validated_data['safety_stock']:
                        row_warnings.append(f"Row {row_num}: Reorder point should be higher than safety stock")
                
                # Add vendor to validated data
                validated_data['vendor'] = business_partner
                
                # If there are errors, skip this row
                if row_errors:
                    results['errors'].extend(row_errors)
                    results['error_count'] += 1
                    continue
                
                # Add warnings to results
                if row_warnings:
                    results['warnings'].extend(row_warnings)
                
                # Create or update part if not validation-only mode
                if not validate_only:
                    compatible_vehicles = validated_data.pop('compatible_vehicles', [])
                    
                    if existing_part:
                        # Update existing part
                        for key, value in validated_data.items():
                            if key != 'vendor':  # Don't update vendor
                                setattr(existing_part, key, value)
                        existing_part.save()
                        
                        # Update vehicle compatibility
                        if compatible_vehicles and hasattr(existing_part, 'compatible_vehicles'):
                            existing_part.compatible_vehicles.set(compatible_vehicles)
                        
                        results['updated_count'] += 1
                    else:
                        # Create new part
                        if import_status in ['draft', 'published', 'archived']:
                            validated_data['status'] = import_status
                        new_part = Part.objects.create(**validated_data)
                        
                        # Set vehicle compatibility
                        if compatible_vehicles and hasattr(new_part, 'compatible_vehicles'):
                            new_part.compatible_vehicles.set(compatible_vehicles)
                        
                        results['created_count'] += 1
                
                results['valid_count'] += 1
                
            except Exception as e:
                error_msg = f"Row {row_num}: Unexpected error - {str(e)}"
                results['errors'].append(error_msg)
                results['error_count'] += 1
        
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
