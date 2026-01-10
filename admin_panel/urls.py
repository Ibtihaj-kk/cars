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
    path('settings/', views.admin_settings_view, name='settings'),
    
    # User Management
    path('users/', views.users_management_view, name='users'),
    path('users/add/', views.add_user_view, name='add_user'),
    path('users/<int:user_id>/', views.user_detail_view, name='user_detail'),
    path('users/<int:user_id>/update/', views.update_user_view, name='update_user'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status_view, name='toggle_user_status'),
    
    # Roles & Permissions
    path('roles/', views.roles_permissions_view, name='roles'),
    path('roles/add/', views.add_role_view, name='add_role'),
    path('roles/<int:role_id>/update/', views.update_role_view, name='update_role'),
    path('roles/<int:role_id>/delete/', views.delete_role_view, name='delete_role'),
    path('roles/<int:role_id>/permissions/', views.get_role_permissions_view, name='get_role_permissions'),
    path('roles/update/', views.update_role_permissions_view, name='update_role_permissions'),
    
    # Parts Management
    path('parts/', views.parts_management_view, name='parts'),
    path('parts/<int:part_id>/', views.part_detail_view, name='part_detail'),
    path('parts/<int:part_id>/update/', views.update_part_view, name='update_part'),
    path('parts/<int:part_id>/delete/', views.delete_part_view, name='delete_part'),
    
    # Categories & Brands
    path('categories/', views.categories_view, name='categories'),
    path('categories/add/', views.add_category_view, name='add_category'),
    path('categories/<int:category_id>/update/', views.update_category_view, name='update_category'),
    path('categories/<int:category_id>/delete/', views.delete_category_view, name='delete_category'),
    path('brands/add/', views.add_brand_view, name='add_brand'),
    path('brands/<int:brand_id>/update/', views.update_brand_view, name='update_brand'),
    path('brands/<int:brand_id>/delete/', views.delete_brand_view, name='delete_brand'),
    
    # Orders Management
    path('orders/', views.orders_management_view, name='orders'),
    path('orders/<int:order_id>/', views.order_detail_view, name='order_detail'),
    path('orders/<int:order_id>/update-status/', views.update_order_status_view, name='update_order_status'),

    # Catalog
    path('catalog/', views.catalog_management_view, name='catalog_management'),
    path('catalog/list/', views.catalog_list_view, name='catalog_list'),
    path('catalog/categories/', views.catalog_categories_view, name='catalog_categories'),
    path('catalog/makes/', views.catalog_makes_view, name='catalog_makes'),
    path('catalog/makes/add/', views.catalog_make_add_view, name='catalog_make_add'),
    path('catalog/makes/<int:pk>/edit/', views.catalog_make_edit_view, name='catalog_make_edit'),
    path('catalog/makes/<int:pk>/delete/', views.catalog_make_delete_view, name='catalog_make_delete'),
    path('catalog/add/', views.catalog_add_view, name='catalog_add'),
    path('catalog/inventory/', views.catalog_inventory_view, name='catalog_inventory'),
    path('catalog/<int:pk>/', views.catalog_detail_view, name='catalog_detail'),
    path('catalog/<int:pk>/edit/', views.catalog_edit_view, name='catalog_edit'),
    path('catalog/<int:pk>/delete/', views.catalog_delete_view, name='catalog_delete'),
    
    # Reviews Management
    path('reviews/', views.reviews_management_view, name='reviews'),
    path('reviews/<int:review_id>/approve/', views.approve_review_view, name='approve_review'),
    path('reviews/<int:review_id>/reject/', views.reject_review_view, name='reject_review'),
    
    # Bulk Upload
    path('bulk-upload/', views.bulk_upload_view, name='bulk_upload'),
    path('bulk-upload/template/', views.bulk_upload_template_view, name='bulk_upload_template'),
    path('bulk-upload/process/', views.process_bulk_upload_view, name='process_bulk_upload'),
    
    # Invoices & Finance
    path('invoices/', views.invoices_view, name='invoices'),
    path('invoices/<int:order_id>/', views.invoice_detail_view, name='invoice_detail'),
    
    # Centralized Finance (New)
    path('finance/ledger/', views.finance_ledger_view, name='finance_ledger'),
    path('finance/wallets/', views.wallets_management_view, name='finance_wallets'),
    path('finance/escrow/', views.escrow_management_view, name='finance_escrow'),
    path('finance/commission/', views.commission_management_view, name='commission_management'),
    path('finance/commission/add/', views.create_commission_rule, name='create_commission_rule'),
    path('finance/commission/<int:rule_id>/toggle/', views.toggle_commission_rule, name='toggle_commission_rule'),
    path('finance/commission/<int:rule_id>/delete/', views.delete_commission_rule, name='delete_commission_rule'),
    path('finance/cod-settlements/', views.admin_cod_settlements_view, name='finance_cod_settlements'),
    path('finance/audit-logs/', views.financial_audit_logs_view, name='finance_audit_logs'),
    
    # Tax Rules
    path('taxes/', views.taxes_view, name='taxes'),
    path('taxes/add/', views.add_tax_rule_view, name='add_tax_rule'),
    path('taxes/<int:tax_id>/update/', views.update_tax_rule_view, name='update_tax_rule'),
    
    # Business Partners
    path('partners/', views.partners_view, name='partners'),
    path('partners/<int:partner_id>/', views.partner_detail_view, name='partner_detail'),
    
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
    path('vendors/<int:vendor_id>/verify-bank/', views.verify_vendor_bank_view, name='verify_vendor_bank'),
    path('vendors/approval-queue/', views.vendor_approval_queue_view, name='vendor_approval_queue'),
    path('vendors/performance/<int:vendor_id>/', views.vendor_performance_view, name='vendor_performance'),
    path('vendors/applications/', views.vendor_management_view, name='vendor_applications'),
    path('vendors/applications/<int:application_id>/', views.vendor_application_detail_view, name='vendor_application_detail'),
    path('vendors/applications/<int:application_id>/approve/', views.approve_vendor_application_view, name='approve_vendor_application'),
    path('vendors/applications/<int:application_id>/reject/', views.reject_vendor_application_view, name='reject_vendor_application'),
    path('vendors/applications/<int:application_id>/request-changes/', views.request_changes_vendor_application_view, name='request_changes_vendor_application'),
    path('vendors/<int:vendor_id>/documents/', views.vendor_documents_view, name='vendor_documents'),
    path('vendors/documents/<uuid:document_id>/verify/', views.verify_vendor_document_view, name='verify_vendor_document'),
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
    path('payments/batch/<int:batch_id>/export/', views.export_payment_batch_csv, name='export_payment_batch_csv'),
    path('commissions/rules/create/', views.create_commission_rule, name='create_commission_rule'),
    path('commissions/rules/<int:rule_id>/update/', views.update_commission_rule, name='update_commission_rule'),
    path('commissions/rules/<int:rule_id>/toggle/', views.toggle_commission_rule, name='toggle_commission_rule'),
    path('commissions/rules/<int:rule_id>/delete/', views.delete_commission_rule, name='delete_commission_rule'),
    path('payments/vendor/<int:vendor_id>/balance/adjust/', views.adjust_vendor_balance_view, name='adjust_vendor_balance'),
    
    # API endpoints for dashboard widgets
    path('api/stats/', views.api_dashboard_stats, name='api_dashboard_stats'),
    path('api/recent-activity/', views.api_recent_activity, name='api_recent_activity'),
    
    # Email Console
    path('email-console/', views.email_console, name='admin_email_console'),
    path('email-queue/', views.email_queue, name='admin_email_queue'),
    path('email-analytics/', views.email_analytics, name='admin_email_analytics'),
    path('send-manual-email/', views.send_manual_email, name='send_manual_email'),
    path('send-bulk-email/', views.send_bulk_email, name='send_bulk_email'),
    path('retry-email/<uuid:email_id>/', views.retry_failed_email, name='retry_email'),
    path('cancel-email/<uuid:email_id>/', views.cancel_email, name='cancel_email'),
    path('clear-email-queue/', views.clear_email_queue, name='clear_email_queue'),
    
]
