from django_filters import rest_framework as filters
from django.db import models
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.db.models import Q, F, Case, When, IntegerField
from .models import VehicleListing, ListingStatus, ConditionType


class VehicleListingFilter(filters.FilterSet):
    """PostgreSQL-optimized filter for vehicle listings."""
    
    # Price range filters with PostgreSQL optimization
    min_price = filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='price', lookup_expr='lte')
    price_range = filters.CharFilter(method='filter_price_range')
    
    # Kilometers range filters
    min_kilometers = filters.NumberFilter(field_name='kilometers', lookup_expr='gte')
    max_kilometers = filters.NumberFilter(field_name='kilometers', lookup_expr='lte')
    kilometers_range = filters.CharFilter(method='filter_kilometers_range')
    
    # Year range filters
    min_year = filters.NumberFilter(field_name='year', lookup_expr='gte')
    max_year = filters.NumberFilter(field_name='year', lookup_expr='lte')
    year_range = filters.CharFilter(method='filter_year_range')
    
    # Vehicle filters with exact matching for better performance
    make = filters.CharFilter(field_name='make', lookup_expr='iexact')
    make_contains = filters.CharFilter(field_name='make', lookup_expr='icontains')
    model = filters.CharFilter(field_name='model', lookup_expr='iexact')
    model_contains = filters.CharFilter(field_name='model', lookup_expr='icontains')
    
    # Multiple selection filters
    makes = filters.CharFilter(method='filter_makes')
    models = filters.CharFilter(method='filter_models')
    fuel_types = filters.CharFilter(method='filter_fuel_types')
    transmissions = filters.CharFilter(method='filter_transmissions')
    conditions = filters.CharFilter(method='filter_conditions')
    body_types = filters.CharFilter(method='filter_body_types')
    cities = filters.CharFilter(method='filter_cities')
    
    # Single choice filters
    fuel_type = filters.ChoiceFilter(choices=[
        ('gasoline', 'Gasoline'),
        ('diesel', 'Diesel'),
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid'),
        ('plug_in_hybrid', 'Plug-in Hybrid'),
        ('lpg', 'LPG'),
        ('cng', 'CNG'),
    ])
    transmission = filters.ChoiceFilter(choices=[
        ('manual', 'Manual'),
        ('automatic', 'Automatic'),
        ('cvt', 'CVT'),
        ('semi_automatic', 'Semi-Automatic'),
    ])
    
    # Engine size range filters
    min_engine_size = filters.NumberFilter(field_name='engine_size', lookup_expr='gte')
    max_engine_size = filters.NumberFilter(field_name='engine_size', lookup_expr='lte')
    
    # Doors and seats filters
    doors = filters.NumberFilter(field_name='doors')
    seating_capacity = filters.NumberFilter(field_name='seating_capacity')
    
    # Location filters
    city = filters.CharFilter(field_name='location_city', lookup_expr='iexact')
    country = filters.CharFilter(field_name='location_country', lookup_expr='iexact')
    
    # Color filter
    exterior_color = filters.CharFilter(field_name='exterior_color', lookup_expr='icontains')
    
    # Listing status filters
    is_featured = filters.BooleanFilter(field_name='is_featured')
    is_premium = filters.BooleanFilter(field_name='is_premium')
    
    # PostgreSQL full-text search
    search = filters.CharFilter(method='filter_search')
    
    # Sorting options
    ordering = filters.OrderingFilter(
        fields=(
            ('created_at', 'created_at'),
            ('price', 'price'),
            ('year', 'year'),
            ('kilometers', 'kilometers'),
            ('views_count', 'views_count'),
            ('published_at', 'published_at'),
        ),
        field_labels={
            'created_at': 'Date Created',
            'price': 'Price',
            'year': 'Year',
            'kilometers': 'Kilometers',
            'views_count': 'Popularity',
            'published_at': 'Date Published',
        }
    )
    
    def filter_search(self, queryset, name, value):
        """PostgreSQL full-text search with ranking."""
        if not value:
            return queryset
            
        # Create search vector for multiple fields
        search_vector = SearchVector('title', weight='A') + \
                       SearchVector('description', weight='B') + \
                       SearchVector('make', weight='A') + \
                       SearchVector('model', weight='A') + \
                       SearchVector('location_city', weight='C') + \
                       SearchVector('exterior_color', weight='D')
        
        search_query = SearchQuery(value)
        
        return queryset.annotate(
            search=search_vector,
            rank=SearchRank(search_vector, search_query)
        ).filter(search=search_query).order_by('-rank', '-created_at')
    
    def filter_price_range(self, queryset, name, value):
        """Filter by predefined price ranges."""
        ranges = {
            'under_10k': Q(price__lt=10000),
            '10k_25k': Q(price__gte=10000, price__lt=25000),
            '25k_50k': Q(price__gte=25000, price__lt=50000),
            '50k_100k': Q(price__gte=50000, price__lt=100000),
            'over_100k': Q(price__gte=100000),
        }
        return queryset.filter(ranges.get(value, Q())) if value in ranges else queryset
    
    def filter_kilometers_range(self, queryset, name, value):
        """Filter by predefined kilometers ranges."""
        ranges = {
            'under_50k': Q(kilometers__lt=50000),
            '50k_100k': Q(kilometers__gte=50000, kilometers__lt=100000),
            '100k_150k': Q(kilometers__gte=100000, kilometers__lt=150000),
            'over_150k': Q(kilometers__gte=150000),
        }
        return queryset.filter(ranges.get(value, Q())) if value in ranges else queryset
    
    def filter_year_range(self, queryset, name, value):
        """Filter by predefined year ranges."""
        ranges = {
            'last_year': Q(year__gte=2023),
            'last_3_years': Q(year__gte=2021),
            'last_5_years': Q(year__gte=2019),
            'last_10_years': Q(year__gte=2014),
            'older': Q(year__lt=2014),
        }
        return queryset.filter(ranges.get(value, Q())) if value in ranges else queryset
    
    def filter_makes(self, queryset, name, value):
        """Filter by multiple makes."""
        if not value:
            return queryset
        makes_list = [make.strip() for make in value.split(',')]
        return queryset.filter(make__in=makes_list)
    
    def filter_models(self, queryset, name, value):
        """Filter by multiple models."""
        if not value:
            return queryset
        models_list = [model.strip() for model in value.split(',')]
        return queryset.filter(model__in=models_list)
    
    def filter_fuel_types(self, queryset, name, value):
        """Filter by multiple fuel types."""
        if not value:
            return queryset
        fuel_types_list = [ft.strip() for ft in value.split(',')]
        return queryset.filter(fuel_type__in=fuel_types_list)
    
    def filter_transmissions(self, queryset, name, value):
        """Filter by multiple transmissions."""
        if not value:
            return queryset
        transmissions_list = [t.strip() for t in value.split(',')]
        return queryset.filter(transmission__in=transmissions_list)
    
    def filter_conditions(self, queryset, name, value):
        """Filter by multiple conditions."""
        if not value:
            return queryset
        conditions_list = [c.strip() for c in value.split(',')]
        return queryset.filter(condition__in=conditions_list)
    
    def filter_body_types(self, queryset, name, value):
        """Filter by multiple body types."""
        if not value:
            return queryset
        body_types_list = [bt.strip() for bt in value.split(',')]
        return queryset.filter(body_type__in=body_types_list)
    
    def filter_cities(self, queryset, name, value):
        """Filter by multiple cities."""
        if not value:
            return queryset
        cities_list = [city.strip() for city in value.split(',')]
        return queryset.filter(location_city__in=cities_list)
    
    class Meta:
        model = VehicleListing
        fields = [
            'condition', 'status', 'user', 'year', 'make', 'model',
            'fuel_type', 'transmission', 'exterior_color', 'doors', 'seating_capacity',
            'city', 'country', 'is_featured', 'is_premium'
        ]