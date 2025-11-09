from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.db.models import Q
from rest_framework import viewsets, permissions, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    SubscriptionPlan, 
    UserSubscription, 
    SubscriptionPayment, 
    SubscriptionFeatureUsage,
    SubscriptionStatus
)
from .serializers import (
    SubscriptionPlanSerializer,
    UserSubscriptionListSerializer,
    UserSubscriptionDetailSerializer,
    UserSubscriptionCreateSerializer,
    UserSubscriptionUpdateSerializer,
    SubscriptionCancelSerializer,
    SubscriptionPaymentSerializer,
    SubscriptionFeatureUsageSerializer
)


class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    """ViewSet for subscription plans."""
    queryset = SubscriptionPlan.objects.filter(is_active=True)
    serializer_class = SubscriptionPlanSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['name', 'description']
    filterset_fields = ['plan_type', 'billing_cycle']
    ordering_fields = ['price', 'created_at']
    ordering = ['price']
    
    def get_permissions(self):
        """Only admin users can create, update or delete plans."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]


class UserSubscriptionViewSet(viewsets.ModelViewSet):
    """ViewSet for user subscriptions."""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'plan__plan_type']
    ordering_fields = ['created_at', 'start_date', 'end_date']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        # Admin users can see all subscriptions
        if user.is_staff or user.is_superuser:
            return UserSubscription.objects.all()
        # Regular users can only see their own subscriptions
        return UserSubscription.objects.filter(user=user)
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return UserSubscriptionDetailSerializer
        elif self.action == 'create':
            return UserSubscriptionCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserSubscriptionUpdateSerializer
        elif self.action == 'cancel':
            return SubscriptionCancelSerializer
        return UserSubscriptionListSerializer
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a subscription."""
        subscription = self.get_object()
        serializer = self.get_serializer(subscription, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'status': 'subscription cancelled'}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get user's active subscription."""
        user = request.user
        now = timezone.now()
        
        # Find active subscription
        subscription = UserSubscription.objects.filter(
            user=user,
            status__in=[SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL],
            start_date__lte=now,
            end_date__gte=now
        ).first()
        
        if not subscription:
            return Response({'detail': 'No active subscription found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = UserSubscriptionDetailSerializer(subscription)
        return Response(serializer.data)


class SubscriptionPaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for subscription payments."""
    serializer_class = SubscriptionPaymentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['is_successful', 'status']
    ordering_fields = ['payment_date']
    ordering = ['-payment_date']
    
    def get_queryset(self):
        user = self.request.user
        # Admin users can see all payments
        if user.is_staff or user.is_superuser:
            return SubscriptionPayment.objects.all()
        # Regular users can only see their own payments
        return SubscriptionPayment.objects.filter(subscription__user=user)


class SubscriptionFeatureUsageViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for subscription feature usage (read-only)."""
    serializer_class = SubscriptionFeatureUsageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # Admin users can see all feature usage
        if user.is_staff or user.is_superuser:
            return SubscriptionFeatureUsage.objects.all()
        # Regular users can only see their own feature usage
        return SubscriptionFeatureUsage.objects.filter(subscription__user=user)
