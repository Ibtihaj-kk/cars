"""
Analytics serializers for API responses
"""
from rest_framework import serializers
from .models import (
    SalesMetric, RevenueTracking, VendorAnalytics, 
    SalesForecast, CustomerAnalytics
)


class SalesMetricSerializer(serializers.ModelSerializer):
    """Serializer for sales metrics"""
    
    class Meta:
        model = SalesMetric
        fields = [
            'id', 'metric_type', 'period', 'date_from', 'date_to',
            'value', 'value_formatted', 'vendor', 'category', 'part'
        ]
        read_only_fields = ['id']


class RevenueTrackingSerializer(serializers.ModelSerializer):
    """Serializer for revenue tracking"""
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = RevenueTracking
        fields = [
            'id', 'vendor', 'vendor_name', 'revenue_type', 'amount', 'currency',
            'transaction_date', 'transaction_time', 'order', 'order_number',
            'description', 'reference_number', 'is_confirmed', 'is_recurring',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class VendorAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for vendor analytics"""
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    
    class Meta:
        model = VendorAnalytics
        fields = [
            'id', 'vendor', 'vendor_name', 'total_revenue', 'total_orders',
            'average_order_value', 'customer_count', 'total_parts_listed',
            'parts_in_stock', 'low_stock_alerts', 'out_of_stock_count',
            'last_sale_date', 'last_order_date', 'performance_score',
            'reliability_score', 'customer_satisfaction', 'revenue_growth_rate',
            'order_growth_rate', 'last_calculated', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class SalesForecastSerializer(serializers.ModelSerializer):
    """Serializer for sales forecasts"""
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    accuracy_percentage_display = serializers.SerializerMethodField()
    
    class Meta:
        model = SalesForecast
        fields = [
            'id', 'vendor', 'vendor_name', 'forecast_type', 'forecast_date',
            'forecast_period', 'predicted_revenue', 'predicted_orders',
            'confidence_level', 'historical_data_points', 'historical_period_days',
            'actual_revenue', 'actual_orders', 'accuracy_percentage',
            'accuracy_percentage_display', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_accuracy_percentage_display(self, obj):
        """Get formatted accuracy percentage"""
        if obj.accuracy_percentage is not None:
            return f"{obj.accuracy_percentage:.1f}%"
        return "N/A"


class CustomerAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for customer analytics"""
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    loyalty_score_display = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomerAnalytics
        fields = [
            'id', 'customer', 'customer_name', 'total_orders', 'total_spent',
            'average_order_value', 'first_order_date', 'last_order_date',
            'days_since_last_order', 'preferred_categories', 'preferred_vendors',
            'loyalty_score', 'loyalty_score_display', 'customer_lifetime_value',
            'customer_segment', 'risk_level', 'last_updated', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_loyalty_score_display(self, obj):
        """Get formatted loyalty score"""
        return f"{obj.loyalty_score:.1f}/100"


class DashboardSummarySerializer(serializers.Serializer):
    """Serializer for dashboard summary data"""
    
    # Revenue metrics
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    revenue_growth = serializers.FloatField()
    monthly_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    # Order metrics
    total_orders = serializers.IntegerField()
    orders_growth = serializers.FloatField()
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    # Customer metrics
    total_customers = serializers.IntegerField()
    new_customers = serializers.IntegerField()
    returning_customers = serializers.IntegerField()
    
    # Stock metrics
    total_parts = serializers.IntegerField()
    low_stock_items = serializers.IntegerField()
    out_of_stock_items = serializers.IntegerField()
    
    # Performance metrics
    performance_score = serializers.FloatField()
    top_selling_parts = serializers.ListField()
    recent_orders = serializers.ListField()
    
    # Charts data
    revenue_chart_data = serializers.DictField()
    orders_chart_data = serializers.DictField()
    stock_chart_data = serializers.DictField()


class RevenueFilterSerializer(serializers.Serializer):
    """Serializer for revenue filtering parameters"""
    
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    vendor_id = serializers.IntegerField(required=False)
    revenue_type = serializers.ChoiceField(
        choices=RevenueTracking.REVENUE_TYPES,
        required=False
    )
    group_by = serializers.ChoiceField(
        choices=['day', 'week', 'month', 'quarter', 'year'],
        default='month'
    )
    include_forecast = serializers.BooleanField(default=False)
    
    def validate(self, data):
        """Validate filter parameters"""
        if 'date_from' in data and 'date_to' in data:
            if data['date_from'] > data['date_to']:
                raise serializers.ValidationError(
                    "date_from must be before date_to"
                )
        return data


class SalesReportSerializer(serializers.Serializer):
    """Serializer for sales reports"""
    
    report_type = serializers.ChoiceField(
        choices=['revenue', 'orders', 'parts', 'customers', 'performance']
    )
    period = serializers.ChoiceField(
        choices=['daily', 'weekly', 'monthly', 'quarterly', 'yearly', 'custom']
    )
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    vendor_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False
    )
    format = serializers.ChoiceField(
        choices=['json', 'csv', 'pdf'],
        default='json'
    )
    
    def validate(self, data):
        """Validate report parameters"""
        if data['period'] == 'custom':
            if not data.get('date_from') or not data.get('date_to'):
                raise serializers.ValidationError(
                    "date_from and date_to are required for custom period"
                )
            if data['date_from'] > data['date_to']:
                raise serializers.ValidationError(
                    "date_from must be before date_to"
                )
        return data


class ChartDataSerializer(serializers.Serializer):
    """Serializer for chart data responses"""
    
    labels = serializers.ListField(child=serializers.CharField())
    datasets = serializers.ListField(
        child=serializers.DictField()
    )
    chart_type = serializers.CharField()
    title = serializers.CharField()
    
    
class PerformanceMetricSerializer(serializers.Serializer):
    """Serializer for performance metrics"""
    
    metric_name = serializers.CharField()
    current_value = serializers.FloatField()
    previous_value = serializers.FloatField()
    change_percentage = serializers.FloatField()
    trend = serializers.ChoiceField(choices=['up', 'down', 'stable'])
    target_value = serializers.FloatField(required=False)
    performance_percentage = serializers.FloatField(required=False)