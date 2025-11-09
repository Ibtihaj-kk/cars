from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, permissions, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from django_filters.rest_framework import DjangoFilterBackend

from .models import Brand, VehicleModel, VehicleCategory, VehicleSpecification, VehicleFeature, FuelType, TransmissionType
from .serializers import (
    BrandSerializer,
    VehicleCategorySerializer,
    VehicleModelListSerializer,
    VehicleModelDetailSerializer,
    VehicleModelCreateUpdateSerializer,
    VehicleFeatureSerializer,
    VehicleSpecificationListSerializer,
    VehicleSpecificationDetailSerializer,
    VehicleSpecificationCreateUpdateSerializer,
    FuelTypeSerializer,
    TransmissionTypeSerializer
)


class BrandViewSet(viewsets.ModelViewSet):
    """ViewSet for vehicle brands."""
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['name', 'country_of_origin']
    filterset_fields = ['country_of_origin']
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [AllowAny()]
        
    @action(detail=True, methods=['get'])
    def models(self, request, pk=None):
        """Get all models for a specific brand."""
        brand = self.get_object()
        models = VehicleModel.objects.filter(brand=brand)
        serializer = VehicleModelListSerializer(models, many=True)
        return Response(serializer.data)


class VehicleCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for vehicle categories."""
    queryset = VehicleCategory.objects.all()
    serializer_class = VehicleCategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [AllowAny()]


class VehicleModelViewSet(viewsets.ModelViewSet):
    """ViewSet for vehicle models."""
    queryset = VehicleModel.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['name', 'brand__name']
    filterset_fields = ['brand', 'category', 'launch_year', 'is_active']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return VehicleModelDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return VehicleModelCreateUpdateSerializer
        return VehicleModelListSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [AllowAny()]
    
    @action(detail=True, methods=['get'])
    def specifications(self, request, pk=None):
        """Get all specifications for a vehicle model."""
        model = self.get_object()
        specs = VehicleSpecification.objects.filter(vehicle_model=model)
        serializer = VehicleSpecificationListSerializer(specs, many=True)
        return Response(serializer.data)


class FuelTypeViewSet(viewsets.ModelViewSet):
    """ViewSet for fuel types."""
    queryset = FuelType.objects.all()
    serializer_class = FuelTypeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['name', 'description']
    filterset_fields = ['is_active']
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [AllowAny()]


class TransmissionTypeViewSet(viewsets.ModelViewSet):
    """ViewSet for transmission types."""
    queryset = TransmissionType.objects.all()
    serializer_class = TransmissionTypeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['name', 'description']
    filterset_fields = ['is_active']
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [AllowAny()]


class VehicleFeatureViewSet(viewsets.ModelViewSet):
    """ViewSet for vehicle features."""
    queryset = VehicleFeature.objects.all()
    serializer_class = VehicleFeatureSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['name', 'category']
    filterset_fields = ['category']
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [AllowAny()]


class VehicleSpecificationViewSet(viewsets.ModelViewSet):
    """ViewSet for vehicle specifications."""
    queryset = VehicleSpecification.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['model__name', 'model__brand__name']
    filterset_fields = ['model', 'year', 'fuel_type', 'transmission', 'category']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return VehicleSpecificationDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return VehicleSpecificationCreateUpdateSerializer
        return VehicleSpecificationListSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [AllowAny()]
