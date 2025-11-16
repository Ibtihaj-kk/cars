from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.generic import (
    ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView, FormView
)
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseServerError
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Count, Sum, Avg, F, Prefetch, Value, IntegerField
from django.db import transaction
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
import json
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError
from decimal import Decimal

from .models import (
    Part, Category, Brand, Inventory, Order, OrderItem, Review, BulkUploadLog, 
    IntegrationSource, Cart, CartItem, DiscountCode, OrderDiscount, SaudiCity, 
    CityArea, ShippingRate, OrderShipping, OrderStatusHistory
)
from vehicles.models import VehicleMake, VehicleModelTaxonomy, VehicleVariant
from .cache import (
    get_cached_categories, get_cached_brands, get_cached_popular_parts, 
    get_cached_featured_parts, invalidate_part_cache
)
from .forms import (
    PartForm, PartSearchForm, VendorPartSearchForm, AdminPartSearchForm, 
    CategoryForm, BrandForm, InventoryForm, CSVUploadForm
)
from users.models import User, UserRole


# Permission Mixins and Decorators
class DealerAdminRequiredMixin(UserPassesTestMixin):
    """Mixin to ensure only dealers (sellers) and admins can access the view."""
    
    def test_func(self):
        user = self.request.user
        return (
            user.is_authenticated and 
            (user.role in [UserRole.SELLER, UserRole.ADMIN] or user.is_staff or user.is_superuser)
        )
    
    def handle_no_permission(self):
        messages.error(self.request, "You don't have permission to access this page.")
        return redirect('parts:part_list')


class OwnerOrAdminRequiredMixin(UserPassesTestMixin):
    """Mixin to ensure only the owner of the part or admin can modify it."""
    
    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        
        # Admin and staff can access everything
        if user.role == UserRole.ADMIN or user.is_staff or user.is_superuser:
            return True
        
        # Dealers can only access their own parts
        if user.role == UserRole.SELLER:
            part = self.get_object()
            return part.dealer == user
        
        return False
    
    def handle_no_permission(self):
        messages.error(self.request, "You can only manage your own parts.")
        return redirect('parts:dealer_dashboard')


def dealer_admin_required(view_func):
    """Decorator for function-based views requiring dealer or admin access."""
    def check_permissions(user):
        return (
            user.is_authenticated and 
            (user.role in [UserRole.SELLER, UserRole.ADMIN] or user.is_staff or user.is_superuser)
        )
    
    return user_passes_test(check_permissions)(login_required(view_func))


# Public Views
class PartListView(ListView):
    """Public view to list all active parts with search and filtering, including vendor parts."""
    model = Part
    template_name = 'parts/part_list.html'
    context_object_name = 'parts'
    paginate_by = 12
    
    def get_queryset(self):
        """Get optimized queryset with select_related and prefetch_related for performance."""
        from business_partners.models import BusinessPartner, VendorProfile
        
        queryset = Part.objects.filter(is_active=True).select_related(
            'category', 'brand', 'dealer', 'inventory', 'vendor'
        ).prefetch_related(
            Prefetch('reviews', queryset=Review.objects.select_related('user')),
            'cart_items',
            Prefetch('vendor__vendor_profile', queryset=VendorProfile.objects.all())
        ).annotate(
            # Pre-calculate aggregated fields to avoid N+1 queries
            annotated_review_count=Count('reviews', filter=Q(reviews__is_approved=True)),
            avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True)),
            total_sales=Count('order_items'),
            vendor_rating=F('vendor__vendor_profile__vendor_rating')
        )
        
        # Enhanced search functionality including vendor names
        search_query = self.request.GET.get('search')
        if search_query:
            # Check for vendor prefix search (e.g., "vendor:Zeeshan Motors")
            if search_query.startswith('vendor:'):
                vendor_name = search_query[7:].strip()
                queryset = queryset.filter(vendor__name__icontains=vendor_name)
            else:
                queryset = queryset.filter(
                    Q(name__icontains=search_query) |
                    Q(description__icontains=search_query) |
                    Q(sku__icontains=search_query) |
                    Q(brand__name__icontains=search_query) |
                    Q(parts_number__icontains=search_query) |
                    Q(material_description__icontains=search_query) |
                    Q(manufacturer_part_number__icontains=search_query) |
                    Q(vendor__name__icontains=search_query)  # Include vendor names in search
                )
        
        # Separate SKU filter
        sku_query = self.request.GET.get('sku', '').strip()
        if sku_query:
            queryset = queryset.filter(sku__icontains=sku_query)

        # Separate parts number filter
        parts_number_query = self.request.GET.get('parts_number', '').strip()
        if parts_number_query:
            queryset = queryset.filter(parts_number__icontains=parts_number_query)
        
        # Category filter (single from dropdown)
        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Multiple categories filter (from sidebar checkboxes)
        categories = self.request.GET.getlist('categories')
        if categories:
            queryset = queryset.filter(category_id__in=categories)
        
        # Brand filter (single from dropdown)
        brand_id = self.request.GET.get('brand')
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)
        
        # Multiple brands filter (from sidebar checkboxes)
        brands = self.request.GET.getlist('brands')
        if brands:
            queryset = queryset.filter(brand_id__in=brands)
        
        # Price range filter
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        # Enhanced stock filter
        stock_filter = self.request.GET.get('stock_availability')
        if stock_filter == 'in_stock':
            queryset = queryset.filter(quantity__gt=0)
        elif stock_filter == 'pre_order':
            # Assuming pre-order is when quantity is 0 but part is still active
            queryset = queryset.filter(quantity=0, is_active=True)
        
        # Legacy stock filters for backward compatibility
        in_stock = self.request.GET.get('in_stock')
        if in_stock == 'true':
            queryset = queryset.filter(quantity__gt=0)
        
        # Low stock filter
        low_stock = self.request.GET.get('low_stock')
        if low_stock == 'true':
            queryset = queryset.filter(quantity__lte=10, quantity__gt=0)
        
        # Featured filter
        featured = self.request.GET.get('featured')
        if featured == 'true':
            queryset = queryset.filter(is_featured=True)
        
        # Minimum rating filter using pre-calculated annotation
        min_rating = self.request.GET.get('min_rating')
        if min_rating:
            queryset = queryset.filter(avg_rating__gte=min_rating)
        
        # NEW VENDOR FILTERS
        # Vendor type filter
        vendor_filter = self.request.GET.get('vendor_type')
        if vendor_filter == 'verified':
            # Assuming verified vendors have a specific status or field
            queryset = queryset.filter(vendor__vendor_profile__isnull=False)
        elif vendor_filter == 'top_rated':
            queryset = queryset.filter(vendor__vendor_profile__vendor_rating__gte=4.0)
        
        # Vendor rating filter
        vendor_min_rating = self.request.GET.get('vendor_min_rating')
        if vendor_min_rating:
            queryset = queryset.filter(vendor__vendor_profile__vendor_rating__gte=vendor_min_rating)
        
        # ==================== NEW MATERIAL-RELATED FILTERS ====================
        
        # Material Type filter
        material_types = self.request.GET.getlist('material_types')
        if material_types:
            queryset = queryset.filter(material_type__in=material_types)
        
        # Plant filter
        plants = self.request.GET.getlist('plants')
        if plants:
            queryset = queryset.filter(plant__in=plants)
        
        # Storage Location filter
        storage_locations = self.request.GET.getlist('storage_locations')
        if storage_locations:
            queryset = queryset.filter(storage_location__in=storage_locations)
        
        # Material Group filter
        material_groups = self.request.GET.getlist('material_groups')
        if material_groups:
            queryset = queryset.filter(material_group__in=material_groups)
        
        # Division filter
        divisions = self.request.GET.getlist('divisions')
        if divisions:
            queryset = queryset.filter(division__in=divisions)
        
        # ABC Indicator filter
        abc_indicators = self.request.GET.getlist('abc_indicators')
        if abc_indicators:
            queryset = queryset.filter(abc_indicator__in=abc_indicators)
        
        # Procurement Type filter
        procurement_types = self.request.GET.getlist('procurement_types')
        if procurement_types:
            queryset = queryset.filter(procurement_type__in=procurement_types)
        
        # Industry Sector filter
        industry_sectors = self.request.GET.getlist('industry_sectors')
        if industry_sectors:
            queryset = queryset.filter(industry_sector__in=industry_sectors)
        
        # Valuation Class filter
        valuation_classes = self.request.GET.getlist('valuation_classes')
        if valuation_classes:
            queryset = queryset.filter(valuation_class__in=valuation_classes)
        
        # Weight range filter
        min_weight = self.request.GET.get('min_weight')
        max_weight = self.request.GET.get('max_weight')
        if min_weight:
            queryset = queryset.filter(gross_weight__gte=min_weight)
        if max_weight:
            queryset = queryset.filter(gross_weight__lte=max_weight)
        
        # ==================== VEHICLE COMPATIBILITY FILTERS ====================
        
        # Vehicle Make filter
        vehicle_makes = self.request.GET.getlist('vehicle_make')
        if vehicle_makes:
            queryset = queryset.filter(vehicle_variants__model__make_id__in=vehicle_makes).distinct()
        
        # Vehicle Model filter
        vehicle_models = self.request.GET.getlist('vehicle_model')
        if vehicle_models:
            queryset = queryset.filter(vehicle_variants__model_id__in=vehicle_models).distinct()
        
        # Vehicle Variant filter
        vehicle_variants = self.request.GET.getlist('vehicle_variant')
        if vehicle_variants:
            queryset = queryset.filter(vehicle_variants__id__in=vehicle_variants).distinct()
        
        # Sorting
        sort_by = self.request.GET.get('sort', '-created_at')
        if sort_by in ['name', '-name', 'price', '-price', 'created_at', '-created_at', 'vendor_rating', '-vendor_rating']:
            queryset = queryset.order_by(sort_by)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        from business_partners.models import BusinessPartner
        
        context = super().get_context_data(**kwargs)
        context['search_form'] = PartSearchForm(self.request.GET)
        # Use cached data for better performance
        context['categories'] = get_cached_categories()
        context['brands'] = get_cached_brands()
        context['popular_parts'] = get_cached_popular_parts(limit=6)
        context['featured_parts'] = get_cached_featured_parts(limit=4)
        
        # Add vendor-related context
        context['vendors'] = BusinessPartner.objects.filter(
            roles__role_type='vendor',
            status='active'
        ).select_related('vendor_profile').order_by('name')
        
        # ==================== NEW MATERIAL-RELATED FILTER OPTIONS ====================
        
        # Get distinct values for filter dropdowns from active parts
        active_parts = Part.objects.filter(is_active=True)
        
        # Material Types with counts
        material_type_counts = active_parts.exclude(
            material_type__isnull=True
        ).exclude(material_type='').values('material_type').annotate(
            count=Count('id')
        ).order_by('material_type')
        context['material_types'] = material_type_counts
        
        # Plants with counts
        plant_counts = active_parts.exclude(
            plant__isnull=True
        ).exclude(plant='').values('plant').annotate(
            count=Count('id')
        ).order_by('plant')
        context['plants'] = plant_counts
        
        # Storage Locations with counts
        storage_location_counts = active_parts.exclude(
            storage_location__isnull=True
        ).exclude(storage_location='').values('storage_location').annotate(
            count=Count('id')
        ).order_by('storage_location')
        context['storage_locations'] = storage_location_counts
        
        # Material Groups with counts
        material_group_counts = active_parts.exclude(
            material_group__isnull=True
        ).exclude(material_group='').values('material_group').annotate(
            count=Count('id')
        ).order_by('material_group')
        context['material_groups'] = material_group_counts
        
        # Divisions with counts
        division_counts = active_parts.exclude(
            division__isnull=True
        ).exclude(division='').values('division').annotate(
            count=Count('id')
        ).order_by('division')
        context['divisions'] = division_counts
        
        # ABC Indicators with counts
        abc_indicator_counts = active_parts.exclude(
            abc_indicator__isnull=True
        ).exclude(abc_indicator='').values('abc_indicator').annotate(
            count=Count('id')
        ).order_by('abc_indicator')
        context['abc_indicators'] = abc_indicator_counts
        
        # Vehicle Makes with counts (only if vehicle variants exist)
        if VehicleVariant.objects.exists():
            vehicle_make_counts = VehicleMake.objects.filter(
                is_active=True
            ).annotate(
                count=Count('taxonomy_models__variants__parts', distinct=True)
            ).filter(count__gt=0).order_by('name')
        else:
            vehicle_make_counts = VehicleMake.objects.filter(is_active=True).annotate(count=Value(0, output_field=IntegerField()))
        context['vehicle_makes'] = vehicle_make_counts
        
        # Vehicle Models with counts (only if vehicle variants exist)
        if VehicleVariant.objects.exists():
            vehicle_model_counts = VehicleModelTaxonomy.objects.filter(
                make__is_active=True
            ).annotate(
                count=Count('variants__parts', distinct=True)
            ).filter(count__gt=0).order_by('make__name', 'name')
        else:
            vehicle_model_counts = VehicleModelTaxonomy.objects.filter(make__is_active=True).annotate(count=Value(0, output_field=IntegerField()))
        context['vehicle_models'] = vehicle_model_counts
        
        # Vehicle Variants with counts (only if vehicle variants exist)
        if VehicleVariant.objects.exists():
            vehicle_variant_counts = VehicleVariant.objects.filter(
                model__make__is_active=True
            ).annotate(
                count=Count('parts', distinct=True)
            ).filter(count__gt=0).order_by('model__make__name', 'model__name', 'name')
        else:
            vehicle_variant_counts = VehicleVariant.objects.none()
        context['vehicle_variants'] = vehicle_variant_counts
        
        # Procurement Types
        context['procurement_types'] = active_parts.exclude(
            procurement_type__isnull=True
        ).exclude(procurement_type='').values_list(
            'procurement_type', flat=True
        ).distinct().order_by('procurement_type')
        
        # Industry Sectors
        context['industry_sectors'] = active_parts.exclude(
            industry_sector__isnull=True
        ).exclude(industry_sector='').values_list(
            'industry_sector', flat=True
        ).distinct().order_by('industry_sector')
        
        # Valuation Classes
        context['valuation_classes'] = active_parts.exclude(
            valuation_class__isnull=True
        ).exclude(valuation_class='').values_list(
            'valuation_class', flat=True
        ).distinct().order_by('valuation_class')
        
        return context


@require_http_methods(["POST"])
@login_required
def part_activate(request, pk):
    """Activate a part (HTMX endpoint)."""
    try:
        part = get_object_or_404(Part, pk=pk)
        
        # Check permissions
        if not (request.user.is_staff or part.dealer == request.user):
            return HttpResponseForbidden("You don't have permission to activate this part.")
        
        part.is_active = True
        part.save()
        
        # Return updated parts list
        return redirect('parts:admin_parts_search')
        
    except Exception as e:
        return HttpResponseServerError(f"Error activating part: {str(e)}")


@require_http_methods(["POST"])
@login_required
def part_deactivate(request, pk):
    """Deactivate a part (HTMX endpoint)."""
    try:
        part = get_object_or_404(Part, pk=pk)
        
        # Check permissions
        if not (request.user.is_staff or part.dealer == request.user):
            return HttpResponseForbidden("You don't have permission to deactivate this part.")
        
        part.is_active = False
        part.save()
        
        # Return updated parts list
        return redirect('parts:admin_parts_search')
        
    except Exception as e:
        return HttpResponseServerError(f"Error deactivating part: {str(e)}")


# ==================== ROLE-BASED PARTS SEARCH AND FILTERING VIEWS ====================

class UserPartsListView(ListView):
    """
    Enhanced parts list view for regular users with role-based field visibility.
    Shows only user-visible fields (dark green fields from Excel).
    """
    model = Part
    template_name = 'parts/user_parts_list.html'
    context_object_name = 'parts'
    paginate_by = 12
    
    def get_queryset(self):
        """Get filtered queryset for user view with only user-visible fields."""
        queryset = Part.objects.filter(is_active=True).select_related(
            'category', 'brand'
        ).prefetch_related(
            Prefetch('reviews', queryset=Review.objects.select_related('user')),
            'inventory'
        ).annotate(
            annotated_review_count=Count('reviews', filter=Q(reviews__is_approved=True)),
            avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True))
        )
        
        # Apply search and filters
        form = PartSearchForm(self.request.GET, user=self.request.user)
        if form.is_valid():
            # Search query
            query = form.cleaned_data.get('query')
            if query:
                queryset = queryset.filter(
                    Q(parts_number__icontains=query) |
                    Q(material_description__icontains=query) |
                    Q(material_description_ar__icontains=query) |
                    Q(manufacturer_part_number__icontains=query) |
                    Q(manufacturer_oem_number__icontains=query) |
                    Q(name__icontains=query) |  # Legacy field
                    Q(description__icontains=query)  # Legacy field
                )
            
            # Category filter
            category = form.cleaned_data.get('category')
            if category:
                queryset = queryset.filter(category=category)
            
            # Brand filter
            brand = form.cleaned_data.get('brand')
            if brand:
                queryset = queryset.filter(brand=brand)
            
            # Price range
            min_price = form.cleaned_data.get('min_price')
            max_price = form.cleaned_data.get('max_price')
            if min_price:
                queryset = queryset.filter(price__gte=min_price)
            if max_price:
                queryset = queryset.filter(price__lte=max_price)
            
            # Stock filter
            in_stock_only = form.cleaned_data.get('in_stock_only')
            if in_stock_only:
                queryset = queryset.filter(inventory__stock__gt=0)
            
            # Vehicle compatibility filters (placeholder for future implementation)
            vehicle_make = form.cleaned_data.get('vehicle_make')
            vehicle_model = form.cleaned_data.get('vehicle_model')
            # TODO: Implement vehicle compatibility filtering when compatibility models are created
        
        # Default sorting
        sort_by = self.request.GET.get('sort', '-created_at')
        if sort_by in ['parts_number', '-parts_number', 'price', '-price', 'created_at', '-created_at']:
            queryset = queryset.order_by(sort_by)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = PartSearchForm(self.request.GET, user=self.request.user)
        context['view_type'] = 'user'
        context['categories'] = get_cached_categories()
        context['brands'] = get_cached_brands()
        return context


class VendorPartsListView(DealerAdminRequiredMixin, ListView):
    """
    Enhanced parts list view for vendors with additional filters and all field access.
    Shows vendor/admin fields for their own parts.
    """
    model = Part
    template_name = 'parts/vendor_parts_list.html'
    context_object_name = 'parts'
    paginate_by = 20
    
    def get_queryset(self):
        """Get filtered queryset for vendor view with vendor-specific filters."""
        # Vendors see their own parts plus any public parts
        queryset = Part.objects.filter(
            Q(dealer=self.request.user) | Q(is_active=True)
        ).select_related(
            'category', 'brand', 'dealer'
        ).prefetch_related(
            'inventory'
        ).annotate(
            stock_level=F('inventory__stock'),
            reorder_level=F('inventory__reorder_level')
        )
        
        # Apply search and filters
        form = VendorPartSearchForm(self.request.GET, user=self.request.user)
        if form.is_valid():
            # Basic search filters (inherited from PartSearchForm)
            query = form.cleaned_data.get('query')
            if query:
                queryset = queryset.filter(
                    Q(parts_number__icontains=query) |
                    Q(material_description__icontains=query) |
                    Q(material_description_ar__icontains=query) |
                    Q(manufacturer_part_number__icontains=query) |
                    Q(manufacturer_oem_number__icontains=query) |
                    Q(material_type__icontains=query) |  # Vendor-visible field
                    Q(name__icontains=query) |
                    Q(description__icontains=query)
                )
            
            # Category and brand filters
            category = form.cleaned_data.get('category')
            if category:
                queryset = queryset.filter(category=category)
            
            brand = form.cleaned_data.get('brand')
            if brand:
                queryset = queryset.filter(brand=brand)
            
            # Price range
            min_price = form.cleaned_data.get('min_price')
            max_price = form.cleaned_data.get('max_price')
            if min_price:
                queryset = queryset.filter(price__gte=min_price)
            if max_price:
                queryset = queryset.filter(price__lte=max_price)
            
            # Stock filters
            in_stock_only = form.cleaned_data.get('in_stock_only')
            if in_stock_only:
                queryset = queryset.filter(inventory__stock__gt=0)
            
            low_stock_only = form.cleaned_data.get('low_stock_only')
            if low_stock_only:
                queryset = queryset.filter(
                    inventory__stock__lte=F('inventory__reorder_level'),
                    inventory__stock__gt=0
                )
            
            # Status filter
            status = form.cleaned_data.get('status')
            if status == 'active':
                queryset = queryset.filter(is_active=True)
            elif status == 'inactive':
                queryset = queryset.filter(is_active=False)
            elif status == 'featured':
                queryset = queryset.filter(is_featured=True)
            elif status == 'out_of_stock':
                queryset = queryset.filter(inventory__stock=0)
            
            # Profitability filter (based on margin calculation)
            profitability = form.cleaned_data.get('profitability')
            if profitability:
                # Calculate margin: (price - moving_average_price) / price * 100
                if profitability == 'high':
                    queryset = queryset.filter(
                        price__gt=F('moving_average_price') * 1.3  # >30% margin
                    )
                elif profitability == 'medium':
                    queryset = queryset.filter(
                        price__gt=F('moving_average_price') * 1.15,  # 15-30% margin
                        price__lte=F('moving_average_price') * 1.3
                    )
                elif profitability == 'low':
                    queryset = queryset.filter(
                        price__lte=F('moving_average_price') * 1.15  # <15% margin
                    )
            
            # Material type filter
            material_type = form.cleaned_data.get('material_type')
            if material_type:
                queryset = queryset.filter(material_type__icontains=material_type)
        
        # Default sorting
        sort_by = self.request.GET.get('sort', '-created_at')
        if sort_by in ['parts_number', '-parts_number', 'price', '-price', 
                       'created_at', '-created_at', 'stock_level', '-stock_level']:
            queryset = queryset.order_by(sort_by)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = VendorPartSearchForm(self.request.GET, user=self.request.user)
        context['view_type'] = 'vendor'
        context['categories'] = get_cached_categories()
        context['brands'] = get_cached_brands()
        return context


class AdminPartsListView(UserPassesTestMixin, ListView):
    """
    Enhanced parts list view for administrators with global management capabilities.
    Shows all fields for all vendors with advanced filtering.
    """
    model = Part
    template_name = 'parts/admin_parts_list.html'
    context_object_name = 'parts'
    paginate_by = 25
    
    def test_func(self):
        """Only allow admin users."""
        return (self.request.user.is_authenticated and 
                (self.request.user.is_staff or self.request.user.is_superuser))
    
    def get_queryset(self):
        """Get filtered queryset for admin view with global access."""
        queryset = Part.objects.all().select_related(
            'category', 'brand', 'dealer'
        ).prefetch_related(
            'inventory'
        ).annotate(
            stock_level=F('inventory__stock'),
            reorder_level=F('inventory__reorder_level'),
            dealer_name=F('dealer__email')
        )
        
        # Apply search and filters
        form = AdminPartSearchForm(self.request.GET, user=self.request.user)
        if form.is_valid():
            # Basic search filters
            query = form.cleaned_data.get('query')
            if query:
                queryset = queryset.filter(
                    Q(parts_number__icontains=query) |
                    Q(material_description__icontains=query) |
                    Q(material_description_ar__icontains=query) |
                    Q(manufacturer_part_number__icontains=query) |
                    Q(manufacturer_oem_number__icontains=query) |
                    Q(material_type__icontains=query) |
                    Q(plant__icontains=query) |
                    Q(name__icontains=query) |
                    Q(description__icontains=query)
                )
            
            # Category and brand filters
            category = form.cleaned_data.get('category')
            if category:
                queryset = queryset.filter(category=category)
            
            brand = form.cleaned_data.get('brand')
            if brand:
                queryset = queryset.filter(brand=brand)
            
            # Dealer filter
            dealer = form.cleaned_data.get('dealer')
            if dealer:
                queryset = queryset.filter(dealer=dealer)
            
            # Price range
            min_price = form.cleaned_data.get('min_price')
            max_price = form.cleaned_data.get('max_price')
            if min_price:
                queryset = queryset.filter(price__gte=min_price)
            if max_price:
                queryset = queryset.filter(price__lte=max_price)
            
            # Stock filters
            in_stock_only = form.cleaned_data.get('in_stock_only')
            if in_stock_only:
                queryset = queryset.filter(inventory__stock__gt=0)
            
            low_stock_only = form.cleaned_data.get('low_stock_only')
            if low_stock_only:
                queryset = queryset.filter(
                    inventory__stock__lte=F('inventory__reorder_level'),
                    inventory__stock__gt=0
                )
            
            # Status filter
            status = form.cleaned_data.get('status')
            if status == 'active':
                queryset = queryset.filter(is_active=True)
            elif status == 'inactive':
                queryset = queryset.filter(is_active=False)
            elif status == 'featured':
                queryset = queryset.filter(is_featured=True)
            elif status == 'out_of_stock':
                queryset = queryset.filter(inventory__stock=0)
            
            # ABC indicator filter
            abc_indicator = form.cleaned_data.get('abc_indicator')
            if abc_indicator:
                queryset = queryset.filter(abc_indicator=abc_indicator)
            
            # Plant filter
            plant = form.cleaned_data.get('plant')
            if plant:
                queryset = queryset.filter(plant__icontains=plant)
            
            # Material type filter
            material_type = form.cleaned_data.get('material_type')
            if material_type:
                queryset = queryset.filter(material_type__icontains=material_type)
        
        # Default sorting
        sort_by = self.request.GET.get('sort', '-created_at')
        if sort_by in ['parts_number', '-parts_number', 'price', '-price', 
                       'created_at', '-created_at', 'stock_level', '-stock_level',
                       'dealer_name', '-dealer_name']:
            queryset = queryset.order_by(sort_by)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = AdminPartSearchForm(self.request.GET, user=self.request.user)
        context['view_type'] = 'admin'
        context['categories'] = get_cached_categories()
        context['brands'] = get_cached_brands()
        return context


# ==================== HTMX PARTIAL VIEWS ====================

def parts_results_partial(request):
    """
    HTMX partial view for dynamic parts results based on user role.
    Returns appropriate template fragment based on user permissions.
    """
    user = request.user
    
    # Determine user role and redirect to appropriate view
    if user.is_authenticated and (user.is_staff or user.is_superuser):
        # Admin view
        view = AdminPartsListView.as_view()
        template_name = 'parts/partials/admin_parts_grid.html'
    elif user.is_authenticated and hasattr(user, 'role') and user.role in [UserRole.SELLER]:
        # Vendor view
        view = VendorPartsListView.as_view()
        template_name = 'parts/partials/vendor_parts_table.html'
    else:
        # User view
        view = UserPartsListView.as_view()
        template_name = 'parts/partials/user_parts_grid.html'
    
    # Get the response from the appropriate view
    response = view(request)
    
    # If it's an HTMX request, return just the partial template
    if request.headers.get('HX-Request'):
        context = response.context_data
        context['is_htmx'] = True
        return render(request, template_name, context)
    
    return response


def vehicle_models_partial(request):
    """
    HTMX partial view for dynamic vehicle model loading based on selected make.
    """
    make_id = request.GET.get('vehicle_make')
    
    if make_id:
        try:
            from vehicles.models import VehicleModelTaxonomy
            models = VehicleModelTaxonomy.objects.filter(
                make_id=make_id, is_active=True
            ).order_by('name')
        except ImportError:
            models = []
    else:
        models = []
    
    return render(request, 'parts/partials/vehicle_models_options.html', {
        'models': models
    })


# API ViewSets
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from .serializers import PartUserSerializer, PartVendorAdminSerializer

class PartViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API ViewSet for Parts with field visibility based on user permissions.
    """
    queryset = Part.objects.filter(is_active=True)
    permission_classes = [permissions.AllowAny]  # For testing purposes
    
    def get_serializer_class(self):
        """Return appropriate serializer based on user permissions."""
        user = self.request.user
        
        # Check if user is admin/vendor
        if (user.is_authenticated and 
            (user.is_staff or user.is_superuser or 
             getattr(user, 'role', None) in [UserRole.ADMIN, UserRole.SELLER])):
            return PartVendorAdminSerializer
        else:
            return PartUserSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = super().get_queryset()
        user = self.request.user
        
        # If user is a dealer, show only their parts plus public parts
        if (user.is_authenticated and 
            getattr(user, 'role', None) == UserRole.SELLER):
            queryset = queryset.filter(
                models.Q(dealer=user) | models.Q(dealer__isnull=True)
            )
        
        return queryset


@require_POST
def buy_now(request):
    """Handle immediate order creation for Buy Now functionality."""
    import json
    from django.db import transaction
    from django.urls import reverse
    from django.http import JsonResponse
    from django.shortcuts import get_object_or_404
    from decimal import Decimal
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Parse request data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        part_id = data.get('part_id')
        qty = int(data.get('qty', 1))
        
        logger.info(f"Buy now request received: part_id={part_id}, qty={qty}, user={request.user}")
        
        if not part_id:
            logger.warning("Buy now failed: Part ID is required")
            return JsonResponse({'error': 'Part ID is required'}, status=400)
        
        if qty < 1:
            logger.warning(f"Buy now failed: Invalid quantity {qty}")
            return JsonResponse({'error': 'Quantity must be at least 1'}, status=400)
        
        with transaction.atomic():
            # Get the part and check if it's active
            part = get_object_or_404(Part, pk=part_id, is_active=True)
            
            # Check stock availability
            if part.quantity < qty:
                logger.warning(f"Buy now failed: Insufficient stock for part {part_id}. Available: {part.quantity}, Requested: {qty}")
                return JsonResponse({
                    'error': f'Insufficient stock. Only {part.quantity} items available.'
                }, status=400)
            
            # Calculate total price
            item_total = part.price * qty
            shipping_cost = Decimal('0.00')  # You can implement shipping calculation logic here
            tax_amount = Decimal('0.00')    # You can implement tax calculation logic here
            total_price = item_total + shipping_cost + tax_amount
            
            # Create order
            order_data = {
                'total_price': total_price,
                'shipping_cost': shipping_cost,
                'tax_amount': tax_amount,
                'status': 'pending',
                'payment_method': None,  # Will be set during checkout
                'payment_status': 'pending',
                'notes': f'Buy Now order for {part.name}'
            }
            
            # Set customer or guest information
            if request.user.is_authenticated:
                order_data['customer'] = request.user
            else:
                # For guest orders, you might want to collect this info in the frontend
                # For now, we'll create a minimal guest order
                order_data['guest_name'] = 'Guest Customer'
                order_data['guest_email'] = data.get('guest_email', '')
                order_data['guest_phone'] = data.get('guest_phone', '')
                order_data['guest_address'] = data.get('guest_address', '')
            
            # Create the order
            order = Order.objects.create(**order_data)
            logger.info(f"Created buy now order: order_id={order.id}, order_number={order.order_number}")
            
            # Create order item
            OrderItem.objects.create(
                order=order,
                part=part,
                quantity=qty,
                price=part.price
            )
            
            # Reserve stock (decrement quantity)
            part.quantity -= qty
            part.save(update_fields=['quantity'])
            
            # Optionally add to user's cart for consistency (but don't duplicate if already there)
            if request.user.is_authenticated:
                try:
                    cart = Cart.objects.get(user=request.user)
                    cart_item, created = CartItem.objects.get_or_create(
                        cart=cart,
                        part=part,
                        defaults={'quantity': qty}
                    )
                    if not created:
                        # If item already exists, update quantity
                        cart_item.quantity += qty
                        cart_item.save()
                except Cart.DoesNotExist:
                    # If user doesn't have a cart, create one
                    cart = Cart.objects.create(user=request.user)
                    CartItem.objects.create(cart=cart, part=part, quantity=qty)
            
            # Generate checkout URL
            checkout_url = reverse('parts:checkout_step1') + f'?order_id={order.id}'
            
            logger.info(f"Buy now successful: order_id={order.id}, order_number={order.order_number}, checkout_url={checkout_url}")
            
            return JsonResponse({
                'success': True,
                'order_id': order.id,
                'order_number': order.order_number,
                'checkout_url': checkout_url,
                'message': f'Order {order.order_number} created successfully!'
            })
            
    except ValueError as e:
        logger.error(f"Buy now failed: Invalid data error - {str(e)}")
        return JsonResponse({'error': f'Invalid data: {str(e)}'}, status=400)
    except Exception as e:
        logger.error(f"Buy now failed: Unexpected error - {str(e)}", exc_info=True)
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)

    def get_template_names(self):
        # Return partial template for HTMX requests
        if self.request.headers.get('HX-Request'):
            return ['parts/partials/parts_results.html']
        return [self.template_name]


class PartDetailView(DetailView):
    """Public view to display part details."""
    model = Part
    template_name = 'parts/part_detail.html'
    context_object_name = 'part'
    
    def get_queryset(self):
        """Get optimized queryset for part detail view."""
        return Part.objects.filter(is_active=True).select_related(
            'category', 'brand', 'dealer', 'inventory'
        ).prefetch_related(
            Prefetch('reviews', queryset=Review.objects.select_related('user').filter(is_approved=True)),
            'cart_items',
            'order_items'
        )
    
    def get_object(self):
        part = super().get_object()
        # Increment view count
        Part.objects.filter(pk=part.pk).update(view_count=F('view_count') + 1)
        return part
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        part = self.get_object()
        
        # Get reviews
        reviews = part.reviews.filter(is_approved=True).order_by('-created_at')
        context['reviews'] = reviews
        context['average_rating'] = reviews.aggregate(avg_rating=Avg('rating'))['avg_rating']
        context['review_count'] = reviews.count()
        
        # Related parts
        context['related_parts'] = Part.objects.filter(
            category=part.category, is_active=True
        ).exclude(pk=part.pk)[:4]
        
        # Dynamic categories with part counts for Similar Accessories section
        from .models import Category
        categories_with_counts = Category.objects.annotate(
            part_count=Count('parts', filter=Q(parts__is_active=True))
        ).filter(part_count__gt=0).order_by('-part_count')[:20]  # Top 20 categories
        
        context['categories_with_counts'] = categories_with_counts
        
        return context


# Dealer/Admin CRUD Views
class DealerDashboardView(DealerAdminRequiredMixin, TemplateView):
    """Dashboard for dealers and admins with inventory analytics."""
    template_name = 'parts/dealer_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Base queryset - admin sees all, dealers see only their parts
        if user.role == UserRole.ADMIN or user.is_staff or user.is_superuser:
            parts_queryset = Part.objects.all()
            orders_queryset = Order.objects.all()
        else:
            parts_queryset = Part.objects.filter(dealer=user)
            orders_queryset = Order.objects.filter(orderitem__part__dealer=user).distinct()
        
        # Parts analytics
        total_parts = parts_queryset.count()
        active_parts = parts_queryset.filter(is_active=True).count()
        inactive_parts = total_parts - active_parts
        
        # Inventory analytics
        inventories = Inventory.objects.filter(part__in=parts_queryset)
        low_stock_parts = inventories.filter(
            stock__lte=F('reorder_level')
        ).select_related('part')
        
        total_stock_value = parts_queryset.aggregate(
            total_value=Sum(F('price') * F('quantity'))
        )['total_value'] or 0
        
        # Recent orders
        recent_orders = orders_queryset.order_by('-created_at')[:10]
        
        # Monthly sales data (last 6 months)
        six_months_ago = timezone.now() - timedelta(days=180)
        monthly_sales = orders_queryset.filter(
            created_at__gte=six_months_ago
        ).extra(
            select={'month': "DATE_FORMAT(created_at, '%%Y-%%m')"}
        ).values('month').annotate(
            total_sales=Sum('total_price'),
            order_count=Count('id')
        ).order_by('month')
        
        # Top selling parts
        top_parts = parts_queryset.annotate(
            total_sold=Sum('orderitem__quantity')
        ).filter(total_sold__gt=0).order_by('-total_sold')[:5]
        
        context.update({
            'total_parts': total_parts,
            'active_parts': active_parts,
            'inactive_parts': inactive_parts,
            'low_stock_count': low_stock_parts.count(),
            'low_stock_parts': low_stock_parts[:10],
            'total_stock_value': total_stock_value,
            'recent_orders': recent_orders,
            'monthly_sales': list(monthly_sales),
            'top_parts': top_parts,
            'is_admin': user.role == UserRole.ADMIN or user.is_staff or user.is_superuser,
        })
        
        return context


class DealerPartListView(DealerAdminRequiredMixin, ListView):
    """List view for dealer's own parts with management options."""
    model = Part
    template_name = 'parts/dealer_part_list.html'
    context_object_name = 'parts'
    paginate_by = 20
    
    def get_queryset(self):
        """Get optimized queryset for dealer part management."""
        user = self.request.user
        
        # Admin sees all parts, dealers see only their own
        if user.role == UserRole.ADMIN or user.is_staff or user.is_superuser:
            queryset = Part.objects.all()
        else:
            queryset = Part.objects.filter(dealer=user)
        
        queryset = queryset.select_related(
            'category', 'brand', 'inventory', 'dealer'
        ).prefetch_related(
            Prefetch('reviews', queryset=Review.objects.select_related('user')),
            'order_items',
            'cart_items'
        ).annotate(
            # Pre-calculate aggregated fields for dashboard metrics
            annotated_review_count=Count('reviews'),
            avg_rating=Avg('reviews__rating'),
            total_orders=Count('order_items'),
            total_revenue=Sum(F('order_items__quantity') * F('order_items__price'))
        ).order_by('-created_at')
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(sku__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # Status filter
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        elif status == 'low_stock':
            queryset = queryset.filter(
                inventory__stock__lte=F('inventory__reorder_level')
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        return context


class PartCreateView(DealerAdminRequiredMixin, CreateView):
    """Create view for new parts."""
    model = Part
    form_class = PartForm
    template_name = 'parts/part_form.html'
    success_url = reverse_lazy('parts:dealer_part_list')
    
    def form_valid(self, form):
        # Set the dealer to current user if not admin
        if self.request.user.role != UserRole.ADMIN and not self.request.user.is_staff:
            form.instance.dealer = self.request.user
        
        response = super().form_valid(form)
        
        # Create or update inventory record
        with transaction.atomic():
            inventory, created = Inventory.objects.get_or_create(
                part=self.object,
                defaults={
                    'stock': self.object.quantity,
                    'reorder_level': 10,  # Default reorder level
                    'max_stock_level': self.object.quantity * 2,
                    'last_restock_date': timezone.now(),
                }
            )
            if not created:
                inventory.stock = self.object.quantity
                inventory.last_restock_date = timezone.now()
                inventory.save()
        
        messages.success(self.request, f'Part "{self.object.name}" created successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Part'
        context['button_text'] = 'Create Part'
        return context


class PartUpdateView(OwnerOrAdminRequiredMixin, UpdateView):
    """Update view for existing parts."""
    model = Part
    form_class = PartForm
    template_name = 'parts/part_form.html'
    
    def get_success_url(self):
        return reverse('parts:part_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Update inventory record
        with transaction.atomic():
            inventory, created = Inventory.objects.get_or_create(
                part=self.object,
                defaults={
                    'stock': self.object.quantity,
                    'reorder_level': 10,
                    'max_stock_level': self.object.quantity * 2,
                    'last_restock_date': timezone.now(),
                }
            )
            
            # Update stock if quantity changed
            if inventory.stock != self.object.quantity:
                inventory.stock = self.object.quantity
                inventory.last_restock_date = timezone.now()
                inventory.save()
        
        messages.success(self.request, f'Part "{self.object.name}" updated successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit {self.object.name}'
        context['button_text'] = 'Update Part'
        return context


class PartDeleteView(OwnerOrAdminRequiredMixin, DeleteView):
    """Delete view for parts."""
    model = Part
    template_name = 'parts/part_confirm_delete.html'
    success_url = reverse_lazy('parts:dealer_part_list')
    
    def delete(self, request, *args, **kwargs):
        part = self.get_object()
        part_name = part.name
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'Part "{part_name}" deleted successfully!')
        return response


# Inventory Management Views
class InventoryUpdateView(OwnerOrAdminRequiredMixin, UpdateView):
    """Update inventory levels for a part."""
    model = Inventory
    form_class = InventoryForm
    template_name = 'parts/inventory_form.html'
    
    def get_object(self):
        part = get_object_or_404(Part, pk=self.kwargs['part_pk'])
        inventory, created = Inventory.objects.get_or_create(
            part=part,
            defaults={
                'stock': part.quantity,
                'reorder_level': 10,
                'max_stock_level': part.quantity * 2,
                'last_restock_date': timezone.now(),
            }
        )
        return inventory
    
    def get_success_url(self):
        return reverse('parts:part_detail', kwargs={'pk': self.object.part.pk})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Update part quantity to match inventory stock
        with transaction.atomic():
            part = self.object.part
            part.quantity = self.object.stock
            part.save()
        
        messages.success(self.request, 'Inventory updated successfully!')
        return response
    
    def test_func(self):
        # Override to check part ownership instead of inventory ownership
        user = self.request.user
        if not user.is_authenticated:
            return False
        
        if user.role == UserRole.ADMIN or user.is_staff or user.is_superuser:
            return True
        
        if user.role == UserRole.SELLER:
            part = get_object_or_404(Part, pk=self.kwargs['part_pk'])
            return part.dealer == user
        
        return False


# AJAX Views for Dashboard
@dealer_admin_required
def low_stock_alerts_ajax(request):
    """AJAX view to get low stock alerts."""
    user = request.user
    
    if user.role == UserRole.ADMIN or user.is_staff or user.is_superuser:
        inventories = Inventory.objects.filter(
            stock__lte=F('reorder_level')
        ).select_related('part')
    else:
        inventories = Inventory.objects.filter(
            part__dealer=user,
            stock__lte=F('reorder_level')
        ).select_related('part')
    
    alerts = []
    for inventory in inventories:
        alerts.append({
            'part_id': inventory.part.id,
            'part_name': inventory.part.name,
            'current_stock': inventory.stock,
            'reorder_level': inventory.reorder_level,
            'sku': inventory.part.sku,
        })
    
    return JsonResponse({'alerts': alerts})


@dealer_admin_required
def inventory_analytics_ajax(request):
    """AJAX view to get inventory analytics data."""
    user = request.user
    
    if user.role == UserRole.ADMIN or user.is_staff or user.is_superuser:
        parts_queryset = Part.objects.all()
    else:
        parts_queryset = Part.objects.filter(dealer=user)
    
    # Calculate analytics
    total_parts = parts_queryset.count()
    total_stock_value = parts_queryset.aggregate(
        total_value=Sum(F('price') * F('quantity'))
    )['total_value'] or 0
    
    low_stock_count = Inventory.objects.filter(
        part__in=parts_queryset,
        stock__lte=F('reorder_level')
    ).count()
    
    out_of_stock_count = parts_queryset.filter(quantity=0).count()
    
    return JsonResponse({
        'total_parts': total_parts,
        'total_stock_value': float(total_stock_value),
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
    })


class CSVUploadView(DealerAdminRequiredMixin, FormView):
    """View for uploading CSV files to bulk create parts."""
    template_name = 'parts/csv_upload.html'
    form_class = CSVUploadForm
    success_url = reverse_lazy('parts:csv_upload')
    
    def form_valid(self, form):
        """Process the uploaded CSV file using Celery task."""
        from .tasks import process_csv_import
        
        csv_file = form.cleaned_data['csv_file']
        
        # Read file content
        csv_file.seek(0)
        file_content = csv_file.read().decode('utf-8')
        
        # Create bulk upload log
        upload_log = BulkUploadLog.objects.create(
            user=self.request.user,
            import_type='csv',
            source_name=csv_file.name,
            status='queued'
        )
        
        # Start background task
        task = process_csv_import.delay(
            file_content, 
            self.request.user.id, 
            upload_log.id
        )
        
        # Store task ID in session for tracking
        self.request.session['csv_import_task_id'] = task.id
        
        # Add success message
        messages.success(
            self.request,
            'CSV upload has been queued for processing. You will receive an email notification when complete.'
        )
        
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """Handle form validation errors."""
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        """Add upload results to context if available."""
        context = super().get_context_data(**kwargs)
        
        # Get results from session
        results = self.request.session.pop('csv_upload_results', None)
        if results:
            context['upload_results'] = results
        
        return context
    
    def process_csv_file(self, csv_file, skip_duplicates, update_existing):
        """Process the uploaded CSV file and create parts."""
        import csv
        import io
        from decimal import Decimal, InvalidOperation
        from django.db import transaction
        
        # Initialize counters
        success_count = 0
        error_count = 0
        skipped_count = 0
        errors = []
        created_parts = []
        updated_parts = []
        
        # Read CSV content
        csv_file.seek(0)
        file_content = csv_file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(file_content))
        
        # Create bulk upload log
        bulk_log = BulkUploadLog.objects.create(
            uploaded_by=self.request.user,
            file_name=csv_file.name,
            total_rows=0,  # Will be updated later
            success_count=0,
            error_count=0,
            status='processing'
        )
        
        try:
            with transaction.atomic():
                row_number = 1
                for row in csv_reader:
                    row_number += 1
                    
                    try:
                        # Clean and validate row data
                        name = row.get('name', '').strip()
                        category_name = row.get('category', '').strip()
                        brand_name = row.get('brand', '').strip()
                        price_str = row.get('price', '').strip()
                        quantity_str = row.get('quantity', '').strip()
                        sku = row.get('sku', '').strip()
                        description = row.get('description', '').strip()
                        image_url = row.get('image_url', '').strip()
                        
                        # Validate required fields
                        if not all([name, category_name, brand_name, price_str, quantity_str, sku]):
                            errors.append(f'Row {row_number}: Missing required fields')
                            error_count += 1
                            continue
                        
                        # Convert price and quantity
                        try:
                            price = Decimal(price_str)
                            quantity = int(quantity_str)
                        except (ValueError, InvalidOperation):
                            errors.append(f'Row {row_number}: Invalid price or quantity format')
                            error_count += 1
                            continue
                        
                        # Check for duplicates
                        existing_part = Part.objects.filter(
                            models.Q(sku=sku) | models.Q(name=name)
                        ).first()
                        
                        if existing_part:
                            if skip_duplicates and not update_existing:
                                skipped_count += 1
                                continue
                            elif update_existing:
                                # Update existing part
                                existing_part.price = price
                                existing_part.quantity = quantity
                                if description:
                                    existing_part.description = description
                                existing_part.save()
                                updated_parts.append(existing_part.name)
                                success_count += 1
                                continue
                        
                        # Get or create category
                        category, _ = Category.objects.get_or_create(
                            name=category_name,
                            defaults={'description': f'Auto-created category for {category_name}'}
                        )
                        
                        # Get or create brand
                        brand, _ = Brand.objects.get_or_create(
                            name=brand_name,
                            defaults={'description': f'Auto-created brand for {brand_name}'}
                        )
                        
                        # Create new part
                        part = Part.objects.create(
                            name=name,
                            sku=sku,
                            description=description,
                            price=price,
                            quantity=quantity,
                            category=category,
                            brand=brand,
                            created_by=self.request.user,
                            is_active=True
                        )
                        
                        # Create inventory record
                        Inventory.objects.create(
                            part=part,
                            stock=quantity,
                            reorder_level=max(1, quantity // 10),  # Set reorder level to 10% of initial stock
                            location='Warehouse'
                        )
                        
                        created_parts.append(part.name)
                        success_count += 1
                        
                    except Exception as e:
                        errors.append(f'Row {row_number}: {str(e)}')
                        error_count += 1
                        continue
                
                # Update bulk upload log
                bulk_log.total_rows = row_number - 1
                bulk_log.success_count = success_count
                bulk_log.error_count = error_count
                bulk_log.status = 'completed' if error_count == 0 else 'completed_with_errors'
                bulk_log.error_details = '\n'.join(errors) if errors else None
                bulk_log.save()
                
        except Exception as e:
            # Update log with failure status
            bulk_log.status = 'failed'
            bulk_log.error_details = str(e)
            bulk_log.save()
            raise
        
        return {
            'success_count': success_count,
            'error_count': error_count,
            'skipped_count': skipped_count,
            'errors': errors[:10],  # Limit to first 10 errors for display
            'created_parts': created_parts[:10],  # Limit for display
            'updated_parts': updated_parts[:10],  # Limit for display
            'bulk_log_id': bulk_log.id,
        }


@dealer_admin_required
def fetch_api_parts(request, source_id):
     """Fetch parts from external API using registered IntegrationSource."""
     if request.method != 'POST':
         return JsonResponse({'error': 'Only POST method allowed'}, status=405)
     
     try:
         # Get the integration source
         integration_source = get_object_or_404(
             IntegrationSource, 
             id=source_id, 
             dealer=request.user,
             is_active=True
         )
         
         # Create bulk upload log
         bulk_log = BulkUploadLog.objects.create(
             user=request.user,
             file_name=f'API Import - {integration_source.name}',
             file_size=0,  # API import doesn't have file size
             status='processing'
         )
         
         try:
             # Prepare headers based on auth type
             headers = {'Content-Type': 'application/json'}
             
             if integration_source.auth_type == 'api_key':
                 headers['Authorization'] = f'Bearer {integration_source.api_key}'
             elif integration_source.auth_type == 'basic':
                 # For basic auth, api_key should contain username:password
                 import base64
                 encoded_credentials = base64.b64encode(integration_source.api_key.encode()).decode()
                 headers['Authorization'] = f'Basic {encoded_credentials}'
             
             # Make API request
             response = requests.get(
                 integration_source.api_url, 
                 headers=headers, 
                 timeout=30
             )
             response.raise_for_status()
             api_data = response.json()
             
             # Process API data
             results = process_api_data(api_data, request.user, integration_source, bulk_log)
             
             # Update integration source last sync
             integration_source.last_sync = timezone.now()
             integration_source.save()
             
             return JsonResponse({
                 'success': True,
                 'message': f'Successfully processed {results["success_count"]} parts from {integration_source.name}',
                 'results': results
             })
             
         except (RequestException, Timeout, ConnectionError) as e:
             bulk_log.status = 'failed'
             bulk_log.error_details = f'API request failed: {str(e)}'
             bulk_log.save()
             return JsonResponse({'error': f'API request failed: {str(e)}'}, status=400)
             
         except json.JSONDecodeError:
             bulk_log.status = 'failed'
             bulk_log.error_details = 'Invalid JSON response from API'
             bulk_log.save()
             return JsonResponse({'error': 'Invalid JSON response from API'}, status=400)
             
     except IntegrationSource.DoesNotExist:
         return JsonResponse({'error': 'Integration source not found or not accessible'}, status=404)
     except Exception as e:
         if 'bulk_log' in locals():
             bulk_log.status = 'failed'
             bulk_log.error_details = str(e)
             bulk_log.save()
         return JsonResponse({'error': f'Unexpected error: {str(e)}'}, status=500)


def process_api_data(api_data, user, integration_source, bulk_log):
    """Process API data and create parts."""
    from decimal import Decimal, InvalidOperation
    
    success_count = 0
    error_count = 0
    skipped_count = 0
    errors = []
    created_parts = []
    updated_parts = []
    
    # Handle different API response formats
    parts_data = api_data
    if isinstance(api_data, dict):
        # Try common keys for parts data
        for key in ['parts', 'products', 'items', 'data']:
            if key in api_data and isinstance(api_data[key], list):
                parts_data = api_data[key]
                break
    
    if not isinstance(parts_data, list):
        return {
            'success_count': 0,
            'error_count': 1,
            'errors': ['API response does not contain a valid parts array'],
            'created_parts': []
        }
    
    try:
        with transaction.atomic():
            for item in parts_data:
                try:
                    # Extract part data with flexible field mapping
                    name = item.get('name') or item.get('title') or item.get('product_name')
                    sku = item.get('sku') or item.get('part_number') or item.get('id')
                    price_value = item.get('price') or item.get('cost') or item.get('unit_price')
                    quantity_value = item.get('quantity') or item.get('stock') or item.get('inventory', 0)
                    description = item.get('description') or item.get('details', '')
                    category_name = item.get('category') or item.get('category_name', 'Uncategorized')
                    brand_name = item.get('brand') or item.get('manufacturer', 'Unknown')
                    
                    # Validate required fields
                    if not all([name, sku, price_value]):
                        errors.append(f'Missing required fields for item: {item}')
                        error_count += 1
                        continue
                    
                    # Convert price and quantity
                    try:
                        price = Decimal(str(price_value))
                        quantity = int(quantity_value)
                    except (ValueError, InvalidOperation):
                        errors.append(f'Invalid price or quantity for {name}')
                        error_count += 1
                        continue
                    
                    # Check for existing part
                    existing_part = Part.objects.filter(sku=sku).first()
                    if existing_part:
                        # Update existing part if needed
                        updated = False
                        if existing_part.price != price:
                            existing_part.price = price
                            updated = True
                        if existing_part.quantity != quantity:
                            existing_part.quantity = quantity
                            updated = True
                        
                        if updated:
                            existing_part.save()
                            updated_parts.append(existing_part.name)
                        else:
                            skipped_count += 1
                        continue
                    
                    # Get or create category
                    category, _ = Category.objects.get_or_create(
                        name=category_name,
                        defaults={'description': f'Auto-created from {integration_source.name}'}
                    )
                    
                    # Get or create brand
                    brand, _ = Brand.objects.get_or_create(
                        name=brand_name,
                        defaults={'description': f'Auto-created from {integration_source.name}'}
                    )
                    
                    # Create part
                    part = Part.objects.create(
                        name=name,
                        sku=sku,
                        description=description,
                        price=price,
                        quantity=quantity,
                        category=category,
                        brand=brand,
                        dealer=user if user.role == UserRole.SELLER else None,
                        is_active=True
                    )
                    
                    # Create inventory record
                    Inventory.objects.create(
                        part=part,
                        stock=quantity,
                        reorder_level=max(1, quantity // 10)
                    )
                    
                    created_parts.append(part.name)
                    success_count += 1
                    
                except Exception as e:
                    errors.append(f'Error processing item {item.get("name", "unknown")}: {str(e)}')
                    error_count += 1
                    continue
            
            # Update bulk upload log
            bulk_log.total_records = len(parts_data) if isinstance(parts_data, list) else 0
            bulk_log.successful_records = success_count
            bulk_log.failed_records = error_count
            bulk_log.status = 'completed' if error_count == 0 else 'partial'
            bulk_log.error_log = '\n'.join(errors) if errors else None
            bulk_log.save()
            
    except Exception as e:
        errors.append(f'Transaction failed: {str(e)}')
        error_count += 1
        # Update log with failure status
        bulk_log.status = 'failed'
        bulk_log.error_log = str(e)
        bulk_log.save()
    
    return {
        'success_count': success_count,
        'error_count': error_count,
        'skipped_count': skipped_count,
        'errors': errors[:10],  # Limit errors for display
        'created_parts': created_parts[:10],  # Limit for display
        'updated_parts': updated_parts[:10],  # Limit for display
        'total_rows': len(parts_data) if isinstance(parts_data, list) else 0,
        'bulk_log_id': bulk_log.id
    }


@login_required
def api_import_view(request):
    """Display API import interface with available integration sources."""
    if not hasattr(request.user, 'dealer'):
        messages.error(request, 'Access denied. Dealer account required.')
        return redirect('parts:dealer_dashboard')
    
    # Get active integration sources for the dealer
    integration_sources = IntegrationSource.objects.filter(
        dealer=request.user.dealer,
        is_active=True
    ).order_by('-last_sync', 'name')
    
    context = {
        'integration_sources': integration_sources,
        'page_title': 'API Import'
    }
    
    return render(request, 'parts/api_import.html', context)


# Cart Functionality
def get_cart(request):
    """Get cart from session."""
    cart = request.session.get('cart', {})
    return cart


def get_cart_total(request):
    """Calculate cart total for both authenticated and anonymous users."""
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            return float(cart.total_price)
        except Cart.DoesNotExist:
            return 0.0
    else:
        # Session-based cart for anonymous users
        cart = get_cart(request)
        total = 0
        for item_id, item_data in cart.items():
            try:
                part = Part.objects.get(id=item_id, is_active=True)
                total += float(part.price) * item_data['quantity']
            except Part.DoesNotExist:
                continue
        return total


def get_cart_count(request):
    """Get total number of items in cart."""
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            return cart.items.count()
        except Cart.DoesNotExist:
            return 0
    else:
        # Session-based cart for anonymous users
        cart = get_cart(request)
        return sum(item['quantity'] for item in cart.values())


@ensure_csrf_cookie
def add_to_cart(request, part_id):
    """Add item to cart - supports both AJAX JSON and form POST requests."""
    if request.method == 'POST':
        try:
            # Parse quantity from both JSON and form data
            if request.content_type == 'application/json':
                try:
                    data = json.loads(request.body)
                    quantity = int(data.get('qty', data.get('quantity', 1)))
                except (json.JSONDecodeError, ValueError):
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
                    messages.error(request, 'Invalid request data.')
                    return redirect('parts:part_detail', pk=part_id)
            else:
                quantity = int(request.POST.get('qty', request.POST.get('quantity', 1)))
            
            # Validate quantity
            if quantity < 1:
                error_msg = 'Quantity must be at least 1.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': error_msg}, status=400)
                messages.error(request, error_msg)
                return redirect('parts:part_detail', pk=part_id)
            
            # Use atomic transaction for cart operations
            with transaction.atomic():
                # Get part with SELECT FOR UPDATE to prevent race conditions
                part = get_object_or_404(Part.objects.select_for_update(), id=part_id, is_active=True)
                
                # Check stock availability
                available_stock = part.inventory.stock if hasattr(part, 'inventory') else part.quantity
                if available_stock < quantity:
                    error_msg = f'Only {available_stock} items available in stock.'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'error': error_msg}, status=400)
                    messages.error(request, error_msg)
                    return redirect('parts:part_detail', pk=part_id)
                
                # Get or create cart
                cart = get_cart(request)
                
                # Add or update item in cart
                if str(part_id) in cart:
                    new_quantity = cart[str(part_id)]['quantity'] + quantity
                    # Check total quantity against stock
                    if available_stock < new_quantity:
                        error_msg = f'Cannot add more items. Only {available_stock} available in stock.'
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return JsonResponse({'error': error_msg}, status=400)
                        messages.error(request, error_msg)
                        return redirect('parts:part_detail', pk=part_id)
                    cart[str(part_id)]['quantity'] = new_quantity
                    success_msg = f'Updated {part.name} quantity in cart.'
                else:
                    cart[str(part_id)] = {
                        'quantity': quantity,
                        'name': part.name,
                        'price': float(part.price),
                        'sku': part.sku,
                        'image_url': part.image.url if part.image else (part.image_url or ''),
                    }
                    success_msg = f'Added {part.name} to cart.'
                
                # Save cart to session
                request.session['cart'] = cart
                request.session.modified = True
                
                # Return JSON response for AJAX requests
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': success_msg,
                        'cart_count': get_cart_count(request),
                        'cart_total': float(get_cart_total(request))
                    })
                
                messages.success(request, success_msg)
                return redirect('parts:cart_view')
                
        except Part.DoesNotExist:
            error_msg = 'Part not found.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': error_msg}, status=404)
            messages.error(request, error_msg)
        except ValueError:
            error_msg = 'Invalid quantity.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': error_msg}, status=400)
            messages.error(request, error_msg)
        except Exception as e:
            error_msg = f'Error adding item to cart: {str(e)}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': error_msg}, status=500)
            messages.error(request, error_msg)
    
    # For non-POST requests or fallback
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    return redirect('parts:part_detail', pk=part_id)


def cart_view(request):
    """Display cart contents - works for both authenticated and anonymous users"""
    if request.user.is_authenticated:
        # Use database cart for authenticated users
        try:
            cart_obj = Cart.objects.get(user=request.user)
            cart_items = cart_obj.items.select_related('part', 'part__brand', 'part__category').all()
            
            # Convert to template-compatible format
            cart_items_list = []
            has_out_of_stock = False
            has_insufficient_stock = False
            cart_total = 0
            
            for item in cart_items:
                part = item.part
                available_stock = part.inventory.stock if hasattr(part, 'inventory') else part.quantity
                in_stock = available_stock >= item.quantity
                
                # Track stock issues
                if available_stock == 0:
                    has_out_of_stock = True
                elif not in_stock:
                    has_insufficient_stock = True
                
                cart_items_list.append({
                    'part': part,
                    'quantity': item.quantity,
                    'item_total': item.total_price,
                    'in_stock': in_stock,
                    'available_stock': available_stock,
                    'id': item.id  # Add item ID for authenticated users
                })
                cart_total += item.total_price
            
            context = {
                'cart_items': cart_items_list,
                'cart_total': cart_total,
                'cart_count': len(cart_items_list),
                'has_out_of_stock': has_out_of_stock,
                'has_insufficient_stock': has_insufficient_stock,
                'can_checkout': not has_out_of_stock and not has_insufficient_stock,
                'page_title': 'Shopping Cart'
            }
            
            return render(request, 'parts/cart.html', context)
            
        except Cart.DoesNotExist:
            # No cart exists for authenticated user
            context = {
                'cart_items': [],
                'cart_total': 0,
                'cart_count': 0,
                'has_out_of_stock': False,
                'has_insufficient_stock': False,
                'can_checkout': True,
                'page_title': 'Shopping Cart'
            }
            return render(request, 'parts/cart.html', context)
    
    else:
        # Session-based cart for anonymous users
        cart = get_cart(request)
        cart_items = []
        cart_total = 0
        has_out_of_stock = False
        has_insufficient_stock = False
        
        for item_id, item_data in cart.items():
            try:
                part = Part.objects.get(id=item_id, is_active=True)
                item_total = part.price * item_data['quantity']
                available_stock = part.inventory.stock if hasattr(part, 'inventory') else part.quantity
                in_stock = available_stock >= item_data['quantity']
                
                # Track stock issues
                if available_stock == 0:
                    has_out_of_stock = True
                elif not in_stock:
                    has_insufficient_stock = True
                
                cart_items.append({
                    'part': part,
                    'quantity': item_data['quantity'],
                    'item_total': item_total,
                    'in_stock': in_stock,
                    'available_stock': available_stock,
                    'part_id': item_id  # Use part_id for guest users
                })
                cart_total += item_total
            except Part.DoesNotExist:
                # Remove invalid items from cart
                del cart[item_id]
                request.session['cart'] = cart
                request.session.modified = True
        
        context = {
            'cart_items': cart_items,
            'cart_total': cart_total,
            'cart_count': len(cart_items),
            'has_out_of_stock': has_out_of_stock,
            'has_insufficient_stock': has_insufficient_stock,
            'can_checkout': not has_out_of_stock and not has_insufficient_stock,
            'page_title': 'Shopping Cart'
        }
        
        return render(request, 'parts/cart.html', context)


def update_cart(request, part_id):
    """Update item quantity in cart."""
    if request.method == 'POST':
        try:
            part = get_object_or_404(Part, id=part_id, is_active=True)
            quantity = int(request.POST.get('quantity', 1))
            
            cart = get_cart(request)
            
            if str(part_id) in cart:
                if quantity <= 0:
                    # Remove item if quantity is 0 or negative
                    del cart[str(part_id)]
                    messages.success(request, f'Removed {part.name} from cart.')
                else:
                    # Check stock availability
                    available_stock = part.inventory.stock if hasattr(part, 'inventory') else part.quantity
                    if available_stock < quantity:
                        messages.error(request, f'Only {available_stock} items available in stock.')
                        return redirect('parts:cart_view')
                    
                    cart[str(part_id)]['quantity'] = quantity
                    messages.success(request, f'Updated {part.name} quantity.')
                
                request.session['cart'] = cart
                request.session.modified = True
            
            # Return JSON response for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'cart_count': get_cart_count(request),
                    'cart_total': float(get_cart_total(request))
                })
            
        except (Part.DoesNotExist, ValueError) as e:
            messages.error(request, 'Error updating cart.')
    
    return redirect('parts:cart_view')


def remove_from_session_cart_legacy(request, part_id):
    """Remove item from cart (legacy session-based function for non-AJAX requests)."""
    try:
        part = get_object_or_404(Part, id=part_id)
        cart = get_cart(request)
        
        if str(part_id) in cart:
            del cart[str(part_id)]
            request.session['cart'] = cart
            request.session.modified = True
            messages.success(request, f'Removed {part.name} from cart.')
        
        # Return JSON response for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Removed {part.name} from cart.',
                'cart_count': get_cart_count(request),
                'cart_total': float(get_cart_total(request))
            })
        
    except Part.DoesNotExist:
        messages.error(request, 'Part not found.')
    
    return redirect('parts:cart_view')


def clear_cart(request):
    """Clear all items from cart."""
    if 'cart' in request.session:
        del request.session['cart']
        request.session.modified = True
        messages.success(request, 'Cart cleared successfully.')
    
    return redirect('parts:cart_view')


def clear_cart_universal(request):
    """Clear all items from cart for both authenticated and guest users via AJAX."""
    if request.user.is_authenticated:
        # Clear database cart for authenticated users
        try:
            cart = Cart.objects.get(user=request.user)
            cart.items.all().delete()
            return JsonResponse({
                'success': True,
                'message': 'Cart cleared successfully',
                'cart_total_items': 0,
                'cart_total_price': 0.00
            })
        except Cart.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'No cart found'
            })
    else:
        # Clear session cart for guest users
        if 'cart' in request.session:
            del request.session['cart']
            request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'message': 'Cart cleared successfully',
            'cart_count': 0,
            'cart_total': 0.00
        })


def update_cart_item_universal(request, item_id):
    """Universal cart item update that works for both authenticated and guest users."""
    if request.user.is_authenticated:
        # Use database cart for authenticated users
        return update_cart_item(request, item_id)
    else:
        # Use session cart for guest users
        return update_session_cart_item(request, item_id)


@require_http_methods(["POST"])
def remove_from_cart_universal(request, item_id):
    """Universal cart item removal that works for both authenticated and guest users."""
    if request.user.is_authenticated:
        # Use database cart for authenticated users
        return remove_from_cart(request, item_id)
    else:
        # Use session cart for guest users
        return remove_from_session_cart(request, item_id)


def remove_from_session_cart(request, part_id):
    """Remove item from session cart for guest users via AJAX."""
    try:
        # Use filter instead of get_object_or_404 to avoid Http404 exception
        part = Part.objects.filter(id=part_id, is_active=True).first()
        
        if not part:
            return JsonResponse({
                'success': False,
                'message': 'Part not found'
            })
        
        cart = get_cart(request)
        
        if str(part_id) in cart:
            del cart[str(part_id)]
            request.session['cart'] = cart
            request.session.modified = True
            
            # Always return JSON response
            return JsonResponse({
                'success': True,
                'message': f'Removed {part.name} from cart',
                'cart_count': get_cart_count(request),
                'cart_total': float(get_cart_total(request))
            })
        else:
            # Item not found in cart
            return JsonResponse({
                'success': False,
                'message': 'Item not found in cart'
            })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while removing from cart'
        })


def update_session_cart_item(request, part_id):
    """Update quantity of a session cart item via AJAX for guest users."""
    try:
        part = get_object_or_404(Part, id=part_id)
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity <= 0:
            return JsonResponse({
                'success': False,
                'message': 'Invalid quantity'
            })
        
        cart = get_cart(request)
        part_id_str = str(part_id)
        
        if part_id_str in cart:
            # Check stock availability
            if quantity > part.quantity:
                return JsonResponse({
                    'success': False,
                    'message': f'Only {part.quantity} items available in stock'
                })
            
            # Update quantity
            cart[part_id_str]['quantity'] = quantity
            request.session['cart'] = cart
            request.session.modified = True
            
            return JsonResponse({
                'success': True,
                'message': 'Quantity updated successfully',
                'cart_count': get_cart_count(request),
                'cart_total': float(get_cart_total(request))
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Item not found in cart'
            })
            
    except Part.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Part not found'
        })
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid quantity value'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while updating cart'
        })


def cart_count_api(request):
    """API endpoint to get cart count for both authenticated and anonymous users."""
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            return JsonResponse({
                'cart_count': cart.total_items,
                'cart_total': float(cart.total_price)
            })
        except Cart.DoesNotExist:
            return JsonResponse({
                'cart_count': 0,
                'cart_total': 0.0
            })
    else:
        # Use session-based cart for anonymous users
        return JsonResponse({
            'cart_count': get_cart_count(request),
            'cart_total': float(get_cart_total(request))
        })


def checkout(request):
    """Checkout view for both authenticated and guest users."""
    cart = get_cart(request)
    
    if not cart:
        messages.error(request, 'Your cart is empty.')
        return redirect('parts:cart_view')
    
    cart_total = get_cart_total(request)
    
    if request.method == 'POST':
        if request.user.is_authenticated:
            # Process authenticated user checkout
            return process_authenticated_checkout(request, cart, cart_total)
        else:
            # Process guest checkout
            return process_guest_checkout(request, cart, cart_total)
    
    # GET request - show checkout form
    context = {
        'cart': cart,
        'cart_total': cart_total,
        'is_authenticated': request.user.is_authenticated,
    }
    
    if not request.user.is_authenticated:
        from .forms import GuestCheckoutForm
        context['guest_form'] = GuestCheckoutForm()
    
    return render(request, 'parts/checkout.html', context)


def process_guest_checkout(request, cart, cart_total):
    """Process checkout for guest users."""
    from .forms import GuestCheckoutForm
    from .models import Order, OrderItem, OrderStatusHistory
    from django.core.mail import send_mail
    from django.conf import settings
    from django.db import transaction
    
    form = GuestCheckoutForm(request.POST)
    
    if form.is_valid():
        try:
            with transaction.atomic():
                # Create order
                order = Order.objects.create(
                    guest_name=form.cleaned_data['name'],
                    guest_email=form.cleaned_data['email'],
                    guest_phone=form.cleaned_data['phone'],
                    guest_address=form.cleaned_data['address'],
                    total_price=cart_total,
                    session_key=request.session.session_key,
                    status='pending'
                )
                
                # Create order items first
                for part_id, item in cart.items():
                    part = Part.objects.select_for_update().get(id=part_id)
                    quantity = item['quantity']
                    
                    # Create order item
                    OrderItem.objects.create(
                        order=order,
                        part=part,
                        quantity=quantity,
                        price=part.price
                    )
                
                # Check stock availability for all items
                stock_available, error_message = order.check_stock_availability()
                if not stock_available:
                    raise ValueError(error_message)
                
                # Deduct inventory for all items
                order.deduct_inventory()
                
                # Update order status to confirmed with audit logging
                order.update_status('confirmed', request=request, 
                                  change_reason='Order confirmed after successful payment')
                
                # Create initial status history entry for order creation
                OrderStatusHistory.objects.create(
                    order=order,
                    previous_status=None,
                    new_status='pending',
                    notes='Order created by guest user',
                    ip_address=order.get_client_ip(request) if request else None,
                    user_agent=request.META.get('HTTP_USER_AGENT', '') if request else ''
                )
                
                # Clear cart
                if 'cart' in request.session:
                    del request.session['cart']
                    request.session.modified = True
                
                # Store order confirmation in session
                request.session['order_confirmation'] = {
                    'order_number': order.order_number,
                    'email': order.guest_email,
                    'total': float(order.total_price)
                }
                
                # Send confirmation email
                send_order_confirmation_email(order)
                
                messages.success(request, f'Order {order.order_number} placed successfully! Confirmation email sent.')
                return redirect('parts:order_confirmation')
                
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, 'An error occurred while processing your order. Please try again.')
    
    # If form is invalid or error occurred, show form with errors
    context = {
        'cart': cart,
        'cart_total': cart_total,
        'guest_form': form,
        'is_authenticated': False,
    }
    return render(request, 'parts/checkout.html', context)


def process_authenticated_checkout(request, cart, cart_total):
    """Process checkout for authenticated users."""
    from .models import Order, OrderItem, OrderStatusHistory
    from django.db import transaction
    
    try:
        with transaction.atomic():
            # Create order for authenticated user
            order = Order.objects.create(
                user=request.user,
                total_price=cart_total,
                status='pending'
            )
            
            # Create order items first
            for part_id, item in cart.items():
                part = Part.objects.select_for_update().get(id=part_id)
                quantity = item['quantity']
                
                # Create order item
                OrderItem.objects.create(
                    order=order,
                    part=part,
                    quantity=quantity,
                    price=part.price
                )
            
            # Check stock availability for all items
            stock_available, error_message = order.check_stock_availability()
            if not stock_available:
                raise ValueError(error_message)
            
            # Deduct inventory for all items
            order.deduct_inventory()
            
            # Update order status to confirmed with audit logging
            order.update_status('confirmed', request=request, 
                              change_reason='Order confirmed after successful payment')
            
            # Create initial status history entry for order creation
            OrderStatusHistory.objects.create(
                order=order,
                previous_status=None,
                new_status='pending',
                changed_by=request.user,
                notes='Order created by authenticated user',
                ip_address=order.get_client_ip(request) if request else None,
                user_agent=request.META.get('HTTP_USER_AGENT', '') if request else ''
            )
            
            # Clear cart
            if 'cart' in request.session:
                del request.session['cart']
                request.session.modified = True
            
            # Store order confirmation in session
            request.session['order_confirmation'] = {
                'order_number': order.order_number,
                'email': request.user.email,
                'total': float(order.total_price)
            }
            
            # Send confirmation email
            send_order_confirmation_email(order)
            
            messages.success(request, f'Order {order.order_number} placed successfully! Confirmation email sent.')
            return redirect('parts:order_confirmation')
            
    except ValueError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, 'An error occurred while processing your order. Please try again.')
    
    return redirect('parts:checkout')


def send_order_confirmation_email(order):
    """Send order confirmation email to customer."""
    from django.core.mail import send_mail
    from django.conf import settings
    from django.template.loader import render_to_string
    
    try:
        # Prepare email context
        context = {
            'order': order,
            'order_items': order.items.all(),
            'customer_name': order.customer_name,
        }
        
        # Render email content
        subject = f'Order Confirmation - {order.order_number}'
        message = render_to_string('emails/order_confirmation.txt', context)
        html_message = render_to_string('emails/order_confirmation.html', context)
        
        # Send email
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@carsportal.com'),
            recipient_list=[order.customer_email],
            html_message=html_message,
            fail_silently=False,
        )
        
    except Exception as e:
        # Log the error but don't fail the order
        print(f"Failed to send confirmation email for order {order.order_number}: {str(e)}")


def order_confirmation(request):
    """Display order confirmation page."""
    order_data = request.session.get('order_confirmation')
    
    if not order_data:
        messages.error(request, 'No order confirmation found.')
        return redirect('parts:part_list')
    
    context = {
        'order_number': order_data['order_number'],
        'email': order_data['email'],
        'total': order_data['total'],
    }
    
    # Clear the confirmation from session after displaying
    if 'order_confirmation' in request.session:
        del request.session['order_confirmation']
        request.session.modified = True
    
    return render(request, 'parts/order_confirmation.html', context)


# Cart Views
@require_http_methods(["POST"])
@login_required
def add_to_cart_authenticated(request, part_id):
    """Add a part to the user's cart via AJAX."""
    try:
        part = get_object_or_404(Part, id=part_id, is_active=True)
        quantity = int(request.POST.get('quantity', 1))
        
        # Validate quantity
        if quantity <= 0:
            return JsonResponse({
                'success': False,
                'message': 'Invalid quantity'
            })
        
        if quantity > part.quantity:
            return JsonResponse({
                'success': False,
                'message': f'Only {part.quantity} items available in stock'
            })
        
        # Get or create cart
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Get or create cart item
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            part=part,
            defaults={'quantity': quantity}
        )
        
        if not item_created:
            # Update existing item
            new_quantity = cart_item.quantity + quantity
            if new_quantity > part.quantity:
                return JsonResponse({
                    'success': False,
                    'message': f'Cannot add {quantity} more. Only {part.quantity - cart_item.quantity} more available.'
                })
            cart_item.quantity = new_quantity
            cart_item.save()
        
        return JsonResponse({
            'success': True,
            'message': f'{part.name} added to cart',
            'cart_total_items': cart.total_items,
            'cart_total_price': float(cart.total_price)
        })
        
    except Part.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Part not found'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while adding to cart'
        })


@require_http_methods(["POST"])
@login_required
def remove_from_cart(request, item_id):
    """Remove an item from the user's cart via AJAX."""
    try:
        # Use filter instead of get_object_or_404 to avoid Http404 exception
        cart_item = CartItem.objects.filter(id=item_id, cart__user=request.user).first()
        
        if not cart_item:
            return JsonResponse({
                'success': False,
                'message': 'Cart item not found'
            })
        
        part_name = cart_item.part.name
        cart = cart_item.cart
        cart_item.delete()
        
        # Get updated cart totals after deletion
        cart.refresh_from_db()
        
        return JsonResponse({
            'success': True,
            'message': f'{part_name} removed from cart',
            'cart_total_items': cart.total_items,
            'cart_total_price': float(cart.total_price)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while removing from cart'
        })


@require_http_methods(["POST"])
@login_required
def update_cart_item(request, item_id):
    """Update quantity of a cart item via AJAX."""
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity <= 0:
            return JsonResponse({
                'success': False,
                'message': 'Invalid quantity'
            })
        
        if quantity > cart_item.part.quantity:
            return JsonResponse({
                'success': False,
                'message': f'Only {cart_item.part.quantity} items available in stock'
            })
        
        cart_item.quantity = quantity
        cart_item.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Cart updated',
            'item_total_price': float(cart_item.total_price),
            'cart_total_items': cart_item.cart.total_items,
            'cart_total_price': float(cart_item.cart.total_price)
        })
        
    except CartItem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cart item not found'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while updating cart'
        })


def cart_view(request):
    """Display cart contents - works for both authenticated and anonymous users"""
    if request.user.is_authenticated:
        # Use database cart for authenticated users
        try:
            cart_obj = Cart.objects.get(user=request.user)
            cart_items = cart_obj.items.select_related('part', 'part__brand', 'part__category').all()
            
            # Convert to template-compatible format
            cart = {}
            cart_total = 0
            for item in cart_items:
                cart[str(item.part.id)] = {
                    'id': item.id,  # CartItem ID for updates/removal
                    'name': item.part.name,
                    'price': item.part.price,
                    'quantity': item.quantity,
                    'image': item.part.image,
                    'image_url': item.part.image_url,
                    'sku': item.part.sku,
                    'brand': item.part.brand.name if item.part.brand else '',
                    'total': item.total_price,
                    'available_stock': item.part.quantity,
                    'in_stock': item.part.is_in_stock,
                }
                cart_total += item.total_price
        except Cart.DoesNotExist:
            cart = {}
            cart_total = 0
    else:
        # Use session cart for anonymous users
        cart = get_cart(request)
        cart_total = 0
        for part_id, item_data in cart.items():
            try:
                part = Part.objects.get(id=part_id, is_active=True)
                item_total = part.price * item_data['quantity']
                cart[part_id].update({
                    'name': part.name,
                    'price': part.price,
                    'image': part.image,
                    'image_url': part.image_url,
                    'sku': part.sku,
                    'brand': part.brand.name if part.brand else '',
                    'total': item_total,
                    'available_stock': part.quantity,
                    'in_stock': part.is_in_stock,
                })
                cart_total += item_total
            except Part.DoesNotExist:
                continue
    
    context = {
        'cart': cart,
        'cart_total': cart_total,
        'cart_count': len(cart),
        'title': 'Shopping Cart'
    }
    
    return render(request, 'parts/cart.html', context)



# Multi-step Checkout Views


def checkout_step1_order_summary(request):
    """Step 1: Order Summary - Display cart items and allow discount code application.
    Works for both authenticated and guest users."""
    
    # Handle Buy Now order_id parameter
    order_id = request.GET.get('order_id')
    if order_id:
        try:
            order = Order.objects.get(id=order_id)
            if request.user.is_authenticated and order.customer != request.user:
                messages.error(request, 'Invalid order access.')
                return redirect('parts:cart_view')
            
            # Create checkout data from order
            checkout_data = {
                'items_total': str(order.total_price - order.shipping_cost - order.tax_amount),
                'discount_amount': '0.00',
                'discount_code': None,
                'buy_now_order_id': order_id,
            }
            request.session['checkout_data'] = checkout_data
            return redirect('parts:checkout_step2')
            
        except Order.DoesNotExist:
            messages.error(request, 'Order not found.')
            return redirect('parts:cart_view')
    
    # Initialize variables to avoid UnboundLocalError
    cart = None
    cart_items = None
    cart_items_data = []
    items_total = Decimal('0.00')
    shipping_cost = Decimal('0.00')
    tax_amount = Decimal('0.00')
    discount_amount = Decimal('0.00')
    discount_code = None
    grand_total = Decimal('0.00')
    
    # Handle both authenticated and guest users
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_items = cart.items.all()
            
            if not cart_items.exists():
                messages.warning(request, 'Your cart is empty.')
                return redirect('parts:cart_view')
            
            # Use database cart data
            items_total = cart.total_price
            cart_items_data = cart_items
            
        except Cart.DoesNotExist:
            messages.warning(request, 'Your cart is empty.')
            return redirect('parts:cart_view')
    else:
        # Handle guest users with session cart
        cart = get_cart(request)
        if not cart:
            messages.warning(request, 'Your cart is empty.')
            return redirect('parts:cart_view')
        
        # Convert session cart to items format
        cart_items_data = []
        items_total = Decimal('0.00')
        
        for item_id, item_data in cart.items():
            try:
                part = Part.objects.get(id=item_id, is_active=True)
                item_total = part.price * item_data['quantity']
                items_total += item_total
                
                # Create a mock cart item object for template compatibility
                cart_items_data.append({
                    'part': part,
                    'quantity': item_data['quantity'],
                    'price': part.price,
                    'total_price': item_total,
                    'get_total_price': lambda: item_total,  # For template compatibility
                })
            except Part.DoesNotExist:
                continue
        
        if not cart_items_data:
            messages.warning(request, 'Your cart is empty.')
            return redirect('parts:cart_view')
        
        # Calculate totals - items_total is already calculated above
        shipping_cost = Decimal('0.00')  # Will be calculated in step 2
        tax_amount = Decimal('0.00')  # Will be calculated based on location
        discount_amount = Decimal('0.00')
        
        # Check for applied discount
        discount_code = None
        if 'applied_discount_code' in request.session:
            try:
                discount_code = DiscountCode.objects.get(
                    code=request.session['applied_discount_code'],
                    is_active=True
                )
                is_valid, message = discount_code.is_valid()
                if is_valid:
                    discount_amount = discount_code.calculate_discount(items_total)
                else:
                    del request.session['applied_discount_code']
                    messages.error(request, f'Discount code error: {message}')
            except DiscountCode.DoesNotExist:
                del request.session['applied_discount_code']
                messages.error(request, 'Invalid discount code.')
        
        grand_total = items_total + shipping_cost + tax_amount - discount_amount
        
        # Handle discount code application
        if request.method == 'POST':
            action = request.POST.get('action')
            
            if action == 'apply_discount':
                discount_code_input = request.POST.get('discount_code', '').strip().upper()
                
                if discount_code_input:
                    try:
                        discount_code = DiscountCode.objects.get(
                            code=discount_code_input,
                            is_active=True
                        )
                        is_valid, message = discount_code.is_valid()
                        
                        if is_valid:
                            if items_total >= discount_code.minimum_order_amount:
                                request.session['applied_discount_code'] = discount_code.code
                                messages.success(request, f'Discount code "{discount_code.code}" applied successfully!')
                                return redirect('parts:checkout_step1')
                            else:
                                messages.error(request, f'Minimum order amount of {discount_code.minimum_order_amount} SAR required.')
                        else:
                            messages.error(request, message)
                    except DiscountCode.DoesNotExist:
                        messages.error(request, 'Invalid discount code.')
                else:
                    messages.error(request, 'Please enter a discount code.')
            
            elif action == 'remove_discount':
                if 'applied_discount_code' in request.session:
                    del request.session['applied_discount_code']
                    messages.success(request, 'Discount code removed.')
                return redirect('parts:checkout_step1')
            
            elif action == 'proceed_to_shipping':
                # Store order summary in session and proceed to step 2
                request.session['checkout_data'] = {
                    'items_total': str(items_total),
                    'discount_amount': str(discount_amount),
                    'discount_code': discount_code.code if discount_code else None,
                }
                return redirect('parts:checkout_step2')
        
        context = {
            'cart': cart,
            'cart_items': cart_items_data,  # Use the unified data structure
            'items_total': items_total,
            'shipping_cost': shipping_cost,
            'tax_amount': tax_amount,
            'discount_amount': discount_amount,
            'discount_code': discount_code,
            'grand_total': grand_total,
            'step': 1,
            'title': 'Checkout - Order Summary'
        }
        
        return render(request, 'parts/checkout/step1_order_summary.html', context)

def checkout_step2_shipping_info(request):
    """Step 2: Shipping Information - Collect contact and shipping details.
    Works for both authenticated and guest users."""
    
    # Check if step 1 is completed
    if 'checkout_data' not in request.session:
        messages.warning(request, 'Please complete the order summary first.')
        return redirect('parts:checkout_step1')
    
    # Get checkout data for both user types
    checkout_data = request.session['checkout_data']
    items_total = Decimal(checkout_data['items_total'])
    discount_amount = Decimal(checkout_data['discount_amount'])
    
    # Handle both authenticated and guest users
    # Check if this is a buy now order
    buy_now_order = None
    if checkout_data.get('buy_now_order_id'):
        try:
            buy_now_order = Order.objects.get(id=checkout_data['buy_now_order_id'])
            # For buy now orders, we don't need a cart
            cart = None
        except Order.DoesNotExist:
            messages.error(request, 'Order not found.')
            return redirect('parts:cart_view')
    else:
        # Regular cart checkout flow
        if request.user.is_authenticated:
            try:
                cart = Cart.objects.get(user=request.user)
                if not cart.items.exists():
                    messages.warning(request, 'Your cart is empty.')
                    return redirect('parts:cart_view')
            except Cart.DoesNotExist:
                messages.warning(request, 'Your cart is empty.')
                return redirect('parts:cart_view')
        else:
            # Check guest cart
            cart = get_cart(request)
            if not cart:
                messages.warning(request, 'Your cart is empty.')
                return redirect('parts:cart_view')
    
    cities = SaudiCity.objects.filter(is_active=True).order_by('name')
    
    if request.method == 'POST':
        # Collect shipping information - map template field names to our data structure
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        city_id = request.POST.get('city')
        area = request.POST.get('area')  # This is city_area_id in template
        address = request.POST.get('address', '').strip()
        building = request.POST.get('building', '').strip()
        apartment = request.POST.get('apartment', '').strip()
        additional_info = request.POST.get('additional_info', '').strip()
        
        # Map template fields to our internal structure
        contact_name = f"{first_name} {last_name}".strip()
        mobile_number = phone
        city_area_id = area
        landmark = additional_info
        comments = additional_info
        
        # Build full address with building and apartment info
        full_address = address
        if building:
            full_address += f", Building: {building}"
        if apartment:
            full_address += f", Apartment: {apartment}"
        
        # Validation
        errors = []
        if not contact_name:
            errors.append('Contact name is required.')
        if not mobile_number:
            errors.append('Mobile number is required.')
        if not city_id:
            errors.append('City selection is required.')
        if not city_area_id:
            errors.append('Area selection is required.')
        if not address:
            errors.append('Address is required.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            try:
                city = SaudiCity.objects.get(id=city_id, is_active=True)
                city_area = None
                if city_area_id:
                    city_area = CityArea.objects.get(id=city_area_id, city=city, is_active=True)
                
                # Calculate shipping cost
                shipping_cost = Decimal('0.00')
                try:
                    shipping_rate = ShippingRate.objects.get(city=city, is_active=True)
                    shipping_cost = shipping_rate.calculate_shipping_cost(items_total)
                except ShippingRate.DoesNotExist:
                    shipping_cost = Decimal('25.00')  # Default shipping cost
                
                # Calculate tax (15% VAT in Saudi Arabia)
                tax_rate = Decimal('0.15')
                tax_amount = (items_total + shipping_cost - discount_amount) * tax_rate
                
                grand_total = items_total + shipping_cost + tax_amount - discount_amount
                
                # Update checkout data
                checkout_data.update({
                    'contact_name': contact_name,
                    'mobile_number': mobile_number,
                    'email': email,
                    'city_id': city_id,
                    'city_name': city.name,
                    'city_area_id': city_area_id,
                    'city_area_name': city_area.name if city_area else '',
                    'address': full_address,
                    'landmark': landmark,
                    'comments': comments,
                    'shipping_cost': str(shipping_cost),
                    'tax_amount': str(tax_amount),
                    'grand_total': str(grand_total),
                })
                request.session['checkout_data'] = checkout_data
                
                return redirect('parts:checkout_step3')
                
            except (SaudiCity.DoesNotExist, CityArea.DoesNotExist):
                messages.error(request, 'Invalid city or area selection.')
    
    # Get city areas for each city to populate the area dropdown
    city_areas = {}
    for city in cities:
        areas = CityArea.objects.filter(city=city, is_active=True).order_by('name')
        city_areas[city.id] = [{'id': area.id, 'name': area.name} for area in areas]
    
    context = {
        'cart': cart,
        'cities': cities,
        'city_areas': city_areas,
        'checkout_data': {
            'items_total': str(items_total),
            'discount_amount': str(discount_amount),
            'grand_total': str(items_total - discount_amount),  # Simple total without shipping/tax for display
        },
        'step': 2,
        'title': 'Checkout - Shipping Information'
    }
    
    return render(request, 'parts/checkout/step2_shipping_info.html', context)


def checkout_step3_payment_method(request):
    """Step 3: Payment Method - Select payment method and complete order."""
    import logging
    logger = logging.getLogger(__name__)
    
    # Check if previous steps are completed
    if 'checkout_data' not in request.session:
        messages.warning(request, 'Please complete the previous steps first.')
        return redirect('parts:checkout_step1')
    
    checkout_data = request.session['checkout_data']
    required_fields = ['contact_name', 'mobile_number', 'city_id', 'address']
    
    if not all(field in checkout_data for field in required_fields):
        messages.warning(request, 'Please complete the shipping information first.')
        return redirect('parts:checkout_step2')
    
    try:
        # Handle both authenticated and guest users
        # Check if this is a buy now order
        buy_now_order = None
        if checkout_data.get('buy_now_order_id'):
            try:
                buy_now_order = Order.objects.get(id=checkout_data['buy_now_order_id'])
                # For buy now orders, we don't need a cart
                cart = None
            except Order.DoesNotExist:
                messages.error(request, 'Order not found.')
                return redirect('parts:cart_view')
        else:
            # Regular cart checkout flow
            if request.user.is_authenticated:
                cart = Cart.objects.get(user=request.user)
                if not cart.items.exists():
                    messages.warning(request, 'Your cart is empty.')
                    return redirect('parts:cart_view')
            else:
                # Check guest cart
                cart = get_cart(request)
                if not cart:
                    messages.warning(request, 'Your cart is empty.')
                    return redirect('parts:cart_view')
        
        # Get totals from checkout data
        items_total = Decimal(checkout_data['items_total'])
        shipping_cost = Decimal(checkout_data.get('shipping_cost', '0.00'))
        tax_amount = Decimal(checkout_data.get('tax_amount', '0.00'))
        discount_amount = Decimal(checkout_data['discount_amount'])
        grand_total = items_total + shipping_cost + tax_amount - discount_amount
        
        if request.method == 'POST':
            payment_method = request.POST.get('payment_method')
            
            if payment_method in ['cash_on_delivery', 'bank_transfer']:
                try:
                    with transaction.atomic():
                        logger.info(f"Processing payment for order: buy_now_order={buy_now_order is not None}, payment_method={payment_method}")
                        
                        # Handle buy now orders vs regular cart orders
                        if buy_now_order:
                            # Update existing buy now order
                            order = buy_now_order
                            order.payment_method = payment_method
                            order.payment_status = 'pending'
                            order.status = 'pending'
                            order.shipping_cost = shipping_cost
                            order.tax_amount = tax_amount
                            order.total_price = grand_total
                            
                            # Update customer info if authenticated
                            if request.user.is_authenticated:
                                order.customer = request.user
                            
                            order.save()
                            logger.info(f"Updated buy now order: order_id={order.id}, payment_method={payment_method}")
                        else:
                            # Create new order for regular cart checkout
                            order_data = {
                                'total_price': grand_total,
                                'shipping_cost': shipping_cost,
                                'tax_amount': tax_amount,
                                'status': 'pending',
                                'payment_method': payment_method,
                                'payment_status': 'pending'
                            }
                            
                            # Set customer or guest information
                            if request.user.is_authenticated:
                                order_data['customer'] = request.user
                            else:
                                order_data['guest_name'] = checkout_data.get('contact_name', 'Guest Customer')
                                order_data['guest_email'] = checkout_data.get('email', '')
                                order_data['guest_phone'] = checkout_data.get('mobile_number', '')
                                order_data['guest_address'] = checkout_data.get('address', '')
                            
                            # Create the order
                            order = Order.objects.create(**order_data)
                        
                        # Create order items (only for regular cart orders)
                        if not buy_now_order:
                            if request.user.is_authenticated:
                                # Database cart for authenticated users
                                for cart_item in cart.items.all():
                                    OrderItem.objects.create(
                                        order=order,
                                        part=cart_item.part,
                                        quantity=cart_item.quantity,
                                        price=cart_item.part.price
                                    )
                                    
                                    # Update part inventory
                                    cart_item.part.quantity -= cart_item.quantity
                                    cart_item.part.save()
                            else:
                                # Session cart for guest users
                                for part_id, item_data in cart.items():
                                    try:
                                        part = Part.objects.get(id=part_id, is_active=True)
                                        quantity = item_data['quantity']
                                        
                                        # Create order item
                                        OrderItem.objects.create(
                                            order=order,
                                            part=part,
                                            quantity=quantity,
                                            price=part.price
                                        )
                                        
                                        # Update part inventory
                                        part.quantity -= quantity
                                        part.save()
                                    except Part.DoesNotExist:
                                        logger.warning(f"Part {part_id} not found for guest cart item")
                                        continue
                        
                        # Create shipping information (for both buy now and regular orders)
                        city = SaudiCity.objects.get(id=checkout_data['city_id'])
                        city_area = None
                        if checkout_data.get('city_area_id'):
                            city_area = CityArea.objects.get(id=checkout_data['city_area_id'])
                        
                        OrderShipping.objects.create(
                            order=order,
                            contact_name=checkout_data['contact_name'],
                            mobile_number=checkout_data['mobile_number'],
                            city=city,
                            city_area=city_area,
                            address=checkout_data['address'],
                            landmark=checkout_data.get('landmark', ''),
                            comments=checkout_data.get('comments', ''),
                            shipping_cost=shipping_cost
                        )
                        
                        # Apply discount if any
                        if checkout_data.get('discount_code'):
                            discount_code = DiscountCode.objects.get(code=checkout_data['discount_code'])
                            OrderDiscount.objects.create(
                                order=order,
                                discount_code=discount_code,
                                discount_amount=discount_amount
                            )
                            # Update discount usage count
                            discount_code.used_count += 1
                            discount_code.save()
                        
                        # Clear cart and session data for regular orders only
                        if not buy_now_order:
                            if request.user.is_authenticated and cart:
                                # Clear database cart for authenticated users
                                cart.clear()
                            elif not request.user.is_authenticated:
                                # Clear session cart for guest users
                                if 'cart' in request.session:
                                    del request.session['cart']
                                    request.session.modified = True
                        
                        # Clear checkout session data
                        if 'checkout_data' in request.session:
                            del request.session['checkout_data']
                        if 'applied_discount_code' in request.session:
                            del request.session['applied_discount_code']
                        
                        logger.info(f"Order completed successfully: order_id={order.id}, order_number={order.order_number}")
                        messages.success(request, f'Order #{order.order_number} placed successfully!')
                        return redirect('parts:order_confirmation', order_number=order.order_number)
                        
                except Exception as e:
                    logger.error(f"Order processing failed: {str(e)}", exc_info=True)
                    messages.error(request, f'Error processing order: {str(e)}')
                    return redirect('parts:checkout_step3')
            else:
                messages.error(request, 'Please select a valid payment method.')
                return redirect('parts:checkout_step3')
        
        context = {
            'cart': cart,
            'checkout_data': checkout_data,
            'items_total': items_total,
            'shipping_cost': shipping_cost,
            'tax_amount': tax_amount,
            'discount_amount': discount_amount,
            'grand_total': grand_total,
            'step': 3,
            'title': 'Checkout - Payment Method'
        }
        
        return render(request, 'parts/checkout/step3_payment_method.html', context)
        
    except Cart.DoesNotExist:
        messages.warning(request, 'Your cart is empty.')
        return redirect('parts:cart_view')


def order_confirmation(request, order_number):
    """Order confirmation page for both authenticated and guest users."""
    try:
        if request.user.is_authenticated:
            order = Order.objects.get(order_number=order_number, customer=request.user)
        else:
            # For guest users, check if the order was created in this session
            order = Order.objects.get(order_number=order_number)
            # Additional security: check if order was created recently and matches session
            if not order.guest_email or order.created_at < timezone.now() - timedelta(hours=24):
                messages.error(request, 'Order not found or access denied.')
                return redirect('parts:cart_view')
        
        context = {
            'order_number': order.order_number,
            'email': order.customer_email if order.customer_email else order.guest_email,
            'total': order.total_price,
            'title': f'Order Confirmation - {order.order_number}'
        }
        
        return render(request, 'parts/order_confirmation.html', context)
        
    except Order.DoesNotExist:
        messages.error(request, 'Order not found.')
        return redirect('parts:cart_view')


# AJAX Views for Checkout

def get_city_areas(request):
    """Get areas for a selected city via AJAX."""
    city_id = request.GET.get('city_id')
    
    if city_id:
        try:
            city = SaudiCity.objects.get(id=city_id, is_active=True)
            areas = city.areas.filter(is_active=True).order_by('name')
            
            areas_data = [
                {'id': area.id, 'name': area.name}
                for area in areas
            ]
            
            return JsonResponse({
                'success': True,
                'areas': areas_data
            })
        except SaudiCity.DoesNotExist:
            pass
    
    return JsonResponse({
        'success': False,
        'areas': []
    })


def verify_discount_code(request):
    """Verify discount code via AJAX."""
    
    code = request.GET.get('code', '').strip().upper()
    
    if code:
        try:
            discount_code = DiscountCode.objects.get(code=code, is_active=True)
            is_valid, message = discount_code.is_valid()
            
            if is_valid:
                return JsonResponse({
                    'success': True,
                    'valid': True,
                    'message': 'Valid discount code',
                    'discount_type': discount_code.discount_type,
                    'discount_value': str(discount_code.discount_value),
                    'minimum_order_amount': str(discount_code.minimum_order_amount)
                })
            else:
                return JsonResponse({
                    'success': True,
                    'valid': False,
                    'message': message
                })
        except DiscountCode.DoesNotExist:
            return JsonResponse({
                'success': True,
                'valid': False,
                'message': 'Invalid discount code'
            })
    
    return JsonResponse({
        'success': False,
        'valid': False,
        'message': 'Please enter a discount code'
    })


# User-specific views for My Orders and My Inventory
class MyOrdersView(LoginRequiredMixin, ListView):
    """View for customers to see their orders."""
    model = Order
    template_name = 'parts/my_orders.html'
    context_object_name = 'orders'
    paginate_by = 10
    
    def get_queryset(self):
        """Return orders for the current user."""
        return Order.objects.filter(
            customer=self.request.user
        ).select_related(
            'customer', 'shipping_info'
        ).prefetch_related(
            'items__part',
            'items__part__brand',
            'items__part__category',
            'status_history'
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'My Orders'
        
        # Order statistics
        orders = self.get_queryset()
        context['total_orders'] = orders.count()
        context['pending_orders'] = orders.filter(status='pending').count()
        context['confirmed_orders'] = orders.filter(status='confirmed').count()
        context['shipped_orders'] = orders.filter(status='shipped').count()
        context['delivered_orders'] = orders.filter(status='delivered').count()
        
        return context


class MyInventoryView(DealerAdminRequiredMixin, ListView):
    """View for dealers to manage their inventory."""
    model = Inventory
    template_name = 'parts/my_inventory.html'
    context_object_name = 'inventories'
    paginate_by = 20
    
    def get_queryset(self):
        """Return inventory for the current dealer."""
        user = self.request.user
        
        # Admin sees all inventory, dealers see only their own
        if user.role == UserRole.ADMIN or user.is_staff or user.is_superuser:
            queryset = Inventory.objects.all()
        else:
            queryset = Inventory.objects.filter(part__dealer=user)
        
        return queryset.select_related(
            'part', 'part__brand', 'part__category', 'part__dealer'
        ).annotate(
            total_orders=Count('part__order_items'),
            total_revenue=Sum(F('part__order_items__quantity') * F('part__order_items__price'))
        ).order_by('-last_restock_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'My Inventory'
        
        # Inventory statistics
        inventories = self.get_queryset()
        context['total_items'] = inventories.count()
        context['low_stock_items'] = inventories.filter(
            stock__lte=F('reorder_level')
        ).count()
        context['out_of_stock_items'] = inventories.filter(stock=0).count()
        context['total_stock_value'] = inventories.aggregate(
            total_value=Sum(F('part__price') * F('stock'))
        )['total_value'] or 0
        
        return context


class OrderDetailView(LoginRequiredMixin, DetailView):
    """Detailed view for a specific order."""
    model = Order
    template_name = 'parts/order_detail.html'
    context_object_name = 'order'
    
    def get_queryset(self):
        """Ensure users can only see their own orders (or admins see all)."""
        user = self.request.user
        
        if user.role == UserRole.ADMIN or user.is_staff or user.is_superuser:
            return Order.objects.all()
        else:
            return Order.objects.filter(customer=user)
    
    def get_object(self):
        """Get order and ensure proper permissions."""
        order = super().get_object()
        
        # Additional permission check for dealers to see orders of their parts
        user = self.request.user
        if user.role == UserRole.SELLER:
            # Check if this dealer has any parts in this order
            dealer_parts_in_order = order.items.filter(part__dealer=user).exists()
            if not dealer_parts_in_order and order.user != user:
                raise PermissionDenied("You don't have permission to view this order.")
        
        return order
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Order #{self.object.order_number}'
        
        # Get order items with related data
        context['order_items'] = self.object.items.select_related(
            'part', 'part__brand', 'part__category'
        )
        
        # Get status history
        context['status_history'] = self.object.status_history.order_by('-timestamp')
        
        return context
