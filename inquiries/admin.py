from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import ListingInquiry, InquiryResponse, TestDriveRequest


@admin.register(ListingInquiry)
class ListingInquiryAdmin(admin.ModelAdmin):
    """Admin configuration for ListingInquiry model."""
    
    list_display = [
        'id', 'name', 'email', 'listing_link', 'inquiry_type', 
        'status_badge', 'is_read', 'created_at', 'seller_name'
    ]
    list_filter = [
        'status', 'inquiry_type', 'is_read', 'created_at'
    ]
    search_fields = [
        'name', 'email', 'phone', 'message', 
        'listing__title', 'listing__make', 'listing__model'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'ip_address', 'user_agent',
        'seller_name', 'listing_link'
    ]
    fieldsets = (
        ('Inquiry Information', {
            'fields': ('listing', 'user', 'name', 'email', 'phone', 'inquiry_type', 'message')
        }),
        ('Status & Tracking', {
            'fields': ('status', 'is_read')
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Related Information', {
            'fields': ('seller_name', 'listing_link'),
            'classes': ('collapse',)
        })
    )
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    def status_badge(self, obj):
        """Display status with color coding."""
        colors = {
            'new': '#dc3545',      # Red
            'viewed': '#ffc107',   # Yellow
            'replied': '#17a2b8',  # Blue
            'closed': '#28a745'    # Green
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def listing_link(self, obj):
        """Display link to the listing."""
        if obj.listing:
            url = reverse('admin:listings_vehiclelisting_change', args=[obj.listing.pk])
            return format_html('<a href="{}">{}</a>', url, obj.listing.title)
        return '-'
    listing_link.short_description = 'Listing'
    
    def seller_name(self, obj):
        """Display seller name."""
        return obj.seller.get_full_name() if obj.seller else '-'
    seller_name.short_description = 'Seller'
    
    actions = ['mark_as_viewed', 'mark_as_replied', 'mark_as_closed']
    
    def mark_as_viewed(self, request, queryset):
        """Mark selected inquiries as viewed."""
        updated = queryset.update(status='viewed')
        self.message_user(request, f'{updated} inquiries marked as viewed.')
    mark_as_viewed.short_description = 'Mark selected inquiries as viewed'
    
    def mark_as_replied(self, request, queryset):
        """Mark selected inquiries as replied."""
        updated = queryset.update(status='replied')
        self.message_user(request, f'{updated} inquiries marked as replied.')
    mark_as_replied.short_description = 'Mark selected inquiries as replied'
    
    def mark_as_closed(self, request, queryset):
        """Mark selected inquiries as closed."""
        updated = queryset.update(status='closed')
        self.message_user(request, f'{updated} inquiries marked as closed.')
    mark_as_closed.short_description = 'Mark selected inquiries as closed'


@admin.register(InquiryResponse)
class InquiryResponseAdmin(admin.ModelAdmin):
    """Admin configuration for InquiryResponse model."""
    
    list_display = [
        'id', 'inquiry_link', 'responder', 'response_preview', 'created_at'
    ]
    list_filter = ['created_at', 'responder']
    search_fields = ['message', 'inquiry__name', 'inquiry__email', 'responder__email']
    readonly_fields = ['created_at']
    fieldsets = (
        ('Response Information', {
            'fields': ('inquiry', 'responder', 'message')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    def inquiry_link(self, obj):
        """Display link to the inquiry."""
        url = reverse('admin:inquiries_listinginquiry_change', args=[obj.inquiry.pk])
        return format_html('<a href="{}">Inquiry #{}</a>', url, obj.inquiry.pk)
    inquiry_link.short_description = 'Inquiry'
    
    def response_preview(self, obj):
        """Display preview of response."""
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    response_preview.short_description = 'Response Preview'


@admin.register(TestDriveRequest)
class TestDriveRequestAdmin(admin.ModelAdmin):
    """Admin configuration for TestDriveRequest model."""
    
    list_display = [
        'id', 'inquiry_link', 'preferred_date', 'preferred_time', 
        'is_confirmed', 'confirmation_date'
    ]
    list_filter = ['is_confirmed', 'preferred_date', 'confirmation_date']
    search_fields = [
        'inquiry__name', 'inquiry__email', 'additional_notes',
        'inquiry__listing__title', 'location_preference'
    ]
    readonly_fields = ['confirmation_date']
    fieldsets = (
        ('Test Drive Information', {
            'fields': ('inquiry', 'preferred_date', 'preferred_time', 
                      'alternate_date', 'alternate_time', 'location_preference', 'additional_notes')
        }),
        ('Confirmation', {
            'fields': ('is_confirmed', 'confirmed_by', 'confirmation_date')
        })
    )
    ordering = ['preferred_date', 'preferred_time']
    date_hierarchy = 'preferred_date'
    
    def inquiry_link(self, obj):
        """Display link to the inquiry."""
        url = reverse('admin:inquiries_listinginquiry_change', args=[obj.inquiry.pk])
        return format_html('<a href="{}">Inquiry #{}</a>', url, obj.inquiry.pk)
    inquiry_link.short_description = 'Inquiry'
    
    actions = ['mark_as_confirmed', 'mark_as_unconfirmed']
    
    def mark_as_confirmed(self, request, queryset):
        """Mark selected test drives as confirmed."""
        from django.utils import timezone
        updated = queryset.update(is_confirmed=True, confirmation_date=timezone.now(), confirmed_by=request.user)
        self.message_user(request, f'{updated} test drives marked as confirmed.')
    mark_as_confirmed.short_description = 'Mark selected test drives as confirmed'
    
    def mark_as_unconfirmed(self, request, queryset):
        """Mark selected test drives as unconfirmed."""
        updated = queryset.update(is_confirmed=False, confirmation_date=None, confirmed_by=None)
        self.message_user(request, f'{updated} test drives marked as unconfirmed.')
    mark_as_unconfirmed.short_description = 'Mark selected test drives as unconfirmed'
