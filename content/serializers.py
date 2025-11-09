from rest_framework import serializers
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import (
    ContentCategory, 
    Tag, 
    Article, 
    Page, 
    MediaGallery, 
    MediaItem, 
    Banner
)
from vehicles.serializers import BrandSerializer, VehicleModelListSerializer

User = get_user_model()


class UserBriefSerializer(serializers.ModelSerializer):
    """Brief serializer for user information."""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']


class TagSerializer(serializers.ModelSerializer):
    """Serializer for content tags."""
    
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']
        read_only_fields = ['slug']


class ContentCategorySerializer(serializers.ModelSerializer):
    """Serializer for content categories."""
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    
    class Meta:
        model = ContentCategory
        fields = [
            'id', 'name', 'slug', 'description', 'parent', 'parent_name',
            'order', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at']


class ContentCategoryNestedSerializer(serializers.ModelSerializer):
    """Simplified serializer for nested content categories."""
    
    class Meta:
        model = ContentCategory
        fields = ['id', 'name', 'slug']


class ArticleListSerializer(serializers.ModelSerializer):
    """Serializer for listing articles."""
    author_name = serializers.SerializerMethodField()
    categories = ContentCategoryNestedSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Article
        fields = [
            'id', 'title', 'slug', 'subtitle', 'excerpt', 'author', 'author_name',
            'featured_image', 'categories', 'tags', 'status', 'status_display',
            'is_featured', 'views_count', 'created_at', 'published_at'
        ]
        read_only_fields = ['slug', 'views_count', 'created_at', 'published_at']
    
    def get_author_name(self, obj):
        return f"{obj.author.first_name} {obj.author.last_name}".strip() or obj.author.username


class ArticleDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed article information."""
    author = UserBriefSerializer(read_only=True)
    categories = ContentCategoryNestedSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    related_brands = BrandSerializer(many=True, read_only=True)
    related_vehicle_models = VehicleModelListSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Article
        fields = [
            'id', 'title', 'slug', 'subtitle', 'content', 'excerpt', 'author',
            'featured_image', 'categories', 'tags', 'status', 'status_display',
            'meta_title', 'meta_description', 'meta_keywords',
            'related_brands', 'related_vehicle_models',
            'is_featured', 'views_count', 'created_at', 'updated_at',
            'published_at', 'scheduled_at'
        ]
        read_only_fields = ['slug', 'views_count', 'created_at', 'updated_at', 'published_at']


class ArticleCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating articles."""
    
    class Meta:
        model = Article
        fields = [
            'title', 'subtitle', 'content', 'excerpt', 'featured_image',
            'categories', 'tags', 'status', 'meta_title', 'meta_description',
            'meta_keywords', 'related_brands', 'related_vehicle_models',
            'is_featured', 'scheduled_at'
        ]
    
    def create(self, validated_data):
        # Set the author to the current user
        user = self.context['request'].user
        return Article.objects.create(author=user, **validated_data)


class PageSerializer(serializers.ModelSerializer):
    """Serializer for static pages."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    parent_title = serializers.CharField(source='parent.title', read_only=True)
    
    class Meta:
        model = Page
        fields = [
            'id', 'title', 'slug', 'content', 'featured_image', 'status', 'status_display',
            'meta_title', 'meta_description', 'meta_keywords',
            'order', 'show_in_menu', 'show_in_footer', 'parent', 'parent_title',
            'created_at', 'updated_at', 'published_at'
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at', 'published_at']


class MediaItemSerializer(serializers.ModelSerializer):
    """Serializer for media items."""
    media_type_display = serializers.CharField(source='get_media_type_display', read_only=True)
    
    class Meta:
        model = MediaItem
        fields = [
            'id', 'gallery', 'title', 'description', 'media_type', 'media_type_display',
            'file', 'thumbnail', 'order', 'created_at', 'video_url', 'duration'
        ]
        read_only_fields = ['created_at']


class MediaGalleryListSerializer(serializers.ModelSerializer):
    """Serializer for listing media galleries."""
    categories = ContentCategoryNestedSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = MediaGallery
        fields = [
            'id', 'title', 'slug', 'description', 'cover_image',
            'categories', 'tags', 'status', 'status_display',
            'created_at', 'published_at', 'item_count'
        ]
        read_only_fields = ['slug', 'created_at', 'published_at']
    
    def get_item_count(self, obj):
        return obj.items.count()


class MediaGalleryDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed media gallery information."""
    categories = ContentCategoryNestedSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    related_brands = BrandSerializer(many=True, read_only=True)
    related_vehicle_models = VehicleModelListSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    items = MediaItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = MediaGallery
        fields = [
            'id', 'title', 'slug', 'description', 'cover_image',
            'categories', 'tags', 'related_brands', 'related_vehicle_models',
            'status', 'status_display', 'created_at', 'updated_at',
            'published_at', 'items'
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at', 'published_at']


class MediaGalleryCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating media galleries."""
    
    class Meta:
        model = MediaGallery
        fields = [
            'title', 'description', 'cover_image', 'categories', 'tags',
            'related_brands', 'related_vehicle_models', 'status'
        ]


class BannerSerializer(serializers.ModelSerializer):
    """Serializer for promotional banners."""
    is_scheduled = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Banner
        fields = [
            'id', 'title', 'subtitle', 'image', 'mobile_image', 'link_url',
            'button_text', 'position', 'order', 'is_active', 'is_scheduled',
            'start_date', 'end_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']