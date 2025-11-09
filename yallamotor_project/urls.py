"""
URL configuration for carsportal_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from listings.views import dashboard_summary_view
from frontend_views import homepage_view, filter_listings_api, search_listings_view, car_detail_view, schedule_test_drive_view

# API Documentation imports
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# API Documentation Schema
schema_view = get_schema_view(
    openapi.Info(
        title="Cars Portal API",
        default_version='v1',
        description="API documentation for Cars Portal backend",
        contact=openapi.Contact(email="contact@carsportal.com"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='admin_panel/auth/login.html'), name='login'),
    path('admin-panel/', include('admin_panel.urls')),  # Admin panel at root level
    path('api/users/', include('users.urls')),
    path('api/vehicles/', include('vehicles.urls')),
    path('api/listings/', include('listings.urls')),
    path('api/inquiries/', include('inquiries.urls')),
    path('api/reviews/', include('reviews.urls')),
    path('api/subscriptions/', include('subscriptions.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/content/', include('content.urls')),
    path('business-partners/', include('business_partners.urls')),  # Vendor registration system
    path('parts/', include('parts.urls')),
    path('shop/', include('parts.urls')),  # Shop alias for parts
    path('api/parts/', include('parts.urls')),  # API endpoint for parts
    path('', homepage_view, name='home'),
    path('api/filter-listings/', filter_listings_api, name='filter-listings'),
    path('search/', search_listings_view, name='search-listings'),
    path('car/<slug:slug>/', car_detail_view, name='car-detail'),
    path('schedule-test-drive/', schedule_test_drive_view, name='schedule_test_drive'),
    # Dashboard endpoints
    path('api/dashboard/summary/', dashboard_summary_view, name='dashboard-summary'),
    
    # API Documentation
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='swagger-docs'),
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
