from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from django.db import transaction
from .models import Cart, CartItem, Part

@receiver(user_logged_in)
def merge_cart_on_login(sender, user, request, **kwargs):
    """
    Merge session cart into user's database cart upon login.
    """
    if not request:
        return

    session_cart = request.session.get('cart', {})
    
    if not session_cart:
        return

    with transaction.atomic():
        # Get or create user's cart
        user_cart, created = Cart.objects.get_or_create(user=user)
        
        for part_id_str, item_data in session_cart.items():
            try:
                part_id = int(part_id_str)
                part = Part.objects.get(id=part_id, is_active=True)
                quantity = item_data.get('quantity', 1)
                
                # Check if item already exists in user cart
                cart_item, created = CartItem.objects.get_or_create(
                    cart=user_cart,
                    part=part,
                    defaults={'quantity': quantity}
                )
                
                if not created:
                    # Update quantity if item exists
                    # Check stock limits
                    new_quantity = cart_item.quantity + quantity
                    if new_quantity <= part.quantity:
                        cart_item.quantity = new_quantity
                        cart_item.save()
                    else:
                        # Cap at max available stock
                        cart_item.quantity = part.quantity
                        cart_item.save()
                        
            except (Part.DoesNotExist, ValueError):
                continue
                
        # Clear session cart after merging
        if 'cart' in request.session:
            del request.session['cart']
            request.session.modified = True
