"""
Compliance check views and endpoints
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status

from .models import ComplianceCheck
from .compliance_checks import (
    run_compliance_checks, 
    run_specific_compliance_check,
    get_compliance_summary
)
from core.audit_logging import audit_logger


@method_decorator(login_required, name='dispatch')
class ComplianceDashboardView(TemplateView):
    """Compliance monitoring dashboard"""
    template_name = 'core/compliance_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
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
        
        context.update({
            'summary': summary,
            'recent_checks': recent_checks[:20],
            'failing_checks': failing_checks[:10],
            'overall_compliance_score': round(overall_score, 2),
            'dashboard_title': 'Compliance Monitoring Dashboard'
        })
        
        return context


@api_view(['POST'])
@permission_classes([IsAdminUser])
def run_compliance_check(request, check_type):
    """Run a specific compliance check"""
    try:
        # Run the compliance check
        result = run_specific_compliance_check(check_type)
        
        # Log the compliance check run
        audit_logger.log_action(
            action_type='COMPLIANCE_CHECK_RUN',
            user=request.user,
            object_type='ComplianceCheck',
            object_id=None,
            object_repr=f'Ran {check_type} compliance check',
            additional_data={
                'check_type': check_type,
                'status': result['status'],
                'score': result['score'],
                'issues': result['details'].get('issues', [])
            }
        )
        
        return Response({
            'success': True,
            'check_type': check_type,
            'result': result,
            'timestamp': timezone.now().isoformat()
        })
        
    except ValueError as e:
        return Response({
            'success': False,
            'error': str(e),
            'check_type': check_type
        }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"Error running compliance check {check_type}: {str(e)}")
        return Response({
            'success': False,
            'error': 'Internal server error',
            'check_type': check_type
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def compliance_summary(request):
    """Get compliance summary"""
    try:
        summary = get_compliance_summary()
        
        # Add additional metrics
        recent_checks = ComplianceCheck.objects.filter(
            last_run__gte=timezone.now() - timedelta(days=30)
        )
        
        # Get compliance trend (last 7 days)
        trend_data = ComplianceCheck.objects.filter(
            last_run__gte=timezone.now() - timedelta(days=7)
        ).extra(
            select={'day': "TO_CHAR(last_run, 'YYYY-MM-DD')"}
        ).values('day').annotate(
            avg_score=Avg('compliance_score'),
            passed_count=Count('id', filter=Q(status='PASSED')),
            failed_count=Count('id', filter=Q(status='FAILED'))
        ).order_by('day')
        
        return Response({
            'success': True,
            'summary': summary,
            'trend_data': list(trend_data),
            'last_updated': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting compliance summary: {str(e)}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST'])
@permission_classes([IsAdminUser])
def compliance_report(request):
    """Generate compliance report"""
    if request.method == 'POST':
        # Generate custom report
        try:
            report_config = request.data
            
            # Get date range
            date_from = report_config.get('date_from')
            date_to = report_config.get('date_to')
            check_types = report_config.get('check_types', [])
            
            # Build query
            query = Q()
            
            if date_from:
                query &= Q(last_run__gte=date_from)
            
            if date_to:
                query &= Q(last_run__lte=date_to)
            
            if check_types:
                query &= Q(check_type__in=check_types)
            
            # Get compliance data
            compliance_data = ComplianceCheck.objects.filter(query).order_by('-last_run')
            
            # Calculate statistics
            total_checks = compliance_data.count()
            passed_checks = compliance_data.filter(status='PASSED').count()
            failed_checks = compliance_data.filter(status='FAILED').count()
            avg_score = compliance_data.aggregate(avg_score=Avg('compliance_score'))['avg_score'] or 0
            
            # Group by check type
            by_type = compliance_data.values('check_type').annotate(
                total=Count('id'),
                passed=Count('id', filter=Q(status='PASSED')),
                failed=Count('id', filter=Q(status='FAILED')),
                avg_score=Avg('compliance_score')
            ).order_by('-total')
            
            report = {
                'report_config': report_config,
                'summary': {
                    'total_checks': total_checks,
                    'passed_checks': passed_checks,
                    'failed_checks': failed_checks,
                    'average_score': round(avg_score, 2),
                    'pass_rate': round((passed_checks / total_checks * 100) if total_checks > 0 else 0, 2)
                },
                'by_check_type': list(by_type),
                'failing_checks': list(compliance_data.filter(status='FAILED').values(
                    'name', 'check_type', 'compliance_score', 'last_run', 'description'
                )[:20]),
                'generated_at': timezone.now().isoformat()
            }
            
            # Log report generation
            audit_logger.log_action(
                action_type='COMPLIANCE_REPORT_GENERATED',
                user=request.user,
                object_type='ComplianceCheck',
                object_id=None,
                object_repr=f'Generated compliance report for {total_checks} checks',
                additional_data={
                    'report_config': report_config,
                    'total_checks': total_checks,
                    'passed_checks': passed_checks,
                    'failed_checks': failed_checks
                }
            )
            
            return Response({
                'success': True,
                'report': report
            })
            
        except Exception as e:
            logger.error(f"Error generating compliance report: {str(e)}")
            return Response({
                'success': False,
                'error': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    else:  # GET
        # Get default report (last 30 days)
        try:
            thirty_days_ago = timezone.now() - timedelta(days=30)
            
            compliance_data = ComplianceCheck.objects.filter(
                last_run__gte=thirty_days_ago
            ).order_by('-last_run')
            
            # Calculate statistics
            total_checks = compliance_data.count()
            passed_checks = compliance_data.filter(status='PASSED').count()
            failed_checks = compliance_data.filter(status='FAILED').count()
            avg_score = compliance_data.aggregate(avg_score=Avg('compliance_score'))['avg_score'] or 0
            
            # Group by check type
            by_type = compliance_data.values('check_type').annotate(
                total=Count('id'),
                passed=Count('id', filter=Q(status='PASSED')),
                failed=Count('id', filter=Q(status='FAILED')),
                avg_score=Avg('compliance_score')
            ).order_by('-total')
            
            report = {
                'report_config': {
                    'date_from': thirty_days_ago.isoformat(),
                    'date_to': timezone.now().isoformat(),
                    'check_types': [],
                    'description': 'Default 30-day compliance report'
                },
                'summary': {
                    'total_checks': total_checks,
                    'passed_checks': passed_checks,
                    'failed_checks': failed_checks,
                    'average_score': round(avg_score, 2),
                    'pass_rate': round((passed_checks / total_checks * 100) if total_checks > 0 else 0, 2)
                },
                'by_check_type': list(by_type),
                'failing_checks': list(compliance_data.filter(status='FAILED').values(
                    'name', 'check_type', 'compliance_score', 'last_run', 'description'
                )[:20]),
                'generated_at': timezone.now().isoformat()
            }
            
            return Response({
                'success': True,
                'report': report
            })
            
        except Exception as e:
            logger.error(f"Error getting default compliance report: {str(e)}")
            return Response({
                'success': False,
                'error': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@login_required
def compliance_dashboard_data(request):
    """AJAX endpoint for compliance dashboard data"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        # Get requested data type
        data_type = request.GET.get('type', 'summary')
        
        if data_type == 'summary':
            data = get_compliance_summary()
        elif data_type == 'failing_checks':
            data = list(ComplianceCheck.objects.filter(
                status='FAILED',
                last_run__gte=timezone.now() - timedelta(days=7)
            ).values('name', 'check_type', 'compliance_score', 'last_run', 'description')[:10])
        elif data_type == 'recent_activity':
            data = list(ComplianceCheck.objects.filter(
                last_run__gte=timezone.now() - timedelta(days=1)
            ).values('name', 'check_type', 'status', 'compliance_score', 'last_run').order_by('-last_run')[:20])
        else:
            data = {'error': 'Unknown data type'}
        
        return JsonResponse({
            'type': data_type,
            'data': data,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting compliance dashboard data: {str(e)}")
        return JsonResponse({
            'error': 'Internal server error'
        }, status=500)


# Import logger
import logging
logger = logging.getLogger(__name__)