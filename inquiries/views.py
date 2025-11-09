from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Count
from django.utils import timezone
from rest_framework import viewsets, permissions, status, filters, generics
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from core.pagination import StandardResultsSetPagination
import threading

from .models import ListingInquiry, InquiryResponse, TestDriveRequest
from .permissions import (
    IsInquiryOwnerOrListingOwner,
    IsListingOwner,
    IsResponseOwnerOrInquiryParticipant,
    CanCreateInquiry,
    CanManageTestDrive,
    IsDealerRole
)
from .serializers import (
    ListingInquiryListSerializer,
    ListingInquiryDetailSerializer,
    ListingInquiryCreateSerializer,
    InquiryResponseSerializer,
    InquiryResponseCreateSerializer,
    TestDriveRequestSerializer,
    TestDriveRequestUpdateSerializer,
    ReceivedInquirySerializer,
    UnauthenticatedInquiryCreateSerializer
)
from listings.models import VehicleListing


class ListingInquiryViewSet(viewsets.ModelViewSet):
    """ViewSet for listing inquiries."""
    permission_classes = [IsAuthenticated, IsInquiryOwnerOrListingOwner]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['message']
    filterset_fields = ['status', 'inquiry_type', 'listing']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        
        # If user is staff or admin, they can see all inquiries
        if user.is_staff or user.is_superuser:
            return ListingInquiry.objects.all()
        
        # Regular users can see their own inquiries and inquiries for their listings
        return ListingInquiry.objects.filter(
            # User's own inquiries
            Q(user=user) |
            # Inquiries for user's listings
            Q(listing__user=user)
        )
    
    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action == 'create':
            permission_classes = [IsAuthenticated, CanCreateInquiry]
        elif self.action in ['mark_as_viewed', 'mark_as_closed']:
            permission_classes = [IsAuthenticated, IsListingOwner]
        else:
            permission_classes = [IsAuthenticated, IsInquiryOwnerOrListingOwner]
        
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        """Set the user when creating an inquiry and send notification email."""
        from .email_service import DealerNotificationEmailService
        
        # Save the inquiry
        inquiry = serializer.save(user=self.request.user)
        
        # Send email notification to dealer (async to avoid blocking the request)
        try:
            if DealerNotificationEmailService.should_send_notification(inquiry):
                # Import here to avoid circular imports
                from django.utils import timezone
                import threading
                
                # Send email in a separate thread to avoid blocking the API response
                def send_notification():
                    DealerNotificationEmailService.send_new_inquiry_notification(inquiry)
                
                thread = threading.Thread(target=send_notification)
                thread.daemon = True
                thread.start()
        except Exception as e:
            # Log error but don't fail the inquiry creation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error initiating email notification for inquiry {inquiry.id}: {str(e)}")
        
        return inquiry

    def create(self, request, *args, **kwargs):
        """Create an inquiry and return it with the list serializer."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Return the created inquiry using the list serializer to include the ID
        instance = serializer.instance
        response_serializer = ListingInquiryListSerializer(instance, context={'request': request})
        headers = self.get_success_headers(serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def get_serializer_class(self):
        if self.action == 'create':
            return ListingInquiryCreateSerializer
        elif self.action in ['list', 'my_inquiries', 'received_inquiries', 'seller_dashboard']:
            return ListingInquiryListSerializer
        return ListingInquiryDetailSerializer
    
    @action(detail=False, methods=['get'])
    def my_inquiries(self, request):
        """Get current user's inquiries."""
        inquiries = ListingInquiry.objects.filter(user=request.user)
        serializer = ListingInquiryListSerializer(inquiries, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def received_inquiries(self, request):
        """Get inquiries for current user's listings (Seller Portal)."""
        inquiries = ListingInquiry.objects.filter(listing__user=request.user)
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            inquiries = inquiries.filter(status=status_filter)
        
        serializer = ListingInquiryListSerializer(inquiries, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_as_viewed(self, request, pk=None):
        """Mark inquiry as viewed by seller."""
        inquiry = self.get_object()
        
        # Only the listing owner can mark as viewed
        if inquiry.listing.user != request.user:
            return Response(
                {'error': 'You do not have permission to update this inquiry.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        inquiry.mark_as_viewed()
        serializer = self.get_serializer(inquiry)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_as_closed(self, request, pk=None):
        """Mark inquiry as closed."""
        inquiry = self.get_object()
        
        # Only the listing owner can close the inquiry
        if inquiry.listing.user != request.user:
            return Response(
                {'error': 'You do not have permission to update this inquiry.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        inquiry.mark_as_closed()
        serializer = self.get_serializer(inquiry)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def seller_dashboard(self, request):
        """Get seller dashboard statistics."""
        user_inquiries = ListingInquiry.objects.filter(listing__user=request.user)
        
        stats = {
            'total_inquiries': user_inquiries.count(),
            'new_inquiries': user_inquiries.filter(status='new').count(),
            'viewed_inquiries': user_inquiries.filter(status='viewed').count(),
            'replied_inquiries': user_inquiries.filter(status='replied').count(),
            'closed_inquiries': user_inquiries.filter(status='closed').count(),
            'recent_inquiries': ListingInquiryListSerializer(
                user_inquiries[:5], many=True
            ).data
        }
        
        return Response(stats)


class InquiryResponseViewSet(viewsets.ModelViewSet):
    """ViewSet for inquiry responses."""
    serializer_class = InquiryResponseSerializer
    permission_classes = [IsAuthenticated, IsResponseOwnerOrInquiryParticipant]
    
    def get_queryset(self):
        user = self.request.user
        
        # If user is staff or admin, they can see all responses
        if user.is_staff or user.is_superuser:
            return InquiryResponse.objects.all()
        
        # Regular users can see responses to their inquiries and responses they've made
        return InquiryResponse.objects.filter(
            # Responses to user's inquiries
            Q(inquiry__user=user) |
            # Responses user has made
            Q(responder=user) |
            # Responses to inquiries about user's listings
            Q(inquiry__listing__user=user)
        )
    
    def get_serializer_class(self):
        if self.action == 'create':
            return InquiryResponseCreateSerializer
        return InquiryResponseSerializer
    
    def perform_create(self, serializer):
        """Create response and mark inquiry as replied."""
        response = serializer.save(responder=self.request.user)
        # The inquiry status is automatically updated in the model's save method
        return response


class TestDriveRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for test drive requests."""
    serializer_class = TestDriveRequestSerializer
    permission_classes = [IsAuthenticated, CanManageTestDrive]
    
    def get_queryset(self):
        user = self.request.user
        
        # If user is staff or admin, they can see all test drive requests
        if user.is_staff or user.is_superuser:
            return TestDriveRequest.objects.all()
        
        # Regular users can see their own test drive requests and requests for their listings
        return TestDriveRequest.objects.filter(
            # User's own test drive requests
            Q(inquiry__user=user) |
            # Test drive requests for user's listings
            Q(inquiry__listing__user=user)
        )
    
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return TestDriveRequestUpdateSerializer
        return TestDriveRequestSerializer
    
    @action(detail=True, methods=['post'])
    def confirm_test_drive(self, request, pk=None):
        """Confirm or unconfirm a test drive request."""
        test_drive = self.get_object()
        
        # Only the listing owner can confirm the test drive
        if test_drive.inquiry.listing.user != request.user:
            return Response(
                {'error': 'You do not have permission to update this test drive request.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        is_confirmed = request.data.get('is_confirmed', True)
        test_drive.is_confirmed = is_confirmed
        
        if is_confirmed:
            from django.utils import timezone
            test_drive.confirmation_date = timezone.now()
            test_drive.confirmed_by = request.user
        else:
            test_drive.confirmation_date = None
            test_drive.confirmed_by = None
            
        test_drive.save()
        
        serializer = self.get_serializer(test_drive)
        return Response(serializer.data)


class ReceivedInquiriesView(generics.ListAPIView):
    """
    API endpoint for dealers to retrieve inquiries for their vehicle listings.
    
    This endpoint allows authenticated dealers to view all inquiries 
    associated with their vehicle listings with proper authorization
    and pagination.
    """
    serializer_class = ReceivedInquirySerializer
    permission_classes = [permissions.IsAuthenticated, IsDealerRole]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['inquiry_type', 'status', 'is_read']
    ordering_fields = ['created_at', 'updated_at', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Get inquiries for the current dealer's listings.
        
        Returns:
            QuerySet: ListingInquiry objects filtered by dealer's listings
        """
        # Get all listings owned by the current dealer
        dealer_listings = VehicleListing.objects.filter(user=self.request.user)
        
        # Filter inquiries to only those related to dealer's listings
        return ListingInquiry.objects.filter(
            listing__in=dealer_listings
        ).select_related(
            'listing', 'user'
        ).order_by('-created_at')


class UnauthenticatedInquiryCreateView(APIView):
    """
    API endpoint for creating inquiries without authentication.
    
    This endpoint allows both authenticated and unauthenticated users 
    to submit inquiries about vehicle listings.
    """
    permission_classes = []  # No authentication required
    
    def post(self, request, *args, **kwargs):
        """Create a new inquiry without requiring authentication."""
        # Get client IP and user agent for tracking
        ip_address = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Add context for the serializer
        context = {
            'request': request,
            'ip_address': ip_address,
            'user_agent': user_agent
        }
        
        serializer = UnauthenticatedInquiryCreateSerializer(
            data=request.data, 
            context=context
        )
        
        if serializer.is_valid():
            inquiry = serializer.save()
            
            # Send email notification in a separate thread
            def send_notification():
                try:
                    if DealerNotificationEmailService.should_send_notification(inquiry):
                        email_service = DealerNotificationEmailService()
                        email_service.send_new_inquiry_notification(inquiry)
                except Exception as e:
                    # Log the error but don't fail the request
                    import logging
                    logger = logging.getLogger('email_notifications')
                    logger.error(f"Failed to send email notification for inquiry {inquiry.id}: {str(e)}")
            
            # Start email notification in background
            threading.Thread(target=send_notification).start()
            
            # Return success response
            return Response({
                'id': inquiry.id,
                'message': 'Inquiry submitted successfully',
                'listing_id': inquiry.listing.id,
                'status': 'created'
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self, request):
        """Get the client's IP address from the request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
