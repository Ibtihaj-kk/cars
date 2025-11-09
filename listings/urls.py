"""
URL patterns for vehicle listings API.
"""
from django.urls import path
from . import views

app_name = 'listings'

urlpatterns = [
    # Public listing endpoints
    path('', views.VehicleListingListView.as_view(), name='listing-list'),
    
    # Public data endpoints (must come before slug patterns)
    path('popular-makes/', views.popular_makes_view, name='popular-makes'),
    path('featured/', views.FeaturedListingsView.as_view(), name='featured-listings'),
    path('recent/', views.RecentListingsView.as_view(), name='recent-listings'),
    
    # Filter data endpoints
    path('filter-data/', views.filter_data_view, name='filter-data'),
    path('models-by-make/', views.models_by_make_view, name='models-by-make'),
    path('search/', views.advanced_search_view, name='advanced-search'),
    path('live-search/', views.live_search_view, name='live-search'),
    
    # Listing management endpoints (authenticated)
    path('create/', views.VehicleListingCreateView.as_view(), name='listing-create'),
    
    # User's listings
    path('my/', views.MyListingsView.as_view(), name='my-listings'),
    
    # Saved listings
    path('saved/', views.SavedListingListView.as_view(), name='saved-listings'),
    path('saved/<int:pk>/delete/', views.SavedListingDeleteView.as_view(), name='saved-listing-delete'),
    
    # Statistics and analytics
    path('stats/', views.listing_stats_view, name='listing-stats'),
    
    # Bulk operations
    path('bulk/status-change/', views.bulk_status_change_view, name='bulk-status-change'),
    
    # Slug-based patterns (must come last to avoid conflicts)
    path('<slug:slug>/', views.VehicleListingDetailView.as_view(), name='listing-detail'),
    path('<slug:slug>/update/', views.VehicleListingUpdateView.as_view(), name='listing-update'),
    path('<slug:slug>/delete/', views.VehicleListingDeleteView.as_view(), name='listing-delete'),
    path('<slug:slug>/status/', views.VehicleListingStatusView.as_view(), name='listing-status'),
    
    # Media management
    path('<slug:listing_slug>/images/', views.ListingImageListView.as_view(), name='listing-images'),
    path('<slug:listing_slug>/images/<int:pk>/', views.ListingImageDetailView.as_view(), name='listing-image-detail'),
    path('<slug:listing_slug>/videos/', views.ListingVideoListView.as_view(), name='listing-videos'),
    path('<slug:listing_slug>/videos/<int:pk>/', views.ListingVideoDetailView.as_view(), name='listing-video-detail'),
]