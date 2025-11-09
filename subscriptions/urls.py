from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'subscriptions'

router = DefaultRouter()
router.register(r'plans', views.SubscriptionPlanViewSet, basename='plan')
router.register(r'user-subscriptions', views.UserSubscriptionViewSet, basename='user-subscription')
router.register(r'payments', views.SubscriptionPaymentViewSet, basename='payment')
router.register(r'feature-usage', views.SubscriptionFeatureUsageViewSet, basename='feature-usage')

urlpatterns = [
    path('', include(router.urls)),
]