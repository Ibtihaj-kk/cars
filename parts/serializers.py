"""
Serializers for Parts app with field visibility separation.
"""
from rest_framework import serializers
from .models import Part, Category, Brand, Inventory, Order, OrderItem, Review


class DynamicPartSerializer(serializers.ModelSerializer):
    """
    Dynamic serializer that adjusts fields based on user permissions and part ownership.
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    dealer_name = serializers.CharField(source='dealer.email', read_only=True)
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    
    class Meta:
        model = Part
        fields = '__all__'  # We'll dynamically filter fields
    
    def __init__(self, *args, **kwargs):
        # Extract user from context
        self.user = kwargs.get('context', {}).get('request', {}).user if hasattr(kwargs.get('context', {}).get('request', {}), 'user') else None
        super().__init__(*args, **kwargs)
        
        # If we have an instance and user, filter fields based on permissions
        if self.instance and self.user:
            if hasattr(self.instance, '__iter__'):
                # Handle queryset - use first item to determine fields
                if self.instance:
                    sample_part = self.instance[0] if len(self.instance) > 0 else None
                    if sample_part:
                        allowed_fields = sample_part.get_fields_for_user(self.user).keys()
                        self._filter_fields(allowed_fields)
            else:
                # Handle single instance
                allowed_fields = self.instance.get_fields_for_user(self.user).keys()
                self._filter_fields(allowed_fields)
    
    def _filter_fields(self, allowed_fields):
        """Filter serializer fields based on allowed fields."""
        # Always include these meta fields
        meta_fields = {'id', 'category_name', 'brand_name', 'dealer_name', 'vendor_name'}
        allowed_fields = set(allowed_fields) | meta_fields
        
        # Remove fields not in allowed list
        existing_fields = set(self.fields.keys())
        fields_to_remove = existing_fields - allowed_fields
        
        for field_name in fields_to_remove:
            self.fields.pop(field_name, None)
    
    def to_representation(self, instance):
        """Override to add computed fields and ensure field visibility."""
        # If we have a user and instance, check permissions again
        if self.user and instance:
            allowed_fields = instance.get_fields_for_user(self.user)
            # Filter the data to only include allowed fields
            data = {}
            for field_name, field_value in allowed_fields.items():
                if field_name in self.fields:
                    data[field_name] = field_value
            
            # Add meta fields
            data['id'] = instance.id
            if hasattr(instance, 'category') and instance.category:
                data['category_name'] = instance.category.name
            if hasattr(instance, 'brand') and instance.brand:
                data['brand_name'] = instance.brand.name
            if hasattr(instance, 'dealer') and instance.dealer:
                data['dealer_name'] = instance.dealer.email
            if hasattr(instance, 'vendor') and instance.vendor:
                data['vendor_name'] = instance.vendor.name
            
            # Add computed fields
            data['is_in_stock'] = instance.is_in_stock
            data['average_rating'] = instance.average_rating
            data['review_count'] = instance.review_count
            data['can_edit'] = instance.can_user_edit(self.user)
            
            return data
        else:
            # Fallback to default behavior
            return super().to_representation(instance)


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model."""
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'parent', 'is_active']


class BrandSerializer(serializers.ModelSerializer):
    """Serializer for Brand model."""
    
    class Meta:
        model = Brand
        fields = ['id', 'name', 'slug', 'description', 'logo', 'website', 'is_active']


class PartUserSerializer(serializers.ModelSerializer):
    """
    Serializer for Part model - USER VIEW
    Only includes user-visible fields (Dark Green fields from Excel).
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    
    class Meta:
        model = Part
        fields = [
            # Core identification
            'id',
            'parts_number',
            'sku',  # Legacy field for compatibility
            
            # USER-VISIBLE FIELDS (Dark Green in Excel)
            'material_description',
            'material_description_ar',
            'base_unit_of_measure',
            'gross_weight',
            'net_weight',
            'size_dimensions',
            'manufacturer_part_number',
            'manufacturer_oem_number',
            
            # Additional user-friendly fields
            'name',  # Legacy field for compatibility
            'description',  # Legacy field for compatibility
            'price',
            'image',
            'image_url',
            'warranty_period',
            'is_active',
            'is_featured',
            'category_name',
            'brand_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'category_name', 'brand_name']
    
    def to_representation(self, instance):
        """Override to ensure only user-visible fields are returned."""
        data = super().to_representation(instance)
        
        # Add computed fields
        data['is_in_stock'] = instance.is_in_stock
        data['average_rating'] = instance.average_rating
        data['review_count'] = instance.review_count
        
        return data


class PartVendorAdminSerializer(serializers.ModelSerializer):
    """
    Serializer for Part model - VENDOR/ADMIN VIEW
    Includes ALL fields for comprehensive management.
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    dealer_name = serializers.CharField(source='dealer.email', read_only=True)
    
    class Meta:
        model = Part
        fields = [
            # Core identification
            'id',
            'parts_number',
            'sku',
            'slug',
            'name',
            'description',
            
            # USER-VISIBLE FIELDS (Dark Green in Excel)
            'material_description',
            'material_description_ar',
            'base_unit_of_measure',
            'gross_weight',
            'net_weight',
            'size_dimensions',
            'manufacturer_part_number',
            'manufacturer_oem_number',
            
            # VENDOR/ADMIN-ONLY FIELDS (All other Excel fields)
            'material_type',
            'plant',
            'storage_location',
            'warehouse_number',
            'material_group',
            'division',
            'minimum_order_quantity',
            'old_material_number',
            'expiration_xchpf',
            'external_material_group',
            'abc_indicator',
            'safety_stock',
            'minimum_safety_stock',
            'planned_delivery_time_days',
            'goods_receipt_processing_time_days',
            'valuation_class',
            'price_unit_peinh',
            'moving_average_price',
            
            # Legacy and additional fields
            'category',
            'brand',
            'dealer',
            'price',
            'quantity',
            'image',
            'image_url',
            'weight',
            'dimensions',
            'warranty_period',
            'is_active',
            'is_featured',
            'view_count',
            'created_at',
            'updated_at',
            
            # Related field names for display
            'category_name',
            'brand_name',
            'dealer_name',
        ]
        read_only_fields = ['id', 'slug', 'view_count', 'created_at', 'updated_at', 
                           'category_name', 'brand_name', 'dealer_name']
    
    def to_representation(self, instance):
        """Override to add computed fields and additional information."""
        data = super().to_representation(instance)
        
        # Add computed fields
        data['is_in_stock'] = instance.is_in_stock
        data['average_rating'] = instance.average_rating
        data['review_count'] = instance.review_count
        
        # Add user and vendor visible field lists for reference
        data['user_visible_fields'] = instance.user_visible_fields()
        data['vendor_admin_fields'] = instance.vendor_admin_fields()
        
        return data


class PartCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating Part instances.
    Used by vendors/admins for full CRUD operations.
    """
    
    class Meta:
        model = Part
        fields = [
            # Core identification
            'parts_number',
            'sku',
            'name',
            'description',
            
            # USER-VISIBLE FIELDS
            'material_description',
            'material_description_ar',
            'base_unit_of_measure',
            'gross_weight',
            'net_weight',
            'size_dimensions',
            'manufacturer_part_number',
            'manufacturer_oem_number',
            
            # VENDOR/ADMIN-ONLY FIELDS
            'material_type',
            'plant',
            'storage_location',
            'warehouse_number',
            'material_group',
            'division',
            'minimum_order_quantity',
            'old_material_number',
            'expiration_xchpf',
            'external_material_group',
            'abc_indicator',
            'safety_stock',
            'minimum_safety_stock',
            'planned_delivery_time_days',
            'goods_receipt_processing_time_days',
            'valuation_class',
            'price_unit_peinh',
            'moving_average_price',
            
            # Additional fields
            'category',
            'brand',
            'dealer',
            'price',
            'quantity',
            'image',
            'image_url',
            'weight',
            'dimensions',
            'warranty_period',
            'is_active',
            'is_featured',
        ]
    
    def validate_parts_number(self, value):
        """Validate parts number format and uniqueness."""
        if not value or not value.strip():
            raise serializers.ValidationError("Parts number is required.")
        
        # Check uniqueness for new instances or when parts_number changes
        if self.instance is None or self.instance.parts_number != value:
            if Part.objects.filter(parts_number=value).exists():
                raise serializers.ValidationError("Parts number must be unique.")
        
        return value.strip()
    
    def validate_manufacturer_part_number(self, value):
        """Validate manufacturer part number (40 digit number)."""
        if value and len(str(value)) > 40:
            raise serializers.ValidationError("Manufacturer part number cannot exceed 40 digits.")
        return value
    
    def validate(self, data):
        """Cross-field validation."""
        # Ensure gross weight >= net weight if both are provided
        gross_weight = data.get('gross_weight')
        net_weight = data.get('net_weight')
        
        if gross_weight and net_weight and gross_weight < net_weight:
            raise serializers.ValidationError({
                'gross_weight': 'Gross weight must be greater than or equal to net weight.'
            })
        
        # Ensure safety stock >= minimum safety stock if both are provided
        safety_stock = data.get('safety_stock')
        min_safety_stock = data.get('minimum_safety_stock')
        
        if safety_stock and min_safety_stock and safety_stock < min_safety_stock:
            raise serializers.ValidationError({
                'safety_stock': 'Safety stock must be greater than or equal to minimum safety stock.'
            })
        
        return data


class InventorySerializer(serializers.ModelSerializer):
    """Serializer for Inventory model."""
    part_name = serializers.CharField(source='part.name', read_only=True)
    part_sku = serializers.CharField(source='part.sku', read_only=True)
    
    class Meta:
        model = Inventory
        fields = [
            'id', 'part', 'part_name', 'part_sku', 'quantity_on_hand',
            'quantity_reserved', 'quantity_available', 'reorder_point',
            'reorder_quantity', 'supplier', 'supplier_part_number',
            'last_restocked', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'part_name', 'part_sku', 'quantity_available', 
                           'created_at', 'updated_at']


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for OrderItem model."""
    part_name = serializers.CharField(source='part.name', read_only=True)
    part_sku = serializers.CharField(source='part.sku', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'part', 'part_name', 'part_sku', 'quantity', 
            'price', 'total_price'
        ]
        read_only_fields = ['id', 'part_name', 'part_sku', 'total_price']


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Order model."""
    items = OrderItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.email', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer', 'customer_name', 'guest_name',
            'guest_email', 'guest_phone', 'status', 'total_amount',
            'shipping_cost', 'tax_amount', 'discount_amount', 'final_amount',
            'shipping_address', 'billing_address', 'payment_method',
            'payment_status', 'tracking_number', 'notes', 'items',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'order_number', 'customer_name', 'items',
                           'created_at', 'updated_at']


class ReviewSerializer(serializers.ModelSerializer):
    """Serializer for Review model."""
    user_name = serializers.CharField(source='user.email', read_only=True)
    part_name = serializers.CharField(source='part.name', read_only=True)
    
    class Meta:
        model = Review
        fields = [
            'id', 'part', 'part_name', 'user', 'user_name', 'rating',
            'title', 'comment', 'is_verified_purchase', 'is_approved',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'part_name', 'user_name', 'is_verified_purchase',
                           'created_at', 'updated_at']
    
    def validate_rating(self, value):
        """Validate rating is between 1 and 5."""
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value