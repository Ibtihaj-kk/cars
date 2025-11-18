from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    VendorApplication, BusinessPartner, BusinessPartnerRole,
    ReorderNotification, VendorAuditLog
)
from .document_models import VendorDocument, DocumentCategory
from .workflow_engine import VendorComplianceCheck


class VendorApplicationSerializer(serializers.ModelSerializer):
    """Serializer for VendorApplication model."""
    
    class Meta:
        model = VendorApplication
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at', 'user')


class VendorApplicationListSerializer(serializers.ModelSerializer):
    """List serializer for VendorApplication with summary fields."""
    
    class Meta:
        model = VendorApplication
        fields = ['id', 'company_name', 'contact_email', 'status', 'created_at', 'priority']


class VendorApplicationReviewSerializer(serializers.ModelSerializer):
    """Serializer for vendor application review operations."""
    
    class Meta:
        model = VendorApplication
        fields = ['status', 'notes', 'reviewed_at', 'reviewed_by']
        read_only_fields = ('reviewed_at', 'reviewed_by')


class BusinessPartnerSerializer(serializers.ModelSerializer):
    """Serializer for BusinessPartner model."""
    
    class Meta:
        model = BusinessPartner
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at', 'bp_number')


class VendorDocumentSerializer(serializers.ModelSerializer):
    """Serializer for VendorDocument model."""
    
    class Meta:
        model = VendorDocument
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at', 'uploaded_by')


class DocumentCategorySerializer(serializers.ModelSerializer):
    """Serializer for DocumentCategory model."""
    
    class Meta:
        model = DocumentCategory
        fields = '__all__'


class VendorComplianceSerializer(serializers.ModelSerializer):
    """Serializer for VendorComplianceCheck model."""
    
    class Meta:
        model = VendorComplianceCheck
        fields = '__all__'


class VendorPerformanceSerializer(serializers.Serializer):
    """Serializer for vendor performance data."""
    
    vendor_id = serializers.IntegerField()
    vendor_name = serializers.CharField()
    total_orders = serializers.IntegerField(default=0)
    completed_orders = serializers.IntegerField(default=0)
    on_time_delivery_rate = serializers.FloatField(default=0.0)
    quality_score = serializers.FloatField(default=0.0)
    average_rating = serializers.FloatField(default=0.0)
    performance_score = serializers.FloatField(default=0.0)
    period_start = serializers.DateField()
    period_end = serializers.DateField()


class VendorAnalyticsSerializer(serializers.Serializer):
    """Serializer for vendor analytics data."""
    
    total_vendors = serializers.IntegerField(default=0)
    active_vendors = serializers.IntegerField(default=0)
    pending_applications = serializers.IntegerField(default=0)
    total_orders = serializers.IntegerField(default=0)
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    top_performing_vendors = serializers.ListField(child=serializers.DictField(), default=list)
    recent_orders = serializers.ListField(child=serializers.DictField(), default=list)


class ReorderNotificationSerializer(serializers.ModelSerializer):
    """Serializer for ReorderNotification model."""
    
    class Meta:
        model = ReorderNotification
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')