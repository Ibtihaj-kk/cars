"""
Admin Email Console Views

Provides admin interface for manual email sending and email management.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone

from core.email_service.orchestrator import send_email, send_email_async, schedule_email
from core.email_service.models import EmailQueue, EmailTemplate
from users.models import User
from business_partners.models import BusinessPartner, VendorProfile


def is_admin_user(user):
    """Check if user is admin or staff."""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


@login_required
@user_passes_test(is_admin_user)
def email_console(request):
    """Main email console dashboard."""
    # Get email statistics
    email_stats = {
        'total_emails': EmailQueue.objects.count(),
        'queued_emails': EmailQueue.objects.filter(status='queued').count(),
        'sent_emails': EmailQueue.objects.filter(status='sent').count(),
        'failed_emails': EmailQueue.objects.filter(status='failed').count(),
        'recent_emails': EmailQueue.objects.order_by('-created_at')[:10],
    }
    
    # Get user counts for targeting
    user_counts = {
        'total_users': User.objects.count(),
        'verified_users': User.objects.filter(is_verified=True).count(),
        'vendors': BusinessPartner.objects.filter(roles__role_type='vendor').distinct().count(),
    'customers': BusinessPartner.objects.filter(roles__role_type='customer').distinct().count(),
    }
    
    # Get available templates
    templates = EmailTemplate.objects.filter(is_active=True)
    
    context = {
        'email_stats': email_stats,
        'user_counts': user_counts,
        'templates': templates,
        'active_tab': 'email_console',
    }
    
    return render(request, 'admin_panel/email_console.html', context)


@login_required
@user_passes_test(is_admin_user)
def email_queue(request):
    """View and manage email queue."""
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '')
    
    queryset = EmailQueue.objects.all()
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    if search_query:
        queryset = queryset.filter(
            Q(to_email__icontains=search_query) |
            Q(subject__icontains=search_query) |
            Q(email_type__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(queryset.order_by('-created_at'), 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
        'status_choices': dict(EmailQueue.STATUS_CHOICES),
        'active_tab': 'email_queue',
    }
    
    return render(request, 'admin_panel/email_queue.html', context)


@login_required
@user_passes_test(is_admin_user)
def send_manual_email(request):
    """Send manual email from admin console."""
    if request.method == 'POST':
        try:
            # Get form data
            recipient_type = request.POST.get('recipient_type')
            recipient_emails = request.POST.get('recipient_emails', '').strip()
            template_name = request.POST.get('template_name')
            subject = request.POST.get('subject', '')
            message_content = request.POST.get('message_content', '')
            
            # Validate recipient emails
            if not recipient_emails:
                messages.error(request, 'Recipient emails are required')
                return redirect('admin_panel:admin_email_console')
            
            # Parse recipient emails
            email_list = [email.strip() for email in recipient_emails.split(',') if email.strip()]
            
            # Validate emails
            for email in email_list:
                if '@' not in email or '.' not in email.split('@')[1]:
                    messages.error(request, f'Invalid email format: {email}')
                    return redirect('admin_panel:admin_email_console')
            
            # Prepare context
            context = {
                'message_content': message_content,
                'sent_by_admin': True,
                'admin_user_id': request.user.id,
                'sent_at': timezone.now().isoformat(),
            }
            
            # Send emails
            results = []
            
            for email in email_list:
                try:
                    email_id = send_email(
                        email_type='manual_admin',
                        to_email=email,
                        template_name=template_name,
                        subject=subject,
                        context=context,
                        priority='high'
                    )
                    results.append({'email': email, 'success': True, 'message_id': email_id})
                except Exception as e:
                    results.append({'email': email, 'success': False, 'error': str(e)})
            
            # Show results
            success_count = sum(1 for r in results if r['success'])
            error_count = len(results) - success_count
            
            if success_count > 0:
                messages.success(request, f'Successfully sent {success_count} email(s)')
            if error_count > 0:
                messages.warning(request, f'Failed to send {error_count} email(s)')
            
            # Store detailed results in session for display
            request.session['email_send_results'] = results
            
            return redirect('admin_panel:admin_email_console')
            
        except Exception as e:
            messages.error(request, f'Error sending email: {str(e)}')
            return redirect('admin_panel:admin_email_console')
    
    return redirect('admin_panel:admin_email_console')


@login_required
@user_passes_test(is_admin_user)
def send_bulk_email(request):
    """Send bulk email to user groups."""
    if request.method == 'POST':
        try:
            target_group = request.POST.get('target_group')
            template_name = request.POST.get('template_name')
            subject = request.POST.get('subject', '')
            message_content = request.POST.get('message_content', '')
            
            # Get target users based on group
            users = []
            
            if target_group == 'all_users':
                users = User.objects.filter(is_active=True)
            elif target_group == 'verified_users':
                users = User.objects.filter(is_active=True, is_verified=True)
            elif target_group == 'unverified_users':
                users = User.objects.filter(is_active=True, is_verified=False)
            elif target_group == 'vendors':
                vendor_partners = BusinessPartner.objects.filter(
                    roles__name='Vendor', 
                    is_active=True
                )
                users = User.objects.filter(
                    business_partner__in=vendor_partners,
                    is_active=True
                )
            elif target_group == 'customers':
                customer_partners = BusinessPartner.objects.filter(
                    roles__name='Customer', 
                    is_active=True
                )
                users = User.objects.filter(
                    business_partner__in=customer_partners,
                    is_active=True
                )
            
            # Prepare context
            context = {
                'message_content': message_content,
                'is_bulk_email': True,
                'sent_by_admin': True,
                'admin_user_id': request.user.id, # Store ID instead of object
                'sent_at': timezone.now().isoformat(), # Use ISO format
            }
            
            # Send emails
            results = []
            
            for user in users:
                try:
                    email_id = send_email(
                        email_type='bulk_admin',
                        to_email=user.email,
                        template_name=template_name,
                        subject=subject,
                        context=context,
                        priority='normal'
                    )
                    results.append({'email': user.email, 'success': True, 'message_id': email_id})
                except Exception as e:
                    results.append({'email': user.email, 'success': False, 'error': str(e)})
            
            # Show results
            success_count = sum(1 for r in results if r['success'])
            error_count = len(results) - success_count
            
            messages.success(request, 
                f'Bulk email initiated. Success: {success_count}, Failed: {error_count}'
            )
            
            # Store results for detailed view
            request.session['bulk_email_results'] = {
                'target_group': target_group,
                'total_users': len(users),
                'results': results,
                'sent_at': timezone.now().isoformat(),
            }
            request.session.modified = True
            
            return redirect('admin_panel:admin_email_console')
            
        except Exception as e:
            messages.error(request, f'Error sending bulk email: {str(e)}')
            return redirect('admin_panel:admin_email_console')
    
    return redirect('admin_panel:admin_email_console')


@login_required
@user_passes_test(is_admin_user)
def retry_failed_email(request, email_id):
    """Retry a failed email."""
    try:
        email = EmailQueue.objects.get(message_id=email_id, status='failed')
        
        if email.can_retry():
            orchestrator = EmailOrchestrator()
            new_email_id = orchestrator.retry_email(email_id)
            
            messages.success(request, f'Email queued for retry: {new_email_id}')
        else:
            messages.error(request, 'Email cannot be retried (max retries reached)')
            
    except EmailQueue.DoesNotExist:
        messages.error(request, 'Email not found or not in failed state')
    except Exception as e:
        messages.error(request, f'Error retrying email: {str(e)}')
    
    return redirect('admin_panel:admin_email_queue')


@login_required
@user_passes_test(is_admin_user)
def cancel_email(request, email_id):
    """Cancel a queued email."""
    try:
        email = EmailQueue.objects.get(message_id=email_id, status='queued')
        email.status = 'cancelled'
        email.save()
        
        messages.success(request, 'Email cancelled successfully')
        
    except EmailQueue.DoesNotExist:
        messages.error(request, 'Email not found or not in queued state')
    except Exception as e:
        messages.error(request, f'Error cancelling email: {str(e)}')
    
    return redirect('admin_panel:admin_email_queue')


@login_required
@user_passes_test(is_admin_user)
def email_analytics(request):
    """View email analytics and statistics."""
    # Basic analytics
    total_emails = EmailQueue.objects.count()
    sent_emails = EmailQueue.objects.filter(status='sent').count()
    failed_emails = EmailQueue.objects.filter(status='failed').count()
    
    # Daily stats for last 30 days
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    daily_stats = EmailQueue.objects.filter(
        created_at__gte=thirty_days_ago
    ).extra(
        {'date': "date(created_at)"}
    ).values('date').annotate(
        total=Count('id'),
        sent=Count('id', filter=Q(status='sent')),
        failed=Count('id', filter=Q(status='failed'))
    ).order_by('date')
    
    # Email type distribution
    type_stats = EmailQueue.objects.values('email_type').annotate(
        count=Count('id'),
        sent=Count('id', filter=Q(status='sent')),
        failed=Count('id', filter=Q(status='failed'))
    ).order_by('-count')
    
    context = {
        'total_emails': total_emails,
        'sent_emails': sent_emails,
        'failed_emails': failed_emails,
        'success_rate': (sent_emails / total_emails * 100) if total_emails > 0 else 0,
        'daily_stats': daily_stats,
        'type_stats': type_stats,
        'active_tab': 'email_analytics',
    }
    
    return render(request, 'admin_panel/email_analytics.html', context)


@login_required
@user_passes_test(is_admin_user)
@require_http_methods(["POST"])
def clear_email_queue(request):
    """Clear old emails from queue."""
    try:
        # Clear emails older than 30 days
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        deleted_count, _ = EmailQueue.objects.filter(
            created_at__lte=thirty_days_ago,
            status__in=['sent', 'failed', 'cancelled']
        ).delete()
        
        messages.success(request, f'Cleared {deleted_count} old emails from queue')
        
    except Exception as e:
        messages.error(request, f'Error clearing queue: {str(e)}')
    
    return redirect('admin_panel:admin_email_queue')