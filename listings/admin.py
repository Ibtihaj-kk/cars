from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Dealer, VehicleListing, ListingImage, ListingView, ListingStatusLog
from .status_manager import ListingStatusManager


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 1
    readonly_fields = ('thumbnail_preview',)
    fields = ('image', 'thumbnail_preview', 'is_primary', 'caption', 'order')
    
    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html('<img src="{}" width="150" height="100" />', obj.thumbnail.url)
        return "-"
    thumbnail_preview.short_description = 'Thumbnail Preview'


class ListingViewInline(admin.TabularInline):
    model = ListingView
    extra = 0
    readonly_fields = ('user', 'ip_address', 'user_agent', 'created_at')
    fields = ('user', 'ip_address', 'created_at')
    can_delete = False
    max_num = 10
    verbose_name_plural = 'Recent Views'
    ordering = ('-created_at',)


class ListingStatusLogInline(admin.TabularInline):
    model = ListingStatusLog
    extra = 0
    readonly_fields = ('old_status', 'new_status', 'changed_by', 'reason', 'timestamp')
    fields = ('old_status', 'new_status', 'changed_by', 'reason', 'timestamp')
    can_delete = False
    max_num = 10
    verbose_name_plural = 'Status History'
    ordering = ('-timestamp',)


@admin.register(Dealer)
class DealerAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'country', 'phone', 'rating', 'review_count', 'is_active', 'is_verified')
    list_filter = ('is_active', 'is_verified', 'country', 'city')
    search_fields = ('name', 'address', 'phone', 'email')
    readonly_fields = ('created_at', 'updated_at')
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'logo')
        }),
        ('Contact Information', {
            'fields': ('address', 'phone', 'email', 'website', 'hours')
        }),
        ('Business Information', {
            'fields': ('license_number', 'rating', 'review_count')
        }),
        ('Location', {
            'fields': ('city', 'state', 'country', 'latitude', 'longitude')
        }),
        ('Status', {
            'fields': ('is_active', 'is_verified')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(VehicleListing)
class VehicleListingAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'dealer', 'vehicle_info', 'price_display', 'status', 'views_display', 'is_featured', 'created_at')
    list_filter = ('status', 'condition', 'is_featured', 'is_premium', 'make', 'fuel_type', 'transmission', 'dealer', 'is_luxury', 'is_certified')
    search_fields = ('title', 'description', 'user__email', 'vin', 'make__name', 'model__name', 'stock_number')
    readonly_fields = ('views_count', 'inquiries_count', 'created_at', 'updated_at', 'slug')
    inlines = [ListingImageInline, ListingViewInline, ListingStatusLogInline]
    list_per_page = 25
    date_hierarchy = 'created_at'
    actions = ['publish_listings', 'suspend_listings', 'mark_as_sold', 'reject_listings']
    
    def vehicle_info(self, obj):
        return f"{obj.make} {obj.model} {obj.year}"
    vehicle_info.short_description = 'Vehicle'
    
    def price_display(self, obj):
        return f"${obj.price:,.2f}"
    price_display.short_description = 'Price'
    price_display.admin_order_field = 'price'
    
    def views_display(self, obj):
        return obj.views_count
    views_display.short_description = 'Views'
    views_display.admin_order_field = 'views_count'
    
    def mark_as_featured(self, request, queryset):
        queryset.update(is_featured=True)
    mark_as_featured.short_description = "Mark selected listings as featured"
    
    def mark_as_premium(self, request, queryset):
        queryset.update(is_premium=True)
    mark_as_premium.short_description = "Mark selected listings as premium"
    
    def mark_as_active(self, request, queryset):
        queryset.update(status='active')
    mark_as_active.short_description = "Mark selected listings as active"
    
    def publish_listings(self, request, queryset):
        """Publish selected listings"""
        success_count = 0
        error_count = 0
        
        for listing in queryset:
            try:
                listing.publish(user=request.user)
                success_count += 1
            except Exception as e:
                error_count += 1
                messages.error(request, f"Failed to publish '{listing.title}': {str(e)}")
        
        if success_count:
            messages.success(request, f'{success_count} listing(s) were successfully published.')
        if error_count:
            messages.warning(request, f'{error_count} listing(s) could not be published.')
    
    publish_listings.short_description = "Publish selected listings"

    def suspend_listings(self, request, queryset):
        """Suspend selected listings"""
        success_count = 0
        error_count = 0
        
        for listing in queryset:
            try:
                listing.suspend(reason="Suspended by admin", user=request.user)
                success_count += 1
            except Exception as e:
                error_count += 1
                messages.error(request, f"Failed to suspend '{listing.title}': {str(e)}")
        
        if success_count:
            messages.success(request, f'{success_count} listing(s) were successfully suspended.')
        if error_count:
            messages.warning(request, f'{error_count} listing(s) could not be suspended.')
    
    suspend_listings.short_description = "Suspend selected listings"

    def mark_as_sold(self, request, queryset):
        """Mark selected listings as sold"""
        success_count = 0
        error_count = 0
        
        for listing in queryset:
            try:
                listing.mark_as_sold(user=request.user)
                success_count += 1
            except Exception as e:
                error_count += 1
                messages.error(request, f"Failed to mark '{listing.title}' as sold: {str(e)}")
        
        if success_count:
            messages.success(request, f'{success_count} listing(s) were successfully marked as sold.')
        if error_count:
            messages.warning(request, f'{error_count} listing(s) could not be marked as sold.')
    
    mark_as_sold.short_description = "Mark selected listings as sold"

    def reject_listings(self, request, queryset):
        """Reject selected listings"""
        success_count = 0
        error_count = 0
        
        for listing in queryset:
            try:
                listing.reject(reason="Rejected by admin", user=request.user)
                success_count += 1
            except Exception as e:
                error_count += 1
                messages.error(request, f"Failed to reject '{listing.title}': {str(e)}")
        
        if success_count:
            messages.success(request, f'{success_count} listing(s) were successfully rejected.')
        if error_count:
            messages.warning(request, f'{error_count} listing(s) could not be rejected.')
    
    reject_listings.short_description = "Reject selected listings"
    
    def save_model(self, request, obj, form, change):
        """Custom save method to handle listing saving properly."""
        try:
            # Save the object normally
            super().save_model(request, obj, form, change)
        except Exception as e:
            # Log the error and re-raise with more context
            messages.error(request, f"Error saving listing: {str(e)}")
            raise
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'user', 'condition', 'status')
        }),
        ('Vehicle Details', {
            'fields': ('year', 'make', 'model', 'fuel_type', 'transmission', 'engine_size', 'doors', 'seating_capacity', 'exterior_color', 'vin')
        }),
        ('Pricing and Mileage', {
            'fields': ('price', 'kilometers')
        }),
        ('Location', {
            'fields': ('location_city', 'location_state', 'location_country')
        }),
        ('Description and Features', {
            'fields': ('description', 'warranty_information', 'additional_features', 'seller_notes')
        }),
        ('Listing Options', {
            'fields': ('is_featured', 'is_premium', 'expires_at')
        }),
        ('SEO Options', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',),
        }),
        ('Statistics', {
            'fields': ('views_count', 'inquiries_count', 'created_at', 'updated_at')
        }),
    )


@admin.register(ListingImage)
class ListingImageAdmin(admin.ModelAdmin):
    list_display = ('listing', 'image_preview', 'is_primary', 'order', 'created_at')
    list_filter = ('is_primary', 'listing__make')
    search_fields = ('listing__title', 'caption')
    readonly_fields = ('image_preview', 'thumbnail_preview')
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="75" />', obj.image.url)
        return "-"
    image_preview.short_description = 'Image Preview'
    
    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html('<img src="{}" width="100" height="75" />', obj.thumbnail.url)
        return "-"
    thumbnail_preview.short_description = 'Thumbnail Preview'


@admin.register(ListingView)
class ListingViewAdmin(admin.ModelAdmin):
    list_display = ('listing', 'user', 'ip_address', 'created_at')
    list_filter = ('created_at', 'listing__make')
    search_fields = ('listing__title', 'user__email', 'ip_address')
    readonly_fields = ('listing', 'user', 'ip_address', 'user_agent', 'created_at')
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ListingStatusLog)
class ListingStatusLogAdmin(admin.ModelAdmin):
    list_display = ('listing', 'old_status', 'new_status', 'changed_by', 'timestamp')
    list_filter = ('old_status', 'new_status', 'timestamp', 'listing__make')
    search_fields = ('listing__title', 'changed_by__username', 'reason')
    readonly_fields = ('listing', 'old_status', 'new_status', 'changed_by', 'reason', 'timestamp')
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
