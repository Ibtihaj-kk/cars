def cache_clearing(request):
    """
    Context processor to enable cache clearing for development environments.
    Returns a flag indicating whether cache clearing should be enabled.
    """
    host = request.get_host()
    
    # Enable cache clearing for localhost and 127.0.0.1 in development
    is_development = (
        host.startswith('localhost:') or 
        host.startswith('127.0.0.1:') or
        (DEBUG and any(host.startswith(dev_host) for dev_host in ['localhost', '127.0.0.1']))
    )
    
    return {
        'SHOW_CACHE_CLEARING': is_development
    }