from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('wallet/', views.user_wallet_view, name='user_wallet'),
    path('transaction/<int:transaction_id>/', views.transaction_detail_view, name='transaction_detail'),
    
    # Vendor specific finance URLs
    path('vendor/wallet/', views.vendor_wallet_view, name='vendor_wallet'),
    path('vendor/transaction/<int:transaction_id>/', views.vendor_transaction_detail_view, name='vendor_transaction_detail'),
    path('vendor/cod-settlement/submit/', views.submit_cod_settlement, name='submit_cod_settlement'),
    path('vendor/payout/request/', views.request_payout, name='request_payout'),
    
    # Admin specific finance URLs
    path('admin/cod-settlements/', views.admin_cod_settlements, name='admin_cod_settlements'),
]
