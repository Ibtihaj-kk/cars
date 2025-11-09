"""
Comprehensive API views for vehicle listings.
"""
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Avg, Max, Min
from django.core.paginator import Paginator
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import generics, status, filters, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters
from django.core.cache import cache
from django.db.models import Prefetch

# Import activity logging utilities
from admin_panel.utils import log_listing_activity, log_status_change_activity
from admin_panel.models import ActivityLogType

from .models import VehicleListing, ListingImage, ListingVideo, SavedListing, ListingView, ListingStatusLog
from inquiries.models import ListingInquiry
from vehicles.models import VehicleCategory
from .serializers import (
    VehicleListingListSerializer, VehicleListingDetailSerializer,
    VehicleListingCreateUpdateSerializer, SavedListingSerializer,
    ListingViewSerializer, VehicleListingStatusSerializer,
    VehicleListingStatsSerializer, ListingImageSerializer,
    ListingVideoSerializer
)
from .status_manager import ListingStatusManager
from .security import (
    RateLimitMixin, APISecurityMixin, CacheControlMixin,
    rate_limit, admin_required, get_rate_limit
)
from .filters import VehicleListingFilter as OptimizedVehicleListingFilter

User = get_user_model()


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for listings."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class VehicleListingFilter(django_filters.FilterSet):
    """Advanced filtering for vehicle listings."""
    
    # Price filters
    price_min = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    
    # Year filters
    year_min = django_filters.NumberFilter(field_name='year', lookup_expr='gte')
    year_max = django_filters.NumberFilter(field_name='year', lookup_expr='lte')
    
    # Kilometers filters
    kilometers_min = django_filters.NumberFilter(field_name='kilometers', lookup_expr='gte')
    kilometers_max = django_filters.NumberFilter(field_name='kilometers', lookup_expr='lte')
    
    # Location filters
    city = django_filters.CharFilter(field_name='location_city', lookup_expr='icontains')
    state = django_filters.CharFilter(field_name='location_state', lookup_expr='icontains')
    country = django_filters.CharFilter(field_name='location_country', lookup_expr='icontains')
    
    # Multiple choice filters
    make = django_filters.CharFilter(field_name='make', lookup_expr='iexact')
    model = django_filters.CharFilter(field_name='model', lookup_expr='icontains')
    fuel_type = django_filters.MultipleChoiceFilter(choices=[
        ('gasoline', 'Gasoline'),
        ('diesel', 'Diesel'),
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid'),
        ('plug_in_hybrid', 'Plug-in Hybrid'),
        ('lpg', 'LPG'),
        ('cng', 'CNG'),
    ])
    transmission = django_filters.MultipleChoiceFilter(choices=[
        ('automatic', 'Automatic'),
        ('manual', 'Manual'),
        ('cvt', 'CVT'),
        ('semi_automatic', 'Semi-Automatic'),
    ])
    condition = django_filters.MultipleChoiceFilter(choices=[
        ('new', 'New'),
        ('used', 'Used'),
        ('certified_pre_owned', 'Certified Pre-Owned'),
    ])
    exterior_color = django_filters.CharFilter(field_name='exterior_color', lookup_expr='icontains')
    body_type = django_filters.ModelChoiceFilter(
        field_name='body_type',
        queryset=None,  # Will be set in __init__
        empty_label="All Body Types"
    )
    
    # Boolean filters
    is_featured = django_filters.BooleanFilter()
    is_premium = django_filters.BooleanFilter()
    
    # Date filters
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    # Search filter
    search = django_filters.CharFilter(method='filter_search')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters['body_type'].queryset = VehicleCategory.objects.filter(is_active=True)
    
    class Meta:
        model = VehicleListing
        fields = []
    
    def filter_search(self, queryset, name, value):
        """Full-text search across multiple fields."""
        if not value:
            return queryset
        
        return queryset.filter(
            Q(title__icontains=value) |
            Q(description__icontains=value) |
            Q(make__icontains=value) |
            Q(model__icontains=value) |
            Q(additional_features__icontains=value) |
            Q(location_city__icontains=value) |
            Q(location_state__icontains=value)
        )


class VehicleListingListView(RateLimitMixin, APISecurityMixin, CacheControlMixin, generics.ListAPIView):
    """List all published vehicle listings with PostgreSQL-optimized filtering and pagination."""
    serializer_class = VehicleListingListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = OptimizedVehicleListingFilter
    ordering_fields = ['price', 'year', 'kilometers', 'created_at', 'views_count', 'published_at']
    ordering = ['-created_at']
    cache_timeout = 300  # 5 minutes for list views
    
    def get_queryset(self):
        """Get published listings with PostgreSQL-optimized queries."""
        # Use cache for frequently accessed data
        cache_key = 'published_listings_base_queryset'
        queryset = cache.get(cache_key)
        
        if queryset is None:
            queryset = VehicleListing.objects.filter(
                status='published'
            ).select_related(
                'user',
                'dealer'
            ).prefetch_related(
                Prefetch(
                    'images',
                    queryset=ListingImage.objects.filter(is_primary=True).order_by('order')[:1],
                    to_attr='primary_images'
                ),
                Prefetch(
                    'images',
                    queryset=ListingImage.objects.order_by('order')[:5],
                    to_attr='preview_images'
                )
            ).only(
                # Only fetch necessary fields for list view
                'id', 'slug', 'title', 'price', 'year', 'make', 'model',
                'kilometers', 'fuel_type', 'transmission', 'condition',
                'location_city', 'location_country', 'is_featured', 'is_premium',
                'created_at', 'published_at', 'views_count', 'user__email',
                'dealer__name', 'exterior_color', 'body_type'
            )
            
            # Cache for 5 minutes
            cache.set(cache_key, queryset, 300)
        
        return queryset


class VehicleListingDetailView(generics.RetrieveAPIView):
    """Retrieve detailed information about a specific listing."""
    serializer_class = VehicleListingDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'
    
    def get_queryset(self):
        """Get published listings with all related data."""
        return VehicleListing.objects.filter(
            status='published'
        ).select_related('user').prefetch_related(
            'images', 'videos', 'status_logs__changed_by'
        )
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve listing and record view."""
        instance = self.get_object()
        
        # Record view if not the owner
        if not request.user.is_authenticated or request.user != instance.user:
            self._record_view(request, instance)
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def _record_view(self, request, listing):
        """Record a view for analytics."""
        # Get IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        
        # Get user agent
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Create view record
        ListingView.objects.create(
            listing=listing,
            user=request.user if request.user.is_authenticated else None,
            ip_address=ip_address,
            user_agent=user_agent
        )


class VehicleListingCreateView(generics.CreateAPIView):
    """Create a new vehicle listing."""
    serializer_class = VehicleListingCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @rate_limit(rate='10/h', methods=['POST'])
    def perform_create(self, serializer):
        """Set user and initial status."""
        listing = serializer.save(user=self.request.user, status='draft')
        
        # Log the listing creation
        log_listing_activity(
            user=self.request.user,
            action_type=ActivityLogType.CREATE,
            listing=listing,
            description=f'Created new listing: {listing.title}',
            request=self.request
        )


class VehicleListingUpdateView(generics.UpdateAPIView):
    """Update an existing vehicle listing."""
    serializer_class = VehicleListingCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'slug'
    
    def get_queryset(self):
        """Only allow users to update their own listings."""
        return VehicleListing.objects.filter(user=self.request.user)
    
    def perform_update(self, serializer):
        """Update listing with logging."""
        listing = serializer.save()
        
        # Log the listing update
        log_listing_activity(
            user=self.request.user,
            action_type=ActivityLogType.UPDATE,
            listing=listing,
            description=f'Updated listing: {listing.title}',
            request=self.request
        )


class VehicleListingDeleteView(generics.DestroyAPIView):
    """Delete a vehicle listing."""
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'slug'
    
    def get_queryset(self):
        """Only allow users to delete their own listings."""
        return VehicleListing.objects.filter(user=self.request.user)
    
    def perform_destroy(self, instance):
        """Delete listing with logging."""
        # Log the listing deletion before deleting
        log_listing_activity(
            user=self.request.user,
            action_type=ActivityLogType.DELETE,
            listing=instance,
            description=f'Deleted listing: {instance.title}',
            request=self.request
        )
        
        # Perform the actual deletion
        instance.delete()


class MyListingsView(generics.ListAPIView):
    """
    List current user's listings.
    
    This endpoint returns listings belonging exclusively to the currently logged-in dealer.
    Supports filtering, ordering, and pagination.
    """
    serializer_class = VehicleListingListSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = VehicleListingFilter
    ordering_fields = ['created_at', 'updated_at', 'status', 'price', 'year', 'kilometers', 'views_count']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Get user's listings with optimized queries.
        
        Returns:
            QuerySet: VehicleListing objects filtered by owner=request.user
        """
        return VehicleListing.objects.filter(
            user=self.request.user
        ).select_related('user').prefetch_related('images', 'videos')


class VehicleListingStatusView(RateLimitMixin, APISecurityMixin, generics.UpdateAPIView):
    """Change listing status."""
    serializer_class = VehicleListingStatusSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'slug'
    
    def get_queryset(self):
        """Allow owners and staff to change status."""
        if self.request.user.is_staff:
            return VehicleListing.objects.all()
        return VehicleListing.objects.filter(user=self.request.user)
    
    @rate_limit(rate='20/h', methods=['POST', 'PUT', 'PATCH'])
    def update(self, request, *args, **kwargs):
        """Update listing status using workflow methods."""
        listing = self.get_object()
        serializer = self.get_serializer(data=request.data, context={'listing': listing})
        serializer.is_valid(raise_exception=True)
        
        new_status = serializer.validated_data['status']
        reason = serializer.validated_data.get('reason', '')
        
        try:
            # Store old status for logging
            old_status = listing.status
            
            # Use status manager for workflow validation
            status_manager = ListingStatusManager(listing)
            if status_manager.can_transition_to(new_status):
                # Use appropriate workflow method
                if new_status == 'published':
                    listing.publish(user=request.user, reason=reason)
                elif new_status == 'rejected':
                    listing.reject(user=request.user, reason=reason)
                elif new_status == 'sold':
                    listing.mark_as_sold(user=request.user)
                elif new_status == 'suspended':
                    listing.suspend(user=request.user, reason=reason)
                elif new_status == 'draft':
                    listing.make_draft(user=request.user, reason=reason)
                else:
                    listing.change_status(new_status, user=request.user, reason=reason)
                
                # Log comprehensive status change
                log_status_change_activity(
                    user=request.user,
                    listing=listing,
                    old_status=old_status,
                    new_status=new_status,
                    reason=reason,
                    request=request
                )
                
                # Log security event
                self.log_security_event(request, 'status_changed', {
                    'listing_id': listing.id,
                    'old_status': old_status,
                    'new_status': new_status,
                    'reason': reason
                })
                
                return Response({
                    'status': 'success',
                    'message': f'Listing status changed to {new_status}',
                    'new_status': listing.status
                })
            else:
                return Response({
                    'status': 'error',
                    'message': f'Cannot change status from {listing.status} to {new_status}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except ValueError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class SavedListingListView(generics.ListCreateAPIView):
    """List and create saved listings."""
    serializer_class = SavedListingSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        """Get user's saved listings."""
        return SavedListing.objects.filter(
            user=self.request.user
        ).select_related('listing__user').prefetch_related('listing__images')
    
    def perform_create(self, serializer):
        """Save listing for current user."""
        serializer.save(user=self.request.user)


class SavedListingDeleteView(generics.DestroyAPIView):
    """Remove a saved listing."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get user's saved listings."""
        return SavedListing.objects.filter(user=self.request.user)


class ListingImageListView(generics.ListCreateAPIView):
    """List and upload images for a listing."""
    serializer_class = ListingImageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get images for user's listing."""
        listing_slug = self.kwargs['listing_slug']
        listing = get_object_or_404(
            VehicleListing, 
            slug=listing_slug, 
            user=self.request.user
        )
        return ListingImage.objects.filter(listing=listing).order_by('order')
    
    def perform_create(self, serializer):
        """Create image for user's listing."""
        listing_slug = self.kwargs['listing_slug']
        listing = get_object_or_404(
            VehicleListing, 
            slug=listing_slug, 
            user=self.request.user
        )
        
        # Set order based on existing images
        max_order = ListingImage.objects.filter(listing=listing).aggregate(
            max_order=Max('order')
        )['max_order'] or -1
        
        serializer.save(listing=listing, order=max_order + 1)


class ListingImageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a listing image."""
    serializer_class = ListingImageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get images for user's listing."""
        listing_slug = self.kwargs['listing_slug']
        listing = get_object_or_404(
            VehicleListing, 
            slug=listing_slug, 
            user=self.request.user
        )
        return ListingImage.objects.filter(listing=listing)


class ListingVideoListView(generics.ListCreateAPIView):
    """List and upload videos for a listing."""
    serializer_class = ListingVideoSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get videos for user's listing."""
        listing_slug = self.kwargs['listing_slug']
        listing = get_object_or_404(
            VehicleListing, 
            slug=listing_slug, 
            user=self.request.user
        )
        return ListingVideo.objects.filter(listing=listing).order_by('order')
    
    def perform_create(self, serializer):
        """Create video for user's listing."""
        listing_slug = self.kwargs['listing_slug']
        listing = get_object_or_404(
            VehicleListing, 
            slug=listing_slug, 
            user=self.request.user
        )
        
        # Set order based on existing videos
        max_order = ListingVideo.objects.filter(listing=listing).aggregate(
            max_order=Max('order')
        )['max_order'] or -1
        
        serializer.save(listing=listing, order=max_order + 1)


class ListingVideoDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a listing video."""
    serializer_class = ListingVideoSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get videos for user's listing."""
        listing_slug = self.kwargs['listing_slug']
        listing = get_object_or_404(
            VehicleListing, 
            slug=listing_slug, 
            user=self.request.user
        )
        return ListingVideo.objects.filter(listing=listing)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def listing_stats_view(request):
    """Get listing statistics for current user."""
    user_listings = VehicleListing.objects.filter(user=request.user)
    
    stats = {
        'total_listings': user_listings.count(),
        'published_listings': user_listings.filter(status='published').count(),
        'draft_listings': user_listings.filter(status='draft').count(),
        'sold_listings': user_listings.filter(status='sold').count(),
        'total_views': ListingView.objects.filter(listing__user=request.user).count(),
        'total_inquiries': 0,  # Will be implemented with inquiries app
        'avg_price': user_listings.aggregate(avg_price=Avg('price'))['avg_price'] or 0,
        'popular_makes': list(
            user_listings.values('make').annotate(
                count=Count('make')
            ).order_by('-count')[:5]
        ),
        'recent_activity': list(
            user_listings.order_by('-updated_at')[:10].values(
                'title', 'status', 'updated_at'
            )
        )
    }
    
    serializer = VehicleListingStatsSerializer(stats)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def popular_makes_view(request):
    """Get popular vehicle makes."""
    popular_makes = VehicleListing.objects.filter(
        status='published'
    ).values('make').annotate(
        count=Count('make')
    ).order_by('-count')[:20]
    
    return Response(popular_makes)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def filter_data_view(request):
    """Get all filter data for listings with PostgreSQL optimization and caching."""
    # Check cache first
    cache_key = 'filter_data_optimized'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return Response(cached_data)
    
    # Get published listings for filter data with optimized query
    published_listings = VehicleListing.objects.filter(status='published').select_related(
        'make', 'model', 'fuel_type', 'transmission', 'body_type'
    )
    
    # Use PostgreSQL-optimized aggregations
    filter_data = {}
    
    # Get unique makes with counts (PostgreSQL optimized)
    makes_data = published_listings.values('make__name').annotate(
        count=Count('make__name')
    ).filter(make__name__isnull=False).exclude(make__name='').order_by('make__name')
    filter_data['makes'] = [
        {'value': item['make__name'], 'label': item['make__name'], 'count': item['count']}
        for item in makes_data
    ]
    
    # Get unique models with counts
    models_data = published_listings.values('model__name').annotate(
        count=Count('model__name')
    ).filter(model__name__isnull=False).exclude(model__name='').order_by('model__name')
    filter_data['models'] = [
        {'value': item['model__name'], 'label': item['model__name'], 'count': item['count']}
        for item in models_data
    ]
    
    # Get unique cities with counts
    cities_data = published_listings.values('location_city').annotate(
        count=Count('location_city')
    ).filter(location_city__isnull=False).exclude(location_city='').order_by('location_city')
    filter_data['cities'] = [
        {'value': item['location_city'], 'label': item['location_city'], 'count': item['count']}
        for item in cities_data
    ]
    
    # Get unique years with counts
    years_data = published_listings.values('year').annotate(
        count=Count('year')
    ).filter(year__isnull=False).order_by('-year')
    filter_data['years'] = [
        {'value': item['year'], 'label': str(item['year']), 'count': item['count']}
        for item in years_data
    ]
    
    # Get fuel types with counts
    fuel_types_data = published_listings.values('fuel_type__name').annotate(
        count=Count('fuel_type__name')
    ).filter(fuel_type__name__isnull=False).exclude(fuel_type__name='').order_by('fuel_type__name')
    filter_data['fuel_types'] = [
        {'value': item['fuel_type__name'], 'label': item['fuel_type__name'].replace('_', ' ').title(), 'count': item['count']}
        for item in fuel_types_data
    ]
    
    # Get transmissions with counts
    transmissions_data = published_listings.values('transmission__name').annotate(
        count=Count('transmission__name')
    ).filter(transmission__name__isnull=False).exclude(transmission__name='').order_by('transmission__name')
    filter_data['transmissions'] = [
        {'value': item['transmission__name'], 'label': item['transmission__name'].replace('_', ' ').title(), 'count': item['count']}
        for item in transmissions_data
    ]
    
    # Get conditions with counts
    conditions_data = published_listings.values('condition').annotate(
        count=Count('condition')
    ).filter(condition__isnull=False).exclude(condition='').order_by('condition')
    filter_data['conditions'] = [
        {'value': item['condition'], 'label': item['condition'].replace('_', ' ').title(), 'count': item['count']}
        for item in conditions_data
    ]
    
    # Get body types with counts
    body_types_data = published_listings.values('body_type__name').annotate(
        count=Count('body_type__name')
    ).filter(body_type__name__isnull=False).exclude(body_type__name='').order_by('body_type__name')
    filter_data['body_types'] = [
        {'value': item['body_type__name'], 'label': item['body_type__name'].replace('_', ' ').title(), 'count': item['count']}
        for item in body_types_data
    ]
    
    # Get exterior colors with counts
    colors_data = published_listings.values('exterior_color').annotate(
        count=Count('exterior_color')
    ).filter(exterior_color__isnull=False).exclude(exterior_color='').order_by('exterior_color')
    filter_data['exterior_colors'] = [
        {'value': item['exterior_color'], 'label': item['exterior_color'].title(), 'count': item['count']}
        for item in colors_data
    ]
    
    # Get price range and statistics
    price_stats = published_listings.aggregate(
        min_price=Min('price'),
        max_price=Max('price'),
        avg_price=Avg('price'),
        count=Count('price')
    )
    
    filter_data['price_range'] = {
        'min': int(price_stats['min_price'] or 0),
        'max': int(price_stats['max_price'] or 100000),
        'avg': int(price_stats['avg_price'] or 0),
        'count': price_stats['count']
    }
    
    # Get year range
    year_stats = published_listings.aggregate(
        min_year=Min('year'),
        max_year=Max('year')
    )
    
    filter_data['year_range'] = {
        'min': year_stats['min_year'] or 2000,
        'max': year_stats['max_year'] or timezone.now().year
    }
    
    # Predefined filter ranges for better UX
    filter_data['price_ranges'] = [
        {'value': 'under_10k', 'label': 'Under $10,000', 'min': 0, 'max': 9999},
        {'value': '10k_25k', 'label': '$10,000 - $25,000', 'min': 10000, 'max': 24999},
        {'value': '25k_50k', 'label': '$25,000 - $50,000', 'min': 25000, 'max': 49999},
        {'value': '50k_100k', 'label': '$50,000 - $100,000', 'min': 50000, 'max': 99999},
        {'value': 'over_100k', 'label': 'Over $100,000', 'min': 100000, 'max': None},
    ]
    
    filter_data['year_ranges'] = [
        {'value': 'last_year', 'label': 'Last Year', 'min': 2023, 'max': None},
        {'value': 'last_3_years', 'label': 'Last 3 Years', 'min': 2021, 'max': None},
        {'value': 'last_5_years', 'label': 'Last 5 Years', 'min': 2019, 'max': None},
        {'value': 'last_10_years', 'label': 'Last 10 Years', 'min': 2014, 'max': None},
        {'value': 'older', 'label': 'Older than 10 Years', 'min': None, 'max': 2013},
    ]
    
    filter_data['kilometers_ranges'] = [
        {'value': 'under_50k', 'label': 'Under 50,000 km', 'min': 0, 'max': 49999},
        {'value': '50k_100k', 'label': '50,000 - 100,000 km', 'min': 50000, 'max': 99999},
        {'value': '100k_150k', 'label': '100,000 - 150,000 km', 'min': 100000, 'max': 149999},
        {'value': 'over_150k', 'label': 'Over 150,000 km', 'min': 150000, 'max': None},
    ]
    
    # Cache for 10 minutes
    cache.set(cache_key, filter_data, 600)
    
    return Response(filter_data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def models_by_make_view(request):
    """Get vehicle models filtered by make."""
    make = request.GET.get('make')
    if not make:
        return Response({'error': 'Make parameter is required'}, status=400)
    
    models = VehicleListing.objects.filter(
        status='published',
        make__icontains=make
    ).values_list('model', flat=True).distinct().order_by('model')
    
    models = [model for model in models if model]
    
    return Response({'models': models})


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def advanced_search_view(request):
    """Advanced search API with comprehensive filtering."""
    # Get query parameters
    search_query = request.GET.get('search', '')
    make = request.GET.get('make', '')
    model = request.GET.get('model', '')
    body_type_id = request.GET.get('body_type')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    min_year = request.GET.get('min_year')
    max_year = request.GET.get('max_year')
    city = request.GET.get('city', '')
    fuel_type = request.GET.get('fuel_type', '')
    transmission = request.GET.get('transmission', '')
    condition = request.GET.get('condition', '')
    min_kilometers = request.GET.get('min_kilometers')
    max_kilometers = request.GET.get('max_kilometers')
    is_featured = request.GET.get('is_featured')
    sort_by = request.GET.get('sort_by', '-created_at')
    
    # Start with published listings
    queryset = VehicleListing.objects.filter(status='published')
    
    # Apply filters
    if search_query:
        queryset = queryset.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(make__name__icontains=search_query) |
            Q(model__name__icontains=search_query)
        )
    
    if make:
        queryset = queryset.filter(make__name__icontains=make)
    
    if model:
        queryset = queryset.filter(model__name__icontains=model)
    
    if body_type_id and body_type_id.strip():
        try:
            queryset = queryset.filter(body_type_id=int(body_type_id))
        except (ValueError, TypeError):
            pass  # Skip invalid body_type_id
    
    if min_price and min_price.strip():
        try:
            queryset = queryset.filter(price__gte=float(min_price))
        except (ValueError, TypeError):
            pass  # Skip invalid min_price
    
    if max_price and max_price.strip():
        try:
            queryset = queryset.filter(price__lte=float(max_price))
        except (ValueError, TypeError):
            pass  # Skip invalid max_price
    
    if min_year and min_year.strip():
        try:
            queryset = queryset.filter(year__gte=int(min_year))
        except (ValueError, TypeError):
            pass  # Skip invalid min_year
    
    if max_year and max_year.strip():
        try:
            queryset = queryset.filter(year__lte=int(max_year))
        except (ValueError, TypeError):
            pass  # Skip invalid max_year
    
    if city:
        queryset = queryset.filter(location_city__icontains=city)
    
    if fuel_type:
        queryset = queryset.filter(fuel_type__name__icontains=fuel_type)
    
    if transmission:
        queryset = queryset.filter(transmission__name__icontains=transmission)
    
    if condition:
        queryset = queryset.filter(condition__icontains=condition)
    
    if min_kilometers and min_kilometers.strip():
        try:
            queryset = queryset.filter(kilometers__gte=float(min_kilometers))
        except (ValueError, TypeError):
            pass  # Skip invalid min_kilometers
    
    if max_kilometers and max_kilometers.strip():
        try:
            queryset = queryset.filter(kilometers__lte=float(max_kilometers))
        except (ValueError, TypeError):
            pass  # Skip invalid max_kilometers
    
    if is_featured and is_featured.lower() == 'true':
        queryset = queryset.filter(is_featured=True)
    
    # Apply sorting
    valid_sort_fields = [
        'price', '-price', 'year', '-year', 'kilometers', '-kilometers',
        'created_at', '-created_at', 'views_count', '-views_count'
    ]
    if sort_by in valid_sort_fields:
        queryset = queryset.order_by(sort_by)
    else:
        queryset = queryset.order_by('-created_at')
    
    # Optimize query
    queryset = queryset.select_related('user', 'body_type', 'make', 'model', 'fuel_type', 'transmission').prefetch_related('images')
    
    # Apply pagination
    paginator = Paginator(queryset, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Serialize data
    serializer = VehicleListingListSerializer(page_obj, many=True)
    
    return Response({
        'results': serializer.data,
        'count': paginator.count,
        'num_pages': paginator.num_pages,
        'current_page': page_obj.number,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'page_size': 12
    })


class FeaturedListingsView(RateLimitMixin, APISecurityMixin, CacheControlMixin, generics.ListAPIView):
    """Get featured listings with pagination."""
    serializer_class = VehicleListingListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = VehicleListingFilter
    ordering_fields = ['price', 'year', 'kilometers', 'created_at', 'views_count']
    ordering = ['-created_at']
    cache_timeout = 300  # 5 minutes for list views
    
    def get_queryset(self):
        """Return featured listings."""
        return VehicleListing.objects.filter(
            status='published',
            is_featured=True
        ).select_related('user').prefetch_related('images')


class RecentListingsView(RateLimitMixin, APISecurityMixin, CacheControlMixin, generics.ListAPIView):
    """Get recently added listings with pagination."""
    serializer_class = VehicleListingListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = VehicleListingFilter
    ordering_fields = ['price', 'year', 'kilometers', 'created_at', 'views_count']
    ordering = ['-created_at']
    cache_timeout = 300  # 5 minutes for list views
    
    def get_queryset(self):
        """Return recently added listings."""
        return VehicleListing.objects.filter(
            status='published'
        ).select_related('user').prefetch_related('images')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def bulk_status_change_view(request):
    """Bulk change status for multiple listings."""
    listing_ids = request.data.get('listing_ids', [])
    new_status = request.data.get('status')
    reason = request.data.get('reason', '')
    
    if not listing_ids or not new_status:
        return Response({
            'error': 'listing_ids and status are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Get user's listings or all if staff
    if request.user.is_staff:
        listings = VehicleListing.objects.filter(id__in=listing_ids)
    else:
        listings = VehicleListing.objects.filter(
            id__in=listing_ids, 
            user=request.user
        )
    
    results = []
    for listing in listings:
        try:
            if new_status == 'published':
                listing.publish(user=request.user)
            elif new_status == 'rejected':
                listing.reject(user=request.user, reason=reason)
            elif new_status == 'sold':
                listing.mark_as_sold(user=request.user)
            elif new_status == 'suspended':
                listing.suspend(user=request.user, reason=reason)
            else:
                listing.change_status(new_status, user=request.user, reason=reason)
            
            results.append({
                'id': listing.id,
                'title': listing.title,
                'status': 'success',
                'new_status': listing.status
            })
        except ValueError as e:
            results.append({
                'id': listing.id,
                'title': listing.title,
                'status': 'error',
                'error': str(e)
            })
    
    return Response({
        'message': f'Processed {len(results)} listings',
        'results': results
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def live_search_view(request):
    """
    Live search endpoint for real-time search suggestions.
    
    Returns quick search results with minimal data for fast response times.
    Optimized for live search with debouncing on the frontend.
    """
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 2:
        return Response({
            'suggestions': [],
            'count': 0
        })
    
    # Limit results for performance
    limit = min(int(request.GET.get('limit', 8)), 20)
    
    try:
        # Use optimized query with select_related for better performance
        listings = VehicleListing.objects.filter(
            Q(title__icontains=query) |
            Q(make__name__icontains=query) |
            Q(model__name__icontains=query) |
            Q(location_city__icontains=query),
            status='published'
        ).select_related('make', 'model').only(
            'id', 'slug', 'title', 'price', 'year', 'location_city',
            'make__name', 'model__name'
        )[:limit]
        
        suggestions = []
        for listing in listings:
            suggestions.append({
                'id': listing.id,
                'slug': listing.slug,
                'title': listing.title,
                'make': listing.make.name if listing.make else '',
                'model': listing.model.name if listing.model else '',
                'year': listing.year,
                'price': listing.price,
                'location': listing.location_city,
                'url': f'/car/{listing.slug}/'
            })
        
        return Response({
            'suggestions': suggestions,
            'count': len(suggestions),
            'query': query
        })
        
    except Exception as e:
        return Response({
            'suggestions': [],
            'count': 0,
            'error': 'Search temporarily unavailable'
        }, status=500)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_summary_view(request):
    """
    Dashboard summary endpoint for dealers.
    
    Returns aggregated data about the dealer's listings, inquiries, and saved listings.
    Optimized with database-level aggregations and prefetch-related queries.
    """
    user = request.user
    
    # Get dealer's active listings count
    total_listings = VehicleListing.objects.filter(
        user=user,
        status__in=['published', 'pending_review', 'draft']
    ).count()
    
    # Get total inquiries on dealer's listings using optimized query
    total_inquiries = ListingInquiry.objects.filter(
        listing__user=user
    ).count()
    
    # Get total saved listings (how many users saved this dealer's listings)
    total_saved_listings = SavedListing.objects.filter(
        listing__user=user
    ).count()
    
    return Response({
        'total_listings': total_listings,
        'total_inquiries': total_inquiries,
        'total_saved_listings': total_saved_listings
    })
