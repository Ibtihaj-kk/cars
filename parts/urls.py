from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router for API endpoints
router = DefaultRouter()
router.register(r'parts', views.PartViewSet)  # API ViewSet for parts

app_name = 'parts'

urlpatterns = [
    # Public views
    path('', views.PartListView.as_view(), name='part_list'),
    path('part/<int:pk>/', views.PartDetailView.as_view(), name='part_detail'),
    
    # Role-based parts search and filtering views
    path('search/user/', views.UserPartsListView.as_view(), name='user_parts_search'),
    path('search/vendor/', views.VendorPartsListView.as_view(), name='vendor_parts_search'),
    path('search/admin/', views.AdminPartsListView.as_view(), name='admin_parts_search'),
    
    # HTMX partial views
    path('htmx/parts-results/', views.parts_results_partial, name='parts_results_partial'),
    path('htmx/vehicle-models/', views.vehicle_models_partial, name='vehicle_models_partial'),
    
    # Dealer/Admin Dashboard
    path('dealer/', views.DealerDashboardView.as_view(), name='dealer_dashboard'),
    path('dealer/parts/', views.DealerPartListView.as_view(), name='dealer_part_list'),
    
    # Parts CRUD operations
    path('dealer/part/add/', views.PartCreateView.as_view(), name='part_create'),
    path('dealer/part/<int:pk>/edit/', views.PartUpdateView.as_view(), name='part_update'),
    path('dealer/part/<int:pk>/delete/', views.PartDeleteView.as_view(), name='part_delete'),
    path('dealer/part/<int:pk>/activate/', views.part_activate, name='part_activate'),
    path('dealer/part/<int:pk>/deactivate/', views.part_deactivate, name='part_deactivate'),
    
    # Inventory management
    path('dealer/part/<int:part_pk>/inventory/', views.InventoryUpdateView.as_view(), name='inventory_update'),
    
    # AJAX endpoints for dashboard
    path('ajax/low-stock-alerts/', views.low_stock_alerts_ajax, name='low_stock_alerts_ajax'),
    path('ajax/inventory-analytics/', views.inventory_analytics_ajax, name='inventory_analytics_ajax'),
    
    # Legacy/Future endpoints (to be implemented)
    path('search/', views.PartListView.as_view(), name='parts_search'),
    path('category/<str:category>/', views.PartListView.as_view(), name='parts_by_category'),
    path('part/<int:pk>/order/', views.PartDetailView.as_view(), name='part_order'),  # Will redirect to order form
    
    # User-specific views
    path('my-orders/', views.MyOrdersView.as_view(), name='my_orders'),
    path('my-inventory/', views.MyInventoryView.as_view(), name='my_inventory'),
    path('order/<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    
    # Order management (to be implemented)
    path('orders/', views.PartListView.as_view(), name='order_list'),  # Placeholder
    path('order/<int:pk>/update/', views.PartDetailView.as_view(), name='order_update'),  # Placeholder
    
    # Guest ordering (to be implemented)
    path('guest-order/', views.PartListView.as_view(), name='guest_order'),  # Placeholder
    path('guest-order/success/', views.PartListView.as_view(), name='guest_order_success'),  # Placeholder
    
    # Cart functionality
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<int:part_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item_universal, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart_universal, name='remove_from_cart'),
    path('cart/clear/', views.clear_cart_universal, name='clear_cart'),
    
    # Buy Now functionality
    path('buy-now/', views.buy_now, name='buy_now'),
    path('api/cart/count/', views.cart_count_api, name='cart_count_api'),
    
    # Multi-step Checkout functionality
    path('checkout/step1/', views.checkout_step1_order_summary, name='checkout_step1'),
    path('checkout/step2/', views.checkout_step2_shipping_info, name='checkout_step2'),
    path('checkout/step3/', views.checkout_step3_payment_method, name='checkout_step3'),
    path('order-confirmation/<str:order_number>/', views.order_confirmation, name='order_confirmation'),
    
    # AJAX endpoints for checkout
    path('ajax/city-areas/', views.get_city_areas, name='get_city_areas'),
    path('ajax/verify-discount/', views.verify_discount_code, name='verify_discount_code'),
    
    # CSV Upload
    path('dealer/csv-upload/', views.CSVUploadView.as_view(), name='csv_upload'),
    
    # API Import
    path('dealer/api-import/', views.api_import_view, name='api_import'),
    path('api/import/<int:source_id>/', views.fetch_api_parts, name='fetch_api_parts'),
    
    # Integration Source Management (placeholder for future implementation)
    # path('dealer/integration-sources/', views.IntegrationSourceListView.as_view(), name='integration_source_list'),
    # path('dealer/integration-source/add/', views.IntegrationSourceCreateView.as_view(), name='integration_source_create'),
    
    # API endpoints
    path('api/', include(router.urls)),
    # path('api/search/', views.api_parts_search, name='api_parts_search'),  # To be implemented
    # path('api/categories/', views.api_categories, name='api_categories'),  # To be implemented
]