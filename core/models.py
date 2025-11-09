"""
Core models including AuditLog
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.serializers.json import DjangoJSONEncoder
import json

User = get_user_model()


class AuditLog(models.Model):
    """Comprehensive audit log for tracking all system activities"""
    
    ACTION_TYPES = [
        # User Management
        ('USER_CREATE', 'User Created'),
        ('USER_UPDATE', 'User Updated'),
        ('USER_DELETE', 'User Deleted'),
        ('USER_LOGIN', 'User Login'),
        ('USER_LOGOUT', 'User Logout'),
        ('USER_PASSWORD_CHANGE', 'Password Changed'),
        ('USER_PASSWORD_RESET', 'Password Reset'),
        ('USER_BAN', 'User Banned'),
        ('USER_UNBAN', 'User Unbanned'),
        ('USER_SUSPEND', 'User Suspended'),
        ('USER_UNSUSPEND', 'User Unsuspended'),
        ('USER_ROLE_CHANGE', 'User Role Changed'),
        
        # Permission Management
        ('PERMISSION_GRANT', 'Permission Granted'),
        ('PERMISSION_REVOKE', 'Permission Revoked'),
        ('ROLE_ASSIGN', 'Role Assigned'),
        ('ROLE_REMOVE', 'Role Removed'),
        ('ROLE_CREATE', 'Role Created'),
        ('ROLE_UPDATE', 'Role Updated'),
        ('ROLE_DELETE', 'Role Deleted'),
        
        # Business Partner Management
        ('PARTNER_CREATE', 'Business Partner Created'),
        ('PARTNER_UPDATE', 'Business Partner Updated'),
        ('PARTNER_DELETE', 'Business Partner Deleted'),
        ('PARTNER_APPROVE', 'Business Partner Approved'),
        ('PARTNER_REJECT', 'Business Partner Rejected'),
        ('PARTNER_SUSPEND', 'Business Partner Suspended'),
        ('PARTNER_UNSUSPEND', 'Business Partner Unsuspended'),
        
        # Part Management
        ('PART_CREATE', 'Part Created'),
        ('PART_UPDATE', 'Part Updated'),
        ('PART_DELETE', 'Part Deleted'),
        ('PART_STOCK_UPDATE', 'Part Stock Updated'),
        ('PART_PRICE_UPDATE', 'Part Price Updated'),
        
        # Inventory Management
        ('INVENTORY_CREATE', 'Inventory Created'),
        ('INVENTORY_UPDATE', 'Inventory Updated'),
        ('INVENTORY_DELETE', 'Inventory Deleted'),
        ('STOCK_MOVEMENT', 'Stock Movement'),
        ('STOCK_ALERT', 'Stock Alert'),
        ('REORDER_NOTIFICATION', 'Reorder Notification'),
        
        # Order Management
        ('ORDER_CREATE', 'Order Created'),
        ('ORDER_UPDATE', 'Order Updated'),
        ('ORDER_CANCEL', 'Order Cancelled'),
        ('ORDER_COMPLETE', 'Order Completed'),
        ('ORDER_PAYMENT', 'Order Payment'),
        ('ORDER_SHIPMENT', 'Order Shipment'),
        
        # Document Management
        ('DOCUMENT_UPLOAD', 'Document Uploaded'),
        ('DOCUMENT_UPDATE', 'Document Updated'),
        ('DOCUMENT_DELETE', 'Document Deleted'),
        ('DOCUMENT_APPROVE', 'Document Approved'),
        ('DOCUMENT_REJECT', 'Document Rejected'),
        
        # API Actions
        ('API_CALL', 'API Call'),
        ('API_CREATE', 'API Create'),
        ('API_UPDATE', 'API Update'),
        ('API_DELETE', 'API Delete'),
        ('API_ERROR', 'API Error'),
        
        # Security Events
        ('SECURITY_LOGIN_ATTEMPT', 'Login Attempt'),
        ('SECURITY_PASSWORD_RESET_REQUEST', 'Password Reset Request'),
        ('SECURITY_2FA_ENABLED', '2FA Enabled'),
        ('SECURITY_2FA_DISABLED', '2FA Disabled'),
        ('SECURITY_SUSPICIOUS_ACTIVITY', 'Suspicious Activity'),
        ('SECURITY_RATE_LIMIT_EXCEEDED', 'Rate Limit Exceeded'),
        ('SECURITY_PERMISSION_DENIED', 'Permission Denied'),
        ('SECURITY_UNAUTHORIZED_ACCESS', 'Unauthorized Access'),
        ('SECURITY_DATA_ACCESS', 'Data Access'),
        ('SECURITY_DATA_EXPORT', 'Data Export'),
        ('SECURITY_DATA_IMPORT', 'Data Import'),
        
        # System Events
        ('SYSTEM_STARTUP', 'System Startup'),
        ('SYSTEM_SHUTDOWN', 'System Shutdown'),
        ('SYSTEM_BACKUP', 'System Backup'),
        ('SYSTEM_RESTORE', 'System Restore'),
        ('SYSTEM_MAINTENANCE', 'System Maintenance'),
        ('SYSTEM_ERROR', 'System Error'),
        ('SYSTEM_WARNING', 'System Warning'),
        ('SYSTEM_INFO', 'System Info'),
        
        # Compliance Events
        ('COMPLIANCE_CHECK', 'Compliance Check'),
        ('COMPLIANCE_VIOLATION', 'Compliance Violation'),
        ('COMPLIANCE_REPORT', 'Compliance Report'),
        ('COMPLIANCE_AUDIT', 'Compliance Audit'),
        
        # Analytics Events
        ('ANALYTICS_VIEW', 'Analytics View'),
        ('ANALYTICS_EXPORT', 'Analytics Export'),
        ('ANALYTICS_REPORT', 'Analytics Report'),
        ('ANALYTICS_DASHBOARD_VIEW', 'Analytics Dashboard View'),
        
        # General CRUD
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('VIEW', 'View'),
        ('LOGIN_ATTEMPT', 'Login Attempt'),
    ]
    
    # Core fields
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Object being acted upon
    object_type = models.CharField(max_length=100, null=True, blank=True)
    object_id = models.CharField(max_length=255, null=True, blank=True)
    object_repr = models.TextField(null=True, blank=True)
    
    # Changes made (JSON)
    changes = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
    
    # Request context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    session_id = models.CharField(max_length=255, null=True, blank=True)
    request_path = models.CharField(max_length=500, null=True, blank=True)
    request_method = models.CharField(max_length=10, null=True, blank=True)
    
    # Additional data (JSON)
    additional_data = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
    
    # Success/failure tracking
    success = models.BooleanField(default=True, db_index=True)
    error_message = models.TextField(null=True, blank=True)
    error_traceback = models.TextField(null=True, blank=True)
    
    # Performance metrics (for API calls and operations)
    response_time_ms = models.IntegerField(null=True, blank=True)
    
    # Compliance and retention
    retention_period_days = models.IntegerField(default=2555)  # 7 years default
    compliance_flagged = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'core_audit_log'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action_type', '-timestamp']),
            models.Index(fields=['object_type', 'object_id', '-timestamp']),
            models.Index(fields=['ip_address', '-timestamp']),
            models.Index(fields=['success', '-timestamp']),
            models.Index(fields=['timestamp', 'action_type']),
        ]
    
    def __str__(self):
        user_str = str(self.user) if self.user else 'System'
        return f"{self.get_action_type_display()} by {user_str} at {self.timestamp}"
    
    @property
    def is_security_event(self):
        """Check if this is a security-related event"""
        return self.action_type.startswith('SECURITY_')
    
    @property
    def is_system_event(self):
        """Check if this is a system event"""
        return self.action_type.startswith('SYSTEM_')
    
    @property
    def is_compliance_event(self):
        """Check if this is a compliance event"""
        return self.action_type.startswith('COMPLIANCE_')
    
    @property
    def retention_expires_at(self):
        """Calculate when this log entry expires"""
        return self.timestamp + timedelta(days=self.retention_period_days)
    
    @property
    def is_expired(self):
        """Check if this log entry has expired"""
        return timezone.now() > self.retention_expires_at
    
    def get_changes_summary(self):
        """Get a human-readable summary of changes"""
        if not self.changes:
            return None
        
        summary = []
        for field, change in self.changes.items():
            if isinstance(change, dict) and 'old' in change and 'new' in change:
                summary.append(f"{field}: {change['old']} → {change['new']}")
            else:
                summary.append(f"{field}: {change}")
        
        return '; '.join(summary)


class SystemMetric(models.Model):
    """System performance and monitoring metrics"""
    
    METRIC_TYPES = [
        ('CPU_USAGE', 'CPU Usage'),
        ('MEMORY_USAGE', 'Memory Usage'),
        ('DISK_USAGE', 'Disk Usage'),
        ('RESPONSE_TIME', 'Response Time'),
        ('ERROR_RATE', 'Error Rate'),
        ('ACTIVE_USERS', 'Active Users'),
        ('DB_CONNECTIONS', 'Database Connections'),
        ('CACHE_HIT_RATE', 'Cache Hit Rate'),
        ('QUEUE_SIZE', 'Queue Size'),
        ('BACKUP_SIZE', 'Backup Size'),
        ('API_CALLS', 'API Calls'),
        ('LOGIN_ATTEMPTS', 'Login Attempts'),
        ('SECURITY_EVENTS', 'Security Events'),
        ('COMPLIANCE_SCORE', 'Compliance Score'),
    ]
    
    metric_type = models.CharField(max_length=50, choices=METRIC_TYPES)
    value = models.FloatField()
    unit = models.CharField(max_length=20, default='')
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    metadata = models.JSONField(null=True, blank=True)
    
    class Meta:
        db_table = 'core_system_metrics'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['metric_type', '-timestamp']),
            models.Index(fields=['timestamp', 'metric_type']),
        ]
    
    def __str__(self):
        return f"{self.get_metric_type_display()}: {self.value}{self.unit} at {self.timestamp}"


class ComplianceCheck(models.Model):
    """Compliance checks and their results"""
    
    CHECK_TYPES = [
        ('DATA_RETENTION', 'Data Retention'),
        ('AUDIT_LOG_RETENTION', 'Audit Log Retention'),
        ('USER_ACCESS_REVIEW', 'User Access Review'),
        ('PERMISSION_REVIEW', 'Permission Review'),
        ('SECURITY_SCAN', 'Security Scan'),
        ('BACKUP_VERIFICATION', 'Backup Verification'),
        ('DATA_ENCRYPTION', 'Data Encryption'),
        ('ACCESS_CONTROL', 'Access Control'),
        ('PASSWORD_POLICY', 'Password Policy'),
        ('SESSION_MANAGEMENT', 'Session Management'),
        ('DATA_PRIVACY', 'Data Privacy'),
        ('VENDOR_COMPLIANCE', 'Vendor Compliance'),
        ('INVENTORY_COMPLIANCE', 'Inventory Compliance'),
        ('ORDER_COMPLIANCE', 'Order Compliance'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('PASSED', 'Passed'),
        ('FAILED', 'Failed'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
    ]
    
    check_type = models.CharField(max_length=50, choices=CHECK_TYPES)
    name = models.CharField(max_length=200)
    description = models.TextField()
    
    # Check configuration
    check_config = models.JSONField(default=dict)
    schedule_config = models.JSONField(default=dict)  # For automated scheduling
    
    # Results
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    
    # Results data
    results = models.JSONField(null=True, blank=True)
    issues_found = models.JSONField(null=True, blank=True)
    recommendations = models.JSONField(null=True, blank=True)
    
    # Scoring
    compliance_score = models.FloatField(null=True, blank=True)
    max_score = models.FloatField(default=100.0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Automation
    is_automated = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'core_compliance_checks'
        ordering = ['-last_run']
        indexes = [
            models.Index(fields=['check_type', '-last_run']),
            models.Index(fields=['status', '-last_run']),
            models.Index(fields=['next_run']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_check_type_display()}) - {self.get_status_display()}"
    
    @property
    def compliance_percentage(self):
        """Get compliance percentage"""
        if self.compliance_score and self.max_score:
            return (self.compliance_score / self.max_score) * 100
        return None
    
    @property
    def is_due(self):
        """Check if this check is due to run"""
        if not self.next_run:
            return False
        return timezone.now() >= self.next_run
    
    def mark_as_run(self, status, results=None, issues=None, recommendations=None, score=None):
        """Mark compliance check as run with results"""
        self.status = status
        self.last_run = timezone.now()
        
        if results:
            self.results = results
        if issues:
            self.issues_found = issues
        if recommendations:
            self.recommendations = recommendations
        if score is not None:
            self.compliance_score = score
        
        # Schedule next run if automated
        if self.is_automated and self.schedule_config:
            self.schedule_next_run()
        
        self.save()
    
    def schedule_next_run(self):
        """Schedule next run based on configuration"""
        if not self.schedule_config:
            return
        
        # Simple scheduling - can be extended with cron-like syntax
        interval_hours = self.schedule_config.get('interval_hours', 24)
        self.next_run = timezone.now() + timedelta(hours=interval_hours)


class DashboardWidget(models.Model):
    """Configurable dashboard widgets"""
    
    WIDGET_TYPES = [
        ('CHART_LINE', 'Line Chart'),
        ('CHART_BAR', 'Bar Chart'),
        ('CHART_PIE', 'Pie Chart'),
        ('CHART_AREA', 'Area Chart'),
        ('METRIC_CARD', 'Metric Card'),
        ('TABLE', 'Data Table'),
        ('PROGRESS_BAR', 'Progress Bar'),
        ('GAUGE', 'Gauge'),
        ('MAP', 'Map'),
        ('TEXT', 'Text Widget'),
        ('ALERT_LIST', 'Alert List'),
        ('ACTIVITY_FEED', 'Activity Feed'),
    ]
    
    name = models.CharField(max_length=100)
    widget_type = models.CharField(max_length=30, choices=WIDGET_TYPES)
    description = models.TextField(blank=True)
    
    # Configuration
    config = models.JSONField(default=dict)
    data_source = models.CharField(max_length=200)  # Function or API endpoint
    refresh_interval = models.IntegerField(default=300)  # seconds
    
    # Display settings
    position_row = models.IntegerField(default=0)
    position_col = models.IntegerField(default=0)
    width = models.IntegerField(default=4)
    height = models.IntegerField(default=2)
    
    # Permissions
    required_permission = models.CharField(max_length=100, blank=True)
    required_role = models.CharField(max_length=50, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'core_dashboard_widgets'
        ordering = ['position_row', 'position_col']
    
    def __str__(self):
        return f"{self.name} ({self.get_widget_type_display()})"