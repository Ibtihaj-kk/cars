from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.db.models import Q, Count, Avg, Exists, OuterRef, Subquery, F, Sum
from django.db import models, transaction
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from django import forms
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.urls import reverse
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from datetime import datetime, timedelta
from decimal import Decimal
import json

# Local app models
from listings.models import VehicleListing, ListingStatusLog
from users.models import User
from vehicles.models import Brand, VehicleModel
from business_partners.models import (
    BusinessPartner, BusinessPartnerRole, ContactInfo, 
    VendorProfile, VendorApplication
)
from business_partners.document_models import VendorDocument, DocumentVerificationQueue
from business_partners.audit_logger import VendorAuditLogger
from inquiries.models import ListingInquiry, InquiryStatus
from notifications.models import Notification, NotificationType, NotificationPriority
from finance.models import Wallet, Transaction, EscrowEntry, CODSettlementRequest, FinancialAuditLog
from finance.services import FinanceService
from core.models import Currency, ExchangeRate

# Admin panel local models/utils
from .payment_models import (
    VendorPayment, CommissionRule, PaymentBatch, PaymentHistory, 
    VendorBalance, PaymentStatus, PaymentMethod
)
from .messaging_models import (
    AdminMessage, MessageTemplate, VendorNotification, 
    MessageStatus, MessagePriority, MessageCategory
)
from .models import ActivityLog, ActivityLogType, DashboardWidget
from .utils import (
    log_activity, log_listing_activity, log_bulk_listing_activity,
    log_status_change_activity, log_feature_toggle_activity
)
from .decorators import (
    admin_required, staff_required, superuser_required, can_manage_listings, 
    can_view_analytics, can_view_audit_logs, ajax_admin_required
)
from .session_manager import require_valid_admin_session
from .audit_logger import AdminAuditLogger, audit_admin_action

# Import email views for URL routing
from .email_views import (
    email_console, email_queue, email_analytics,
    send_manual_email, send_bulk_email, retry_failed_email,
    cancel_email, clear_email_queue
)


def verify_vendor_bank_view(request, vendor_id):
    """Verify vendor bank details by admin."""
    if not request.user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    
    vendor = get_object_or_404(BusinessPartner, id=vendor_id)
    try:
        profile = vendor.vendor_profile
        profile.bank_details_verified = True
        profile.bank_verification_date = timezone.now()
        profile.bank_verified_by = request.user
        profile.save(update_fields=['bank_details_verified', 'bank_verification_date', 'bank_verified_by'], user=request.user)
        
        # Log the verification
        VendorAuditLogger.log_vendor_action(
            action_type='bank_details_verified',
            user=request.user,
            vendor=vendor,
            details={'message': 'Bank details verified by admin'}
        )
        
        return JsonResponse({'status': 'success', 'message': f'Bank details for {vendor.business_name} verified successfully'})
    except VendorProfile.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Vendor profile not found'}, status=404)


def is_admin_user(user):
    """Check if user is admin or staff."""
    return user.is_authenticated and (user.is_staff or user.is_superuser)

PER_PAGE_OPTIONS = (10, 20, 25, 50, 100)


def get_per_page_param(request, default):
    value = request.GET.get('per_page')
    if value is None or value == '':
        return default
    try:
        per_page = int(value)
    except (TypeError, ValueError):
        return default
    return per_page if per_page in PER_PAGE_OPTIONS else default


def _get_display_currency_code(request):
    currency_obj = getattr(request, "currency", None)
    code = getattr(currency_obj, "code", None)
    if code:
        return code
    session = getattr(request, "session", None)
    if session is not None:
        code = session.get("currency_code")
        if code:
            return code
    return "USD"


def _get_base_currency_code():
    base = Currency.objects.filter(is_active=True, is_base=True).first()
    if base:
        return base.code
    any_active = Currency.objects.filter(is_active=True).order_by("code").first()
    if any_active:
        return any_active.code
    return "USD"


def _as_decimal(value):
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    return Decimal(text)


def _as_decimal_with_default(value, default):
    parsed = _as_decimal(value)
    return parsed if parsed is not None else default


def _rate_decimal(base_code, target_code):
    rate = ExchangeRate.get_current_rate(base_code, target_code)
    return Decimal(str(rate))


def _convert_display_to_base(amount_display, display_code, base_code):
    if amount_display is None:
        return None
    if display_code == base_code:
        return amount_display
    rate = _rate_decimal(base_code, display_code)
    return amount_display / rate


def _convert_base_to_display(amount_base, display_code, base_code):
    if amount_base is None:
        return None
    if display_code == base_code:
        return amount_base
    rate = _rate_decimal(base_code, display_code)
    return amount_base * rate


def get_pagination_query_string(request):
    params = request.GET.copy()
    params.pop('page', None)
    return params.urlencode()


def get_preserved_query_params(request):
    preserved = []
    for key in request.GET.keys():
        if key in {'page', 'per_page'}:
            continue
        for value in request.GET.getlist(key):
            preserved.append((key, value))
    return preserved


class AdminProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone_number")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_classes = "w-full bg-white border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-black/10"
        for name, field in self.fields.items():
            field.widget.attrs.setdefault("class", base_classes)
            if name == "first_name":
                field.widget.attrs.setdefault("placeholder", "First name")
            if name == "last_name":
                field.widget.attrs.setdefault("placeholder", "Last name")
            if name == "phone_number":
                field.widget.attrs.setdefault("placeholder", "Phone number")


@admin_required(min_role="staff")
@require_valid_admin_session
@require_http_methods(["GET", "POST"])
@audit_admin_action(ActivityLogType.VIEW, "Accessed admin settings")
def admin_settings_view(request):
    user = request.user
    profile_form = AdminProfileForm(instance=user)
    password_form = PasswordChangeForm(user=user)
    base_classes = "w-full bg-white border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-black/10"
    for field in password_form.fields.values():
        field.widget.attrs.setdefault("class", base_classes)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "update_profile":
            profile_form = AdminProfileForm(request.POST, instance=user)
            password_form = PasswordChangeForm(user=user)
            for field in password_form.fields.values():
                field.widget.attrs.setdefault("class", base_classes)
            if profile_form.is_valid():
                profile_form.save()
                log_activity(
                    user=user,
                    action_type=ActivityLogType.UPDATE,
                    description="Updated admin profile",
                    request=request,
                )
                messages.success(request, "Profile updated successfully.")
                return redirect("admin_panel:settings")

        elif action == "change_password":
            profile_form = AdminProfileForm(instance=user)
            password_form = PasswordChangeForm(user=user, data=request.POST)
            for field in password_form.fields.values():
                field.widget.attrs.setdefault("class", base_classes)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, user)
                log_activity(
                    user=user,
                    action_type=ActivityLogType.UPDATE,
                    description="Changed admin password",
                    request=request,
                )
                messages.success(request, "Password changed successfully.")
                return redirect("admin_panel:settings")

        else:
            messages.error(request, "Invalid action.")
            return redirect("admin_panel:settings")

    context = {
        "profile_form": profile_form,
        "password_form": password_form,
    }
    return render(request, "admin_panel/settings.html", context)


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
    vendors_qs = BusinessPartner.objects.filter(roles__role_type='vendor').distinct()
    total_vendors = vendors_qs.count()
    pending_vendors = vendors_qs.filter(status='pending').count()
    approved_vendors = vendors_qs.filter(status='active').count()
    rejected_vendors = 0
    
    # Vendor Application metrics
    total_applications = VendorApplication.objects.count()
    # Note: 'submitted' status is what VendorApplication uses for pending review
    pending_applications = VendorApplication.objects.filter(status='submitted').count()
    under_review_applications = VendorApplication.objects.filter(status='under_review').count()
    approved_applications = VendorApplication.objects.filter(status='approved').count()
    rejected_applications = VendorApplication.objects.filter(status='rejected').count()
    requires_changes_applications = VendorApplication.objects.filter(status='requires_changes').count()
    
    # Vendor Performance metrics
    active_vendors = vendors_qs.filter(status='active', user__is_active=True).count()
    
    # Vendor with listings (simplified - count active vendors)
    vendors_with_listings = vendors_qs.filter(user__listings__isnull=False).distinct().count()
    
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
    recent_vendors = vendors_qs.select_related('user').order_by('-created_at')[:5]
    
    # Popular makes
    popular_makes = VehicleListing.objects.filter(status='published').values('make__name').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Status distribution
    status_distribution = VehicleListing.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Vendor status distribution
    vendor_status_distribution = vendors_qs.values('status').annotate(
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
        count = vendors_qs.filter(created_at__gte=month_start, created_at__lt=month_end).count()
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
    legacy_total_payments = VendorPayment.objects.count()
    legacy_pending_payments = VendorPayment.objects.filter(status='pending').count()
    legacy_completed_payments = VendorPayment.objects.filter(status='completed').count()
    legacy_total_commission_earned = VendorPayment.objects.filter(
        status='completed'
    ).aggregate(total=Sum('commission_amount'))['total'] or Decimal('0.00')
    
    unified_total_payments = Transaction.objects.filter(transaction_type='PAYOUT').count()
    unified_completed_payments = unified_total_payments # Transactions are completed ledger entries
    unified_total_commission = Transaction.objects.filter(
        transaction_type='COMMISSION'
    ).aggregate(total=Sum('amount_base'))['total'] or Decimal('0.00')

    total_payments = legacy_total_payments + unified_total_payments
    pending_payments = legacy_pending_payments
    completed_payments = legacy_completed_payments + unified_completed_payments
    total_commission_earned = legacy_total_commission_earned + unified_total_commission
    
    total_commission_rules = CommissionRule.objects.count()
    active_commission_rules = CommissionRule.objects.filter(is_active=True).count()
    
    # Recent payments (Combined)
    legacy_recent = VendorPayment.objects.select_related('vendor').order_by('-created_at')[:5]
    unified_recent = Transaction.objects.filter(transaction_type='PAYOUT').order_by('-created_at')[:5]
    
    recent_payments_list = []
    for lp in legacy_recent:
        recent_payments_list.append({
            'vendor': lp.vendor,
            'amount': lp.net_amount,
            'status': lp.status,
            'created_at': lp.created_at,
            'reference': lp.payment_reference,
            'is_unified': False
        })
    for ut in unified_recent:
        # Payout destination is usually vendor wallet, so ut.source_wallet owner is platform, 
        # and ut.destination_wallet owner is vendor.
        vendor = None
        if ut.destination_wallet and ut.destination_wallet.owner_content_type.model == 'businesspartner':
            vendor = ut.destination_wallet.owner
        
        recent_payments_list.append({
            'vendor': vendor,
            'amount': ut.amount_base,
            'status': 'completed',
            'created_at': ut.created_at,
            'reference': f"TRX-{ut.id}",
            'is_unified': True
        })
    
    recent_payments_list.sort(key=lambda x: x['created_at'], reverse=True)
    recent_payments = recent_payments_list[:5]
    
    # Vendor balance summary
    legacy_total_balance = VendorBalance.objects.aggregate(total=Sum('current_balance'))['total'] or Decimal('0.00')
    unified_total_balance = Wallet.objects.aggregate(total=Sum('available_balance'))['total'] or Decimal('0.00')
    total_vendor_balance = legacy_total_balance + unified_total_balance
    
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
    per_page = get_per_page_param(request, 25)
    paginator = Paginator(listings, per_page)
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
        'per_page': per_page,
        'per_page_options': PER_PAGE_OPTIONS,
        'query_string': get_pagination_query_string(request),
        'preserved_query_params': get_preserved_query_params(request),
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
    """Process multiple payments in batch using the unified PaymentBatch model"""
    try:
        name = request.POST.get('name', f"Batch {timezone.now().strftime('%Y-%m-%d %H:%M')}")
        description = request.POST.get('description', '')
        payment_ids = request.POST.getlist('payment_ids')
        
        if not payment_ids:
            return JsonResponse({'success': False, 'message': 'No payments selected'})
            
        # Get pending payments
        payments = VendorPayment.objects.filter(id__in=payment_ids, status=PaymentStatus.PENDING)
        
        if not payments.exists():
            return JsonResponse({'success': False, 'message': 'No valid pending payments found'})
        
        # Create payment batch
        batch = PaymentBatch.objects.create(
            name=name,
            description=description,
            total_payments=payments.count(),
            total_amount=payments.aggregate(total=Sum('net_amount'))['total'] or 0,
            created_by=request.user
        )
        
        # Add payments to batch
        batch.payments.set(payments)
        
        # Process the batch using the model method
        success_count, fail_count = batch.process_batch(request.user)
        
        return JsonResponse({
            'success': True, 
            'message': f'Batch processing completed. Success: {success_count}, Failed: {fail_count}',
            'batch_id': batch.id,
            'success_count': success_count,
            'fail_count': fail_count
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def export_payment_batch_csv(request, batch_id):
    """Export a payment batch to CSV for bank upload"""
    import csv
    from django.http import HttpResponse
    
    try:
        batch = PaymentBatch.objects.get(id=batch_id)
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="payout_batch_{batch.batch_reference}.csv"'
        
        writer = csv.writer(response)
        # Header for bank upload - usually specific to the bank, but we'll use a standard format
        writer.writerow([
            'Payment Reference', 'Vendor Name', 'Bank Name', 'Account Holder', 
            'Account Number', 'IBAN', 'SWIFT', 'Amount', 'Currency', 'Status'
        ])
        
        for payment in batch.payments.all():
            vendor = payment.vendor
            try:
                profile = vendor.vendor_profile
                bank_name = profile.bank_name or ''
                acc_holder = profile.bank_account_holder_name or ''
                acc_num = profile.bank_account_number or ''
                iban = profile.iban or ''
                swift = profile.swift_code or ''
            except Exception:
                bank_name = acc_holder = acc_num = iban = swift = 'N/A'
                
            writer.writerow([
                payment.payment_reference,
                vendor.business_name,
                bank_name,
                acc_holder,
                acc_num,
                iban,
                swift,
                payment.net_amount,
                'USD', # Base currency
                payment.status
            ])
            
        return response
        
    except PaymentBatch.DoesNotExist:
        return HttpResponse("Batch not found", status=404)
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)


@login_required
def finance_ledger_view(request):
    """
    Centralized Finance Ledger for MasterAdmin.
    """
    transactions = Transaction.objects.all().select_related('source_wallet', 'destination_wallet')
    
    # Filters
    txn_type = request.GET.get('type')
    if txn_type:
        transactions = transactions.filter(transaction_type=txn_type)
        
    date_from = request.GET.get('date_from')
    if date_from:
        transactions = transactions.filter(created_at__date__gte=date_from)
        
    date_to = request.GET.get('date_to')
    if date_to:
        transactions = transactions.filter(created_at__date__lte=date_to)

    # Summary Stats
    platform_wallet = FinanceService.get_platform_wallet()
    stats = {
        'total_revenue': platform_wallet.available_balance,
        'escrow_total': Wallet.objects.aggregate(total=Sum('escrow_balance'))['total'] or 0,
        'liability_total': Wallet.objects.aggregate(total=Sum('liability_balance'))['total'] or 0,
    }

    context = {
        'transactions': transactions,
        'stats': stats,
        'txn_types': Transaction.TYPES,
    }
    return render(request, 'admin_panel/finance/ledger.html', context)

@login_required
def wallets_management_view(request):
    """
    Manage all wallets (Vendors, Admin).
    """
    from business_partners.models import BusinessPartner
    from decimal import Decimal
    from django.db.models import DecimalField, F, OuterRef, Subquery, Sum, Value
    from django.db.models.functions import Coalesce

    try:
        FinanceService.get_platform_wallet()
    except Exception:
        pass

    vendors = BusinessPartner.objects.filter(roles__role_type='vendor').distinct()
    for vendor in vendors:
        try:
            FinanceService.get_or_create_wallet(vendor)
        except Exception:
            continue

    try:
        FinanceService.sync_legacy_vendor_payments(limit=5000)
    except Exception:
        pass

    wallets_qs = (
        Wallet.objects.select_related('owner_content_type')
        .annotate(
            virtual_credits=Coalesce(
                Subquery(
                    Transaction.objects.filter(
                        destination_wallet=OuterRef('pk'),
                        status='completed',
                        transaction_type__in=['PAYMENT', 'ESCROW_RELEASE', 'ADJUSTMENT', 'COMMISSION', 'COD_SETTLEMENT', 'SUBSCRIPTION'],
                    )
                    .values('destination_wallet')
                    .annotate(total=Sum('amount_base'))
                    .values('total')[:1],
                    output_field=DecimalField(max_digits=15, decimal_places=2),
                ),
                Value(Decimal('0.00')),
                output_field=DecimalField(max_digits=15, decimal_places=2),
            ),
            virtual_debits=Coalesce(
                Subquery(
                    Transaction.objects.filter(
                        source_wallet=OuterRef('pk'),
                        status='completed',
                        transaction_type__in=['PAYOUT', 'REFUND', 'ADJUSTMENT', 'COD_SETTLEMENT', 'COMMISSION'],
                    )
                    .values('source_wallet')
                    .annotate(total=Sum('amount_base'))
                    .values('total')[:1],
                    output_field=DecimalField(max_digits=15, decimal_places=2),
                ),
                Value(Decimal('0.00')),
                output_field=DecimalField(max_digits=15, decimal_places=2),
            ),
        )
        .annotate(
            virtual_balance=F('virtual_credits') - F('virtual_debits')
        )
        .all()
        .order_by('-virtual_balance', '-available_balance', '-escrow_balance', '-liability_balance', '-updated_at')
    )
    
    # Search
    query = request.GET.get('q')
    if query:
        q = query.strip().lower()
        wallets = [
            w
            for w in wallets_qs
            if q in (str(getattr(w, 'owner', '')) or '').lower()
            or q in (str(getattr(getattr(w, 'owner_content_type', None), 'model', '')) or '').lower()
            or q in str(getattr(w, 'owner_id', '') or '')
        ]
    else:
        wallets = wallets_qs

    context = {
        'wallets': wallets,
    }
    return render(request, 'admin_panel/finance/wallets.html', context)

@login_required
def escrow_management_view(request):
    """
    Manage escrow releases.
    """
    escrow_entries = EscrowEntry.objects.filter(is_released=False).order_by('release_date')
    
    context = {
        'escrow_entries': escrow_entries,
        'now': timezone.now(),
    }
    return render(request, 'admin_panel/finance/escrow.html', context)


@login_required
def admin_cod_settlements_view(request):
    """View for admins to review and process COD settlements."""
    if not request.user.is_staff:
        return redirect('admin_panel:dashboard')
        
    status_filter = request.GET.get('status', 'pending')
    requests = CODSettlementRequest.objects.filter(status=status_filter).order_by('-created_at')
    
    if request.method == 'POST':
        request_id = request.POST.get('request_id')
        action = request.POST.get('action') # 'approved' or 'rejected'
        notes = request.POST.get('notes', '')
        
        settlement_req = get_object_or_404(CODSettlementRequest, id=request_id)
        
        try:
            FinanceService.process_cod_settlement(
                settlement_req, 
                action, 
                request.user, 
                notes
            )
            messages.success(request, f"Settlement request {action} successfully.")
        except Exception as e:
            messages.error(request, f"Error processing settlement: {str(e)}")
            
        return redirect('admin_panel:finance_cod_settlements')
        
    return render(request, 'admin_panel/finance/cod_settlements.html', {
        'settlement_requests': requests, 
        'status_filter': status_filter
    })


@login_required
def financial_audit_logs_view(request):
    """
    View for high-level financial audit logs.
    """
    logs = FinancialAuditLog.objects.all().select_related('user', 'wallet')
    
    # Filters
    action_type = request.GET.get('action_type')
    if action_type:
        logs = logs.filter(action_type=action_type)
        
    context = {
        'logs': logs,
        'action_types': FinancialAuditLog.ACTION_TYPES,
    }
    return render(request, 'admin_panel/finance/audit_logs.html', context)


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
    per_page = get_per_page_param(request, 50)
    paginator = Paginator(logs, per_page)
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
        },
        'per_page': per_page,
        'per_page_options': PER_PAGE_OPTIONS,
        'query_string': get_pagination_query_string(request),
        'preserved_query_params': get_preserved_query_params(request),
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
    # Get tab and filter parameters
    tab = request.GET.get('tab', 'all')
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    
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
    
    # Filter based on tab
    if tab == 'pending':
        vendors = vendors.filter(status='pending')
    elif tab == 'applications':
        vendors = vendors.filter(status__in=['pending', 'submitted', 'under_review'])
    
    # Apply status filter if provided
    if status_filter:
        vendors = vendors.filter(status=status_filter)
    
    # Apply search filter
    if search_query:
        vendors = vendors.filter(
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(name__icontains=search_query)
        )
    
    # Order by creation date (newest first)
    vendors = vendors.order_by('-created_at')
    
    # Pagination
    per_page = get_per_page_param(request, 25)
    paginator = Paginator(vendors, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    status_choices = BusinessPartner.STATUS_CHOICES if hasattr(BusinessPartner, 'STATUS_CHOICES') else []
    
    # Calculate vendor statistics
    total_vendors = vendors_base.count()
    active_vendors = vendors_base.filter(status='active').count()
    pending_vendors = vendors_base.filter(status='pending').count()
    inactive_vendors = vendors_base.filter(status='inactive').count()
    suspended_vendors = vendors_base.filter(status='suspended').count()
    
    context = {
        'vendors': page_obj,
        'page_obj': page_obj,
        'tab': tab,
        'search': search_query,
        'status_filter': status_filter,
        'status_choices': status_choices,
        'total_vendors': total_vendors,
        'active_vendors': active_vendors,
        'pending_vendors': pending_vendors,
        'inactive_vendors': inactive_vendors,
        'suspended_vendors': suspended_vendors,
        'per_page': per_page,
        'per_page_options': PER_PAGE_OPTIONS,
        'query_string': get_pagination_query_string(request),
        'preserved_query_params': get_preserved_query_params(request),
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
    
    # Get related listings if vendor is a dealer - get full queryset first for counts
    all_listings = VehicleListing.objects.filter(user=vendor.user).order_by('-created_at')
    
    # Calculate vendor metrics before slicing
    total_listings = all_listings.count()
    active_listings = all_listings.filter(status='published').count()

    vendor_inquiries = ListingInquiry.objects.filter(listing__user=vendor.user)
    total_inquiries = vendor_inquiries.count()
    replied_inquiries = vendor_inquiries.filter(
        Q(status=InquiryStatus.REPLIED) | Q(responses__isnull=False)
    ).distinct().count()
    response_rate = round((replied_inquiries / total_inquiries) * 100, 1) if total_inquiries else 0.0
    
    # Now slice for display
    listings = all_listings[:10]
    
    context = {
        'vendor': vendor,
        'roles': roles,
        'contact_info': contact_info,
        'listings': listings,
        'metrics': {
            'total_listings': total_listings,
            'active_listings': active_listings,
            'total_inquiries': total_inquiries,
            'replied_inquiries': replied_inquiries,
            'response_rate': response_rate,
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
    
    # Also update any related VendorApplication status
    # Map BusinessPartner status to VendorApplication status
    application_status_map = {
        'active': 'approved',
        'inactive': 'rejected',
        'suspended': 'rejected',
    }
    
    if new_status in application_status_map:
        app_status = application_status_map[new_status]
        # Find application by user
        VendorApplication.objects.filter(
            user=vendor.user,
            status__in=['submitted', 'under_review', 'pending', 'draft']
        ).update(
            status=app_status,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
            approved_at=timezone.now() if app_status == 'approved' else None,
            rejection_reason=reason if app_status == 'rejected' else None
        )
    
    # Also update VendorProfile.is_approved (this controls vendor dashboard display)
    try:
        vendor_profile = vendor.vendor_profile
        approval_state_map = {
            'active': 'APPROVED',
            'inactive': 'REJECTED',
            'suspended': 'SUSPENDED',
            'pending': 'PENDING',
        }
        if new_status in approval_state_map:
            vendor_profile.approval_state = approval_state_map[new_status]
            vendor_profile.save()
    except Exception:
        pass  # VendorProfile may not exist
    
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
    """View vendor applications for approval."""
    search = request.GET.get('search', '')
    application_id_filter = request.GET.get('application_id', '')
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    applications = VendorApplication.objects.select_related('user', 'reviewed_by').filter(
        status__in=['submitted', 'under_review', 'requires_changes']
    )

    if search:
        applications = applications.filter(
            Q(application_id__icontains=search)
            | Q(company_name__icontains=search)
            | Q(user__email__icontains=search)
        )

    if application_id_filter:
        applications = applications.filter(application_id__icontains=application_id_filter)

    if status_filter:
        applications = applications.filter(status=status_filter)

    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            applications = applications.filter(submitted_at__date__gte=date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            applications = applications.filter(submitted_at__date__lte=date_to_obj)
        except ValueError:
            pass

    applications = applications.order_by('-submitted_at', '-created_at')

    per_page = get_per_page_param(request, 20)
    paginator = Paginator(applications, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'applications': page_obj,
        'status_choices': VendorApplication.APPLICATION_STATUS,
        'current_filters': {
            'search': search,
            'application_id': application_id_filter,
            'status': status_filter,
            'date_from': date_from,
            'date_to': date_to,
        },
        'pending_count': applications.count(),
        'per_page': per_page,
        'per_page_options': PER_PAGE_OPTIONS,
        'query_string': get_pagination_query_string(request),
        'preserved_query_params': get_preserved_query_params(request),
    }
    
    return render(request, 'admin_panel/vendor_approval_queue.html', context)

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
            Q(business_partner__name__icontains=search)
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
            if business_partner:
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
                action_type=ActivityLogType.CREATE,
                description=f'Sent message to {business_partner.name if business_partner else recipient.email}: {subject}',
                content_object=message,
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
    
    # 1. Fetch Legacy Payments
    legacy_payments = VendorPayment.objects.select_related('vendor').prefetch_related('related_listings')
    if status_filter:
        legacy_payments = legacy_payments.filter(status=status_filter)
    if vendor_filter:
        legacy_payments = legacy_payments.filter(vendor_id=vendor_filter)
    if date_from:
        legacy_payments = legacy_payments.filter(created_at__date__gte=date_from)
    if date_to:
        legacy_payments = legacy_payments.filter(created_at__date__lte=date_to)
    if payment_method:
        legacy_payments = legacy_payments.filter(payment_method=payment_method)

    # 2. Fetch Unified Transactions (Payouts)
    # Note: unified transactions are effectively always "completed" in this ledger
    unified_payouts = Transaction.objects.filter(transaction_type='PAYOUT')
    if status_filter and status_filter != 'completed':
        unified_payouts = unified_payouts.none() # Only completed in unified
    if vendor_filter:
        unified_payouts = unified_payouts.filter(destination_wallet__owner_id=vendor_filter, destination_wallet__owner_content_type__model='businesspartner')
    if date_from:
        unified_payouts = unified_payouts.filter(created_at__date__gte=date_from)
    if date_to:
        unified_payouts = unified_payouts.filter(created_at__date__lte=date_to)
    # payment_method filter for unified might need metadata check if we store it there
    if payment_method:
        unified_payouts = unified_payouts.filter(metadata__payment_method=payment_method)

    # 3. Normalize and Merge
    merged_records = []
    for lp in legacy_payments:
        merged_records.append({
            'id': lp.id,
            'payment_reference': lp.payment_reference,
            'vendor': lp.vendor,
            'amount': lp.amount,
            'commission_amount': lp.commission_amount,
            'net_amount': lp.net_amount,
            'status': lp.status,
            'created_at': lp.created_at,
            'is_unified': False
        })
    
    for ut in unified_payouts:
        vendor = None
        if ut.destination_wallet and ut.destination_wallet.owner_content_type.model == 'businesspartner':
            vendor = ut.destination_wallet.owner
            
        merged_records.append({
            'id': ut.id,
            'payment_reference': f"TRX-{ut.id}",
            'vendor': vendor,
            'amount': ut.amount_base,
            'commission_amount': Decimal('0.00'), # Commissions are separate transactions in unified
            'net_amount': ut.amount_base,
            'status': 'completed',
            'created_at': ut.created_at,
            'is_unified': True
        })

    # Sort merged list
    merged_records.sort(key=lambda x: x['created_at'], reverse=True)

    # Statistics (Combined)
    legacy_stats = legacy_payments.aggregate(
        total_amount=Sum('amount'),
        total_commission=Sum('commission_amount')
    )
    
    # Unified commission needs to be fetched separately if we want total commission in the stats
    total_unified_commission = Transaction.objects.filter(transaction_type='COMMISSION')
    if vendor_filter:
        total_unified_commission = total_unified_commission.filter(metadata__vendor_id=vendor_filter)
    if date_from:
        total_unified_commission = total_unified_commission.filter(created_at__date__gte=date_from)
    if date_to:
        total_unified_commission = total_unified_commission.filter(created_at__date__lte=date_to)
    
    unified_commission_amount = total_unified_commission.aggregate(total=Sum('amount_base'))['total'] or Decimal('0.00')
    unified_payout_amount = unified_payouts.aggregate(total=Sum('amount_base'))['total'] or Decimal('0.00')

    payment_stats = {
        'total_payments': len(merged_records),
        'total_amount': (legacy_stats['total_amount'] or Decimal('0.00')) + unified_payout_amount,
        'total_commission': (legacy_stats['total_commission'] or Decimal('0.00')) + unified_commission_amount,
        'pending_payments': legacy_payments.filter(status='pending').count(),
        'completed_payments': legacy_payments.filter(status='completed').count() + unified_payouts.count(),
        'failed_payments': legacy_payments.filter(status='failed').count(),
    }
    
    # Pagination
    per_page = get_per_page_param(request, 20)
    paginator = Paginator(merged_records, per_page)
    payments_page = paginator.get_page(request.GET.get('page'))
    
    # Get vendors for filter dropdown
    vendors = (
        BusinessPartner.objects.filter(roles__role_type='vendor')
        .exclude(status='pending')
        .distinct()
        .order_by('name')
    )
    
    context = {
        'payments': payments_page,
        'page_obj': payments_page,
        'payment_stats': payment_stats,
        'vendors': vendors,
        'status_choices': PaymentStatus.choices,
        'payment_method_choices': PaymentMethod.choices,
        'status_filter': status_filter,
        'vendor_filter': vendor_filter,
        'date_from': date_from,
        'date_to': date_to,
        'payment_method_filter': payment_method,
        'per_page': per_page,
        'per_page_options': PER_PAGE_OPTIONS,
        'query_string': get_pagination_query_string(request),
        'preserved_query_params': get_preserved_query_params(request),
    }
    
    return render(request, 'admin_panel/payment_management.html', context)


@login_required
@staff_required
def commission_management_view(request):
    """View for managing commission rules and rates."""
    
    # Get all commission rules
    commission_rules = CommissionRule.objects.select_related('created_by').prefetch_related('specific_vendors')

    status_filter = request.GET.get('status', '')
    scope_filter = request.GET.get('scope', '')

    if status_filter == 'active':
        commission_rules = commission_rules.filter(is_active=True)
    elif status_filter == 'inactive':
        commission_rules = commission_rules.filter(is_active=False)

    if scope_filter == 'vendor_specific':
        commission_rules = commission_rules.filter(applies_to_all_vendors=False)
    elif scope_filter == 'all_vendors':
        commission_rules = commission_rules.filter(applies_to_all_vendors=True)
    
    # Calculate statistics
    commission_stats = {
        'total_rules': CommissionRule.objects.count(),
        'active_rules': CommissionRule.objects.filter(is_active=True).count(),
        'vendor_specific_rules': CommissionRule.objects.filter(applies_to_all_vendors=False).count(),
    }

    display_currency_code = _get_display_currency_code(request)
    base_currency_code = _get_base_currency_code()
    commission_rules = list(commission_rules)
    for rule in commission_rules:
        rule.edit_min_amount = _convert_base_to_display(rule.min_amount, display_currency_code, base_currency_code)
        rule.edit_max_amount = (
            _convert_base_to_display(rule.max_amount, display_currency_code, base_currency_code)
            if rule.max_amount is not None
            else None
        )
        rule.edit_commission_rate = (
            _convert_base_to_display(rule.commission_rate, display_currency_code, base_currency_code)
            if rule.commission_type == "fixed_amount"
            else rule.commission_rate
        )
    
    context = {
        'commission_rules': commission_rules,
        'commission_stats': commission_stats,
        'commission_type_choices': CommissionRule.commission_type.field.choices,
        'status_filter': status_filter,
        'scope_filter': scope_filter,
        'preserved_query_params': get_preserved_query_params(request),
    }
    
    return render(request, 'admin_panel/commission_management.html', context)


@login_required
@staff_required
def create_commission_rule(request):
    """View to handle creation of a new commission rule."""
    if request.method == 'POST':
        try:
            name = (request.POST.get('name') or '').strip()
            commission_type = (request.POST.get('commission_type') or '').strip() or 'percentage'
            commission_rate_raw = request.POST.get('commission_rate')
            if not name or not commission_type or (commission_rate_raw is None or str(commission_rate_raw).strip() == ''):
                raise ValueError("Rule name, type, and rate are required.")

            category = (request.POST.get('category') or '').strip() or None
            description = request.POST.get('description', '')

            display_currency_code = _get_display_currency_code(request)
            base_currency_code = _get_base_currency_code()

            if commission_type == "fixed_amount":
                commission_rate_display = _as_decimal(commission_rate_raw)
                commission_rate = _convert_display_to_base(commission_rate_display, display_currency_code, base_currency_code)
            else:
                commission_rate = _as_decimal(commission_rate_raw)

            fixed_amount = _as_decimal_with_default(request.POST.get('fixed_amount'), Decimal('0.00'))
            min_amount_display = _as_decimal_with_default(request.POST.get('min_amount'), Decimal('0.00'))
            min_amount = _convert_display_to_base(min_amount_display, display_currency_code, base_currency_code)

            max_amount_display = _as_decimal(request.POST.get('max_amount'))
            max_amount = (
                _convert_display_to_base(max_amount_display, display_currency_code, base_currency_code)
                if max_amount_display is not None
                else None
            )

            applies_to_all = request.POST.get('applies_to_all_vendors') == 'on'
            is_active = request.POST.get('is_active') == 'on'
            
            rule = CommissionRule.objects.create(
                name=name,
                category=category,
                description=description,
                commission_type=commission_type,
                commission_rate=commission_rate,
                fixed_amount=fixed_amount,
                min_amount=min_amount,
                max_amount=max_amount,
                applies_to_all_vendors=applies_to_all,
                is_active=is_active,
                created_by=request.user
            )
            
            messages.success(request, f"Commission rule '{name}' created successfully.")
        except Exception as e:
            messages.error(request, f"Error creating rule: {str(e)}")
            
    return redirect('admin_panel:commission_management')


@login_required
@staff_required
def toggle_commission_rule(request, rule_id):
    """Toggle the active status of a commission rule."""
    if request.method == 'POST':
        rule = get_object_or_404(CommissionRule, id=rule_id)
        rule.is_active = not rule.is_active
        rule.save()
        messages.success(request, f"Rule '{rule.name}' is now {'active' if rule.is_active else 'inactive'}.")
    return redirect('admin_panel:commission_management')


@login_required
@staff_required
def delete_commission_rule(request, rule_id):
    """Delete a commission rule."""
    if request.method == 'POST':
        rule = get_object_or_404(CommissionRule, id=rule_id)
        name = rule.name
        rule.delete()
        messages.success(request, f"Rule '{name}' has been deleted.")
    return redirect('admin_panel:commission_management')


@login_required
@staff_required
def update_commission_rule(request, rule_id):
    """Update an existing commission rule."""
    if request.method == 'POST':
        try:
            rule = get_object_or_404(CommissionRule, id=rule_id)
            name = (request.POST.get('name') or '').strip()
            commission_type = (request.POST.get('commission_type') or '').strip() or 'percentage'
            commission_rate_raw = request.POST.get('commission_rate')
            if not name or not commission_type or (commission_rate_raw is None or str(commission_rate_raw).strip() == ''):
                raise ValueError("Rule name, type, and rate are required.")

            rule.name = name
            rule.category = (request.POST.get('category') or '').strip() or None
            rule.description = request.POST.get('description', '')
            rule.commission_type = commission_type

            display_currency_code = _get_display_currency_code(request)
            base_currency_code = _get_base_currency_code()

            if commission_type == "fixed_amount":
                commission_rate_display = _as_decimal(commission_rate_raw)
                rule.commission_rate = _convert_display_to_base(commission_rate_display, display_currency_code, base_currency_code)
            else:
                rule.commission_rate = _as_decimal(commission_rate_raw)

            rule.fixed_amount = _as_decimal_with_default(request.POST.get('fixed_amount'), Decimal('0.00'))
            min_amount_display = _as_decimal_with_default(request.POST.get('min_amount'), Decimal('0.00'))
            rule.min_amount = _convert_display_to_base(min_amount_display, display_currency_code, base_currency_code)

            max_amount_display = _as_decimal(request.POST.get('max_amount'))
            rule.max_amount = (
                _convert_display_to_base(max_amount_display, display_currency_code, base_currency_code)
                if max_amount_display is not None
                else None
            )
            
            rule.applies_to_all_vendors = request.POST.get('applies_to_all_vendors') == 'on'
            rule.is_active = request.POST.get('is_active') == 'on'
            
            rule.save()
            messages.success(request, f"Commission rule '{rule.name}' updated successfully.")
        except Exception as e:
            messages.error(request, f"Error updating rule: {str(e)}")
            
    return redirect('admin_panel:commission_management')


@login_required
@staff_required
def vendor_balance_view(request, vendor_id):
    """View for vendor balance and payment history."""
    
    vendor = get_object_or_404(
        BusinessPartner.objects.filter(roles__role_type='vendor').distinct(),
        id=vendor_id,
    )
    
    # 1. Get Legacy Data
    legacy_balance, _ = VendorBalance.objects.get_or_create(vendor=vendor)
    legacy_payments = VendorPayment.objects.filter(vendor=vendor).order_by('-created_at')
    
    # 2. Get Unified Data
    vendor_ct = ContentType.objects.get_for_model(vendor)
    wallet, created = Wallet.objects.get_or_create(
        owner_content_type=vendor_ct,
        owner_id=vendor.id,
        defaults={'currency': 'USD'}
    )

    try:
        FinanceService.sync_legacy_vendor_payments(vendor=vendor, limit=None)
    except Exception:
        pass
    
    unified_transactions = Transaction.objects.filter(
        Q(source_wallet=wallet) | Q(destination_wallet=wallet)
    ).order_by('-created_at')
    
    # 3. Merge History
    history = []
    for lp in legacy_payments:
        history.append({
            'type': 'PAYOUT' if lp.status == 'completed' else 'PENDING_PAYOUT',
            'amount': lp.net_amount,
            'date': lp.created_at,
            'reference': lp.payment_reference,
            'status': lp.status,
            'is_unified': False
        })
    
    for ut in unified_transactions:
        history.append({
            'type': ut.transaction_type,
            'amount': ut.amount_base,
            'date': ut.created_at,
            'reference': f"TRX-{ut.id}",
            'status': 'completed',
            'is_unified': True
        })
    
    history.sort(key=lambda x: x['date'], reverse=True)
    
    # 4. Combined Statistics
    unified_earned = unified_transactions.filter(
        destination_wallet=wallet, 
        transaction_type__in=['PAYMENT', 'EARNING', 'COMMISSION_REBATE']
    ).aggregate(total=Sum('amount_base'))['total'] or Decimal('0.00')
    
    unified_paid = unified_transactions.filter(
        source_wallet=wallet, 
        transaction_type='PAYOUT'
    ).aggregate(total=Sum('amount_base'))['total'] or Decimal('0.00')
    
    balance_stats = {
        'legacy_earned': legacy_balance.total_earned,
        'legacy_paid': legacy_balance.total_paid,
        'unified_earned': unified_earned,
        'unified_paid': unified_paid,
        'total_earned': (legacy_balance.total_earned or Decimal('0.00')) + (unified_earned or Decimal('0.00')),
        'total_paid': (legacy_balance.total_paid or Decimal('0.00')) + (unified_paid or Decimal('0.00')),
        'available_balance': (legacy_balance.current_balance or Decimal('0.00')) + (wallet.available_balance or Decimal('0.00')),
        'pending_balance': (legacy_balance.pending_balance or Decimal('0.00')) + (wallet.escrow_balance or Decimal('0.00')),
        'escrow_balance': wallet.escrow_balance,
        'liability_balance': wallet.liability_balance,
    }
    
    context = {
        'vendor': vendor,
        'wallet': wallet,
        'legacy_balance': legacy_balance,
        'history': history[:50],  # Combined history
        'balance_stats': balance_stats,
    }
    
    return render(request, 'admin_panel/vendor_balance.html', context)


@login_required
@staff_required
@require_POST
def adjust_vendor_balance_view(request, vendor_id):
    """Manually adjust a vendor's balance using unified Transaction model."""
    vendor = get_object_or_404(BusinessPartner, id=vendor_id)
    vendor_ct = ContentType.objects.get_for_model(vendor)
    wallet, created = Wallet.objects.get_or_create(
        owner_content_type=vendor_ct,
        owner_id=vendor.id,
        defaults={'currency': 'USD'}
    )
    
    try:
        amount = Decimal(request.POST.get('amount', '0'))
        adjustment_type = request.POST.get('type', 'credit')  # credit or debit
        reason = request.POST.get('reason', 'Manual adjustment')
        
        with transaction.atomic():
            old_balance = wallet.available_balance
            
            if adjustment_type == 'debit':
                wallet.available_balance -= amount
                # Create Transaction record
                Transaction.objects.create(
                    source_wallet=wallet,
                    amount_base=amount,
                    amount_display=amount,
                    exchange_rate=1.0,
                    currency=wallet.currency,
                    transaction_type='ADJUSTMENT',
                    metadata={'reason': reason, 'admin_id': request.user.id, 'adjustment_type': 'debit'}
                )
            else:
                wallet.available_balance += amount
                # Create Transaction record
                Transaction.objects.create(
                    destination_wallet=wallet,
                    amount_base=amount,
                    amount_display=amount,
                    exchange_rate=1.0,
                    currency=wallet.currency,
                    transaction_type='ADJUSTMENT',
                    metadata={'reason': reason, 'admin_id': request.user.id, 'adjustment_type': 'credit'}
                )
            
            wallet.save()
        
        # Log the adjustment in activity log
        log_activity(
            user=request.user,
            action_type=ActivityLogType.UPDATE,
            description=f"Adjusted wallet for {vendor.business_name}: {amount} (Old: {old_balance}, New: {wallet.available_balance}). Reason: {reason}",
            content_object=vendor,
            request=request,
            data={
                'amount': str(amount),
                'old_balance': str(old_balance),
                'new_balance': str(wallet.available_balance),
                'reason': reason,
                'type': adjustment_type
            }
        )
        
        messages.success(request, f"Successfully adjusted wallet for {vendor.business_name} by {amount}")
        
    except (ValueError, TypeError, Exception) as e:
        messages.error(request, f"Error adjusting balance: {str(e)}")
    
    return redirect('admin_panel:vendor_balance', vendor_id=vendor_id)


@login_required
@staff_required
def process_payment_view(request, payment_id):
    """Process a vendor payment."""
    
    if request.method == 'POST':
        payment = get_object_or_404(VendorPayment, id=payment_id)
        
        # Check if vendor bank details are verified
        try:
            profile = payment.vendor.vendor_profile
            if not profile.bank_details_verified:
                messages.error(request, f"Cannot process payment: Bank details for {payment.vendor.business_name} are not verified.")
                return redirect('admin_panel:payment_management')
        except VendorProfile.DoesNotExist:
            messages.error(request, "Vendor profile not found.")
            return redirect('admin_panel:payment_management')

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
        # time.sleep(2)  # Removed for faster processing in dev

        with transaction.atomic():
            # Update to completed status
            payment.status = 'completed'
            payment.payment_date = timezone.now()
            payment.save()

            # Log payout in audit trail
            VendorAuditLogger.log_vendor_action(
                action_type='payout_processed',
                user=request.user,
                vendor=payment.vendor,
                details={
                    'payment_id': payment.id,
                    'amount': str(payment.net_amount),
                    'reference': payment.payment_reference,
                    'notes': 'Single payment processed'
                }
            )
            
            # Create payment history for completion
            PaymentHistory.objects.create(
                payment=payment,
                old_status='processing',
                new_status='completed',
                notes=f"Payment completed by {request.user.get_full_name()}",
                changed_by=request.user
            )
            
            # --- Sync with Unified Finance Model ---
            vendor = payment.vendor
            vendor_ct = ContentType.objects.get_for_model(vendor)
            wallet, created = Wallet.objects.get_or_create(
                owner_content_type=vendor_ct,
                owner_id=vendor.id,
                defaults={'currency': 'USD'}
            )
            
            # Log the PAYOUT in the unified Transaction ledger
            Transaction.objects.create(
                source_wallet=wallet,  # Money leaving vendor wallet (payout)
                amount_base=payment.net_amount,
                amount_display=payment.net_amount,
                exchange_rate=1.0,
                currency=wallet.currency,
                transaction_type='PAYOUT',
                reference_content_type=ContentType.objects.get_for_model(payment),
                reference_id=payment.id,
                metadata={
                    'payment_reference': payment.payment_reference,
                    'method': payment.payment_method,
                    'processed_by': request.user.id
                }
            )
            
            # Update wallet available balance (deduct the payout amount)
            wallet.available_balance -= payment.net_amount
            wallet.save()
            
            # Legacy sync (keep for compatibility until fully migrated)
            balance, created = VendorBalance.objects.get_or_create(
                vendor=vendor,
                defaults={'current_balance': 0, 'total_earned': 0, 'total_paid': 0}
            )
            balance.total_paid += payment.net_amount
            balance.last_payment_date = payment.payment_date
            balance.last_payment_amount = payment.net_amount
            balance.update_balance()
            # ---------------------------------------
        
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

@admin_required(min_role='staff')
@require_valid_admin_session
@audit_admin_action(ActivityLogType.VIEW, "Viewed vendor application {application_id}")
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


@admin_required(min_role='staff')
@require_valid_admin_session
@require_POST
@audit_admin_action(ActivityLogType.UPDATE, "Approved vendor application {application_id}")
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
                action_type=ActivityLogType.UPDATE,
                description=f'Approved vendor application for {application.company_name}',
                content_object=application,
            )
            
            # Send notification to applicant
            if application.user:
                Notification.objects.create(
                    user=application.user,
                    notification_type=NotificationType.ACCOUNT,
                    title='Vendor Application Approved',
                    message=f'Congratulations! Your vendor application for {application.company_name} has been approved.',
                    priority=NotificationPriority.HIGH,
                    action_url=reverse('business_partners:vendor_registration_status'),
                    data={'application_id': application.application_id},
                )
        else:
            messages.error(request, 'Failed to approve vendor application.')
    
    except Exception as e:
        messages.error(request, f'Error approving application: {str(e)}')
    
    return redirect('admin_panel:vendor_management')


@admin_required(min_role='staff')
@require_valid_admin_session
@require_POST
@audit_admin_action(ActivityLogType.UPDATE, "Rejected vendor application {application_id}")
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
            action_type=ActivityLogType.UPDATE,
            description=f'Rejected vendor application for {application.company_name}',
            content_object=application,
        )
        
        # Send notification to applicant
        if application.user:
            Notification.objects.create(
                user=application.user,
                notification_type=NotificationType.ACCOUNT,
                title='Vendor Application Rejected',
                message=f'Your vendor application for {application.company_name} has been rejected. Reason: {rejection_reason}',
                priority=NotificationPriority.HIGH,
                action_url=reverse('business_partners:vendor_registration_status'),
                data={'application_id': application.application_id},
            )
    
    except Exception as e:
        messages.error(request, f'Error rejecting application: {str(e)}')
    
    return redirect('admin_panel:vendor_management')


@admin_required(min_role='staff')
@require_valid_admin_session
@require_POST
@audit_admin_action(ActivityLogType.UPDATE, "Requested changes for vendor application {application_id}")
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
            action_type=ActivityLogType.UPDATE,
            description=f'Requested changes for vendor application {application.company_name}',
            content_object=application,
        )
        
        # Send notification to applicant
        if application.user:
            Notification.objects.create(
                user=application.user,
                notification_type=NotificationType.ACCOUNT,
                title='Changes Required for Vendor Application',
                message=f'Your vendor application for {application.company_name} requires changes: {changes_required}',
                priority=NotificationPriority.MEDIUM,
                action_url=reverse('business_partners:vendor_registration_status'),
                data={'application_id': application.application_id},
            )
    
    except Exception as e:
        messages.error(request, f'Error requesting changes: {str(e)}')
    
    return redirect('admin_panel:vendor_management')


@admin_required(min_role='staff')
@require_valid_admin_session
@audit_admin_action(ActivityLogType.VIEW, "Viewed vendor performance for vendor {vendor_id}")
def vendor_performance_view(request, vendor_id):
    """View vendor performance metrics and ratings."""
    
    vendor = get_object_or_404(
        BusinessPartner.objects.filter(roles__role_type='vendor').distinct(),
        id=vendor_id,
    )
    vendor_profile = get_object_or_404(VendorProfile, business_partner=vendor)
    
    # Get vendor listings
    vendor_listings = VehicleListing.objects.filter(user=vendor.user).order_by('-created_at')
    
    # Calculate performance metrics
    total_listings = vendor_listings.count()
    published_listings = vendor_listings.filter(status='published').count()
    sold_listings = vendor_listings.filter(status='sold').count()

    vendor_inquiries = ListingInquiry.objects.filter(listing__user=vendor.user)
    total_inquiries = vendor_inquiries.count()
    replied_inquiries = vendor_inquiries.filter(
        Q(status=InquiryStatus.REPLIED) | Q(responses__isnull=False)
    ).distinct().count()
    response_rate = round((replied_inquiries / total_inquiries) * 100, 1) if total_inquiries else 0.0
    
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
        'total_inquiries': total_inquiries,
        'replied_inquiries': replied_inquiries,
        'response_rate': response_rate,
        'total_sales_value': total_sales_value,
        'avg_listing_days': round(avg_listing_days, 1),
        'recent_reviews': recent_reviews,
        'review_stats': review_stats,
        'monthly_performance': monthly_performance,
    }
    
    return render(request, 'admin_panel/vendor_performance.html', context)


@admin_required(min_role='staff')
@require_valid_admin_session
@audit_admin_action(ActivityLogType.VIEW, "Viewed vendor documents for vendor {vendor_id}")
def vendor_documents_view(request, vendor_id):
    """View and manage vendor documents."""
    
    vendor = get_object_or_404(BusinessPartner, id=vendor_id)
    
    # Get all vendor documents
    documents = VendorDocument.objects.filter(
        business_partner=vendor
    ).select_related('category').order_by('-uploaded_at')
    
    # Get pending verifications for this vendor's documents
    doc_ids = documents.values_list('id', flat=True)
    pending_verifications = DocumentVerificationQueue.objects.filter(
        document_id__in=doc_ids,
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


@admin_required(min_role='staff')
@require_valid_admin_session
@require_POST
@audit_admin_action(ActivityLogType.UPDATE, "Verified vendor document {document_id}")
def verify_vendor_document_view(request, document_id):
    """Verify or reject a vendor document."""
    
    document = get_object_or_404(VendorDocument, id=document_id)
    
    # Template sends 'action' with values 'verify' or 'reject'
    action = request.POST.get('action')
    verification_notes = request.POST.get('verification_notes', '')
    
    # Map action to status
    status_map = {'verify': 'verified', 'reject': 'rejected'}
    verification_status = status_map.get(action)
    
    if not verification_status:
        messages.error(request, 'Invalid action')
        return redirect('admin_panel:vendor_documents', vendor_id=document.business_partner.id)
    
    try:
        # Update document status
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
            action_type=ActivityLogType.UPDATE,
            description=f'{"Verified" if verification_status == "verified" else "Rejected"} document for {document.business_partner.name}'
        )
        
        messages.success(request, f'Document has been {verification_status}.')
    
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
    
    return redirect('admin_panel:vendor_documents', vendor_id=document.business_partner.id)


@admin_required(min_role='staff')
@require_valid_admin_session
@audit_admin_action(ActivityLogType.VIEW, "Viewed vendor communication for vendor {vendor_id}")
def vendor_communication_view(request, vendor_id):
    """View and manage communication with a specific vendor."""
    
    vendor = get_object_or_404(
        BusinessPartner.objects.filter(roles__role_type='vendor').distinct(),
        id=vendor_id,
    )
    
    # Get all messages with this vendor
    messages_qs = AdminMessage.objects.filter(
        Q(sender=request.user, recipient=vendor.user) |
        Q(sender=vendor.user, recipient=request.user)
    ).select_related('sender', 'recipient').order_by('-created_at')
    
    # Get vendor notifications
    notifications = VendorNotification.objects.filter(
        vendor=vendor
    ).select_related('message').order_by('-created_at')
    
    context = {
        'vendor': vendor,
        'conversation_messages': messages_qs[:20],  # Last 20 messages
        'notifications': notifications[:10],  # Last 10 notifications
    }
    
    return render(request, 'admin_panel/vendor_communication.html', context)


# ==================== USER MANAGEMENT VIEWS ====================

@login_required
@staff_required
def users_management_view(request):
    """User management view with filtering and search."""
    from users.models import UserRole
    from django.db.models import Count, Q, OuterRef, Subquery, IntegerField
    from vendor_employees.models import VendorEmployee
    from business_partners.models import BusinessPartner
    
    search = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    
    # Subquery for employee count if user is a vendor (business partner)
    # A user can have multiple business partners, but usually one as vendor
    vendor_bp_subquery = BusinessPartner.objects.filter(
        user=OuterRef('pk'),
        roles__role_type='vendor'
    ).values('pk')[:1]

    employee_count_subquery = BusinessPartner.objects.filter(
        user=OuterRef('pk'),
        roles__role_type='vendor'
    ).annotate(
        count=Count('employees')
    ).values('count')[:1]

    users = User.objects.all().annotate(
        employee_count=Subquery(employee_count_subquery, output_field=IntegerField())
    ).select_related('vendor_employee', 'vendor_employee__vendor', 'vendor_employee__role').order_by('-date_joined')
    
    if search:
        users = users.filter(
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(vendor_employee__vendor__name__icontains=search) |
            Q(business_partners__name__icontains=search)
        ).distinct()
    
    if role_filter:
        if role_filter == 'vendor':
            users = users.filter(business_partners__roles__role_type='vendor')
        elif role_filter == 'vendor_employee':
            users = users.filter(vendor_employee__isnull=False)
        else:
            users = users.filter(role=role_filter)
    
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    per_page = get_per_page_param(request, 25)
    paginator = Paginator(users, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    role_choices = list(UserRole.choices)
    role_choices.extend([
        ('vendor', 'Vendor Partner'),
        ('vendor_employee', 'Vendor Employee'),
    ])
    
    context = {
        'page_obj': page_obj,
        'users': page_obj,
        'search': search,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'role_choices': role_choices,
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'per_page': per_page,
        'per_page_options': PER_PAGE_OPTIONS,
        'query_string': get_pagination_query_string(request),
        'preserved_query_params': get_preserved_query_params(request),
    }
    
    return render(request, 'users/users.html', context)


@login_required
@staff_required
@require_POST
def add_user_view(request):
    """Add a new user."""
    from django.core.mail import send_mail
    from django.conf import settings
    from users.models import UserRole
    
    email = request.POST.get('email', '').strip()
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    role = request.POST.get('role', 'client')
    password = request.POST.get('password', '')
    confirm_password = request.POST.get('confirm_password', '')
    
    # Validation
    if not email or not first_name or not last_name:
        messages.error(request, 'All fields are required.')
        return redirect('admin_panel:users')
    
    if password != confirm_password:
        messages.error(request, 'Passwords do not match.')
        return redirect('admin_panel:users')
    
    if len(password) < 8:
        messages.error(request, 'Password must be at least 8 characters.')
        return redirect('admin_panel:users')
    
    if User.objects.filter(email=email).exists():
        messages.error(request, 'A user with this email already exists.')
        return redirect('admin_panel:users')

    if role not in set(UserRole.values):
        messages.error(request, 'Invalid role selected.')
        return redirect('admin_panel:users')
    
    try:
        # Create the user
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        
        # Set role
        if hasattr(user, 'role'):
            user.role = role
        
        # Set permissions based on role
        if role == 'admin':
            user.is_staff = True
            user.is_superuser = True
        elif role == 'staff':
            user.is_staff = True
        
        user.save()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type=ActivityLogType.CREATE,
            description=f'Created new user: {user.email} with role {role}'
        )
        
        # Send welcome email
        try:
            send_mail(
                subject='Welcome to CarSyncro',
                message=f'''Hi {first_name},

Your account has been created on CarSyncro.

Email: {email}
Role: {role.title()}

You can login at: {settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'the website'}

Please change your password after your first login.

Best regards,
CarSyncro Team''',
                from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else None,
                recipient_list=[email],
                fail_silently=True,
            )
        except Exception as email_error:
            # Email sending failed but user was created
            pass
        
        messages.success(request, f'User {email} created successfully.')
    
    except Exception as e:
        messages.error(request, f'Error creating user: {str(e)}')
    
    return redirect('admin_panel:users')


@login_required
@staff_required
def user_detail_view(request, user_id):
    """View user details."""
    from users.models import UserRole

    user = get_object_or_404(User, id=user_id)
    context = {
        'user_obj': user,
        'role_choices': UserRole.choices,
    }
    return render(request, 'users/user_detail.html', context)


@login_required
@staff_required
@require_POST
def update_user_view(request, user_id):
    """Update user details."""
    user = get_object_or_404(User, id=user_id)
    
    role = request.POST.get('role')
    if role:
        user.role = role
        user.is_staff = role in ['staff', 'admin']
        user.is_superuser = role == 'admin'
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
    from collections import defaultdict
    from django.db.models import Case, When, IntegerField
    from core.rbac_models import Role, Permission
    from core.rbac_permissions import create_system_permissions, create_system_roles, assign_role_permissions
    from users.models import UserRole

    if not Permission.objects.exists() or not Role.objects.exists():
        create_system_permissions()
        create_system_roles()
        assign_role_permissions()

    allowed_role_names = [label for _, label in UserRole.choices]
    role_type_by_name = {
        UserRole.ADMIN.label: 'admin',
        UserRole.STAFF.label: 'staff',
        UserRole.SELLER.label: 'custom',
        UserRole.CLIENT.label: 'custom',
        UserRole.USER.label: 'custom',
    }
    for role_name in allowed_role_names:
        Role.objects.get_or_create(
            name=role_name,
            defaults={
                'role_type': role_type_by_name.get(role_name, 'custom'),
                'is_system': False,
                'is_active': True,
                'created_by': request.user,
            },
        )

    ordering = Case(
        *[When(name=name, then=pos) for pos, name in enumerate(allowed_role_names)],
        output_field=IntegerField(),
    )
    roles = (
        Role.objects.prefetch_related('permissions')
        .filter(is_active=True, name__in=allowed_role_names)
        .order_by(ordering)
    )

    module_label_map = dict(Permission._meta.get_field('module').choices)
    module_order = [
        'admin',
        'users',
        'business_partners',
        'parts',
        'inventory',
        'orders',
        'analytics',
        'system',
    ]
    action_to_index = {'view': 0, 'create': 1, 'update': 2, 'delete': 3}

    permissions = (
        Permission.objects.filter(action__in=list(action_to_index.keys()))
        .order_by('module', 'codename', 'action')
    )

    pages_by_module = defaultdict(lambda: defaultdict(lambda: [None, None, None, None]))

    def extract_resource_key(perm_codename):
        right = perm_codename.split('.', 1)[1] if '.' in perm_codename else perm_codename
        for prefix in ('view_', 'create_', 'update_', 'delete_'):
            if right.startswith(prefix):
                return right[len(prefix):]
        return right

    for perm in permissions:
        idx = action_to_index.get(perm.action)
        if idx is None:
            continue
        resource_key = extract_resource_key(perm.codename)
        pages_by_module[perm.module][resource_key][idx] = perm

    permission_modules = []
    for module_key in module_order:
        resources = pages_by_module.get(module_key)
        if not resources:
            continue
        pages = []
        for resource_key, perms in resources.items():
            pages.append({
                'key': f'{module_key}.{resource_key}',
                'label': resource_key.replace('_', ' ').title(),
                'perms': perms,
            })
        pages.sort(key=lambda p: p['label'])
        permission_modules.append({
            'key': module_key,
            'label': module_label_map.get(module_key, module_key.replace('_', ' ').title()),
            'pages': pages,
        })

    selected_role = roles.first()
    current_permissions = set()
    if selected_role:
        current_permissions = set(selected_role.permissions.values_list('id', flat=True))

    context = {
        'groups': roles,
        'permission_modules': permission_modules,
        'current_permissions': current_permissions,
        'selected_group_id': selected_role.id if selected_role else None,
        'allow_custom_roles': False,
    }

    return render(request, 'roles/permissions.html', context)


@login_required
@staff_required
@require_POST
def add_role_view(request):
    """Add a new RBAC role."""
    from core.rbac_models import Role

    name = request.POST.get('name', '').strip()
    
    if not name:
        return JsonResponse({'success': False, 'message': 'Role name is required.'})
    
    if Role.objects.filter(name__iexact=name).exists():
        return JsonResponse({'success': False, 'message': 'A role with this name already exists.'})
    
    try:
        role = Role.objects.create(name=name, role_type='custom', created_by=request.user)
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type=ActivityLogType.CREATE,
            description=f'Created new role: {name}'
        )
        
        return JsonResponse({'success': True, 'message': f'Role "{name}" created successfully.', 'role_id': role.id})
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@staff_required
@require_POST
def update_role_view(request, role_id):
    """Update an RBAC role name."""
    from core.rbac_models import Role

    name = request.POST.get('name', '').strip()
    
    if not name:
        return JsonResponse({'success': False, 'message': 'Role name is required.'})
    
    try:
        role = get_object_or_404(Role, id=role_id)
        if role.is_system:
            return JsonResponse({'success': False, 'message': 'System roles cannot be renamed.'})
        old_name = role.name
        
        # Check if another role with this name exists
        if Role.objects.filter(name__iexact=name).exclude(id=role_id).exists():
            return JsonResponse({'success': False, 'message': 'A role with this name already exists.'})
        
        role.name = name
        role.save()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type=ActivityLogType.UPDATE,
            description=f'Updated role name from "{old_name}" to "{name}"'
        )
        
        return JsonResponse({'success': True, 'message': f'Role updated to "{name}" successfully.'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@staff_required
@require_POST
def delete_role_view(request, role_id):
    """Delete an RBAC role."""
    from core.rbac_models import Role

    try:
        role = get_object_or_404(Role, id=role_id)
        if role.is_system:
            return JsonResponse({'success': False, 'message': 'System roles cannot be deleted.'})
        role_name = role.name
        
        role.delete()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type=ActivityLogType.DELETE,
            description=f'Deleted role: {role_name}'
        )
        
        return JsonResponse({'success': True, 'message': f'Role "{role_name}" deleted successfully.'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@staff_required
@require_POST
def update_role_permissions_view(request):
    """Update role permissions."""
    from core.rbac_models import Role
    
    try:
        data = json.loads(request.body)
        group_id = data.get('group_id')
        permission_ids = data.get('permissions', [])
        
        role = get_object_or_404(Role, id=group_id)
        if role.is_system:
            return JsonResponse({'success': False, 'message': 'System role permissions cannot be changed.'})
        role.permissions.set(permission_ids)

        ActivityLog.objects.create(
            user=request.user,
            action_type=ActivityLogType.UPDATE,
            description=f'Updated permissions for role: {role.name}'
        )
        
        return JsonResponse({'success': True, 'message': 'Permissions updated successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@staff_required
def get_role_permissions_view(request, role_id):
    from core.rbac_models import Role

    role = get_object_or_404(Role, id=role_id)
    permission_ids = list(role.permissions.values_list('id', flat=True))
    return JsonResponse({'success': True, 'group_id': role.id, 'permissions': permission_ids})


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
    
    per_page = get_per_page_param(request, 25)
    paginator = Paginator(parts, per_page)
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
        'per_page': per_page,
        'per_page_options': PER_PAGE_OPTIONS,
        'query_string': get_pagination_query_string(request),
        'preserved_query_params': get_preserved_query_params(request),
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
    return redirect('admin_panel:catalog_management')


@login_required
@staff_required
def part_field_config_view(request):
    """Manage dynamic field requirements and visibility for Part form."""
    from parts.models import PartFieldConfiguration
    from business_partners.forms import VendorPartForm
    
    # Initialize configurations if they don't exist
    existing_fields = set(PartFieldConfiguration.objects.values_list('field_name', flat=True))
    form = VendorPartForm()
    
    # Define groups based on form sections
    groups = {
        'Basic Info': ['parts_number', 'name', 'material_description', 'material_description_ar', 'manufacturer_part_number', 'manufacturer_oem_number'],
        'Classification': ['category', 'brand', 'material_type', 'material_group', 'division'],
        'Weights & Dimensions': ['base_unit_of_measure', 'gross_weight', 'net_weight', 'weight_of_unit', 'size_dimensions', 'weight', 'dimensions'],
        'Pricing & Valuation': ['price', 'quantity', 'standard_price', 'moving_average_price', 'valuation_class', 'price_control_indicator', 'price_unit_peinh'],
        'Logistics': ['plant', 'storage_location', 'warehouse_number', 'storage_bin', 'minimum_order_quantity', 'safety_stock', 'minimum_safety_stock', 'reorder_point', 'lot_size'],
        'Planning': ['mrp_type', 'mrp_controller', 'mrp_group', 'procurement_type', 'planned_delivery_time_days', 'goods_receipt_processing_time_days', 'total_replenishment_lead_time'],
        'Forecasting': ['forecast_model', 'forecast_periods', 'historical_periods', 'initialization_indicator', 'period_indicator'],
        'Sales': ['sales_organization', 'distribution_channel', 'material_pricing_group', 'account_assignment_group', 'item_category_group', 'general_item_category_group', 'tax_classification_material', 'transportation_group', 'loading_group', 'profit_center', 'purchasing_group', 'availability_check'],
        'Status': ['status', 'abc_indicator', 'valuation_category'],
        'Media': ['image', 'image_url'],
        'Other': ['description', 'old_material_number', 'expiration_xchpf', 'external_material_group', 'industry_sector', 'inventory_threshold', 'warranty_period']
    }
    
    # Core fields that should be locked as required
    locked_fields = ['parts_number', 'material_description', 'category', 'brand', 'price']
    
    new_configs = []
    for group_name, field_names in groups.items():
        for field_name in field_names:
            if field_name in form.fields and field_name not in existing_fields:
                field = form.fields[field_name]
                new_configs.append(PartFieldConfiguration(
                    field_name=field_name,
                    label=field.label or field_name.replace('_', ' ').title(),
                    is_required=field.required,
                    is_visible=True,
                    group_name=group_name,
                    is_locked=field_name in locked_fields
                ))
    
    if new_configs:
        PartFieldConfiguration.objects.bulk_create(new_configs)
        
    configurations = PartFieldConfiguration.objects.all().order_by('group_name', 'field_name')
    
    # Re-group for display
    grouped_configs = {}
    for config in configurations:
        if config.group_name not in grouped_configs:
            grouped_configs[config.group_name] = []
        grouped_configs[config.group_name].append(config)
        
    context = {
        'grouped_configs': grouped_configs,
    }
    return render(request, './catalog/field_config.html', context)


@login_required
@staff_required
@require_POST
def update_part_field_config(request):
    """Update dynamic field configurations."""
    from parts.models import PartFieldConfiguration
    
    field_ids = request.POST.getlist('field_ids')
    required_fields = request.POST.getlist('is_required')
    visible_fields = request.POST.getlist('is_visible')
    
    with transaction.atomic():
        # Reset all to optional/hidden first (only for the fields being sent)
        configs = PartFieldConfiguration.objects.filter(id__in=field_ids)
        for config in configs:
            # Skip locked fields for requirement changes, but they can be toggled if we wanted
            # For now, let's just apply what's sent
            config.is_required = str(config.id) in required_fields
            config.is_visible = str(config.id) in visible_fields
            
            # Ensure locked fields stay required
            if config.is_locked:
                config.is_required = True
                config.is_visible = True
                
            config.save()
            
    messages.success(request, 'Field configurations updated successfully.')
    return redirect('admin_panel:part_field_config')


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
    from business_partners.models import BusinessPartner
    
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    payment_filter = request.GET.get('payment', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    orders = (
        Order.objects.select_related('customer')
        .prefetch_related('items', 'items__part', 'items__part__vendor')
        .all()
    )
    
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
    
    per_page = get_per_page_param(request, 25)
    paginator = Paginator(orders, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    customer_ids = {o.customer_id for o in page_obj if o.customer_id}
    customer_bp_map = {
        bp.user_id: bp.bp_number
        for bp in BusinessPartner.objects.filter(user_id__in=customer_ids).only('user_id', 'bp_number')
    }

    for order in page_obj:
        order.customer_bp_number = customer_bp_map.get(order.customer_id) if order.customer_id else None

        vendors = []
        vendor_bp_numbers = []
        for item in getattr(order, 'items', []).all():
            part = getattr(item, 'part', None)
            vendor = getattr(part, 'vendor', None) if part else None
            if not vendor:
                continue
            if vendor.name and vendor.name not in vendors:
                vendors.append(vendor.name)
            if vendor.bp_number and vendor.bp_number not in vendor_bp_numbers:
                vendor_bp_numbers.append(vendor.bp_number)

        order.vendor_names_display = ", ".join(vendors) if vendors else None
        order.vendor_bp_numbers_display = ", ".join(vendor_bp_numbers) if vendor_bp_numbers else None
    
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
        'per_page': per_page,
        'per_page_options': PER_PAGE_OPTIONS,
        'query_string': get_pagination_query_string(request),
        'preserved_query_params': get_preserved_query_params(request),
    }
    
    return render(request, './catalog/orders.html', context)


@login_required
@staff_required
def order_detail_view(request, order_id):
    """View order details."""
    from parts.models import Order
    from business_partners.models import BusinessPartner

    order = (
        Order.objects.select_related('customer')
        .prefetch_related('items', 'items__part', 'items__part__vendor')
        .get(id=order_id)
    )

    customer_bp_number = None
    if order.customer_id:
        customer_bp_number = (
            BusinessPartner.objects.filter(user_id=order.customer_id)
            .values_list('bp_number', flat=True)
            .first()
        )

    vendors = []
    vendor_bp_numbers = []
    for item in order.items.all():
        part = getattr(item, 'part', None)
        vendor = getattr(part, 'vendor', None) if part else None
        if vendor:
            if vendor.name and vendor.name not in vendors:
                vendors.append(vendor.name)
            if vendor.bp_number and vendor.bp_number not in vendor_bp_numbers:
                vendor_bp_numbers.append(vendor.bp_number)
        item.vendor = vendor

    context = {
        'order': order,
        'customer_bp_number': customer_bp_number,
        'vendor_names_display': ", ".join(vendors) if vendors else None,
        'vendor_bp_numbers_display': ", ".join(vendor_bp_numbers) if vendor_bp_numbers else None,
    }
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


def _normalize_catalog_part(value: str) -> str:
    return "".join(ch for ch in (value or "").strip().upper() if ch.isalnum())


def _build_catalog_part_number(category, make: str, model: str | None, year: int | None) -> str:
    import uuid

    cat = _normalize_catalog_part(getattr(category, "name", ""))[:10] if category else "CAT"
    mk = _normalize_catalog_part(make)[:10] or "MAKE"
    mdl = _normalize_catalog_part(model or "")[:10] or "MODEL"
    yr = str(year) if year else "NA"
    suffix = uuid.uuid4().hex[:6].upper()
    return f"{cat}-{yr}-{mk}-{mdl}-{suffix}"[:100]


def _build_catalog_description(category, make: str, model: str | None, year: int | None, trim: str | None, engine: str | None) -> str:
    cat = getattr(category, "name", None) or "Catalog item"
    vehicle_parts = [make, (model or "").strip()]
    vehicle = " ".join([p for p in vehicle_parts if p]).strip()
    if year:
        vehicle = f"{vehicle} ({year})" if vehicle else f"({year})"
    base = f"{cat} for {vehicle or make}"
    extra = []
    if trim:
        extra.append(f"Trim: {trim}")
    if engine:
        extra.append(f"Engine: {engine}")
    if extra:
        return f"{base}\n" + "\n".join(extra)
    return base


@login_required
@staff_required
def catalog_list_view(request):
    from business_partners.catalog_models import CatalogItem

    catalog_items = (
        CatalogItem.objects.select_related("category", "vendor")
        .prefetch_related("images")
        .order_by("-created_at")
    )

    paginator = Paginator(catalog_items, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "catalog_items": page_obj,
        "page_obj": page_obj,
        "total_items": catalog_items.count(),
    }
    return render(request, "catalog/catalog_list.html", context)


@login_required
@staff_required
def catalog_detail_view(request, pk):
    from business_partners.catalog_models import CatalogItem

    catalog_item = get_object_or_404(
        CatalogItem.objects.select_related("category", "vendor").prefetch_related("images"),
        pk=pk,
    )
    return render(request, "catalog/catalog_detail.html", {"catalog_item": catalog_item})


@login_required
@staff_required
def catalog_add_view(request):
    from business_partners.catalog_models import CatalogItem
    from parts.models import Category
    from business_partners.models import BusinessPartner
    from parts.models import Brand

    if request.method == "POST":
        category_value = (request.POST.get("category") or "").strip()
        make = request.POST.get("make", "").strip()
        model = request.POST.get("model", "").strip() or None
        year = request.POST.get("year", "").strip()
        trim = request.POST.get("trim", "").strip() or None
        engine = request.POST.get("engine", "").strip() or None

        errors = []

        vendor = (
            BusinessPartner.objects.filter(roles__role_type="vendor")
            .distinct()
            .order_by("id")
            .first()
        )
        if not vendor:
            errors.append("At least one vendor must exist to add catalog items.")

        category = None
        if not category_value:
            errors.append("Category is required.")
        else:
            try:
                category_id = int(category_value)
                category = Category.objects.get(pk=category_id)
            except (TypeError, ValueError):
                category, _ = Category.objects.get_or_create(name=category_value)
            except Category.DoesNotExist:
                category, _ = Category.objects.get_or_create(name=category_value)

        if make:
            existing_make = Brand.objects.filter(name__iexact=make, is_active=True).first()
            if not existing_make:
                errors.append("Please select a valid Make from the master list.")
            else:
                make = existing_make.name
        else:
            make = "-"

        year_value = None
        if year:
            try:
                year_int = int(year)
                if year_int < 1900 or year_int > 2100:
                    errors.append("Please enter a valid year.")
                else:
                    year_value = year_int
            except ValueError:
                errors.append("Year must be a number.")

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            catalog_item = CatalogItem.objects.create(
                vendor=vendor,
                category=category,
                make=make,
                model=model,
                year=year_value,
                trim=trim,
                engine=engine,
                part_number=_build_catalog_part_number(category, make, model, year_value),
                description=_build_catalog_description(category, make, model, year_value, trim, engine),
            )
            messages.success(request, f'Catalog item "{catalog_item.part_number}" has been added successfully.')
            return redirect("admin_panel:catalog_management")

    current_year = timezone.now().year
    context = {
        "current_year": current_year,
        "year_range": range(current_year, 1979, -1),
        "categories": Category.objects.all().order_by("name"),
        "makes": Brand.objects.filter(is_active=True).order_by("name"),
    }
    return render(request, "catalog/catalog_add.html", context)


@login_required
@staff_required
def catalog_edit_view(request, pk):
    from business_partners.catalog_models import CatalogItem
    from parts.models import Category
    from parts.models import Brand

    catalog_item = get_object_or_404(
        CatalogItem.objects.select_related("category", "vendor").prefetch_related("images"),
        pk=pk,
    )

    if request.method == "POST":
        category_value = (request.POST.get("category") or "").strip()
        make = request.POST.get("make", "").strip()
        model = request.POST.get("model", "").strip() or None
        year = request.POST.get("year", "").strip()
        trim = request.POST.get("trim", "").strip() or None
        engine = request.POST.get("engine", "").strip() or None

        errors = []

        category = None
        if not category_value:
            errors.append("Category is required.")
        else:
            try:
                category_id = int(category_value)
                category = Category.objects.get(pk=category_id)
            except (TypeError, ValueError):
                category, _ = Category.objects.get_or_create(name=category_value)
            except Category.DoesNotExist:
                errors.append("Please select a valid category.")

        if not make:
            errors.append("Make is required.")
        else:
            existing_make = Brand.objects.filter(name__iexact=make, is_active=True).first()
            if not existing_make:
                errors.append("Please select a valid Make from the master list.")
            else:
                make = existing_make.name

        year_value = None
        if year:
            try:
                year_int = int(year)
                if year_int < 1900 or year_int > 2100:
                    errors.append("Please enter a valid year.")
                else:
                    year_value = year_int
            except ValueError:
                errors.append("Year must be a number.")

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            catalog_item.category = category
            catalog_item.make = make
            catalog_item.model = model
            catalog_item.year = year_value
            catalog_item.trim = trim
            catalog_item.engine = engine
            catalog_item.part_number = _build_catalog_part_number(category, make, model, year_value)
            catalog_item.description = _build_catalog_description(category, make, model, year_value, trim, engine)
            catalog_item.save()

            messages.success(request, "Catalog item has been updated successfully.")
            return redirect("admin_panel:catalog_detail", pk=catalog_item.pk)

    current_year = timezone.now().year
    context = {
        "catalog_item": catalog_item,
        "current_year": current_year,
        "year_range": range(current_year, 1979, -1),
        "categories": Category.objects.all().order_by("name"),
        "makes": Brand.objects.filter(is_active=True).order_by("name"),
    }
    return render(request, "catalog/catalog_edit.html", context)


@login_required
@staff_required
@require_http_methods(["POST"])
def catalog_delete_view(request, pk):
    from business_partners.catalog_models import CatalogItem

    catalog_item = get_object_or_404(CatalogItem, pk=pk)
    part_number = catalog_item.part_number
    catalog_item.delete()
    messages.success(request, f'Catalog item "{part_number}" has been deleted.')
    return redirect("admin_panel:catalog_management")


@login_required
@staff_required
def catalog_management_view(request):
    from business_partners.catalog_models import CatalogItem
    from parts.models import Category
    from parts.models import Brand

    catalog_queryset = CatalogItem.objects.select_related("category", "vendor").prefetch_related("images")

    search_query = request.GET.get("search", "")
    if search_query:
        catalog_queryset = catalog_queryset.filter(
            Q(part_number__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(category__name__icontains=search_query)
            | Q(make__icontains=search_query)
            | Q(model__icontains=search_query)
            | Q(trim__icontains=search_query)
            | Q(engine__icontains=search_query)
            | Q(vendor__name__icontains=search_query)
        )

    category_filter = request.GET.get("category", "").strip()
    if category_filter:
        try:
            catalog_queryset = catalog_queryset.filter(category_id=int(category_filter))
        except ValueError:
            pass

    make_filter = request.GET.get("make", "").strip()
    if make_filter:
        catalog_queryset = catalog_queryset.filter(make__iexact=make_filter)

    model_filter = request.GET.get("model", "").strip()
    if model_filter:
        catalog_queryset = catalog_queryset.filter(model__iexact=model_filter)

    year_filter = request.GET.get("year", "").strip()
    if year_filter:
        try:
            catalog_queryset = catalog_queryset.filter(year=int(year_filter))
        except ValueError:
            pass

    catalog_queryset = catalog_queryset.order_by("-created_at")

    paginator = Paginator(catalog_queryset, 25)
    page_number = request.GET.get("page")
    catalog_items = paginator.get_page(page_number)

    base_queryset = CatalogItem.objects.select_related("category")
    master_makes = list(Brand.objects.filter(is_active=True).values_list("name", flat=True).order_by("name"))
    catalog_makes = list(
        base_queryset.exclude(make__isnull=True).exclude(make__exact="").values_list("make", flat=True).distinct()
    )
    makes = sorted(set(master_makes) | set(catalog_makes), key=lambda s: s.lower())
    models = (
        base_queryset.filter(make__iexact=make_filter)
        .exclude(model__isnull=True)
        .values_list("model", flat=True)
        .distinct()
        .order_by("model")
        if make_filter
        else base_queryset.exclude(model__isnull=True).values_list("model", flat=True).distinct().order_by("model")
    )
    years = (
        base_queryset.filter(make__iexact=make_filter, model__iexact=model_filter)
        .exclude(year__isnull=True)
        .values_list("year", flat=True)
        .distinct()
        .order_by("-year")
        if make_filter and model_filter
        else base_queryset.exclude(year__isnull=True).values_list("year", flat=True).distinct().order_by("-year")
    )

    total_items = catalog_queryset.count()
    categories = Category.objects.filter(vendor_catalog_items__isnull=False).distinct().order_by("name")
    category_count = base_queryset.exclude(category__isnull=True).values("category").distinct().count()
    make_count = base_queryset.exclude(make__isnull=True).values("make").distinct().count()
    model_count = base_queryset.exclude(model__isnull=True).values("model").distinct().count()
    year_count = base_queryset.exclude(year__isnull=True).values("year").distinct().count()

    context = {
        "catalog_items": catalog_items,
        "parts": catalog_items,
        "total_items": total_items,
        "total_parts": total_items,
        "total_skus": total_items,
        "categories": categories,
        "category_count": category_count,
        "make_count": make_count,
        "model_count": model_count,
        "year_count": year_count,
        "makes": makes,
        "models": models,
        "years": years,
        "search_query": search_query,
        "category_filter": category_filter,
        "make_filter": make_filter,
        "model_filter": model_filter,
        "year_filter": year_filter,
    }
    return render(request, "catalog/catalog_management.html", context)


@login_required
@staff_required
def catalog_inventory_view(request):
    from parts.models import Part
    from business_partners.models import BusinessPartner
    from django.db.models import Count, Sum
    from django.db.models import F
    from django.db.models.functions import Coalesce

    inventory_queryset = Part.objects.filter(vendor__isnull=False).select_related(
        "vendor", "category", "brand", "inventory"
    )

    vendor_filter = (request.GET.get("vendor") or "").strip()
    if vendor_filter:
        try:
            inventory_queryset = inventory_queryset.filter(vendor_id=int(vendor_filter))
        except ValueError:
            inventory_queryset = inventory_queryset.none()

    search_query = (request.GET.get("search") or "").strip()
    if search_query:
        inventory_queryset = inventory_queryset.filter(
            Q(parts_number__icontains=search_query)
            | Q(material_description__icontains=search_query)
            | Q(manufacturer_part_number__icontains=search_query)
            | Q(category__name__icontains=search_query)
            | Q(vendor__name__icontains=search_query)
        )

    vendor_queryset = (
        BusinessPartner.objects
        .filter(vendor_parts__isnull=False)
        .annotate(
            inventory_count=Count("vendor_parts", distinct=True),
            stock_units=Coalesce(
                Sum("vendor_parts__quantity"),
                0
            ),
        )
        .order_by("name")
    )

    total_vendors = vendor_queryset.count()
    total_inventory_items = Part.objects.filter(vendor__isnull=False).count()
    total_stock_units = (
                            Part.objects
                            .filter(vendor__isnull=False)
                            .aggregate(total=Sum("quantity"))
                        )["total"] or 0

    filtered_stock_units = inventory_queryset.aggregate(
        total=Sum(Coalesce(F("inventory__stock"), F("quantity")))
    )["total"] or 0

    inventory_queryset = inventory_queryset.order_by("-created_at")

    per_page = get_per_page_param(request, 25)
    paginator = Paginator(inventory_queryset, per_page)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "inventory_items": page_obj,
        "search_query": search_query,
        "page_obj": page_obj,
        "per_page": per_page,
        "per_page_options": PER_PAGE_OPTIONS,
        "query_string": get_pagination_query_string(request),
        "preserved_query_params": get_preserved_query_params(request),
        "total_inventory_items": inventory_queryset.count(),
        "filtered_stock_units": filtered_stock_units,
        "vendors": vendor_queryset,
        "vendor_filter": vendor_filter,
        "cards": {
            "total_vendors": total_vendors,
            "total_inventory_items": total_inventory_items,
            "total_stock_units": total_stock_units,
        },
    }
    return render(request, "catalog/inventory.html", context)


@login_required
@staff_required
def catalog_categories_view(request):
    from parts.models import Category

    categories = (
        Category.objects.annotate(
            parts_count=Count("vendor_catalog_items", distinct=True),
            subcategories_count=models.Value(0, output_field=models.IntegerField()),
        )
        .order_by("name")
    )
    return render(request, "catalog/catalog_categories.html", {"categories": categories})


@login_required
@staff_required
def catalog_makes_view(request):
    from parts.models import Brand

    makes = Brand.objects.all().order_by("name")
    return render(request, "catalog/catalog_makes.html", {"makes": makes})


@login_required
@staff_required
def catalog_make_add_view(request):
    from parts.models import Brand

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        description = (request.POST.get("description") or "").strip() or None
        website = (request.POST.get("website") or "").strip() or None
        is_active = request.POST.get("is_active") == "on"
        logo = request.FILES.get("logo")

        if not name:
            messages.error(request, "Make name is required.")
        else:
            if Brand.objects.filter(name__iexact=name).exists():
                messages.error(request, "This make already exists.")
            else:
                make = Brand(name=name, description=description, website=website, is_active=is_active)
                if logo:
                    make.logo = logo
                make.save()
                messages.success(request, "Make has been created successfully.")
                return redirect("admin_panel:catalog_makes")

    return render(request, "catalog/catalog_make_add.html")


@login_required
@staff_required
def catalog_make_edit_view(request, pk):
    from parts.models import Brand

    make_obj = get_object_or_404(Brand, pk=pk)

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        description = (request.POST.get("description") or "").strip() or None
        website = (request.POST.get("website") or "").strip() or None
        is_active = request.POST.get("is_active") == "on"
        logo = request.FILES.get("logo")

        if not name:
            messages.error(request, "Make name is required.")
        else:
            duplicate = Brand.objects.filter(name__iexact=name).exclude(pk=make_obj.pk).exists()
            if duplicate:
                messages.error(request, "This make already exists.")
            else:
                make_obj.name = name
                make_obj.description = description
                make_obj.website = website
                make_obj.is_active = is_active
                if logo:
                    make_obj.logo = logo
                make_obj.save()
                messages.success(request, "Make has been updated successfully.")
                return redirect("admin_panel:catalog_makes")

    return render(request, "catalog/catalog_make_edit.html", {"make": make_obj})


@login_required
@staff_required
@require_http_methods(["POST"])
def catalog_make_delete_view(request, pk):
    from parts.models import Brand

    make_obj = get_object_or_404(Brand, pk=pk)
    make_obj.is_active = False
    make_obj.save(update_fields=["is_active"])
    messages.success(request, "Make has been deactivated.")
    return redirect("admin_panel:catalog_makes")


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
    
    per_page = get_per_page_param(request, 25)
    paginator = Paginator(reviews, per_page)
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
        'per_page': per_page,
        'per_page_options': PER_PAGE_OPTIONS,
        'query_string': get_pagination_query_string(request),
        'preserved_query_params': get_preserved_query_params(request),
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
def bulk_upload_template_view(request):
    import csv
    import io
    from django.http import HttpResponse

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Category",
        "Year",
        "Make",
        "Model",
        "Trim",
        "Engine",
    ])
    writer.writerow([
        "Engine Parts",
        "2020",
        "Toyota",
        "Camry",
        "SE",
        "2.5L",
    ])

    response = HttpResponse(output.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="catalog_bulk_upload_template.csv"'
    return response


@login_required
@staff_required
@require_POST
def process_bulk_upload_view(request):
    from django.core.files.storage import default_storage
    from parts.models import BulkUploadLog
    from parts.tasks import process_catalog_bulk_upload_file, process_catalog_parts_import
    
    if 'file' not in request.FILES:
        messages.error(request, 'No file provided.')
        return redirect('admin_panel:bulk_upload')
    
    uploaded_file = request.FILES['file']

    processing_mode = 'sync'

    upload_log = BulkUploadLog.objects.create(
        user=request.user,
        file_name=uploaded_file.name,
        file_size=uploaded_file.size,
        status='processing',
        processing_mode='sync',
    )

    try:
        total_records, successful_records, failed_records, errors = process_catalog_bulk_upload_file(
            uploaded_file,
            uploaded_file.name,
            upload_log_id=upload_log.id,
        )

        upload_log.total_records = total_records
        upload_log.successful_records = successful_records
        upload_log.failed_records = failed_records
        upload_log.completed_at = timezone.now()
        upload_log.error_log = "\n".join(errors) if errors else ""

        if failed_records:
            upload_log.status = "failed"
            upload_log.success_message = ""
            if errors:
                preview = " | ".join(errors[:3])
                more = "" if len(errors) <= 3 else f" (+{len(errors) - 3} more)"
                messages.error(request, f"Bulk upload failed: {preview}{more}")
            else:
                messages.error(request, "Bulk upload failed. Please fix the errors and try again.")
        else:
            upload_log.status = "completed"
            upload_log.success_message = f"Successfully processed {successful_records} records."
            messages.success(request, upload_log.success_message)

        upload_log.save()
        return redirect('admin_panel:bulk_upload')

    except Exception as exc:
        upload_log.status = "failed"
        upload_log.completed_at = timezone.now()
        upload_log.error_log = str(exc)
        upload_log.save(update_fields=['status', 'completed_at', 'error_log'])
        messages.error(request, f"Bulk upload failed: {str(exc)}")
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
    
    per_page = get_per_page_param(request, 25)
    paginator = Paginator(orders, per_page)
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
        'per_page': per_page,
        'per_page_options': PER_PAGE_OPTIONS,
        'query_string': get_pagination_query_string(request),
        'preserved_query_params': get_preserved_query_params(request),
    }
    
    return render(request, './finance/invoices.html', context)


@login_required
@staff_required
def invoice_detail_view(request, order_id):
    """View invoice details (order-based)."""
    from parts.models import Order
    from business_partners.models import BusinessPartner

    order = (
        Order.objects.select_related('customer')
        .prefetch_related('items', 'items__part', 'items__part__vendor')
        .get(id=order_id)
    )

    customer_bp_number = None
    if order.customer_id:
        customer_bp_number = (
            BusinessPartner.objects.filter(user_id=order.customer_id)
            .values_list('bp_number', flat=True)
            .first()
        )

    vendors = []
    vendor_bp_numbers = []
    for item in order.items.all():
        part = getattr(item, 'part', None)
        vendor = getattr(part, 'vendor', None) if part else None
        if vendor:
            if vendor.name and vendor.name not in vendors:
                vendors.append(vendor.name)
            if vendor.bp_number and vendor.bp_number not in vendor_bp_numbers:
                vendor_bp_numbers.append(vendor.bp_number)
        item.vendor = vendor

    context = {
        'order': order,
        'invoice': order,
        'customer_bp_number': customer_bp_number,
        'vendor_names_display': ", ".join(vendors) if vendors else None,
        'vendor_bp_numbers_display': ", ".join(vendor_bp_numbers) if vendor_bp_numbers else None,
    }
    return render(request, './finance/invoice_detail.html', context)


# ==================== TAX RULES VIEWS ====================

@login_required
@staff_required
def taxes_view(request):
    """Tax rules configuration."""
    from .models import AdminSetting
    from parts.models import Country
    
    # Get tax settings from AdminSetting model
    tax_settings = AdminSetting.objects.filter(
        key__startswith='tax_'
    ).order_by('key')

    countries = Country.objects.filter(is_active=True).order_by('name')
    
    context = {
        'tax_settings': tax_settings,
        'countries': countries,
        'country_codes': [c.code for c in countries],
    }
    
    return render(request, './finance/taxes.html', context)


@login_required
@staff_required
@require_POST
def add_tax_rule_view(request):
    """Add a tax rule."""
    from .models import AdminSetting
    import re
    
    country_code = (request.POST.get('country_code') or '').strip().upper()
    raw_key = (request.POST.get('key') or '').strip()
    key = re.sub(r'[^a-z0-9_]+', '_', raw_key.lower()).strip('_')
    value = request.POST.get('value')
    description = request.POST.get('description', '')

    if country_code:
        setting_key = f'tax_{country_code}_{key}'
    else:
        setting_key = f'tax_{key}'
    
    AdminSetting.objects.update_or_create(
        key=setting_key,
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
    
    per_page = get_per_page_param(request, 25)
    paginator = Paginator(partners, per_page)
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
        'per_page': per_page,
        'per_page_options': PER_PAGE_OPTIONS,
        'query_string': get_pagination_query_string(request),
        'preserved_query_params': get_preserved_query_params(request),
    }
    
    return render(request, 'partners/business-partners.html', context)


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
    
    return render(request, 'partners/partner_detail.html', context)

