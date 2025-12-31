from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from django.db.models import Count, Sum, F, Q, OuterRef, Subquery, CharField
from django.db.models.functions import Coalesce
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from parts.models import Order, OrderItem
from .models import BusinessPartner
from .utils import get_vendor_profile

User = get_user_model()

class VendorCustomerListView(LoginRequiredMixin, ListView):
    template_name = 'vendors/customers.html'
    context_object_name = 'customers'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        vendor_profile = get_vendor_profile(user)
        if not vendor_profile:
            return User.objects.none()

        vendor_partner = vendor_profile.business_partner

        # Get users who have ordered items from this vendor
        qs = User.objects.filter(
            orders__items__part__vendor=vendor_partner
        ).distinct()

        # Search
        search = self.request.GET.get('search')
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )

        # Annotate with stats specific to this vendor
        customer_bp_number_subquery = BusinessPartner.objects.filter(
            user=OuterRef('pk'),
            roles__role_type='customer',
        ).order_by('-created_at').values('bp_number')[:1]
        any_bp_number_subquery = BusinessPartner.objects.filter(
            user=OuterRef('pk'),
        ).order_by('-created_at').values('bp_number')[:1]

        qs = qs.annotate(
            vendor_orders_count=Count(
                'orders',
                filter=Q(orders__items__part__vendor=vendor_partner),
                distinct=True
            ),
            vendor_total_spent=Sum(
                F('orders__items__quantity') * F('orders__items__price'),
                filter=Q(orders__items__part__vendor=vendor_partner) & 
                       Q(orders__status__in=['delivered', 'shipped', 'processing'])
            ),
            bp_number=Coalesce(
                Subquery(customer_bp_number_subquery),
                Subquery(any_bp_number_subquery),
                output_field=CharField(),
            ),
        )
        
        # Order by most recent join date by default
        return qs.order_by('-date_joined')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vendor_profile = get_vendor_profile(self.request.user)
        if vendor_profile:
            context['vendor_profile'] = vendor_profile
            
            # Unfiltered count for the dashboard stat
            base_qs = User.objects.filter(
                orders__items__part__vendor=vendor_profile.business_partner
            ).distinct()
            context['total_customers_count'] = base_qs.count()
            
            # Active customers
            context['active_customers'] = base_qs.filter(is_active=True).count()
            
            # New customers (this month)
            now = timezone.now()
            context['new_customers'] = base_qs.filter(
                date_joined__year=now.year,
                date_joined__month=now.month
            ).count()
            
            # Avg Spend
            total_revenue = OrderItem.objects.filter(
                part__vendor=vendor_profile.business_partner,
                order__status__in=['delivered', 'shipped', 'processing']
            ).aggregate(
                total=Sum(F('quantity') * F('price'))
            )['total'] or 0
            
            count = base_qs.count()
            context['avg_spend'] = round(total_revenue / count, 0) if count > 0 else 0
            
            context['search_query'] = self.request.GET.get('search', '')
            
        return context

class VendorCustomerDetailView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'vendors/customer_detail.html'
    context_object_name = 'customer'

    def get_object(self):
        user_id = self.kwargs.get('pk')
        customer = get_object_or_404(User, pk=user_id)
        
        # Verify this customer belongs to the vendor
        vendor_profile = get_vendor_profile(self.request.user)
        if not vendor_profile:
            raise PermissionDenied
            
        has_orders = Order.objects.filter(
            customer=customer,
            items__part__vendor=vendor_profile.business_partner
        ).exists()
        
        if not has_orders:
            raise PermissionDenied
            
        return customer

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vendor_profile = get_vendor_profile(self.request.user)
        customer = self.object
        
        if vendor_profile:
            vendor_partner = vendor_profile.business_partner
            
            # Get orders for this customer from this vendor
            orders = Order.objects.filter(
                customer=customer,
                items__part__vendor=vendor_partner
            ).distinct().order_by('-created_at')
            
            # Annotate orders with vendor specific totals
            orders = orders.annotate(
                vendor_total=Sum(
                    F('items__quantity') * F('items__price'),
                    filter=Q(items__part__vendor=vendor_partner)
                ),
                vendor_items_count=Count(
                    'items',
                    filter=Q(items__part__vendor=vendor_partner)
                )
            )
            
            context['orders'] = orders
            context['orders_count'] = orders.count()
            
            # Calculate total spent
            total_spent = OrderItem.objects.filter(
                order__customer=customer,
                part__vendor=vendor_partner,
                order__status__in=['delivered', 'shipped', 'processing']
            ).aggregate(
                total=Sum(F('quantity') * F('price'))
            )['total'] or 0
            
            context['vendor_total_spent'] = total_spent
            
            # Last order date
            last_order = orders.first()
            context['last_order_date'] = last_order.created_at if last_order else None
            
            context['vendor_profile'] = vendor_profile
            
        return context
