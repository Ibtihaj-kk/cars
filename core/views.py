"""
Core application views
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from .models import SystemMetric, DashboardWidget, ComplianceCheck
from .audit_logging import audit_logger
from users.models import UserRole
from business_partners.permissions import get_vendor_profile
from parts.cache import get_cached_categories, get_cached_brands, get_cached_popular_parts, get_cached_featured_parts
from parts.models import Part, Category, Brand
from vehicles.models import VehicleMake, VehicleModelTaxonomy, VehicleVariant
from django.db.models import Q, Count, Sum, Avg, F, Prefetch
from business_partners.models import BusinessPartner


def home(request):
    """Home page view"""
    context = {
        'user': request.user if request.user.is_authenticated else None
    }
    return render(request, 'home/index.html', context)


@csrf_protect
@require_http_methods(["GET", "POST"])
def custom_login_view(request):
    """
    Custom login view with role-based redirect logic.
    Vendors/sellers are redirected to vendor dashboard, others to home with popup.
    """
    print(f"Login view called - Method: {request.method}")
    
    # If user is already authenticated, redirect them away from login page
    if request.user.is_authenticated:
        vendor_profile = get_vendor_profile(request.user)
        if vendor_profile and vendor_profile.is_approved:
            return redirect('business_partners:vendor_dashboard')
        elif vendor_profile:
            return redirect('business_partners:vendor_registration_status')
        else:
                # Regular authenticated user
                if request.user.is_staff or request.user.is_superuser:
                    return redirect('/admin/')
                else:
                    return redirect('users:user-dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('username', '').strip().lower()
        password = request.POST.get('password', '')
        
        print(f"Login attempt - Email: {email}, Password: {'*' * len(password) if password else 'empty'}")
        
        if not email or not password:
            messages.error(request, 'Email and password are required.')
            return render(request, 'home/login.html')
        
        # Authenticate user
        user = authenticate(request, username=email, password=password)
        print(f"Authentication result: {user is not None}")
        
        if user is not None:
            login(request, user)
            print(f"User logged in successfully: {user.email}")
            
            # Check if user is vendor or seller
            is_vendor = False
            
            # Check if user has vendor profile
            vendor_profile = get_vendor_profile(user)
            if vendor_profile and vendor_profile.is_approved:
                is_vendor = True
                print(f"User has approved vendor profile")
            
            # Debug logging
            print(f"User {user.email} logged in. Role: {getattr(user, 'role', 'unknown')}, Vendor profile: {vendor_profile is not None}, Is vendor: {is_vendor}")
            
            # Redirect based on role or next parameter
            next_url = request.GET.get('next') or request.POST.get('next')
            
            if next_url:
                messages.success(request, f'Welcome back, {user.get_full_name() or user.email}!')
                return redirect(next_url)
                
            if is_vendor:
                messages.success(request, f'Welcome back, {user.get_full_name() or user.email}!')
                return redirect('business_partners:vendor_dashboard')
            elif request.user.is_superuser or request.user.is_staff:
                 return redirect('/admin/')
            else:
                # Show popup message for non-vendors
                messages.info(request, 'Welcome! You are logged in as a regular user.')
                return redirect('users:user-dashboard')
        else:
            messages.error(request, 'Invalid email or password.')
            print(f"Failed login attempt for email: {email}")
    
    # GET request - show login form
    print("Showing login form")
    return render(request, 'home/login.html')


@login_required
def dashboard(request):
    """Main dashboard view"""
    context = {
        'user': request.user,
        'dashboard_title': 'CorporateDock Dashboard'
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def compliance_dashboard(request):
    """Compliance dashboard view"""
    from .compliance_checks import get_compliance_summary
    
    # Get compliance summary
    summary = get_compliance_summary()
    
    # Get recent compliance checks
    recent_checks = ComplianceCheck.objects.filter(
        last_run__gte=timezone.now() - timedelta(days=30)
    ).order_by('-last_run')
    
    # Get failing checks
    failing_checks = ComplianceCheck.objects.filter(
        status='FAILED',
        last_run__gte=timezone.now() - timedelta(days=7)
    ).order_by('-compliance_score')
    
    # Calculate overall compliance score
    overall_score = recent_checks.aggregate(
        avg_score=Avg('compliance_score')
    )['avg_score'] or 0
    
    context = {
        'dashboard_title': 'Compliance Monitoring Dashboard',
        'summary': summary,
        'recent_checks': recent_checks[:20],
        'failing_checks': failing_checks[:10],
        'overall_compliance_score': round(overall_score, 2)
    }
    
    return render(request, 'core/compliance_dashboard.html', context)


