from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class SubscriptionPlanType(models.TextChoices):
    FREE = 'free', 'Free'
    BASIC = 'basic', 'Basic'
    PREMIUM = 'premium', 'Premium'
    DEALER = 'dealer', 'Dealer'
    ENTERPRISE = 'enterprise', 'Enterprise'


class BillingCycle(models.TextChoices):
    MONTHLY = 'monthly', 'Monthly'
    QUARTERLY = 'quarterly', 'Quarterly'
    SEMI_ANNUAL = 'semi_annual', 'Semi-Annual'
    ANNUAL = 'annual', 'Annual'


class SubscriptionPlan(models.Model):
    """Model for subscription plans available to users."""
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=SubscriptionPlanType.choices)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    billing_cycle = models.CharField(max_length=20, choices=BillingCycle.choices, default=BillingCycle.MONTHLY)
    features = models.JSONField(default=dict, help_text='JSON field to store plan features and limits')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Plan limits
    max_listings = models.PositiveIntegerField(default=1)
    max_images_per_listing = models.PositiveIntegerField(default=5)
    featured_listings_count = models.PositiveIntegerField(default=0)
    premium_listings_count = models.PositiveIntegerField(default=0)
    listing_duration_days = models.PositiveIntegerField(default=30)
    
    class Meta:
        ordering = ['price']
    
    def __str__(self):
        return f"{self.name} ({self.get_billing_cycle_display()})"


class SubscriptionStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    PENDING = 'pending', 'Pending'
    CANCELLED = 'cancelled', 'Cancelled'
    EXPIRED = 'expired', 'Expired'
    TRIAL = 'trial', 'Trial'


class UserSubscription(models.Model):
    """Model for user subscriptions to plans."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='user_subscriptions')
    subscription_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    status = models.CharField(max_length=20, choices=SubscriptionStatus.choices, default=SubscriptionStatus.PENDING)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    auto_renew = models.BooleanField(default=True)
    is_trial = models.BooleanField(default=False)
    trial_end_date = models.DateTimeField(null=True, blank=True)
    
    # Payment tracking
    last_payment_date = models.DateTimeField(null=True, blank=True)
    next_payment_date = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(max_length=100, blank=True, null=True)
    
    # Usage tracking
    listings_used = models.PositiveIntegerField(default=0)
    featured_listings_used = models.PositiveIntegerField(default=0)
    premium_listings_used = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['start_date']),
            models.Index(fields=['end_date']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.plan.name} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        # Set end date based on billing cycle if not provided
        if not self.end_date:
            if self.plan.billing_cycle == BillingCycle.MONTHLY:
                self.end_date = self.start_date + timezone.timedelta(days=30)
            elif self.plan.billing_cycle == BillingCycle.QUARTERLY:
                self.end_date = self.start_date + timezone.timedelta(days=90)
            elif self.plan.billing_cycle == BillingCycle.SEMI_ANNUAL:
                self.end_date = self.start_date + timezone.timedelta(days=180)
            elif self.plan.billing_cycle == BillingCycle.ANNUAL:
                self.end_date = self.start_date + timezone.timedelta(days=365)
        super().save(*args, **kwargs)
    
    @property
    def is_active(self):
        now = timezone.now()
        return self.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL] and self.start_date <= now <= self.end_date
    
    @property
    def days_remaining(self):
        if not self.is_active:
            return 0
        now = timezone.now()
        return (self.end_date - now).days


class SubscriptionPayment(models.Model):
    """Model for tracking subscription payments."""
    subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(default=timezone.now)
    payment_method = models.CharField(max_length=100)
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=50)
    is_successful = models.BooleanField(default=False)
    failure_reason = models.TextField(blank=True, null=True)
    receipt_url = models.URLField(blank=True, null=True)
    
    class Meta:
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"Payment of {self.amount} for {self.subscription} on {self.payment_date.date()}"


class SubscriptionFeatureUsage(models.Model):
    """Model for tracking usage of subscription features."""
    subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE, related_name='feature_usage')
    feature_name = models.CharField(max_length=100)
    allowed_usage = models.PositiveIntegerField()
    current_usage = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['subscription', 'feature_name']
    
    def __str__(self):
        return f"{self.feature_name} usage for {self.subscription}"
    
    @property
    def usage_percentage(self):
        if self.allowed_usage == 0:
            return 100  # Avoid division by zero
        return (self.current_usage / self.allowed_usage) * 100
    
    @property
    def is_limit_reached(self):
        return self.current_usage >= self.allowed_usage
