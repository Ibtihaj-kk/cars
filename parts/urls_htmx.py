"""
HTMX URL Patterns for Parts Module
"""
from django.urls import path
from . import htmx_views

app_name = 'parts_htmx'

urlpatterns = [
    # Parts Catalog
    path('parts/', htmx_views.parts_list_htmx, name='parts_list'),
    path('parts/<int:part_id>/', htmx_views.part_detail_htmx, name='part_detail'),

    # Shopping Cart
    path('cart/', htmx_views.cart_view_htmx, name='cart_view'),
    path('cart/add/<int:part_id>/', htmx_views.add_to_cart_htmx, name='add_to_cart'),
    path('cart/update/<int:item_id>/', htmx_views.update_cart_item_htmx, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', htmx_views.remove_cart_item_htmx, name='remove_cart_item'),

    # Checkout
    path('checkout/', htmx_views.checkout_htmx, name='checkout'),
    path('checkout/place-order/', htmx_views.place_order_htmx, name='place_order'),

    # Orders
    path('orders/', htmx_views.orders_list_htmx, name='orders_list'),
    path('orders/<int:order_id>/', htmx_views.order_detail_htmx, name='order_detail'),

    # Filter Helpers
    path('models/<int:make_id>/', htmx_views.get_models_by_make_htmx, name='get_models'),
    path('categories/', htmx_views.get_categories_htmx, name='get_categories'),
]
