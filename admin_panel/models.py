from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class ActivityLogType(models.TextChoices):
    CREATE = 'create', 'Create'
    UPDATE = 'update', 'Update'
    DELETE = 'delete', 'Delete'
    LOGIN = 'login', 'Login'
    LOGOUT = 'logout', 'Logout'
    VIEW = 'view', 'View'
    EXPORT = 'export', 'Export'
    IMPORT = 'import', 'Import'
    OTHER = 'other', 'Other'


class ActivityLog(models.Model):
    """Model for tracking admin user activities."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activity_logs', null=True, blank=True)
    action_type = models.CharField(max_length=20, choices=ActivityLogType.choices)
    action_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    description = models.TextField()
    
    # Generic relation to the object this activity is about
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, blank=True, null=True)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Additional data as JSON
    data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-action_time']
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'
        indexes = [
            models.Index(fields=['action_type']),
            models.Index(fields=['action_time']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.get_action_type_display()} - {self.action_time}"


class AdminSetting(models.Model):
    """Model for storing admin panel settings."""
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    value_type = models.CharField(max_length=20, default='string',
                                help_text='Data type of the value (string, integer, boolean, json)')
    description = models.TextField(blank=True, null=True)
    is_public = models.BooleanField(default=False, help_text='Whether this setting is accessible to public API')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                  null=True, blank=True, related_name='updated_settings')
    
    class Meta:
        ordering = ['key']
        verbose_name = 'Admin Setting'
        verbose_name_plural = 'Admin Settings'
    
    def __str__(self):
        return self.key


class DashboardWidget(models.Model):
    """Model for customizable dashboard widgets."""
    WIDGET_TYPE_CHOICES = [
        ('chart', 'Chart'),
        ('counter', 'Counter'),
        ('list', 'List'),
        ('table', 'Table'),
        ('custom', 'Custom'),
    ]
    
    title = models.CharField(max_length=100)
    widget_type = models.CharField(max_length=20, choices=WIDGET_TYPE_CHOICES)
    data_source = models.CharField(max_length=255, help_text='API endpoint or function name for data')
    refresh_interval = models.PositiveIntegerField(default=0, help_text='Refresh interval in seconds (0 for no auto-refresh)')
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    size = models.CharField(max_length=20, default='medium', help_text='Widget size (small, medium, large)')
    config = models.JSONField(default=dict, blank=True, help_text='Widget configuration as JSON')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.title


class UserDashboardPreference(models.Model):
    """Model for storing user dashboard preferences."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dashboard_preference')
    widgets = models.ManyToManyField(DashboardWidget, through='UserWidgetSetting')
    layout = models.JSONField(default=dict, blank=True, help_text='Dashboard layout configuration')
    theme = models.CharField(max_length=50, default='default')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Dashboard preferences for {self.user.email}"


class UserWidgetSetting(models.Model):
    """Model for user-specific widget settings."""
    user_preference = models.ForeignKey(UserDashboardPreference, on_delete=models.CASCADE)
    widget = models.ForeignKey(DashboardWidget, on_delete=models.CASCADE)
    is_visible = models.BooleanField(default=True)
    position = models.PositiveIntegerField(default=0)
    custom_config = models.JSONField(default=dict, blank=True, help_text='User-specific widget configuration')
    
    class Meta:
        ordering = ['position']
        unique_together = ['user_preference', 'widget']
    
    def __str__(self):
        return f"{self.widget.title} settings for {self.user_preference.user.email}"
