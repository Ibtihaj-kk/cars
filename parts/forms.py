from django import forms
from django.core.validators import FileExtensionValidator
from django.contrib.auth import get_user_model
from .models import (
    Part, Category, Brand, Order, OrderItem, Review, 
    BulkUploadLog, IntegrationSource, Inventory
)
import csv
import io

User = get_user_model()


class PartAdminForm(forms.ModelForm):
    """Comprehensive admin form for Part model with all fields."""
    
    class Meta:
        model = Part
        exclude = ['vehicle_variants']  # Exclude fields referencing disabled apps
        widgets = {
            'slug': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'URL-friendly slug (auto-generated if empty)'
            }),
            'material_description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Short description of the material/part'
            }),
            'material_description_ar': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Arabic description of the material/part'
            }),
            'parts_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Unique parts identification number'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Part name (legacy field)'
            }),
            'sku': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'SKU (legacy field)'
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': 'Detailed description (legacy field)'
            }),
            'price': forms.NumberInput(attrs={
                'step': '0.01',
                'class': 'form-control',
                'placeholder': '0.00'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'brand': forms.Select(attrs={'class': 'form-control'}),
            'dealer': forms.Select(attrs={'class': 'form-control'}),
            'vendor': forms.Select(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'image_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com/image.jpg'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class PartForm(forms.ModelForm):
    """Form for creating and editing parts."""
    
    class Meta:
        model = Part
        fields = [
            # Core Product Data
            'parts_number', 'material_description', 'material_description_ar',
            'manufacturer_part_number', 'manufacturer_oem_number', 'old_material_number',
            'material_type', 'material_group', 'external_material_group', 'division',
            'industry_sector',
            
            # Pricing & Sales Data
            'standard_price', 'moving_average_price', 'price_unit_peinh',
            'valuation_class', 'valuation_category', 'price_control_indicator',
            'sales_organization', 'distribution_channel', 'profit_center',
            'tax_classification_material', 'account_assignment_group', 'item_category_group',
            
            # Inventory & Logistics
            'plant', 'storage_location', 'warehouse_number', 'storage_bin',
            'base_unit_of_measure', 'gross_weight', 'net_weight', 'size_dimensions',
            'minimum_order_quantity', 'transportation_group', 'loading_group', 'abc_indicator',
            
            # Planning (MRP)
            'mrp_type', 'mrp_controller', 'procurement_type', 'reorder_point',
            'safety_stock', 'minimum_safety_stock', 'planned_delivery_time_days',
            'goods_receipt_processing_time_days', 'total_replenishment_lead_time',
            'purchasing_group', 'lot_size', 'availability_check',
            
            # Legacy fields for backward compatibility
            'name', 'description', 'sku', 'slug', 'category', 'brand', 
            'price', 'quantity', 'image', 'image_url', 'weight', 
            'dimensions', 'warranty_period', 'is_active', 'is_featured',
            
            # Status field for draft functionality
            'status'
        ]
        widgets = {
            # Core Product Data widgets
            'parts_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'INT-001-X'
            }),
            'material_description': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. Front Brake Pads Ceramic'
            }),
            'material_description_ar': forms.TextInput(attrs={
                'class': 'form-input text-right',
                'placeholder': 'وصف المادة'
            }),
            'manufacturer_part_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'OEM-123456789...'
            }),
            'manufacturer_oem_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Original Equipment Number'
            }),
            'old_material_number': forms.TextInput(attrs={
                'class': 'form-input'
            }),
            'material_type': forms.Select(attrs={
                'class': 'form-input bg-white'
            }),
            'material_group': forms.TextInput(attrs={
                'class': 'form-input'
            }),
            'external_material_group': forms.TextInput(attrs={
                'class': 'form-input'
            }),
            'division': forms.TextInput(attrs={
                'class': 'form-input'
            }),
            'industry_sector': forms.Select(attrs={
                'class': 'form-input bg-white'
            }),
            
            # Pricing & Sales Data widgets
            'standard_price': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'moving_average_price': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'price_unit_peinh': forms.NumberInput(attrs={
                'class': 'form-input',
                'value': '1'
            }),
            'valuation_class': forms.TextInput(attrs={
                'class': 'form-input'
            }),
            'valuation_category': forms.TextInput(attrs={
                'class': 'form-input'
            }),
            'price_control_indicator': forms.Select(attrs={
                'class': 'form-input bg-white'
            }),
            'sales_organization': forms.TextInput(attrs={
                'class': 'form-input'
            }),
            'distribution_channel': forms.TextInput(attrs={
                'class': 'form-input'
            }),
            'profit_center': forms.TextInput(attrs={
                'class': 'form-input'
            }),
            'tax_classification_material': forms.Select(attrs={
                'class': 'form-input bg-white'
            }),
            'account_assignment_group': forms.TextInput(attrs={
                'class': 'form-input'
            }),
            'item_category_group': forms.TextInput(attrs={
                'class': 'form-input'
            }),
            
            # Inventory & Logistics widgets
            'plant': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Code'
            }),
            'storage_location': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Code'
            }),
            'warehouse_number': forms.TextInput(attrs={
                'class': 'form-input'
            }),
            'storage_bin': forms.TextInput(attrs={
                'class': 'form-input'
            }),
            'base_unit_of_measure': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'EA / PC'
            }),
            'gross_weight': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'kg'
            }),
            'net_weight': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'kg'
            }),
            'size_dimensions': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'L x W x H'
            }),
            'minimum_order_quantity': forms.NumberInput(attrs={
                'class': 'form-input',
                'value': '1'
            }),
            'transportation_group': forms.TextInput(attrs={
                'class': 'form-input'
            }),
            'loading_group': forms.TextInput(attrs={
                'class': 'form-input'
            }),
            'abc_indicator': forms.Select(attrs={
                'class': 'form-input bg-white'
            }),
            
            # Planning (MRP) widgets
            'mrp_type': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'PD / ND'
            }),
            'mrp_controller': forms.TextInput(attrs={
                'class': 'form-input'
            }),
            'procurement_type': forms.Select(attrs={
                'class': 'form-input bg-white'
            }),
            'reorder_point': forms.NumberInput(attrs={
                'class': 'form-input'
            }),
            'safety_stock': forms.NumberInput(attrs={
                'class': 'form-input'
            }),
            'minimum_safety_stock': forms.NumberInput(attrs={
                'class': 'form-input'
            }),
            'planned_delivery_time_days': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Days'
            }),
            'goods_receipt_processing_time_days': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Days'
            }),
            'total_replenishment_lead_time': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Days'
            }),
            'purchasing_group': forms.TextInput(attrs={
                'class': 'form-input'
            }),
            'lot_size': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'EX / FX'
            }),
            'availability_check': forms.TextInput(attrs={
                'class': 'form-input'
            }),
            
            'description': forms.Textarea(attrs={
                'rows': 4, 
                'class': 'form-control',
                'placeholder': 'Detailed description of the part...'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Part name'
            }),
            'sku': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Unique SKU'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'URL-friendly slug (auto-generated if empty)'
            }),
            'price': forms.NumberInput(attrs={
                'step': '0.01',
                'class': 'form-control',
                'placeholder': '0.00'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'brand': forms.Select(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'image_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com/image.jpg'
            }),
            'weight': forms.NumberInput(attrs={
                'step': '0.01',
                'class': 'form-control',
                'placeholder': 'Weight in kg'
            }),
            'dimensions': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'L x W x H (cm)'
            }),
            'warranty_period': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Months',
                'min': '0'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all()
        self.fields['brand'].queryset = Brand.objects.filter(is_active=True)


class CategoryForm(forms.ModelForm):
    """Form for creating and editing categories."""
    
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Category name'
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Category description...'
            }),
        }


class BrandForm(forms.ModelForm):
    """Form for creating and editing brands."""
    
    class Meta:
        model = Brand
        fields = ['name', 'logo', 'description', 'website', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brand name'
            }),
            'logo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Brand description...'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://brand-website.com'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class PartSearchForm(forms.Form):
    """Form for searching and filtering parts with role-based options."""
    
    query = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search parts by name, description, or part number...',
            'id': 'search-query',
            'hx-get': '',
            'hx-trigger': 'keyup changed delay:300ms',
            'hx-target': '#parts-results',
            'hx-indicator': '#loading-indicator'
        })
    )
    
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'category-filter',
            'hx-get': '',
            'hx-trigger': 'change',
            'hx-target': '#parts-results',
            'hx-indicator': '#loading-indicator'
        })
    )
    
    brand = forms.ModelChoiceField(
        queryset=Brand.objects.filter(is_active=True),
        required=False,
        empty_label="All Brands",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'brand-filter',
            'hx-get': '',
            'hx-trigger': 'change',
            'hx-target': '#parts-results',
            'hx-indicator': '#loading-indicator'
        })
    )
    
    min_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min Price',
            'step': '0.01',
            'id': 'min-price',
            'hx-get': '',
            'hx-trigger': 'keyup changed delay:500ms',
            'hx-target': '#parts-results',
            'hx-indicator': '#loading-indicator'
        })
    )
    
    max_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max Price',
            'step': '0.01',
            'id': 'max-price',
            'hx-get': '',
            'hx-trigger': 'keyup changed delay:500ms',
            'hx-target': '#parts-results',
            'hx-indicator': '#loading-indicator'
        })
    )
    
    in_stock_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'in-stock-only',
            'hx-get': '',
            'hx-trigger': 'change',
            'hx-target': '#parts-results',
            'hx-indicator': '#loading-indicator'
        })
    )
    
    # Vehicle compatibility filters - Disabled, vehicles app not in INSTALLED_APPS
    # vehicle_make = forms.ModelChoiceField(
    #     queryset=None,  # Will be set dynamically
    #     required=False,
    #     empty_label="All Makes",
    #     widget=forms.Select(attrs={
    #         'class': 'form-select',
    #         'id': 'vehicle-make-filter',
    #         'hx-get': '',
    #         'hx-trigger': 'change',
    #         'hx-target': '#vehicle-model-filter',
    #         'hx-indicator': '#loading-indicator'
    #     })
    # )
    # 
    # vehicle_model = forms.ModelChoiceField(
    #     queryset=None,  # Will be set dynamically based on make
    #     required=False,
    #     empty_label="All Models",
    #     widget=forms.Select(attrs={
    #         'class': 'form-select',
    #         'id': 'vehicle-model-filter',
    #         'hx-get': '',
    #         'hx-trigger': 'change',
    #         'hx-target': '#parts-results',
    #         'hx-indicator': '#loading-indicator'
    #     })
    # )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)


class VendorPartSearchForm(PartSearchForm):
    """Extended search form for vendors with additional filters."""
    
    # Vendor-specific filters
    low_stock_only = forms.BooleanField(
        required=False,
        label="Low Stock Only",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'low-stock-only',
            'hx-get': '',
            'hx-trigger': 'change',
            'hx-target': '#parts-results',
            'hx-indicator': '#loading-indicator'
        })
    )
    
    STATUS_CHOICES = [
        ('', 'All Status'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('featured', 'Featured'),
        ('out_of_stock', 'Out of Stock'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'status-filter',
            'hx-get': '',
            'hx-trigger': 'change',
            'hx-target': '#parts-results',
            'hx-indicator': '#loading-indicator'
        })
    )
    
    PROFITABILITY_CHOICES = [
        ('', 'All Profitability'),
        ('high', 'High Margin (>30%)'),
        ('medium', 'Medium Margin (15-30%)'),
        ('low', 'Low Margin (<15%)'),
    ]
    
    profitability = forms.ChoiceField(
        choices=PROFITABILITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'profitability-filter',
            'hx-get': '',
            'hx-trigger': 'change',
            'hx-target': '#parts-results',
            'hx-indicator': '#loading-indicator'
        })
    )
    
    # Material type filter (vendor/admin only field)
    material_type = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Material Type',
            'id': 'material-type-filter',
            'hx-get': '',
            'hx-trigger': 'keyup changed delay:300ms',
            'hx-target': '#parts-results',
            'hx-indicator': '#loading-indicator'
        })
    )


class AdminPartSearchForm(VendorPartSearchForm):
    """Extended search form for admins with global management filters."""
    
    # Admin-specific filters
    dealer = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        empty_label="All Dealers",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'dealer-filter',
            'hx-get': '',
            'hx-trigger': 'change',
            'hx-target': '#parts-results',
            'hx-indicator': '#loading-indicator'
        })
    )
    
    ABC_CHOICES = [
        ('', 'All ABC Categories'),
        ('A', 'A - High Value'),
        ('B', 'B - Medium Value'),
        ('C', 'C - Low Value'),
    ]
    
    abc_indicator = forms.ChoiceField(
        choices=ABC_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'abc-filter',
            'hx-get': '',
            'hx-trigger': 'change',
            'hx-target': '#parts-results',
            'hx-indicator': '#loading-indicator'
        })
    )
    
    plant = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Plant',
            'id': 'plant-filter',
            'hx-get': '',
            'hx-trigger': 'keyup changed delay:300ms',
            'hx-target': '#parts-results',
            'hx-indicator': '#loading-indicator'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set dealer queryset to users with dealer permissions
        self.fields['dealer'].queryset = User.objects.filter(
            groups__name__in=['Dealers', 'Vendors']
        ).distinct()


class GuestOrderForm(forms.Form):
    """Form for guest customer information during checkout."""
    
    guest_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'placeholder': 'Full Name',
            'class': 'form-control',
            'required': True
        })
    )
    guest_email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'Email Address',
            'class': 'form-control',
            'required': True
        })
    )
    guest_phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'placeholder': 'Phone Number',
            'class': 'form-control',
            'required': True
        })
    )
    guest_address = forms.CharField(
        widget=forms.Textarea(attrs={
            'placeholder': 'Shipping Address',
            'class': 'form-control',
            'rows': 3,
            'required': True
        })
    )


class OrderStatusForm(forms.ModelForm):
    """Form for updating order status."""
    
    class Meta:
        model = Order
        fields = ['status', 'tracking_number', 'notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'tracking_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tracking number'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Order notes...'
            }),
        }


class ReviewForm(forms.ModelForm):
    """Form for creating part reviews."""
    
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(
                choices=[(i, f'{i} Star{"s" if i != 1 else ""}') for i in range(1, 6)],
                attrs={'class': 'form-control'}
            ),
            'comment': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': 'Share your experience with this part...'
            }),
        }


class InventoryForm(forms.ModelForm):
    """Form for managing inventory."""
    
    class Meta:
        model = Inventory
        fields = ['stock', 'reorder_level', 'max_stock_level', 'supplier_info']
        widgets = {
            'stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'reorder_level': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'max_stock_level': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'supplier_info': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Supplier information...'
            }),
        }


class DealerUploadForm(forms.Form):
    """Form for dealers to upload CSV files."""
    
    csv_file = forms.FileField(
        validators=[FileExtensionValidator(allowed_extensions=['csv'])],
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv'
        }),
        help_text='Upload a CSV file with part data. Maximum file size: 5MB.'
    )
    
    def clean_csv_file(self):
        file = self.cleaned_data['csv_file']
        if file.size > 5 * 1024 * 1024:  # 5MB limit
            raise forms.ValidationError('File size cannot exceed 5MB.')
        return file


class IntegrationSourceForm(forms.ModelForm):
    """Form for creating and editing integration sources."""
    
    class Meta:
        model = IntegrationSource
        fields = [
            'name', 'api_url', 'api_key', 'auth_type', 
            'is_active', 'sync_frequency'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Integration name'
            }),
            'api_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://api.example.com'
            }),
            'api_key': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'API Key'
            }),
            'auth_type': forms.Select(attrs={'class': 'form-control'}),
            'sync_frequency': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'Minutes'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class BulkPartUpdateForm(forms.Form):
    """Form for bulk updating part prices or quantities."""
    
    UPDATE_CHOICES = [
        ('price', 'Update Prices'),
        ('quantity', 'Update Quantities'),
        ('status', 'Update Status'),
    ]
    
    update_type = forms.ChoiceField(
        choices=UPDATE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    brand = forms.ModelChoiceField(
        queryset=Brand.objects.filter(is_active=True),
        required=False,
        empty_label="All Brands",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # For price updates
    price_adjustment = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Percentage (e.g., 10 for 10% increase)',
            'step': '0.01'
        }),
        help_text='Percentage increase/decrease (use negative for decrease)'
    )
    
    # For quantity updates
    quantity_adjustment = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Quantity to add/subtract'
        }),
        help_text='Quantity to add (use negative to subtract)'
    )
    
    # For status updates
    new_status = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Check to activate, uncheck to deactivate'
    )


class CSVUploadForm(forms.Form):
    """Form for uploading CSV files to bulk create parts."""
    
    csv_file = forms.FileField(
        label='CSV File',
        validators=[FileExtensionValidator(allowed_extensions=['csv'])],
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv',
            'id': 'csvFileInput'
        }),
        help_text='Upload a CSV file with columns: name, category, brand, price, quantity, sku, description, image_url'
    )
    
    skip_duplicates = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Skip rows with duplicate SKU or name'
    )
    
    update_existing = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Update existing parts if SKU matches'
    )
    
    def clean_csv_file(self):
        """Validate CSV file format and structure."""
        csv_file = self.cleaned_data.get('csv_file')
        
        if not csv_file:
            return csv_file


class GuestCheckoutForm(forms.Form):
    """Form for guest user checkout information."""
    
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'pw-form-input',
            'placeholder': 'Full Name',
            'required': True
        }),
        label='Full Name'
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'pw-form-input',
            'placeholder': 'Email Address',
            'required': True
        }),
        label='Email Address'
    )
    
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'pw-form-input',
            'placeholder': 'Phone Number',
            'required': True
        }),
        label='Phone Number'
    )
    
    address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'pw-form-textarea',
            'placeholder': 'Complete Address',
            'rows': 3,
            'required': True
        }),
        label='Address'
    )
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            # Remove any non-digit characters for validation
            digits_only = ''.join(filter(str.isdigit, phone))
            if len(digits_only) < 10:
                raise forms.ValidationError('Please enter a valid phone number.')
        return phone


class OrderForm(forms.ModelForm):
    """Form for creating orders."""
    
    class Meta:
        model = Order
        fields = ['guest_name', 'guest_email', 'guest_phone', 'guest_address']
        widgets = {
            'guest_name': forms.TextInput(attrs={
                'class': 'pw-form-input',
                'placeholder': 'Full Name'
            }),
            'guest_email': forms.EmailInput(attrs={
                'class': 'pw-form-input',
                'placeholder': 'Email Address'
            }),
            'guest_phone': forms.TextInput(attrs={
                'class': 'pw-form-input',
                'placeholder': 'Phone Number'
            }),
            'guest_address': forms.Textarea(attrs={
                'class': 'pw-form-textarea',
                'placeholder': 'Complete Address',
                'rows': 3
            }),
        }