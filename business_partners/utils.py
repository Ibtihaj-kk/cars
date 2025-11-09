from .models import VendorProfile, BusinessPartner


def get_vendor_profile(user):
    """
    Get the vendor profile for a given user.
    Returns None if no vendor profile exists.
    Handles multiple BusinessPartner records by returning the first active vendor.
    """
    try:
        # Get all business partners for this user that are active vendors
        business_partners = BusinessPartner.objects.filter(
            user=user,
            status='active',
            businesspartnerrole__role_type='vendor'
        ).distinct()
        
        if not business_partners.exists():
            return None
            
        # Return the vendor profile for the first active vendor business partner
        business_partner = business_partners.first()
        return business_partner.vendor_profile
    except VendorProfile.DoesNotExist:
        return None


def get_vendor_from_request(request):
    """
    Get the vendor profile from the request object.
    Returns None if user is not authenticated or has no vendor profile.
    """
    if not request.user.is_authenticated:
        return None
    
    return get_vendor_profile(request.user)


def is_vendor_approved(user):
    """
    Check if a user has an approved vendor profile.
    """
    vendor_profile = get_vendor_profile(user)
    if vendor_profile is None:
        return False
    
    # Check if the business partner is active and has vendor role
    business_partner = vendor_profile.business_partner
    return (business_partner.status == 'active' and 
            business_partner.has_role('vendor'))


def get_vendor_stats(vendor_profile):
    """
    Get various statistics for a vendor profile.
    """
    from orders.models import Order, OrderItem
    from parts.models import Part
    
    # Get all parts owned by this vendor
    vendor_parts = Part.objects.filter(vendor=vendor_profile)
    
    # Get all order items for this vendor's parts
    vendor_order_items = OrderItem.objects.filter(part__in=vendor_parts)
    
    # Get all orders containing this vendor's parts
    vendor_orders = Order.objects.filter(order_items__in=vendor_order_items).distinct()
    
    # Calculate statistics
    total_orders = vendor_orders.count()
    pending_orders = vendor_orders.filter(status='pending').count()
    confirmed_orders = vendor_orders.filter(status='confirmed').count()
    processing_orders = vendor_orders.filter(status='processing').count()
    delivered_orders = vendor_orders.filter(status='delivered').count()
    
    # Calculate total revenue
    total_revenue = sum(
        item.quantity * item.price_at_purchase
        for item in vendor_order_items.filter(order__status='delivered')
    )
    
    return {
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'confirmed_orders': confirmed_orders,
        'processing_orders': processing_orders,
        'delivered_orders': delivered_orders,
        'total_revenue': total_revenue,
        'total_parts': vendor_parts.count(),
    }