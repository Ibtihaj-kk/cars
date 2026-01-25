from business_partners.utils import get_business_partner_for_user

def get_vendor_context(user):
    """
    Get the vendor (BusinessPartner) associated with the user.
    Handles both master vendor users and vendor employees.
    """
    # Check if user is a master vendor
    business_partner = get_business_partner_for_user(user)
    if business_partner and business_partner.roles.filter(role_type='vendor').exists():
        return business_partner
    
    # Check if user is a vendor employee
    from .models import VendorEmployee
    employee = VendorEmployee.objects.select_related('vendor').filter(
        user=user, 
        is_active=True
    ).first()
    
    if employee:
        return employee.vendor
        
    return None
