"""
Vendor Order Management Views
Handles vendor-specific order processing, order management, and order-related functionality
for business partners (vendors).
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import ListView, DetailView, UpdateView
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseForbidden
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Count, Sum, F, Prefetch, Case, When, Value, Avg
from django.db import transaction
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta, datetime
import json

from parts.models import Order, OrderItem, OrderStatusHistory, OrderShipping, OrderDiscount
from .models import BusinessPartner, VendorProfile
from .decorators import vendor_required
from .utils import get_vendor_profile


class VendorOrderListView(LoginRequiredMixin, ListView):
    """Vendor-specific view to list orders containing their parts."""
    model = Order
    template_name = 'business_partners/vendor_orders_list_standardized.html'
    context_object_name = 'orders'
    paginate_by = 20
    
    def get_queryset(self):
        """Return orders that contain parts from the current vendor."""
        user = self.request.user
        vendor_profile = get_vendor_profile(user)
        
        if not vendor_profile:
            return Order.objects.none()
        
        # Get orders that contain parts from this vendor
        return Order.objects.filter(
            items__part__vendor=vendor_profile.business_partner
        ).distinct().select_related(
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
        
        # Get vendor profile
        vendor_profile = get_vendor_profile(self.request.user)
        if vendor_profile:
            # Add vendor profile to context for template
            context['vendor_profile'] = vendor_profile
            # Order statistics for this vendor
            vendor_orders = self.get_queryset()
            
            context['total_orders'] = vendor_orders.count()
            
            # Status counts for dashboard cards
            context['status_counts'] = {
                'pending': vendor_orders.filter(status='pending').count(),
                'processing': vendor_orders.filter(status='processing').count(),
                'completed': vendor_orders.filter(status='delivered').count(),  # Using 'delivered' as 'completed'
            }
            
            # Keep individual counts for backward compatibility
            context['pending_orders'] = vendor_orders.filter(status='pending').count()
            context['confirmed_orders'] = vendor_orders.filter(status='confirmed').count()
            context['processing_orders'] = vendor_orders.filter(status='processing').count()
            context['shipped_orders'] = vendor_orders.filter(status='shipped').count()
            context['delivered_orders'] = vendor_orders.filter(status='delivered').count()
            context['cancelled_orders'] = vendor_orders.filter(status='cancelled').count()
            
            # Revenue statistics
            context['total_revenue'] = vendor_orders.filter(
                status__in=['delivered', 'shipped']
            ).aggregate(
                total=Sum(F('items__quantity') * F('items__price'))
            )['total'] or 0
            
            # Recent activity
            context['recent_orders'] = vendor_orders[:5]
            
            # Status filter from URL
            status_filter = self.request.GET.get('status')
            if status_filter:
                context['status_filter'] = status_filter  # Changed from current_status_filter to match template
            
            # Filter parameters for form persistence
            context['search_query'] = self.request.GET.get('search', '')
            context['date_from'] = self.request.GET.get('date_from', '')
            context['date_to'] = self.request.GET.get('date_to', '')
            context['min_amount'] = self.request.GET.get('min_amount', '')
            context['max_amount'] = self.request.GET.get('max_amount', '')
        
        return context


class VendorOrderDetailView(LoginRequiredMixin, DetailView):
    """Detailed view of an order for vendors (only shows their parts)."""
    model = Order
    template_name = 'business_partners/vendor_order_detail.html'
    context_object_name = 'order'
    
    def get_object(self):
        """Get order and verify vendor has parts in this order."""
        order = super().get_object()
        user = self.request.user
        vendor_profile = get_vendor_profile(user)
        
        if not vendor_profile:
            raise PermissionDenied("You don't have vendor access.")
        
        # Check if this order contains parts from this vendor
        vendor_items = order.items.filter(part__vendor=vendor_profile.business_partner)
        if not vendor_items.exists():
            raise PermissionDenied("This order doesn't contain any of your parts.")
        
        return order
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Order #{self.object.order_number}'
        
        # Get vendor profile
        vendor_profile = get_vendor_profile(self.request.user)
        
        # Get only the vendor's items from this order
        vendor_items = self.object.items.filter(
            part__vendor=vendor_profile.business_partner
        ).select_related(
            'part', 'part__brand', 'part__category'
        )
        
        context['vendor_items'] = vendor_items
        context['vendor_items_total'] = vendor_items.aggregate(
            total=Sum(F('quantity') * F('price'))
        )['total'] or 0
        
        # Get order status history
        context['status_history'] = self.object.status_history.order_by('-timestamp')
        
        # Get shipping information
        try:
            context['shipping_info'] = self.object.shipping_info
        except OrderShipping.DoesNotExist:
            context['shipping_info'] = None
        
        # Get discount information
        try:
            context['discount_info'] = self.object.discount_info
        except OrderDiscount.DoesNotExist:
            context['discount_info'] = None
        
        return context


@login_required
@require_POST
def vendor_update_order_status(request, order_id):
    """AJAX endpoint for vendors to update order status for their parts."""
    try:
        order = get_object_or_404(Order, id=order_id)
        vendor_profile = get_vendor_profile(request.user)
        
        if not vendor_profile:
            return JsonResponse({
                'success': False,
                'error': 'Vendor profile not found.'
            })
        
        # Check if this order contains parts from this vendor
        vendor_items = order.items.filter(part__vendor=vendor_profile.business_partner)
        if not vendor_items.exists():
            return JsonResponse({
                'success': False,
                'error': 'This order doesn\'t contain any of your parts.'
            })
        
        # Get new status and tracking info
        new_status = request.POST.get('status')
        tracking_number = request.POST.get('tracking_number', '').strip()
        notes = request.POST.get('notes', '').strip()
        
        # Validate status transition
        valid_transitions = {
            'pending': ['confirmed', 'cancelled'],
            'confirmed': ['processing', 'cancelled'],
            'processing': ['shipped', 'cancelled'],
            'shipped': ['delivered'],
            'delivered': [],
            'cancelled': [],
            'refunded': []
        }
        
        if new_status not in valid_transitions.get(order.status, []):
            return JsonResponse({
                'success': False,
                'error': f'Invalid status transition from {order.status} to {new_status}.'
            })
        
        # Update order status
        previous_status = order.status
        order.status = new_status
        
        if tracking_number:
            order.tracking_number = tracking_number
        
        if notes:
            order.notes = notes
        
        order.save()
        
        # Create status history entry
        OrderStatusHistory.objects.create(
            order=order,
            previous_status=previous_status,
            new_status=new_status,
            changed_by=request.user,
            change_reason=f'Updated by vendor {vendor_profile.business_partner.name}',
            notes=notes
        )
        
        # Update timestamps for specific statuses
        if new_status == 'shipped':
            order.shipped_at = timezone.now()
            order.save()
        elif new_status == 'delivered':
            order.delivered_at = timezone.now()
            order.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Order status updated to {new_status} successfully.',
            'new_status': new_status,
            'status_display': order.get_status_display()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def vendor_order_analytics(request):
    """Vendor-specific order analytics dashboard."""
    vendor_profile = get_vendor_profile(request.user)
    
    if not vendor_profile:
        messages.error(request, 'Vendor profile not found.')
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
        items__part__vendor=vendor_profile.business_partner,
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
        'vendor_profile': vendor_profile,
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
def vendor_order_reports(request):
    """Generate and download order reports for vendors."""
    vendor_profile = get_vendor_profile(request.user)
    
    if not vendor_profile:
        messages.error(request, 'Vendor profile not found.')
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
        items__part__vendor=vendor_profile.business_partner
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
                part__vendor=vendor_profile.business_partner
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
            'vendor_profile': vendor_profile,
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