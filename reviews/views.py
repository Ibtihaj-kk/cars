from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Avg
from rest_framework import viewsets, permissions, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from django_filters.rest_framework import DjangoFilterBackend

from .models import VehicleReview, DealerReview, SellerReview, ListingReview, ReviewImage, ReviewVote, ReviewComment, ReviewStatus
from .moderation import ReviewModerationService, ReviewQualityAnalyzer
from .serializers import (
    VehicleReviewListSerializer,
    VehicleReviewDetailSerializer,
    VehicleReviewCreateUpdateSerializer,
    DealerReviewListSerializer,
    DealerReviewDetailSerializer,
    DealerReviewCreateUpdateSerializer,
    SellerReviewListSerializer,
    SellerReviewDetailSerializer,
    SellerReviewCreateUpdateSerializer,
    ListingReviewListSerializer,
    ListingReviewDetailSerializer,
    ListingReviewCreateUpdateSerializer,
    ReviewCommentSerializer,
    ReviewVoteCreateSerializer
)
from vehicles.models import VehicleModel


class VehicleReviewViewSet(viewsets.ModelViewSet):
    """ViewSet for vehicle reviews."""
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['title', 'content', 'pros', 'cons']
    filterset_fields = ['vehicle_model', 'status', 'user']
    ordering_fields = ['created_at', 'overall_rating']
    ordering = ['-created_at']
    
    def get_queryset(self):
        # By default, only show approved reviews to the public
        queryset = VehicleReview.objects.all()
        
        # If user is staff or admin, they can see all reviews
        user = self.request.user
        if not (user.is_authenticated and (user.is_staff or user.is_superuser)):
            queryset = queryset.filter(status=ReviewStatus.APPROVED)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return VehicleReviewDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return VehicleReviewCreateUpdateSerializer
        return VehicleReviewListSerializer
    
    def perform_create(self, serializer):
        """Create vehicle review with logging and moderation."""
        from .models import ReviewLog
        
        review = serializer.save(user=self.request.user)
        
        # Perform automated moderation
        moderation_results = ReviewModerationService.moderate_review(review)
        
        # Update review status based on moderation
        review.status = moderation_results['status']
        review.save()
        
        # Log moderation action
        ReviewModerationService.log_moderation_action(review, moderation_results, self.request.user)
        
        # Log the creation
        ReviewLog.log_action(
            user=self.request.user,
            content_object=review,
            action='CREATE',
            description=f"Vehicle review created for {review.vehicle_model.name}",
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            new_data={'moderation_status': moderation_results['status'], 'moderation_score': moderation_results['score']}
        )
    
    def get_client_ip(self):
        """Get client IP address."""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip
    
    @action(detail=False, methods=['get'])
    def my_reviews(self, request):
        """Get current user's vehicle reviews."""
        reviews = VehicleReview.objects.filter(user=request.user)
        serializer = VehicleReviewListSerializer(reviews, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get statistics for vehicle reviews."""
        vehicle_model_id = request.query_params.get('vehicle_model')
        if not vehicle_model_id:
            return Response({'error': 'vehicle_model parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            vehicle_model = VehicleModel.objects.get(id=vehicle_model_id)
        except VehicleModel.DoesNotExist:
            return Response({'error': 'Vehicle model not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get approved reviews for this vehicle model
        reviews = VehicleReview.objects.filter(
            vehicle_model=vehicle_model,
            status=ReviewStatus.APPROVED
        )
        
        # Calculate average ratings
        avg_ratings = reviews.aggregate(
            avg_overall=Avg('overall_rating'),
            avg_performance=Avg('performance_rating'),
            avg_comfort=Avg('comfort_rating'),
            avg_reliability=Avg('reliability_rating'),
            avg_value=Avg('value_rating'),
            avg_fuel_economy=Avg('fuel_economy_rating')
        )
        
        # Count reviews by rating
        rating_counts = {
            '5': reviews.filter(overall_rating=5).count(),
            '4': reviews.filter(overall_rating=4).count(),
            '3': reviews.filter(overall_rating=3).count(),
            '2': reviews.filter(overall_rating=2).count(),
            '1': reviews.filter(overall_rating=1).count()
        }
        
        return Response({
            'vehicle_model': vehicle_model.name,
            'total_reviews': reviews.count(),
            'average_ratings': avg_ratings,
            'rating_counts': rating_counts
        })
    
    @action(detail=True, methods=['get'])
    def quality_analysis(self, request, pk=None):
        """Get quality analysis for a specific vehicle review."""
        review = self.get_object()
        analysis = ReviewQualityAnalyzer.analyze_review_quality(review)
        return Response(analysis)


class DealerReviewViewSet(viewsets.ModelViewSet):
    """ViewSet for dealer reviews."""
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['title', 'content', 'pros', 'cons']
    filterset_fields = ['dealer', 'status', 'user']
    ordering_fields = ['created_at', 'overall_rating']
    ordering = ['-created_at']
    
    def get_queryset(self):
        # By default, only show approved reviews to the public
        queryset = DealerReview.objects.all()
        
        # If user is staff or admin, they can see all reviews
        user = self.request.user
        if not (user.is_authenticated and (user.is_staff or user.is_superuser)):
            queryset = queryset.filter(status=DealerReview.ReviewStatus.APPROVED)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DealerReviewDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return DealerReviewCreateUpdateSerializer
        return DealerReviewListSerializer
    
    def perform_create(self, serializer):
        """Create dealer review with logging and moderation."""
        from .models import ReviewLog
        
        review = serializer.save(user=self.request.user)
        
        # Perform automated moderation
        moderation_results = ReviewModerationService.moderate_review(review)
        
        # Update review status based on moderation
        if moderation_results['status'] != 'approved':
            review.status = moderation_results['status']
            review.save()
        
        # Log moderation action
        ReviewModerationService.log_moderation_action(review, moderation_results, self.request.user)
        
        # Log the creation
        ReviewLog.log_action(
            user=self.request.user,
            content_object=review,
            action='CREATE',
            description=f"Dealer review created for {review.dealer.name}",
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            new_data={'moderation_status': moderation_results['status'], 'moderation_score': moderation_results['score']}
        )
    
    def get_client_ip(self):
        """Get client IP address."""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip
    
    @action(detail=False, methods=['get'])
    def my_reviews(self, request):
        """Get current user's dealer reviews."""
        reviews = DealerReview.objects.filter(user=request.user)
        serializer = DealerReviewListSerializer(reviews, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get statistics for dealer reviews."""
        dealer_id = request.query_params.get('dealer')
        if not dealer_id:
            return Response({'error': 'dealer parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get approved reviews for this dealer
        reviews = DealerReview.objects.filter(
            dealer_id=dealer_id,
            status=DealerReview.ReviewStatus.APPROVED
        )
        
        # Calculate average ratings
        avg_ratings = reviews.aggregate(
            avg_overall=Avg('overall_rating'),
            avg_customer_service=Avg('customer_service_rating'),
            avg_buying_process=Avg('buying_process_rating'),
            avg_price_fairness=Avg('price_fairness_rating'),
            avg_facility=Avg('facility_rating')
        )
        
        # Count reviews by rating
        rating_counts = {
            '5': reviews.filter(overall_rating=5).count(),
            '4': reviews.filter(overall_rating=4).count(),
            '3': reviews.filter(overall_rating=3).count(),
            '2': reviews.filter(overall_rating=2).count(),
            '1': reviews.filter(overall_rating=1).count()
        }
        
        return Response({
            'dealer_id': dealer_id,
            'total_reviews': reviews.count(),
            'average_ratings': avg_ratings,
            'rating_counts': rating_counts
        })


class ReviewCommentViewSet(viewsets.ModelViewSet):
    """ViewSet for review comments."""
    serializer_class = ReviewCommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        # Filter comments by review type and ID
        review_type = self.request.query_params.get('review_type')
        review_id = self.request.query_params.get('review_id')
        
        queryset = ReviewComment.objects.all()
        
        if review_type and review_id:
            if review_type == 'vehicle':
                queryset = queryset.filter(vehicle_review_id=review_id)
            elif review_type == 'dealer':
                queryset = queryset.filter(dealer_review_id=review_id)
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        # Extract review type and ID from request data
        review_type = request.data.get('review_type')
        review_id = request.data.get('review_id')
        content = request.data.get('content')
        
        if not all([review_type, review_id, content]):
            return Response(
                {'error': 'review_type, review_id, and content are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create comment based on review type
        try:
            if review_type == 'vehicle':
                review = VehicleReview.objects.get(id=review_id)
                comment = ReviewComment.objects.create(
                    user=request.user,
                    vehicle_review=review,
                    content=content
                )
            elif review_type == 'dealer':
                review = DealerReview.objects.get(id=review_id)
                comment = ReviewComment.objects.create(
                    user=request.user,
                    dealer_review=review,
                    content=content
                )
            else:
                return Response(
                    {'error': 'Invalid review_type. Must be "vehicle" or "dealer".'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (VehicleReview.DoesNotExist, DealerReview.DoesNotExist):
            return Response(
                {'error': 'Review not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(comment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ReviewVoteViewSet(viewsets.GenericViewSet):
    """ViewSet for review votes."""
    serializer_class = ReviewVoteCreateSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def vote(self, request):
        """Vote on a review."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vote = serializer.save()
        
        return Response({'status': 'vote recorded'}, status=status.HTTP_201_CREATED)


class SellerReviewViewSet(viewsets.ModelViewSet):
    """ViewSet for managing seller reviews."""
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'overall_rating', 'is_verified_transaction']
    search_fields = ['title', 'review_text', 'pros', 'cons']
    ordering_fields = ['created_at', 'overall_rating', 'helpful_votes']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get seller reviews with vote counts."""
        from django.db.models import Count, Q
        return SellerReview.objects.select_related('user', 'seller').prefetch_related(
            'images', 'comments', 'votes'
        ).annotate(
            helpful_votes=Count('votes', filter=Q(votes__is_helpful=True)),
            unhelpful_votes=Count('votes', filter=Q(votes__is_helpful=False))
        ).filter(status='approved')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return SellerReviewListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return SellerReviewCreateUpdateSerializer
        return SellerReviewDetailSerializer
    
    def perform_create(self, serializer):
        """Create seller review with logging."""
        from .models import ReviewLog
        
        review = serializer.save(user=self.request.user)
        
        # Log the creation
        ReviewLog.log_action(
            user=self.request.user,
            content_object=review,
            action='CREATE',
            description=f"Seller review created for {review.seller.email}",
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
    
    def perform_update(self, serializer):
        """Update seller review with logging."""
        from .models import ReviewLog
        
        old_instance = self.get_object()
        previous_data = {
            'title': old_instance.title,
            'review_text': old_instance.review_text,
            'overall_rating': old_instance.overall_rating,
            'status': old_instance.status,
        }
        
        review = serializer.save()
        
        new_data = {
            'title': review.title,
            'review_text': review.review_text,
            'overall_rating': review.overall_rating,
            'status': review.status,
        }
        
        # Log the update
        ReviewLog.log_action(
            user=self.request.user,
            content_object=review,
            action='UPDATE',
            description=f"Seller review updated for {review.seller.email}",
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            previous_data=previous_data,
            new_data=new_data
        )
    
    def perform_destroy(self, instance):
        """Delete seller review with logging."""
        from .models import ReviewLog
        
        # Log before deletion
        ReviewLog.log_action(
            user=self.request.user,
            content_object=instance,
            action='DELETE',
            description=f"Seller review deleted for {instance.seller.email}",
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            previous_data={
                'title': instance.title,
                'review_text': instance.review_text,
                'overall_rating': instance.overall_rating,
                'status': instance.status,
            }
        )
        
        super().perform_destroy(instance)
    
    def get_client_ip(self):
        """Get client IP address."""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip
    
    @action(detail=False, methods=['get'])
    def my_reviews(self, request):
        """Get current user's seller reviews."""
        reviews = self.get_queryset().filter(user=request.user)
        page = self.paginate_queryset(reviews)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get seller review statistics."""
        from django.db.models import Avg, Count
        
        seller_id = request.query_params.get('seller_id')
        if not seller_id:
            return Response({'error': 'seller_id parameter is required'}, status=400)
        
        reviews = self.get_queryset().filter(seller_id=seller_id)
        
        stats = reviews.aggregate(
            total_reviews=Count('id'),
            average_rating=Avg('overall_rating'),
            average_communication=Avg('communication_rating'),
            average_reliability=Avg('reliability_rating'),
            average_responsiveness=Avg('responsiveness_rating'),
        )
        
        # Add rating distribution
        rating_counts = {}
        for i in range(1, 6):
            rating_counts[f'rating_{i}_count'] = reviews.filter(overall_rating=i).count()
        
        stats.update(rating_counts)
        return Response(stats)
    
    @action(detail=True, methods=['get'])
    def quality_analysis(self, request, pk=None):
        """Get quality analysis for a specific review."""
        review = self.get_object()
        analysis = ReviewQualityAnalyzer.analyze_review_quality(review)
        return Response(analysis)


class ListingReviewViewSet(viewsets.ModelViewSet):
    """ViewSet for managing listing reviews."""
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'overall_rating', 'is_verified_purchase']
    search_fields = ['title', 'review_text', 'pros', 'cons']
    ordering_fields = ['created_at', 'overall_rating', 'helpful_votes']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get listing reviews with vote counts."""
        from django.db.models import Count, Q
        return ListingReview.objects.select_related('user', 'listing').prefetch_related(
            'images', 'comments', 'votes'
        ).annotate(
            helpful_votes=Count('votes', filter=Q(votes__is_helpful=True)),
            unhelpful_votes=Count('votes', filter=Q(votes__is_helpful=False))
        ).filter(status='approved')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return ListingReviewListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ListingReviewCreateUpdateSerializer
        return ListingReviewDetailSerializer
    
    def perform_create(self, serializer):
        """Create listing review with logging."""
        from .models import ReviewLog
        
        review = serializer.save(user=self.request.user)
        
        # Log the creation
        ReviewLog.log_action(
            user=self.request.user,
            content_object=review,
            action='CREATE',
            description=f"Listing review created for {review.listing.title}",
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
    
    def perform_update(self, serializer):
        """Update listing review with logging."""
        from .models import ReviewLog
        
        old_instance = self.get_object()
        previous_data = {
            'title': old_instance.title,
            'review_text': old_instance.review_text,
            'overall_rating': old_instance.overall_rating,
            'status': old_instance.status,
        }
        
        review = serializer.save()
        
        new_data = {
            'title': review.title,
            'review_text': review.review_text,
            'overall_rating': review.overall_rating,
            'status': review.status,
        }
        
        # Log the update
        ReviewLog.log_action(
            user=self.request.user,
            content_object=review,
            action='UPDATE',
            description=f"Listing review updated for {review.listing.title}",
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            previous_data=previous_data,
            new_data=new_data
        )
    
    def perform_destroy(self, instance):
        """Delete listing review with logging."""
        from .models import ReviewLog
        
        # Log before deletion
        ReviewLog.log_action(
            user=self.request.user,
            content_object=instance,
            action='DELETE',
            description=f"Listing review deleted for {instance.listing.title}",
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            previous_data={
                'title': instance.title,
                'review_text': instance.review_text,
                'overall_rating': instance.overall_rating,
                'status': instance.status,
            }
        )
        
        super().perform_destroy(instance)
    
    def get_client_ip(self):
        """Get client IP address."""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip
    
    @action(detail=False, methods=['get'])
    def my_reviews(self, request):
        """Get current user's listing reviews."""
        reviews = self.get_queryset().filter(user=request.user)
        page = self.paginate_queryset(reviews)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get listing review statistics."""
        from django.db.models import Avg, Count
        
        listing_id = request.query_params.get('listing_id')
        if not listing_id:
            return Response({'error': 'listing_id parameter is required'}, status=400)
        
        reviews = self.get_queryset().filter(listing_id=listing_id)
        
        stats = reviews.aggregate(
            total_reviews=Count('id'),
            average_rating=Avg('overall_rating'),
            average_condition=Avg('condition_rating'),
            average_value=Avg('value_rating'),
            average_description_accuracy=Avg('description_accuracy_rating'),
        )
        
        # Add rating distribution
        rating_counts = {}
        for i in range(1, 6):
            rating_counts[f'rating_{i}_count'] = reviews.filter(overall_rating=i).count()
        
        stats.update(rating_counts)
        return Response(stats)
