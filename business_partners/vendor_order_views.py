"""
Vendor Order Management Views
Handles vendor-specific order processing, order management, and order-related functionality
for business partners (vendors).
"""
import logging
import traceback
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import ListView, DetailView, UpdateView
from django.urls import reverse_lazy
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest, JsonResponse, HttpResponseServerError, Http404
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Count, Sum, F, Prefetch, Case, When, Value, Avg
from django.db import transaction
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal
import json

from parts.models import Order, OrderItem, OrderStatusHistory, OrderShipping, OrderDiscount, VendorOrderItemStatus
from .models import BusinessPartner, VendorProfile
from .decorators import vendor_required
from vendor_employees.utils import get_vendor_context
from vendor_employees.permissions import VendorPermissionRequiredMixin


class VendorOrderListView(VendorPermissionRequiredMixin, ListView):
    """Vendor-specific view to list orders containing their parts."""
    model = Order
    template_name = 'vendors/orders.html'
    context_object_name = 'orders'
    paginate_by = 20
    vendor_permission_code = 'orders'
    vendor_permission_action = 'view'
    
    def get_queryset(self):
        """Return orders that contain parts from the current vendor."""
        user = self.request.user
        vendor_partner = get_vendor_context(user)
        
        if not vendor_partner:
            return Order.objects.none()
        
        # Base filters
        base_filters = Q(items__part__vendor=vendor_partner)
        
        # Location-based filtering for vendor employees
        vendor_employee = getattr(user, 'vendor_employee', None)
        if vendor_employee and vendor_employee.is_active:
            employee_locations = vendor_employee.locations.filter(is_active=True).values_list('name', flat=True)
            if employee_locations:
                location_filter = (
                    Q(items__part__plant__in=employee_locations) | 
                    Q(items__part__storage_location__in=employee_locations) | 
                    Q(items__part__warehouse_number__in=employee_locations)
                )
                base_filters &= location_filter
            else:
                return Order.objects.none()
        
        # Base queryset: orders with vendor's parts
        qs = Order.objects.filter(
            base_filters
        ).exclude(status='created').distinct()

        # Apply status filter
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)

        # Apply search filter
        search = self.request.GET.get('search')
        if search:
            qs = qs.filter(
                Q(order_number__icontains=search) |
                Q(customer__first_name__icontains=search) |
                Q(customer__last_name__icontains=search) |
                Q(customer__email__icontains=search) |
                Q(guest_name__icontains=search) |
                Q(guest_email__icontains=search)
            )
        
        return qs.select_related(
            'customer', 'shipping_info'
        ).prefetch_related(
            'items__part',
            'items__part__brand',
            'items__part__category',
            'status_history'
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'My Orders'
        
        # Get vendor context
        vendor_partner = get_vendor_context(self.request.user)
        if vendor_partner:
            context['business_partner'] = vendor_partner
            context['vendor_profile'] = getattr(vendor_partner, 'vendor_profile', None)
            
            # Base filters for counts (unfiltered by status/search)
            base_filters = Q(items__part__vendor=vendor_partner)
            
            # Location-based filtering for vendor employees
            vendor_employee = getattr(self.request.user, 'vendor_employee', None)
            if vendor_employee and vendor_employee.is_active:
                employee_locations = vendor_employee.locations.filter(is_active=True).values_list('name', flat=True)
                if employee_locations:
                    location_filter = (
                        Q(items__part__plant__in=employee_locations) | 
                        Q(items__part__storage_location__in=employee_locations) | 
                        Q(items__part__warehouse_number__in=employee_locations)
                    )
                    base_filters &= location_filter
                else:
                    # If an employee has no locations, all counts should be 0
                    base_filters = Q(pk__in=[])
            
            base_qs = Order.objects.filter(
                base_filters
            ).distinct()
            
            context['total_orders'] = base_qs.count()
            
            # Status counts for dashboard cards and tabs
            context['status_counts'] = {
                'pending': base_qs.filter(status='pending').count(),
                'processing': base_qs.filter(status='processing').count(),
                'completed': base_qs.filter(status='delivered').count(),
            }
            
            # Individual counts
            context['pending_orders'] = base_qs.filter(status='pending').count()
            context['confirmed_orders'] = base_qs.filter(status='confirmed').count()
            context['processing_orders'] = base_qs.filter(status='processing').count()
            context['shipped_orders'] = base_qs.filter(status='shipped').count()
            context['delivered_orders'] = base_qs.filter(status='delivered').count()
            context['cancelled_orders'] = base_qs.filter(status='cancelled').count()
            
            # Revenue statistics (Vendor Specific)
            revenue_qs = OrderItem.objects.filter(
                part__vendor=vendor_partner,
                order__status__in=['delivered', 'shipped']
            )
            
            # Location-based filtering for vendor employees
            if vendor_employee and vendor_employee.is_active:
                if employee_locations:
                    location_filter = (
                        Q(part__plant__in=employee_locations) | 
                        Q(part__storage_location__in=employee_locations) | 
                        Q(part__warehouse_number__in=employee_locations)
                    )
                    revenue_qs = revenue_qs.filter(location_filter)
                else:
                    revenue_qs = revenue_qs.none()
            
            context['total_revenue'] = revenue_qs.aggregate(
                total=Sum(F('quantity') * F('price'))
            )['total'] or 0
            
            # Recent activity
            context['recent_orders'] = base_qs.order_by('-created_at')[:5]
            
            # Status filter from URL
            status_filter = self.request.GET.get('status')
            if status_filter:
                context['status_filter'] = status_filter
            
            # Filter parameters for form persistence
            context['search_query'] = self.request.GET.get('search', '')
            context['date_from'] = self.request.GET.get('date_from', '')
            context['date_to'] = self.request.GET.get('date_to', '')
            context['min_amount'] = self.request.GET.get('min_amount', '')
            context['max_amount'] = self.request.GET.get('max_amount', '')
            
            orders_page = context.get('orders')
            if orders_page:
                try:
                    from core.models import ExchangeRate
                    from decimal import Decimal as D
                except Exception:
                    ExchangeRate = None
                    D = Decimal
                
                currency_rates_to_usd = {}
                for order in orders_page:
                    vendor_total_usd = Decimal('0.00')
                    vendor_tax_total_usd = Decimal('0.00')
                    for item in getattr(order, 'items', []).all():
                        if not item.part_id or getattr(item.part, 'vendor_id', None) != vendor_partner.id:
                            continue

                        unit_price_usd = None
                        if getattr(item, 'vendor_currency_amount', None):
                            vendor_amount = item.vendor_currency_amount
                            original_currency_code = (getattr(item, 'original_currency_code', None) or getattr(item.part, 'original_currency', None) or 'USD').upper()
                            if getattr(item, 'locked_exchange_rate', None):
                                if original_currency_code == 'USD':
                                    unit_price_usd = vendor_amount
                                else:
                                    unit_price_usd = vendor_amount * item.locked_exchange_rate
                            else:
                                if original_currency_code == 'USD':
                                    unit_price_usd = vendor_amount
                                elif ExchangeRate:
                                    if original_currency_code not in currency_rates_to_usd:
                                        currency_rates_to_usd[original_currency_code] = D(str(ExchangeRate.get_current_rate(original_currency_code, 'USD')))
                                    unit_price_usd = vendor_amount * currency_rates_to_usd[original_currency_code]
                        if unit_price_usd is None:
                            original_currency_code = (getattr(item, 'original_currency_code', None) or getattr(item.part, 'original_currency', None) or 'USD').upper()
                            if original_currency_code == 'USD':
                                unit_price_usd = item.part.standard_price
                            elif ExchangeRate:
                                if original_currency_code not in currency_rates_to_usd:
                                    currency_rates_to_usd[original_currency_code] = D(str(ExchangeRate.get_current_rate(original_currency_code, 'USD')))
                                unit_price_usd = item.part.standard_price * currency_rates_to_usd[original_currency_code]
                            else:
                                unit_price_usd = item.price

                        line_subtotal_usd = (unit_price_usd or Decimal('0.00')) * item.quantity

                        tax_rate = Decimal('0.15')
                        tax_classification = getattr(item.part, 'tax_classification_material', None)
                        if tax_classification == 'VAT_5':
                            tax_rate = Decimal('0.05')
                        elif tax_classification in ('ZERO', 'EXEMPT'):
                            tax_rate = Decimal('0.00')

                        vendor_total_usd += line_subtotal_usd
                        vendor_tax_total_usd += line_subtotal_usd * tax_rate

                    order.vendor_total = vendor_total_usd + vendor_tax_total_usd
        
        return context


class VendorOrderDetailView(VendorPermissionRequiredMixin, DetailView):
    """Detailed view of an order for vendors (only shows their parts)."""
    model = Order
    template_name = 'vendors/order_details.html'
    context_object_name = 'order'
    vendor_permission_code = 'orders'
    vendor_permission_action = 'view'
    
    def get_object(self):
        """Get order and verify vendor has parts in this order."""
        # Use select_related to reduce initial DB hits
        queryset = super().get_queryset().select_related('customer')
        
        try:
            order = queryset.get(pk=self.kwargs.get('pk'))
        except self.model.DoesNotExist:
            raise Http404("Order not found")
        
        # Hide draft/created orders from vendors
        if order.status == 'created':
            raise Http404("Order not found")
            
        user = self.request.user
        vendor_partner = get_vendor_context(user)
        
        if not vendor_partner:
            raise PermissionDenied("You don't have vendor access.")
        
        # Check if this order contains parts from this vendor
        # We check existence efficiently
        item_filters = Q(part__vendor=vendor_partner)
        
        # Location-based filtering for vendor employees
        vendor_employee = getattr(user, 'vendor_employee', None)
        if vendor_employee and vendor_employee.is_active:
            employee_locations = vendor_employee.locations.filter(is_active=True).values_list('name', flat=True)
            if employee_locations:
                location_filter = (
                    Q(part__plant__in=employee_locations) | 
                    Q(part__storage_location__in=employee_locations) | 
                    Q(part__warehouse_number__in=employee_locations)
                )
                item_filters &= location_filter
            else:
                raise PermissionDenied("You don't have access to any locations.")

        has_items = order.items.filter(item_filters).exists()
        if not has_items:
            raise PermissionDenied("This order doesn't contain any of your parts for your assigned locations.")
        
        return order
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Order #{self.object.order_number}'
        
        vendor_partner = get_vendor_context(self.request.user)
        
        # Prefetch specifically the status for THIS vendor to avoid fetching other vendors' statuses
        status_prefetch = Prefetch(
            'vendor_statuses',
            queryset=VendorOrderItemStatus.objects.filter(vendor=vendor_partner),
            to_attr='current_vendor_status' # Store in a specific attribute
        )

        # Get vendor's items with optimized queries
        item_filters = Q(part__vendor=vendor_partner)
        
        # Location-based filtering for vendor employees
        vendor_employee = getattr(self.request.user, 'vendor_employee', None)
        if vendor_employee and vendor_employee.is_active:
            employee_locations = vendor_employee.locations.filter(is_active=True).values_list('name', flat=True)
            if employee_locations:
                location_filter = (
                    Q(part__plant__in=employee_locations) | 
                    Q(part__storage_location__in=employee_locations) | 
                    Q(part__warehouse_number__in=employee_locations)
                )
                item_filters &= location_filter
            else:
                item_filters = Q(pk__in=[])

        vendor_items = self.object.items.filter(
            item_filters
        ).select_related(
            'part', 'part__brand', 'part__category'
        ).prefetch_related(
            status_prefetch
        )
        
        enhanced_vendor_items = []
        vendor_statuses_list = []

        for item in vendor_items:
            # PERFORMANCE FIX: Use the prefetched list (to_attr) instead of .filter()
            # which would hit the DB again for every item.
            vendor_status_obj = item.current_vendor_status[0] if item.current_vendor_status else None
            
            current_status = vendor_status_obj.status if vendor_status_obj else self.object.status
            # Fallback for display if no vendor specific status exists
            status_display = vendor_status_obj.get_status_display() if vendor_status_obj else self.object.get_status_display()

            try:
                from core.models import ExchangeRate
                from decimal import Decimal as D
            except Exception:
                ExchangeRate = None
                D = Decimal

            unit_price_usd = None
            if getattr(item, 'vendor_currency_amount', None):
                original_currency_code = (getattr(item, 'original_currency_code', None) or getattr(item.part, 'original_currency', None) or 'USD').upper()
                if getattr(item, 'locked_exchange_rate', None):
                    if original_currency_code == 'USD':
                        unit_price_usd = item.vendor_currency_amount
                    else:
                        unit_price_usd = item.vendor_currency_amount * item.locked_exchange_rate
                else:
                    if original_currency_code == 'USD':
                        unit_price_usd = item.vendor_currency_amount
                    elif ExchangeRate:
                        unit_price_usd = item.vendor_currency_amount * D(str(ExchangeRate.get_current_rate(original_currency_code, 'USD')))

            if unit_price_usd is None:
                original_currency_code = (getattr(item, 'original_currency_code', None) or getattr(item.part, 'original_currency', None) or 'USD').upper()
                if original_currency_code == 'USD':
                    unit_price_usd = item.part.standard_price
                elif ExchangeRate:
                    unit_price_usd = item.part.standard_price * D(str(ExchangeRate.get_current_rate(original_currency_code, 'USD')))
                else:
                    unit_price_usd = item.price

            line_subtotal_usd = unit_price_usd * item.quantity
            item_tax = getattr(item, 'tax_amount', None)
            if item_tax is None:
                item_tax = Decimal('0.00')
            tax_rate = (item_tax / line_subtotal_usd).quantize(Decimal('0.0001')) if line_subtotal_usd else Decimal('0.0000')
            tax_classification = getattr(item.part, 'tax_classification_material', None)
            if tax_classification == 'VAT_5':
                tax_rate_display = '5%'
            elif tax_classification == 'ZERO':
                tax_rate_display = '0% (Zero Rated)'
            elif tax_classification == 'EXEMPT':
                tax_rate_display = 'Exempt'
            else:
                tax_rate_display = f"{(tax_rate * Decimal('100')).quantize(Decimal('0.01'))}%"
            item_total_with_tax = line_subtotal_usd + item_tax
            
            # Get vendor currency amounts using locked exchange rates
            vendor_currency_amount = None
            vendor_currency_code = None
            vendor_currency_total = None
            vendor_currency_tax = None
            vendor_currency_grand_total = None
            
            if hasattr(item, 'vendor_currency_amount') and item.vendor_currency_amount:
                vendor_currency_amount = item.vendor_currency_amount
                vendor_currency_code = item.original_currency_code if hasattr(item, 'original_currency_code') else 'USD'
                vendor_currency_total = item.quantity * vendor_currency_amount
                vendor_currency_tax = vendor_currency_total * tax_rate
                vendor_currency_grand_total = vendor_currency_total + vendor_currency_tax
            else:
                vendor_currency_code = (getattr(item.part, 'original_currency', None) or getattr(item, 'original_currency_code', None) or 'USD').upper()
                vendor_currency_amount = item.part.standard_price
                vendor_currency_total = item.quantity * vendor_currency_amount
                vendor_currency_tax = vendor_currency_total * tax_rate
                vendor_currency_grand_total = vendor_currency_total + vendor_currency_tax

            item_data = {
                'item': item,
                'vendor_status': vendor_status_obj,
                'current_status': current_status,
                'status_display': status_display,
                'tracking_number': vendor_status_obj.tracking_number if vendor_status_obj else None,
                'status_updated_at': vendor_status_obj.updated_at if vendor_status_obj else None,
                'unit_price_usd': unit_price_usd,
                'line_subtotal_usd': line_subtotal_usd,
                'tax_rate': tax_rate,
                'tax_rate_display': tax_rate_display,
                'tax_amount': item_tax,
                'total_with_tax': item_total_with_tax,
                'vendor_currency_amount': vendor_currency_amount,
                'vendor_currency_code': vendor_currency_code,
                'vendor_currency_total': vendor_currency_total,
                'vendor_currency_tax': vendor_currency_tax,
                'vendor_currency_grand_total': vendor_currency_grand_total
            }
            enhanced_vendor_items.append(item_data)
            vendor_statuses_list.append(current_status)
        
        # Calculate vendor's overall status
        vendor_overall_status = 'pending'
        vendor_overall_status_display = 'Pending'
        vendor_next_action = 'confirm'

        if vendor_statuses_list:
            if all(s == 'delivered' for s in vendor_statuses_list):
                vendor_overall_status = 'delivered'
                vendor_overall_status_display = 'Delivered'
                vendor_next_action = None
            elif all(s == 'cancelled' for s in vendor_statuses_list):
                vendor_overall_status = 'cancelled'
                vendor_overall_status_display = 'Cancelled'
                vendor_next_action = None
            elif 'shipped' in vendor_statuses_list:
                vendor_overall_status = 'shipped'
                vendor_overall_status_display = 'Shipped'
                vendor_next_action = 'deliver'
            elif 'processing' in vendor_statuses_list:
                vendor_overall_status = 'processing'
                vendor_overall_status_display = 'Processing'
                vendor_next_action = 'ship'
            elif 'confirmed' in vendor_statuses_list:
                vendor_overall_status = 'confirmed'
                vendor_overall_status_display = 'Confirmed'
                vendor_next_action = 'process'
            elif all(s == 'pending' for s in vendor_statuses_list):
                vendor_overall_status = 'pending'
                vendor_overall_status_display = 'Pending'
                vendor_next_action = 'confirm'
            else:
                # Mixed/Fallthrough state
                vendor_overall_status = 'pending'
                vendor_overall_status_display = 'Pending'
        
        context['enhanced_vendor_items'] = enhanced_vendor_items
        # context['vendor_items'] = vendor_items # Removed redundant queryset to prevent confusion in template
        context['vendor_overall_status'] = vendor_overall_status
        context['vendor_overall_status_display'] = vendor_overall_status_display
        context['vendor_next_action'] = vendor_next_action
        
        # Calculate Total Price (Quantity * Price) and Tax
        vendor_items_total = Decimal('0.00')
        vendor_tax_total = Decimal('0.00')
        
        for item_data in enhanced_vendor_items:
            vendor_items_total += item_data.get('line_subtotal_usd') or Decimal('0.00')
            vendor_tax_total += item_data['tax_amount']
            
        context['vendor_items_total'] = vendor_items_total
        context['vendor_tax_total'] = vendor_tax_total
        context['vendor_grand_total'] = vendor_items_total + vendor_tax_total
        
        # Status History
        context['vendor_status_history'] = VendorOrderItemStatus.objects.filter(
            order_item__order=self.object,
            vendor=vendor_partner
        ).select_related('order_item', 'order_item__part').order_by('-updated_at')
        
        context['status_history'] = self.object.status_history.order_by('-timestamp')
        
        # Handle RelatedObjectDoesNotExist safely
        context['shipping_info'] = getattr(self.object, 'shipping_info', None)
        context['discount_info'] = getattr(self.object, 'discount_info', None)
        
        return context


logger = logging.getLogger(__name__)

@login_required
@require_POST
@transaction.atomic
def vendor_update_order_status(request, order_id):
    """
    Endpoint for vendors to update order status for their specific items.
    """
    # Helper to return error based on request type
    def send_error(message, status_code=400):
        if request.headers.get('HX-Request'):
            return HttpResponse(message, status=status_code)
        return JsonResponse({'success': False, 'error': message}, status=status_code)

    try:
        order = get_object_or_404(Order, id=order_id)
        
        vendor_partner = get_vendor_context(request.user)
            
        if not vendor_partner:
            return send_error("Vendor access required.", 403)
        
        # Check if this order contains parts from this vendor
        vendor_items = order.items.filter(part__vendor=vendor_partner).select_related('part')
        
        if not vendor_items.exists():
            return send_error("This order doesn't contain any of your parts.", 403)
        
        # Get inputs
        new_status = request.POST.get('status')
        tracking_number = request.POST.get('tracking_number', '').strip()
        notes = request.POST.get('notes', '').strip()
        
        if not new_status:
            return send_error('Status parameter is required.')
        
        # Validate status
        valid_statuses = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded']
        if new_status not in valid_statuses:
            return send_error(f'Invalid status: {new_status}')
        
        # Update Items
        updated_count = 0
        for item in vendor_items:
            # Get or create vendor-specific status
            vendor_status, created = VendorOrderItemStatus.objects.get_or_create(
                order_item=item,
                vendor=vendor_partner,
                defaults={'status': 'pending'}
            )
            
            previous_status = vendor_status.status
            
            # Update fields
            vendor_status.status = new_status
            if tracking_number:
                vendor_status.tracking_number = tracking_number
            if notes:
                vendor_status.notes = notes
            vendor_status.save()
            
            # Create History Log
            if previous_status != new_status or notes:
                OrderStatusHistory.objects.create(
                    order=order,
                    previous_status=previous_status,
                    new_status=new_status,
                    changed_by=request.user,
                    change_reason=f'Updated by {vendor_partner.name}',
                    notes=f"Item: {item.part.name} - {notes}" if notes else f"Item: {item.part.name} status updated"
                )
            
            updated_count += 1
        
        # Update Overall Order Status (Simplified Logic)
        all_order_items = order.items.all()
        status_list = []
        
        for item in all_order_items:
            # Safely get the status using related manager
            # Adjust 'vendor_statuses' if your related_name is different
            v_stats = item.vendor_statuses.all() 
            if v_stats.exists():
                status_list.append(v_stats.latest('updated_at').status)
            else:
                status_list.append(order.status)
        
        new_order_status = order.status
        if status_list:
            if all(s == 'cancelled' for s in status_list): new_order_status = 'cancelled'
            elif all(s == 'delivered' for s in status_list): new_order_status = 'delivered'
            elif any(s == 'shipped' for s in status_list): new_order_status = 'shipped'
            elif any(s == 'processing' for s in status_list): new_order_status = 'processing'
            elif any(s == 'confirmed' for s in status_list): new_order_status = 'confirmed'
        
        if new_order_status != order.status:
            order.status = new_order_status
            order.save()
            
            # If the order is now delivered, trigger escrow release timer in Finance System
            if new_order_status == 'delivered':
                from finance.services import FinanceService
                FinanceService.trigger_delivery_settlement(order)

        # HTMX Success Response
        if request.headers.get('HX-Request'):
            response = HttpResponse("Status Updated")
            response['HX-Refresh'] = "true"
            return response

        return JsonResponse({
            'success': True,
            'message': f'Updated items to {new_status}.',
        })
        
    except Exception as e:
        # Print actual error to console for debugging
        print("\n!!!!!!!!!!!! SERVER ERROR !!!!!!!!!!!!")
        print(traceback.format_exc())
        return HttpResponseServerError(f"Server Error: {str(e)}")


@login_required
@vendor_required
def vendor_order_analytics(request):
    """Vendor-specific order analytics dashboard."""
    vendor_partner = get_vendor_context(request.user)
    
    if not vendor_partner:
        messages.error(request, 'Vendor access required.')
        return redirect('business_partners:vendor_dashboard')
    
    # Get date range from request
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if not date_from:
        date_from = (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not date_to:
        date_to = timezone.now().strftime('%Y-%m-%d')
    
    # Convert to datetime objects
    try:
        date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
        date_to_dt = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
    except ValueError:
        date_from_dt = timezone.now() - timedelta(days=30)
        date_to_dt = timezone.now()
    
    # Get vendor orders in date range
    vendor_orders = Order.objects.filter(
        items__part__vendor=vendor_partner,
        created_at__range=[date_from_dt, date_to_dt]
    ).distinct()
    
    # Order status breakdown
    status_breakdown = vendor_orders.values('status').annotate(
        count=Count('id'),
        total_revenue=Sum(F('items__quantity') * F('items__price'))
    ).order_by('status')
    
    # Daily order trends
    daily_orders = vendor_orders.extra(
        select={'day': 'date(parts_order.created_at)'}
    ).values('day').annotate(
        order_count=Count('id'),
        revenue=Sum(F('items__quantity') * F('items__price'))
    ).order_by('day')
    
    # Top selling parts
    top_parts = vendor_orders.values(
        'items__part__name',
        'items__part__sku'
    ).annotate(
        total_quantity=Sum('items__quantity'),
        total_revenue=Sum(F('items__quantity') * F('items__price'))
    ).order_by('-total_quantity')[:10]
    
    # Recent orders
    recent_orders = vendor_orders.order_by('-created_at')[:10]
    
    context = {
        'title': 'Order Analytics',
        'business_partner': vendor_partner,
        'vendor_profile': getattr(vendor_partner, 'vendor_profile', None),
        'date_from': date_from,
        'date_to': date_to,
        'total_orders': vendor_orders.count(),
        'total_revenue': vendor_orders.aggregate(
            total=Sum(F('items__quantity') * F('items__price'))
        )['total'] or 0,
        'status_breakdown': status_breakdown,
        'daily_orders': daily_orders,
        'top_parts': top_parts,
        'recent_orders': recent_orders,
        'average_order_value': vendor_orders.aggregate(
            avg=Avg(F('items__quantity') * F('items__price'))
        )['avg'] or 0,
    }
    
    return render(request, 'business_partners/vendor_order_analytics.html', context)


@login_required
@vendor_required
def vendor_order_reports(request):
    """Generate and download order reports for vendors."""
    vendor_partner = get_vendor_context(request.user)
    
    if not vendor_partner:
        messages.error(request, 'Vendor access required.')
        return redirect('business_partners:vendor_dashboard')
    
    # Get filter parameters
    report_type = request.GET.get('report_type', 'summary')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    status = request.GET.get('status')
    
    if not date_from:
        date_from = (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not date_to:
        date_to = timezone.now().strftime('%Y-%m-%d')
    
    # Get vendor orders based on filters
    vendor_orders = Order.objects.filter(
        items__part__vendor=vendor_partner
    ).distinct()
    
    # Apply date filter
    try:
        date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
        date_to_dt = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
        vendor_orders = vendor_orders.filter(created_at__range=[date_from_dt, date_to_dt])
    except ValueError:
        pass
    
    # Apply status filter
    if status and status != 'all':
        vendor_orders = vendor_orders.filter(status=status)
    
    if report_type == 'csv':
        # Generate CSV report
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="vendor_orders_{date_from}_to_{date_to}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Order Number', 'Date', 'Customer', 'Status', 'Total Amount',
            'Vendor Items Total', 'Shipping Cost', 'Payment Method', 'Tracking Number'
        ])
        
        for order in vendor_orders:
            vendor_items_total = order.items.filter(
                part__vendor=vendor_partner
            ).aggregate(total=Sum(F('quantity') * F('price')))['total'] or 0
            
            writer.writerow([
                order.order_number,
                order.created_at.strftime('%Y-%m-%d %H:%M'),
                order.customer.email if order.customer else order.guest_name,
                order.get_status_display(),
                order.total_price,
                vendor_items_total,
                order.shipping_cost,
                order.get_payment_method_display(),
                order.tracking_number or ''
            ])
        
        return response
    
    else:
        # Show report preview
        context = {
            'title': 'Order Reports',
            'business_partner': vendor_partner,
            'vendor_profile': getattr(vendor_partner, 'vendor_profile', None),
            'date_from': date_from,
            'date_to': date_to,
            'status': status,
            'report_type': report_type,
            'orders': vendor_orders,
            'total_orders': vendor_orders.count(),
            'total_revenue': vendor_orders.aggregate(
                total=Sum(F('items__quantity') * F('items__price'))
            )['total'] or 0,
        }
        
        return render(request, 'business_partners/vendor_order_reports.html', context)
