from .models import VendorProfile, BusinessPartner, CustomerProfile


COUNTRY_TO_CURRENCY = {
    'United States': 'USD',
    'USA': 'USD',
    'United Kingdom': 'GBP',
    'UK': 'GBP',
    'Saudi Arabia': 'SAR',
    'United Arab Emirates': 'AED',
    'UAE': 'AED',
    'Pakistan': 'PKR',
    'Canada': 'CAD',
    'Australia': 'AUD',
    'Japan': 'JPY',
    'China': 'CNY',
    'India': 'INR',
    'Germany': 'EUR',
    'France': 'EUR',
    'Italy': 'EUR',
    'Spain': 'EUR',
    'Netherlands': 'EUR',
    # Add more as needed
}

def get_currency_for_country(country_name):
    """
    Get the currency code for a given country name.
    Returns 3-letter currency code (e.g., 'USD', 'AED').
    Defaults to 'USD' if not found.
    """
    if not country_name:
        return 'USD'
    
    # Get currency code from mapping
    currency_code = COUNTRY_TO_CURRENCY.get(country_name, 'USD')
    
    # Return the currency code (3-letter string)
    return currency_code


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
            roles__role_type='vendor'
        ).distinct()
        
        if not business_partners.exists():
            return None
            
        # Return the vendor profile for the first active vendor business partner
        business_partner = business_partners.first()
        return business_partner.vendor_profile
    except VendorProfile.DoesNotExist:
        return None


def get_customer_profile(user):
    """
    Get the customer profile for a given user.
    """
    if not user.is_authenticated:
        return None
        
    try:
        # Get all business partners for this user that are active customers
        business_partners = BusinessPartner.objects.filter(
            user=user,
            status='active',
            roles__role_type='customer'
        ).distinct()
        
        if not business_partners.exists():
            return None
            
        # Return the customer profile for the first active customer business partner
        business_partner = business_partners.first()
        if hasattr(business_partner, 'customer_profile'):
            return business_partner.customer_profile
        return None
    except Exception:
        return None


def get_user_currency(user):
    """
    Get the preferred currency for a user (Vendor or Customer).
    Defaults to 'USD'.
    """
    if not user or not user.is_authenticated:
        return 'USD'

    # Check vendor profile
    vendor_profile = get_vendor_profile(user)
    if vendor_profile:
        return vendor_profile.preferred_currency
    
    # Check customer profile
    customer_profile = get_customer_profile(user)
    if customer_profile:
        return customer_profile.preferred_currency
        
    return 'USD'


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