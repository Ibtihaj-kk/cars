import logging
from datetime import datetime, timedelta
from django.db.models import Count, Sum, Avg, Q, F
from django.utils import timezone
from parts.models import Order, OrderItem, InventoryTransaction
from .models import BusinessPartner

logger = logging.getLogger(__name__)


class VendorPerformanceCalculator:
    """Calculates vendor performance metrics."""
    
    def calculate_vendor_performance(self, vendor, start_date, end_date):
        """Calculate comprehensive performance metrics for a vendor."""
        try:
            # Convert string dates to datetime objects if needed
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Get orders for the vendor in the specified period
            orders = Order.objects.filter(
                vendor=vendor,
                created_at__date__range=[start_date, end_date]
            ).select_related('vendor')
            
            # Calculate basic metrics
            total_orders = orders.count()
            completed_orders = orders.filter(status='completed').count()
            
            # Calculate on-time delivery rate
            on_time_orders = orders.filter(
                status='completed',
                delivered_at__lte=F('expected_delivery_date')
            ).count()
            
            on_time_delivery_rate = (on_time_orders / completed_orders * 100) if completed_orders > 0 else 0.0
            
            # Calculate quality score based on return rate
            returned_orders = orders.filter(has_returns=True).count()
            quality_score = 100.0 - ((returned_orders / total_orders * 100) if total_orders > 0 else 0.0)
            
            # Calculate average rating
            avg_rating = orders.filter(rating__isnull=False).aggregate(
                avg_rating=Avg('rating')
            )['avg_rating'] or 0.0
            
            # Calculate overall performance score (weighted average)
            performance_score = (
                (on_time_delivery_rate * 0.4) +  # 40% weight on delivery
                (quality_score * 0.3) +          # 30% weight on quality
                (avg_rating * 20 * 0.3)          # 30% weight on rating (assuming 5-star scale)
            )
            
            return {
                'vendor_id': vendor.id,
                'vendor_name': vendor.name,
                'total_orders': total_orders,
                'completed_orders': completed_orders,
                'on_time_delivery_rate': round(on_time_delivery_rate, 2),
                'quality_score': round(quality_score, 2),
                'average_rating': round(avg_rating, 2),
                'performance_score': round(performance_score, 2),
                'period_start': start_date.strftime('%Y-%m-%d'),
                'period_end': end_date.strftime('%Y-%m-%d')
            }
            
        except Exception as e:
            logger.error(f"Error calculating vendor performance for {vendor.id}: {str(e)}", exc_info=True)
            return {
                'vendor_id': vendor.id,
                'vendor_name': vendor.name,
                'total_orders': 0,
                'completed_orders': 0,
                'on_time_delivery_rate': 0.0,
                'quality_score': 0.0,
                'average_rating': 0.0,
                'performance_score': 0.0,
                'period_start': start_date.strftime('%Y-%m-%d'),
                'period_end': end_date.strftime('%Y-%m-%d'),
                'error': str(e)
            }


class VendorPerformanceAnalyzer:
    """Analyzes vendor performance trends and patterns."""
    
    def get_vendor_performance_trend(self, vendor, months=6):
        """Get performance trend data for the specified number of months."""
        try:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=months * 30)
            
            calculator = VendorPerformanceCalculator()
            trend_data = []
            
            # Calculate performance for each month
            for i in range(months):
                month_start = start_date + timedelta(days=i * 30)
                month_end = month_start + timedelta(days=30)
                
                monthly_performance = calculator.calculate_vendor_performance(
                    vendor, month_start, month_end
                )
                trend_data.append({
                    'month': month_start.strftime('%Y-%m'),
                    'performance_score': monthly_performance['performance_score'],
                    'on_time_delivery_rate': monthly_performance['on_time_delivery_rate'],
                    'quality_score': monthly_performance['quality_score'],
                    'average_rating': monthly_performance['average_rating']
                })
            
            return {
                'vendor_id': vendor.id,
                'vendor_name': vendor.name,
                'trend_data': trend_data,
                'average_performance': sum(d['performance_score'] for d in trend_data) / len(trend_data) if trend_data else 0.0
            }
            
        except Exception as e:
            logger.error(f"Error calculating performance trend for vendor {vendor.id}: {str(e)}", exc_info=True)
            return {
                'vendor_id': vendor.id,
                'vendor_name': vendor.name,
                'trend_data': [],
                'average_performance': 0.0,
                'error': str(e)
            }
    
    def get_top_performing_vendors(self, limit=10, period_days=30):
        """Get top performing vendors for the specified period."""
        try:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=period_days)
            
            calculator = VendorPerformanceCalculator()
            vendors = BusinessPartner.objects.filter(type='vendor', status='active')
            
            performance_scores = []
            for vendor in vendors:
                performance = calculator.calculate_vendor_performance(vendor, start_date, end_date)
                performance_scores.append({
                    'vendor_id': vendor.id,
                    'vendor_name': vendor.name,
                    'performance_score': performance['performance_score'],
                    'total_orders': performance['total_orders'],
                    'on_time_delivery_rate': performance['on_time_delivery_rate'],
                    'quality_score': performance['quality_score'],
                    'average_rating': performance['average_rating']
                })
            
            # Sort by performance score and return top performers
            performance_scores.sort(key=lambda x: x['performance_score'], reverse=True)
            return performance_scores[:limit]
            
        except Exception as e:
            logger.error(f"Error getting top performing vendors: {str(e)}", exc_info=True)
            return []
    
    def identify_performance_issues(self, vendor):
        """Identify potential performance issues for a vendor."""
        try:
            calculator = VendorPerformanceCalculator()
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=90)  # Look at last 90 days
            
            performance = calculator.calculate_vendor_performance(vendor, start_date, end_date)
            
            issues = []
            
            # Check for low on-time delivery rate
            if performance['on_time_delivery_rate'] < 80:
                issues.append({
                    'type': 'delivery',
                    'severity': 'high' if performance['on_time_delivery_rate'] < 60 else 'medium',
                    'message': f'Low on-time delivery rate: {performance["on_time_delivery_rate"]}%',
                    'metric': performance['on_time_delivery_rate']
                })
            
            # Check for low quality score
            if performance['quality_score'] < 85:
                issues.append({
                    'type': 'quality',
                    'severity': 'high' if performance['quality_score'] < 70 else 'medium',
                    'message': f'Low quality score: {performance["quality_score"]}%',
                    'metric': performance['quality_score']
                })
            
            # Check for low average rating
            if performance['average_rating'] < 3.0:
                issues.append({
                    'type': 'rating',
                    'severity': 'high' if performance['average_rating'] < 2.0 else 'medium',
                    'message': f'Low average rating: {performance["average_rating"]} stars',
                    'metric': performance['average_rating']
                })
            
            # Check for declining performance trend
            trend_data = self.get_vendor_performance_trend(vendor, months=3)
            if trend_data['trend_data'] and len(trend_data['trend_data']) >= 2:
                recent_performance = trend_data['trend_data'][-1]['performance_score']
                previous_performance = trend_data['trend_data'][-2]['performance_score']
                
                if recent_performance < previous_performance * 0.8:  # 20% decline
                    issues.append({
                        'type': 'trend',
                        'severity': 'high',
                        'message': f'Declining performance trend: {previous_performance:.1f} → {recent_performance:.1f}',
                        'metric': recent_performance
                    })
            
            return {
                'vendor_id': vendor.id,
                'vendor_name': vendor.name,
                'issues': issues,
                'overall_performance': performance['performance_score']
            }
            
        except Exception as e:
            logger.error(f"Error identifying performance issues for vendor {vendor.id}: {str(e)}", exc_info=True)
            return {
                'vendor_id': vendor.id,
                'vendor_name': vendor.name,
                'issues': [],
                'overall_performance': 0.0,
                'error': str(e)
            }