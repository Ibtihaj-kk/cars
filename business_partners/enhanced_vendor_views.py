"""
Enhanced Vendor Registration & Management Views
Implements comprehensive vendor lifecycle management with state machine
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, UpdateView, View
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.urls import reverse_lazy
import json
import logging

from .models import VendorApplication, BusinessPartner, VendorProfile
from .workflow_engine import (
    VendorWorkflowState, VendorWorkflowAuditLog, VendorComplianceCheck,
    VendorPriorityQueue, VendorStatus
)
from .forms import VendorApplicationReviewForm, VendorComplianceOverrideForm

logger = logging.getLogger(__name__)


class AdminVendorDashboardView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Comprehensive admin dashboard for vendor management"""
    
    model = VendorWorkflowState
    template_name = 'business_partners/admin_vendor_dashboard.html'
    context_object_name = 'vendor_states'
    paginate_by = 20
    
    def test_func(self):
        """Check if user is admin"""
        return self.request.user.is_staff or self.request.user.groups.filter(name='Admin').exists()
    
    def get_queryset(self):
        """Filter and order vendor states"""
        queryset = VendorWorkflowState.objects.select_related(
            'vendor_application',
            'vendor_application__user'
        ).prefetch_related(
            'compliance_checks',
            'priority_queue_entries'
        )
        
        # Apply filters from request
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(current_status=status_filter)
        
        priority_filter = self.request.GET.get('priority')
        if priority_filter:
            queryset = queryset.filter(
                priority_queue_entries__priority__gte=int(priority_filter),
                priority_queue_entries__is_resolved=False
            ).distinct()
        
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                models.Q(vendor_application__company_name__icontains=search_query) |
                models.Q(vendor_application__application_id__icontains=search_query) |
                models.Q(vendor_application__user__email__icontains=search_query)
            )
        
        # Order by priority and creation date
        return queryset.order_by('-priority_queue_entries__priority', '-created_at')
    
    def get_context_data(self, **kwargs):
        """Add additional context for dashboard"""
        context = super().get_context_data(**kwargs)
        
        # Get statistics
        context['total_vendors'] = VendorWorkflowState.objects.count()
        context['pending_reviews'] = VendorWorkflowState.objects.filter(
            current_status=VendorStatus.PENDING.value
        ).count()
        context['under_review'] = VendorWorkflowState.objects.filter(
            current_status=VendorStatus.UNDER_REVIEW.value
        ).count()
        context['escalated_cases'] = VendorWorkflowState.objects.filter(
            escalation_level__gt=0
        ).count()
        context['high_priority'] = VendorPriorityQueue.objects.filter(
            priority__gte=4,
            is_resolved=False
        ).count()
        
        # Recent activity
        context['recent_activity'] = VendorWorkflowAuditLog.objects.select_related(
            'workflow_state',
            'performed_by'
        ).order_by('-created_at')[:10]
        
        # Status distribution
        context['status_distribution'] = self._get_status_distribution()
        
        return context
    
    def _get_status_distribution(self):
        """Get distribution of vendor statuses"""
        from django.db.models import Count
        
        distribution = VendorWorkflowState.objects.values('current_status').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return [
            {
                'status': item['current_status'],
                'count': item['count'],
                'label': dict(VendorWorkflowState.STATUS_CHOICES).get(
                    item['current_status'], item['current_status']
                )
            }
            for item in distribution
        ]


class VendorApplicationReviewView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """Detailed vendor application review interface"""
    
    model = VendorApplication
    template_name = 'business_partners/vendor_application_review.html'
    context_object_name = 'application'
    
    def test_func(self):
        """Check if user can review vendor applications"""
        return self.request.user.is_staff or self.request.user.groups.filter(
            name__in=['Admin', 'VendorReviewer']
        ).exists()
    
    def get_context_data(self, **kwargs):
        """Add review context"""
        context = super().get_context_data(**kwargs)
        
        application = self.get_object()
        
        # Get or create workflow state
        workflow_state, created = VendorWorkflowState.objects.get_or_create(
            vendor_application=application
        )
        
        context['workflow_state'] = workflow_state
        context['compliance_checks'] = VendorComplianceCheck.objects.filter(
            workflow_state=workflow_state
        ).order_by('-created_at')
        
        context['audit_logs'] = VendorWorkflowAuditLog.objects.filter(
            workflow_state=workflow_state
        ).select_related('performed_by').order_by('-created_at')
        
        context['review_form'] = VendorApplicationReviewForm()
        context['compliance_override_form'] = VendorComplianceOverrideForm()
        
        # Calculate completion percentage
        context['completion_percentage'] = application.calculate_completion_percentage()
        
        # Performance metrics if vendor is active
        if workflow_state.current_status == VendorStatus.ACTIVE.value:
            context['performance_metrics'] = self._get_performance_metrics(application)
        
        return context
    
    def _get_performance_metrics(self, application):
        """Get performance metrics for active vendor"""
        # Placeholder - would integrate with actual performance data
        return {
            'fulfillment_rate': 95.0,
            'customer_satisfaction': 4.5,
            'on_time_delivery': 88.0,
            'quality_score': 92.0,
            'total_orders': 150,
            'revenue_generated': 125000.0,
            'average_response_time': 2.5,  # hours
        }
    
    def post(self, request, *args, **kwargs):
        """Handle review actions"""
        application = self.get_object()
        action = request.POST.get('action')
        
        try:
            with transaction.atomic():
                workflow_state = VendorWorkflowState.objects.get(
                    vendor_application=application
                )
                
                if action == 'approve':
                    self._approve_application(application, workflow_state)
                elif action == 'reject':
                    self._reject_application(application, workflow_state)
                elif action == 'request_info':
                    self._request_additional_info(application, workflow_state)
                elif action == 'escalate':
                    self._escalate_application(application, workflow_state)
                elif action == 'override_compliance':
                    self._override_compliance_check(application, workflow_state)
                
                messages.success(request, f"Application {action}d successfully.")
                
        except Exception as e:
            logger.error(f"Error processing review action: {str(e)}")
            messages.error(request, f"Error processing action: {str(e)}")
        
        return redirect('business_partners:vendor_application_review', pk=application.pk)
    
    def _approve_application(self, application, workflow_state):
        """Approve vendor application"""
        notes = self.request.POST.get('review_notes', '')
        
        # Update application status
        application.status = 'approved'
        application.reviewer = self.request.user
        application.review_notes = notes
        application.reviewed_at = timezone.now()
        application.save()
        
        # Transition workflow state
        workflow_state.transition_to(
            VendorStatus.APPROVED.value,
            user=self.request.user,
            reason="Application approved after review",
            notes=notes
        )
        
        # Create business partner and vendor profile
        business_partner = self._create_business_partner(application)
        vendor_profile = self._create_vendor_profile(application, business_partner)
        
        # Resolve any priority queue entries
        VendorPriorityQueue.objects.filter(
            workflow_state=workflow_state,
            is_resolved=False
        ).update(
            is_resolved=True,
            resolved_by=self.request.user,
            resolved_at=timezone.now()
        )
        
        logger.info(f"Vendor application {application.application_id} approved by {self.request.user}")
    
    def _reject_application(self, application, workflow_state):
        """Reject vendor application"""
        rejection_reason = self.request.POST.get('rejection_reason', '')
        notes = self.request.POST.get('review_notes', '')
        
        application.status = 'rejected'
        application.reviewer = self.request.user
        application.rejection_reason = rejection_reason
        application.review_notes = notes
        application.reviewed_at = timezone.now()
        application.save()
        
        workflow_state.transition_to(
            VendorStatus.REJECTED.value,
            user=self.request.user,
            reason=rejection_reason,
            notes=notes
        )
        
        # Resolve priority queue entries
        VendorPriorityQueue.objects.filter(
            workflow_state=workflow_state,
            is_resolved=False
        ).update(
            is_resolved=True,
            resolved_by=self.request.user,
            resolved_at=timezone.now()
        )
        
        logger.info(f"Vendor application {application.application_id} rejected by {self.request.user}")
    
    def _request_additional_info(self, application, workflow_state):
        """Request additional information from vendor"""
        required_info = self.request.POST.get('required_info', '')
        
        workflow_state.transition_to(
            VendorStatus.REQUIRES_INFO.value,
            user=self.request.user,
            reason="Additional information required",
            notes=required_info
        )
        
        # Create priority queue entry
        VendorPriorityQueue.objects.create(
            workflow_state=workflow_state,
            queue_type='new_application',
            priority=2,
            flag_reason=f"Additional information requested: {required_info}",
            auto_flagged=False
        )
        
        logger.info(f"Additional information requested for application {application.application_id}")
    
    def _escalate_application(self, application, workflow_state):
        """Escalate application for additional review"""
        escalation_reason = self.request.POST.get('escalation_reason', '')
        escalation_level = int(self.request.POST.get('escalation_level', 1))
        
        # Get escalation target user (would be based on escalation matrix)
        escalation_target = self._get_escalation_target(escalation_level)
        
        workflow_state.escalate_case(
            user=escalation_target,
            reason=escalation_reason,
            level=escalation_level
        )
        
        # Create priority queue entry
        VendorPriorityQueue.objects.create(
            workflow_state=workflow_state,
            queue_type='escalated_review',
            priority=4,
            flag_reason=f"Escalated to level {escalation_level}: {escalation_reason}",
            assigned_to=escalation_target,
            auto_flagged=False
        )
        
        logger.info(f"Application {application.application_id} escalated to level {escalation_level}")
    
    def _override_compliance_check(self, application, workflow_state):
        """Override a failed compliance check"""
        check_id = self.request.POST.get('check_id')
        override_reason = self.request.POST.get('override_reason', '')
        
        compliance_check = VendorComplianceCheck.objects.get(
            id=check_id,
            workflow_state=workflow_state
        )
        
        compliance_check.manually_overridden = True
        compliance_check.override_reason = override_reason
        compliance_check.overridden_by = self.request.user
        compliance_check.save()
        
        # Create audit log
        VendorWorkflowAuditLog.objects.create(
            workflow_state=workflow_state,
            action_type='compliance_check',
            performed_by=self.request.user,
            reason=f"Compliance check overridden: {override_reason}",
            notes=f"Check type: {compliance_check.get_check_type_display()}"
        )
        
        logger.warning(f"Compliance check {check_id} overridden by {self.request.user}")
    
    def _create_business_partner(self, application):
        """Create business partner from approved application"""
        business_partner = BusinessPartner.objects.create(
            bp_number=BusinessPartner.generate_bp_number(),
            bp_type='company',
            name=application.company_name,
            slug=BusinessPartner.generate_slug(application.company_name),
            legal_name=application.company_name,
            tax_id=application.legal_identifier,
            registration_number=application.commercial_registration_number,
            website=application.website or '',
            description=application.description or '',
            is_active=True,
            created_by=application.user
        )
        
        # Add vendor role
        from .models import BusinessPartnerRole
        BusinessPartnerRole.objects.create(
            business_partner=business_partner,
            role_type='vendor',
            is_primary=True
        )
        
        # Create contact info
        from .models import ContactInfo
        ContactInfo.objects.create(
            business_partner=business_partner,
            contact_person=application.contact_person,
            title=application.contact_person_title,
            email=application.email,
            phone=application.phone,
            is_primary=True
        )
        
        # Create address
        from .models import Address
        Address.objects.create(
            business_partner=business_partner,
            street=application.street_address,
            city=application.city,
            state_province=application.state_province,
            postal_code=application.postal_code,
            country=application.country,
            address_type='headquarters',
            is_primary=True
        )
        
        return business_partner
    
    def _create_vendor_profile(self, application, business_partner):
        """Create vendor profile from approved application"""
        vendor_profile = VendorProfile.objects.create(
            business_partner=business_partner,
            user=application.user,
            expected_monthly_volume=application.expected_monthly_volume,
            years_in_business=application.years_in_business,
            product_categories=application.product_categories or '',
            references=application.references or '',
            is_verified=True,
            verification_date=timezone.now(),
            verified_by=self.request.user
        )
        
        return vendor_profile
    
    def _get_escalation_target(self, level):
        """Get escalation target based on level"""
        # Placeholder - would implement proper escalation matrix
        # Level 1: Senior reviewer
        # Level 2: Manager
        # Level 3: Director
        # Level 4+: Executive
        
        if level == 1:
            # Get senior reviewer
            return User.objects.filter(
                groups__name='SeniorReviewer'
            ).first() or self.request.user
        elif level == 2:
            # Get manager
            return User.objects.filter(
                groups__name='VendorManager'
            ).first() or self.request.user
        else:
            # Get admin
            return User.objects.filter(
                is_staff=True
            ).first() or self.request.user


class VendorPerformanceDashboardView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Vendor performance monitoring dashboard"""
    
    def test_func(self):
        """Check if user is admin"""
        return self.request.user.is_staff or self.request.user.groups.filter(
            name__in=['Admin', 'VendorManager']
        ).exists()
    
    def get(self, request):
        """Render performance dashboard"""
        # Get active vendors
        active_vendors = VendorWorkflowState.objects.filter(
            current_status=VendorStatus.ACTIVE.value
        ).select_related('vendor_application')
        
        # Calculate performance metrics
        performance_data = []
        for vendor_state in active_vendors:
            metrics = self._calculate_vendor_metrics(vendor_state)
            performance_data.append({
                'vendor': vendor_state.vendor_application,
                'workflow_state': vendor_state,
                'metrics': metrics
            })
        
        # Sort by performance score
        performance_data.sort(key=lambda x: x['metrics']['overall_score'], reverse=True)
        
        context = {
            'performance_data': performance_data,
            'total_active_vendors': len(performance_data),
            'average_performance': self._calculate_average_performance(performance_data),
            'low_performing_vendors': [
                data for data in performance_data 
                if data['metrics']['overall_score'] < 70
            ]
        }
        
        return render(request, 'business_partners/vendor_performance_dashboard.html', context)
    
    def _calculate_vendor_metrics(self, vendor_state):
        """Calculate comprehensive vendor performance metrics"""
        # Placeholder implementation - would integrate with actual data
        import random
        
        return {
            'fulfillment_rate': random.uniform(85, 98),
            'customer_satisfaction': random.uniform(4.0, 4.8),
            'on_time_delivery': random.uniform(80, 95),
            'quality_score': random.uniform(85, 95),
            'revenue_generated': random.uniform(50000, 500000),
            'order_count': random.randint(50, 500),
            'response_time_hours': random.uniform(1, 8),
            'complaint_rate': random.uniform(0.1, 2.0),
            'overall_score': random.uniform(75, 95)
        }
    
    def _calculate_average_performance(self, performance_data):
        """Calculate average performance across all vendors"""
        if not performance_data:
            return 0
        
        total_score = sum(
            data['metrics']['overall_score'] 
            for data in performance_data
        )
        
        return total_score / len(performance_data)


class VendorRevenueTrackingView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Revenue tracking and analytics for vendors"""
    
    def test_func(self):
        """Check if user is admin"""
        return self.request.user.is_staff or self.request.user.groups.filter(
            name__in=['Admin', 'Finance']
        ).exists()
    
    def get(self, request):
        """Render revenue tracking dashboard"""
        from datetime import datetime, timedelta
        
        # Get date range from request
        date_from = request.GET.get('date_from', 
            (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        date_to = request.GET.get('date_to', datetime.now().strftime('%Y-%m-%d'))
        
        category_filter = request.GET.get('category')
        region_filter = request.GET.get('region')
        
        # Get revenue data (placeholder)
        revenue_data = self._get_revenue_data(date_from, date_to, category_filter, region_filter)
        
        context = {
            'revenue_data': revenue_data,
            'date_from': date_from,
            'date_to': date_to,
            'total_revenue': sum(data['revenue'] for data in revenue_data),
            'total_orders': sum(data['orders'] for data in revenue_data),
            'average_order_value': 0,
            'top_performers': sorted(revenue_data, key=lambda x: x['revenue'], reverse=True)[:10]
        }
        
        if context['total_orders'] > 0:
            context['average_order_value'] = context['total_revenue'] / context['total_orders']
        
        return render(request, 'business_partners/vendor_revenue_tracking.html', context)
    
    def _get_revenue_data(self, date_from, date_to, category_filter, region_filter):
        """Get revenue data for specified filters"""
        # Placeholder implementation
        import random
        from datetime import datetime
        
        active_vendors = VendorWorkflowState.objects.filter(
            current_status=VendorStatus.ACTIVE.value
        ).select_related('vendor_application')[:20]
        
        revenue_data = []
        for vendor_state in active_vendors:
            revenue_data.append({
                'vendor': vendor_state.vendor_application,
                'revenue': random.uniform(10000, 100000),
                'orders': random.randint(10, 200),
                'category': random.choice(['Electronics', 'Automotive', 'Industrial']),
                'region': random.choice(['Riyadh', 'Jeddah', 'Dammam']),
                'growth_rate': random.uniform(-10, 25)
            })
        
        return revenue_data