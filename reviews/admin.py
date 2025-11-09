from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.admin import SimpleListFilter
from django.contrib import messages
from django.http import HttpRequest
from .models import (
    VehicleReview, DealerReview, SellerReview, ListingReview,
    ReviewImage, ReviewVote, ReviewComment, ReviewLog
)


class ReviewStatusFilter(SimpleListFilter):
    """Filter reviews by status."""
    title = 'Review Status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return [
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('flagged', 'Flagged'),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


class ReviewImageInline(admin.TabularInline):
    """Inline admin for review images."""
    model = ReviewImage
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('image', 'caption', 'created_at')


class ReviewVoteInline(admin.TabularInline):
    """Inline admin for review votes."""
    model = ReviewVote
    extra = 0
    readonly_fields = ('user', 'is_helpful', 'created_at')
    fields = ('user', 'is_helpful', 'created_at')


class ReviewCommentInline(admin.TabularInline):
    """Inline admin for review comments."""
    model = ReviewComment
    extra = 0
    readonly_fields = ('user', 'created_at')
    fields = ('user', 'comment', 'created_at')


class BaseReviewAdmin(admin.ModelAdmin):
    """Base admin class for all review types."""
    list_per_page = 25
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'helpful_votes', 'unhelpful_votes')
    
    def get_readonly_fields(self, request, obj=None):
        """Make certain fields readonly for non-superusers."""
        readonly = list(self.readonly_fields)
        if not request.user.is_superuser:
            readonly.extend(['user', 'created_at', 'updated_at'])
        return readonly
    
    def save_model(self, request, obj, form, change):
        """Log admin actions when saving reviews."""
        from .models import ReviewLog
        
        # Get previous data for logging
        previous_data = None
        if change and obj.pk:
            try:
                old_obj = obj.__class__.objects.get(pk=obj.pk)
                previous_data = {
                    'status': old_obj.status,
                    'overall_rating': old_obj.overall_rating,
                    'title': getattr(old_obj, 'title', ''),
                    'review_text': getattr(old_obj, 'review_text', ''),
                }
            except obj.__class__.DoesNotExist:
                pass
        
        # Save the object
        super().save_model(request, obj, form, change)
        
        # Log the action
        action = 'ADMIN_EDIT' if change else 'ADMIN_CREATE'
        new_data = {
            'status': obj.status,
            'overall_rating': obj.overall_rating,
            'title': getattr(obj, 'title', ''),
            'review_text': getattr(obj, 'review_text', ''),
        }
        
        ReviewLog.log_action(
            user=obj.user,
            content_object=obj,
            action=action,
            description=f"Review {action.lower().replace('admin_', '')}d by admin {request.user.email}",
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            previous_data=previous_data,
            new_data=new_data,
            admin_user=request.user,
            admin_reason=f"Administrative {action.lower().replace('admin_', '')}"
        )
        
        # Add success message
        action_name = "updated" if change else "created"
        messages.success(request, f"Review {action_name} successfully and logged.")
    
    def delete_model(self, request, obj):
        """Log admin actions when deleting reviews."""
        from .models import ReviewLog
        
        # Log before deletion
        ReviewLog.log_action(
            user=obj.user,
            content_object=obj,
            action='ADMIN_DELETE',
            description=f"Review deleted by admin {request.user.email}",
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            previous_data={
                'status': obj.status,
                'overall_rating': obj.overall_rating,
                'title': getattr(obj, 'title', ''),
                'review_text': getattr(obj, 'review_text', ''),
            },
            admin_user=request.user,
            admin_reason="Administrative deletion"
        )
        
        super().delete_model(request, obj)
        messages.success(request, "Review deleted successfully and logged.")
    
    def get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def approve_reviews(self, request, queryset):
        """Bulk action to approve reviews."""
        from .models import ReviewLog
        
        updated = 0
        for review in queryset:
            if review.status != 'approved':
                old_status = review.status
                review.status = 'approved'
                review.save()
                
                # Log the approval
                ReviewLog.log_action(
                    user=review.user,
                    content_object=review,
                    action='ADMIN_APPROVE',
                    description=f"Review approved by admin {request.user.email}",
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    previous_data={'status': old_status},
                    new_data={'status': 'approved'},
                    admin_user=request.user,
                    admin_reason="Bulk approval"
                )
                updated += 1
        
        messages.success(request, f"{updated} review(s) approved successfully.")
    approve_reviews.short_description = "Approve selected reviews"
    
    def reject_reviews(self, request, queryset):
        """Bulk action to reject reviews."""
        from .models import ReviewLog
        
        updated = 0
        for review in queryset:
            if review.status != 'rejected':
                old_status = review.status
                review.status = 'rejected'
                review.save()
                
                # Log the rejection
                ReviewLog.log_action(
                    user=review.user,
                    content_object=review,
                    action='ADMIN_REJECT',
                    description=f"Review rejected by admin {request.user.email}",
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    previous_data={'status': old_status},
                    new_data={'status': 'rejected'},
                    admin_user=request.user,
                    admin_reason="Bulk rejection"
                )
                updated += 1
        
        messages.success(request, f"{updated} review(s) rejected successfully.")
    reject_reviews.short_description = "Reject selected reviews"
    
    def flag_reviews(self, request, queryset):
        """Bulk action to flag reviews for review."""
        from .models import ReviewLog
        
        updated = 0
        for review in queryset:
            if review.status != 'flagged':
                old_status = review.status
                review.status = 'flagged'
                review.save()
                
                # Log the flagging
                ReviewLog.log_action(
                    user=review.user,
                    content_object=review,
                    action='ADMIN_FLAG',
                    description=f"Review flagged by admin {request.user.email}",
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    previous_data={'status': old_status},
                    new_data={'status': 'flagged'},
                    admin_user=request.user,
                    admin_reason="Bulk flagging"
                )
                updated += 1
        
        messages.success(request, f"{updated} review(s) flagged successfully.")
    flag_reviews.short_description = "Flag selected reviews"
    
    actions = ['approve_reviews', 'reject_reviews', 'flag_reviews']


@admin.register(VehicleReview)
class VehicleReviewAdmin(BaseReviewAdmin):
    """Admin interface for vehicle reviews."""
    list_display = [
        'title', 'user_email', 'vehicle_display', 'overall_rating', 
        'status', 'created_at', 'helpful_votes', 'unhelpful_votes'
    ]
    list_filter = [ReviewStatusFilter, 'overall_rating', 'created_at']
    search_fields = ['title', 'review_text', 'user__email', 'vehicle__make', 'vehicle__model']
    inlines = [ReviewImageInline, ReviewVoteInline, ReviewCommentInline]
    
    fieldsets = (
        ('Review Information', {
            'fields': ('user', 'vehicle', 'title', 'review_text', 'overall_rating', 'status')
        }),
        ('Detailed Ratings', {
            'fields': ('performance_rating', 'reliability_rating', 'fuel_economy_rating', 
                      'comfort_rating', 'value_rating'),
            'classes': ('collapse',)
        }),
        ('Review Details', {
            'fields': ('pros', 'cons', 'is_verified_purchase'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'helpful_votes', 'unhelpful_votes'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    
    def vehicle_display(self, obj):
        return f"{obj.vehicle.year} {obj.vehicle.make} {obj.vehicle.model}"
    vehicle_display.short_description = 'Vehicle'


@admin.register(DealerReview)
class DealerReviewAdmin(BaseReviewAdmin):
    """Admin interface for dealer reviews."""
    list_display = [
        'title', 'user_email', 'dealer_display', 'overall_rating', 
        'status', 'created_at', 'helpful_votes', 'unhelpful_votes'
    ]
    list_filter = [ReviewStatusFilter, 'overall_rating', 'created_at']
    search_fields = ['title', 'review_text', 'user__email', 'dealer__email', 'dealer__business_name']
    inlines = [ReviewImageInline, ReviewVoteInline, ReviewCommentInline]
    
    fieldsets = (
        ('Review Information', {
            'fields': ('user', 'dealer', 'title', 'review_text', 'overall_rating', 'status')
        }),
        ('Detailed Ratings', {
            'fields': ('customer_service_rating', 'communication_rating', 'delivery_rating', 
                      'value_rating'),
            'classes': ('collapse',)
        }),
        ('Review Details', {
            'fields': ('pros', 'cons', 'is_verified_purchase'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'helpful_votes', 'unhelpful_votes'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    
    def dealer_display(self, obj):
        return obj.dealer.business_name or obj.dealer.email
    dealer_display.short_description = 'Dealer'


@admin.register(SellerReview)
class SellerReviewAdmin(BaseReviewAdmin):
    """Admin interface for seller reviews."""
    list_display = [
        'title', 'user_email', 'seller_display', 'overall_rating', 
        'status', 'created_at', 'helpful_votes', 'unhelpful_votes'
    ]
    list_filter = [ReviewStatusFilter, 'overall_rating', 'is_verified_transaction', 'created_at']
    search_fields = ['title', 'review_text', 'user__email', 'seller__email']
    inlines = [ReviewImageInline, ReviewVoteInline, ReviewCommentInline]
    
    fieldsets = (
        ('Review Information', {
            'fields': ('user', 'seller', 'title', 'review_text', 'overall_rating', 'status')
        }),
        ('Detailed Ratings', {
            'fields': ('communication_rating', 'reliability_rating', 'responsiveness_rating'),
            'classes': ('collapse',)
        }),
        ('Review Details', {
            'fields': ('pros', 'cons', 'is_verified_transaction'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'helpful_votes', 'unhelpful_votes'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    
    def seller_display(self, obj):
        return obj.seller.email
    seller_display.short_description = 'Seller'


@admin.register(ListingReview)
class ListingReviewAdmin(BaseReviewAdmin):
    """Admin interface for listing reviews."""
    list_display = [
        'title', 'user_email', 'listing_display', 'overall_rating', 
        'status', 'created_at', 'helpful_votes', 'unhelpful_votes'
    ]
    list_filter = [ReviewStatusFilter, 'overall_rating', 'is_verified_purchase', 'created_at']
    search_fields = ['title', 'review_text', 'user__email', 'listing__title']
    inlines = [ReviewImageInline, ReviewVoteInline, ReviewCommentInline]
    
    fieldsets = (
        ('Review Information', {
            'fields': ('user', 'listing', 'title', 'review_text', 'overall_rating', 'status')
        }),
        ('Detailed Ratings', {
            'fields': ('condition_rating', 'value_rating', 'description_accuracy_rating'),
            'classes': ('collapse',)
        }),
        ('Review Details', {
            'fields': ('pros', 'cons', 'is_verified_purchase'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'helpful_votes', 'unhelpful_votes'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    
    def listing_display(self, obj):
        return obj.listing.title
    listing_display.short_description = 'Listing'


@admin.register(ReviewImage)
class ReviewImageAdmin(admin.ModelAdmin):
    """Admin interface for review images."""
    list_display = ['image_preview', 'review_display', 'caption', 'created_at']
    list_filter = ['created_at']
    search_fields = ['caption']
    readonly_fields = ['created_at', 'image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 100px;" />', obj.image.url)
        return "No image"
    image_preview.short_description = 'Preview'
    
    def review_display(self, obj):
        review = obj.vehicle_review or obj.dealer_review or obj.seller_review or obj.listing_review
        return str(review)
    review_display.short_description = 'Review'


@admin.register(ReviewVote)
class ReviewVoteAdmin(admin.ModelAdmin):
    """Admin interface for review votes."""
    list_display = ['user', 'review_display', 'vote_type', 'created_at']
    list_filter = ['is_helpful', 'created_at']
    search_fields = ['user__email']
    readonly_fields = ['created_at']
    
    def review_display(self, obj):
        review = obj.vehicle_review or obj.dealer_review or obj.seller_review or obj.listing_review
        return str(review)
    review_display.short_description = 'Review'
    
    def vote_type(self, obj):
        return "Helpful" if obj.is_helpful else "Unhelpful"
    vote_type.short_description = 'Vote Type'


@admin.register(ReviewComment)
class ReviewCommentAdmin(admin.ModelAdmin):
    """Admin interface for review comments."""
    list_display = ['user', 'review_display', 'comment_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__email', 'comment']
    readonly_fields = ['created_at']
    
    def review_display(self, obj):
        review = obj.vehicle_review or obj.dealer_review or obj.seller_review or obj.listing_review
        return str(review)
    review_display.short_description = 'Review'
    
    def comment_preview(self, obj):
        return obj.comment[:50] + "..." if len(obj.comment) > 50 else obj.comment
    comment_preview.short_description = 'Comment'


@admin.register(ReviewLog)
class ReviewLogAdmin(admin.ModelAdmin):
    """Admin interface for review logs."""
    list_display = ['user', 'action', 'content_object_display', 'admin_user', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['user__email', 'description', 'admin_user__email']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Log Information', {
            'fields': ('user', 'content_type', 'object_id', 'action', 'description')
        }),
        ('Request Details', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Data Changes', {
            'fields': ('previous_data', 'new_data'),
            'classes': ('collapse',)
        }),
        ('Administrative', {
            'fields': ('admin_user', 'admin_reason'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def content_object_display(self, obj):
        return str(obj.content_object) if obj.content_object else "Deleted"
    content_object_display.short_description = 'Review Object'
    
    def has_add_permission(self, request):
        """Prevent manual creation of log entries."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Make logs read-only."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of log entries."""
        return request.user.is_superuser
