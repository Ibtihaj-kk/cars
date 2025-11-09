from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    VehicleReview, DealerReview, SellerReview, ListingReview,
    ReviewImage, ReviewVote, ReviewComment
)
from vehicles.serializers import VehicleModelListSerializer
from users.serializers import UserSerializer

User = get_user_model()


class ReviewImageSerializer(serializers.ModelSerializer):
    """Serializer for review images."""
    
    class Meta:
        model = ReviewImage
        fields = ['id', 'image', 'caption', 'created_at']


class ReviewVoteSerializer(serializers.ModelSerializer):
    """Serializer for review votes."""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = ReviewVote
        fields = ['id', 'user', 'is_helpful', 'created_at']
        read_only_fields = ['user']


class ReviewCommentSerializer(serializers.ModelSerializer):
    """Serializer for review comments."""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = ReviewComment
        fields = ['id', 'user', 'content', 'created_at', 'updated_at']
        read_only_fields = ['user']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class VehicleReviewListSerializer(serializers.ModelSerializer):
    """Serializer for listing vehicle reviews."""
    user = UserSerializer(read_only=True)
    vehicle_model = VehicleModelListSerializer(read_only=True)
    helpful_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    
    class Meta:
        model = VehicleReview
        fields = [
            'id', 'user', 'vehicle_model', 'title', 'content', 'overall_rating',
            'created_at', 'status', 'helpful_count', 'comment_count'
        ]
    
    def get_helpful_count(self, obj):
        return obj.reviewvote_set.filter(is_helpful=True).count()
    
    def get_comment_count(self, obj):
        return obj.reviewcomment_set.count()


class VehicleReviewDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for vehicle reviews."""
    user = UserSerializer(read_only=True)
    vehicle_model = VehicleModelListSerializer(read_only=True)
    images = ReviewImageSerializer(source='reviewimage_set', many=True, read_only=True)
    votes = ReviewVoteSerializer(source='reviewvote_set', many=True, read_only=True)
    comments = ReviewCommentSerializer(source='reviewcomment_set', many=True, read_only=True)
    helpful_count = serializers.SerializerMethodField()
    unhelpful_count = serializers.SerializerMethodField()
    user_vote = serializers.SerializerMethodField()
    
    class Meta:
        model = VehicleReview
        fields = [
            'id', 'user', 'vehicle_model', 'year', 'title', 'content', 'pros', 'cons',
            'overall_rating', 'performance_rating', 'comfort_rating',
            'reliability_rating', 'value_rating', 'fuel_economy_rating', 'created_at',
            'updated_at', 'status', 'images', 'votes', 'comments', 'helpful_count',
            'unhelpful_count', 'user_vote'
        ]
    
    def get_helpful_count(self, obj):
        return obj.reviewvote_set.filter(is_helpful=True).count()
    
    def get_unhelpful_count(self, obj):
        return obj.reviewvote_set.filter(is_helpful=False).count()
    
    def get_user_vote(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            vote = obj.reviewvote_set.filter(user=request.user).first()
            if vote:
                return {'id': vote.id, 'is_helpful': vote.is_helpful}
        return None


class VehicleReviewCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating vehicle reviews."""
    images = serializers.ListField(child=serializers.ImageField(), required=False, write_only=True)
    image_captions = serializers.ListField(child=serializers.CharField(), required=False, write_only=True)
    
    class Meta:
        model = VehicleReview
        fields = [
            'id', 'vehicle_model', 'year', 'title', 'content', 'pros', 'cons',
            'overall_rating', 'performance_rating', 'comfort_rating',
            'reliability_rating', 'value_rating', 'fuel_economy_rating', 'images',
            'image_captions'
        ]
    
    def create(self, validated_data):
        images_data = validated_data.pop('images', [])
        image_captions = validated_data.pop('image_captions', [])
        
        # Set the user from the request
        validated_data['user'] = self.context['request'].user
        
        # Create the review
        review = VehicleReview.objects.create(**validated_data)
        
        # Create images
        self._process_images(review, images_data, image_captions)
        
        return review
    
    def update(self, instance, validated_data):
        images_data = validated_data.pop('images', None)
        image_captions = validated_data.pop('image_captions', [])
        
        # Update review fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update images if provided
        if images_data is not None:
            # Clear existing images
            instance.reviewimage_set.all().delete()
            # Create new images
            self._process_images(instance, images_data, image_captions)
        
        return instance
    
    def _process_images(self, review, images_data, image_captions):
        for i, image_data in enumerate(images_data):
            caption = image_captions[i] if i < len(image_captions) else ''
            ReviewImage.objects.create(
                review=review,
                image=image_data,
                caption=caption
            )


class DealerReviewListSerializer(serializers.ModelSerializer):
    """Serializer for listing dealer reviews."""
    user = UserSerializer(read_only=True)
    dealer = UserSerializer(read_only=True)
    helpful_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DealerReview
        fields = [
            'id', 'user', 'dealer', 'title', 'content', 'overall_rating',
            'created_at', 'status', 'helpful_count', 'comment_count'
        ]
    
    def get_helpful_count(self, obj):
        return obj.reviewvote_set.filter(is_helpful=True).count()
    
    def get_comment_count(self, obj):
        return obj.reviewcomment_set.count()


class DealerReviewDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for dealer reviews."""
    user = UserSerializer(read_only=True)
    dealer = UserSerializer(read_only=True)
    images = ReviewImageSerializer(source='reviewimage_set', many=True, read_only=True)
    votes = ReviewVoteSerializer(source='reviewvote_set', many=True, read_only=True)
    comments = ReviewCommentSerializer(source='reviewcomment_set', many=True, read_only=True)
    helpful_count = serializers.SerializerMethodField()
    unhelpful_count = serializers.SerializerMethodField()
    user_vote = serializers.SerializerMethodField()
    
    class Meta:
        model = DealerReview
        fields = [
            'id', 'user', 'dealer', 'title', 'content', 'pros', 'cons',
            'overall_rating', 'customer_service_rating', 'buying_process_rating',
            'price_fairness_rating', 'facility_rating', 'created_at', 'updated_at',
            'status', 'images', 'votes', 'comments', 'helpful_count', 'unhelpful_count',
            'user_vote'
        ]
    
    def get_helpful_count(self, obj):
        return obj.reviewvote_set.filter(is_helpful=True).count()
    
    def get_unhelpful_count(self, obj):
        return obj.reviewvote_set.filter(is_helpful=False).count()
    
    def get_user_vote(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            vote = obj.reviewvote_set.filter(user=request.user).first()
            if vote:
                return {'id': vote.id, 'is_helpful': vote.is_helpful}
        return None


class DealerReviewCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating dealer reviews."""
    images = serializers.ListField(child=serializers.ImageField(), required=False, write_only=True)
    image_captions = serializers.ListField(child=serializers.CharField(), required=False, write_only=True)
    
    class Meta:
        model = DealerReview
        fields = [
            'dealer', 'title', 'content', 'pros', 'cons',
            'overall_rating', 'customer_service_rating', 'buying_process_rating',
            'price_fairness_rating', 'facility_rating', 'images', 'image_captions'
        ]
    
    def create(self, validated_data):
        images_data = validated_data.pop('images', [])
        image_captions = validated_data.pop('image_captions', [])
        
        # Set the user from the request
        validated_data['user'] = self.context['request'].user
        
        # Create the review
        review = DealerReview.objects.create(**validated_data)
        
        # Create images
        self._process_images(review, images_data, image_captions)
        
        return review
    
    def update(self, instance, validated_data):
        images_data = validated_data.pop('images', None)
        image_captions = validated_data.pop('image_captions', [])
        
        # Update review fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update images if provided
        if images_data is not None:
            # Clear existing images
            instance.reviewimage_set.all().delete()
            # Create new images
            self._process_images(instance, images_data, image_captions)
        
        return instance
    
    def _process_images(self, review, images_data, image_captions):
        for i, image_data in enumerate(images_data):
            caption = image_captions[i] if i < len(image_captions) else ''
            ReviewImage.objects.create(
                review=review,
                image=image_data,
                caption=caption
            )


class ReviewVoteCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating review votes."""
    
    class Meta:
        model = ReviewVote
        fields = ['review_type', 'review_id', 'is_helpful']
        
    review_type = serializers.ChoiceField(choices=['vehicle', 'dealer'])
    review_id = serializers.IntegerField()
    
    def validate(self, data):
        review_type = data.pop('review_type')
        review_id = data.pop('review_id')
        
        # Get the review based on type
        if review_type == 'vehicle':
            try:
                review = VehicleReview.objects.get(id=review_id)
                data['vehicle_review'] = review
            except VehicleReview.DoesNotExist:
                raise serializers.ValidationError({'review_id': 'Vehicle review not found.'})
        else:  # dealer
            try:
                review = DealerReview.objects.get(id=review_id)
                data['dealer_review'] = review
            except DealerReview.DoesNotExist:
                raise serializers.ValidationError({'review_id': 'Dealer review not found.'})
        
        return data
    
    def create(self, validated_data):
        user = self.context['request'].user
        is_helpful = validated_data.get('is_helpful')
        
        # Check if vehicle_review or dealer_review is in validated_data
        vehicle_review = validated_data.get('vehicle_review')
        dealer_review = validated_data.get('dealer_review')
        
        # Delete existing vote if any
        if vehicle_review:
            ReviewVote.objects.filter(user=user, vehicle_review=vehicle_review).delete()
            return ReviewVote.objects.create(user=user, vehicle_review=vehicle_review, is_helpful=is_helpful)
        else:  # dealer_review
            ReviewVote.objects.filter(user=user, dealer_review=dealer_review).delete()
            return ReviewVote.objects.create(user=user, dealer_review=dealer_review, is_helpful=is_helpful)


class SellerReviewListSerializer(serializers.ModelSerializer):
    """Serializer for listing seller reviews."""
    user = serializers.StringRelatedField()
    seller = serializers.StringRelatedField()
    helpful_votes = serializers.IntegerField(read_only=True)
    unhelpful_votes = serializers.IntegerField(read_only=True)
    images = ReviewImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = SellerReview
        fields = [
            'id', 'user', 'seller', 'title', 'content', 'overall_rating',
            'communication_rating', 'reliability_rating', 'responsiveness_rating',
            'pros', 'cons', 'status', 'is_verified_transaction',
            'helpful_votes', 'unhelpful_votes', 'images', 'created_at', 'updated_at'
        ]


class SellerReviewDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for seller reviews with comments and votes."""
    user = serializers.StringRelatedField()
    seller = serializers.StringRelatedField()
    helpful_votes = serializers.IntegerField(read_only=True)
    unhelpful_votes = serializers.IntegerField(read_only=True)
    images = ReviewImageSerializer(many=True, read_only=True)
    comments = ReviewCommentSerializer(many=True, read_only=True)
    votes = ReviewVoteSerializer(many=True, read_only=True)
    
    class Meta:
        model = SellerReview
        fields = [
            'id', 'user', 'seller', 'title', 'content', 'overall_rating',
            'communication_rating', 'reliability_rating', 'responsiveness_rating',
            'pros', 'cons', 'status', 'is_verified_transaction',
            'helpful_votes', 'unhelpful_votes', 'images', 'comments', 'votes',
            'created_at', 'updated_at'
        ]


class SellerReviewCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating seller reviews."""
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        allow_empty=True
    )
    image_captions = serializers.ListField(
        child=serializers.CharField(max_length=255, allow_blank=True),
        write_only=True,
        required=False,
        allow_empty=True
    )
    
    class Meta:
        model = SellerReview
        fields = [
            'id', 'seller', 'title', 'content', 'overall_rating',
            'communication_rating', 'reliability_rating', 'responsiveness_rating',
            'pros', 'cons', 'is_verified_transaction', 'images', 'image_captions'
        ]
    
    def validate_overall_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Overall rating must be between 1 and 5.")
        return value
    
    def validate(self, data):
        # Validate that images and captions lists have the same length
        images = data.get('images', [])
        captions = data.get('image_captions', [])
        
        if len(images) != len(captions) and captions:
            raise serializers.ValidationError(
                "Number of images and captions must match."
            )
        
        return data
    
    def create(self, validated_data):
        images = validated_data.pop('images', [])
        image_captions = validated_data.pop('image_captions', [])
        
        review = SellerReview.objects.create(**validated_data)
        
        # Create review images
        for i, image in enumerate(images):
            caption = image_captions[i] if i < len(image_captions) else ''
            ReviewImage.objects.create(
                seller_review=review,
                image=image,
                caption=caption
            )
        
        return review
    
    def update(self, instance, validated_data):
        images = validated_data.pop('images', [])
        image_captions = validated_data.pop('image_captions', [])
        
        # Update review fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Handle new images (existing images are not replaced)
        for i, image in enumerate(images):
            caption = image_captions[i] if i < len(image_captions) else ''
            ReviewImage.objects.create(
                seller_review=instance,
                image=image,
                caption=caption
            )
        
        return instance


class ListingReviewListSerializer(serializers.ModelSerializer):
    """Serializer for listing listing reviews."""
    user = serializers.StringRelatedField()
    listing = serializers.StringRelatedField()
    helpful_votes = serializers.IntegerField(read_only=True)
    unhelpful_votes = serializers.IntegerField(read_only=True)
    images = ReviewImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = ListingReview
        fields = [
            'id', 'user', 'listing', 'title', 'content', 'overall_rating',
            'vehicle_condition_rating', 'value_for_money_rating', 'listing_accuracy_rating',
            'seller_interaction_rating', 'pros', 'cons', 'status', 'is_verified_purchase',
            'helpful_votes', 'unhelpful_votes', 'images', 'created_at', 'updated_at'
        ]


class ListingReviewDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for listing reviews with comments and votes."""
    user = serializers.StringRelatedField()
    listing = serializers.StringRelatedField()
    helpful_votes = serializers.IntegerField(read_only=True)
    unhelpful_votes = serializers.IntegerField(read_only=True)
    images = ReviewImageSerializer(many=True, read_only=True)
    comments = ReviewCommentSerializer(many=True, read_only=True)
    votes = ReviewVoteSerializer(many=True, read_only=True)
    
    class Meta:
        model = ListingReview
        fields = [
            'id', 'user', 'listing', 'title', 'content', 'overall_rating',
            'vehicle_condition_rating', 'value_for_money_rating', 'listing_accuracy_rating',
            'seller_interaction_rating', 'pros', 'cons', 'status', 'is_verified_purchase',
            'helpful_votes', 'unhelpful_votes', 'images', 'comments', 'votes',
            'created_at', 'updated_at'
        ]


class ListingReviewCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating listing reviews."""
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        allow_empty=True
    )
    image_captions = serializers.ListField(
        child=serializers.CharField(max_length=255, allow_blank=True),
        write_only=True,
        required=False,
        allow_empty=True
    )
    
    class Meta:
        model = ListingReview
        fields = [
            'id', 'listing', 'title', 'content', 'overall_rating',
            'vehicle_condition_rating', 'value_for_money_rating', 'listing_accuracy_rating',
            'seller_interaction_rating', 'pros', 'cons', 'is_verified_purchase', 'images', 'image_captions'
        ]
    
    def validate_overall_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Overall rating must be between 1 and 5.")
        return value
    
    def validate(self, data):
        # Validate that images and captions lists have the same length
        images = data.get('images', [])
        captions = data.get('image_captions', [])
        
        if len(images) != len(captions) and captions:
            raise serializers.ValidationError(
                "Number of images and captions must match."
            )
        
        return data
    
    def create(self, validated_data):
        images = validated_data.pop('images', [])
        image_captions = validated_data.pop('image_captions', [])
        
        review = ListingReview.objects.create(**validated_data)
        
        # Create review images
        for i, image in enumerate(images):
            caption = image_captions[i] if i < len(image_captions) else ''
            ReviewImage.objects.create(
                listing_review=review,
                image=image,
                caption=caption
            )
        
        return review
    
    def update(self, instance, validated_data):
        images = validated_data.pop('images', [])
        image_captions = validated_data.pop('image_captions', [])
        
        # Update review fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Handle new images (existing images are not replaced)
        for i, image in enumerate(images):
            caption = image_captions[i] if i < len(image_captions) else ''
            ReviewImage.objects.create(
                listing_review=instance,
                image=image,
                caption=caption
            )
        
        return instance