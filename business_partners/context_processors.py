"""
Context processors for business partners and vendor access.
"""
from django.db import models
from .permissions import get_vendor_profile, user_has_vendor_access
from parts.models import Order, OrderItem


def vendor_access(request):
    """
    Context processor to add vendor access information to all templates.
    """
    context = {
        'has_vendor_access': False,
        'vendor_profile': None,
        'pending_orders_count': 0,
        'reorder_alerts_count': 0,
    }
    
    if hasattr(request, 'user') and request.user.is_authenticated:
        context['has_vendor_access'] = user_has_vendor_access(request.user)
        vendor_profile = get_vendor_profile(request.user)
        context['vendor_profile'] = vendor_profile
        
        # Get pending orders count for vendor
        if vendor_profile:
            business_partner = vendor_profile.business_partner
            pending_orders = Order.objects.filter(
                items__part__vendor=business_partner,
                status__in=['pending', 'confirmed']
            ).distinct().count()
            context['pending_orders_count'] = pending_orders
            
            # Get reorder alerts count
            from parts.models import Inventory
            reorder_alerts = Inventory.objects.filter(
                part__vendor=business_partner,
                stock__lte=models.F('reorder_level')
            ).count()
            context['reorder_alerts_count'] = reorder_alerts
    
    return context