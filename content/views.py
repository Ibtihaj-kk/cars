from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    ContentCategory, 
    Tag, 
    Article, 
    Page, 
    MediaGallery, 
    MediaItem, 
    Banner,
    ContentStatus
)
from .serializers import (
    ContentCategorySerializer,
    TagSerializer,
    ArticleListSerializer,
    ArticleDetailSerializer,
    ArticleCreateUpdateSerializer,
    PageSerializer,
    MediaGalleryListSerializer,
    MediaGalleryDetailSerializer,
    MediaGalleryCreateUpdateSerializer,
    MediaItemSerializer,
    BannerSerializer
)
from core.permissions import IsAdminUserOrReadOnly, IsAdminUser


class ContentCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for content categories."""
    queryset = ContentCategory.objects.all()
    serializer_class = ContentCategorySerializer
    permission_classes = [IsAdminUserOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'parent']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'order', 'created_at']
    ordering = ['order', 'name']
    lookup_field = 'slug'


class TagViewSet(viewsets.ModelViewSet):
    """ViewSet for content tags."""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAdminUserOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']
    lookup_field = 'slug'


class ArticleViewSet(viewsets.ModelViewSet):
    """ViewSet for articles."""
    queryset = Article.objects.all()
    permission_classes = [IsAdminUserOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'categories', 'tags', 'is_featured', 'author']
    search_fields = ['title', 'subtitle', 'content', 'excerpt']
    ordering_fields = ['title', 'created_at', 'published_at', 'views_count']
    ordering = ['-published_at']
    lookup_field = 'slug'

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # For non-admin users, only show published articles
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(status=ContentStatus.PUBLISHED) &
                (Q(published_at__isnull=True) | Q(published_at__lte=timezone.now()))
            )
        
        # Filter by related brands if provided
        brand_id = self.request.query_params.get('brand_id')
        if brand_id:
            queryset = queryset.filter(related_brands__id=brand_id)
        
        # Filter by related vehicle models if provided
        model_id = self.request.query_params.get('model_id')
        if model_id:
            queryset = queryset.filter(related_vehicle_models__id=model_id)
        
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return ArticleListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ArticleCreateUpdateSerializer
        return ArticleDetailSerializer

    @action(detail=True, methods=['post'])
    def increment_views(self, request, slug=None):
        """Increment the view count for an article."""
        article = self.get_object()
        article.views_count += 1
        article.save(update_fields=['views_count'])
        return Response({'status': 'view count incremented'})

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured articles."""
        queryset = self.get_queryset().filter(is_featured=True)
        serializer = ArticleListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent articles."""
        limit = int(request.query_params.get('limit', 5))
        queryset = self.get_queryset().order_by('-published_at')[:limit]
        serializer = ArticleListSerializer(queryset, many=True)
        return Response(serializer.data)


class PageViewSet(viewsets.ModelViewSet):
    """ViewSet for static pages."""
    queryset = Page.objects.all()
    serializer_class = PageSerializer
    permission_classes = [IsAdminUserOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'show_in_menu', 'show_in_footer', 'parent']
    search_fields = ['title', 'content']
    ordering_fields = ['title', 'order', 'created_at']
    ordering = ['order', 'title']
    lookup_field = 'slug'

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # For non-admin users, only show published pages
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(status=ContentStatus.PUBLISHED) &
                (Q(published_at__isnull=True) | Q(published_at__lte=timezone.now()))
            )
        
        return queryset

    @action(detail=False, methods=['get'])
    def menu_items(self, request):
        """Get pages that should appear in the main menu."""
        queryset = self.get_queryset().filter(show_in_menu=True).order_by('order')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def footer_items(self, request):
        """Get pages that should appear in the footer."""
        queryset = self.get_queryset().filter(show_in_footer=True).order_by('order')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class MediaGalleryViewSet(viewsets.ModelViewSet):
    """ViewSet for media galleries."""
    queryset = MediaGallery.objects.all()
    permission_classes = [IsAdminUserOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'categories', 'tags']
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'created_at', 'published_at']
    ordering = ['-published_at']
    lookup_field = 'slug'

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # For non-admin users, only show published galleries
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(status=ContentStatus.PUBLISHED) &
                (Q(published_at__isnull=True) | Q(published_at__lte=timezone.now()))
            )
        
        # Filter by related brands if provided
        brand_id = self.request.query_params.get('brand_id')
        if brand_id:
            queryset = queryset.filter(related_brands__id=brand_id)
        
        # Filter by related vehicle models if provided
        model_id = self.request.query_params.get('model_id')
        if model_id:
            queryset = queryset.filter(related_vehicle_models__id=model_id)
        
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return MediaGalleryListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return MediaGalleryCreateUpdateSerializer
        return MediaGalleryDetailSerializer


class MediaItemViewSet(viewsets.ModelViewSet):
    """ViewSet for media items."""
    queryset = MediaItem.objects.all()
    serializer_class = MediaItemSerializer
    permission_classes = [IsAdminUserOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['gallery', 'media_type']
    ordering_fields = ['order', 'created_at']
    ordering = ['order', 'created_at']

    @action(detail=False, methods=['get'])
    def by_gallery(self, request):
        """Get media items for a specific gallery."""
        gallery_slug = request.query_params.get('gallery_slug')
        if not gallery_slug:
            return Response(
                {'error': 'gallery_slug parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        gallery = get_object_or_404(MediaGallery, slug=gallery_slug)
        
        # Check if user can view this gallery
        if not request.user.is_staff and gallery.status != ContentStatus.PUBLISHED:
            return Response(
                {'error': 'Gallery not found or not published'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        queryset = self.get_queryset().filter(gallery=gallery)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class BannerViewSet(viewsets.ModelViewSet):
    """ViewSet for promotional banners."""
    queryset = Banner.objects.all()
    serializer_class = BannerSerializer
    permission_classes = [IsAdminUserOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['position', 'is_active']
    ordering_fields = ['position', 'order']
    ordering = ['position', 'order']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # For non-admin users, only show active banners within their scheduled dates
        if not self.request.user.is_staff:
            now = timezone.now()
            queryset = queryset.filter(
                is_active=True
            )
            queryset = queryset.filter(
                Q(start_date__isnull=True) | Q(start_date__lte=now)
            )
            queryset = queryset.filter(
                Q(end_date__isnull=True) | Q(end_date__gte=now)
            )
        
        # Filter by position if provided
        position = self.request.query_params.get('position')
        if position:
            queryset = queryset.filter(position=position)
        
        return queryset

    @action(detail=False, methods=['get'])
    def by_position(self, request):
        """Get banners for a specific position."""
        position = request.query_params.get('position')
        if not position:
            return Response(
                {'error': 'position parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(position=position)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
