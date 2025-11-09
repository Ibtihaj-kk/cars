from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.db.models import Q, F
from datetime import datetime, timedelta
import json

from .permissions import vendor_required, get_vendor_profile
from .models import BusinessPartner, ReorderNotification
from parts.models import Part, Inventory


@method_decorator(csrf_exempt, name='dispatch')
class StockMonitoringAPI(View):
    """API endpoints for stock level monitoring"""
    
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to handle vendor authentication"""
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        # Check if user has vendor access
        vendor_profile = self.get_vendor_from_request(request)
        if not vendor_profile:
            return JsonResponse({'error': 'Vendor access required'}, status=403)
        
        # Store vendor profile for use in methods
        self.vendor_profile = vendor_profile
        self.business_partner = vendor_profile.business_partner
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_vendor_from_request(self, request):
        """Get vendor profile from request"""
        if request.user.is_authenticated:
            return get_vendor_profile(request.user)
        return None
    
    def get(self, request, endpoint=None):
        """Handle GET requests for stock monitoring data"""
        if endpoint == 'summary':
            return self.get_stock_summary(self.business_partner)
        elif endpoint == 'alerts':
            return self.get_stock_alerts(self.business_partner, request)
        elif endpoint == 'notifications':
            return self.get_reorder_notifications(self.business_partner, request)
        elif endpoint == 'health':
            return self.get_inventory_health(self.business_partner)
        else:
            return JsonResponse({'error': 'Invalid endpoint'}, status=400)
    
    def post(self, request, endpoint=None):
        """Handle POST requests for stock monitoring actions"""
        if endpoint == 'acknowledge-alert':
            return self.acknowledge_alert(self.business_partner, request)
        elif endpoint == 'mark-ordered':
            return self.mark_ordered(self.business_partner, request)
        else:
            return JsonResponse({'error': 'Invalid endpoint'}, status=400)
    
    def get_stock_summary(self, business_partner):
        """Get stock summary for vendor"""
        parts_queryset = Part.objects.filter(vendor=business_partner, is_active=True)
        
        # Stock status counts
        total_parts = parts_queryset.count()
        out_of_stock = parts_queryset.filter(quantity=0).count()
        low_stock = parts_queryset.filter(quantity__gt=0, quantity__lte=10).count()
        below_safety_stock = parts_queryset.filter(
            safety_stock__isnull=False,
            quantity__lt=F('safety_stock')
        ).count()
        
        # Reorder notifications
        pending_notifications = ReorderNotification.objects.filter(
            vendor=business_partner,
            status='pending'
        ).count()
        
        critical_notifications = ReorderNotification.objects.filter(
            vendor=business_partner,
            priority='critical',
            status__in=['pending', 'acknowledged']
        ).count()
        
        # Calculate inventory health
        healthy_stock_count = total_parts - out_of_stock - low_stock - below_safety_stock
        inventory_health = (healthy_stock_count / total_parts * 100) if total_parts > 0 else 100
        
        return JsonResponse({
            'success': True,
            'data': {
                'total_parts': total_parts,
                'out_of_stock': out_of_stock,
                'low_stock': low_stock,
                'below_safety_stock': below_safety_stock,
                'healthy_stock': healthy_stock_count,
                'pending_notifications': pending_notifications,
                'critical_notifications': critical_notifications,
                'inventory_health_percentage': round(inventory_health, 1),
                'health_status': self.get_health_status(inventory_health)
            }
        })
    
    def get_stock_alerts(self, business_partner, request):
        """Get detailed stock alerts"""
        # Get filter parameters
        severity = request.GET.get('severity', 'all')
        limit = int(request.GET.get('limit', 50))
        
        # Build query based on severity
        if severity == 'critical':
            alerts = self.get_critical_alerts(business_partner)
        elif severity == 'high':
            alerts = self.get_high_priority_alerts(business_partner)
        elif severity == 'medium':
            alerts = self.get_medium_priority_alerts(business_partner)
        else:
            alerts = self.get_all_alerts(business_partner)
        
        # Limit results
        alerts = alerts[:limit]
        
        # Serialize alerts
        alert_data = []
        for part, issue_type, severity_level in alerts:
            inventory = getattr(part, 'inventory', None)
            alert_data.append({
                'part_id': part.id,
                'part_number': part.parts_number,
                'part_name': part.name,
                'description': part.material_description,
                'current_stock': part.quantity,
                'reorder_level': inventory.reorder_level if inventory else 10,
                'safety_stock': part.safety_stock or 0,
                'issue_type': issue_type,
                'severity': severity_level,
                'category': part.category.name if part.category else 'Uncategorized',
                'brand': part.brand.name if part.brand else 'No Brand',
                'last_updated': part.updated_at.isoformat() if part.updated_at else None
            })
        
        return JsonResponse({
            'success': True,
            'data': {
                'alerts': alert_data,
                'total_count': len(alert_data),
                'severity_filter': severity
            }
        })
    
    def get_reorder_notifications(self, business_partner, request):
        """Get reorder notifications"""
        # Get filter parameters
        status = request.GET.get('status', 'all')
        priority = request.GET.get('priority', 'all')
        limit = int(request.GET.get('limit', 20))
        
        # Base queryset
        notifications = ReorderNotification.objects.filter(
            vendor=business_partner
        ).select_related('part', 'acknowledged_by')
        
        # Apply filters
        if status != 'all':
            notifications = notifications.filter(status=status)
        
        if priority != 'all':
            notifications = notifications.filter(priority=priority)
        
        # Order by urgency and date
        notifications = notifications.order_by('-urgency_score', '-created_at')[:limit]
        
        # Serialize notifications
        notification_data = []
        for notification in notifications:
            notification_data.append({
                'id': notification.id,
                'part_id': notification.part.id,
                'part_number': notification.part.parts_number,
                'part_name': notification.part.name,
                'current_stock': notification.current_stock,
                'safety_stock': notification.safety_stock,
                'reorder_level': notification.reorder_level,
                'suggested_quantity': notification.suggested_quantity,
                'priority': notification.priority,
                'status': notification.status,
                'message': notification.message,
                'created_at': notification.created_at.isoformat(),
                'acknowledged_by': notification.acknowledged_by.get_full_name() if notification.acknowledged_by else None,
                'is_overdue': notification.is_overdue,
                'urgency_score': notification.urgency_score
            })
        
        return JsonResponse({
            'success': True,
            'data': {
                'notifications': notification_data,
                'total_count': len(notification_data),
                'filters': {
                    'status': status,
                    'priority': priority
                }
            }
        })
    
    def get_inventory_health(self, business_partner):
        """Get detailed inventory health metrics"""
        parts_queryset = Part.objects.filter(vendor=business_partner, is_active=True)
        total_parts = parts_queryset.count()
        
        if total_parts == 0:
            return JsonResponse({
                'success': True,
                'data': {
                    'health_percentage': 100,
                    'status': 'Excellent',
                    'breakdown': {},
                    'recommendations': []
                }
            })
        
        # Calculate health breakdown
        out_of_stock = parts_queryset.filter(quantity=0).count()
        low_stock = parts_queryset.filter(quantity__gt=0, quantity__lte=10).count()
        below_safety = parts_queryset.filter(
            safety_stock__isnull=False,
            quantity__lt=F('safety_stock')
        ).count()
        healthy = total_parts - out_of_stock - low_stock - below_safety
        
        # Calculate health percentage
        health_percentage = (healthy / total_parts) * 100
        
        # Generate recommendations
        recommendations = []
        if out_of_stock > 0:
            recommendations.append(f"Restock {out_of_stock} out-of-stock items immediately")
        if low_stock > 0:
            recommendations.append(f"Consider reordering {low_stock} low-stock items")
        if below_safety > 0:
            recommendations.append(f"Review safety stock levels for {below_safety} items")
        if health_percentage < 80:
            recommendations.append("Overall inventory health needs attention")
        if health_percentage >= 90:
            recommendations.append("Excellent inventory management!")
        
        return JsonResponse({
            'success': True,
            'data': {
                'health_percentage': round(health_percentage, 1),
                'status': self.get_health_status(health_percentage),
                'breakdown': {
                    'healthy': healthy,
                    'low_stock': low_stock,
                    'out_of_stock': out_of_stock,
                    'below_safety': below_safety,
                    'total': total_parts
                },
                'recommendations': recommendations
            }
        })
    
    def acknowledge_alert(self, business_partner, request):
        """Acknowledge a reorder notification"""
        try:
            data = json.loads(request.body)
            notification_id = data.get('notification_id')
            
            if not notification_id:
                return JsonResponse({'error': 'Notification ID required'}, status=400)
            
            notification = ReorderNotification.objects.get(
                id=notification_id,
                vendor=business_partner
            )
            
            notification.acknowledge(request.user)
            
            return JsonResponse({
                'success': True,
                'message': 'Notification acknowledged successfully',
                'data': {
                    'notification_id': notification_id,
                    'new_status': notification.status,
                    'acknowledged_by': request.user.get_full_name(),
                    'acknowledged_at': notification.acknowledged_at.isoformat()
                }
            })
            
        except ReorderNotification.DoesNotExist:
            return JsonResponse({'error': 'Notification not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def mark_ordered(self, business_partner, request):
        """Mark a reorder notification as ordered"""
        try:
            data = json.loads(request.body)
            notification_id = data.get('notification_id')
            order_reference = data.get('order_reference', '')
            expected_delivery = data.get('expected_delivery')
            
            if not notification_id:
                return JsonResponse({'error': 'Notification ID required'}, status=400)
            
            notification = ReorderNotification.objects.get(
                id=notification_id,
                vendor=business_partner
            )
            
            # Parse expected delivery date if provided
            expected_delivery_date = None
            if expected_delivery:
                try:
                    expected_delivery_date = datetime.strptime(expected_delivery, '%Y-%m-%d').date()
                except ValueError:
                    return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
            
            notification.mark_ordered(order_reference, expected_delivery_date)
            
            return JsonResponse({
                'success': True,
                'message': 'Notification marked as ordered',
                'data': {
                    'notification_id': notification_id,
                    'new_status': notification.status,
                    'order_reference': order_reference,
                    'expected_delivery': expected_delivery_date.isoformat() if expected_delivery_date else None
                }
            })
            
        except ReorderNotification.DoesNotExist:
            return JsonResponse({'error': 'Notification not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def get_health_status(self, health_percentage):
        """Get health status based on percentage"""
        if health_percentage >= 90:
            return 'Excellent'
        elif health_percentage >= 80:
            return 'Good'
        elif health_percentage >= 70:
            return 'Fair'
        elif health_percentage >= 60:
            return 'Poor'
        else:
            return 'Critical'
    
    def get_critical_alerts(self, business_partner):
        """Get critical stock alerts"""
        parts = Part.objects.filter(
            vendor=business_partner,
            is_active=True
        ).select_related('inventory')
        
        alerts = []
        for part in parts:
            current_stock = part.quantity
            safety_stock = part.safety_stock or 0
            
            if current_stock == 0:
                alerts.append((part, 'out_of_stock', 'critical'))
            elif safety_stock > 0 and current_stock < safety_stock:
                alerts.append((part, 'below_safety_stock', 'critical'))
        
        return alerts
    
    def get_high_priority_alerts(self, business_partner):
        """Get high priority stock alerts"""
        parts = Part.objects.filter(
            vendor=business_partner,
            is_active=True
        ).select_related('inventory')
        
        alerts = []
        for part in parts:
            inventory = getattr(part, 'inventory', None)
            current_stock = part.quantity
            reorder_level = inventory.reorder_level if inventory else 10
            
            if current_stock <= reorder_level and current_stock > 0:
                alerts.append((part, 'at_reorder_level', 'high'))
        
        return alerts
    
    def get_medium_priority_alerts(self, business_partner):
        """Get medium priority stock alerts"""
        parts = Part.objects.filter(
            vendor=business_partner,
            is_active=True
        ).select_related('inventory')
        
        alerts = []
        for part in parts:
            inventory = getattr(part, 'inventory', None)
            current_stock = part.quantity
            reorder_level = inventory.reorder_level if inventory else 10
            
            if current_stock <= reorder_level * 1.2 and current_stock > reorder_level:
                alerts.append((part, 'approaching_reorder', 'medium'))
        
        return alerts
    
    def get_all_alerts(self, business_partner):
        """Get all stock alerts"""
        critical = self.get_critical_alerts(business_partner)
        high = self.get_high_priority_alerts(business_partner)
        medium = self.get_medium_priority_alerts(business_partner)
        
        return critical + high + medium


# URL patterns for the API
stock_monitoring_api = StockMonitoringAPI.as_view()