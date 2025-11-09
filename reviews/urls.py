from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    VehicleReviewViewSet, DealerReviewViewSet, SellerReviewViewSet, 
    ListingReviewViewSet, ReviewCommentViewSet, ReviewVoteViewSet
)

app_name = 'reviews'

router = DefaultRouter()
router.register(r'vehicle-reviews', VehicleReviewViewSet, basename='vehiclereview')
router.register(r'dealer-reviews', DealerReviewViewSet, basename='dealerreview')
router.register(r'seller-reviews', SellerReviewViewSet, basename='sellerreview')
router.register(r'listing-reviews', ListingReviewViewSet, basename='listingreview')
router.register(r'comments', ReviewCommentViewSet, basename='reviewcomment')
router.register(r'votes', ReviewVoteViewSet, basename='reviewvote')

urlpatterns = [
    path('', include(router.urls)),
]