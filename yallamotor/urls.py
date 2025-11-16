"""
YallaMotor URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),
    path('api/analytics/', include('analytics.urls')),
    path('api/compliance/', include('core.compliance_urls')),
    path('api/performance/', include('admin_panel.performance_urls')),
    path('api/vendors/', include('business_partners.api_urls')),
    path('', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)