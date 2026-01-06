from django.contrib import admin
from core.email_service.models import EmailQueue, EmailTemplate, EmailAnalytics

# Register your models here.

@admin.register(EmailQueue)
class EmailQueueAdmin(admin.ModelAdmin):
    list_display = ['message_id', 'to_email', 'subject', 'email_type', 'status', 'priority', 'created_at']
    list_filter = ['status', 'priority', 'email_type', 'created_at']
    search_fields = ['to_email', 'subject', 'email_type']
    readonly_fields = ['message_id', 'created_at', 'processing_started_at', 'processing_completed_at', 'sent_at']
    list_per_page = 50

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'version', 'template_type', 'is_active', 'updated_at']
    list_filter = ['template_type', 'is_active', 'updated_at']
    search_fields = ['name', 'description', 'subject_template']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(EmailAnalytics)
class EmailAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['message_id', 'event_type', 'provider', 'created_at']
    list_filter = ['event_type', 'provider', 'created_at']
    search_fields = ['message_id', 'provider_message_id']
    readonly_fields = ['created_at']
