from django.utils.text import slugify
from django.utils import timezone
import uuid
import re


def generate_unique_slug(instance, field_name, new_slug=None):
    """Generate a unique slug for a model instance.
    
    Args:
        instance: Model instance
        field_name: Name of the field to slugify
        new_slug: Optional slug to use instead of generating from field_name
        
    Returns:
        A unique slug string
    """
    if new_slug is not None:
        slug = new_slug
    else:
        field_value = getattr(instance, field_name)
        slug = slugify(field_value)
    
    # Get model class
    model_class = instance.__class__
    
    # Check if slug exists
    slug_exists = model_class.objects.filter(slug=slug).exists()
    
    # If this is an update and the slug hasn't changed, return it
    if instance.pk is not None:
        existing_instance = model_class.objects.filter(pk=instance.pk).first()
        if existing_instance and existing_instance.slug == slug:
            return slug
    
    # If slug exists, append a UUID
    if slug_exists:
        unique_slug = f"{slug}-{str(uuid.uuid4())[:8]}"
        return generate_unique_slug(instance, field_name, new_slug=unique_slug)
    
    return slug


def clean_phone_number(phone_number):
    """Clean a phone number by removing non-digit characters.
    
    Args:
        phone_number: Phone number string
        
    Returns:
        Cleaned phone number string
    """
    if not phone_number:
        return ""
    
    # Remove all non-digit characters
    return re.sub(r'\D', '', phone_number)


def format_currency(amount, currency='AED'):
    """Format a currency amount.
    
    Args:
        amount: Numeric amount
        currency: Currency code (default: AED)
        
    Returns:
        Formatted currency string
    """
    if amount is None:
        return ""
    
    # Format with 2 decimal places
    formatted = f"{float(amount):,.2f}"
    
    # Remove trailing zeros after decimal point
    if '.' in formatted:
        formatted = formatted.rstrip('0').rstrip('.') if '.' in formatted else formatted
    
    # Add currency code
    return f"{formatted} {currency}"


def get_client_ip(request):
    """Get the client IP address from a request.
    
    Args:
        request: Django request object
        
    Returns:
        IP address string
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def is_valid_uuid(val):
    """Check if a string is a valid UUID.
    
    Args:
        val: String to check
        
    Returns:
        Boolean indicating if the string is a valid UUID
    """
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, AttributeError, TypeError):
        return False