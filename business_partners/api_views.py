from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q, Count, Avg, F, Case, When, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.auth.decorators import permission_required, login_required
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from admin_panel.rbac_decorators import can_manage_vendors, can_review_vendor_applications, can_approve_vendors
from core.rbac_manager import rbac_manager
from decimal import Decimal
import logging

from .models import (
    VendorApplication, BusinessPartner, BusinessPartnerRole,
    ReorderNotification
)
from .document_models import VendorDocument, DocumentCategory
from .workflow_engine import VendorComplianceCheck
from .audit_logger import VendorAuditLog
from .serializers import (
    VendorApplicationListSerializer, VendorApplicationSerializer, 
    VendorApplicationReviewSerializer, BusinessPartnerSerializer,
    VendorDocumentSerializer, DocumentCategorySerializer,
    VendorComplianceSerializer, VendorPerformanceSerializer,
    VendorAnalyticsSerializer
)
from .performance_engine import VendorPerformanceCalculator, VendorPerformanceAnalyzer
from .error_handlers import (
    VendorAPIErrorHandler, create_error_response, create_validation_error_response,
    create_success_response, handle_vendor_api_errors
)
from .audit_logger import VendorAuditLogger
from .permissions import IsVendorManager

from parts.models import Part, Category, Inventory, InventoryTransaction, Order, OrderItem

logger = logging.getLogger(__name__)


class VendorApplicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing vendor applications.
    Provides CRUD operations and workflow transitions with comprehensive error handling and audit logging.
    """
    queryset = VendorApplication.objects.all()
    serializer_class = VendorApplicationSerializer
    permission_classes = [IsVendorManager]
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        user = self.request.user
        
        if not rbac_manager.has_permission(user, 'business_partners.can_manage_vendors'):
            raise PermissionDenied("You don't have permission to manage vendor applications.")
        
        queryset = VendorApplication.objects.select_related('user').prefetch_related('documents')
        
        # Filter by status if provided
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by priority if provided
        priority_filter = self.request.query_params.get('priority')
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)
        
        # Filter by date range if provided
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        return queryset.order_by('-created_at')
    
    @handle_vendor_api_errors
    def create(self, request, *args, **kwargs):
        """Create a new vendor application with validation and audit logging."""
        try:
            # Validate input data
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Create application
            application = serializer.save(user=request.user)
            
            # Log the action
            VendorAuditLogger.log_application_submission(
                request.user,
                application,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            return create_success_response(
                'Vendor application submitted successfully',
                {'application': serializer.data}
            )
            
        except Exception as e:
            logger.error(f"Error creating vendor application: {str(e)}", exc_info=True)
            raise
    
    @handle_vendor_api_errors
    def update(self, request, *args, **kwargs):
        """Update vendor application with audit logging."""
        try:
            instance = self.get_object()
            old_status = instance.status
            
            # Validate and update
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            updated_instance = serializer.save()
            
            # Log status change if applicable
            if old_status != updated_instance.status:
                VendorAuditLogger.log_application_review(
                    request.user,
                    updated_instance,
                    old_status,
                    updated_instance.status,
                    notes=updated_instance.notes,
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT')
                )
            
            return create_success_response(
                'Vendor application updated successfully',
                {'application': serializer.data}
            )
            
        except Exception as e:
            logger.error(f"Error updating vendor application: {str(e)}", exc_info=True)
            raise
    
    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class VendorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing approved vendors (BusinessPartners).
    Provides CRUD operations and vendor-specific endpoints with error handling and audit logging.
    """
    queryset = BusinessPartner.objects.filter(type='vendor')
    serializer_class = BusinessPartnerSerializer
    permission_classes = [IsVendorManager]
    
    def get_queryset(self):
        """Filter queryset based on user permissions and search criteria."""
        user = self.request.user
        
        if not rbac_manager.has_permission(user, 'business_partners.can_manage_vendors'):
            raise PermissionDenied("You don't have permission to manage vendors.")
        
        queryset = BusinessPartner.objects.filter(type='vendor').select_related('user')
        
        # Search functionality
        search_query = self.request.query_params.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(company_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(phone__icontains=search_query)
            )
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by rating
        rating_filter = self.request.query_params.get('rating')
        if rating_filter:
            queryset = queryset.filter(vendor_rating__gte=float(rating_filter))
        
        return queryset.order_by('-created_at')
    
    @action(detail=True, methods=['get'])
    @handle_vendor_api_errors
    def performance(self, request, pk=None):
        """Get vendor performance metrics and scores for a specified period."""
        try:
            vendor = self.get_object()
            
            # Check permissions
            if not rbac_manager.has_permission(request.user, 'business_partners.can_view_vendor_performance'):
                return create_error_response(
                    'You don\'t have permission to view vendor performance metrics',
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            # Get date range parameters
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            if not start_date or not end_date:
                return create_validation_error_response(
                    'start_date and end_date parameters are required',
                    {'start_date': ['This field is required'], 'end_date': ['This field is required']}
                )
            
            # Calculate performance metrics
            calculator = VendorPerformanceCalculator()
            metrics = calculator.calculate_vendor_performance(vendor, start_date, end_date)
            
            # Get performance scores
            scores = VendorPerformanceScore.objects.filter(
                vendor=vendor,
                period_start__gte=start_date,
                period_end__lte=end_date
            ).order_by('-created_at')
            
            # Serialize data
            performance_data = {
                'vendor_id': vendor.id,
                'vendor_name': vendor.name,
                'period_start': start_date,
                'period_end': end_date,
                'metrics': metrics,
                'scores': VendorPerformanceSerializer(scores, many=True).data
            }
            
            # Log the action
            VendorAuditLogger.log_performance_view(
                request.user,
                vendor,
                start_date,
                end_date,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            return create_success_response(
                'Vendor performance data retrieved successfully',
                performance_data
            )
            
        except Exception as e:
            logger.error(f"Error retrieving vendor performance: {str(e)}", exc_info=True)
            raise
    
    @action(detail=True, methods=['post'])
    @handle_vendor_api_errors
    def calculate_performance(self, request, pk=None):
        """Trigger calculation of vendor performance for a given period."""
        try:
            vendor = self.get_object()
            
            # Check permissions
            if not rbac_manager.has_permission(request.user, 'business_partners.can_calculate_vendor_performance'):
                return create_error_response(
                    'You don\'t have permission to calculate vendor performance',
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            # Get date range from request
            start_date = request.data.get('start_date')
            end_date = request.data.get('end_date')
            
            if not start_date or not end_date:
                return create_validation_error_response(
                    'start_date and end_date are required',
                    {'start_date': ['This field is required'], 'end_date': ['This field is required']}
                )
            
            # Calculate performance
            calculator = VendorPerformanceCalculator()
            result = calculator.calculate_and_save_performance(vendor, start_date, end_date)
            
            # Log the action
            VendorAuditLogger.log_performance_calculation(
                request.user,
                vendor,
                start_date,
                end_date,
                result['overall_score'],
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            return create_success_response(
                'Vendor performance calculated successfully',
                result
            )
            
        except Exception as e:
            logger.error(f"Error calculating vendor performance: {str(e)}", exc_info=True)
            raise
    
    @action(detail=True, methods=['post'])
    @handle_vendor_api_errors
    def toggle_status(self, request, pk=None):
        """Toggle vendor status (active/inactive) with audit logging."""
        try:
            vendor = self.get_object()
            
            # Check permissions
            if not rbac_manager.has_permission(request.user, 'business_partners.can_approve_vendors'):
                return create_error_response(
                    'You don\'t have permission to change vendor status',
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            # Toggle status
            new_status = 'inactive' if vendor.status == 'active' else 'active'
            old_status = vendor.status
            
            vendor.status = new_status
            vendor.save()
            
            # Log the action
            VendorAuditLogger.log_vendor_status_change(
                request.user,
                vendor,
                old_status,
                new_status,
                reason=request.data.get('reason', 'Status toggled via API'),
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            return create_success_response(
                f'Vendor status changed from {old_status} to {new_status}',
                {'vendor_id': vendor.id, 'new_status': new_status}
            )
            
        except Exception as e:
            logger.error(f"Error toggling vendor status: {str(e)}", exc_info=True)
            raise
    
    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class VendorDocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing vendor documents with comprehensive validation and audit logging.
    """
    queryset = VendorDocument.objects.all()
    serializer_class = VendorDocumentSerializer
    permission_classes = [IsVendorManager]
    
    def get_queryset(self):
        """Filter queryset based on user permissions and vendor access."""
        user = self.request.user
        
        if not rbac_manager.has_permission(user, 'business_partners.can_manage_vendor_documents'):
            raise PermissionDenied("You don't have permission to manage vendor documents.")
        
        queryset = VendorDocument.objects.select_related('vendor', 'category', 'uploaded_by')
        
        # Filter by vendor if provided
        vendor_id = self.request.query_params.get('vendor_id')
        if vendor_id:
            queryset = queryset.filter(vendor_id=vendor_id)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by category
        category_filter = self.request.query_params.get('category')
        if category_filter:
            queryset = queryset.filter(category__name__icontains=category_filter)
        
        # Filter by expiry status
        expiry_filter = self.request.query_params.get('expiry_status')
        if expiry_filter:
            if expiry_filter == 'expired':
                queryset = queryset.filter(expiry_date__lt=timezone.now().date())
            elif expiry_filter == 'expiring_soon':
                soon_date = timezone.now().date() + timedelta(days=30)
                queryset = queryset.filter(expiry_date__lte=soon_date, expiry_date__gte=timezone.now().date())
        
        return queryset.order_by('-uploaded_at')
    
    @handle_vendor_api_errors
    def create(self, request, *args, **kwargs):
        """Upload a new document with validation and audit logging."""
        try:
            # Validate file upload
            if 'file' not in request.FILES:
                return create_validation_error_response(
                    'No file provided',
                    {'file': ['This field is required']}
                )
            
            # Validate and create document
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            document = serializer.save(uploaded_by=request.user)
            
            # Log the action
            VendorAuditLogger.log_document_upload(
                request.user,
                document.vendor,
                document,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            return create_success_response(
                'Document uploaded successfully',
                {'document': serializer.data}
            )
            
        except Exception as e:
            logger.error(f"Error uploading document: {str(e)}", exc_info=True)
            raise
    
    @action(detail=True, methods=['post'])
    @handle_vendor_api_errors
    def verify(self, request, pk=None):
        """Verify a document with audit logging."""
        try:
            document = self.get_object()
            
            # Check permissions
            if not rbac_manager.has_permission(request.user, 'business_partners.can_verify_vendor_documents'):
                return create_error_response(
                    'You don\'t have permission to verify documents',
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            # Update status
            old_status = document.status
            document.status = 'verified'
            document.verified_by = request.user
            document.verified_at = timezone.now()
            document.verification_notes = request.data.get('notes', '')
            document.save()
            
            # Log the action
            VendorAuditLogger.log_document_verification(
                request.user,
                document.vendor,
                document,
                old_status,
                'verified',
                notes=document.verification_notes,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            return create_success_response(
                'Document verified successfully',
                {'document_id': document.id, 'status': 'verified'}
            )
            
        except Exception as e:
            logger.error(f"Error verifying document: {str(e)}", exc_info=True)
            raise
    
    @action(detail=True, methods=['post'])
    @handle_vendor_api_errors
    def reject(self, request, pk=None):
        """Reject a document with audit logging."""
        try:
            document = self.get_object()
            
            # Check permissions
            if not rbac_manager.has_permission(request.user, 'business_partners.can_verify_vendor_documents'):
                return create_error_response(
                    'You don\'t have permission to reject documents',
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            # Get rejection reason
            rejection_reason = request.data.get('reason')
            if not rejection_reason:
                return create_validation_error_response(
                    'Rejection reason is required',
                    {'reason': ['This field is required']}
                )
            
            # Update status
            old_status = document.status
            document.status = 'rejected'
            document.verified_by = request.user
            document.verified_at = timezone.now()
            document.verification_notes = rejection_reason
            document.save()
            
            # Log the action
            VendorAuditLogger.log_document_rejection(
                request.user,
                document.vendor,
                document,
                old_status,
                'rejected',
                rejection_reason,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            return create_success_response(
                'Document rejected successfully',
                {'document_id': document.id, 'status': 'rejected', 'reason': rejection_reason}
            )
            
        except Exception as e:
            logger.error(f"Error rejecting document: {str(e)}", exc_info=True)
            raise
    
    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class VendorPerformanceAnalyticsViewSet(viewsets.ViewSet):
    """
    ViewSet for vendor performance analytics and reporting.
    """
    permission_classes = [IsVendorManager]
    
    @action(detail=False, methods=['get'])
    @handle_vendor_api_errors
    def overall_performance(self, request):
        """Get overall performance analytics for all vendors."""
        try:
            # Check permissions
            if not rbac_manager.has_permission(request.user, 'business_partners.can_view_vendor_analytics'):
                return create_error_response(
                    'You don\'t have permission to view vendor analytics',
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            # Get date range
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            if not start_date or not end_date:
                # Default to last 30 days
                end_date = timezone.now().date()
                start_date = end_date - timedelta(days=30)
            
            # Get all active vendors
            vendors = BusinessPartner.objects.filter(type='vendor', status='active')
            
            # Calculate performance metrics for each vendor
            analyzer = VendorPerformanceAnalyzer()
            performance_data = []
            
            for vendor in vendors:
                metrics = analyzer.analyze_vendor_performance(vendor, start_date, end_date)
                performance_data.append({
                    'vendor_id': vendor.id,
                    'vendor_name': vendor.name,
                    'metrics': metrics
                })
            
            # Calculate overall statistics
            overall_stats = {
                'total_vendors': len(performance_data),
                'average_performance': sum(p['metrics']['overall_score'] for p in performance_data) / len(performance_data) if performance_data else 0,
                'top_performers': sorted(performance_data, key=lambda x: x['metrics']['overall_score'], reverse=True)[:5],
                'underperformers': sorted(performance_data, key=lambda x: x['metrics']['overall_score'])[:5]
            }
            
            # Log the action
            VendorAuditLogger.log_analytics_view(
                request.user,
                'overall_performance',
                start_date,
                end_date,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            return create_success_response(
                'Overall performance analytics retrieved successfully',
                {
                    'period_start': start_date,
                    'period_end': end_date,
                    'overall_stats': overall_stats,
                    'vendor_performance': performance_data
                }
            )
            
        except Exception as e:
            logger.error(f"Error retrieving overall performance analytics: {str(e)}", exc_info=True)
            raise
    
    @action(detail=False, methods=['get'])
    @handle_vendor_api_errors
    def vendor_rankings(self, request):
        """Get vendor rankings based on performance metrics."""
        try:
            # Check permissions
            if not rbac_manager.has_permission(request.user, 'business_partners.can_view_vendor_analytics'):
                return create_error_response(
                    'You don\'t have permission to view vendor rankings',
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            # Get parameters
            metric = request.query_params.get('metric', 'overall_score')
            period = request.query_params.get('period', '30d')
            limit = int(request.query_params.get('limit', 10))
            
            # Calculate date range based on period
            end_date = timezone.now().date()
            if period == '7d':
                start_date = end_date - timedelta(days=7)
            elif period == '30d':
                start_date = end_date - timedelta(days=30)
            elif period == '90d':
                start_date = end_date - timedelta(days=90)
            else:
                start_date = end_date - timedelta(days=30)
            
            # Get vendor rankings
            analyzer = VendorPerformanceAnalyzer()
            rankings = analyzer.get_vendor_rankings(metric, start_date, end_date, limit)
            
            # Log the action
            VendorAuditLogger.log_analytics_view(
                request.user,
                'vendor_rankings',
                start_date,
                end_date,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            return create_success_response(
                'Vendor rankings retrieved successfully',
                {
                    'metric': metric,
                    'period': period,
                    'rankings': rankings
                }
            )
            
        except Exception as e:
            logger.error(f"Error retrieving vendor rankings: {str(e)}", exc_info=True)
            raise
    
    @action(detail=False, methods=['get'])
    @handle_vendor_api_errors
    def performance_trends(self, request):
        """Get performance trends over time."""
        try:
            # Check permissions
            if not rbac_manager.has_permission(request.user, 'business_partners.can_view_vendor_analytics'):
                return create_error_response(
                    'You don\'t have permission to view performance trends',
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            # Get parameters
            vendor_id = request.query_params.get('vendor_id')
            metric = request.query_params.get('metric', 'overall_score')
            period = request.query_params.get('period', '30d')
            
            # Calculate date range
            end_date = timezone.now().date()
            if period == '7d':
                start_date = end_date - timedelta(days=7)
            elif period == '30d':
                start_date = end_date - timedelta(days=30)
            elif period == '90d':
                start_date = end_date - timedelta(days=90)
            else:
                start_date = end_date - timedelta(days=30)
            
            # Get trend data
            analyzer = VendorPerformanceAnalyzer()
            
            if vendor_id:
                # Single vendor trends
                try:
                    vendor = BusinessPartner.objects.get(id=vendor_id, type='vendor')
                    trends = analyzer.get_vendor_trends(vendor, metric, start_date, end_date)
                except BusinessPartner.DoesNotExist:
                    return create_error_response(
                        'Vendor not found',
                        status_code=status.HTTP_404_NOT_FOUND
                    )
            else:
                # Overall trends
                trends = analyzer.get_overall_trends(metric, start_date, end_date)
            
            # Log the action
            VendorAuditLogger.log_analytics_view(
                request.user,
                'performance_trends',
                start_date,
                end_date,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            return create_success_response(
                'Performance trends retrieved successfully',
                {
                    'metric': metric,
                    'period': period,
                    'trends': trends
                }
            )
            
        except Exception as e:
            logger.error(f"Error retrieving performance trends: {str(e)}", exc_info=True)
            raise
    
    @action(detail=False, methods=['get'])
    @handle_vendor_api_errors
    def performance_issues(self, request):
        """Identify vendors with performance issues."""
        try:
            # Check permissions
            if not rbac_manager.has_permission(request.user, 'business_partners.can_view_vendor_analytics'):
                return create_error_response(
                    'You don\'t have permission to view performance issues',
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            # Get parameters
            threshold = float(request.query_params.get('threshold', 70.0))
            period = request.query_params.get('period', '30d')
            
            # Calculate date range
            end_date = timezone.now().date()
            if period == '7d':
                start_date = end_date - timedelta(days=7)
            elif period == '30d':
                start_date = end_date - timedelta(days=30)
            elif period == '90d':
                start_date = end_date - timedelta(days=90)
            else:
                start_date = end_date - timedelta(days=30)
            
            # Identify performance issues
            analyzer = VendorPerformanceAnalyzer()
            issues = analyzer.identify_performance_issues(start_date, end_date, threshold)
            
            # Log the action
            VendorAuditLogger.log_analytics_view(
                request.user,
                'performance_issues',
                start_date,
                end_date,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            return create_success_response(
                'Performance issues identified successfully',
                {
                    'threshold': threshold,
                    'period': period,
                    'issues': issues
                }
            )
            
        except Exception as e:
            logger.error(f"Error identifying performance issues: {str(e)}", exc_info=True)
            raise
    
    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# Import the permission class at the bottom to avoid circular imports
from .permissions import IsVendorManager


# Dashboard API Endpoints
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_vendor_dashboard_stats(request):
    """Get vendor dashboard statistics."""
    try:
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return JsonResponse({
                'error': 'Authentication required',
                'stats': {}
            }, status=401)
        
        # Get vendor profile using the utility function
        from .utils import get_vendor_profile
        vendor_profile = get_vendor_profile(request.user)
        
        if not vendor_profile:
            return JsonResponse({
                'error': 'No vendor profile found',
                'stats': {
                    'total_parts': 0,
                    'active_parts': 0,
                    'featured_parts': 0,
                    'out_of_stock': 0,
                    'low_stock': 0,
                    'below_safety_stock': 0,
                    'reorder_recommendations': 0,
                    'total_inventory_value': 0,
                    'average_price': 0,
                    'inventory_health': 'N/A'
                }
            }, status=404)
        
        # Get vendor's business partner
        vendor_partner = vendor_profile.business_partner
        
        # Get vendor's parts
        vendor_parts = Part.objects.filter(vendor=vendor_partner)
        
        # Calculate statistics
        total_parts = vendor_parts.count()
        active_parts = vendor_parts.filter(is_active=True).count()
        featured_parts = vendor_parts.filter(is_featured=True).count()
        
        # Inventory statistics
        out_of_stock = 0
        low_stock = 0
        below_safety_stock = 0
        reorder_recommendations = 0
        total_inventory_value = Decimal('0.00')
        
        for part in vendor_parts:
            inventory = part.inventory
            if inventory:
                if inventory.quantity == 0:
                    out_of_stock += 1
                elif inventory.quantity <= inventory.reorder_point:
                    low_stock += 1
                
                if inventory.quantity < inventory.safety_stock:
                    below_safety_stock += 1
                
                if inventory.needs_reorder:
                    reorder_recommendations += 1
                
                total_inventory_value += inventory.quantity * part.price
        
        # Calculate average price
        average_price = vendor_parts.aggregate(
            avg_price=Avg('price')
        )['avg_price'] or Decimal('0.00')
        
        # Inventory health calculation
        if total_parts > 0:
            healthy_percentage = ((total_parts - out_of_stock - low_stock) / total_parts) * 100
            if healthy_percentage >= 80:
                inventory_health = 'Excellent'
            elif healthy_percentage >= 60:
                inventory_health = 'Good'
            elif healthy_percentage >= 40:
                inventory_health = 'Fair'
            else:
                inventory_health = 'Poor'
        else:
            inventory_health = 'N/A'
        
        stats = {
            'total_parts': total_parts,
            'active_parts': active_parts,
            'featured_parts': featured_parts,
            'out_of_stock': out_of_stock,
            'low_stock': low_stock,
            'below_safety_stock': below_safety_stock,
            'reorder_recommendations': reorder_recommendations,
            'total_inventory_value': float(total_inventory_value),
            'average_price': float(average_price),
            'inventory_health': inventory_health
        }
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Error fetching stats: {str(e)}',
            'stats': {}
        }, status=500)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_recent_orders(request):
    """Get recent orders for the vendor."""
    try:
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return JsonResponse({
                'error': 'Authentication required',
                'orders': []
            }, status=401)
        
        # Get vendor profile using the utility function
        from .utils import get_vendor_profile
        vendor_profile = get_vendor_profile(request.user)
        
        if not vendor_profile:
            return JsonResponse({
                'error': 'No vendor profile found',
                'orders': []
            }, status=404)
        
        # Get vendor's business partner
        vendor_partner = vendor_profile.business_partner
        
        # Get recent orders (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        recent_orders = Order.objects.filter(
            items__part__vendor=vendor_partner,
            created_at__gte=thirty_days_ago
        ).distinct().order_by('-created_at')[:10]
        
        orders_data = []
        for order in recent_orders:
            order_items = order.items.filter(part__vendor=vendor_partner)
            total_items = order_items.count()
            
            orders_data.append({
                'id': order.id,
                'order_number': order.order_number,
                'customer_name': order.customer_name or 'Guest Customer',
                'customer_email': order.customer_email or order.guest_email or 'N/A',
                'status': order.status,
                'total_price': float(order.total_price),
                'total_items': total_items,
                'created_at': order.created_at.strftime('%Y-%m-%d %H:%M'),
                'status_display': order.get_status_display(),
                'tracking_number': order.tracking_number or ''
            })
        
        return JsonResponse({
            'success': True,
            'orders': orders_data
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Error fetching orders: {str(e)}',
            'orders': []
        }, status=500)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_top_products(request):
    """Get top selling products for the vendor."""
    try:
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return JsonResponse({
                'error': 'Authentication required',
                'products': []
            }, status=401)
        
        # Get vendor profile using the utility function
        from .utils import get_vendor_profile
        vendor_profile = get_vendor_profile(request.user)
        
        if not vendor_profile:
            return JsonResponse({
                'error': 'No vendor profile found',
                'products': []
            }, status=404)
        
        # Get vendor's business partner
        vendor_partner = vendor_profile.business_partner
        
        # Get top products by sales (last 90 days)
        ninety_days_ago = timezone.now() - timedelta(days=90)
        
        top_products = Part.objects.filter(
            vendor=vendor_partner,
            order_items__order__created_at__gte=ninety_days_ago
        ).annotate(
            total_sold=Sum('order_items__quantity'),
            total_revenue=Sum('order_items__price')
        ).order_by('-total_sold')[:5]
        
        products_data = []
        for product in top_products:
            # Calculate growth (compare last 30 days vs previous 30 days)
            last_30_days = timezone.now() - timedelta(days=30)
            previous_30_days = last_30_days - timedelta(days=30)
            
            current_period_sales = OrderItem.objects.filter(
                part=product,
                order__created_at__gte=last_30_days,
                order__status__in=['delivered', 'shipped']
            ).aggregate(total_sold=Sum('quantity'))['total_sold'] or 0
            
            previous_period_sales = OrderItem.objects.filter(
                part=product,
                order__created_at__gte=previous_30_days,
                order__created_at__lt=last_30_days,
                order__status__in=['delivered', 'shipped']
            ).aggregate(total_sold=Sum('quantity'))['total_sold'] or 0
            
            # Calculate growth percentage
            if previous_period_sales > 0:
                growth = ((current_period_sales - previous_period_sales) / previous_period_sales) * 100
            else:
                growth = 100 if current_period_sales > 0 else 0
            
            products_data.append({
                'id': product.id,
                'name': product.name,
                'part_number': product.part_number,
                'price': float(product.price),
                'total_sold': product.total_sold or 0,
                'total_revenue': float(product.total_revenue or 0),
                'growth': round(growth, 1),
                'stock_status': product.inventory.get_stock_status_display() if hasattr(product, 'inventory') else 'Unknown',
                'image_url': product.images.first().image.url if product.images.exists() else ''
            })
        
        return JsonResponse({
            'success': True,
            'products': products_data
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Error fetching top products: {str(e)}',
            'products': []
        }, status=500)


def get_sales_performance(request):
    """Get sales performance data for charts."""
    try:
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return JsonResponse({
                'error': 'Authentication required',
                'chart_data': {'labels': [], 'data': []}
            }, status=401)
        
        # Get vendor profile using the utility function
        from .utils import get_vendor_profile
        vendor_profile = get_vendor_profile(request.user)
        
        if not vendor_profile:
            return JsonResponse({
                'error': 'No vendor profile found',
                'chart_data': {'labels': [], 'data': []}
            }, status=404)
        
        # Get vendor's business partner
        vendor_partner = vendor_profile.business_partner
        
        # Get sales data for last 12 months
        today = timezone.now()
        months_data = []
        
        for i in range(11, -1, -1):
            month_start = today.replace(day=1) - timedelta(days=i*30)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            monthly_sales = OrderItem.objects.filter(
                part__vendor=vendor_partner,
                order__created_at__gte=month_start,
                order__created_at__lte=month_end,
                order__status__in=['delivered', 'shipped']
            ).aggregate(
                total_revenue=Sum('price'),
                total_orders=Count('order', distinct=True)
            )
            
            months_data.append({
                'month': month_start.strftime('%b %Y'),
                'revenue': float(monthly_sales['total_revenue'] or 0),
                'orders': monthly_sales['total_orders'] or 0
            })
        
        return JsonResponse({
            'success': True,
            'chart_data': {
                'labels': [item['month'] for item in months_data],
                'revenue': [item['revenue'] for item in months_data],
                'orders': [item['orders'] for item in months_data]
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Error fetching sales performance: {str(e)}',
            'chart_data': {'labels': [], 'data': []}
        }, status=500)


def get_notifications(request):
    """Get notifications for the vendor."""
    try:
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return JsonResponse({
                'error': 'Authentication required',
                'notifications': []
            }, status=401)
        
        # Get vendor profile using the utility function
        from .utils import get_vendor_profile
        vendor_profile = get_vendor_profile(request.user)
        
        if not vendor_profile:
            return JsonResponse({
                'error': 'No vendor profile found',
                'notifications': []
            }, status=404)
        
        # Get vendor's business partner
        vendor_partner = vendor_profile.business_partner
        
        # Get recent reorder notifications
        recent_notifications = ReorderNotification.objects.filter(
            part__vendor=vendor_partner,
            is_active=True
        ).order_by('-created_at')[:10]
        
        notifications_data = []
        for notification in recent_notifications:
            notifications_data.append({
                'id': notification.id,
                'message': notification.message,
                'part_name': notification.part.name,
                'part_number': notification.part.part_number,
                'current_stock': notification.part.inventory.quantity if hasattr(notification.part, 'inventory') else 0,
                'reorder_point': notification.part.inventory.reorder_point if hasattr(notification.part, 'inventory') else 0,
                'priority': notification.priority,
                'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M'),
                'is_read': notification.is_read
            })
        
        return JsonResponse({
            'success': True,
            'notifications': notifications_data
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Error fetching notifications: {str(e)}',
            'notifications': []
        }, status=500)


def get_recent_customers(request):
    """Get recent customers for the vendor."""
    try:
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return JsonResponse({
                'error': 'Authentication required',
                'customers': []
            }, status=401)
        
        # Get vendor profile using the utility function
        from .utils import get_vendor_profile
        vendor_profile = get_vendor_profile(request.user)
        
        if not vendor_profile:
            return JsonResponse({
                'error': 'No vendor profile found',
                'customers': []
            }, status=404)
        
        # Get vendor's business partner
        vendor_partner = vendor_profile.business_partner
        
        # Get recent customers (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # Get distinct customers who ordered from this vendor
        recent_orders = Order.objects.filter(
            items__part__vendor=vendor_partner,
            created_at__gte=thirty_days_ago,
            status__in=['delivered', 'shipped', 'processing']
        ).select_related('customer').distinct()[:10]
        
        customers_data = []
        for order in recent_orders:
            if order.customer:  # Skip guest orders
                customer = order.customer
                # Count total orders from this customer
                order_count = Order.objects.filter(
                    customer=customer,
                    items__part__vendor=vendor_partner,
                    status__in=['delivered', 'shipped', 'processing']
                ).count()
                
                customers_data.append({
                    'id': customer.id,
                    'name': f"{customer.first_name} {customer.last_name}".strip() or customer.username,
                    'initials': f"{customer.first_name[:1]}{customer.last_name[:1]}" if customer.first_name and customer.last_name else customer.username[:2].upper(),
                    'email': customer.email,
                    'order_count': order_count,
                    'joined_at': customer.date_joined.strftime('%Y-%m-%d %H:%M')
                })
        
        return JsonResponse({
            'success': True,
            'customers': customers_data
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Error fetching recent customers: {str(e)}',
            'customers': []
        }, status=500)


def get_low_stock_items(request):
    """Get low stock items for the vendor."""
    try:
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return JsonResponse({
                'error': 'Authentication required',
                'items': []
            }, status=401)
        
        # Get vendor profile using the utility function
        from .utils import get_vendor_profile
        vendor_profile = get_vendor_profile(request.user)
        
        if not vendor_profile:
            return JsonResponse({
                'error': 'No vendor profile found',
                'items': []
            }, status=404)
        
        # Get vendor's business partner
        vendor_partner = vendor_profile.business_partner
        
        # Get low stock items
        low_stock_items = []
        
        # Get parts with inventory below reorder point
        parts_with_inventory = Part.objects.filter(
            vendor=vendor_partner,
            inventory__isnull=False
        ).select_related('inventory')
        
        for part in parts_with_inventory:
            inventory = part.inventory
            if inventory.quantity <= inventory.reorder_point:
                # Determine alert level
                if inventory.quantity == 0:
                    level = 'critical'
                elif inventory.quantity <= inventory.reorder_point * 0.5:
                    level = 'critical'
                elif inventory.quantity <= inventory.reorder_point:
                    level = 'low'
                else:
                    level = 'warning'
                
                low_stock_items.append({
                    'id': part.id,
                    'name': part.name,
                    'part_number': part.part_number,
                    'stock_left': inventory.quantity,
                    'reorder_point': inventory.reorder_point,
                    'level': level
                })
        
        # Sort by urgency (critical first)
        low_stock_items.sort(key=lambda x: (x['level'] != 'critical', x['stock_left']))
        
        return JsonResponse({
            'success': True,
            'items': low_stock_items[:10]  # Return top 10
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Error fetching low stock items: {str(e)}',
            'items': []
        }, status=500)


# Import login_required at the bottom to avoid circular imports
from django.contrib.auth.decorators import login_required