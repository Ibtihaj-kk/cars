"""
URL configuration for CarSyncro project.

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
from users.views import LoginView
from django.views.generic import TemplateView

# Simple home view since core app is disabled
def home(request):
    from django.shortcuts import render
    return render(request, 'home/index.html', {})

# Custom 404 handler
def custom_404_view(request, exception):
    from django.shortcuts import render
    response = render(request, 'home/coming_soon.html', {'status_code': 404})
    response.status_code = 404
    return response

# Custom 500 handler
def custom_500_view(request):
    from django.shortcuts import render
    response = render(request, 'home/coming_soon.html', {'status_code': 500})
    response.status_code = 500
    return response

# API Documentation imports
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# API Documentation Schema
schema_view = get_schema_view(
    openapi.Info(
        title="CarSyncro API",
        default_version='v1',
        description="API documentation for CarSyncro backend",
        contact=openapi.Contact(email="contact@carsyncro.com"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('accounts/login/', LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    # Enabled apps only
    path('api/users/', include('users.urls')),
    path('business-partners/', include('business_partners.urls')),  # Vendor registration system
    path('business-partners/htmx/', include('business_partners.urls_htmx')),  # HTMX endpoints for vendors
    path('parts/', include('parts.urls')),
    path('finance/', include('finance.urls')),
    path('admin_panel/', include('admin_panel.urls')),  # Custom admin panel
    
    # API Documentation
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='swagger-docs'),
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom error handlers
handler404 = 'yallamotor_project.urls.custom_404_view'
handler500 = 'yallamotor_project.urls.custom_500_view'
