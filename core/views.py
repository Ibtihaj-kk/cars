"""
Core application views
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg

from .models import SystemMetric, DashboardWidget, ComplianceCheck
from analytics.models import SalesMetric, VendorAnalytics
from .audit_logging import audit_logger


def home(request):
    """Home page view"""
    return render(request, 'core/home.html')


@login_required
def dashboard(request):
    """Main dashboard view"""
    context = {
        'user': request.user,
        'dashboard_title': 'YallaMotor Dashboard'
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