from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from vehicles.models import VehicleModel, Brand


class ReviewStatus(models.TextChoices):
    PENDING = 'pending', 'Pending Approval'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    FLAGGED = 'flagged', 'Flagged for Review'


class VehicleReview(models.Model):
    """Model for user reviews of specific vehicle models."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vehicle_reviews')
    vehicle_model = models.ForeignKey(VehicleModel, on_delete=models.CASCADE, related_name='reviews')
    year = models.PositiveIntegerField(help_text='Year of the vehicle being reviewed')
    title = models.CharField(max_length=255)
    content = models.TextField()
    pros = models.TextField(blank=True, null=True, help_text='Positive aspects of the vehicle')
    cons = models.TextField(blank=True, null=True, help_text='Negative aspects of the vehicle')
    
    # Rating categories (1-5 scale)
    overall_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comfort_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        blank=True, null=True
    )
    performance_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        blank=True, null=True
    )
    reliability_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        blank=True, null=True
    )
    value_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        blank=True, null=True
    )
    fuel_economy_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        blank=True, null=True
    )
    
    # Review metadata
    status = models.CharField(max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.PENDING)
    is_verified_purchase = models.BooleanField(default=False)
    is_verified_owner = models.BooleanField(default=False)
    helpful_votes = models.PositiveIntegerField(default=0)
    unhelpful_votes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Vehicle Review'
        verbose_name_plural = 'Vehicle Reviews'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['overall_rating']),
            models.Index(fields=['is_verified_owner']),
        ]
        unique_together = ['user', 'vehicle_model', 'year']
    
    def __str__(self):
        return f"{self.title} - {self.vehicle_model.brand.name} {self.vehicle_model.name} {self.year}"


class DealerReview(models.Model):
    """Model for user reviews of car dealers."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dealer_reviews')
    dealer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_reviews',
                              limit_choices_to={'role': 'seller'})
    title = models.CharField(max_length=255)
    content = models.TextField()
    
    # Rating categories (1-5 scale)
    overall_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    customer_service_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        blank=True, null=True
    )
    buying_process_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        blank=True, null=True
    )
    price_fairness_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        blank=True, null=True
    )
    
    # Review metadata
    status = models.CharField(max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.PENDING)
    is_verified_transaction = models.BooleanField(default=False)
    helpful_votes = models.PositiveIntegerField(default=0)
    unhelpful_votes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Dealer Review'
        verbose_name_plural = 'Dealer Reviews'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['overall_rating']),
            models.Index(fields=['is_verified_transaction']),
        ]
        unique_together = ['user', 'dealer']
    
    def __str__(self):
        return f"{self.title} - Review for {self.dealer.email}"


class SellerReview(models.Model):
    """Model for buyer reviews of sellers."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='seller_reviews_given')
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='seller_reviews_received')
    title = models.CharField(max_length=255)
    content = models.TextField()
    pros = models.TextField(blank=True, null=True, help_text='Positive aspects of dealing with this seller')
    cons = models.TextField(blank=True, null=True, help_text='Negative aspects of dealing with this seller')
    
    # Rating categories (1-5 scale)
    overall_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    communication_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        blank=True, null=True
    )
    reliability_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        blank=True, null=True
    )
    honesty_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        blank=True, null=True
    )
    responsiveness_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        blank=True, null=True
    )
    
    # Review metadata
    status = models.CharField(max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.PENDING)
    is_verified_transaction = models.BooleanField(default=False)
    helpful_votes = models.PositiveIntegerField(default=0)
    unhelpful_votes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Seller Review'
        verbose_name_plural = 'Seller Reviews'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['overall_rating']),
            models.Index(fields=['is_verified_transaction']),
        ]
        unique_together = ['user', 'seller']
    
    def __str__(self):
        return f"{self.title} - Review for {self.seller.email}"


class ListingReview(models.Model):
    """Model for buyer reviews of specific vehicle listings."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='listing_reviews_given')
    listing = models.ForeignKey('listings.VehicleListing', on_delete=models.CASCADE, related_name='reviews')
    title = models.CharField(max_length=255)
    content = models.TextField()
    pros = models.TextField(blank=True, null=True, help_text='Positive aspects of this listing/vehicle')
    cons = models.TextField(blank=True, null=True, help_text='Negative aspects of this listing/vehicle')
    
    # Rating categories (1-5 scale)
    overall_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    vehicle_condition_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        blank=True, null=True
    )
    value_for_money_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        blank=True, null=True
    )
    listing_accuracy_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        blank=True, null=True
    )
    seller_interaction_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        blank=True, null=True
    )
    
    # Review metadata
    status = models.CharField(max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.PENDING)
    is_verified_purchase = models.BooleanField(default=False)
    helpful_votes = models.PositiveIntegerField(default=0)
    unhelpful_votes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Listing Review'
        verbose_name_plural = 'Listing Reviews'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['overall_rating']),
            models.Index(fields=['is_verified_purchase']),
        ]
        unique_together = ['user', 'listing']
    
    def __str__(self):
        return f"{self.title} - Review for listing {self.listing.title}"


class ReviewImage(models.Model):
    """Images attached to reviews."""
    vehicle_review = models.ForeignKey(VehicleReview, on_delete=models.CASCADE, related_name='images', null=True, blank=True)
    dealer_review = models.ForeignKey(DealerReview, on_delete=models.CASCADE, related_name='images', null=True, blank=True)
    seller_review = models.ForeignKey(SellerReview, on_delete=models.CASCADE, related_name='images', null=True, blank=True)
    listing_review = models.ForeignKey(ListingReview, on_delete=models.CASCADE, related_name='images', null=True, blank=True)
    image = models.ImageField(upload_to='reviews/images/')
    caption = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        review = self.vehicle_review or self.dealer_review or self.seller_review or self.listing_review
        return f"Image for {review}"


class ReviewVote(models.Model):
    """Track helpful/unhelpful votes on reviews."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='review_votes')
    vehicle_review = models.ForeignKey(VehicleReview, on_delete=models.CASCADE, related_name='votes', null=True, blank=True)
    dealer_review = models.ForeignKey(DealerReview, on_delete=models.CASCADE, related_name='votes', null=True, blank=True)
    seller_review = models.ForeignKey(SellerReview, on_delete=models.CASCADE, related_name='votes', null=True, blank=True)
    listing_review = models.ForeignKey(ListingReview, on_delete=models.CASCADE, related_name='votes', null=True, blank=True)
    is_helpful = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [
            ('user', 'vehicle_review'),
            ('user', 'dealer_review'),
            ('user', 'seller_review'),
            ('user', 'listing_review'),
        ]
    
    def __str__(self):
        review = self.vehicle_review or self.dealer_review or self.seller_review or self.listing_review
        vote_type = "helpful" if self.is_helpful else "unhelpful"
        return f"{self.user.email} found review {review.id} {vote_type}"


class ReviewComment(models.Model):
    """Comments on vehicle, dealer, seller, or listing reviews."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='review_comments')
    vehicle_review = models.ForeignKey(VehicleReview, on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    dealer_review = models.ForeignKey(DealerReview, on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    seller_review = models.ForeignKey(SellerReview, on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    listing_review = models.ForeignKey(ListingReview, on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    content = models.TextField()
    status = models.CharField(max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        review = self.vehicle_review or self.dealer_review or self.seller_review or self.listing_review
        return f"Comment by {self.user.email} on review {review.id}"


class ReviewLogAction(models.TextChoices):
    """Actions that can be logged for reviews."""
    CREATED = 'created', 'Created'
    UPDATED = 'updated', 'Updated'
    DELETED = 'deleted', 'Deleted'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    SUSPENDED = 'suspended', 'Suspended'
    PUBLISHED = 'published', 'Published'
    UNPUBLISHED = 'unpublished', 'Unpublished'
    VOTED = 'voted', 'Voted'
    COMMENTED = 'commented', 'Commented'
    FLAGGED = 'flagged', 'Flagged'
    UNFLAGGED = 'unflagged', 'Unflagged'
    VIEWED = 'viewed', 'Viewed'
    MODERATED = 'moderated', 'Moderated'


class ReviewLog(models.Model):
    """Comprehensive logging for all review interactions and administrative actions."""
    # User who performed the action
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Generic foreign key to any review type
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Action details
    action = models.CharField(max_length=20, choices=ReviewLogAction.choices)
    description = models.TextField(blank=True, null=True)
    
    # Additional metadata
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    
    # Previous and new values for updates
    previous_data = models.JSONField(blank=True, null=True, help_text='Previous state before action')
    new_data = models.JSONField(blank=True, null=True, help_text='New state after action')
    
    # Administrative details
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='admin_review_logs',
        help_text='Admin user who performed the action'
    )
    admin_reason = models.TextField(blank=True, null=True, help_text='Reason for administrative action')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Review Log'
        verbose_name_plural = 'Review Logs'
        indexes = [
            models.Index(fields=['action']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['user']),
            models.Index(fields=['admin_user']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        user_info = f"{self.user.email}" if self.user else "Anonymous"
        return f"{user_info} {self.action} {self.content_object} at {self.created_at}"
    
    @classmethod
    def log_action(cls, user, content_object, action, description=None, ip_address=None, 
                   user_agent=None, previous_data=None, new_data=None, admin_user=None, admin_reason=None):
        """Helper method to create log entries."""
        return cls.objects.create(
            user=user,
            content_object=content_object,
            action=action,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            previous_data=previous_data,
            new_data=new_data,
            admin_user=admin_user,
            admin_reason=admin_reason
        )
