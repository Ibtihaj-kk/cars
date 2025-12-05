"""
HTMX URL Patterns for Business Partners/Vendors Module
"""
from django.urls import path
from . import htmx_views

app_name = 'vendors_htmx'

urlpatterns = [
    # Vendor Dashboard
    path('dashboard/', htmx_views.vendor_dashboard_htmx, name='dashboard'),

    # Inventory Management
    path('inventory/', htmx_views.vendor_inventory_htmx, name='inventory'),
    path('inventory/add/', htmx_views.vendor_part_form_htmx, name='part_add_form'),
    path('inventory/edit/<int:part_id>/', htmx_views.vendor_part_form_htmx, name='part_edit_form'),
    path('inventory/save/', htmx_views.vendor_save_part_htmx, name='part_save'),
    path('inventory/save/<int:part_id>/', htmx_views.vendor_save_part_htmx, name='part_update'),
    path('inventory/toggle/<int:part_id>/', htmx_views.vendor_toggle_part_status_htmx, name='part_toggle_status'),
    path('inventory/delete/<int:part_id>/', htmx_views.vendor_delete_part_htmx, name='part_delete'),
    path('inventory/stock/<int:part_id>/', htmx_views.vendor_update_stock_htmx, name='update_stock'),

    # Orders Management
    path('orders/', htmx_views.vendor_orders_htmx, name='orders'),
    path('orders/<int:order_id>/', htmx_views.vendor_order_detail_htmx, name='order_detail'),
    path('orders/<int:order_id>/status/', htmx_views.vendor_update_order_status_htmx, name='update_order_status'),

    # Analytics
    path('analytics/', htmx_views.vendor_analytics_htmx, name='analytics'),

    # Registration
    path('register/', htmx_views.vendor_registration_form_htmx, name='registration_form'),
    path('registration/validate/', htmx_views.vendor_registration_validate_htmx, name='registration_validate'),
    path('registration/submit/', htmx_views.vendor_registration_submit_htmx, name='registration_submit'),
    path('register/submit/', htmx_views.vendor_submit_application_htmx, name='submit_application'),
    
    # Vendor Login HTMX
    path('login/form/', htmx_views.vendor_login_form_htmx, name='login_form'),
    path('login/validate/', htmx_views.vendor_login_validate_htmx, name='login_validate'),
    path('login/submit/', htmx_views.vendor_login_submit_htmx, name='login_submit'),
    path('login/status/', htmx_views.vendor_login_status_htmx, name='login_status'),
]
