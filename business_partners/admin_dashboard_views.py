from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Q, Count, Case, When, IntegerField, Avg, Sum, F
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.views.generic import ListView, DetailView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import timedelta, datetime

from business_partners.models import VendorApplication, BusinessPartner, BusinessPartnerRole
from .workflow_engine import (
    VendorStatus, VendorWorkflowState, VendorWorkflowAuditLog, 
    VendorComplianceCheck, VendorPriorityQueue
)
from .enhanced_forms import (
    VendorApplicationReviewForm, VendorComplianceOverrideForm,
    VendorSearchForm, VendorBulkActionForm
)


class AdminVendorDashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Comprehensive admin dashboard for vendor management"""
    
    template_name = 'business_partners/admin_vendor_dashboard.html'
    permission_required = 'business_partners.can_manage_vendors'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Vendor Management Dashboard'
        
        # Get current date for calculations
        today = timezone.now().date()
        last_30_days = today - timedelta(days=30)
        
        # Vendor Application Statistics
        context['application_stats'] = {
            'total_pending': VendorApplication.objects.filter(status='pending').count(),
            'total_under_review': VendorApplication.objects.filter(status='under_review').count(),
            'total_approved': VendorApplication.objects.filter(status='approved').count(),
            'total_rejected': VendorApplication.objects.filter(status='rejected').count(),
            'total_requires_changes': VendorApplication.objects.filter(status='requires_changes').count(),
        }
        
        # Priority Queue Statistics
        context['priority_queue_stats'] = {
            'urgent': VendorPriorityQueue.objects.filter(priority='urgent', resolved=False).count(),
            'high': VendorPriorityQueue.objects.filter(priority='high', resolved=False).count(),
            'medium': VendorPriorityQueue.objects.filter(priority='medium', resolved=False).count(),
            'low': VendorPriorityQueue.objects.filter(priority='low', resolved=False).count(),
            'assigned_to_me': VendorPriorityQueue.objects.filter(
                assigned_to=self.request.user, resolved=False
            ).count(),
        }
        
        # Recent Applications (last 7 days)
        recent_applications = VendorApplication.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).order_by('-created_at')[:10]
        context['recent_applications'] = recent_applications
        
        # High Priority Applications (flagged for urgent review)
        high_priority_applications = VendorApplication.objects.filter(
            Q(vendorpriorityqueue__priority__in=['urgent', 'high']) |
            Q(status='pending', created_at__lte=timezone.now() - timedelta(days=3))
        ).distinct().order_by('-created_at')[:10]
        context['high_priority_applications'] = high_priority_applications
        
        # Performance Metrics
        approved_vendors = BusinessPartner.objects.filter(
            businesspartnerrole__role='vendor',
            businesspartnerrole__is_active=True
        )
        
        context['vendor_performance'] = {
            'total_active_vendors': approved_vendors.count(),
            'vendors_added_this_month': approved_vendors.filter(
                created_at__month=today.month, created_at__year=today.year
            ).count(),
            'average_review_time': self.calculate_average_review_time(),
            'compliance_rate': self.calculate_compliance_rate(),
        }
        
        # Document Verification Statistics
        from .document_models import VendorDocument
        context['document_stats'] = {
            'pending_verification': VendorDocument.objects.filter(status='pending').count(),
            'expiring_soon': VendorDocument.objects.filter(
                expiry_date__lte=today + timedelta(days=30),
                status='verified'
            ).count(),
            'expired_documents': VendorDocument.objects.filter(
                expiry_date__lt=today, status='verified'
            ).count(),
        }
        
        # Compliance Alerts
        context['compliance_alerts'] = self.get_compliance_alerts()
        
        # Recent Audit Logs
        context['recent_audit_logs'] = VendorWorkflowAuditLog.objects.select_related(
            'vendor_application', 'performed_by'
        ).order_by('-created_at')[:10]
        
        return context
    
    def calculate_average_review_time(self):
        """Calculate average time to review vendor applications"""
        reviewed_applications = VendorApplication.objects.filter(
            status__in=['approved', 'rejected'],
            reviewed_at__isnull=False,
            submitted_at__isnull=False
        )
        
        if not reviewed_applications.exists():
            return "No data"
        
        total_days = 0
        count = 0
        
        for application in reviewed_applications:
            if application.reviewed_at and application.submitted_at:
                days = (application.reviewed_at - application.submitted_at).days
                total_days += days
                count += 1
        
        if count == 0:
            return "No data"
        
        avg_days = total_days / count
        if avg_days < 1:
            return f"{int(avg_days * 24)} hours"
        elif avg_days < 7:
            return f"{avg_days:.1f} days"
        else:
            return f"{avg_days/7:.1f} weeks"
    
    def calculate_compliance_rate(self):
        """Calculate vendor compliance rate"""
        from .document_models import VendorDocument
        
        total_documents = VendorDocument.objects.filter(
            business_partner__isnull=False
        ).count()
        
        if total_documents == 0:
            return 100
        
        compliant_documents = VendorDocument.objects.filter(
            business_partner__isnull=False,
            status='verified',
            expiry_date__gt=timezone.now().date()
        ).count()
        
        return round((compliant_documents / total_documents) * 100, 1) if total_documents > 0 else 100
    
    def get_compliance_alerts(self):
        """Get compliance alerts for dashboard"""
        alerts = []
        
        # Expiring documents
        from .document_models import VendorDocument
        expiring_docs = VendorDocument.objects.filter(
            expiry_date__lte=timezone.now().date() + timedelta(days=30),
            status='verified'
        ).select_related('business_partner', 'category')[:5]
        
        for doc in expiring_docs:
            alerts.append({
                'type': 'warning',
                'title': f"Document Expiring: {doc.title}",
                'message': f"Document for {doc.business_partner} expires on {doc.expiry_date}",
                'vendor': doc.business_partner,
                'urgency': 'high' if doc.days_until_expiry <= 7 else 'medium'
            })
        
        # Overdue applications
        overdue_apps = VendorApplication.objects.filter(
            status='pending',
            created_at__lte=timezone.now() - timedelta(days=5)
        ).order_by('created_at')[:5]
        
        for app in overdue_apps:
            alerts.append({
                'type': 'info',
                'title': f"Overdue Application: {app.company_name}",
                'message': f"Application pending for {(timezone.now().date() - app.created_at.date()).days} days",
                'vendor': app,
                'urgency': 'high'
            })
        
        return alerts


class VendorApplicationReviewView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detailed view for reviewing vendor applications"""
    
    model = VendorApplication
    template_name = 'business_partners/vendor_application_review.html'
    permission_required = 'business_partners.can_review_vendor_applications'
    context_object_name = 'application'
    
    def get_queryset(self):
        return VendorApplication.objects.select_related('user', 'reviewed_by').prefetch_related(
            'documents', 'vendorpriorityqueue'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"Review Application: {self.object.company_name}"
        
        # Add review form
        context['review_form'] = VendorApplicationReviewForm()
        
        # Add compliance override form if needed
        if self.object.status in ['pending', 'under_review']:
            context['compliance_override_form'] = VendorComplianceOverrideForm()
        
        # Add related documents
        from .document_models import VendorDocument
        context['documents'] = VendorDocument.objects.filter(
            vendor_application=self.object
        ).select_related('category')
        
        # Add audit trail
        context['audit_logs'] = VendorWorkflowAuditLog.objects.filter(
            vendor_application=self.object
        ).select_related('performed_by').order_by('-created_at')
        
        # Add compliance checks
        context['compliance_checks'] = VendorComplianceCheck.objects.filter(
            vendor_application=self.object
        ).order_by('-created_at')
        
        # Add priority information
        context['priority_info'] = self.get_priority_info()
        
        return context
    
    def get_priority_info(self):
        """Get priority information for the application"""
        try:
            priority_queue = self.object.vendorpriorityqueue.get(resolved=False)
            return {
                'priority': priority_queue.priority,
                'reason': priority_queue.reason,
                'flagged_by': priority_queue.flagged_by,
                'flagged_at': priority_queue.flagged_at,
                'assigned_to': priority_queue.assigned_to,
            }
        except VendorPriorityQueue.DoesNotExist:
            return None
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get('action')
        
        if action == 'review':
            return self.handle_review(request)
        elif action == 'compliance_override':
            return self.handle_compliance_override(request)
        elif action == 'escalate':
            return self.handle_escalate(request)
        
        return redirect('business_partners:vendor_application_review', pk=self.object.pk)
    
    def handle_review(self, request):
        """Handle application review actions"""
        form = VendorApplicationReviewForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            notes = form.cleaned_data.get('notes', '')
            
            try:
                if action == 'approve':
                    self.object.approve(request.user, notes)
                    message = f"Application for {self.object.company_name} has been approved."
                    
                    # Resolve priority queue if exists
                    try:
                        priority_queue = self.object.vendorpriorityqueue.get(resolved=False)
                        priority_queue.resolved = True
                        priority_queue.resolved_at = timezone.now()
                        priority_queue.resolved_by = request.user
                        priority_queue.save()
                    except VendorPriorityQueue.DoesNotExist:
                        pass
                    
                elif action == 'reject':
                    reason = form.cleaned_data.get('rejection_reason', '')
                    self.object.reject(request.user, reason, notes)
                    message = f"Application for {self.object.company_name} has been rejected."
                    
                    # Resolve priority queue if exists
                    try:
                        priority_queue = self.object.vendorpriorityqueue.get(resolved=False)
                        priority_queue.resolved = True
                        priority_queue.resolved_at = timezone.now()
                        priority_queue.resolved_by = request.user
                        priority_queue.save()
                    except VendorPriorityQueue.DoesNotExist:
                        pass
                    
                elif action == 'request_info':
                    self.object.request_changes(request.user, 'Additional information required', notes)
                    message = f"Information request sent to {self.object.company_name}."
                    
                elif action == 'escalate':
                    return self.handle_escalate(request)
                
                # Log the action
                VendorWorkflowAuditLog.log_action(
                    vendor_application=self.object,
                    action=action,
                    performed_by=request.user,
                    details=notes
                )
                
                messages.success(request, message)
                return redirect('business_partners:admin_vendor_dashboard')
                
            except Exception as e:
                messages.error(request, f"Error processing application: {str(e)}")
                return redirect('business_partners:vendor_application_review', pk=self.object.pk)
        
        return self.render_to_response(self.get_context_data(review_form=form))
    
    def handle_compliance_override(self, request):
        """Handle compliance override requests"""
        form = VendorComplianceOverrideForm(request.POST)
        if form.is_valid():
            # Create a compliance check record with override flag
            compliance_check = VendorComplianceCheck.objects.create(
                vendor_application=self.object,
                check_type='manual_override',
                status='passed_with_override',
                performed_by=request.user,
                notes=f"Compliance override: {form.cleaned_data['override_reason']}"
            )
            
            # Log the override action
            VendorWorkflowAuditLog.log_action(
                vendor_application=self.object,
                action='compliance_override',
                performed_by=request.user,
                details=form.cleaned_data['override_reason']
            )
            
            messages.success(request, "Compliance override recorded successfully.")
            return redirect('business_partners:vendor_application_review', pk=self.object.pk)
        
        return self.render_to_response(self.get_context_data(compliance_override_form=form))
    
    def handle_escalate(self, request):
        """Handle application escalation"""
        reason = request.POST.get('escalation_reason', '')
        
        # Create or update priority queue entry
        priority_queue, created = VendorPriorityQueue.objects.get_or_create(
            vendor_application=self.object,
            resolved=False,
            defaults={
                'priority': 'high',
                'reason': f"Escalated: {reason}",
                'flagged_by': request.user,
            }
        )
        
        if not created:
            priority_queue.priority = 'high'
            priority_queue.reason = f"Escalated: {reason}"
            priority_queue.save()
        
        # Log the escalation
        VendorWorkflowAuditLog.log_action(
            vendor_application=self.object,
            action='escalated',
            performed_by=request.user,
            details=f"Application escalated: {reason}"
        )
        
        messages.success(request, f"Application escalated to high priority: {reason}")
        return redirect('business_partners:admin_vendor_dashboard')


class VendorPerformanceDashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Dashboard for monitoring vendor performance"""
    
    template_name = 'business_partners/vendor_performance_dashboard.html'
    permission_required = 'business_partners.can_monitor_vendor_performance'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Vendor Performance Dashboard'
        
        # Get date range from request
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from and date_to:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            except ValueError:
                date_from = timezone.now().date() - timedelta(days=30)
                date_to = timezone.now().date()
        else:
            date_from = timezone.now().date() - timedelta(days=30)
            date_to = timezone.now().date()
        
        context['date_range'] = {'from': date_from, 'to': date_to}
        
        # Get active vendors
        active_vendors = BusinessPartner.objects.filter(
            businesspartnerrole__role='vendor',
            businesspartnerrole__is_active=True
        ).distinct()
        
        # Performance metrics by vendor
        vendor_performance = []
        for vendor in active_vendors:
            performance_data = self.get_vendor_performance_data(vendor, date_from, date_to)
            vendor_performance.append({
                'vendor': vendor,
                'performance': performance_data
            })
        
        context['vendor_performance'] = vendor_performance
        
        # Overall performance metrics
        context['overall_metrics'] = self.get_overall_performance_metrics(date_from, date_to)
        
        # Underperforming vendors
        context['underperforming_vendors'] = self.get_underperforming_vendors(date_from, date_to)
        
        return context
    
    def get_vendor_performance_data(self, vendor, date_from, date_to):
        """Get performance data for a specific vendor"""
        # This would integrate with your order/transaction models
        # For now, returning placeholder data structure
        return {
            'total_orders': 0,  # Would come from orders model
            'fulfillment_rate': 0,  # Would be calculated from orders
            'average_rating': 0,  # Would come from reviews/ratings
            'revenue_generated': 0,  # Would come from transactions
            'customer_satisfaction': 0,  # Would be calculated from feedback
        }
    
    def get_overall_performance_metrics(self, date_from, date_to):
        """Get overall performance metrics"""
        return {
            'total_vendors': BusinessPartner.objects.filter(
                businesspartnerrole__role='vendor',
                businesspartnerrole__is_active=True
            ).distinct().count(),
            'active_vendors': 0,  # Would be calculated based on activity
            'total_revenue': 0,  # Would come from transactions
            'average_fulfillment_rate': 0,  # Would be calculated
            'top_performers': [],  # Would be calculated
        }
    
    def get_underperforming_vendors(self, date_from, date_to):
        """Identify underperforming vendors"""
        # This would analyze performance data to identify vendors needing attention
        return []


class VendorRevenueTrackingView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """View for tracking vendor revenue and financial metrics"""
    
    template_name = 'business_partners/vendor_revenue_tracking.html'
    permission_required = 'business_partners.can_track_vendor_revenue'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Vendor Revenue Tracking'
        
        # Get filter parameters
        time_period = self.request.GET.get('period', '30d')
        category = self.request.GET.get('category', '')
        region = self.request.GET.get('region', '')
        
        # Calculate date range based on period
        date_to = timezone.now().date()
        if time_period == '7d':
            date_from = date_to - timedelta(days=7)
        elif time_period == '30d':
            date_from = date_to - timedelta(days=30)
        elif time_period == '90d':
            date_from = date_to - timedelta(days=90)
        elif time_period == '1y':
            date_from = date_to - timedelta(days=365)
        else:
            date_from = date_to - timedelta(days=30)
        
        context['filters'] = {
            'time_period': time_period,
            'category': category,
            'region': region,
            'date_from': date_from,
            'date_to': date_to,
        }
        
        # Revenue data (placeholder - would integrate with transaction models)
        context['revenue_data'] = {
            'total_revenue': 0,
            'revenue_by_vendor': [],
            'revenue_by_category': [],
            'revenue_by_region': [],
            'revenue_trend': [],
            'top_revenue_vendors': [],
        }
        
        return context