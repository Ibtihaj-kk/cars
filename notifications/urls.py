from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'notifications'

router = DefaultRouter()
router.register(r'notifications', views.NotificationViewSet, basename='notification')
router.register(r'preferences', views.NotificationPreferenceViewSet, basename='preference')
router.register(r'device-tokens', views.DeviceTokenViewSet, basename='device-token')

urlpatterns = [
    path('', include(router.urls)),
]