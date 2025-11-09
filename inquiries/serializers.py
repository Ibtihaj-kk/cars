from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ListingInquiry, InquiryResponse, TestDriveRequest
from listings.serializers import VehicleListingListSerializer
from users.serializers import UserSerializer

User = get_user_model()


class TestDriveRequestSerializer(serializers.ModelSerializer):
    """Serializer for test drive requests."""
    
    class Meta:
        model = TestDriveRequest
        fields = ['id', 'inquiry', 'preferred_date', 'preferred_time', 'alternate_date', 
                 'alternate_time', 'location_preference', 'additional_notes', 
                 'is_confirmed', 'confirmation_date', 'confirmed_by']


class InquiryResponseSerializer(serializers.ModelSerializer):
    """Serializer for inquiry responses."""
    responder = UserSerializer(read_only=True)
    
    class Meta:
        model = InquiryResponse
        fields = ['id', 'inquiry', 'responder', 'message', 'created_at', 'is_read']
        read_only_fields = ['responder']
    
    def create(self, validated_data):
        validated_data['responder'] = self.context['request'].user
        return super().create(validated_data)


class ListingInquiryListSerializer(serializers.ModelSerializer):
    """Serializer for listing inquiries."""
    user = UserSerializer(read_only=True)
    listing = VehicleListingListSerializer(read_only=True)
    seller = UserSerializer(read_only=True)
    response_count = serializers.SerializerMethodField()
    has_test_drive = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_new = serializers.BooleanField(read_only=True)
    is_viewed = serializers.BooleanField(read_only=True)
    is_replied = serializers.BooleanField(read_only=True)
    is_closed = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = ListingInquiry
        fields = ['id', 'user', 'listing', 'seller', 'name', 'email', 'phone',
                 'inquiry_type', 'message', 'status', 'status_display', 'is_read',
                 'is_new', 'is_viewed', 'is_replied', 'is_closed',
                 'created_at', 'updated_at', 'response_count', 'has_test_drive']
    
    def get_response_count(self, obj):
        return obj.responses.count()
    
    def get_has_test_drive(self, obj):
        return hasattr(obj, 'test_drive_details')


class ListingInquiryDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed listing inquiry view."""
    user = UserSerializer(read_only=True)
    listing = VehicleListingListSerializer(read_only=True)
    seller = UserSerializer(read_only=True)
    responses = InquiryResponseSerializer(many=True, read_only=True)
    test_drive = TestDriveRequestSerializer(source='test_drive_details', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_new = serializers.BooleanField(read_only=True)
    is_viewed = serializers.BooleanField(read_only=True)
    is_replied = serializers.BooleanField(read_only=True)
    is_closed = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = ListingInquiry
        fields = ['id', 'user', 'listing', 'seller', 'name', 'email', 'phone',
                 'inquiry_type', 'message', 'status', 'status_display', 'is_read',
                 'is_new', 'is_viewed', 'is_replied', 'is_closed',
                 'created_at', 'updated_at', 'responses', 'test_drive']


class ListingInquiryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating listing inquiries."""
    test_drive_data = TestDriveRequestSerializer(required=False, write_only=True)
    
    class Meta:
        model = ListingInquiry
        fields = ['listing', 'inquiry_type', 'message', 'test_drive_data']
    
    def create(self, validated_data):
        test_drive_data = validated_data.pop('test_drive_data', None)
        
        # Set the user from the request
        validated_data['user'] = self.context['request'].user
        
        # Create the inquiry
        inquiry = ListingInquiry.objects.create(**validated_data)
        
        # Create test drive request if provided
        if test_drive_data and inquiry.inquiry_type == ListingInquiry.InquiryType.TEST_DRIVE:
            TestDriveRequest.objects.create(inquiry=inquiry, **test_drive_data)
        
        return inquiry


class InquiryResponseCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating inquiry responses."""
    
    class Meta:
        model = InquiryResponse
        fields = ['inquiry', 'message']
    
    def create(self, validated_data):
        validated_data['responder'] = self.context['request'].user
        return super().create(validated_data)


class TestDriveRequestUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating test drive requests."""
    
    class Meta:
        model = TestDriveRequest
        fields = ['preferred_date', 'preferred_time', 'alternate_date', 
                 'alternate_time', 'location_preference', 'additional_notes', 'is_confirmed']


class ReceivedInquirySerializer(serializers.ModelSerializer):
    """Serializer for received inquiries endpoint with specific format."""
    inquiry_id = serializers.IntegerField(source='id', read_only=True)
    listing_id = serializers.IntegerField(source='listing.id', read_only=True)
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ListingInquiry
        fields = ['inquiry_id', 'listing_id', 'user_name', 'message', 'created_at']
    
    def get_user_name(self, obj):
        """Get the full name of the user who made the inquiry."""
        if obj.user:
            full_name = f"{obj.user.first_name} {obj.user.last_name}".strip()
            return full_name if full_name else obj.user.email
        return "Unknown User"


class UnauthenticatedInquiryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating inquiries without authentication."""
    listing_id = serializers.IntegerField(write_only=True)
    user_name = serializers.CharField(max_length=255, write_only=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    
    class Meta:
        model = ListingInquiry
        fields = ['listing_id', 'user_name', 'message', 'email']
    
    def validate_listing_id(self, value):
        """Validate that the listing exists and is published."""
        from listings.models import VehicleListing, ListingStatus
        try:
            listing = VehicleListing.objects.get(id=value, status=ListingStatus.PUBLISHED)
            return value
        except VehicleListing.DoesNotExist:
            raise serializers.ValidationError("Listing not found or not available for inquiries.")
    
    def create(self, validated_data):
        """Create inquiry for unauthenticated user."""
        from listings.models import VehicleListing
        
        listing_id = validated_data.pop('listing_id')
        user_name = validated_data.pop('user_name')
        
        # Get the listing
        listing = VehicleListing.objects.get(id=listing_id)
        
        # Create inquiry with unauthenticated user data
        inquiry = ListingInquiry.objects.create(
            listing=listing,
            user=None,  # No authenticated user
            name=user_name,
            email=validated_data.get('email', ''),
            message=validated_data['message'],
            inquiry_type=validated_data.get('inquiry_type', 'general'),
            ip_address=self.context.get('ip_address'),
            user_agent=self.context.get('user_agent')
        )
        
        return inquiry