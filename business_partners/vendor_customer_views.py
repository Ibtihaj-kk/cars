from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from django.db.models import Count, Sum, F, Q, OuterRef, Subquery, CharField
from django.db.models.functions import Coalesce
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.db.models import Prefetch
from decimal import Decimal
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
            customer_bp_number=Coalesce(
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
            vendor_partner = vendor_profile.business_partner
            
            # Unfiltered count for the dashboard stat
            base_qs = User.objects.filter(
                orders__items__part__vendor=vendor_partner
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
            try:
                from core.models import ExchangeRate
                from decimal import Decimal as D
            except Exception:
                ExchangeRate = None
                D = Decimal

            def _tax_rate(order_item):
                tax_classification = getattr(order_item.part, 'tax_classification_material', None)
                if tax_classification == 'VAT_5':
                    return Decimal('0.05')
                if tax_classification in ('ZERO', 'EXEMPT'):
                    return Decimal('0.00')
                return Decimal('0.15')

            currency_rates_to_usd = {}

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
                        if original_currency_code not in currency_rates_to_usd:
                            currency_rates_to_usd[original_currency_code] = D(str(ExchangeRate.get_current_rate(original_currency_code, 'USD')))
                        return vendor_amount * currency_rates_to_usd[original_currency_code]
                    return order_item.price

                if original_currency_code == 'USD':
                    return order_item.part.standard_price
                if ExchangeRate:
                    if original_currency_code not in currency_rates_to_usd:
                        currency_rates_to_usd[original_currency_code] = D(str(ExchangeRate.get_current_rate(original_currency_code, 'USD')))
                    return order_item.part.standard_price * currency_rates_to_usd[original_currency_code]
                return order_item.price

            total_revenue = Decimal('0.00')
            all_items = (
                OrderItem.objects.filter(
                    part__vendor=vendor_partner,
                    order__status__in=['delivered', 'shipped', 'processing'],
                )
                .select_related('part', 'order')
            )
            for item in all_items:
                line_subtotal = (_unit_price_usd(item) or Decimal('0.00')) * item.quantity
                total_revenue += line_subtotal + (line_subtotal * _tax_rate(item))
            
            count = base_qs.count()
            context['avg_spend'] = round(total_revenue / count, 0) if count > 0 else 0
            
            context['search_query'] = self.request.GET.get('search', '')

            customers_page = context.get('customers')
            customers_list = list(customers_page) if customers_page else []
            customer_ids = [c.id for c in customers_list]

            page_items = (
                OrderItem.objects.filter(
                    order__customer_id__in=customer_ids,
                    part__vendor=vendor_partner,
                    order__status__in=['delivered', 'shipped', 'processing'],
                )
                .select_related('part', 'order')
            )

            totals_by_customer = {cid: Decimal('0.00') for cid in customer_ids}
            for item in page_items:
                line_subtotal = (_unit_price_usd(item) or Decimal('0.00')) * item.quantity
                totals_by_customer[item.order.customer_id] += line_subtotal + (line_subtotal * _tax_rate(item))

            for customer in customers_list:
                customer.vendor_total_spent = totals_by_customer.get(customer.id, Decimal('0.00'))
            
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

            try:
                from core.models import ExchangeRate
                from decimal import Decimal as D
            except Exception:
                ExchangeRate = None
                D = Decimal

            currency_rates_to_usd = {}

            def _tax_rate(order_item):
                tax_classification = getattr(order_item.part, 'tax_classification_material', None)
                if tax_classification == 'VAT_5':
                    return Decimal('0.05')
                if tax_classification in ('ZERO', 'EXEMPT'):
                    return Decimal('0.00')
                return Decimal('0.15')

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
                        if original_currency_code not in currency_rates_to_usd:
                            currency_rates_to_usd[original_currency_code] = D(str(ExchangeRate.get_current_rate(original_currency_code, 'USD')))
                        return vendor_amount * currency_rates_to_usd[original_currency_code]
                    return order_item.price

                if original_currency_code == 'USD':
                    return order_item.part.standard_price
                if ExchangeRate:
                    if original_currency_code not in currency_rates_to_usd:
                        currency_rates_to_usd[original_currency_code] = D(str(ExchangeRate.get_current_rate(original_currency_code, 'USD')))
                    return order_item.part.standard_price * currency_rates_to_usd[original_currency_code]
                return order_item.price
            
            # Get orders for this customer from this vendor
            vendor_items_prefetch = Prefetch(
                'items',
                queryset=OrderItem.objects.filter(part__vendor=vendor_partner).select_related('part'),
                to_attr='vendor_items',
            )

            orders = (
                Order.objects.filter(
                    customer=customer,
                    items__part__vendor=vendor_partner,
                )
                .distinct()
                .order_by('-created_at')
                .prefetch_related(vendor_items_prefetch)
            )

            orders_list = list(orders)
            total_spent = Decimal('0.00')
            for order in orders_list:
                order_total = Decimal('0.00')
                items = getattr(order, 'vendor_items', []) or []
                for item in items:
                    line_subtotal = (_unit_price_usd(item) or Decimal('0.00')) * item.quantity
                    order_total += line_subtotal + (line_subtotal * _tax_rate(item))
                order.vendor_total = order_total
                order.vendor_items_count = len(items)
                if order.status in ['delivered', 'shipped', 'processing']:
                    total_spent += order_total
            
            context['orders'] = orders_list
            context['orders_count'] = len(orders_list)
            context['vendor_total_spent'] = total_spent
            
            # Last order date
            last_order = orders_list[0] if orders_list else None
            context['last_order_date'] = last_order.created_at if last_order else None
            
            context['vendor_profile'] = vendor_profile
            
        return context
