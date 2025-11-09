"""
Cache utilities for the Parts module.
Provides caching functions for common queries to improve performance.
"""

from django.core.cache import cache
from django.conf import settings
from django.db.models import Count, Avg, Q
from django.utils.encoding import force_str
import hashlib
import json


def make_cache_key(*args, **kwargs):
    """
    Generate a cache key from arguments.
    """
    key_parts = []
    for arg in args:
        key_parts.append(force_str(arg))
    
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}:{force_str(v)}")
    
    key_string = ":".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def get_cached_categories():
    """
    Get cached list of all active categories with part counts.
    """
    cache_key = "parts:categories:all"
    cached_data = cache.get(cache_key)
    
    if cached_data is None:
        from .models import Category, Part
        
        categories = Category.objects.annotate(
            part_count=Count('parts', filter=Q(parts__is_active=True))
        ).order_by('name')
        
        cached_data = [
            {
                'id': cat.id,
                'name': cat.name,
                'slug': cat.slug,
                'part_count': cat.part_count
            }
            for cat in categories
        ]
        
        cache.set(cache_key, cached_data, getattr(settings, 'CACHE_TIMEOUTS', {}).get('CATEGORIES', 3600))
    
    return cached_data


def get_cached_brands():
    """
    Get cached list of all active brands with part counts.
    """
    cache_key = "parts:brands:active"
    cached_data = cache.get(cache_key)
    
    if cached_data is None:
        from .models import Brand, Part
        
        brands = Brand.objects.filter(is_active=True).annotate(
            part_count=Count('parts', filter=Q(parts__is_active=True))
        ).order_by('name')
        
        cached_data = [
            {
                'id': brand.id,
                'name': brand.name,
                'part_count': brand.part_count
            }
            for brand in brands
        ]
        
        cache.set(cache_key, cached_data, getattr(settings, 'CACHE_TIMEOUTS', {}).get('BRANDS', 3600))
    
    return cached_data


def get_cached_popular_parts(limit=10):
    """
    Get cached list of popular parts based on view count and sales.
    """
    cache_key = f"parts:popular:{limit}"
    cached_data = cache.get(cache_key)
    
    if cached_data is None:
        from .models import Part
        
        popular_parts = Part.objects.filter(is_active=True).select_related(
            'category', 'brand', 'dealer'
        ).annotate(
            total_orders=Count('order_items'),
            avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True))
        ).order_by('-view_count', '-total_orders')[:limit]
        
        cached_data = [
            {
                'id': part.id,
                'name': part.name,
                'slug': part.slug,
                'price': float(part.price),
                'image_url': part.image.url if part.image else part.image_url,
                'category': part.category.name,
                'brand': part.brand.name,
                'view_count': part.view_count,
                'avg_rating': float(part.avg_rating) if part.avg_rating else 0,
                'total_orders': part.total_orders
            }
            for part in popular_parts
        ]
        
        cache.set(cache_key, cached_data, getattr(settings, 'CACHE_TIMEOUTS', {}).get('POPULAR_PARTS', 1800))
    
    return cached_data


def get_cached_featured_parts(limit=8):
    """
    Get cached list of featured parts.
    """
    cache_key = f"parts:featured:{limit}"
    cached_data = cache.get(cache_key)
    
    if cached_data is None:
        from .models import Part
        
        featured_parts = Part.objects.filter(
            is_active=True, 
            is_featured=True
        ).select_related(
            'category', 'brand', 'dealer'
        ).annotate(
            avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True))
        ).order_by('-created_at')[:limit]
        
        cached_data = [
            {
                'id': part.id,
                'name': part.name,
                'slug': part.slug,
                'price': float(part.price),
                'image_url': part.image.url if part.image else part.image_url,
                'category': part.category.name,
                'brand': part.brand.name,
                'avg_rating': float(part.avg_rating) if part.avg_rating else 0,
                'is_featured': part.is_featured
            }
            for part in featured_parts
        ]
        
        cache.set(cache_key, cached_data, getattr(settings, 'CACHE_TIMEOUTS', {}).get('POPULAR_PARTS', 1800))
    
    return cached_data


def get_cached_part_detail(part_id):
    """
    Get cached part detail with related data.
    """
    cache_key = f"parts:detail:{part_id}"
    cached_data = cache.get(cache_key)
    
    if cached_data is None:
        from .models import Part
        
        try:
            part = Part.objects.select_related(
                'category', 'brand', 'dealer', 'inventory'
            ).prefetch_related(
                'reviews__user'
            ).annotate(
                avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True)),
                annotated_review_count=Count('reviews', filter=Q(reviews__is_approved=True))
            ).get(id=part_id, is_active=True)
            
            cached_data = {
                'id': part.id,
                'name': part.name,
                'slug': part.slug,
                'description': part.description,
                'sku': part.sku,
                'price': float(part.price),
                'quantity': part.quantity,
                'image_url': part.image.url if part.image else part.image_url,
                'weight': float(part.weight) if part.weight else None,
                'dimensions': part.dimensions,
                'warranty_period': part.warranty_period,
                'category': {
                    'id': part.category.id,
                    'name': part.category.name,
                    'slug': part.category.slug
                },
                'brand': {
                    'id': part.brand.id,
                    'name': part.brand.name
                },
                'dealer': {
                    'id': part.dealer.id if part.dealer else None,
                    'name': f"{part.dealer.first_name} {part.dealer.last_name}" if part.dealer else "Cars Portal"
                },
                'avg_rating': float(part.avg_rating) if part.avg_rating else 0,
                'review_count': part.review_count,
                'view_count': part.view_count,
                'is_in_stock': part.quantity > 0,
                'stock_level': part.inventory.stock if hasattr(part, 'inventory') and part.inventory else part.quantity
            }
            
            cache.set(cache_key, cached_data, getattr(settings, 'CACHE_TIMEOUTS', {}).get('PART_DETAIL', 600))
            
        except Part.DoesNotExist:
            cached_data = None
    
    return cached_data


def get_cached_search_results(query, filters=None, limit=50):
    """
    Get cached search results for parts.
    """
    filters = filters or {}
    cache_key = make_cache_key("parts:search", query=query, limit=limit, **filters)
    cached_data = cache.get(cache_key)
    
    if cached_data is None:
        from .models import Part
        
        queryset = Part.objects.filter(is_active=True).select_related(
            'category', 'brand', 'dealer'
        ).annotate(
            avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True))
        )
        
        # Apply search query
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(sku__icontains=query) |
                Q(brand__name__icontains=query)
            )
        
        # Apply filters
        if filters.get('category_id'):
            queryset = queryset.filter(category_id=filters['category_id'])
        
        if filters.get('brand_id'):
            queryset = queryset.filter(brand_id=filters['brand_id'])
        
        if filters.get('min_price'):
            queryset = queryset.filter(price__gte=filters['min_price'])
        
        if filters.get('max_price'):
            queryset = queryset.filter(price__lte=filters['max_price'])
        
        if filters.get('in_stock'):
            queryset = queryset.filter(quantity__gt=0)
        
        # Limit results
        parts = queryset.order_by('-view_count', '-created_at')[:limit]
        
        cached_data = [
            {
                'id': part.id,
                'name': part.name,
                'slug': part.slug,
                'price': float(part.price),
                'image_url': part.image.url if part.image else part.image_url,
                'category': part.category.name,
                'brand': part.brand.name,
                'avg_rating': float(part.avg_rating) if part.avg_rating else 0,
                'quantity': part.quantity
            }
            for part in parts
        ]
        
        cache.set(cache_key, cached_data, getattr(settings, 'CACHE_TIMEOUTS', {}).get('SEARCH_RESULTS', 300))
    
    return cached_data


def invalidate_part_cache(part_id):
    """
    Invalidate cache for a specific part and related caches.
    """
    # Invalidate part detail cache
    cache.delete(f"parts:detail:{part_id}")
    
    # Invalidate list caches that might include this part
    cache.delete_many([
        "parts:popular:10",
        "parts:featured:8",
        "parts:categories:all",
        "parts:brands:active"
    ])
    
    # Clear search result caches (pattern-based deletion would be ideal but not supported by all backends)
    # In production, consider using cache versioning or tags for more efficient invalidation


def invalidate_category_cache():
    """
    Invalidate category-related caches.
    """
    cache.delete("parts:categories:all")


def invalidate_brand_cache():
    """
    Invalidate brand-related caches.
    """
    cache.delete("parts:brands:active")


def warm_cache():
    """
    Warm up the cache with commonly accessed data.
    """
    # Pre-load categories and brands
    get_cached_categories()
    get_cached_brands()
    get_cached_popular_parts()
    get_cached_featured_parts()