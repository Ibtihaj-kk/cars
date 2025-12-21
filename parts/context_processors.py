def cart_processor(request):
    """
    Context processor to make cart count available globally.
    Works for both authenticated (DB) and guest (session) users.
    """
    cart_count = 0
    
    try:
        if request.user.is_authenticated:
            try:
                from .models import Cart
                # Efficiently count items in the user's cart
                # Assuming Cart has a 'user' OneToOneField and 'items' related manager
                # We can optimize this by caching or using a property if available, 
                # but for now a direct query is safe.
                cart = Cart.objects.filter(user=request.user).first()
                if cart:
                    # specific aggregation can be faster, but list comprehension is robust for small carts
                    # Assuming items have a quantity field
                    cart_items = cart.items.all()
                    cart_count = sum(item.quantity for item in cart_items)
            except Exception:
                pass
        else:
            # Guest user - calculate from session
            session_cart = request.session.get('cart', {})
            if session_cart:
                cart_count = sum(item.get('quantity', 0) for item in session_cart.values())
    except Exception:
        pass
            
    return {
        'cart_count': cart_count
    }
