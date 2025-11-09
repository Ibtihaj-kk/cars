"""
Order Processing Workflow Views
Handles the complete order processing workflow from new orders to fulfillment
including automated status transitions, notifications, and inventory management.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import ListView, DetailView, UpdateView
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponse
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Count, Sum, F, Prefetch, Case, When, Value
from django.db import transaction
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta, datetime
import json
import csv

from parts.models import Order, OrderItem, OrderStatusHistory, InventoryTransaction
from .models import BusinessPartner, VendorProfile
from .decorators import vendor_required
from .utils import get_vendor_profile
# from notifications.utils import send_order_notification  # Not available, will implement simple version

def send_order_notification(order, action, user):
    """Simple notification function for order status changes."""
    # This is a placeholder for order notifications
    # In a real system, this would send emails, push notifications, etc.
    pass


class OrderProcessingDashboardView(LoginRequiredMixin, ListView):
    """Enhanced order processing dashboard with workflow management."""
    model = Order
    template_name = 'business_partners/order_processing_dashboard.html'
    context_object_name = 'orders'
    paginate_by = 25
    
    def get_queryset(self):
        """Return orders based on user role and filters."""
        user = self.request.user
        
        # Base queryset with optimizations
        queryset = Order.objects.select_related(
            'customer', 'shipping_info', 'discount_info'
        ).prefetch_related(
            'order_items__part',
            'order_items__part__brand',
            'order_items__part__category',
            'status_history__changed_by'
        )
        
        # Filter by vendor if user is a vendor
        if hasattr(user, 'business_partner'):
            vendor_profile = get_vendor_profile(user)
            if vendor_profile:
                queryset = queryset.filter(
                    order_items__part__vendor=vendor_profile.business_partner
                ).distinct()
        
        # Apply filters from request
        status_filter = self.request.GET.get('status')
        priority_filter = self.request.GET.get('priority')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        search_query = self.request.GET.get('search')
        
        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        
        if priority_filter and priority_filter != 'all':
            queryset = queryset.filter(priority=priority_filter)
        
        if date_from:
            try:
                date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
                queryset = queryset.filter(created_at__gte=date_from_dt)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_dt = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
                queryset = queryset.filter(created_at__lte=date_to_dt)
            except ValueError:
                pass
        
        if search_query:
            queryset = queryset.filter(
                Q(order_number__icontains=search_query) |
                Q(customer__email__icontains=search_query) |
                Q(guest_email__icontains=search_query) |
                Q(guest_name__icontains=search_query)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Order Processing Dashboard'
        
        # Get workflow statistics
        base_orders = self.get_queryset()
        
        # Status breakdown
        context['status_breakdown'] = base_orders.values('status').annotate(
            count=Count('id'),
            total_value=Sum('total_price')
        ).order_by('status')
        
        # Priority breakdown
        context['priority_breakdown'] = base_orders.values('priority').annotate(
            count=Count('id')
        ).order_by('priority')
        
        # Time-based analytics
        today = timezone.now().date()
        last_7_days = today - timedelta(days=7)
        last_30_days = today - timedelta(days=30)
        
        context['orders_today'] = base_orders.filter(
            created_at__date=today
        ).count()
        
        context['orders_this_week'] = base_orders.filter(
            created_at__date__gte=last_7_days
        ).count()
        
        context['orders_this_month'] = base_orders.filter(
            created_at__date__gte=last_30_days
        ).count()
        
        # Processing metrics
        context['avg_processing_time'] = self.calculate_avg_processing_time(base_orders)
        context['fulfillment_rate'] = self.calculate_fulfillment_rate(base_orders)
        
        # Current filters
        context['current_status'] = self.request.GET.get('status', 'all')
        context['current_priority'] = self.request.GET.get('priority', 'all')
        context['current_search'] = self.request.GET.get('search', '')
        context['current_date_from'] = self.request.GET.get('date_from', '')
        context['current_date_to'] = self.request.GET.get('date_to', '')
        
        # Status choices for filter dropdown
        context['status_choices'] = Order.STATUS_CHOICES
        context['priority_choices'] = [
            ('high', 'High'),
            ('medium', 'Medium'),
            ('low', 'Low'),
        ]
        
        return context
    
    def calculate_avg_processing_time(self, orders):
        """Calculate average processing time for delivered orders."""
        delivered_orders = orders.filter(
            status='delivered',
            created_at__isnull=False,
            delivered_at__isnull=False
        )
        
        if not delivered_orders.exists():
            return 0
        
        total_days = 0
        count = 0
        
        for order in delivered_orders:
            if order.delivered_at and order.created_at:
                days = (order.delivered_at - order.created_at).days
                total_days += days
                count += 1
        
        return round(total_days / count, 1) if count > 0 else 0
    
    def calculate_fulfillment_rate(self, orders):
        """Calculate order fulfillment rate."""
        total_orders = orders.count()
        if total_orders == 0:
            return 0
        
        fulfilled_orders = orders.filter(
            status__in=['delivered', 'shipped']
        ).count()
        
        return round((fulfilled_orders / total_orders) * 100, 1)


class OrderProcessingDetailView(LoginRequiredMixin, DetailView):
    """Detailed order view with processing actions and workflow controls."""
    model = Order
    template_name = 'business_partners/order_processing_detail.html'
    context_object_name = 'order'
    
    def get_object(self):
        """Get order with vendor-specific filtering."""
        order = super().get_object()
        user = self.request.user
        
        # If user is a vendor, check if order contains their parts
        if hasattr(user, 'business_partner'):
            vendor_profile = get_vendor_profile(user)
            if vendor_profile:
                vendor_items = order.order_items.filter(
                    part__vendor=vendor_profile.business_partner
                )
                if not vendor_items.exists():
                    raise PermissionDenied("This order doesn't contain any of your parts.")
        
        return order
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.object
        
        context['title'] = f'Order #{order.order_number} Processing'
        
        # Get vendor-specific items if user is vendor
        user = self.request.user
        if hasattr(user, 'business_partner'):
            vendor_profile = get_vendor_profile(user)
            if vendor_profile:
                context['vendor_items'] = order.order_items.filter(
                    part__vendor=vendor_profile.business_partner
                ).select_related('part', 'part__brand')
        
        # Stock availability check
        context['stock_status'] = self.check_stock_availability(order)
        
        # Available status transitions
        context['available_transitions'] = self.get_available_transitions(order)
        
        # Processing timeline
        context['processing_timeline'] = self.get_processing_timeline(order)
        
        # Next actions
        context['next_actions'] = self.get_next_actions(order)
        
        # Related information
        context['status_history'] = order.status_history.select_related('changed_by').order_by('-timestamp')[:10]
        
        try:
            context['shipping_info'] = order.shipping_info
        except OrderShipping.DoesNotExist:
            context['shipping_info'] = None
        
        try:
            context['discount_info'] = order.discount_info
        except OrderDiscount.DoesNotExist:
            context['discount_info'] = None
        
        return context
    
    def check_stock_availability(self, order):
        """Check stock availability for all items in the order."""
        stock_status = []
        
        for item in order.order_items.all():
            inventory = item.part.inventory
            if inventory:
                available = inventory.quantity
                required = item.quantity
                status = {
                    'part': item.part,
                    'available': available,
                    'required': required,
                    'sufficient': available >= required,
                    'stock_status': inventory.stock_status
                }
                stock_status.append(status)
        
        return stock_status
    
    def get_available_transitions(self, order):
        """Get available status transitions based on current status."""
        valid_transitions = {
            'pending': ['confirmed', 'cancelled'],
            'confirmed': ['processing', 'cancelled'],
            'processing': ['shipped', 'cancelled'],
            'shipped': ['delivered'],
            'delivered': [],
            'cancelled': [],
            'refunded': []
        }
        
        current_status = order.status
        return valid_transitions.get(current_status, [])
    
    def get_processing_timeline(self, order):
        """Get processing timeline with key milestones."""
        timeline = []
        
        # Order placed
        if order.created_at:
            timeline.append({
                'timestamp': order.created_at,
                'event': 'Order Placed',
                'status': 'pending',
                'icon': 'shopping-cart'
            })
        
        # Status changes
        for history in order.status_history.order_by('timestamp'):
            timeline.append({
                'timestamp': history.timestamp,
                'event': f'Status Changed to {history.get_new_status_display()}',
                'status': history.new_status,
                'icon': 'exchange-alt',
                'changed_by': history.changed_by
            })
        
        # Shipping
        if order.shipped_at:
            timeline.append({
                'timestamp': order.shipped_at,
                'event': 'Order Shipped',
                'status': 'shipped',
                'icon': 'truck',
                'tracking_number': order.tracking_number
            })
        
        # Delivery
        if order.delivered_at:
            timeline.append({
                'timestamp': order.delivered_at,
                'event': 'Order Delivered',
                'status': 'delivered',
                'icon': 'check-circle'
            })
        
        return sorted(timeline, key=lambda x: x['timestamp'])
    
    def get_next_actions(self, order):
        """Get recommended next actions based on current status."""
        actions = []
        
        if order.status == 'pending':
            actions.append({
                'action': 'confirm',
                'label': 'Confirm Order',
                'description': 'Review and confirm the order',
                'icon': 'check',
                'color': 'success'
            })
            actions.append({
                'action': 'cancel',
                'label': 'Cancel Order',
                'description': 'Cancel the order',
                'icon': 'times',
                'color': 'danger'
            })
        
        elif order.status == 'confirmed':
            actions.append({
                'action': 'process',
                'label': 'Start Processing',
                'description': 'Begin order processing',
                'icon': 'cogs',
                'color': 'primary'
            })
        
        elif order.status == 'processing':
            actions.append({
                'action': 'ship',
                'label': 'Mark as Shipped',
                'description': 'Update order as shipped',
                'icon': 'truck',
                'color': 'info'
            })
        
        elif order.status == 'shipped':
            actions.append({
                'action': 'deliver',
                'label': 'Mark as Delivered',
                'description': 'Confirm order delivery',
                'icon': 'check-circle',
                'color': 'success'
            })
        
        return actions


@login_required
@require_POST
def process_order_action(request, order_id):
    """Handle order processing actions with validation and automation."""
    try:
        order = get_object_or_404(Order, id=order_id)
        
        # Check permissions
        if not request.user.is_staff and hasattr(request.user, 'business_partner'):
            vendor_profile = get_vendor_profile(request.user)
            if not vendor_profile:
                return JsonResponse({
                    'success': False,
                    'error': 'Vendor profile not found.'
                })
            
            # Check if order contains vendor's parts
            vendor_items = order.order_items.filter(
                part__vendor=vendor_profile.business_partner
            )
            if not vendor_items.exists():
                return JsonResponse({
                    'success': False,
                    'error': 'This order doesn\'t contain any of your parts.'
                })
        
        action = request.POST.get('action')
        notes = request.POST.get('notes', '').strip()
        tracking_number = request.POST.get('tracking_number', '').strip()
        
        # Validate action
        valid_actions = ['confirm', 'process', 'ship', 'deliver', 'cancel']
        if action not in valid_actions:
            return JsonResponse({
                'success': False,
                'error': f'Invalid action: {action}'
            })
        
        # Process action with validation
        with transaction.atomic():
            result = process_order_workflow_action(order, action, request.user, {
                'notes': notes,
                'tracking_number': tracking_number,
                'request': request
            })
            
            if result['success']:
                # Send notifications
                send_order_notification(order, action, request.user)
                
                return JsonResponse({
                    'success': True,
                    'message': result['message'],
                    'new_status': order.status,
                    'status_display': order.get_status_display()
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result['error']
                })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


def process_order_workflow_action(order, action, user, options=None):
    """Core function to process order workflow actions with validation."""
    options = options or {}
    notes = options.get('notes', '')
    tracking_number = options.get('tracking_number', '')
    request = options.get('request')
    
    # Define status transitions
    status_transitions = {
        'confirm': 'confirmed',
        'process': 'processing',
        'ship': 'shipped',
        'deliver': 'delivered',
        'cancel': 'cancelled'
    }
    
    new_status = status_transitions.get(action)
    if not new_status:
        return {'success': False, 'error': f'Invalid action: {action}'}
    
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
        return {
            'success': False,
            'error': f'Cannot transition from {order.status} to {new_status}'
        }
    
    # Action-specific validations and processing
    if action == 'confirm':
        # Check stock availability before confirming
        stock_available, stock_message = order.check_stock_availability()
        if not stock_available:
            return {
                'success': False,
                'error': f'Cannot confirm order: {stock_message}'
            }
    
    elif action == 'process':
        # Deduct inventory when processing
        try:
            order.deduct_inventory()
        except ValueError as e:
            return {
                'success': False,
                'error': f'Cannot process order: {str(e)}'
            }
    
    elif action == 'ship':
        if not tracking_number:
            return {
                'success': False,
                'error': 'Tracking number is required for shipping'
            }
        order.tracking_number = tracking_number
    
    elif action == 'cancel':
        # Restore inventory for cancelled orders
        if order.status in ['confirmed', 'processing']:
            try:
                order.restore_inventory()
            except Exception as e:
                return {
                    'success': False,
                    'error': f'Cannot cancel order: {str(e)}'
                }
    
    # Update order status
    previous_status = order.status
    order.status = new_status
    
    # Update timestamps
    if new_status == 'shipped':
        order.shipped_at = timezone.now()
    elif new_status == 'delivered':
        order.delivered_at = timezone.now()
    
    order.save()
    
    # Create status history
    OrderStatusHistory.objects.create(
        order=order,
        previous_status=previous_status,
        new_status=new_status,
        changed_by=user,
        change_reason=f'Order {action}ed by {user.get_full_name() or user.email}',
        notes=notes,
        ip_address=request.META.get('REMOTE_ADDR') if request else None,
        user_agent=request.META.get('HTTP_USER_AGENT') if request else None
    )
    
    return {
        'success': True,
        'message': f'Order {action}ed successfully'
    }


@login_required
def order_processing_api(request, order_id):
    """API endpoint for order processing operations."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        order = get_object_or_404(Order, id=order_id)
        
        # Check permissions
        if not request.user.is_staff and hasattr(request.user, 'business_partner'):
            vendor_profile = get_vendor_profile(request.user)
            if not vendor_profile:
                return JsonResponse({'error': 'Vendor profile not found'}, status=403)
            
            vendor_items = order.order_items.filter(
                part__vendor=vendor_profile.business_partner
            )
            if not vendor_items.exists():
                return JsonResponse({'error': 'No vendor parts in this order'}, status=403)
        
        action = request.POST.get('action')
        if not action:
            return JsonResponse({'error': 'Action is required'}, status=400)
        
        result = process_order_workflow_action(order, action, request.user, {
            'request': request,
            'notes': request.POST.get('notes', ''),
            'tracking_number': request.POST.get('tracking_number', '')
        })
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': result['message'],
                'new_status': order.status,
                'status_display': order.get_status_display()
            })
        else:
            return JsonResponse({'error': result['error']}, status=400)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def bulk_order_processing(request):
    """Handle bulk order processing actions."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        order_ids = request.POST.getlist('order_ids[]')
        action = request.POST.get('action')
        
        if not order_ids or not action:
            return JsonResponse({'error': 'Order IDs and action are required'}, status=400)
        
        results = []
        processed_count = 0
        error_count = 0
        
        for order_id in order_ids:
            try:
                order = Order.objects.get(id=order_id)
                
                # Check permissions
                if not request.user.is_staff and hasattr(request.user, 'business_partner'):
                    vendor_profile = get_vendor_profile(request.user)
                    if not vendor_profile:
                        results.append({
                            'order_id': order_id,
                            'success': False,
                            'error': 'Vendor profile not found'
                        })
                        error_count += 1
                        continue
                    
                    vendor_items = order.order_items.filter(
                        part__vendor=vendor_profile.business_partner
                    )
                    if not vendor_items.exists():
                        results.append({
                            'order_id': order_id,
                            'success': False,
                            'error': 'No vendor parts in this order'
                        })
                        error_count += 1
                        continue
                
                result = process_order_workflow_action(order, action, request.user, {
                    'request': request
                })
                
                if result['success']:
                    processed_count += 1
                    results.append({
                        'order_id': order_id,
                        'success': True,
                        'message': result['message']
                    })
                else:
                    error_count += 1
                    results.append({
                        'order_id': order_id,
                        'success': False,
                        'error': result['error']
                    })
            
            except Order.DoesNotExist:
                error_count += 1
                results.append({
                    'order_id': order_id,
                    'success': False,
                    'error': 'Order not found'
                })
        
        return JsonResponse({
            'success': True,
            'processed_count': processed_count,
            'error_count': error_count,
            'total_count': len(order_ids),
            'results': results
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)