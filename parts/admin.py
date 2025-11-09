from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Category, Brand, Part, Inventory, Order, OrderItem, 
    Review, BulkUploadLog, IntegrationSource
)
from .forms import PartAdminForm


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parts_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    
    def parts_count(self, obj):
        return obj.parts.count()
    parts_count.short_description = 'Parts Count'


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'logo_preview', 'is_active', 'parts_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover;" />',
                obj.logo.url
            )
        return "No Logo"
    logo_preview.short_description = 'Logo'
    
    def parts_count(self, obj):
        return obj.parts.count()
    parts_count.short_description = 'Parts Count'


class InventoryInline(admin.StackedInline):
    model = Inventory
    extra = 0
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    form = PartAdminForm  # Use the comprehensive admin form
    list_display = [
        'parts_number', 'material_description', 'sku', 'category', 'brand', 
        'price', 'quantity', 'is_active', 'is_featured', 'dealer', 'created_at'
    ]
    list_filter = [
        'is_active', 'is_featured', 'category', 'brand', 'dealer',
        'material_type', 'plant', 'abc_indicator', 'industry_sector',
        'procurement_type', 'mrp_type', 'price_control_indicator', 'created_at'
    ]
    search_fields = [
        'parts_number', 'material_description', 'material_description_ar',
        'name', 'sku', 'description', 'manufacturer_part_number', 
        'manufacturer_oem_number', 'old_material_number', 'mrp_controller',
        'purchasing_group', 'profit_center'
    ]
    prepopulated_fields = {'slug': ('name', 'sku')}
    readonly_fields = [
        'created_at', 'updated_at', 'view_count',
        'user_visible_fields_display', 'vendor_admin_fields_display'
    ]
    inlines = [InventoryInline]
    
    fieldsets = (
        ('Core Identification', {
            'fields': ('parts_number', 'sku', 'name', 'slug'),
            'description': 'Primary identification fields for the part'
        }),
        ('USER-VISIBLE FIELDS (Dark Green)', {
            'fields': (
                'material_description', 'material_description_ar',
                'base_unit_of_measure', 'gross_weight', 'net_weight', 'weight_of_unit',
                'size_dimensions', 'manufacturer_part_number', 'manufacturer_oem_number'
            ),
            'description': 'Fields visible to end users in the public interface',
            'classes': ('wide',)
        }),
        ('VENDOR/ADMIN-ONLY FIELDS', {
            'fields': (
                ('material_type', 'plant', 'storage_location'),
                ('warehouse_number', 'storage_bin', 'material_group', 'division'),
                ('minimum_order_quantity', 'old_material_number', 'expiration_xchpf'),
                ('external_material_group', 'abc_indicator', 'industry_sector'),
                ('safety_stock', 'minimum_safety_stock', 'reorder_point'),
                ('planned_delivery_time_days', 'goods_receipt_processing_time_days', 'total_replenishment_lead_time'),
                ('valuation_class', 'valuation_category', 'price_unit_peinh'),
                ('moving_average_price', 'standard_price', 'price_control_indicator'),
                ('procurement_type', 'mrp_type', 'mrp_controller', 'mrp_group'),
                ('purchasing_group', 'profit_center', 'account_assignment_group'),
                ('lot_size', 'forecast_model', 'forecast_periods', 'historical_periods'),
                ('period_indicator', 'initialization_indicator', 'availability_check'),
                ('sales_organization', 'distribution_channel', 'material_pricing_group'),
                ('item_category_group', 'general_item_category_group', 'loading_group'),
                ('transportation_group', 'tax_classification_material')
            ),
            'description': 'Fields visible only to vendors and administrators',
            'classes': ('collapse', 'wide')
        }),
        ('Relationships', {
            'fields': ('dealer', 'category', 'brand')
        }),
        ('Legacy & Compatibility Fields', {
            'fields': ('description', 'price', 'quantity'),
            'description': 'Legacy fields maintained for backward compatibility',
            'classes': ('collapse',)
        }),
        ('Media & Visual', {
            'fields': ('image', 'image_url'),
            'classes': ('collapse',)
        }),
        ('Physical Properties (Legacy)', {
            'fields': ('weight', 'dimensions', 'warranty_period'),
            'description': 'Legacy physical property fields',
            'classes': ('collapse',)
        }),
        ('Status & Metadata', {
            'fields': ('is_active', 'is_featured', 'view_count'),
        }),
        ('Field Visibility Reference', {
            'fields': ('user_visible_fields_display', 'vendor_admin_fields_display'),
            'description': 'Reference lists showing field visibility separation',
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_visible_fields_display(self, obj):
        """Display user-visible fields as a formatted list."""
        if obj.pk:
            fields = obj.user_visible_fields()
            return format_html(
                '<div style="max-height: 200px; overflow-y: auto;">'
                '<strong>User-Visible Fields:</strong><br>'
                '{}</div>',
                '<br>'.join([f"• {field}" for field in fields])
            )
        return "Save the part to see field visibility"
    user_visible_fields_display.short_description = 'User-Visible Fields'
    
    def vendor_admin_fields_display(self, obj):
        """Display vendor/admin fields as a formatted list."""
        if obj.pk:
            fields = obj.vendor_admin_fields()
            return format_html(
                '<div style="max-height: 200px; overflow-y: auto;">'
                '<strong>Vendor/Admin-Only Fields:</strong><br>'
                '{}</div>',
                '<br>'.join([f"• {field}" for field in fields])
            )
        return "Save the part to see field visibility"
    vendor_admin_fields_display.short_description = 'Vendor/Admin-Only Fields'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'category', 'brand', 'dealer'
        )
    
    def save_model(self, request, obj, form, change):
        """Override save to ensure proper field handling."""
        # Set dealer to current user if not set and user is a dealer
        if not obj.dealer and hasattr(request.user, 'is_dealer') and request.user.is_dealer:
            obj.dealer = request.user
        
        super().save_model(request, obj, form, change)
    
    class Media:
        css = {
            'all': ('admin/css/parts_admin.css',)
        }
        js = ('admin/js/parts_admin.js',)


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = [
        'part', 'stock', 'reorder_level', 'stock_status', 
        'needs_reorder', 'last_restock_date'
    ]
    list_filter = ['last_restock_date', 'created_at']
    search_fields = ['part__name', 'part__sku']
    readonly_fields = ['created_at', 'updated_at', 'stock_status', 'needs_reorder']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('part')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['total_price']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'customer_info', 'total_price', 
        'status', 'created_at', 'is_guest_order'
    ]
    list_filter = ['status', 'created_at', 'shipped_at', 'delivered_at']
    search_fields = [
        'order_number', 'customer__email', 'guest_name', 
        'guest_email', 'tracking_number'
    ]
    readonly_fields = [
        'order_number', 'created_at', 'updated_at', 
        'is_guest_order', 'customer_name', 'customer_email'
    ]
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'status', 'tracking_number')
        }),
        ('Customer Information', {
            'fields': ('customer', 'is_guest_order', 'customer_name', 'customer_email')
        }),
        ('Guest Information', {
            'fields': ('guest_name', 'guest_email', 'guest_phone', 'guest_address'),
            'classes': ('collapse',)
        }),
        ('Pricing', {
            'fields': ('total_price', 'shipping_cost', 'tax_amount')
        }),
        ('Notes & Tracking', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'shipped_at', 'delivered_at'),
            'classes': ('collapse',)
        }),
    )
    
    def customer_info(self, obj):
        if obj.customer:
            return f"{obj.customer.email}"
        return f"{obj.guest_name} ({obj.guest_email})"
    customer_info.short_description = 'Customer'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('customer')


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'part', 'quantity', 'price', 'total_price']
    list_filter = ['created_at']
    search_fields = ['order__order_number', 'part__name', 'part__sku']
    readonly_fields = ['total_price', 'created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order', 'part')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        'part', 'user', 'rating', 'is_verified_purchase', 
        'is_approved', 'created_at'
    ]
    list_filter = [
        'rating', 'is_verified_purchase', 'is_approved', 'created_at'
    ]
    search_fields = ['part__name', 'user__email', 'comment']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Review Information', {
            'fields': ('part', 'user', 'rating', 'comment')
        }),
        ('Status', {
            'fields': ('is_verified_purchase', 'is_approved')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('part', 'user')


@admin.register(BulkUploadLog)
class BulkUploadLogAdmin(admin.ModelAdmin):
    list_display = [
        'file_name', 'user', 'status', 'total_records', 
        'successful_records', 'failed_records', 'success_rate_display', 
        'uploaded_at'
    ]
    list_filter = ['status', 'uploaded_at']
    search_fields = ['file_name', 'user__email']
    readonly_fields = [
        'uploaded_at', 'completed_at', 'success_rate', 'success_rate_display'
    ]
    
    fieldsets = (
        ('Upload Information', {
            'fields': ('user', 'file_name', 'file_size', 'status')
        }),
        ('Statistics', {
            'fields': (
                'total_records', 'successful_records', 'failed_records', 
                'success_rate', 'success_rate_display'
            )
        }),
        ('Logs', {
            'fields': ('error_log', 'success_message'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('uploaded_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def success_rate_display(self, obj):
        rate = obj.success_rate
        if rate is not None:
            rate_float = float(rate)  # Cast to float before formatting
            if rate_float >= 90:
                color = 'green'
            elif rate_float >= 70:
                color = 'orange'
            else:
                color = 'red'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
                color, rate_float
            )
        return '-'
    success_rate_display.short_description = 'Success Rate'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(IntegrationSource)
class IntegrationSourceAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'dealer', 'api_url', 'auth_type', 
        'is_active', 'sync_frequency', 'last_sync', 'created_at'
    ]
    list_filter = ['auth_type', 'is_active', 'created_at', 'last_sync']
    search_fields = ['name', 'dealer__email', 'api_url']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('dealer', 'name', 'api_url')
        }),
        ('Authentication', {
            'fields': ('auth_type', 'api_key')
        }),
        ('Configuration', {
            'fields': ('is_active', 'sync_frequency', 'last_sync')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('dealer')
