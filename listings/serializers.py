"""
Comprehensive serializers for vehicle listings API.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import VehicleListing, ListingImage, ListingVideo, SavedListing, ListingView, ListingStatusLog
from users.serializers import UserSerializer
from vehicles.serializers import VehicleCategorySerializer

User = get_user_model()


class ListingImageSerializer(serializers.ModelSerializer):
    """Serializer for listing images."""
    
    class Meta:
        model = ListingImage
        fields = ['id', 'image', 'caption', 'is_primary', 'order', 'created_at']
        read_only_fields = ['id', 'created_at']


class ListingVideoSerializer(serializers.ModelSerializer):
    """Serializer for listing videos."""
    
    class Meta:
        model = ListingVideo
        fields = ['id', 'video', 'thumbnail', 'title', 'description', 'duration', 'order', 'created_at']
        read_only_fields = ['id', 'created_at']


class ListingStatusLogSerializer(serializers.ModelSerializer):
    """Serializer for listing status logs."""
    changed_by = UserSerializer(read_only=True)
    
    class Meta:
        model = ListingStatusLog
        fields = ['id', 'old_status', 'new_status', 'changed_by', 'reason', 'timestamp']
        read_only_fields = ['id', 'timestamp']


class VehicleListingListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing lists and search results."""
    user = UserSerializer(read_only=True)
    body_type = VehicleCategorySerializer(read_only=True)
    primary_image = serializers.SerializerMethodField()
    images = ListingImageSerializer(many=True, read_only=True)
    image_count = serializers.SerializerMethodField()
    location_display = serializers.SerializerMethodField()
    
    class Meta:
        model = VehicleListing
        fields = [
            'id', 'title', 'slug', 'price', 'year', 'make', 'model',
            'kilometers', 'fuel_type', 'transmission', 'exterior_color',
            'condition', 'status', 'is_featured',
            'body_type', 'location_display', 'primary_image', 'images', 'image_count', 'user', 'created_at',
            'views_count', 'inquiries_count'
        ]
        read_only_fields = ['id', 'slug', 'views_count', 'inquiries_count', 'created_at']
    
    def get_primary_image(self, obj):
        """Get the primary image URL."""
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image and primary_image.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(primary_image.image.url)
            return primary_image.image.url
        return None
    
    def get_image_count(self, obj):
        """Get the total number of images for this listing."""
        return obj.images.count()
    
    def get_location_display(self, obj):
        """Get formatted location display."""
        parts = []
        if obj.location_city:
            parts.append(obj.location_city)
        if obj.location_state:
            parts.append(obj.location_state)
        if obj.location_country:
            parts.append(obj.location_country)
        return ', '.join(parts) if parts else None


class VehicleListingDetailSerializer(serializers.ModelSerializer):
    """Comprehensive serializer for detailed listing views."""
    user = UserSerializer(read_only=True)
    body_type = VehicleCategorySerializer(read_only=True)
    images = ListingImageSerializer(many=True, read_only=True)
    videos = ListingVideoSerializer(many=True, read_only=True)
    status_logs = ListingStatusLogSerializer(many=True, read_only=True)
    is_saved = serializers.SerializerMethodField()
    allowed_transitions = serializers.SerializerMethodField()
    
    class Meta:
        model = VehicleListing
        fields = [
            'id', 'title', 'slug', 'description', 'price', 'year', 'make', 'model',
            'kilometers', 'fuel_type', 'transmission', 'engine_size', 'doors', 'seating_capacity',
            'exterior_color', 'interior_color', 'condition', 'vin', 'status',
            'is_featured', 'body_type', 'published_at', 'expires_at',
            'location_city', 'location_state', 'location_country',
            'warranty_information', 'additional_features', 'seller_notes',
            'user', 'images', 'videos', 'status_logs', 'is_saved',
            'allowed_transitions', 'views_count', 'inquiries_count',
            'created_at', 'updated_at', 'meta_title', 'meta_description', 'meta_keywords'
        ]
        read_only_fields = [
            'id', 'slug', 'views_count', 'inquiries_count', 'created_at', 
            'updated_at', 'published_at', 'status_logs', 'allowed_transitions'
        ]
    
    def get_is_saved(self, obj):
        """Check if listing is saved by current user."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return SavedListing.objects.filter(
                user=request.user, 
                listing=obj
            ).exists()
        return False
    
    def get_allowed_transitions(self, obj):
        """Get allowed status transitions for current user."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Only show transitions to listing owner or staff
            if request.user == obj.user or request.user.is_staff:
                return obj.get_allowed_transitions()
        return []


class VehicleListingCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating listings."""
    images = ListingImageSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        help_text="List of images to upload"
    )
    videos = ListingVideoSerializer(many=True, read_only=True)
    uploaded_videos = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False,
        help_text="List of videos to upload"
    )
    
    class Meta:
        model = VehicleListing
        fields = [
            'title', 'description', 'price', 'year', 'make', 'model',
            'kilometers', 'fuel_type', 'transmission', 'engine_size', 'doors', 'seating_capacity',
            'exterior_color', 'interior_color', 'condition', 'vin', 'body_type',
            'location_city', 'location_state', 'location_country',
            'warranty_information', 'additional_features', 'seller_notes',
            'expires_at', 'images', 'videos', 'uploaded_images', 'uploaded_videos',
            'meta_title', 'meta_description', 'meta_keywords'
        ]
        extra_kwargs = {
            'title': {'required': True},
            'description': {'required': True},
            'price': {'required': True, 'min_value': 0},
            'year': {'required': True},
            'make': {'required': True},
            'model': {'required': True},
        }
    
    def validate_price(self, value):
        """Validate price is positive."""
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0")
        return value
    
    def validate_year(self, value):
        """Validate year is reasonable."""
        from datetime import datetime
        current_year = datetime.now().year
        if value < 1900 or value > current_year + 1:
            raise serializers.ValidationError(
                f"Year must be between 1900 and {current_year + 1}"
            )
        return value
    
    def validate_kilometers(self, value):
        """Validate kilometers is not negative."""
        if value < 0:
            raise serializers.ValidationError("Kilometers cannot be negative")
        return value
    
    def create(self, validated_data):
        """Create listing with images and videos."""
        uploaded_images = validated_data.pop('uploaded_images', [])
        uploaded_videos = validated_data.pop('uploaded_videos', [])
        
        # Set user from request
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        
        listing = super().create(validated_data)
        
        # Create images
        for i, image in enumerate(uploaded_images):
            ListingImage.objects.create(
                listing=listing,
                image=image,
                is_primary=(i == 0),  # First image is primary
                order=i
            )
        
        # Create videos
        for i, video in enumerate(uploaded_videos):
            ListingVideo.objects.create(
                listing=listing,
                video=video,
                order=i
            )
        
        return listing
    
    def update(self, instance, validated_data):
        """Update listing with new images and videos."""
        uploaded_images = validated_data.pop('uploaded_images', [])
        uploaded_videos = validated_data.pop('uploaded_videos', [])
        
        listing = super().update(instance, validated_data)
        
        # Add new images (don't replace existing ones)
        existing_images_count = listing.images.count()
        for i, image in enumerate(uploaded_images):
            ListingImage.objects.create(
                listing=listing,
                image=image,
                is_primary=(existing_images_count == 0 and i == 0),
                order=existing_images_count + i
            )
        
        # Add new videos (don't replace existing ones)
        existing_videos_count = listing.videos.count()
        for i, video in enumerate(uploaded_videos):
            ListingVideo.objects.create(
                listing=listing,
                video=video,
                order=existing_videos_count + i
            )
        
        return listing


class SavedListingSerializer(serializers.ModelSerializer):
    """Serializer for saved listings with comprehensive vehicle details."""
    listing = VehicleListingDetailSerializer(read_only=True)
    listing_id = serializers.IntegerField(write_only=True, source='listing')
    
    class Meta:
        model = SavedListing
        fields = ['id', 'listing', 'listing_id', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def validate_listing_id(self, value):
        """Validate that the listing exists and is published."""
        try:
            listing = VehicleListing.objects.get(id=value)
            if listing.status != 'published':
                raise serializers.ValidationError("Cannot save unpublished listings.")
            return listing
        except VehicleListing.DoesNotExist:
            raise serializers.ValidationError("Listing does not exist.")
    
    def validate(self, attrs):
        """Validate that user hasn't already saved this listing."""
        user = self.context['request'].user
        listing = attrs.get('listing')
        
        if SavedListing.objects.filter(user=user, listing=listing).exists():
            raise serializers.ValidationError("You have already saved this listing.")
        
        return attrs


class ListingViewSerializer(serializers.ModelSerializer):
    """Serializer for listing views/analytics."""
    user = UserSerializer(read_only=True)
    listing = VehicleListingListSerializer(read_only=True)
    
    class Meta:
        model = ListingView
        fields = ['id', 'listing', 'user', 'ip_address', 'user_agent', 'created_at']
        read_only_fields = ['id', 'created_at']


class VehicleListingStatusSerializer(serializers.Serializer):
    """Serializer for status change operations."""
    status = serializers.ChoiceField(choices=VehicleListing._meta.get_field('status').choices)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)
    
    def validate(self, data):
        """Validate status transition."""
        listing = self.context.get('listing')
        new_status = data['status']
        
        if listing and not listing.can_transition_to(new_status):
            allowed = listing.get_allowed_transitions()
            raise serializers.ValidationError({
                'status': f"Cannot transition to {new_status}. Allowed: {allowed}"
            })
        
        # Validate reason for rejection
        if new_status == 'rejected' and not data.get('reason'):
            raise serializers.ValidationError({
                'reason': 'Reason is required when rejecting a listing'
            })
        
        return data


class VehicleListingStatsSerializer(serializers.Serializer):
    """Serializer for listing statistics."""
    total_listings = serializers.IntegerField()
    published_listings = serializers.IntegerField()
    draft_listings = serializers.IntegerField()
    sold_listings = serializers.IntegerField()
    total_views = serializers.IntegerField()
    total_inquiries = serializers.IntegerField()
    avg_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    popular_makes = serializers.ListField(child=serializers.DictField())
    recent_activity = serializers.ListField(child=serializers.DictField())