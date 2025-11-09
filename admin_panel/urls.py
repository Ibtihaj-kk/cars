from django.urls import path
from . import views, auth_views

app_name = 'admin_panel'

urlpatterns = [
    # Authentication
    path('login/', auth_views.admin_login_view, name='login'),
    path('logout/', auth_views.admin_logout_view, name='logout'),
    path('setup-2fa/', auth_views.setup_2fa_view, name='setup_2fa'),
    path('disable-2fa/', auth_views.disable_2fa_view, name='disable_2fa'),
    
    # Main dashboard
    path('', views.dashboard_view, name='dashboard'),
    path('dashboard/', views.dashboard_view, name='dashboard_alt'),
    path('demo/', views.dashboard_demo_view, name='dashboard_demo'),
    
    # Listings management
    path('listings/', views.listings_management_view, name='listings_management'),
    path('listings/<int:listing_id>/', views.listing_detail_view, name='listing_detail'),
    path('listings/<int:listing_id>/update-status/', views.update_listing_status, name='update_listing_status'),
    path('listings/bulk-update/', views.bulk_update_listings, name='bulk_update_listings'),
    
    # Analytics
    path('analytics/', views.analytics_view, name='analytics'),
    
    # Activity logs
    path('activity-logs/', views.activity_logs_view, name='activity_logs'),
    
    # Vendor management
    path('vendors/', views.vendor_management_view, name='vendor_management'),
    path('vendors/<int:vendor_id>/', views.vendor_detail_view, name='vendor_detail'),
    path('vendors/<int:vendor_id>/update-status/', views.update_vendor_status, name='update_vendor_status'),
    path('vendors/approval-queue/', views.vendor_approval_queue_view, name='vendor_approval_queue'),
    path('vendors/performance/<int:vendor_id>/', views.vendor_performance_view, name='vendor_performance'),
    path('vendors/applications/', views.vendor_management_view, name='vendor_applications'),
    path('vendors/applications/<int:application_id>/', views.vendor_application_detail_view, name='vendor_application_detail'),
    path('vendors/applications/<int:application_id>/approve/', views.approve_vendor_application_view, name='approve_vendor_application'),
    path('vendors/applications/<int:application_id>/reject/', views.reject_vendor_application_view, name='reject_vendor_application'),
    path('vendors/applications/<int:application_id>/request-changes/', views.request_changes_vendor_application_view, name='request_changes_vendor_application'),
    path('vendors/<int:vendor_id>/documents/', views.vendor_documents_view, name='vendor_documents'),
    path('vendors/documents/<int:document_id>/verify/', views.verify_vendor_document_view, name='verify_vendor_document'),
    path('vendors/<int:vendor_id>/communication/', views.vendor_communication_view, name='vendor_communication'),
    
    # Messaging URLs
    path('messages/', views.vendor_messages_view, name='vendor_messages'),
    path('messages/send/', views.send_vendor_message, name='send_vendor_message'),
    path('messages/send/<int:vendor_id>/', views.send_vendor_message, name='send_vendor_message_to'),
    path('messages/<int:message_id>/', views.message_detail_view, name='message_detail'),
    path('messages/templates/', views.message_templates_view, name='message_templates'),
    path('messages/<int:message_id>/mark-read/', views.mark_message_read, name='mark_message_read'),
    path('messages/<int:message_id>/delete/', views.delete_message, name='delete_message'),
    path('messages/templates/<int:template_id>/', views.get_message_template, name='get_message_template'),
    path('messages/templates/<int:template_id>/delete/', views.delete_message_template, name='delete_message_template'),
    
    # Payment and commission management
    path('payments/', views.payment_management_view, name='payment_management'),
    path('payments/commissions/', views.commission_management_view, name='commission_management'),
    path('payments/vendor/<int:vendor_id>/balance/', views.vendor_balance_view, name='vendor_balance'),
    path('payments/<int:payment_id>/process/', views.process_payment_view, name='process_payment'),
    path('payments/batch-process/', views.batch_process_payments_view, name='batch_process_payments'),
    path('commissions/rules/create/', views.create_commission_rule_view, name='create_commission_rule'),
    path('commissions/rules/<int:rule_id>/toggle/', views.toggle_commission_rule_view, name='toggle_commission_rule'),
    path('commissions/rules/<int:rule_id>/delete/', views.delete_commission_rule_view, name='delete_commission_rule'),
    path('payments/vendor/<int:vendor_id>/balance/adjust/', views.adjust_vendor_balance_view, name='adjust_vendor_balance'),
    
    # API endpoints for dashboard widgets
    path('api/stats/', views.api_dashboard_stats, name='api_dashboard_stats'),
    path('api/recent-activity/', views.api_recent_activity, name='api_recent_activity'),
]