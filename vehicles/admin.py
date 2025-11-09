from django.contrib import admin
from .models import (
    Brand, VehicleModel, VehicleCategory, VehicleSpecification, 
    VehicleFeature, VehicleSpecificationFeature,
    # Taxonomy models
    VehicleMake, VehicleModelTaxonomy, VehicleVariant, PartCategory
)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'country_of_origin', 'founded_year', 'is_active')
    list_filter = ('is_active', 'country_of_origin')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(VehicleModel)
class VehicleModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'is_active')
    list_filter = ('brand', 'is_active')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(VehicleCategory)
class VehicleCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(VehicleSpecification)
class VehicleSpecificationAdmin(admin.ModelAdmin):
    list_display = ('model', 'year', 'engine_type', 'transmission', 'fuel_type')
    list_filter = ('year', 'engine_type', 'transmission', 'fuel_type')
    search_fields = ('model__name', 'engine_type')


@admin.register(VehicleFeature)
class VehicleFeatureAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    list_filter = ('category',)
    search_fields = ('name', 'description')


@admin.register(VehicleSpecificationFeature)
class VehicleSpecificationFeatureAdmin(admin.ModelAdmin):
    list_display = ('specification', 'feature', 'is_standard')
    list_filter = ('is_standard', 'feature__category')
    search_fields = ('specification__model__name', 'feature__name')


# ============================================================================
# VEHICLE TAXONOMY ADMIN INTERFACES
# ============================================================================

class VehicleModelTaxonomyInline(admin.TabularInline):
    model = VehicleModelTaxonomy
    extra = 0
    fields = ('name', 'model_code', 'is_active')
    show_change_link = True


@admin.register(VehicleMake)
class VehicleMakeAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_arabic', 'get_models_count', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'name_arabic')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    inlines = [VehicleModelTaxonomyInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'name_arabic', 'slug', 'logo')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_models_count(self, obj):
        return obj.get_models_count()
    get_models_count.short_description = 'Models Count'


class VehicleVariantInline(admin.TabularInline):
    model = VehicleVariant
    extra = 0
    fields = ('name', 'year', 'engine_code', 'transmission_type', 'fuel_type', 'is_active')
    show_change_link = True


@admin.register(VehicleModelTaxonomy)
class VehicleModelTaxonomyAdmin(admin.ModelAdmin):
    list_display = ('name', 'make', 'model_code', 'get_variants_count', 'is_active', 'created_at')
    list_filter = ('make', 'is_active', 'created_at')
    search_fields = ('name', 'model_code', 'make__name')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    inlines = [VehicleVariantInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('make', 'name', 'model_code', 'slug')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_variants_count(self, obj):
        return obj.get_variants_count()
    get_variants_count.short_description = 'Variants Count'


@admin.register(VehicleVariant)
class VehicleVariantAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_make', 'get_model', 'year', 'engine_code', 'transmission_type', 'fuel_type', 'is_active')
    list_filter = ('model__make', 'year', 'transmission_type', 'fuel_type', 'is_active')
    search_fields = ('name', 'model__name', 'model__make__name', 'engine_code')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Vehicle Information', {
            'fields': ('model', 'name', 'year', 'slug')
        }),
        ('Engine & Transmission', {
            'fields': ('engine_code', 'engine_displacement', 'transmission_type', 'fuel_type')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_make(self, obj):
        return obj.model.make.name
    get_make.short_description = 'Make'
    get_make.admin_order_field = 'model__make__name'

    def get_model(self, obj):
        return obj.model.name
    get_model.short_description = 'Model'
    get_model.admin_order_field = 'model__name'


class PartCategoryInline(admin.TabularInline):
    model = PartCategory
    extra = 0
    fields = ('name', 'name_arabic', 'sort_order', 'is_active')
    show_change_link = True


@admin.register(PartCategory)
class PartCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_arabic', 'parent', 'get_level', 'sort_order', 'is_active', 'created_at')
    list_filter = ('parent', 'is_active', 'created_at')
    search_fields = ('name', 'name_arabic', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    inlines = [PartCategoryInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'name_arabic', 'slug', 'parent')
        }),
        ('Display', {
            'fields': ('description', 'icon', 'sort_order')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_level(self, obj):
        return obj.get_level()
    get_level.short_description = 'Level'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('parent')
