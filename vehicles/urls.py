from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import (
    BrandViewSet,
    VehicleCategoryViewSet,
    VehicleModelViewSet,
    VehicleFeatureViewSet,
    VehicleSpecificationViewSet,
    FuelTypeViewSet,
    TransmissionTypeViewSet
)

app_name = 'vehicles'

router = DefaultRouter()
router.register(r'brands', BrandViewSet)
router.register(r'categories', VehicleCategoryViewSet)
router.register(r'models', VehicleModelViewSet)
router.register(r'features', VehicleFeatureViewSet)
router.register(r'specifications', VehicleSpecificationViewSet)
router.register(r'fuel-types', FuelTypeViewSet)
router.register(r'transmission-types', TransmissionTypeViewSet)

urlpatterns = [
    path('', include(router.urls)),
]