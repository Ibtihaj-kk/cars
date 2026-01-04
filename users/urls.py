from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    UserRegistrationView,
    CustomTokenObtainPairView,
    VerifyOTPView,
    EmailVerificationView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    UserViewSet,
    AdminUserViewSet,
    UserAuditLogViewSet,
    ProfileUpdateView,
    DashboardView,
    register_page,
    user_dashboard,
    user_profile,
    user_orders,
    logout_view,
    check_email_availability
)

app_name = 'users'

# Main router for user endpoints
router = DefaultRouter()
router.register(r'', UserViewSet, basename='users')

# Admin router for admin-specific endpoints
admin_router = DefaultRouter()
admin_router.register(r'users', AdminUserViewSet, basename='admin-users')

# Audit router for audit log endpoints
audit_router = DefaultRouter()
audit_router.register(r'', UserAuditLogViewSet, basename='audit-logs')

urlpatterns = [
    # Authentication endpoints
    path('signup/', register_page, name='register_page'),
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Verification endpoints
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('verify-email/<str:token>/', EmailVerificationView.as_view(), name='verify-email'),
    path('check-email/', check_email_availability, name='check-email-availability'),
    
    # Password reset endpoints
    path('password/reset/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password/reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    
    # Template Views
    path('dashboard/', user_dashboard, name='user-dashboard'),
    path('profile/', user_profile, name='user-profile'),
    path('orders/', user_orders, name='user-orders'),
    path('logout/', logout_view, name='logout'),
    
    # API Endpoints
    path('api/profile/update/', ProfileUpdateView.as_view(), name='api-profile-update'),
    path('api/dashboard/', DashboardView.as_view(), name='api-dashboard'),
    
    # Admin endpoints
    path('admin/', include(admin_router.urls)),
    
    # Audit log endpoints
    path('audit-logs/', include(audit_router.urls)),
    
    # User endpoints
    path('', include(router.urls)),
]
