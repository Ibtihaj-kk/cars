from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse
from decimal import Decimal
import uuid

User = get_user_model()


class Category(models.Model):
    """Model for automotive parts categories."""
    
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug'], name='parts_category_slug_idx'),
            models.Index(fields=['name'], name='parts_category_name_idx'),
            models.Index(fields=['created_at'], name='parts_category_created_idx'),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('parts:parts_by_category', kwargs={'category': self.slug})


class Brand(models.Model):
    """Model for automotive parts brands."""
    
    name = models.CharField(max_length=100, unique=True)
    logo = models.ImageField(upload_to='parts/brands/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Brand"
        verbose_name_plural = "Brands"
        ordering = ['name']
        indexes = [
            models.Index(fields=['name'], name='parts_brand_name_idx'),
            models.Index(fields=['is_active'], name='parts_brand_is_active_idx'),
            models.Index(fields=['is_active', 'name'], name='parts_brand_active_name_idx'),
            models.Index(fields=['created_at'], name='parts_brand_created_idx'),
        ]
    
    def __str__(self):
        return self.name


class Part(models.Model):
    """
    Comprehensive Parts Master model for automotive parts.
    
    Field Visibility:
    - USER-VISIBLE FIELDS: Fields marked with # USER-VISIBLE are shown to end users
    - VENDOR/ADMIN-ONLY FIELDS: All other fields are restricted to vendors/admins
    """
    
    # ==================== USER-VISIBLE FIELDS (Dark Green in Excel) ====================
    
    # USER-VISIBLE: Parts Number
    parts_number = models.CharField(
        max_length=50, 
        unique=True,
        blank=True,
        null=True,
        help_text="Unique parts identification number"
    )
    
    # USER-VISIBLE: Material Description (Short Text)
    material_description = models.CharField(
        max_length=200,
        help_text="Short description of the material/part"
    )
    
    # USER-VISIBLE: Material Description (Short Text) - Arabic
    material_description_ar = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Arabic description of the material/part"
    )
    
    # USER-VISIBLE: Base Unit of Measure
    base_unit_of_measure = models.CharField(
        max_length=10,
        default='EA',
        help_text="Base unit of measure (EA, KG, L, etc.)"
    )
    
    # USER-VISIBLE: Gross Weight
    gross_weight = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        blank=True,
        null=True,
        help_text="Gross weight in kg"
    )
    
    # USER-VISIBLE: Net Weight
    net_weight = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        blank=True,
        null=True,
        help_text="Net weight in kg"
    )
    
    # USER-VISIBLE: Size/dimensions
    size_dimensions = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Physical dimensions of the part"
    )
    
    # USER-VISIBLE: Manufacturer Part Number (40 digit number)
    manufacturer_part_number = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        help_text="Manufacturer's part number (up to 40 digits)"
    )
    
    # USER-VISIBLE: Manufacturer OEM Number
    manufacturer_oem_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Original Equipment Manufacturer number"
    )
    
    # ==================== VENDOR/ADMIN-ONLY FIELDS ====================
    
    # VENDOR/ADMIN-ONLY: Material Type
    material_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Type of material (FERT, HAWA, etc.)"
    )
    
    # VENDOR/ADMIN-ONLY: Plant
    plant = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Plant code"
    )
    
    # VENDOR/ADMIN-ONLY: Storage Location
    storage_location = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Storage location code"
    )
    
    # VENDOR/ADMIN-ONLY: Warehouse number
    warehouse_number = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Warehouse identification number"
    )
    
    # VENDOR/ADMIN-ONLY: Material Group
    material_group = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Material group classification"
    )
    
    # VENDOR/ADMIN-ONLY: Division
    division = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Division code"
    )
    
    # VENDOR/ADMIN-ONLY: Minimum order quantity in base unit of measure
    minimum_order_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        blank=True,
        null=True,
        help_text="Minimum order quantity"
    )
    
    # VENDOR/ADMIN-ONLY: Old material number
    old_material_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Previous material number"
    )
    
    # VENDOR/ADMIN-ONLY: Expiration "x"(XCHPF)
    expiration_xchpf = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Expiration indicator (XCHPF)"
    )
    
    # VENDOR/ADMIN-ONLY: External Material Group
    external_material_group = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="External material group classification"
    )
    
    # VENDOR/ADMIN-ONLY: ABC Indicator
    abc_indicator = models.CharField(
        max_length=1,
        choices=[('A', 'A'), ('B', 'B'), ('C', 'C')],
        blank=True,
        null=True,
        help_text="ABC analysis indicator"
    )
    
    # VENDOR/ADMIN-ONLY: Safety Stock
    safety_stock = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        blank=True,
        null=True,
        help_text="Safety stock quantity"
    )
    
    # VENDOR/ADMIN-ONLY: Minimum Safety Stock
    minimum_safety_stock = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        blank=True,
        null=True,
        help_text="Minimum safety stock quantity"
    )
    
    # VENDOR/ADMIN-ONLY: Planned Delivery Time in Days
    planned_delivery_time_days = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Planned delivery time in days"
    )
    
    # VENDOR/ADMIN-ONLY: Goods Receipt Processing Time in Days
    goods_receipt_processing_time_days = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Goods receipt processing time in days"
    )
    
    # VENDOR/ADMIN-ONLY: Valuation Class
    valuation_class = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Valuation class code"
    )
    
    # VENDOR/ADMIN-ONLY: Price Unit(PEINH)
    price_unit_peinh = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        blank=True,
        null=True,
        help_text="Price unit (PEINH)"
    )
    
    # VENDOR/ADMIN-ONLY: Moving Average Price/Periodic Unit Price
    moving_average_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Moving average price or periodic unit price"
    )
    
    # ==================== ADDITIONAL REQUIRED FIELDS ====================
    
    # Weight of unit
    weight_of_unit = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        blank=True,
        null=True,
        help_text="Weight of unit in kg"
    )
    
    # Storage Bin
    storage_bin = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Storage bin location"
    )
    
    # Price control indicator
    price_control_indicator = models.CharField(
        max_length=1,
        choices=[('S', 'Standard Price'), ('V', 'Moving Average Price')],
        blank=True,
        null=True,
        help_text="Price control indicator (S/V)"
    )
    
    # Sales Organization
    sales_organization = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Sales organization code"
    )
    
    # Distribution Channel
    distribution_channel = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Distribution channel code"
    )
    
    # Tax classification material
    tax_classification_material = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Tax classification for material"
    )
    
    # Industry sector
    industry_sector = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Industry sector code"
    )
    
    # Material Pricing Group
    material_pricing_group = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Material pricing group"
    )
    
    # Account assignment group for this material
    account_assignment_group = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Account assignment group for material"
    )
    
    # General item category group
    general_item_category_group = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="General item category group"
    )
    
    # Item category group from material master
    item_category_group = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Item category group from material master"
    )
    
    # Availability Check
    availability_check = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Availability check rule"
    )
    
    # Transportation Group
    transportation_group = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Transportation group"
    )
    
    # Loading Group
    loading_group = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Loading group"
    )
    
    # Profit Center
    profit_center = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Profit center code"
    )
    
    # Purchasing Group
    purchasing_group = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Purchasing group"
    )
    
    # MRP Group
    mrp_group = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="MRP group"
    )
    
    # MRP Type
    mrp_type = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="MRP type"
    )
    
    # Reorder Point
    reorder_point = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        blank=True,
        null=True,
        help_text="Reorder point quantity"
    )
    
    # Lot size (materials planning)
    lot_size = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        blank=True,
        null=True,
        help_text="Lot size for materials planning"
    )
    
    # MRP Controller (Materials Planner)
    mrp_controller = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="MRP controller (materials planner)"
    )
    
    # Procurement Type
    procurement_type = models.CharField(
        max_length=1,
        choices=[('F', 'In-house production'), ('E', 'External procurement'), ('B', 'Both')],
        blank=True,
        null=True,
        help_text="Procurement type"
    )
    
    # Total replenishment lead time (in workdays)
    total_replenishment_lead_time = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Total replenishment lead time in workdays"
    )
    
    # Forecast Model
    forecast_model = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Forecast model"
    )
    
    # Period Indicator
    period_indicator = models.CharField(
        max_length=1,
        choices=[('D', 'Day'), ('W', 'Week'), ('M', 'Month'), ('Y', 'Year')],
        blank=True,
        null=True,
        help_text="Period indicator for forecasting"
    )
    
    # Historical periods
    historical_periods = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Number of historical periods"
    )
    
    # Forecast periods
    forecast_periods = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Number of forecast periods"
    )
    
    # Initialization indicator
    initialization_indicator = models.CharField(
        max_length=1,
        choices=[('X', 'Initialize'), (' ', 'Do not initialize')],
        blank=True,
        null=True,
        help_text="Initialization indicator"
    )
    
    # Valuation Category
    valuation_category = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Valuation category"
    )
    
    # Standard price
    standard_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Standard price"
    )
    
    # ==================== SYSTEM FIELDS ====================
    
    # Relationships
    dealer = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='parts'
    )
    # Vendor relationship through business partners
    vendor = models.ForeignKey(
        'business_partners.BusinessPartner',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='vendor_parts',
        help_text="Vendor who supplies this part"
    )
    category = models.ForeignKey(
        Category, 
        on_delete=models.CASCADE,
        related_name='parts'
    )
    brand = models.ForeignKey(
        Brand, 
        on_delete=models.CASCADE,
        related_name='parts'
    )
    
    # Legacy fields for backward compatibility
    name = models.CharField(max_length=200, blank=True, help_text="Legacy name field")
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    description = models.TextField(blank=True, help_text="Legacy description field")
    sku = models.CharField(max_length=50, blank=True, help_text="Legacy SKU field")
    
    # Pricing and Inventory
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        blank=True,
        null=True,
        help_text="Selling price"
    )
    quantity = models.PositiveIntegerField(default=0, help_text="Available quantity")
    
    # Media
    image = models.ImageField(upload_to='parts/images/', blank=True, null=True)
    image_url = models.URLField(blank=True, null=True, help_text="Alternative to image upload")
    
    # Additional Details
    weight = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    dimensions = models.CharField(max_length=100, blank=True, null=True)
    warranty_period = models.PositiveIntegerField(
        blank=True, 
        null=True, 
        help_text="Warranty period in months"
    )
    
    # Vehicle Compatibility
    vehicle_variants = models.ManyToManyField(
        'vehicles.VehicleVariant',
        blank=True,
        related_name='parts',
        help_text="Compatible vehicle variants for this part"
    )
    
    # Status and Metadata
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Part"
        verbose_name_plural = "Parts"
        ordering = ['-created_at']
        indexes = [
            # Primary identification indexes
            models.Index(fields=['parts_number'], name='parts_part_parts_number_idx'),
            models.Index(fields=['sku'], name='parts_part_sku_idx'),
            models.Index(fields=['slug'], name='parts_part_slug_idx'),
            
            # Relationship indexes
            models.Index(fields=['category'], name='parts_part_category_idx'),
            models.Index(fields=['brand'], name='parts_part_brand_idx'),
            models.Index(fields=['dealer'], name='parts_part_dealer_idx'),
            models.Index(fields=['vendor'], name='parts_part_vendor_idx'),
            
            # Status and filtering indexes
            models.Index(fields=['is_active'], name='parts_part_is_active_idx'),
            models.Index(fields=['is_featured'], name='parts_part_is_featured_idx'),
            models.Index(fields=['price'], name='parts_part_price_idx'),
            models.Index(fields=['quantity'], name='parts_part_quantity_idx'),
            models.Index(fields=['view_count'], name='parts_part_view_count_idx'),
            models.Index(fields=['created_at'], name='parts_part_created_at_idx'),
            
            # Composite indexes for common query patterns
            models.Index(fields=['is_active', '-created_at'], name='parts_part_active_created_idx'),
            models.Index(fields=['category', 'brand'], name='parts_part_cat_brand_idx'),
            models.Index(fields=['category', 'is_active'], name='parts_part_cat_active_idx'),
            models.Index(fields=['brand', 'is_active'], name='parts_part_brand_active_idx'),
            models.Index(fields=['dealer', 'is_active'], name='parts_part_dealer_active_idx'),
            models.Index(fields=['vendor', 'is_active'], name='parts_part_vendor_active_idx'),
            models.Index(fields=['is_active', 'price'], name='parts_part_active_price_idx'),
            models.Index(fields=['is_active', 'quantity'], name='parts_part_active_qty_idx'),
            models.Index(fields=['is_featured', 'is_active'], name='parts_part_featured_active_idx'),
            models.Index(fields=['category', 'price'], name='parts_part_cat_price_idx'),
            models.Index(fields=['brand', 'price'], name='parts_part_brand_price_idx'),
            
            # Search optimization indexes
            models.Index(fields=['material_description'], name='parts_part_material_desc_idx'),
            models.Index(fields=['manufacturer_part_number'], name='parts_part_mfg_part_num_idx'),
            models.Index(fields=['manufacturer_oem_number'], name='parts_part_mfg_oem_num_idx'),
            
            # Vendor/Admin indexes
            models.Index(fields=['material_type'], name='parts_part_material_type_idx'),
            models.Index(fields=['plant'], name='parts_part_plant_idx'),
            models.Index(fields=['material_group'], name='parts_part_material_group_idx'),
        ]
    
    def __str__(self):
        return f"{self.parts_number} - {self.material_description}"
    
    def save(self, *args, **kwargs):
        # Generate slug from parts_number and material_description
        if not self.slug:
            base_slug = slugify(f"{self.parts_number}-{self.material_description}")
            self.slug = base_slug
            counter = 1
            while Part.objects.filter(slug=self.slug).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        
        # Backward compatibility: populate legacy fields
        if not self.name and self.material_description:
            self.name = self.material_description
        if not self.sku and self.parts_number:
            self.sku = self.parts_number
        if not self.description and self.material_description:
            self.description = self.material_description
        
        super().save(*args, **kwargs)
        
        # Invalidate cache after saving
        try:
            from .cache import invalidate_part_cache
            invalidate_part_cache(self.id)
        except ImportError:
            # Cache module not available, skip invalidation
            pass
    
    def get_absolute_url(self):
        return reverse('parts:part_detail', kwargs={'pk': self.pk})
    
    @property
    def is_in_stock(self):
        return self.quantity > 0
    
    @property
    def average_rating(self):
        reviews = self.reviews.all()
        if reviews:
            return sum(review.rating for review in reviews) / len(reviews)
        return 0
    
    @property
    def review_count(self):
        return self.reviews.count()
    
    def user_visible_fields(self):
        """
        Returns a dictionary containing only user-visible fields.
        This method ensures field visibility separation between users and vendors/admins.
        """
        return {
            'id': self.id,
            'parts_number': self.parts_number,
            'material_description': self.material_description,
            'material_description_ar': self.material_description_ar,
            'base_unit_of_measure': self.base_unit_of_measure,
            'gross_weight': self.gross_weight,
            'net_weight': self.net_weight,
            'size_dimensions': self.size_dimensions,
            'manufacturer_part_number': self.manufacturer_part_number,
            'manufacturer_oem_number': self.manufacturer_oem_number,
            
            # Additional user-relevant fields
            'category': {
                'id': self.category.id,
                'name': self.category.name,
                'slug': self.category.slug,
            } if self.category else None,
            'brand': {
                'id': self.brand.id,
                'name': self.brand.name,
                'logo': self.brand.logo.url if self.brand.logo else None,
            } if self.brand else None,
            'price': self.price,
            'quantity': self.quantity,
            'image': self.image.url if self.image else self.image_url,
            'warranty_period': self.warranty_period,
            'is_in_stock': self.is_in_stock,
            'average_rating': self.average_rating,
            'review_count': self.review_count,
            'created_at': self.created_at,
        }
    
    def vendor_admin_fields(self):
        """
        Returns a dictionary containing all fields for vendor/admin access.
        This includes both user-visible and vendor/admin-only fields.
        """
        user_fields = self.user_visible_fields()
        
        # Add vendor/admin-only fields
        vendor_admin_only = {
            'material_type': self.material_type,
            'plant': self.plant,
            'storage_location': self.storage_location,
            'warehouse_number': self.warehouse_number,
            'material_group': self.material_group,
            'division': self.division,
            'minimum_order_quantity': self.minimum_order_quantity,
            'old_material_number': self.old_material_number,
            'expiration_xchpf': self.expiration_xchpf,
            'external_material_group': self.external_material_group,
            'abc_indicator': self.abc_indicator,
            'safety_stock': self.safety_stock,
            'minimum_safety_stock': self.minimum_safety_stock,
            'planned_delivery_time_days': self.planned_delivery_time_days,
            'goods_receipt_processing_time_days': self.goods_receipt_processing_time_days,
            'valuation_class': self.valuation_class,
            'price_unit_peinh': self.price_unit_peinh,
            'moving_average_price': self.moving_average_price,
            
            # System fields
            'dealer': {
                'id': self.dealer.id,
                'email': self.dealer.email,
            } if self.dealer else None,
            'vendor': {
                'id': self.vendor.id,
                'name': self.vendor.name,
                'business_partner_id': self.vendor.business_partner_id,
            } if self.vendor else None,
            'slug': self.slug,
            'sku': self.sku,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'is_featured': self.is_featured,
            'view_count': self.view_count,
            'updated_at': self.updated_at,
        }
        
        # Merge user fields with vendor/admin fields
        return {**user_fields, **vendor_admin_only}
    
    def get_fields_for_user(self, user):
        """
        Returns appropriate fields based on user permissions and ownership.
        
        Args:
            user: The requesting user
            
        Returns:
            dict: Categorized fields accessible to the user with labels and values
        """
        # Determine which fields the user can access
        if not user or not user.is_authenticated:
            accessible_fields = self.get_user_visible_field_names()
        elif user.is_staff or user.is_superuser:
            accessible_fields = self.get_vendor_admin_field_names()
        else:
            # Check if user is the vendor/dealer for this part
            is_part_owner = False
            
            # Check if user is the dealer
            if self.dealer and self.dealer == user:
                is_part_owner = True
            
            # Check if user is associated with the vendor business partner
            if self.vendor and hasattr(user, 'business_partners'):
                try:
                    business_partner = user.business_partners.first()
                    if business_partner and business_partner == self.vendor:
                        is_part_owner = True
                except:
                    pass
            
            # If user owns this part, return all fields
            if is_part_owner:
                accessible_fields = self.get_vendor_admin_field_names()
            else:
                accessible_fields = self.get_user_visible_field_names()
        
        # Field categorization and labels
        field_categories = {
            # Identification fields
            'parts_number': {'category': 'identification', 'label': 'Parts Number'},
            'manufacturer_part_number': {'category': 'identification', 'label': 'Manufacturer Part Number'},
            'manufacturer_oem_number': {'category': 'identification', 'label': 'Manufacturer OEM Number'},
            'old_material_number': {'category': 'identification', 'label': 'Old Material Number'},
            'material_description': {'category': 'identification', 'label': 'Material Description'},
            'material_description_ar': {'category': 'identification', 'label': 'Material Description (Arabic)'},
            
            # Classification fields
            'category': {'category': 'classification', 'label': 'Category'},
            'brand': {'category': 'classification', 'label': 'Brand'},
            'base_unit_of_measure': {'category': 'classification', 'label': 'Base Unit of Measure'},
            'material_type': {'category': 'classification', 'label': 'Material Type'},
            'material_group': {'category': 'classification', 'label': 'Material Group'},
            'external_material_group': {'category': 'classification', 'label': 'External Material Group'},
            
            # Specifications fields
            'gross_weight': {'category': 'specifications', 'label': 'Gross Weight (kg)'},
            'net_weight': {'category': 'specifications', 'label': 'Net Weight (kg)'},
            'size_dimensions': {'category': 'specifications', 'label': 'Size Dimensions'},
            'warranty_period': {'category': 'specifications', 'label': 'Warranty Period (months)'},
            'expiration_xchpf': {'category': 'specifications', 'label': 'Expiration XCHPF'},
            
            # Pricing fields
            'price': {'category': 'pricing', 'label': 'Current Price'},
            'moving_average_price': {'category': 'pricing', 'label': 'Moving Average Price'},
            'price_unit_peinh': {'category': 'pricing', 'label': 'Price Unit (PEINH)'},
            
            # Inventory fields
            'quantity': {'category': 'inventory', 'label': 'Current Stock'},
            'safety_stock': {'category': 'inventory', 'label': 'Safety Stock'},
            'minimum_safety_stock': {'category': 'inventory', 'label': 'Minimum Safety Stock'},
            'minimum_order_quantity': {'category': 'inventory', 'label': 'Minimum Order Quantity'},
            'planned_delivery_time_days': {'category': 'inventory', 'label': 'Planned Delivery Time (days)'},
            'goods_receipt_processing_time_days': {'category': 'inventory', 'label': 'Goods Receipt Processing Time (days)'},
            
            # Vendor fields
            'plant': {'category': 'vendor', 'label': 'Plant'},
            'storage_location': {'category': 'vendor', 'label': 'Storage Location'},
            'warehouse_number': {'category': 'vendor', 'label': 'Warehouse Number'},
            'division': {'category': 'vendor', 'label': 'Division'},
            'abc_indicator': {'category': 'vendor', 'label': 'ABC Indicator'},
            'valuation_class': {'category': 'vendor', 'label': 'Valuation Class'},
            
            # Admin fields
            'is_active': {'category': 'admin', 'label': 'Active Status'},
            'is_featured': {'category': 'admin', 'label': 'Featured Status'},
            'created_at': {'category': 'admin', 'label': 'Created At'},
            'updated_at': {'category': 'admin', 'label': 'Updated At'},
        }
        
        # Build the result dictionary with categorized fields
        result = {}
        for field_name in accessible_fields:
            if field_name in field_categories:
                field_info = field_categories[field_name]
                
                # Get the field value
                try:
                    if hasattr(self, field_name):
                        value = getattr(self, field_name)
                        
                        # Format specific field types
                        if field_name in ['category', 'brand'] and value:
                            value = value.name
                        elif field_name in ['price', 'moving_average_price'] and value:
                            value = f"${value:.2f}"
                        elif field_name in ['gross_weight', 'net_weight'] and value:
                            value = f"{value} kg"
                        elif field_name in ['warranty_period'] and value:
                            value = f"{value} months"
                        elif field_name in ['planned_delivery_time_days', 'goods_receipt_processing_time_days'] and value:
                            value = f"{value} days"
                        elif field_name in ['is_active', 'is_featured']:
                            value = "Yes" if value else "No"
                        elif field_name in ['created_at', 'updated_at'] and value:
                            value = value.strftime("%Y-%m-%d %H:%M")
                        
                        result[field_name] = {
                            'category': field_info['category'],
                            'label': field_info['label'],
                            'value': value
                        }
                except:
                    # Skip fields that can't be accessed
                    continue
        
        return result
    
    def can_user_edit(self, user):
        """
        Check if user can edit this part.
        
        Args:
            user: The requesting user
            
        Returns:
            bool: True if user can edit this part
        """
        if not user or not user.is_authenticated:
            return False
        
        # Admin/staff can edit all parts
        if user.is_staff or user.is_superuser:
            return True
        
        # Check if user is the dealer
        if self.dealer and self.dealer == user:
            return True
        
        # Check if user is associated with the vendor business partner
        if self.vendor and hasattr(user, 'business_partners'):
            try:
                business_partner = user.business_partners.first()
                if business_partner and business_partner == self.vendor:
                    return True
            except:
                pass
        
        return False
    
    @classmethod
    def get_user_visible_field_names(cls):
        """
        Returns a list of field names that are visible to end users.
        Useful for serializers and API filtering.
        """
        return [
            'id', 'parts_number', 'material_description', 'material_description_ar',
            'base_unit_of_measure', 'gross_weight', 'net_weight', 'size_dimensions',
            'manufacturer_part_number', 'manufacturer_oem_number', 'category', 'brand',
            'price', 'quantity', 'image', 'image_url', 'warranty_period', 'created_at'
        ]
    
    @classmethod
    def get_vendor_admin_field_names(cls):
        """
        Returns a list of all field names accessible to vendors and admins.
        """
        user_fields = cls.get_user_visible_field_names()
        vendor_admin_only = [
            'material_type', 'plant', 'storage_location', 'warehouse_number',
            'material_group', 'division', 'minimum_order_quantity', 'old_material_number',
            'expiration_xchpf', 'external_material_group', 'abc_indicator', 'safety_stock',
            'minimum_safety_stock', 'planned_delivery_time_days', 'goods_receipt_processing_time_days',
            'valuation_class', 'price_unit_peinh', 'moving_average_price', 'dealer', 'vendor',
            'slug', 'sku', 'name', 'description', 'is_active', 'is_featured',
            'view_count', 'updated_at'
        ]
        return user_fields + vendor_admin_only


class Inventory(models.Model):
    """Model for tracking part inventory levels."""
    
    part = models.OneToOneField(
        Part, 
        on_delete=models.CASCADE,
        related_name='inventory'
    )
    stock = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(
        default=10,
        help_text="Minimum stock level before reordering"
    )
    max_stock_level = models.PositiveIntegerField(
        blank=True, 
        null=True,
        help_text="Maximum stock level"
    )
    last_restock_date = models.DateTimeField(blank=True, null=True)
    supplier_info = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Inventory"
        verbose_name_plural = "Inventories"
    
    def __str__(self):
        return f"{self.part.name} - Stock: {self.stock}"
    
    @property
    def needs_reorder(self):
        return self.stock <= self.reorder_level
    
    @property
    def stock_status(self):
        if self.stock == 0:
            return "Out of Stock"
        elif self.needs_reorder:
            return "Low Stock"
        else:
            return "In Stock"


class Order(models.Model):
    """Model for customer orders."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    # Order Identification
    order_number = models.CharField(max_length=20, unique=True, blank=True)
    
    # Customer Information
    customer = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='orders'
    )
    
    # Guest Customer Information
    guest_name = models.CharField(max_length=200, blank=True, null=True)
    guest_email = models.EmailField(blank=True, null=True)
    guest_phone = models.CharField(max_length=20, blank=True, null=True)
    guest_address = models.TextField(blank=True, null=True)
    
    # Order Details
    total_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    shipping_cost = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    tax_amount = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    
    # Status and Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    shipped_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        customer_name = self.customer.email if self.customer else self.guest_name
        return f"Order {self.order_number} - {customer_name}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        """Generate a unique order number."""
        import random
        import string
        while True:
            order_number = 'ORD' + ''.join(random.choices(string.digits, k=7))
            if not Order.objects.filter(order_number=order_number).exists():
                return order_number
    
    @property
    def is_guest_order(self):
        return self.customer is None
    
    @property
    def customer_name(self):
        if self.customer:
            return f"{self.customer.first_name} {self.customer.last_name}".strip()
        return self.guest_name
    
    @property
    def customer_email(self):
        return self.customer.email if self.customer else self.guest_email
    
    def update_status(self, new_status, changed_by=None, change_reason=None, notes=None, request=None):
        """Update order status with audit logging."""
        from django.utils import timezone
        
        if new_status not in dict(self.STATUS_CHOICES):
            raise ValueError(f"Invalid status: {new_status}")
        
        previous_status = self.status
        
        # Update timestamps based on status
        if new_status == 'shipped' and not self.shipped_at:
            self.shipped_at = timezone.now()
        elif new_status == 'delivered' and not self.delivered_at:
            self.delivered_at = timezone.now()
        
        # Update the status
        self.status = new_status
        self.save()
        
        # Create audit log entry
        audit_data = {
            'order': self,
            'previous_status': previous_status,
            'new_status': new_status,
            'changed_by': changed_by,
            'change_reason': change_reason,
            'notes': notes,
        }
        
        # Add request information if available
        if request:
            audit_data['ip_address'] = self.get_client_ip(request)
            audit_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        
        OrderStatusHistory.objects.create(**audit_data)
        
        return True
    
    def get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def deduct_inventory(self):
        """Deduct inventory quantities for all items in this order."""
        from django.db import transaction
        
        with transaction.atomic():
            for order_item in self.items.all():
                inventory = order_item.part.inventory
                
                if inventory.quantity < order_item.quantity:
                    raise ValueError(
                        f"Insufficient stock for {order_item.part.name}. "
                        f"Available: {inventory.quantity}, Required: {order_item.quantity}"
                    )
                
                # Create inventory transaction record
                InventoryTransaction.objects.create(
                    inventory=inventory,
                    transaction_type='sale',
                    quantity_change=-order_item.quantity,
                    previous_quantity=inventory.quantity,
                    new_quantity=inventory.quantity - order_item.quantity,
                    order=self,
                    order_item=order_item,
                    notes=f"Stock deducted for order {self.order_number}"
                )
                
                # Update inventory quantity
                inventory.quantity -= order_item.quantity
                inventory.save()
    
    def check_stock_availability(self):
        """Check if all items in the order have sufficient stock."""
        for order_item in self.items.all():
            inventory = order_item.part.inventory
            if inventory.quantity < order_item.quantity:
                return False, f"Insufficient stock for {order_item.part.name}"
        return True, "All items are in stock"
    
    def restore_inventory(self):
        """Restore inventory quantities (e.g., for cancelled orders)."""
        from django.db import transaction
        
        with transaction.atomic():
            for order_item in self.items.all():
                inventory = order_item.part.inventory
                
                # Create inventory transaction record
                InventoryTransaction.objects.create(
                    inventory=inventory,
                    transaction_type='return',
                    quantity_change=order_item.quantity,
                    previous_quantity=inventory.quantity,
                    new_quantity=inventory.quantity + order_item.quantity,
                    order=self,
                    order_item=order_item,
                    notes=f"Stock restored for cancelled order {self.order_number}"
                )
                
                # Update inventory quantity
                inventory.quantity += order_item.quantity
                inventory.save()


class OrderItem(models.Model):
    """Model for individual items in an order."""
    
    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE,
        related_name='items'
    )
    part = models.ForeignKey(
        Part, 
        on_delete=models.CASCADE,
        related_name='order_items'
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Price at the time of order"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"
        unique_together = ['order', 'part']
    
    def __str__(self):
        return f"{self.part.name} x {self.quantity}"
    
    @property
    def total_price(self):
        return self.quantity * self.price


class Review(models.Model):
    """Model for part reviews and ratings."""
    
    part = models.ForeignKey(
        Part, 
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='part_reviews'
    )
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True, null=True)
    is_verified_purchase = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Review"
        verbose_name_plural = "Reviews"
        unique_together = ['part', 'user']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.part.name} - {self.rating}/5 by {self.user.email}"


class BulkUploadLog(models.Model):
    """Model for tracking bulk upload operations."""
    
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('partial', 'Partially Completed'),
    ]
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='upload_logs'
    )
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    
    # Upload Statistics
    total_records = models.PositiveIntegerField(default=0)
    successful_records = models.PositiveIntegerField(default=0)
    failed_records = models.PositiveIntegerField(default=0)
    
    # Status and Logs
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')
    error_log = models.TextField(blank=True, null=True)
    success_message = models.TextField(blank=True, null=True)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Bulk Upload Log"
        verbose_name_plural = "Bulk Upload Logs"
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.file_name} - {self.status} ({self.uploaded_at})"
    
    @property
    def success_rate(self):
        if self.total_records > 0:
            return (self.successful_records / self.total_records) * 100
        return 0


class IntegrationSource(models.Model):
    """Model for external API integrations."""
    
    dealer = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='integrations'
    )
    name = models.CharField(max_length=100)
    api_url = models.URLField()
    api_key = models.CharField(max_length=255)
    
    # Configuration
    is_active = models.BooleanField(default=True)
    sync_frequency = models.PositiveIntegerField(
        default=60,
        help_text="Sync frequency in minutes"
    )
    last_sync = models.DateTimeField(blank=True, null=True)
    
    # Authentication
    auth_type = models.CharField(
        max_length=20,
        choices=[
            ('api_key', 'API Key'),
            ('oauth', 'OAuth'),
            ('basic', 'Basic Auth'),
        ],
        default='api_key'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Integration Source"
        verbose_name_plural = "Integration Sources"
        unique_together = ['dealer', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.dealer.email}"


class OrderStatusHistory(models.Model):
    """Model for tracking order status changes and audit logging."""
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    previous_status = models.CharField(
        max_length=20,
        choices=Order.STATUS_CHOICES,
        blank=True,
        null=True
    )
    new_status = models.CharField(
        max_length=20,
        choices=Order.STATUS_CHOICES
    )
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_status_changes'
    )
    change_reason = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Additional tracking fields
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Order Status History"
        verbose_name_plural = "Order Status Histories"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['order', '-timestamp']),
            models.Index(fields=['changed_by', '-timestamp']),
            models.Index(fields=['new_status', '-timestamp']),
        ]
    
    def __str__(self):
        return f"Order {self.order.order_number}: {self.previous_status} → {self.new_status}"
    
    @property
    def status_change_display(self):
        """Human-readable status change description."""
        if self.previous_status:
            return f"{self.get_previous_status_display()} → {self.get_new_status_display()}"
        else:
            return f"Created with status: {self.get_new_status_display()}"


class InventoryTransaction(models.Model):
    """Model for tracking inventory changes and stock movements."""
    
    TRANSACTION_TYPES = [
        ('sale', 'Sale'),
        ('restock', 'Restock'),
        ('adjustment', 'Adjustment'),
        ('return', 'Return'),
        ('damage', 'Damage/Loss'),
    ]
    
    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES
    )
    quantity_change = models.IntegerField(
        help_text="Positive for increases, negative for decreases"
    )
    previous_quantity = models.PositiveIntegerField()
    new_quantity = models.PositiveIntegerField()
    
    # Reference to related order if applicable
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_transactions'
    )
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_transactions'
    )
    
    # Tracking information
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_transactions'
    )
    notes = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Inventory Transaction"
        verbose_name_plural = "Inventory Transactions"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['inventory', '-timestamp']),
            models.Index(fields=['transaction_type', '-timestamp']),
            models.Index(fields=['order', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.inventory.part.name}: {self.quantity_change:+d} ({self.get_transaction_type_display()})"
    
    def save(self, *args, **kwargs):
        # Ensure new_quantity is calculated correctly
        if self.new_quantity is None:
            self.new_quantity = max(0, self.previous_quantity + self.quantity_change)
        super().save(*args, **kwargs)


class Cart(models.Model):
    """Model for user shopping cart."""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='cart'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Cart"
        verbose_name_plural = "Carts"
    
    def __str__(self):
        return f"Cart for {self.user.email}"
    
    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())
    
    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())
    
    def clear(self):
        """Clear all items from cart."""
        self.items.all().delete()


class CartItem(models.Model):
    """Model for items in shopping cart."""
    
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    part = models.ForeignKey(
        Part,
        on_delete=models.CASCADE,
        related_name='cart_items'
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        unique_together = ('cart', 'part')
        ordering = ['-added_at']
    
    def __str__(self):
        return f"{self.quantity}x {self.part.name} in {self.cart.user.email}'s cart"
    
    @property
    def total_price(self):
        return self.part.price * self.quantity
    
    def clean(self):
        """Validate that quantity doesn't exceed available stock."""
        if self.quantity > self.part.quantity:
            from django.core.exceptions import ValidationError
            raise ValidationError(f"Only {self.part.quantity} items available in stock.")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class DiscountCode(models.Model):
    """Model for discount codes and coupons."""
    
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    
    code = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=200, blank=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, default='percentage')
    discount_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    minimum_order_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    maximum_discount_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True
    )
    usage_limit = models.PositiveIntegerField(blank=True, null=True)
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Discount Code"
        verbose_name_plural = "Discount Codes"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.code} - {self.discount_value}{'%' if self.discount_type == 'percentage' else ' SAR'}"
    
    def is_valid(self):
        """Check if discount code is valid."""
        from django.utils import timezone
        now = timezone.now()
        
        if not self.is_active:
            return False, "Discount code is not active"
        
        if now < self.valid_from:
            return False, "Discount code is not yet valid"
        
        if now > self.valid_until:
            return False, "Discount code has expired"
        
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False, "Discount code usage limit reached"
        
        return True, "Valid"
    
    def calculate_discount(self, order_amount):
        """Calculate discount amount for given order amount."""
        if order_amount < self.minimum_order_amount:
            return Decimal('0.00')
        
        if self.discount_type == 'percentage':
            discount = order_amount * (self.discount_value / 100)
        else:
            discount = self.discount_value
        
        if self.maximum_discount_amount:
            discount = min(discount, self.maximum_discount_amount)
        
        return discount


class SaudiCity(models.Model):
    """Model for Saudi Arabian cities."""
    
    name = models.CharField(max_length=100, unique=True)
    name_ar = models.CharField(max_length=100, blank=True, null=True)
    region = models.CharField(max_length=100)
    region_ar = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Saudi City"
        verbose_name_plural = "Saudi Cities"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.region})"


class CityArea(models.Model):
    """Model for city areas/districts."""
    
    city = models.ForeignKey(
        SaudiCity,
        on_delete=models.CASCADE,
        related_name='areas'
    )
    name = models.CharField(max_length=100)
    name_ar = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "City Area"
        verbose_name_plural = "City Areas"
        unique_together = ['city', 'name']
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name}, {self.city.name}"


class ShippingRate(models.Model):
    """Model for shipping rates based on location."""
    
    city = models.ForeignKey(
        SaudiCity,
        on_delete=models.CASCADE,
        related_name='shipping_rates'
    )
    base_rate = models.DecimalField(
        max_digits=8, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    per_kg_rate = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    free_shipping_threshold = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True
    )
    estimated_delivery_days = models.PositiveIntegerField(default=3)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Shipping Rate"
        verbose_name_plural = "Shipping Rates"
        unique_together = ['city']
    
    def __str__(self):
        return f"{self.city.name} - {self.base_rate} SAR"
    
    def calculate_shipping_cost(self, order_amount, total_weight=None):
        """Calculate shipping cost for given order."""
        if self.free_shipping_threshold and order_amount >= self.free_shipping_threshold:
            return Decimal('0.00')
        
        cost = self.base_rate
        if total_weight and self.per_kg_rate:
            cost += total_weight * self.per_kg_rate
        
        return cost


class OrderShipping(models.Model):
    """Model for order shipping information."""
    
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='shipping_info'
    )
    
    # Contact Information
    contact_name = models.CharField(max_length=200)
    mobile_number = models.CharField(max_length=20)
    mobile_verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=6, blank=True, null=True)
    verification_sent_at = models.DateTimeField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    
    # Shipping Address
    city = models.ForeignKey(
        SaudiCity,
        on_delete=models.PROTECT,
        related_name='order_shipments'
    )
    city_area = models.ForeignKey(
        CityArea,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='order_shipments'
    )
    address = models.TextField(help_text="House No/Building No, Street, Area")
    landmark = models.CharField(max_length=200, blank=True, null=True)
    
    # Shipping Details
    shipping_cost = models.DecimalField(
        max_digits=8, 
        decimal_places=2,
        default=Decimal('0.00')
    )
    estimated_delivery_date = models.DateField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Order Shipping"
        verbose_name_plural = "Order Shipping"
    
    def __str__(self):
        return f"Shipping for Order {self.order.order_number}"


class OrderDiscount(models.Model):
    """Model for applied discounts on orders."""
    
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='discount_info'
    )
    discount_code = models.ForeignKey(
        DiscountCode,
        on_delete=models.PROTECT,
        related_name='order_applications'
    )
    discount_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    applied_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Order Discount"
        verbose_name_plural = "Order Discounts"
    
    def __str__(self):
        return f"{self.discount_code.code} applied to Order {self.order.order_number}"
