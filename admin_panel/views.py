from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.db.models import Q, Count, Avg, Exists, OuterRef, Subquery, F
from django.db import models
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
import json

from listings.models import VehicleListing, ListingStatusLog
from users.models import User
from vehicles.models import Brand, VehicleModel
from business_partners.models import BusinessPartner, BusinessPartnerRole, ContactInfo
from business_partners.models import VendorApplication
from business_partners.document_models import VendorDocument, DocumentVerificationQueue
from django.db.models import Avg, Count, Q, Sum
from datetime import datetime, timedelta
from .payment_models import VendorPayment, CommissionRule, PaymentBatch, PaymentHistory, VendorBalance, PaymentStatus, PaymentMethod
from .messaging_models import AdminMessage, MessageTemplate, VendorNotification, MessageStatus, MessagePriority, MessageCategory
from .models import ActivityLog, ActivityLogType, DashboardWidget
from .utils import (
    log_activity, log_listing_activity, log_bulk_listing_activity,
    log_status_change_activity, log_feature_toggle_activity
)
from .decorators import (
    admin_required, staff_required, can_manage_listings, 
    can_view_analytics, can_view_audit_logs, ajax_admin_required
)
from .session_manager import require_valid_admin_session
from .audit_logger import AdminAuditLogger, audit_admin_action


def is_admin_user(user):
    """Check if user is admin or staff."""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def dashboard_demo_view(request):
    """Public demo version of the dashboard for testing."""
    # Get basic statistics
    total_listings = VehicleListing.objects.count()
    published_listings = VehicleListing.objects.filter(status='published').count()
    pending_listings = VehicleListing.objects.filter(status='pending_review').count()
    featured_listings = VehicleListing.objects.filter(is_featured=True).count()
    
    # Get recent listings
    recent_listings = VehicleListing.objects.select_related('user').order_by('-created_at')[:10]
    
    # Get popular makes
    popular_makes = VehicleListing.objects.filter(status='published').values('make').annotate(
        count=models.Count('make')
    ).order_by('-count')[:10]
    
    context = {
        'total_listings': total_listings,
        'published_listings': published_listings,
        'pending_listings': pending_listings,
        'featured_listings': featured_listings,
        'recent_listings': recent_listings,
        'popular_makes': popular_makes,
        'demo_mode': True,
    }
    
    return render(request, 'admin_panel/dashboard.html', context)

@admin_required(min_role='staff')
@require_valid_admin_session
@audit_admin_action(ActivityLogType.VIEW, "Accessed admin dashboard")
def dashboard_view(request):
    """Main admin dashboard view."""
    # Get dashboard statistics
    total_listings = VehicleListing.objects.count()
    published_listings = VehicleListing.objects.filter(status='published').count()
    pending_listings = VehicleListing.objects.filter(status='pending').count()
    featured_listings = VehicleListing.objects.filter(is_featured=True).count()
    
    # Vendor-specific metrics
    total_vendors = BusinessPartner.objects.filter(type='vendor').count()
    pending_vendors = BusinessPartner.objects.filter(
        type='vendor', 
        status='pending_review'
    ).count()
    approved_vendors = BusinessPartner.objects.filter(
        type='vendor', 
        status='approved'
    ).count()
    rejected_vendors = BusinessPartner.objects.filter(
        type='vendor', 
        status='rejected'
    ).count()
    
    # Vendor Application metrics
    total_applications = VendorApplication.objects.count()
    pending_applications = VendorApplication.objects.filter(status='pending').count()
    under_review_applications = VendorApplication.objects.filter(status='under_review').count()
    approved_applications = VendorApplication.objects.filter(status='approved').count()
    rejected_applications = VendorApplication.objects.filter(status='rejected').count()
    requires_changes_applications = VendorApplication.objects.filter(status='requires_changes').count()
    
    # Vendor Performance metrics
    active_vendors = BusinessPartner.objects.filter(
        type='vendor', 
        status='approved',
        user__is_active=True
    ).count()
    
    # Vendor with listings (simplified - count active vendors)
    vendors_with_listings = BusinessPartner.objects.filter(
        type='vendor',
        status='approved'
    ).count()
    
    # Average vendor rating (placeholder - rating field not on BusinessPartner)
    avg_vendor_rating = 0
    
    # Vendor document verification stats
    total_documents = VendorDocument.objects.count()
    verified_documents = VendorDocument.objects.filter(status='verified').count()
    pending_verification_docs = VendorDocument.objects.filter(status='pending').count()
    rejected_documents = VendorDocument.objects.filter(status='rejected').count()
    
    # Document verification queue
    verification_queue_count = DocumentVerificationQueue.objects.filter(completed_at__isnull=True).count()
    
    # Recent activity
    recent_listings = VehicleListing.objects.select_related('user', 'make', 'model').order_by('-created_at')[:10]
    recent_activities = ActivityLog.objects.select_related('user').order_by('-action_time')[:10]
    
    # Recent vendor applications
    recent_vendors = BusinessPartner.objects.filter(
        type='vendor'
    ).select_related('user').order_by('-created_at')[:5]
    
    # Popular makes
    popular_makes = VehicleListing.objects.filter(status='published').values('make__name').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Status distribution
    status_distribution = VehicleListing.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Vendor status distribution
    vendor_status_distribution = BusinessPartner.objects.filter(
        type='vendor'
    ).values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Monthly listings trend (last 6 months)
    six_months_ago = timezone.now() - timedelta(days=180)
    monthly_data = []
    for i in range(6):
        month_start = six_months_ago + timedelta(days=30*i)
        month_end = month_start + timedelta(days=30)
        count = VehicleListing.objects.filter(
            created_at__gte=month_start,
            created_at__lt=month_end
        ).count()
        monthly_data.append({
            'month': month_start.strftime('%b %Y'),
            'count': count
        })
    
    # Monthly vendor applications trend (last 6 months)
    vendor_monthly_data = []
    for i in range(6):
        month_start = six_months_ago + timedelta(days=30*i)
        month_end = month_start + timedelta(days=30)
        count = BusinessPartner.objects.filter(
            type='vendor',
            created_at__gte=month_start,
            created_at__lt=month_end
        ).count()
        vendor_monthly_data.append({
            'month': month_start.strftime('%b %Y'),
            'count': count
        })
    
    # Get message statistics for navigation
    message_stats = {
        'unread': AdminMessage.objects.filter(is_read=False).count(),
        'total': AdminMessage.objects.count(),
    }
    
    # Payment and commission statistics
    total_payments = VendorPayment.objects.count()
    pending_payments = VendorPayment.objects.filter(status='pending').count()
    completed_payments = VendorPayment.objects.filter(status='completed').count()
    total_commission_earned = VendorPayment.objects.filter(
        status='completed'
    ).aggregate(total=Sum('commission_amount'))['total'] or 0
    
    total_commission_rules = CommissionRule.objects.count()
    active_commission_rules = CommissionRule.objects.filter(is_active=True).count()
    
    # Recent payments
    recent_payments = VendorPayment.objects.select_related('vendor').order_by('-created_at')[:5]
    
    # Vendor balance summary
    total_vendor_balance = VendorBalance.objects.aggregate(total=Sum('current_balance'))['total'] or 0
    
    context = {
        'total_listings': total_listings,
        'published_listings': published_listings,
        'pending_listings': pending_listings,
        'featured_listings': featured_listings,
        'total_vendors': total_vendors,
        'pending_vendors': pending_vendors,
        'approved_vendors': approved_vendors,
        'rejected_vendors': rejected_vendors,
        'total_applications': total_applications,
        'pending_applications': pending_applications,
        'under_review_applications': under_review_applications,
        'approved_applications': approved_applications,
        'rejected_applications': rejected_applications,
        'requires_changes_applications': requires_changes_applications,
        'active_vendors': active_vendors,
        'vendors_with_listings': vendors_with_listings,
        'avg_vendor_rating': avg_vendor_rating,
        'total_documents': total_documents,
        'verified_documents': verified_documents,
        'pending_verification_docs': pending_verification_docs,
        'rejected_documents': rejected_documents,
        'verification_queue_count': verification_queue_count,
        'recent_listings': recent_listings,
        'recent_activities': recent_activities,
        'recent_vendors': recent_vendors,
        'popular_makes': popular_makes,
        'status_distribution': status_distribution,
        'vendor_status_distribution': vendor_status_distribution,
        'monthly_data': monthly_data,
        'vendor_monthly_data': vendor_monthly_data,
        'message_stats': message_stats,
        'total_payments': total_payments,
        'pending_payments': pending_payments,
        'completed_payments': completed_payments,
        'total_commission_earned': total_commission_earned,
        'total_commission_rules': total_commission_rules,
        'active_commission_rules': active_commission_rules,
        'recent_payments': recent_payments,
        'total_vendor_balance': total_vendor_balance,
    }
    
    return render(request, 'admin_panel/dashboard.html', context)


@can_manage_listings
@require_valid_admin_session
@audit_admin_action(ActivityLogType.VIEW, "Accessed listings management")
def listings_management_view(request):
    """Vehicle listings management view with filtering and bulk operations."""
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    make_filter = request.GET.get('make', '')
    featured_filter = request.GET.get('featured', '')
    search_query = request.GET.get('search', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Build queryset
    listings = VehicleListing.objects.select_related('user', 'make', 'model').all()
    
    if status_filter:
        listings = listings.filter(status=status_filter)
    
    if make_filter:
        listings = listings.filter(make_id=make_filter)
    
    if featured_filter == 'true':
        listings = listings.filter(is_featured=True)
    elif featured_filter == 'false':
        listings = listings.filter(is_featured=False)
    
    if search_query:
        listings = listings.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            listings = listings.filter(created_at__date__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            listings = listings.filter(created_at__date__lte=date_to_obj)
        except ValueError:
            pass
    
    # Order by creation date (newest first)
    listings = listings.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(listings, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    makes = Brand.objects.all().order_by('name')
    status_choices = VehicleListing._meta.get_field('status').choices
    
    total_listings = VehicleListing.objects.count()
    published_listings = VehicleListing.objects.filter(status='published').count()
    pending_listings = VehicleListing.objects.filter(status='pending_review').count()
    draft_listings = VehicleListing.objects.filter(status='draft').count()
    featured_listings = VehicleListing.objects.filter(is_featured=True).count()
    sold_listings = VehicleListing.objects.filter(status='sold').count()
    
    context = {
        'page_obj': page_obj,
        'makes': makes,
        'status_choices': status_choices,
        'search': search_query,
        'status_filter': status_filter,
        'make_filter': make_filter,
        'featured_filter': featured_filter,
        'total_listings': total_listings,
        'published_listings': published_listings,
        'pending_listings': pending_listings,
        'draft_listings': draft_listings,
        'featured_listings': featured_listings,
        'sold_listings': sold_listings,
    }
    
    return render(request, 'admin_panel/listings_management.html', context)


@can_manage_listings
@require_valid_admin_session
@require_http_methods(["POST"])
@csrf_exempt
def bulk_update_listings(request):
    """Handle bulk operations on listings."""
    try:
        data = json.loads(request.body)
        action = data.get('action')
        listing_ids = data.get('listing_ids', [])
        
        if not action or not listing_ids:
            return JsonResponse({'success': False, 'error': 'Missing action or listing IDs'})
        
        listings = VehicleListing.objects.filter(id__in=listing_ids)
        updated_count = 0
        
        if action == 'publish':
            updated_count = listings.update(status='published')
            # Log status changes
            for listing in listings:
                ListingStatusLog.objects.create(
                    listing=listing,
                    old_status=listing.status,
                    new_status='published',
                    changed_by=request.user,
                    reason='Bulk publish operation'
                )
        
        elif action == 'unpublish':
            updated_count = listings.update(status='draft')
            for listing in listings:
                ListingStatusLog.objects.create(
                    listing=listing,
                    old_status=listing.status,
                    new_status='draft',
                    changed_by=request.user,
                    reason='Bulk unpublish operation'
                )
        
        elif action == 'feature':
            updated_count = listings.update(is_featured=True)
        
        elif action == 'unfeature':
            updated_count = listings.update(is_featured=False)
        
        elif action == 'delete':
            updated_count = listings.count()
            listings.delete()
        
        else:
            return JsonResponse({'success': False, 'error': 'Invalid action'})
        
        # Log the bulk operation with comprehensive details
        log_bulk_listing_activity(
            user=request.user,
            action_type=ActivityLogType.UPDATE,
            listings=listings,
            action_name=action,
            request=request
        )
        
        return JsonResponse({
            'success': True, 
            'message': f'Successfully {action}ed {updated_count} listings'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def batch_process_payments_view(request):
    """Process multiple payments in batch"""
    try:
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        payment_method = request.POST.get('payment_method')
        vendor_id = request.POST.get('vendor_id')
        
        # Get pending payments
        payments = VendorPayment.objects.filter(status=PaymentStatus.PENDING)
        if vendor_id:
            payments = payments.filter(vendor_id=vendor_id)
        
        # Create payment batch
        batch = PaymentBatch.objects.create(
            name=name,
            description=description,
            total_payments=payments.count(),
            total_amount=payments.aggregate(total=Sum('net_amount'))['total'] or 0,
            created_by=request.user
        )
        
        # Process each payment
        processed_count = 0
        for payment in payments:
            try:
                # Update payment status
                payment.status = PaymentStatus.COMPLETED
                payment.payment_method = payment_method
                payment.processed_at = timezone.now()
                payment.processed_by = request.user
                payment.batch = batch
                payment.save()
                
                # Update vendor balance
                vendor_balance, created = VendorBalance.objects.get_or_create(
                    vendor=payment.vendor,
                    defaults={'current_balance': 0, 'total_earned': 0, 'total_withdrawn': 0}
                )
                vendor_balance.total_withdrawn += payment.net_amount
                vendor_balance.current_balance -= payment.net_amount
                vendor_balance.save()
                
                # Create payment history
                PaymentHistory.objects.create(
                    payment=payment,
                    action='completed',
                    previous_status=PaymentStatus.PENDING,
                    new_status=PaymentStatus.COMPLETED,
                    notes=f'Processed in batch: {name}',
                    changed_by=request.user
                )
                
                processed_count += 1
                
            except Exception as e:
                # Log error but continue processing other payments
                print(f"Error processing payment {payment.id}: {str(e)}")
                continue
        
        # Update batch status
        batch.processed_payments = processed_count
        batch.status = 'completed' if processed_count == payments.count() else 'partial'
        batch.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'Successfully processed {processed_count} payments',
            'processed_count': processed_count
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@require_POST
def create_commission_rule_view(request):
    """Create a new commission rule"""
    try:
        name = request.POST.get('name')
        category = request.POST.get('category')
        description = request.POST.get('description', '')
        commission_type = request.POST.get('commission_type', 'fixed')
        commission_rate = float(request.POST.get('commission_rate', 0))
        min_amount = float(request.POST.get('min_amount', 0)) if request.POST.get('min_amount') else None
        max_amount = float(request.POST.get('max_amount', 0)) if request.POST.get('max_amount') else None
        is_active = request.POST.get('is_active', 'true') == 'true'
        
        # Create commission rule
        rule = CommissionRule.objects.create(
            name=name,
            category=category,
            description=description,
            commission_type=commission_type,
            commission_rate=commission_rate,
            min_amount=min_amount,
            max_amount=max_amount,
            is_active=is_active,
            created_by=request.user
        )
        
        return JsonResponse({
            'success': True, 
            'message': 'Commission rule created successfully',
            'rule_id': rule.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@require_POST
def toggle_commission_rule_view(request, rule_id):
    """Toggle commission rule status"""
    try:
        rule = get_object_or_404(CommissionRule, id=rule_id)
        rule.is_active = not rule.is_active
        rule.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'Commission rule {"activated" if rule.is_active else "deactivated"}'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@require_POST
def delete_commission_rule_view(request, rule_id):
    """Delete a commission rule (soft delete)"""
    try:
        rule = get_object_or_404(CommissionRule, id=rule_id)
        rule.is_deleted = True
        rule.deleted_at = timezone.now()
        rule.save()
        
        return JsonResponse({
            'success': True, 
            'message': 'Commission rule deleted successfully'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@require_POST
def adjust_vendor_balance_view(request, vendor_id):
    """Adjust vendor balance"""
    try:
        vendor = get_object_or_404(Vendor, id=vendor_id)
        adjustment_type = request.POST.get('adjustment_type')
        amount = float(request.POST.get('amount', 0))
        reason = request.POST.get('reason', '')
        
        if amount <= 0:
            return JsonResponse({'success': False, 'message': 'Amount must be greater than 0'})
        
        # Get or create vendor balance
        balance, created = VendorBalance.objects.get_or_create(
            vendor=vendor,
            defaults={'current_balance': 0, 'total_earned': 0, 'total_withdrawn': 0}
        )
        
        # Apply adjustment
        if adjustment_type == 'credit':
            balance.current_balance += amount
            balance.total_earned += amount
            transaction_type = 'balance_adjustment_credit'
        else:  # debit
            if balance.current_balance < amount:
                return JsonResponse({'success': False, 'message': 'Insufficient balance'})
            balance.current_balance -= amount
            balance.total_withdrawn += amount
            transaction_type = 'balance_adjustment_debit'
        
        balance.save()
        
        # Create transaction history
        PaymentHistory.objects.create(
            vendor=vendor,
            transaction_type=transaction_type,
            amount=amount if adjustment_type == 'credit' else -amount,
            description=f'Balance adjustment: {reason}',
            balance_after=balance.current_balance,
            changed_by=request.user
        )
        
        # Create activity log
        ActivityLog.objects.create(
            user=request.user,
            action='vendor_balance_adjusted',
            description=f'Adjusted {vendor.business_name} balance by ${amount} ({adjustment_type})',
            vendor=vendor
        )
        
        return JsonResponse({
            'success': True, 
            'message': f'Balance adjusted successfully. New balance: ${balance.current_balance}',
            'new_balance': balance.current_balance
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@can_manage_listings
@require_valid_admin_session
@audit_admin_action(ActivityLogType.VIEW, "Viewed listing details for listing {listing_id}")
def listing_detail_view(request, listing_id):
    """Detailed view of a single listing for admin management."""
    listing = get_object_or_404(VehicleListing, id=listing_id)
    
    # Get status history
    status_logs = ListingStatusLog.objects.filter(listing=listing).order_by('-changed_at')
    
    # Get related data
    images = listing.images.all()
    videos = listing.videos.all()
    
    context = {
        'listing': listing,
        'status_logs': status_logs,
        'images': images,
        'videos': videos,
        'status_choices': VehicleListing._meta.get_field('status').choices,
    }
    
    return render(request, 'admin_panel/listing_detail.html', context)


@can_manage_listings
@require_valid_admin_session
@require_http_methods(["POST"])
def update_listing_status(request, listing_id):
    """Update listing status with logging."""
    listing = get_object_or_404(VehicleListing, id=listing_id)
    new_status = request.POST.get('status')
    reason = request.POST.get('reason', '')
    
    if new_status not in dict(VehicleListing._meta.get_field('status').choices):
        messages.error(request, 'Invalid status')
        return redirect('admin_panel:listing_detail', listing_id=listing_id)
    
    old_status = listing.status
    listing.status = new_status
    listing.save()
    
    # Log the status change
    ListingStatusLog.objects.create(
        listing=listing,
        old_status=old_status,
        new_status=new_status,
        changed_by=request.user,
        reason=reason
    )
    
    # Log the status change with comprehensive details
    log_status_change_activity(
        user=request.user,
        listing=listing,
        old_status=old_status,
        new_status=new_status,
        reason=reason,
        request=request
    )
    
    messages.success(request, f'Listing status updated to {new_status}')
    return redirect('admin_panel:listing_detail', listing_id=listing_id)


@can_view_analytics
@require_valid_admin_session
@audit_admin_action(ActivityLogType.VIEW, "Accessed analytics dashboard")
def analytics_view(request):
    """Analytics dashboard for listings."""
    # Time period filter
    period = request.GET.get('period', '30')  # days
    try:
        days = int(period)
    except ValueError:
        days = 30
    
    start_date = timezone.now() - timedelta(days=days)
    
    # Listings created in period
    listings_in_period = VehicleListing.objects.filter(created_at__gte=start_date)
    
    # Daily creation trend
    daily_data = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        count = listings_in_period.filter(
            created_at__date=day.date()
        ).count()
        daily_data.append({
            'date': day.strftime('%Y-%m-%d'),
            'count': count
        })
    
    # Status distribution
    status_stats = listings_in_period.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Make distribution
    make_stats = listings_in_period.values('make__name').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # User activity
    user_stats = listings_in_period.values('user__email').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Average price by make
    price_stats = listings_in_period.filter(
        price__isnull=False
    ).values('make__name').annotate(
        avg_price=Avg('price'),
        count=Count('id')
    ).order_by('-avg_price')[:10]
    
    context = {
        'period': days,
        'daily_data': daily_data,
        'status_stats': status_stats,
        'make_stats': make_stats,
        'user_stats': user_stats,
        'price_stats': price_stats,
        'total_in_period': listings_in_period.count(),
        'avg_daily_in_period': (listings_in_period.count() / days) if days else 0,
    }
    
    return render(request, 'admin_panel/analytics.html', context)


@can_view_audit_logs
@require_valid_admin_session
@audit_admin_action(ActivityLogType.VIEW, "Accessed activity logs")
def activity_logs_view(request):
    """View activity logs."""
    # Filter parameters
    user_filter = request.GET.get('user', '')
    action_filter = request.GET.get('action', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Build queryset
    logs = ActivityLog.objects.select_related('user').all()
    
    if user_filter:
        logs = logs.filter(user__email__icontains=user_filter)
    
    if action_filter:
        logs = logs.filter(action_type=action_filter)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            logs = logs.filter(action_time__date__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            logs = logs.filter(action_time__date__lte=date_to_obj)
        except ValueError:
            pass
    
    # Pagination
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'action_choices': ActivityLogType.choices,
        'current_filters': {
            'user': user_filter,
            'action': action_filter,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    
    return render(request, 'admin_panel/activity_logs.html', context)


# API endpoints for dashboard widgets
@ajax_admin_required
def api_dashboard_stats(request):
    """API endpoint for dashboard statistics."""
    stats = {
        'total_listings': VehicleListing.objects.count(),
        'published_listings': VehicleListing.objects.filter(status='published').count(),
        'pending_listings': VehicleListing.objects.filter(status='pending').count(),
        'featured_listings': VehicleListing.objects.filter(is_featured=True).count(),
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
    }
    return JsonResponse(stats)


@ajax_admin_required
def api_recent_activity(request):
    """API endpoint for recent activity."""
    activities = ActivityLog.objects.select_related('user').order_by('-action_time')[:10]
    data = []
    for activity in activities:
        data.append({
            'user': activity.user.email,
            'action': activity.get_action_type_display(),
            'description': activity.description,
            'time': activity.action_time.isoformat(),
        })
    return JsonResponse({'activities': data})


# Vendor Management Views
@admin_required(min_role='staff')
@require_valid_admin_session
@audit_admin_action(ActivityLogType.VIEW, "Accessed vendor management")
def vendor_management_view(request):
    """Comprehensive vendor management interface."""
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    search_query = request.GET.get('search', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Build queryset
    vendors = BusinessPartner.objects.select_related('user').prefetch_related('roles', 'contact_info')
    
    if status_filter:
        vendors = vendors.filter(status=status_filter)
    
    if type_filter:
        vendors = vendors.filter(roles__role_type=type_filter)
    
    if search_query:
        vendors = vendors.filter(
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(business_name__icontains=search_query)
        )
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            vendors = vendors.filter(created_at__date__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            vendors = vendors.filter(created_at__date__lte=date_to_obj)
        except ValueError:
            pass
    
    # Order by creation date (newest first)
    vendors = vendors.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(vendors, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    status_choices = BusinessPartner.STATUS_CHOICES
    role_types = BusinessPartnerRole.ROLE_CHOICES
    
    # Calculate vendor statistics
    total_vendors = BusinessPartner.objects.count()
    pending_vendors = BusinessPartner.objects.filter(status='pending').count()
    approved_vendors = BusinessPartner.objects.filter(status='approved').count()
    rejected_vendors = BusinessPartner.objects.filter(status='rejected').count()
    
    context = {
        'page_obj': page_obj,
        'status_choices': status_choices,
        'role_types': role_types,
        'current_filters': {
            'status': status_filter,
            'type': type_filter,
            'search': search_query,
            'date_from': date_from,
            'date_to': date_to,
        },
        'vendor_stats': {
            'total': total_vendors,
            'pending': pending_vendors,
            'approved': approved_vendors,
            'rejected': rejected_vendors,
        }
    }
    
    return render(request, 'admin_panel/vendor_management.html', context)


@admin_required(min_role='staff')
@require_valid_admin_session
@audit_admin_action(ActivityLogType.VIEW, "Viewed vendor details for vendor {vendor_id}")
def vendor_detail_view(request, vendor_id):
    """Detailed view of a single vendor for management."""
    vendor = get_object_or_404(BusinessPartner, id=vendor_id)
    
    # Get vendor roles
    roles = vendor.roles.all()
    
    # Get contact information
    contact_info = vendor.contacts.all()
    
    # Get related listings if vendor is a dealer
    listings = VehicleListing.objects.filter(user=vendor.user).order_by('-created_at')[:10]
    
    # Calculate vendor metrics
    total_listings = listings.count()
    active_listings = listings.filter(status='published').count()
    
    context = {
        'vendor': vendor,
        'roles': roles,
        'contact_info': contact_info,
        'listings': listings,
        'metrics': {
            'total_listings': total_listings,
            'active_listings': active_listings,
        },
        'status_choices': BusinessPartner.STATUS_CHOICES,
    }
    
    return render(request, 'admin_panel/vendor_detail.html', context)


@admin_required(min_role='staff')
@require_valid_admin_session
@require_http_methods(["POST"])
@audit_admin_action(ActivityLogType.UPDATE, "Updated vendor status for vendor {vendor_id}")
def update_vendor_status(request, vendor_id):
    """Update vendor status with approval workflow."""
    vendor = get_object_or_404(BusinessPartner, id=vendor_id)
    new_status = request.POST.get('status')
    reason = request.POST.get('reason', '')
    
    if new_status not in dict(BusinessPartner.STATUS_CHOICES):
        messages.error(request, 'Invalid vendor status')
        return redirect('admin_panel:vendor_detail', vendor_id=vendor_id)
    
    old_status = vendor.status
    vendor.status = new_status
    vendor.save()
    
    # Log the status change
    log_description = f"Vendor status changed from {old_status} to {new_status}"
    if reason:
        log_description += f" - Reason: {reason}"
    
    ActivityLog.objects.create(
        user=request.user,
        action_type=ActivityLogType.UPDATE,
        description=log_description,
        content_object=vendor
    )
    
    messages.success(request, f'Vendor status updated to {new_status}')
    return redirect('admin_panel:vendor_detail', vendor_id=vendor_id)


@admin_required(min_role='staff')
@require_valid_admin_session
@audit_admin_action(ActivityLogType.VIEW, "Accessed vendor approval queue")
def vendor_approval_queue_view(request):
    """View pending vendor applications for approval."""
    phone_subquery = ContactInfo.objects.filter(
        business_partner=OuterRef('pk'),
        contact_type='phone',
        is_primary=True,
    ).values('value')[:1]

    pending_vendors = (
        BusinessPartner.objects.filter(
            status='pending',
            roles__role_type='vendor',
        )
        .distinct()
        .select_related('user', 'vendor_profile')
        .prefetch_related('roles', 'contacts')
        .annotate(phone=Subquery(phone_subquery))
    )
    
    # Get filter parameters
    type_filter = request.GET.get('type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if type_filter:
        pending_vendors = pending_vendors.filter(roles__role_type=type_filter)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            pending_vendors = pending_vendors.filter(created_at__date__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            pending_vendors = pending_vendors.filter(created_at__date__lte=date_to_obj)
        except ValueError:
            pass
    
    # Pagination
    paginator = Paginator(pending_vendors, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    role_types = BusinessPartnerRole.ROLE_TYPES
    
    context = {
        'page_obj': page_obj,
        'role_types': role_types,
        'current_filters': {
            'type': type_filter,
            'date_from': date_from,
            'date_to': date_to,
        },
        'pending_count': pending_vendors.count(),
    }
    
    return render(request, 'admin_panel/vendor_approval_queue.html', context)

@login_required
def vendor_performance_view(request):
    """Display vendor performance metrics and ratings."""
    # Get all approved vendors with their performance metrics
    vendors = BusinessPartner.objects.filter(status='approved').annotate(
        total_listings=Count('listings'),
        active_listings=Count('listings', filter=Q(listings__status='published')),
        avg_rating=Avg('reviews__rating'),
        total_reviews=Count('reviews'),
        total_views=Sum('listings__views'),
        total_leads=Count('listings__leads'),
        membership_days=(datetime.now().date() - Avg('created_at')).days
    ).order_by('-avg_rating', '-total_listings')
    
    # Calculate performance metrics
    for vendor in vendors:
        vendor.performance_score = calculate_vendor_performance_score(vendor)
        vendor.response_rate = calculate_response_rate(vendor)
        vendor.conversion_rate = calculate_conversion_rate(vendor)
    
    # Get top performers
    top_performers = vendors[:10]
    
    # Get performance trends for the last 6 months
    six_months_ago = datetime.now() - timedelta(days=180)
    monthly_performance = []
    
    for i in range(6):
        month_start = six_months_ago + timedelta(days=30*i)
        month_end = month_start + timedelta(days=30)
        
        month_data = {
            'month': month_start.strftime('%b %Y'),
            'new_listings': Vehicle.objects.filter(
                seller__business_partner__in=vendors,
                created_at__range=[month_start, month_end]
            ).count(),
            'total_views': Vehicle.objects.filter(
                seller__business_partner__in=vendors,
                created_at__range=[month_start, month_end]
            ).aggregate(Sum('views'))['views__sum'] or 0,
            'new_leads': Lead.objects.filter(
                vehicle__seller__business_partner__in=vendors,
                created_at__range=[month_start, month_end]
            ).count()
        }
        monthly_performance.append(month_data)
    
    context = {
        'vendors': vendors,
        'top_performers': top_performers,
        'monthly_performance': monthly_performance,
        'total_vendors': vendors.count(),
        'avg_rating': vendors.aggregate(Avg('avg_rating'))['avg_rating__avg'] or 0,
        'total_listings': vendors.aggregate(Sum('total_listings'))['total_listings__sum'] or 0,
        'total_reviews': vendors.aggregate(Sum('total_reviews'))['total_reviews__sum'] or 0,
    }
    
    return render(request, 'admin_panel/vendor_performance.html', context)

def calculate_vendor_performance_score(vendor):
    """Calculate a composite performance score for a vendor."""
    score = 0
    
    # Rating component (30%)
    if vendor.avg_rating:
        score += (vendor.avg_rating / 5) * 30
    
    # Activity component (25%)
    if vendor.total_listings > 0:
        activity_score = min(vendor.active_listings / vendor.total_listings, 1) * 25
        score += activity_score
    
    # Engagement component (20%)
    if vendor.total_views and vendor.total_views > 0:
        engagement_score = min(vendor.total_views / 1000, 1) * 20
        score += engagement_score
    
    # Conversion component (15%)
    if vendor.total_leads and vendor.total_views and vendor.total_views > 0:
        conversion_rate = vendor.total_leads / vendor.total_views
        score += min(conversion_rate * 100, 1) * 15
    
    # Reviews component (10%)
    if vendor.total_reviews > 0:
        review_score = min(vendor.total_reviews / 50, 1) * 10
        score += review_score
    
    return round(score, 1)

def calculate_response_rate(vendor):
    """Calculate vendor response rate to inquiries."""
    # This would need a messaging/response tracking system
    # For now, return a placeholder
    return 85.0  # Placeholder

def calculate_conversion_rate(vendor):
    """Calculate vendor conversion rate from views to leads."""
    if vendor.total_leads and vendor.total_views and vendor.total_views > 0:
        return round((vendor.total_leads / vendor.total_views) * 100, 2)
    return 0.0

@login_required
def vendor_messages_view(request):
    """Display all messages with vendors."""
    # Get filter parameters
    status = request.GET.get('status', 'all')
    category = request.GET.get('category', 'all')
    priority = request.GET.get('priority', 'all')
    search = request.GET.get('search', '')
    
    # Base queryset
    messages = AdminMessage.objects.select_related('sender', 'recipient', 'business_partner')
    
    # Apply filters
    if status != 'all':
        messages = messages.filter(status=status)
    if category != 'all':
        messages = messages.filter(category=category)
    if priority != 'all':
        messages = messages.filter(priority=priority)
    if search:
        messages = messages.filter(
            Q(subject__icontains=search) |
            Q(content__icontains=search) |
            Q(sender__email__icontains=search) |
            Q(recipient__email__icontains=search) |
            Q(business_partner__business_name__icontains=search)
        )
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(messages, 20)
    
    try:
        messages = paginator.page(page)
    except PageNotAnInteger:
        messages = paginator.page(1)
    except EmptyPage:
        messages = paginator.page(paginator.num_pages)
    
    # Get message statistics
    message_stats = {
        'total': AdminMessage.objects.count(),
        'unread': AdminMessage.objects.filter(is_read=False).count(),
        'sent': AdminMessage.objects.filter(status=MessageStatus.SENT).count(),
        'read': AdminMessage.objects.filter(status=MessageStatus.READ).count(),
        'replied': AdminMessage.objects.filter(status=MessageStatus.REPLIED).count(),
    }
    
    context = {
        'messages': messages,
        'message_stats': message_stats,
        'status_choices': MessageStatus.choices,
        'category_choices': MessageCategory.choices,
        'priority_choices': MessagePriority.choices,
        'current_filters': {
            'status': status,
            'category': category,
            'priority': priority,
            'search': search,
        }
    }
    
    return render(request, 'admin_panel/vendor_messages.html', context)

@login_required
def send_vendor_message(request, vendor_id=None):
    """Send a message to a vendor."""
    if request.method == 'POST':
        recipient_id = request.POST.get('recipient_id')
        subject = request.POST.get('subject')
        content = request.POST.get('content')
        category = request.POST.get('category', MessageCategory.GENERAL)
        priority = request.POST.get('priority', MessagePriority.MEDIUM)
        template_id = request.POST.get('template_id')
        
        try:
            recipient = User.objects.get(id=recipient_id)
            business_partner = BusinessPartner.objects.filter(user=recipient).first()
            
            # If template is selected, use template content
            if template_id:
                template = MessageTemplate.objects.get(id=template_id)
                context = {
                    'vendor_name': business_partner.business_name if business_partner else recipient.get_full_name(),
                    'vendor_email': recipient.email,
                }
                rendered = template.render_template(context)
                subject = rendered['subject']
                content = rendered['content']
            
            message = AdminMessage.objects.create(
                sender=request.user,
                recipient=recipient,
                business_partner=business_partner,
                subject=subject,
                content=content,
                category=category,
                priority=priority,
                status=MessageStatus.SENT
            )
            
            # Create notification for the vendor
            VendorNotification.objects.create(
                vendor=business_partner,
                message=message,
                title=subject,
                content=content[:200] + '...' if len(content) > 200 else content,
                type=category,
                action_url=f'/messages/{message.id}/',
                action_text='View Message'
            )
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action=ActivityLogType.MESSAGE_SENT,
                description=f'Sent message to {business_partner.business_name if business_partner else recipient.email}: {subject}'
            )
            
            messages.success(request, 'Message sent successfully!')
            return redirect('admin_panel:vendor_messages')
            
        except User.DoesNotExist:
            messages.error(request, 'Recipient not found.')
        except MessageTemplate.DoesNotExist:
            messages.error(request, 'Selected template not found.')
        except Exception as e:
            messages.error(request, f'Error sending message: {str(e)}')
    
    # GET request - show form
    vendors = BusinessPartner.objects.filter(status='approved').select_related('user')
    templates = MessageTemplate.objects.filter(is_active=True)
    
    # If vendor_id is provided, pre-select that vendor
    selected_vendor = None
    if vendor_id:
        selected_vendor = BusinessPartner.objects.filter(id=vendor_id).first()
    
    context = {
        'vendors': vendors,
        'templates': templates,
        'category_choices': MessageCategory.choices,
        'priority_choices': MessagePriority.choices,
        'selected_vendor': selected_vendor,
    }
    
    return render(request, 'admin_panel/send_vendor_message.html', context)

@login_required
def message_detail_view(request, message_id):
    """View detailed message and conversation thread."""
    message = get_object_or_404(AdminMessage, id=message_id)
    
    # Mark as read if it's unread
    if message.recipient == request.user and not message.is_read:
        message.mark_as_read()
    
    # Get conversation thread
    conversation_thread = message.get_conversation_thread()
    
    # Get reply form
    if request.method == 'POST':
        reply_content = request.POST.get('reply_content')
        if reply_content:
            reply = AdminMessage.objects.create(
                sender=request.user,
                recipient=message.sender,
                business_partner=message.business_partner,
                subject=f"Re: {message.subject}",
                content=reply_content,
                category=message.category,
                priority=message.priority,
                parent_message=message,
                status=MessageStatus.SENT
            )
            
            # Update original message status
            message.status = MessageStatus.REPLIED
            message.save(update_fields=['status'])
            
            messages.success(request, 'Reply sent successfully!')
            return redirect('admin_panel:message_detail', message_id=message.id)
    
    context = {
        'message': message,
        'conversation_thread': conversation_thread,
    }
    
    return render(request, 'admin_panel/message_detail.html', context)

@login_required
def message_templates_view(request):
    """Manage message templates."""
    templates = MessageTemplate.objects.filter(is_active=True).order_by('category', 'name')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            name = request.POST.get('name')
            category = request.POST.get('category')
            subject = request.POST.get('subject')
            content = request.POST.get('content')
            
            MessageTemplate.objects.create(
                name=name,
                category=category,
                subject=subject,
                content=content,
                created_by=request.user
            )
            messages.success(request, 'Template created successfully!')
            
        elif action == 'delete':
            template_id = request.POST.get('template_id')
            try:
                template = MessageTemplate.objects.get(id=template_id)
                template.is_active = False
                template.save()
                messages.success(request, 'Template deleted successfully!')
            except MessageTemplate.DoesNotExist:
                messages.error(request, 'Template not found.')
        
        return redirect('admin_panel:message_templates')
    
    context = {
        'templates': templates,
        'category_choices': MessageCategory.choices,
    }
    
    return render(request, 'admin_panel/message_templates.html', context)


@login_required
@staff_required
def mark_message_read(request, message_id):
    """Mark a message as read."""
    if request.method == 'POST':
        message = get_object_or_404(AdminMessage, id=message_id)
        message.status = 'read'
        message.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required
@staff_required
def payment_management_view(request):
    """View for managing vendor payments and commissions."""
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    vendor_filter = request.GET.get('vendor', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    payment_method = request.GET.get('payment_method', '')
    
    # Base queryset
    payments = VendorPayment.objects.select_related('vendor').prefetch_related('related_listings')
    
    # Apply filters
    if status_filter:
        payments = payments.filter(status=status_filter)
    if vendor_filter:
        payments = payments.filter(vendor_id=vendor_filter)
    if date_from:
        payments = payments.filter(created_at__date__gte=date_from)
    if date_to:
        payments = payments.filter(created_at__date__lte=date_to)
    if payment_method:
        payments = payments.filter(payment_method=payment_method)
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(payments, 20)
    
    try:
        payments_page = paginator.page(page)
    except PageNotAnInteger:
        payments_page = paginator.page(1)
    except EmptyPage:
        payments_page = paginator.page(paginator.num_pages)
    
    # Statistics
    payment_stats = {
        'total_payments': payments.count(),
        'total_amount': payments.aggregate(total=Sum('amount'))['total'] or 0,
        'total_commission': payments.aggregate(total=Sum('commission_amount'))['total'] or 0,
        'pending_payments': payments.filter(status='pending').count(),
        'completed_payments': payments.filter(status='completed').count(),
        'failed_payments': payments.filter(status='failed').count(),
    }
    
    # Get vendors for filter dropdown
    vendors = (
        BusinessPartner.objects.filter(roles__role_type='vendor')
        .exclude(status='pending')
        .distinct()
        .order_by('name')
    )
    
    context = {
        'payments': payments_page,
        'payment_stats': payment_stats,
        'vendors': vendors,
        'status_choices': PaymentStatus.choices,
        'payment_method_choices': PaymentMethod.choices,
        'status_filter': status_filter,
        'vendor_filter': vendor_filter,
        'date_from': date_from,
        'date_to': date_to,
        'payment_method_filter': payment_method,
    }
    
    return render(request, 'admin_panel/payment_management.html', context)


@login_required
@staff_required
def commission_management_view(request):
    """View for managing commission rules and rates."""
    
    # Get all commission rules
    commission_rules = CommissionRule.objects.select_related('created_by').prefetch_related('specific_vendors')
    
    # Calculate statistics
    commission_stats = {
        'total_rules': commission_rules.count(),
        'active_rules': commission_rules.filter(is_active=True).count(),
        'vendor_specific_rules': commission_rules.filter(applies_to_all_vendors=False).count(),
    }
    
    context = {
        'commission_rules': commission_rules,
        'commission_stats': commission_stats,
        'commission_type_choices': CommissionRule.commission_type.field.choices,
    }
    
    return render(request, 'admin_panel/commission_management.html', context)


@login_required
@staff_required
def vendor_balance_view(request, vendor_id):
    """View for vendor balance and payment history."""
    
    vendor = get_object_or_404(
        BusinessPartner.objects.filter(roles__role_type='vendor').distinct(),
        id=vendor_id,
    )
    
    # Get or create vendor balance
    balance, created = VendorBalance.objects.get_or_create(
        vendor=vendor,
        defaults={'current_balance': 0, 'total_earned': 0, 'total_paid': 0}
    )
    
    # Get payment history
    payments = VendorPayment.objects.filter(vendor=vendor).order_by('-created_at')
    
    # Calculate statistics
    balance_stats = {
        'total_payments': payments.count(),
        'total_earned': payments.aggregate(total=Sum('amount'))['total'] or 0,
        'total_paid': payments.filter(status='completed').aggregate(total=Sum('net_amount'))['total'] or 0,
        'pending_payments': payments.filter(status='pending').aggregate(total=Sum('net_amount'))['total'] or 0,
        'average_payment': payments.filter(status='completed').aggregate(avg=Avg('net_amount'))['avg'] or 0,
    }
    
    context = {
        'vendor': vendor,
        'balance': balance,
        'payments': payments[:10],  # Last 10 payments
        'balance_stats': balance_stats,
    }
    
    return render(request, 'admin_panel/vendor_balance.html', context)


@login_required
@staff_required
def process_payment_view(request, payment_id):
    """Process a vendor payment."""
    
    if request.method == 'POST':
        payment = get_object_or_404(VendorPayment, id=payment_id)
        
        # Update payment status
        old_status = payment.status
        payment.status = 'processing'
        payment.processed_at = datetime.now()
        payment.save()
        
        # Create payment history
        PaymentHistory.objects.create(
            payment=payment,
            old_status=old_status,
            new_status='processing',
            notes=f"Payment processing initiated by {request.user.get_full_name()}",
            changed_by=request.user
        )
        
        # Simulate payment processing (in real implementation, integrate with payment gateway)
        import time
        time.sleep(2)  # Simulate processing time
        
        # Update to completed status
        payment.status = 'completed'
        payment.payment_date = datetime.now()
        payment.save()
        
        # Create payment history for completion
        PaymentHistory.objects.create(
            payment=payment,
            old_status='processing',
            new_status='completed',
            notes=f"Payment completed by {request.user.get_full_name()}",
            changed_by=request.user
        )
        
        # Update vendor balance
        balance, created = VendorBalance.objects.get_or_create(
            vendor=payment.vendor,
            defaults={'current_balance': 0, 'total_earned': 0, 'total_paid': 0}
        )
        balance.total_paid += payment.net_amount
        balance.last_payment_date = payment.payment_date
        balance.last_payment_amount = payment.net_amount
        balance.update_balance()
        
        messages.success(request, f"Payment {payment.payment_reference} processed successfully!")
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type=ActivityLogType.PAYMENT_PROCESSED,
            description=f"Processed payment {payment.payment_reference} for {payment.vendor.business_name}",
            related_vendor=payment.vendor
        )
        
        return redirect('admin_panel:payment_management')
    
    return redirect('admin_panel:payment_management')


@login_required
@staff_required
def delete_message(request, message_id):
    """Delete a message (soft delete)."""
    if request.method == 'POST':
        message = get_object_or_404(AdminMessage, id=message_id)
        message.is_deleted = True
        message.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required
@staff_required
def get_message_template(request, template_id):
    """Get a message template for viewing/editing."""
    template = get_object_or_404(MessageTemplate, id=template_id)
    return JsonResponse({
        'success': True,
        'template': {
            'id': template.id,
            'name': template.name,
            'description': template.description,
            'category': template.category,
            'category_display': template.get_category_display(),
            'subject': template.subject,
            'content': template.content,
            'priority': template.priority,
            'priority_display': template.get_priority_display(),
            'is_active': template.is_active,
            'created_at': template.created_at.isoformat(),
            'updated_at': template.updated_at.isoformat(),
        }
    })


@login_required
@staff_required
def delete_message_template(request, template_id):
    """Delete a message template (soft delete)."""
    if request.method == 'POST':
        template = get_object_or_404(MessageTemplate, id=template_id)
        template.is_deleted = True
        template.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


# ==================== VENDOR MANAGEMENT VIEWS ====================

@login_required
@staff_required
def vendor_management_view(request):
    tab = request.GET.get('tab', 'all')
    status_filter = request.GET.get('status', '')
    search = request.GET.get('search', '')

    if tab == 'pending' and not status_filter:
        status_filter = 'pending'

    vendors_base = BusinessPartner.objects.filter(roles__role_type='vendor').distinct()

    phone_subquery = ContactInfo.objects.filter(
        business_partner=OuterRef('pk'),
        contact_type='phone',
        is_primary=True,
    ).values('value')[:1]

    vendors = (
        vendors_base.select_related('user', 'vendor_profile')
        .prefetch_related('roles', 'contacts')
        .annotate(
            listing_count=Count('user__listings', distinct=True),
            rating=F('vendor_profile__vendor_rating'),
            phone=Subquery(phone_subquery),
        )
    )

    if status_filter:
        vendors = vendors.filter(status=status_filter)

    if search:
        vendors = vendors.filter(
            Q(name__icontains=search)
            | Q(bp_number__icontains=search)
            | Q(user__email__icontains=search)
            | Q(contacts__value__icontains=search)
        ).distinct()

    vendors = vendors.order_by('-created_at')

    paginator = Paginator(vendors, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'tab': tab,
        'page_obj': page_obj,
        'vendors': page_obj,
        'search': search,
        'status_filter': status_filter,
        'status_choices': BusinessPartner.STATUS_CHOICES,
        'total_vendors': vendors_base.count(),
        'active_vendors': vendors_base.filter(status='active').count(),
        'pending_vendors': vendors_base.filter(status='pending').count(),
        'inactive_vendors': vendors_base.filter(status='inactive').count(),
        'suspended_vendors': vendors_base.filter(status='suspended').count(),
    }

    return render(request, 'admin_panel/vendor_management.html', context)


@login_required
@staff_required
def vendor_application_detail_view(request, application_id):
    """Detailed view of a vendor application for review and approval."""
    
    application = get_object_or_404(VendorApplication, id=application_id)
    
    # Get related documents
    documents = VendorDocument.objects.filter(
        vendor_application=application
    ).select_related('category')
    
    # Get verification queue items
    verification_queue = DocumentVerificationQueue.objects.filter(
        vendor_application=application
    ).select_related('assigned_to')
    
    # Calculate completion percentage
    completion_percentage = application.get_completion_percentage()
    
    # Check if application can be submitted
    can_submit = application.can_submit()
    
    # Get step completion status
    step_status = {
        'step1': application.is_step_completed(1),
        'step2': application.is_step_completed(2),
        'step3': application.is_step_completed(3),
        'step4': application.is_step_completed(4),
    }
    
    context = {
        'application': application,
        'documents': documents,
        'verification_queue': verification_queue,
        'completion_percentage': completion_percentage,
        'can_submit': can_submit,
        'step_status': step_status,
    }
    
    return render(request, 'admin_panel/vendor_application_detail.html', context)


@login_required
@staff_required
@require_POST
def approve_vendor_application_view(request, application_id):
    """Approve a vendor application and create vendor account."""
    
    application = get_object_or_404(VendorApplication, id=application_id)
    notes = request.POST.get('review_notes', '')
    
    if application.status not in ['submitted', 'under_review']:
        messages.error(request, 'This application cannot be approved in its current status.')
        return redirect('admin_panel:vendor_application_detail', application_id=application_id)
    
    try:
        # Approve the application
        business_partner = application.approve(request.user, notes)
        
        if business_partner:
            messages.success(request, f'Vendor application approved successfully! Business partner {business_partner.name} created.')
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action_type=ActivityLogType.VENDOR_APPROVED,
                description=f'Approved vendor application for {application.company_name}',
                related_business_partner=business_partner
            )
            
            # Send notification to applicant
            if application.user:
                VendorNotification.objects.create(
                    recipient=application.user,
                    sender=request.user,
                    subject='Vendor Application Approved',
                    message=f'Congratulations! Your vendor application for {application.company_name} has been approved. You can now start selling on our platform.',
                    category='vendor_approval',
                    priority='high'
                )
        else:
            messages.error(request, 'Failed to approve vendor application.')
    
    except Exception as e:
        messages.error(request, f'Error approving application: {str(e)}')
    
    return redirect('admin_panel:vendor_management')


@login_required
@staff_required
@require_POST
def reject_vendor_application_view(request, application_id):
    """Reject a vendor application with reason."""
    
    application = get_object_or_404(VendorApplication, id=application_id)
    rejection_reason = request.POST.get('rejection_reason', '')
    review_notes = request.POST.get('review_notes', '')
    
    if not rejection_reason:
        messages.error(request, 'Rejection reason is required.')
        return redirect('admin_panel:vendor_application_detail', application_id=application_id)
    
    if application.status not in ['submitted', 'under_review']:
        messages.error(request, 'This application cannot be rejected in its current status.')
        return redirect('admin_panel:vendor_application_detail', application_id=application_id)
    
    try:
        application.reject(request.user, rejection_reason, review_notes)
        
        messages.success(request, f'Vendor application rejected successfully.')
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type=ActivityLogType.VENDOR_REJECTED,
            description=f'Rejected vendor application for {application.company_name}',
            related_application=application
        )
        
        # Send notification to applicant
        if application.user:
            VendorNotification.objects.create(
                recipient=application.user,
                sender=request.user,
                subject='Vendor Application Rejected',
                message=f'Your vendor application for {application.company_name} has been rejected. Reason: {rejection_reason}',
                category='vendor_rejection',
                priority='high'
            )
    
    except Exception as e:
        messages.error(request, f'Error rejecting application: {str(e)}')
    
    return redirect('admin_panel:vendor_management')


@login_required
@staff_required
@require_POST
def request_changes_vendor_application_view(request, application_id):
    """Request changes to a vendor application."""
    
    application = get_object_or_404(VendorApplication, id=application_id)
    changes_required = request.POST.get('changes_required', '')
    review_notes = request.POST.get('review_notes', '')
    
    if not changes_required:
        messages.error(request, 'Changes required description is mandatory.')
        return redirect('admin_panel:vendor_application_detail', application_id=application_id)
    
    if application.status not in ['submitted', 'under_review']:
        messages.error(request, 'This application cannot be modified in its current status.')
        return redirect('admin_panel:vendor_application_detail', application_id=application_id)
    
    try:
        application.request_changes(request.user, changes_required, review_notes)
        
        messages.success(request, f'Changes requested successfully. Applicant has been notified.')
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type=ActivityLogType.VENDOR_CHANGES_REQUESTED,
            description=f'Requested changes for vendor application {application.company_name}',
            related_application=application
        )
        
        # Send notification to applicant
        if application.user:
            VendorNotification.objects.create(
                recipient=application.user,
                sender=request.user,
                subject='Changes Required for Vendor Application',
                message=f'Your vendor application for {application.company_name} requires changes: {changes_required}',
                category='vendor_changes',
                priority='medium'
            )
    
    except Exception as e:
        messages.error(request, f'Error requesting changes: {str(e)}')
    
    return redirect('admin_panel:vendor_management')


@login_required
@staff_required
def vendor_performance_view(request, vendor_id):
    """View vendor performance metrics and ratings."""
    
    vendor = get_object_or_404(BusinessPartner, id=vendor_id, type='vendor')
    vendor_profile = get_object_or_404(VendorProfile, business_partner=vendor)
    
    # Get vendor listings
    vendor_listings = VehicleListing.objects.filter(user=vendor.user).order_by('-created_at')
    
    # Calculate performance metrics
    total_listings = vendor_listings.count()
    published_listings = vendor_listings.filter(status='published').count()
    sold_listings = vendor_listings.filter(status='sold').count()
    
    # Calculate sales metrics
    total_sales_value = vendor_listings.filter(status='sold').aggregate(
        total=Sum('price')
    )['total'] or 0
    
    # Calculate average listing time
    sold_listings_with_dates = vendor_listings.filter(
        status='sold', created_at__isnull=False
    ).exclude(sold_at__isnull=True)
    
    avg_listing_days = 0
    if sold_listings_with_dates.exists():
        total_days = sum(
            (listing.sold_at - listing.created_at).days 
            for listing in sold_listings_with_dates
        )
        avg_listing_days = total_days / sold_listings_with_dates.count()
    
    # Get recent customer reviews
    recent_reviews = vendor.received_reviews.select_related('reviewer').order_by('-created_at')[:10]
    
    # Calculate review statistics
    review_stats = vendor.received_reviews.aggregate(
        avg_rating=Avg('rating'),
        total_reviews=Count('id')
    )
    
    # Monthly performance data
    six_months_ago = timezone.now() - timedelta(days=180)
    monthly_performance = []
    
    for i in range(6):
        month_start = six_months_ago + timedelta(days=30*i)
        month_end = month_start + timedelta(days=30)
        
        month_listings = vendor_listings.filter(
            created_at__gte=month_start,
            created_at__lt=month_end
        ).count()
        
        month_sales = vendor_listings.filter(
            status='sold',
            sold_at__gte=month_start,
            sold_at__lt=month_end
        ).count()
        
        monthly_performance.append({
            'month': month_start.strftime('%b %Y'),
            'listings': month_listings,
            'sales': month_sales
        })
    
    context = {
        'vendor': vendor,
        'vendor_profile': vendor_profile,
        'vendor_listings': vendor_listings[:10],  # Last 10 listings
        'total_listings': total_listings,
        'published_listings': published_listings,
        'sold_listings': sold_listings,
        'total_sales_value': total_sales_value,
        'avg_listing_days': round(avg_listing_days, 1),
        'recent_reviews': recent_reviews,
        'review_stats': review_stats,
        'monthly_performance': monthly_performance,
    }
    
    return render(request, 'admin_panel/vendor_performance.html', context)


@login_required
@staff_required
def vendor_documents_view(request, vendor_id):
    """View and manage vendor documents."""
    
    vendor = get_object_or_404(BusinessPartner, id=vendor_id, type='vendor')
    
    # Get all vendor documents
    documents = VendorDocument.objects.filter(
        business_partner=vendor
    ).select_related('category').order_by('-uploaded_at')
    
    # Get pending verifications
    pending_verifications = DocumentVerificationQueue.objects.filter(
        business_partner=vendor,
        completed_at__isnull=True
    ).select_related('assigned_to', 'document')
    
    # Document statistics
    total_documents = documents.count()
    verified_documents = documents.filter(status='verified').count()
    pending_documents = documents.filter(status='pending').count()
    rejected_documents = documents.filter(status='rejected').count()
    expired_documents = documents.filter(
        status='verified',
        expiry_date__lt=timezone.now().date()
    ).count()
    
    context = {
        'vendor': vendor,
        'documents': documents,
        'pending_verifications': pending_verifications,
        'document_stats': {
            'total': total_documents,
            'verified': verified_documents,
            'pending': pending_documents,
            'rejected': rejected_documents,
            'expired': expired_documents,
        }
    }
    
    return render(request, 'admin_panel/vendor_documents.html', context)


@login_required
@staff_required
@require_POST
def verify_vendor_document_view(request, document_id):
    """Verify a vendor document."""
    
    document = get_object_or_404(VendorDocument, id=document_id)
    verification_status = request.POST.get('verification_status')
    verification_notes = request.POST.get('verification_notes', '')
    
    if verification_status not in ['verified', 'rejected']:
        return JsonResponse({'success': False, 'message': 'Invalid verification status'})
    
    try:
        # Update document status
        old_status = document.status
        document.status = verification_status
        document.verified_by = request.user
        document.verified_at = timezone.now()
        document.verification_notes = verification_notes
        document.save()
        
        # Complete any pending verification queue items
        DocumentVerificationQueue.objects.filter(
            document=document,
            completed_at__isnull=True
        ).update(
            completed_at=timezone.now(),
            assigned_to=request.user,
            notes=verification_notes
        )
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type=ActivityLogType.DOCUMENT_VERIFIED if verification_status == 'verified' else ActivityLogType.DOCUMENT_REJECTED,
            description=f'{"Verified" if verification_status == "verified" else "Rejected"} document {document.category.name} for {document.business_partner.name}',
            related_business_partner=document.business_partner
        )
        
        messages.success(request, f'Document {document.category.name} has been {verification_status}.')
        
        return JsonResponse({'success': True})
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@staff_required
def vendor_communication_view(request, vendor_id):
    """View and manage communication with a specific vendor."""
    
    vendor = get_object_or_404(BusinessPartner, id=vendor_id, type='vendor')
    
    # Get all messages with this vendor
    messages_qs = AdminMessage.objects.filter(
        Q(sender=request.user, recipient=vendor.user) |
        Q(sender=vendor.user, recipient=request.user)
    ).select_related('sender', 'recipient').order_by('-created_at')
    
    # Get vendor notifications
    notifications = VendorNotification.objects.filter(
        recipient=vendor.user
    ).select_related('sender').order_by('-created_at')
    
    context = {
        'vendor': vendor,
        'messages': messages_qs[:20],  # Last 20 messages
        'notifications': notifications[:10],  # Last 10 notifications
    }
    
    return render(request, 'admin_panel/vendor_communication.html', context)


# ==================== USER MANAGEMENT VIEWS ====================

@login_required
@staff_required
def users_management_view(request):
    """User management view with filtering and search."""
    
    search = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    
    users = User.objects.all().order_by('-date_joined')
    
    if search:
        users = users.filter(
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    if role_filter:
        users = users.filter(role=role_filter)
    
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    paginator = Paginator(users, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'users': page_obj,
        'search': search,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'role_choices': User.ROLE_CHOICES if hasattr(User, 'ROLE_CHOICES') else [],
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
    }
    
    return render(request, './users/users.html', context)


@login_required
@staff_required
def user_detail_view(request, user_id):
    """View user details."""
    user = get_object_or_404(User, id=user_id)
    context = {'user_obj': user}
    return render(request, './users/user_detail.html', context)


@login_required
@staff_required
@require_POST
def update_user_view(request, user_id):
    """Update user details."""
    user = get_object_or_404(User, id=user_id)
    
    if request.POST.get('role'):
        user.role = request.POST.get('role')
    if request.POST.get('first_name'):
        user.first_name = request.POST.get('first_name')
    if request.POST.get('last_name'):
        user.last_name = request.POST.get('last_name')
    
    user.save()
    messages.success(request, 'User updated successfully.')
    return redirect('admin_panel:user_detail', user_id=user_id)


@login_required
@staff_required
@require_POST
def toggle_user_status_view(request, user_id):
    """Toggle user active status."""
    user = get_object_or_404(User, id=user_id)
    user.is_active = not user.is_active
    user.save()
    
    status = 'activated' if user.is_active else 'deactivated'
    messages.success(request, f'User {status} successfully.')
    return redirect('admin_panel:users')


# ==================== ROLES & PERMISSIONS VIEWS ====================

@login_required
@staff_required
def roles_permissions_view(request):
    """View and manage roles and permissions."""
    from django.contrib.auth.models import Permission, Group
    
    groups = Group.objects.prefetch_related('permissions').all()
    permissions = Permission.objects.select_related('content_type').all()
    
    # Group permissions by category
    permission_categories = {}
    for perm in permissions:
        category = perm.content_type.app_label
        if category not in permission_categories:
            permission_categories[category] = []
        permission_categories[category].append(perm)
    
    context = {
        'groups': groups,
        'permission_categories': permission_categories,
    }
    
    return render(request, './roles/permissions.html', context)


@login_required
@staff_required
@require_POST
def update_role_permissions_view(request):
    """Update role permissions."""
    from django.contrib.auth.models import Group
    
    try:
        data = json.loads(request.body)
        group_id = data.get('group_id')
        permission_ids = data.get('permissions', [])
        
        group = get_object_or_404(Group, id=group_id)
        group.permissions.set(permission_ids)
        
        return JsonResponse({'success': True, 'message': 'Permissions updated successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


# ==================== PARTS MANAGEMENT VIEWS ====================

@login_required
@staff_required
def parts_management_view(request):
    """Parts catalog management with filtering."""
    from parts.models import Part, Category, Brand
    
    search = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    brand_filter = request.GET.get('brand', '')
    status_filter = request.GET.get('status', '')
    
    parts = Part.objects.select_related('category', 'brand', 'vendor').all()
    
    if search:
        parts = parts.filter(
            Q(name__icontains=search) |
            Q(parts_number__icontains=search) |
            Q(sku__icontains=search) |
            Q(material_description__icontains=search)
        )
    
    if category_filter:
        parts = parts.filter(category_id=category_filter)
    
    if brand_filter:
        parts = parts.filter(brand_id=brand_filter)
    
    if status_filter == 'active':
        parts = parts.filter(is_active=True)
    elif status_filter == 'inactive':
        parts = parts.filter(is_active=False)
    elif status_filter == 'low_stock':
        parts = parts.filter(quantity__lte=10)
    
    parts = parts.order_by('-created_at')
    
    paginator = Paginator(parts, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    categories = Category.objects.all()
    brands = Brand.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'parts': page_obj,
        'categories': categories,
        'brands': brands,
        'search': search,
        'category_filter': category_filter,
        'brand_filter': brand_filter,
        'status_filter': status_filter,
        'total_parts': Part.objects.count(),
        'active_parts': Part.objects.filter(is_active=True).count(),
        'low_stock_parts': Part.objects.filter(quantity__lte=10).count(),
    }
    
    return render(request, './catalog/parts.html', context)


@login_required
@staff_required
def part_detail_view(request, part_id):
    """View part details."""
    from parts.models import Part
    part = get_object_or_404(Part, id=part_id)
    context = {'part': part}
    return render(request, './catalog/part_detail.html', context)


@login_required
@staff_required
@require_POST
def update_part_view(request, part_id):
    """Update part details."""
    from parts.models import Part
    part = get_object_or_404(Part, id=part_id)
    
    if request.POST.get('price'):
        part.price = request.POST.get('price')
    if request.POST.get('quantity'):
        part.quantity = request.POST.get('quantity')
    if request.POST.get('is_active') is not None:
        part.is_active = request.POST.get('is_active') == 'true'
    
    part.save()
    messages.success(request, 'Part updated successfully.')
    return redirect('admin_panel:part_detail', part_id=part_id)


@login_required
@staff_required
@require_POST
def delete_part_view(request, part_id):
    """Delete a part."""
    from parts.models import Part
    part = get_object_or_404(Part, id=part_id)
    part.is_active = False
    part.save()
    messages.success(request, 'Part deactivated successfully.')
    return redirect('admin_panel:parts')


# ==================== CATEGORIES & BRANDS VIEWS ====================

@login_required
@staff_required
def categories_view(request):
    """View and manage categories and brands."""
    from parts.models import Category, Brand
    
    categories = Category.objects.annotate(
        parts_count=Count('parts')
    ).order_by('name')
    
    brands = Brand.objects.annotate(
        parts_count=Count('parts')
    ).order_by('name')
    
    context = {
        'categories': categories,
        'brands': brands,
        'total_categories': categories.count(),
        'total_brands': brands.count(),
    }
    
    return render(request, './catalog/categories.html', context)


@login_required
@staff_required
@require_POST
def add_category_view(request):
    """Add a new category."""
    from parts.models import Category
    
    name = request.POST.get('name')
    description = request.POST.get('description', '')
    
    if Category.objects.filter(name=name).exists():
        messages.error(request, 'Category already exists.')
        return redirect('admin_panel:categories')
    
    Category.objects.create(name=name, description=description)
    messages.success(request, 'Category created successfully.')
    return redirect('admin_panel:categories')


@login_required
@staff_required
@require_POST
def update_category_view(request, category_id):
    """Update a category."""
    from parts.models import Category
    category = get_object_or_404(Category, id=category_id)
    
    if request.POST.get('name'):
        category.name = request.POST.get('name')
    if request.POST.get('description'):
        category.description = request.POST.get('description')
    
    category.save()
    messages.success(request, 'Category updated successfully.')
    return redirect('admin_panel:categories')


@login_required
@staff_required
@require_POST
def delete_category_view(request, category_id):
    """Delete a category."""
    from parts.models import Category
    category = get_object_or_404(Category, id=category_id)
    
    if category.parts.exists():
        messages.error(request, 'Cannot delete category with existing parts.')
        return redirect('admin_panel:categories')
    
    category.delete()
    messages.success(request, 'Category deleted successfully.')
    return redirect('admin_panel:categories')


@login_required
@staff_required
@require_POST
def add_brand_view(request):
    """Add a new brand."""
    from parts.models import Brand
    
    name = request.POST.get('name')
    description = request.POST.get('description', '')
    
    if Brand.objects.filter(name=name).exists():
        messages.error(request, 'Brand already exists.')
        return redirect('admin_panel:categories')
    
    Brand.objects.create(name=name, description=description)
    messages.success(request, 'Brand created successfully.')
    return redirect('admin_panel:categories')


@login_required
@staff_required
@require_POST
def update_brand_view(request, brand_id):
    """Update a brand."""
    from parts.models import Brand
    brand = get_object_or_404(Brand, id=brand_id)
    
    if request.POST.get('name'):
        brand.name = request.POST.get('name')
    if request.POST.get('description'):
        brand.description = request.POST.get('description')
    if request.POST.get('is_active') is not None:
        brand.is_active = request.POST.get('is_active') == 'true'
    
    brand.save()
    messages.success(request, 'Brand updated successfully.')
    return redirect('admin_panel:categories')


@login_required
@staff_required
@require_POST
def delete_brand_view(request, brand_id):
    """Delete a brand."""
    from parts.models import Brand
    brand = get_object_or_404(Brand, id=brand_id)
    brand.is_active = False
    brand.save()
    messages.success(request, 'Brand deactivated successfully.')
    return redirect('admin_panel:categories')


# ==================== ORDERS MANAGEMENT VIEWS ====================

@login_required
@staff_required
def orders_management_view(request):
    """Orders management with filtering."""
    from parts.models import Order
    
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    payment_filter = request.GET.get('payment', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    orders = Order.objects.select_related('customer').prefetch_related('items').all()
    
    if search:
        orders = orders.filter(
            Q(order_number__icontains=search) |
            Q(customer__email__icontains=search) |
            Q(guest_email__icontains=search)
        )
    
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    if payment_filter:
        orders = orders.filter(payment_status=payment_filter)
    
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)
    
    orders = orders.order_by('-created_at')
    
    paginator = Paginator(orders, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    order_stats = {
        'total': Order.objects.count(),
        'pending': Order.objects.filter(status='pending').count(),
        'processing': Order.objects.filter(status='processing').count(),
        'shipped': Order.objects.filter(status='shipped').count(),
        'delivered': Order.objects.filter(status='delivered').count(),
        'cancelled': Order.objects.filter(status='cancelled').count(),
        'total_revenue': Order.objects.filter(status='delivered').aggregate(total=Sum('total_price'))['total'] or 0,
    }
    
    context = {
        'page_obj': page_obj,
        'orders': page_obj,
        'order_stats': order_stats,
        'status_choices': Order.STATUS_CHOICES,
        'payment_status_choices': Order.PAYMENT_STATUS_CHOICES,
        'search': search,
        'status_filter': status_filter,
        'payment_filter': payment_filter,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, './catalog/orders.html', context)


@login_required
@staff_required
def order_detail_view(request, order_id):
    """View order details."""
    from parts.models import Order
    order = get_object_or_404(Order, id=order_id)
    context = {'order': order}
    return render(request, './catalog/order_detail.html', context)


@login_required
@staff_required
@require_POST
def update_order_status_view(request, order_id):
    """Update order status."""
    from parts.models import Order
    order = get_object_or_404(Order, id=order_id)
    
    new_status = request.POST.get('status')
    reason = request.POST.get('reason', '')
    
    if new_status in dict(Order.STATUS_CHOICES):
        order.update_status(new_status, changed_by=request.user, change_reason=reason, request=request)
        messages.success(request, f'Order status updated to {new_status}.')
    else:
        messages.error(request, 'Invalid status.')
    
    return redirect('admin_panel:order_detail', order_id=order_id)


# ==================== INVENTORY MANAGEMENT VIEWS ====================

@login_required
@staff_required
def inventory_management_view(request):
    """Inventory management with stock levels."""
    from parts.models import Inventory, Part
    
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    inventory = Inventory.objects.select_related('part', 'part__category').all()
    
    if search:
        inventory = inventory.filter(
            Q(part__name__icontains=search) |
            Q(part__parts_number__icontains=search) |
            Q(part__sku__icontains=search)
        )
    
    if status_filter == 'low':
        inventory = inventory.filter(stock__lte=models.F('reorder_level'))
    elif status_filter == 'out':
        inventory = inventory.filter(stock=0)
    elif status_filter == 'in_stock':
        inventory = inventory.filter(stock__gt=models.F('reorder_level'))
    
    inventory = inventory.order_by('stock')
    
    paginator = Paginator(inventory, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    inventory_stats = {
        'total_items': Inventory.objects.count(),
        'low_stock': Inventory.objects.filter(stock__lte=models.F('reorder_level')).count(),
        'out_of_stock': Inventory.objects.filter(stock=0).count(),
        'total_stock_value': 0,  # Calculate if needed
    }
    
    context = {
        'page_obj': page_obj,
        'inventory': page_obj,
        'inventory_stats': inventory_stats,
        'search': search,
        'status_filter': status_filter,
    }
    
    return render(request, './catalog/inventory.html', context)


@login_required
@staff_required
@require_POST
def update_inventory_view(request, inventory_id):
    """Update inventory stock."""
    from parts.models import Inventory
    inventory = get_object_or_404(Inventory, id=inventory_id)
    
    if request.POST.get('stock'):
        inventory.stock = int(request.POST.get('stock'))
    if request.POST.get('reorder_level'):
        inventory.reorder_level = int(request.POST.get('reorder_level'))
    
    inventory.save()
    messages.success(request, 'Inventory updated successfully.')
    return redirect('admin_panel:inventory')


# ==================== REVIEWS MANAGEMENT VIEWS ====================

@login_required
@staff_required
def reviews_management_view(request):
    """Reviews moderation view."""
    from parts.models import Review
    
    status_filter = request.GET.get('status', '')
    rating_filter = request.GET.get('rating', '')
    
    reviews = Review.objects.select_related('part', 'user').all()
    
    if status_filter == 'pending':
        reviews = reviews.filter(is_approved=False)
    elif status_filter == 'approved':
        reviews = reviews.filter(is_approved=True)
    
    if rating_filter:
        reviews = reviews.filter(rating=int(rating_filter))
    
    reviews = reviews.order_by('-created_at')
    
    paginator = Paginator(reviews, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'reviews': page_obj,
        'status_filter': status_filter,
        'rating_filter': rating_filter,
        'total_reviews': Review.objects.count(),
        'pending_reviews': Review.objects.filter(is_approved=False).count(),
        'avg_rating': Review.objects.aggregate(avg=Avg('rating'))['avg'] or 0,
    }
    
    return render(request, './feedback/reviews.html', context)


@login_required
@staff_required
@require_POST
def approve_review_view(request, review_id):
    """Approve a review."""
    from parts.models import Review
    review = get_object_or_404(Review, id=review_id)
    review.is_approved = True
    review.save()
    messages.success(request, 'Review approved.')
    return redirect('admin_panel:reviews')


@login_required
@staff_required
@require_POST
def reject_review_view(request, review_id):
    """Reject a review."""
    from parts.models import Review
    review = get_object_or_404(Review, id=review_id)
    review.is_approved = False
    review.save()
    messages.success(request, 'Review rejected.')
    return redirect('admin_panel:reviews')


# ==================== BULK UPLOAD VIEWS ====================

@login_required
@staff_required
def bulk_upload_view(request):
    """Bulk upload interface."""
    from parts.models import BulkUploadLog
    
    recent_uploads = BulkUploadLog.objects.filter(
        user=request.user
    ).order_by('-uploaded_at')[:10]
    
    context = {
        'recent_uploads': recent_uploads,
    }
    
    return render(request, './tools/bulkupload.html', context)


@login_required
@staff_required
@require_POST
def process_bulk_upload_view(request):
    """Process a bulk upload file."""
    from parts.models import BulkUploadLog
    
    if 'file' not in request.FILES:
        messages.error(request, 'No file provided.')
        return redirect('admin_panel:bulk_upload')
    
    uploaded_file = request.FILES['file']
    
    # Create upload log
    upload_log = BulkUploadLog.objects.create(
        user=request.user,
        file_name=uploaded_file.name,
        file_size=uploaded_file.size,
        status='processing'
    )
    
    # TODO: Process the file (CSV/Excel parsing)
    # For now, just mark as completed
    upload_log.status = 'completed'
    upload_log.save()
    
    messages.success(request, 'File uploaded successfully. Processing started.')
    return redirect('admin_panel:bulk_upload')


# ==================== INVOICES & FINANCE VIEWS ====================

@login_required
@staff_required
def invoices_view(request):
    """Invoices view (derived from completed orders)."""
    from parts.models import Order
    
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    # Invoices are based on paid orders
    orders = Order.objects.filter(
        payment_status='completed'
    ).select_related('customer').order_by('-created_at')
    
    if search:
        orders = orders.filter(
            Q(order_number__icontains=search) |
            Q(customer__email__icontains=search)
        )
    
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    paginator = Paginator(orders, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    invoice_stats = {
        'total': orders.count(),
        'total_revenue': orders.aggregate(total=Sum('total_price'))['total'] or 0,
        'total_tax': orders.aggregate(total=Sum('tax_amount'))['total'] or 0,
    }
    
    context = {
        'page_obj': page_obj,
        'invoices': page_obj,
        'invoice_stats': invoice_stats,
        'search': search,
        'status_filter': status_filter,
    }
    
    return render(request, './finance/invoices.html', context)


@login_required
@staff_required
def invoice_detail_view(request, order_id):
    """View invoice details (order-based)."""
    from parts.models import Order
    order = get_object_or_404(Order, id=order_id, payment_status='completed')
    context = {'order': order, 'invoice': order}
    return render(request, './finance/invoice_detail.html', context)


# ==================== TAX RULES VIEWS ====================

@login_required
@staff_required
def taxes_view(request):
    """Tax rules configuration."""
    from .models import AdminSetting
    
    # Get tax settings from AdminSetting model
    tax_settings = AdminSetting.objects.filter(
        key__startswith='tax_'
    ).order_by('key')
    
    context = {
        'tax_settings': tax_settings,
    }
    
    return render(request, './finance/taxes.html', context)


@login_required
@staff_required
@require_POST
def add_tax_rule_view(request):
    """Add a tax rule."""
    from .models import AdminSetting
    
    key = request.POST.get('key')
    value = request.POST.get('value')
    description = request.POST.get('description', '')
    
    AdminSetting.objects.update_or_create(
        key=f'tax_{key}',
        defaults={
            'value': value,
            'description': description,
            'value_type': 'float',
            'updated_by': request.user,
        }
    )
    
    messages.success(request, 'Tax rule saved.')
    return redirect('admin_panel:taxes')


@login_required
@staff_required
@require_POST
def update_tax_rule_view(request, tax_id):
    """Update a tax rule."""
    from .models import AdminSetting
    
    setting = get_object_or_404(AdminSetting, id=tax_id)
    setting.value = request.POST.get('value', setting.value)
    setting.description = request.POST.get('description', setting.description)
    setting.updated_by = request.user
    setting.save()
    
    messages.success(request, 'Tax rule updated.')
    return redirect('admin_panel:taxes')


# ==================== BUSINESS PARTNERS VIEWS ====================

@login_required
@staff_required
def partners_view(request):
    """Business partners management."""
    
    search = request.GET.get('search', '')
    type_filter = request.GET.get('type', '')
    status_filter = request.GET.get('status', '')
    
    partners = (
        BusinessPartner.objects.select_related('user')
        .prefetch_related('roles')
        .annotate(
            has_vendor=Exists(
                BusinessPartnerRole.objects.filter(
                    business_partner=OuterRef('pk'),
                    role_type='vendor',
                )
            )
        )
    )
    
    if search:
        partners = partners.filter(
            Q(name__icontains=search) |
            Q(bp_number__icontains=search) |
            Q(user__email__icontains=search)
        )
    
    if type_filter:
        partners = partners.filter(type=type_filter)
    
    if status_filter:
        partners = partners.filter(status=status_filter)
    
    partners = partners.order_by('-created_at')
    
    paginator = Paginator(partners, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    partner_stats = {
        'total': BusinessPartner.objects.count(),
        'vendors': BusinessPartner.objects.filter(roles__role_type='vendor').distinct().count(),
        'customers': BusinessPartner.objects.filter(roles__role_type='customer').distinct().count(),
        'pending': BusinessPartner.objects.filter(status='pending').count(),
    }
    
    context = {
        'page_obj': page_obj,
        'partners': page_obj,
        'partner_stats': partner_stats,
        'type_choices': BusinessPartner.PARTNER_TYPES,
        'status_choices': BusinessPartner.STATUS_CHOICES,
        'search': search,
        'type_filter': type_filter,
        'status_filter': status_filter,
    }
    
    return render(request, './partners/business-partners.html', context)


@login_required
@staff_required
def partner_detail_view(request, partner_id):
    """View partner details."""
    partner = get_object_or_404(BusinessPartner, id=partner_id)
    
    context = {
        'partner': partner,
        'contacts': partner.contacts.all() if hasattr(partner, 'contacts') else [],
        'addresses': partner.addresses.all() if hasattr(partner, 'addresses') else [],
        'documents': partner.documents.all() if hasattr(partner, 'documents') else [],
    }
    
    return render(request, './partners/partner_detail.html', context)

