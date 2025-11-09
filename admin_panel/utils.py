"""
Utility functions for admin panel operations including activity logging.
"""
from django.contrib.contenttypes.models import ContentType
from .models import ActivityLog, ActivityLogType


def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent_info(request):
    """Get user agent information from request."""
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    # Basic user agent parsing
    info = {
        'user_agent': user_agent,
        'is_mobile': False,
        'is_tablet': False,
        'is_desktop': True,
        'browser': 'Unknown',
        'os': 'Unknown'
    }
    
    if user_agent:
        user_agent_lower = user_agent.lower()
        
        # Detect mobile devices
        mobile_indicators = ['mobile', 'android', 'iphone', 'ipod', 'blackberry', 'windows phone']
        info['is_mobile'] = any(indicator in user_agent_lower for indicator in mobile_indicators)
        
        # Detect tablets
        tablet_indicators = ['tablet', 'ipad']
        info['is_tablet'] = any(indicator in user_agent_lower for indicator in tablet_indicators)
        
        # Adjust desktop flag
        info['is_desktop'] = not (info['is_mobile'] or info['is_tablet'])
        
        # Basic browser detection
        if 'chrome' in user_agent_lower:
            info['browser'] = 'Chrome'
        elif 'firefox' in user_agent_lower:
            info['browser'] = 'Firefox'
        elif 'safari' in user_agent_lower and 'chrome' not in user_agent_lower:
            info['browser'] = 'Safari'
        elif 'edge' in user_agent_lower:
            info['browser'] = 'Edge'
        elif 'opera' in user_agent_lower:
            info['browser'] = 'Opera'
        
        # Basic OS detection
        if 'windows' in user_agent_lower:
            info['os'] = 'Windows'
        elif 'mac' in user_agent_lower:
            info['os'] = 'macOS'
        elif 'linux' in user_agent_lower:
            info['os'] = 'Linux'
        elif 'android' in user_agent_lower:
            info['os'] = 'Android'
        elif 'ios' in user_agent_lower or 'iphone' in user_agent_lower or 'ipad' in user_agent_lower:
            info['os'] = 'iOS'
    
    return info


def log_activity(user, action_type, description, content_object=None, request=None, data=None):
    """
    Log an activity for audit trail.
    
    Args:
        user: User who performed the action
        action_type: Type of action (from ActivityLogType)
        description: Human-readable description of the action
        content_object: The object this action was performed on (optional)
        request: HTTP request object (optional, for IP and user agent)
        data: Additional data to store (optional)
    
    Returns:
        ActivityLog instance
    """
    log_data = {
        'user': user,
        'action_type': action_type,
        'description': description,
        'data': data or {},
    }
    
    # Add content object if provided
    if content_object:
        log_data['content_type'] = ContentType.objects.get_for_model(content_object)
        log_data['object_id'] = content_object.pk
    
    # Add request information if provided
    if request:
        log_data['ip_address'] = get_client_ip(request)
        log_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
    
    return ActivityLog.objects.create(**log_data)


def log_listing_activity(user, action_type, listing, description=None, request=None, data=None):
    """
    Convenience function to log vehicle listing activities.
    
    Args:
        user: User who performed the action
        action_type: Type of action (from ActivityLogType)
        listing: VehicleListing object
        description: Custom description (auto-generated if None)
        request: HTTP request object (optional)
        data: Additional data to store (optional)
    
    Returns:
        ActivityLog instance
    """
    if not description:
        action_map = {
            ActivityLogType.CREATE: f"Created vehicle listing: {listing.title}",
            ActivityLogType.UPDATE: f"Updated vehicle listing: {listing.title}",
            ActivityLogType.DELETE: f"Deleted vehicle listing: {listing.title}",
            ActivityLogType.VIEW: f"Viewed vehicle listing: {listing.title}",
        }
        description = action_map.get(action_type, f"Performed {action_type} on listing: {listing.title}")
    
    # Add listing-specific data
    listing_data = {
        'listing_id': listing.id,
        'listing_title': listing.title,
        'listing_status': listing.status,
        'listing_make': listing.make,
        'listing_model': listing.model,
        'listing_year': listing.year,
        'listing_price': str(listing.price),
    }
    
    if data:
        listing_data.update(data)
    
    return log_activity(
        user=user,
        action_type=action_type,
        description=description,
        content_object=listing,
        request=request,
        data=listing_data
    )


def log_bulk_listing_activity(user, action_type, listings, action_name, request=None):
    """
    Log bulk operations on vehicle listings.
    
    Args:
        user: User who performed the action
        action_type: Type of action (from ActivityLogType)
        listings: QuerySet or list of VehicleListing objects
        action_name: Name of the bulk action (e.g., 'publish', 'delete')
        request: HTTP request object (optional)
    
    Returns:
        ActivityLog instance
    """
    count = len(listings) if hasattr(listings, '__len__') else listings.count()
    listing_ids = [listing.id for listing in listings]
    
    description = f"Bulk {action_name} operation on {count} vehicle listings"
    
    data = {
        'bulk_action': action_name,
        'count': count,
        'listing_ids': listing_ids,
    }
    
    return log_activity(
        user=user,
        action_type=action_type,
        description=description,
        request=request,
        data=data
    )


def log_status_change_activity(user, listing, old_status, new_status, request=None):
    """
    Log vehicle listing status changes.
    
    Args:
        user: User who performed the action
        listing: VehicleListing object
        old_status: Previous status
        new_status: New status
        request: HTTP request object (optional)
    
    Returns:
        ActivityLog instance
    """
    description = f"Changed status of '{listing.title}' from {old_status} to {new_status}"
    
    data = {
        'listing_id': listing.id,
        'old_status': old_status,
        'new_status': new_status,
        'status_change': True,
    }
    
    return log_activity(
        user=user,
        action_type=ActivityLogType.UPDATE,
        description=description,
        content_object=listing,
        request=request,
        data=data
    )


def log_feature_toggle_activity(user, listing, is_featured, request=None):
    """
    Log vehicle listing feature toggle.
    
    Args:
        user: User who performed the action
        listing: VehicleListing object
        is_featured: New featured status
        request: HTTP request object (optional)
    
    Returns:
        ActivityLog instance
    """
    action = "Featured" if is_featured else "Unfeatured"
    description = f"{action} vehicle listing: {listing.title}"
    
    data = {
        'listing_id': listing.id,
        'is_featured': is_featured,
        'feature_toggle': True,
    }
    
    return log_activity(
        user=user,
        action_type=ActivityLogType.UPDATE,
        description=description,
        content_object=listing,
        request=request,
        data=data
    )