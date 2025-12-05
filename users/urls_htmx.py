"""
HTMX URL Patterns for Users Module
"""
from django.urls import path
from . import htmx_views

app_name = 'users_htmx'

urlpatterns = [
    # Authentication
    path('login/', htmx_views.login_form_htmx, name='login_form'),
    path('login/submit/', htmx_views.login_submit_htmx, name='login_submit'),
    path('logout/', htmx_views.logout_htmx, name='logout'),

    # Registration
    path('register/', htmx_views.register_form_htmx, name='register_form'),
    path('register/submit/', htmx_views.register_submit_htmx, name='register_submit'),

    # User Profile
    path('profile/', htmx_views.user_profile_htmx, name='profile'),
    path('profile/edit/', htmx_views.user_profile_edit_htmx, name='profile_edit'),
    path('profile/update/', htmx_views.user_profile_update_htmx, name='profile_update'),

    # User Dashboard
    path('dashboard/', htmx_views.user_dashboard_htmx, name='dashboard'),

    # Orders
    path('orders/', htmx_views.user_orders_htmx, name='orders'),
    path('orders/<int:order_id>/', htmx_views.user_order_detail_htmx, name='order_detail'),

    # Password Management
    path('password/change/', htmx_views.change_password_form_htmx, name='change_password_form'),
    path('password/change/submit/', htmx_views.change_password_submit_htmx, name='change_password_submit'),

    # Account Settings
    path('settings/', htmx_views.account_settings_htmx, name='settings'),
    path('settings/email-preferences/', htmx_views.update_email_preferences_htmx, name='update_email_preferences'),
    path('settings/deactivate/', htmx_views.deactivate_account_htmx, name='deactivate_account'),
]
