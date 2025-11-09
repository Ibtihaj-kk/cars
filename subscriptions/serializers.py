from rest_framework import serializers
from django.utils import timezone
from .models import (
    SubscriptionPlan, 
    UserSubscription, 
    SubscriptionPayment, 
    SubscriptionFeatureUsage,
    SubscriptionStatus,
    BillingCycle
)


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer for subscription plans."""
    billing_cycle_display = serializers.CharField(source='get_billing_cycle_display', read_only=True)
    plan_type_display = serializers.CharField(source='get_plan_type_display', read_only=True)
    
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'plan_type', 'plan_type_display', 'description', 'price',
            'billing_cycle', 'billing_cycle_display', 'features', 'is_active',
            'max_listings', 'max_images_per_listing', 'featured_listings_count',
            'premium_listings_count', 'listing_duration_days', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class SubscriptionFeatureUsageSerializer(serializers.ModelSerializer):
    """Serializer for subscription feature usage."""
    usage_percentage = serializers.FloatField(read_only=True)
    is_limit_reached = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = SubscriptionFeatureUsage
        fields = [
            'id', 'feature_name', 'allowed_usage', 'current_usage',
            'usage_percentage', 'is_limit_reached', 'last_updated'
        ]
        read_only_fields = ['last_updated']


class SubscriptionPaymentSerializer(serializers.ModelSerializer):
    """Serializer for subscription payments."""
    
    class Meta:
        model = SubscriptionPayment
        fields = [
            'id', 'subscription', 'amount', 'payment_date', 'payment_method',
            'transaction_id', 'status', 'is_successful', 'failure_reason', 'receipt_url'
        ]
        read_only_fields = ['payment_date']


class UserSubscriptionListSerializer(serializers.ModelSerializer):
    """Serializer for listing user subscriptions."""
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    plan_type = serializers.CharField(source='plan.plan_type', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = UserSubscription
        fields = [
            'id', 'subscription_id', 'user', 'plan', 'plan_name', 'plan_type',
            'status', 'status_display', 'start_date', 'end_date', 'is_active',
            'days_remaining', 'auto_renew', 'is_trial', 'trial_end_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['subscription_id', 'created_at', 'updated_at']


class UserSubscriptionDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed user subscription information."""
    plan = SubscriptionPlanSerializer(read_only=True)
    feature_usage = SubscriptionFeatureUsageSerializer(many=True, read_only=True)
    payments = SubscriptionPaymentSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = UserSubscription
        fields = [
            'id', 'subscription_id', 'user', 'plan', 'status', 'status_display',
            'start_date', 'end_date', 'auto_renew', 'is_trial', 'trial_end_date',
            'last_payment_date', 'next_payment_date', 'payment_method',
            'listings_used', 'featured_listings_used', 'premium_listings_used',
            'is_active', 'days_remaining', 'feature_usage', 'payments',
            'created_at', 'updated_at', 'cancelled_at', 'cancellation_reason'
        ]
        read_only_fields = ['subscription_id', 'created_at', 'updated_at']


class UserSubscriptionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating user subscriptions."""
    
    class Meta:
        model = UserSubscription
        fields = [
            'plan', 'auto_renew', 'is_trial', 'trial_end_date',
            'payment_method'
        ]
    
    def create(self, validated_data):
        user = self.context['request'].user
        plan = validated_data.get('plan')
        
        # Set start date to now
        start_date = timezone.now()
        
        # Calculate end date based on billing cycle
        if plan.billing_cycle == BillingCycle.MONTHLY:
            end_date = start_date + timezone.timedelta(days=30)
        elif plan.billing_cycle == BillingCycle.QUARTERLY:
            end_date = start_date + timezone.timedelta(days=90)
        elif plan.billing_cycle == BillingCycle.SEMI_ANNUAL:
            end_date = start_date + timezone.timedelta(days=180)
        elif plan.billing_cycle == BillingCycle.ANNUAL:
            end_date = start_date + timezone.timedelta(days=365)
        else:
            end_date = start_date + timezone.timedelta(days=30)  # Default to monthly
        
        # Create subscription
        subscription = UserSubscription.objects.create(
            user=user,
            plan=plan,
            start_date=start_date,
            end_date=end_date,
            status=SubscriptionStatus.ACTIVE if not validated_data.get('is_trial') else SubscriptionStatus.TRIAL,
            **validated_data
        )
        
        # Create feature usage records
        SubscriptionFeatureUsage.objects.create(
            subscription=subscription,
            feature_name='listings',
            allowed_usage=plan.max_listings,
            current_usage=0
        )
        
        SubscriptionFeatureUsage.objects.create(
            subscription=subscription,
            feature_name='featured_listings',
            allowed_usage=plan.featured_listings_count,
            current_usage=0
        )
        
        SubscriptionFeatureUsage.objects.create(
            subscription=subscription,
            feature_name='premium_listings',
            allowed_usage=plan.premium_listings_count,
            current_usage=0
        )
        
        return subscription


class UserSubscriptionUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user subscriptions."""
    
    class Meta:
        model = UserSubscription
        fields = ['auto_renew', 'payment_method']


class SubscriptionCancelSerializer(serializers.ModelSerializer):
    """Serializer for cancelling subscriptions."""
    cancellation_reason = serializers.CharField(required=True)
    
    class Meta:
        model = UserSubscription
        fields = ['cancellation_reason']
    
    def update(self, instance, validated_data):
        instance.status = SubscriptionStatus.CANCELLED
        instance.cancelled_at = timezone.now()
        instance.cancellation_reason = validated_data.get('cancellation_reason')
        instance.auto_renew = False
        instance.save()
        return instance