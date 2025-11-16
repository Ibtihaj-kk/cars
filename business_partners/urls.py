"""
URL patterns for business partners app - vendor registration system and authentication.
Handles multi-step vendor registration workflow, authentication, and admin approval process.
"""

from django.urls import path
from . import views
from . import vendor_views
from . import auth_views
from . import vendor_order_views
from . import vendor_inventory_views
from . import order_processing_views
from . import api_views
from .stock_monitoring_api import stock_monitoring_api

app_name = 'business_partners'

urlpatterns = [
    # Vendor Authentication
    path('vendor/login/', 
         auth_views.VendorLoginView.as_view(), 
         name='vendor_login'),
    
    path('vendor/logout/', 
         auth_views.vendor_logout_view, 
         name='vendor_logout'),
    
    path('vendor/2fa/verify/', 
         auth_views.Vendor2FAVerifyView.as_view(), 
         name='vendor_2fa_verify'),
    
    path('vendor/2fa/setup/', 
         auth_views.Vendor2FASetupView.as_view(), 
         name='vendor_2fa_setup'),
    
    path('vendor/password/reset/', 
         auth_views.VendorPasswordResetRequestView.as_view(), 
         name='vendor_password_reset_request'),
    
    path('vendor/password/reset/confirm/<str:uidb64>/<str:token>/', 
         auth_views.VendorPasswordResetConfirmView.as_view(), 
         name='vendor_password_reset_confirm'),
    
    path('vendor/profile/settings/', 
         auth_views.vendor_profile_settings_view, 
         name='vendor_profile_settings'),
    
    # Vendor Registration Workflow
    # Vendor Registration Workflow
    path('vendor/register/', 
         views.VendorRegistrationStartView.as_view(), 
         name='vendor_registration_start'),
    
    path('vendor/register/step1/', 
         views.VendorRegistrationStep1View.as_view(), 
         name='vendor_registration_step1'),
    
    path('vendor/register/step2/', 
         views.VendorRegistrationStep2View.as_view(), 
         name='vendor_registration_step2'),
    
    path('vendor/register/step3/', 
         views.VendorRegistrationStep3View.as_view(), 
         name='vendor_registration_step3'),
    
    path('vendor/register/step4/', 
         views.VendorRegistrationStep4View.as_view(), 
         name='vendor_registration_step4'),
    
    path('vendor/register/review/', 
         views.VendorRegistrationReviewView.as_view(), 
         name='vendor_registration_review'),
    
    path('vendor/register/submit/', 
         views.VendorRegistrationSubmitView.as_view(), 
         name='vendor_registration_submit'),
    
    path('vendor/register/status/', 
         views.VendorRegistrationStatusView.as_view(), 
         name='vendor_registration_status'),
    
    path('vendor/register/submitted/', 
         views.VendorRegistrationSubmittedView.as_view(), 
         name='vendor_registration_submitted'),
    
    # AJAX Endpoints
    path('ajax/validate-iban/', 
         views.validate_iban_ajax, 
         name='validate_iban_ajax'),
    
    path('ajax/application-progress/', 
         views.application_progress_ajax, 
         name='application_progress_ajax'),
    
    # Admin Views for Application Review
    path('admin/vendor-applications/', 
         views.admin_vendor_applications, 
         name='admin_vendor_applications'),
    
    path('admin/vendor-applications/<str:application_id>/review/', 
         views.admin_review_application, 
         name='admin_review_application'),
    
    # Vendor Part Management
    path('vendor/dashboard/', 
         vendor_views.vendor_dashboard, 
         name='vendor_dashboard'),
    
    # Vendor Store Front (Public)
    path('vendors/<slug:vendor_slug>/', 
         vendor_views.vendor_store_front, 
         name='vendor_store'),
    
    path('vendor/parts/', 
         vendor_views.vendor_parts_list, 
         name='vendor_parts_list'),
    
    path('vendor/parts/create/', 
         vendor_views.vendor_part_create, 
         name='vendor_part_create'),
    
    path('vendor/parts/<int:part_id>/', 
         vendor_views.vendor_part_detail, 
         name='vendor_part_detail'),
    
    path('vendor/parts/<int:part_id>/edit/', 
         vendor_views.vendor_part_edit, 
         name='vendor_part_edit'),
    
    path('vendor/parts/<int:part_id>/delete/', 
         vendor_views.vendor_part_delete, 
         name='vendor_part_delete'),
    
    path('vendor/parts/bulk-update/', 
         vendor_views.vendor_parts_bulk_update, 
         name='vendor_parts_bulk_update'),
    
    path('vendor/parts/bulk-action/', 
         vendor_views.vendor_parts_bulk_action, 
         name='vendor_parts_bulk_action'),
    
    path('vendor/parts/import/', 
         vendor_views.vendor_parts_import, 
         name='vendor_parts_import'),
    
    path('vendor/parts/import/results/', 
         vendor_views.vendor_parts_import_results, 
         name='vendor_parts_import_results'),
    
    path('vendor/parts/export/', 
         vendor_views.vendor_parts_export, 
         name='vendor_parts_export'),
    
    path('vendor/parts/export-csv/', 
         vendor_views.vendor_parts_export_csv, 
         name='vendor_parts_export_csv'),
    
    path('vendor/inventory/alerts/', 
         vendor_views.vendor_inventory_alerts, 
         name='vendor_inventory_alerts'),
    
    # Vendor Inventory Management URLs
    path('vendor/inventory/', 
         vendor_inventory_views.vendor_inventory_list, 
         name='vendor_inventory_list'),
    
    path('vendor/inventory/<int:part_id>/', 
         vendor_inventory_views.vendor_inventory_detail, 
         name='vendor_inventory_detail'),
    
    path('vendor/inventory/<int:part_id>/update/', 
         vendor_inventory_views.vendor_inventory_update, 
         name='vendor_inventory_update'),
    
    path('vendor/inventory/bulk-update/', 
         vendor_inventory_views.vendor_inventory_bulk_update, 
         name='vendor_inventory_bulk_update'),
    
    path('vendor/inventory/<int:part_id>/adjust/', 
         vendor_inventory_views.vendor_inventory_adjustment, 
         name='vendor_inventory_adjustment'),
    
    path('vendor/inventory/export/', 
         vendor_inventory_views.vendor_inventory_export, 
         name='vendor_inventory_export'),
    
    path('vendor/inventory/api/<int:part_id>/', 
         vendor_inventory_views.vendor_inventory_api, 
         name='vendor_inventory_api'),
    
    path('vendor/inventory/alerts/json/', 
         vendor_inventory_views.vendor_inventory_alerts_json, 
         name='vendor_inventory_alerts_json'),
    
    # Reorder Notification URLs
    path('vendor/reorder-notifications/', 
         vendor_views.vendor_reorder_notifications, 
         name='vendor_reorder_notifications'),
    
    path('vendor/reorder-notifications/<int:notification_id>/', 
         vendor_views.vendor_reorder_notification_detail, 
         name='vendor_reorder_notification_detail'),
    
    path('vendor/reorder-notifications/<int:notification_id>/action/', 
         vendor_views.vendor_reorder_notification_action, 
         name='vendor_reorder_notification_action'),
    
    path('vendor/reorder-notifications/bulk-action/', 
         vendor_views.vendor_bulk_reorder_action, 
         name='vendor_bulk_reorder_action'),
    
    # Stock Monitoring API Endpoints
    path('api/vendor/stock-monitoring/summary/', 
         stock_monitoring_api, 
         {'endpoint': 'summary'}, 
         name='api_stock_monitoring_summary'),
    
    path('api/vendor/stock-monitoring/alerts/', 
         stock_monitoring_api, 
         {'endpoint': 'alerts'}, 
         name='api_stock_monitoring_alerts'),
    
    path('api/vendor/stock-monitoring/notifications/', 
         stock_monitoring_api, 
         {'endpoint': 'notifications'}, 
         name='api_stock_monitoring_notifications'),
    
    path('api/vendor/stock-monitoring/health/', 
         stock_monitoring_api, 
         {'endpoint': 'health'}, 
         name='api_stock_monitoring_health'),
    
    path('api/vendor/stock-monitoring/acknowledge-alert/', 
         stock_monitoring_api, 
         {'endpoint': 'acknowledge-alert'}, 
         name='api_stock_monitoring_acknowledge'),
    
    path('api/vendor/stock-monitoring/mark-ordered/', 
         stock_monitoring_api, 
         {'endpoint': 'mark-ordered'}, 
         name='api_stock_monitoring_mark_ordered'),
    
    # Dashboard API Endpoints
    path('api/vendor/dashboard/stats/', 
         api_views.get_vendor_dashboard_stats, 
         name='api_vendor_dashboard_stats'),
    
    path('api/vendor/dashboard/recent-orders/', 
         api_views.get_recent_orders, 
         name='api_vendor_recent_orders'),
    
    path('api/vendor/dashboard/top-products/', 
         api_views.get_top_products, 
         name='api_vendor_top_products'),
    
    path('api/vendor/dashboard/sales-performance/', 
         api_views.get_sales_performance, 
         name='api_vendor_sales_performance'),
    
    path('api/vendor/dashboard/notifications/', 
         api_views.get_notifications, 
         name='api_vendor_notifications'),
    
    path('api/vendor/dashboard/recent-customers/', 
         api_views.get_recent_customers, 
         name='api_vendor_recent_customers'),
    
    path('api/vendor/dashboard/low-stock/', 
         api_views.get_low_stock_items, 
         name='api_vendor_low_stock'),
    
    # Vendor Order Management
    path('vendor/orders/', 
         vendor_order_views.VendorOrderListView.as_view(), 
         name='vendor_orders_list'),
    
    path('vendor/orders/<int:pk>/', 
         vendor_order_views.VendorOrderDetailView.as_view(), 
         name='vendor_order_detail'),
    
    path('vendor/orders/<int:order_id>/update-status/', 
         vendor_order_views.vendor_update_order_status, 
         name='vendor_update_order_status'),
    
    path('vendor/orders/analytics/', 
         vendor_order_views.vendor_order_analytics, 
         name='vendor_order_analytics'),
    
    path('vendor/orders/reports/', 
         vendor_order_views.vendor_order_reports, 
         name='vendor_order_reports'),
    
    # Order processing workflow
    path('order-processing/', order_processing_views.OrderProcessingDashboardView.as_view(), name='order_processing_dashboard'),
    path('order-processing/<int:pk>/', order_processing_views.OrderProcessingDetailView.as_view(), name='order_processing_detail'),
    path('order-processing/<int:order_id>/action/', order_processing_views.process_order_action, name='process_order_action'),
    path('order-processing/bulk-action/', order_processing_views.bulk_order_processing, name='bulk_order_processing'),
    path('order-processing/api/<int:order_id>/', order_processing_views.order_processing_api, name='order_processing_api'),
    
    # CRUD System Test
    path('vendor/crud-test/', 
         vendor_views.vendor_crud_test, 
         name='vendor_crud_test'),
    
    # Responsive Design Test
    path('vendor/responsive-test/', 
         vendor_views.vendor_responsive_test, 
         name='vendor_responsive_test'),
]