"""
Multi-step vendor registration forms with comprehensive validation.
Handles the complete vendor onboarding process with field-specific validation.
"""

from django import forms
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
import re
import os
from .models import VendorApplication, VendorProfile
from .permissions import get_vendor_profile
from .catalog_models import CatalogItem
from .widgets import VehicleVariantMultiSelectWidget, ProfitMarginCalculatorWidget, InventoryThresholdWidget
from parts.models import Part, Category, Brand
from django.contrib.auth import authenticate

User = get_user_model()


class BaseVendorApplicationForm(forms.ModelForm):
    """Base form for vendor application with common functionality"""
    
    class Meta:
        model = VendorApplication
        fields = []
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes to all form fields
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(field.widget, forms.FileInput):
                field.widget.attrs.update({'class': 'form-control-file'})
            else:
                field.widget.attrs.update({'class': 'form-control'})
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        if commit:
            instance.save()
        return instance


class VendorApplicationStep1Form(BaseVendorApplicationForm):
    """Step 1: Business Details Form"""
    
    class Meta:
        model = VendorApplication
        fields = [
            'company_name', 'business_type', 'commercial_registration_number',
            'legal_identifier', 'cr_document', 'business_license',
            'establishment_date', 'business_description'
        ]
        widgets = {
            'establishment_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'business_description': forms.Textarea(
                attrs={'rows': 4, 'class': 'form-control'}
            ),
            'cr_document': forms.FileInput(
                attrs={'accept': '.pdf,.jpg,.jpeg,.png', 'class': 'form-control-file'}
            ),
            'business_license': forms.FileInput(
                attrs={'accept': '.pdf,.jpg,.jpeg,.png', 'class': 'form-control-file'}
            ),
        }




class VendorPartSearchForm(forms.Form):
    """
    Form for searching and filtering vendor parts.
    """
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by part number, description, or OEM number...'
        })
    )
    
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="All Categories"
    )
    
    brand = forms.ModelChoiceField(
        queryset=Brand.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="All Brands"
    )
    
    is_active = forms.ChoiceField(
        choices=[
            ('', 'All Statuses'),
            ('true', 'Active'),
            ('false', 'Inactive'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    stock_status = forms.ChoiceField(
        choices=[
            ('', 'All Stock Levels'),
            ('in_stock', 'In Stock'),
            ('low_stock', 'Low Stock'),
            ('out_of_stock', 'Out of Stock'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    is_featured = forms.ChoiceField(
        choices=[
            ('', 'All'),
            ('true', 'Featured'),
            ('false', 'Standard'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    min_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Min'})
    )
    
    max_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Max'})
    )
    
    material_type = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Material Type'})
    )
    
    plant = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Plant'})
    )
    
    material_group = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Material Group'})
    )
    
    abc_indicator = forms.ChoiceField(
        choices=[('', 'All')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    sort_by = forms.ChoiceField(
        choices=[
            ('created_at', 'Newest First'),
            ('parts_number', 'Part Number'),
            ('price', 'Price: Low to High'),
            ('-price', 'Price: High to Low'),
            ('quantity', 'Quantity'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class VendorApplicationStep2Form(BaseVendorApplicationForm):
    """Step 2: Contact Information Form"""
    
    class Meta:
        model = VendorApplication
        fields = [
            'contact_person_name', 'contact_person_title',
            'business_phone', 'business_email', 'website',
            'street_address', 'city', 'state_province',
            'postal_code', 'country'
        ]
        widgets = {
            'street_address': forms.Textarea(
                attrs={'rows': 3, 'class': 'form-control'}
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make required fields
        required_fields = [
            'contact_person_name', 'business_phone', 'business_email',
            'street_address', 'city', 'country'
        ]
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True
        
        # Add placeholders and validation
        self.fields['contact_person_name'].widget.attrs.update({
            'placeholder': 'Full name of primary contact person'
        })
        self.fields['contact_person_title'].widget.attrs.update({
            'placeholder': 'Job title (e.g., General Manager)'
        })
        self.fields['business_phone'].widget.attrs.update({
            'placeholder': '+966 50 123 4567'
        })
        self.fields['business_email'].widget.attrs.update({
            'placeholder': 'business@company.com'
        })
        self.fields['website'].widget.attrs.update({
            'placeholder': 'https://www.company.com'
        })
        self.fields['postal_code'].widget.attrs.update({
            'placeholder': '12345'
        })
    
    def clean_business_phone(self):
        """Validate business phone number"""
        phone = self.cleaned_data.get('business_phone')
        if phone:
            # Remove spaces, dashes, and parentheses
            phone = re.sub(r'[\s\-\(\)]', '', phone)
            
            # Validate Saudi phone number format
            if not re.match(r'^(\+966|966|0)?[5][0-9]{8}$', phone):
                raise ValidationError(
                    'Please enter a valid Saudi phone number (e.g., +966501234567)'
                )
            
            # Normalize to international format
            if phone.startswith('0'):
                phone = '+966' + phone[1:]
            elif phone.startswith('966'):
                phone = '+' + phone
            elif not phone.startswith('+966'):
                phone = '+966' + phone
                
        return phone
    
    def clean_business_email(self):
        """Validate business email uniqueness"""
        email = self.cleaned_data.get('business_email')
        if email:
            # Check if email already exists in approved applications
            existing = VendorApplication.objects.filter(
                business_email__iexact=email,
                status='approved'
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing.exists():
                raise ValidationError(
                    'A vendor with this email address is already registered.'
                )
        return email
    
    def clean_website(self):
        """Validate website URL"""
        website = self.cleaned_data.get('website')
        if website and not website.startswith(('http://', 'https://')):
            website = 'https://' + website
        return website
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.current_step = 2
        if instance.is_step_completed(2):
            instance.status = 'contact_info_completed'
        if commit:
            instance.save()
        return instance


class VendorApplicationStep3Form(BaseVendorApplicationForm):
    """Step 3: Bank Details Form with IBAN validation"""
    
    class Meta:
        model = VendorApplication
        fields = [
            'bank_name', 'bank_branch', 'account_holder_name',
            'account_number', 'iban', 'swift_code', 'bank_statement'
        ]
        widgets = {
            'bank_statement': forms.FileInput(
                attrs={'accept': '.pdf,.jpg,.jpeg,.png', 'class': 'form-control-file'}
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make required fields
        required_fields = [
            'bank_name', 'account_holder_name', 'account_number', 'iban'
        ]
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True
        
        # Add placeholders and help text
        self.fields['bank_name'].widget.attrs.update({
            'placeholder': 'e.g., Saudi National Bank'
        })
        self.fields['bank_branch'].widget.attrs.update({
            'placeholder': 'Branch name or code'
        })
        self.fields['account_holder_name'].widget.attrs.update({
            'placeholder': 'Must match company name exactly'
        })
        self.fields['account_number'].widget.attrs.update({
            'placeholder': 'Bank account number'
        })
        self.fields['iban'].widget.attrs.update({
            'placeholder': 'SA0380000000608010167519',
            'maxlength': '34'
        })
        self.fields['swift_code'].widget.attrs.update({
            'placeholder': 'e.g., NCBKSAJE',
            'maxlength': '11'
        })
    
    def clean_iban(self):
        """Validate IBAN format and checksum"""
        iban = self.cleaned_data.get('iban')
        if iban:
            # Remove spaces and convert to uppercase
            iban = re.sub(r'\s+', '', iban.upper())
            
            # Check if it's a Saudi IBAN (starts with SA and is 24 characters)
            if not re.match(r'^SA\d{22}$', iban):
                raise ValidationError(
                    'Please enter a valid Saudi IBAN (24 characters starting with SA)'
                )
            
            # Validate IBAN checksum using mod-97 algorithm
            if not self._validate_iban_checksum(iban):
                raise ValidationError(
                    'Invalid IBAN checksum. Please check your IBAN number.'
                )
        
        return iban
    
    def _validate_iban_checksum(self, iban):
        """Validate IBAN using mod-97 algorithm"""
        try:
            # Move first 4 characters to end
            rearranged = iban[4:] + iban[:4]
            
            # Replace letters with numbers (A=10, B=11, ..., Z=35)
            numeric_string = ''
            for char in rearranged:
                if char.isalpha():
                    numeric_string += str(ord(char) - ord('A') + 10)
                else:
                    numeric_string += char
            
            # Calculate mod 97
            return int(numeric_string) % 97 == 1
        except (ValueError, TypeError):
            return False
    
    def clean_account_holder_name(self):
        """Validate account holder name matches company name"""
        account_holder = self.cleaned_data.get('account_holder_name')
        if account_holder and self.instance and self.instance.company_name:
            # Check if account holder name is similar to company name
            company_name = self.instance.company_name.lower()
            holder_name = account_holder.lower()
            
            # Remove common business suffixes for comparison
            suffixes = ['llc', 'ltd', 'limited', 'company', 'corp', 'corporation']
            for suffix in suffixes:
                company_name = company_name.replace(suffix, '').strip()
                holder_name = holder_name.replace(suffix, '').strip()
            
            # Check if names are reasonably similar (at least 70% match)
            if not self._names_similar(company_name, holder_name):
                raise ValidationError(
                    'Account holder name should match or be similar to the company name.'
                )
        
        return account_holder
    
    def _names_similar(self, name1, name2, threshold=0.7):
        """Check if two names are similar using simple string matching"""
        # Simple similarity check - can be enhanced with more sophisticated algorithms
        words1 = set(name1.split())
        words2 = set(name2.split())
        
        if not words1 or not words2:
            return False
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return (intersection / union) >= threshold
    
    def clean_swift_code(self):
        """Validate SWIFT code format"""
        swift = self.cleaned_data.get('swift_code')
        if swift:
            swift = swift.upper().replace(' ', '')
            # SWIFT code format: 8 or 11 characters
            if not re.match(r'^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$', swift):
                raise ValidationError(
                    'Please enter a valid SWIFT code (8 or 11 characters)'
                )
        return swift
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.current_step = 3
        if instance.is_step_completed(3):
            instance.status = 'bank_details_completed'
        if commit:
            instance.save()
        return instance


class VendorApplicationStep4Form(BaseVendorApplicationForm):
    """Step 4: Additional Information Form (Optional)"""
    
    class Meta:
        model = VendorApplication
        fields = [
            'expected_monthly_volume', 'product_categories',
            'years_in_business', 'references'
        ]
        widgets = {
            'product_categories': forms.Textarea(
                attrs={'rows': 4, 'class': 'form-control'}
            ),
            'references': forms.Textarea(
                attrs={'rows': 4, 'class': 'form-control'}
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add placeholders and help text
        self.fields['expected_monthly_volume'].widget.attrs.update({
            'placeholder': '0.00',
            'step': '0.01'
        })
        self.fields['product_categories'].widget.attrs.update({
            'placeholder': 'e.g., Engine parts, Brake systems, Electrical components...'
        })
        self.fields['years_in_business'].widget.attrs.update({
            'placeholder': 'Number of years in automotive parts business'
        })
        self.fields['references'].widget.attrs.update({
            'placeholder': 'Previous business partnerships, supplier references, etc.'
        })
    
    def clean_expected_monthly_volume(self):
        """Validate expected monthly volume"""
        volume = self.cleaned_data.get('expected_monthly_volume')
        if volume is not None and volume < 0:
            raise ValidationError('Expected monthly volume cannot be negative.')
        return volume
    
    def clean_years_in_business(self):
        """Validate years in business"""
        years = self.cleaned_data.get('years_in_business')
        if years is not None and (years < 0 or years > 100):
            raise ValidationError('Years in business must be between 0 and 100.')
        return years
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.current_step = 4
        
        # Check if application can be submitted
        if instance.can_submit():
            instance.status = 'ready_for_submission'
        
        if commit:
            instance.save()
        return instance


class VendorApplicationSubmissionForm(forms.Form):
    """Final submission form with terms and conditions"""
    
    terms_accepted = forms.BooleanField(
        required=True,
        label="I accept the terms and conditions",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    privacy_accepted = forms.BooleanField(
        required=True,
        label="I accept the privacy policy",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    data_accuracy = forms.BooleanField(
        required=True,
        label="I confirm that all provided information is accurate and complete",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        self.application = kwargs.pop('application', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Verify application can be submitted
        if self.application and not self.application.can_submit():
            raise ValidationError(
                'Application is not complete. Please complete all required steps.'
            )
        
        return cleaned_data


class VendorPartBulkUpdateForm(forms.Form):
    """
    Form for bulk updating vendor parts.
    """
    # Price adjustments
    price_adjustment_type = forms.ChoiceField(
        choices=[
            ('', '--- Select Adjustment ---'),
            ('percentage_increase', 'Increase by Percentage (%)'),
            ('percentage_decrease', 'Decrease by Percentage (%)'),
            ('fixed_amount_increase', 'Increase by Fixed Amount'),
            ('fixed_amount_decrease', 'Decrease by Fixed Amount'),
            ('set_price', 'Set Specific Price'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    price_adjustment_value = forms.DecimalField(
        required=False,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )

    # Quantity adjustments
    quantity_adjustment_type = forms.ChoiceField(
        choices=[
            ('', '--- Select Adjustment ---'),
            ('add', 'Add to Stock'),
            ('subtract', 'Subtract from Stock'),
            ('set', 'Set Exact Quantity'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    quantity_adjustment_value = forms.DecimalField(
        required=False,
        decimal_places=3,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'})
    )

    # Status updates
    set_active_status = forms.ChoiceField(
        choices=[
            ('', '--- No Change ---'),
            ('true', 'Active'),
            ('false', 'Inactive'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    set_featured_status = forms.ChoiceField(
        choices=[
            ('', '--- No Change ---'),
            ('true', 'Featured'),
            ('false', 'Not Featured'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # Vendor-specific updates
    update_material_type = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    update_plant = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    update_material_group = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate price adjustment
        price_type = cleaned_data.get('price_adjustment_type')
        price_value = cleaned_data.get('price_adjustment_value')
        
        if price_type and price_value is None:
            self.add_error('price_adjustment_value', 'Value is required when an adjustment type is selected.')
        if price_value is not None and not price_type:
            self.add_error('price_adjustment_type', 'Type is required when a value is entered.')
            
        # Validate quantity adjustment
        qty_type = cleaned_data.get('quantity_adjustment_type')
        qty_value = cleaned_data.get('quantity_adjustment_value')
        
        if qty_type and qty_value is None:
            self.add_error('quantity_adjustment_value', 'Value is required when an adjustment type is selected.')
        if qty_value is not None and not qty_type:
            self.add_error('quantity_adjustment_type', 'Type is required when a value is entered.')
            
        return cleaned_data


class VendorPartForm(forms.ModelForm):
    """
    Form for vendors to add/edit parts with access to all Excel fields.
    """
    inventory_threshold = forms.IntegerField(
        required=False,
        initial=10,
        min_value=0,
        widget=InventoryThresholdWidget(),
        label="Low Stock Alert Threshold",
        help_text="Notify when stock falls below this level"
    )

    class Meta:
        model = Part
        exclude = [
            'vendor', 'dealer', 'slug', 'view_count', 
            'created_at', 'updated_at', 'is_featured', 
            'average_rating', 'review_count', 'is_active'
        ]
        widgets = {
            # Basic Info
            'parts_number': forms.TextInput(attrs={'class': 'form-control'}),
            'material_description': forms.TextInput(attrs={'class': 'form-control'}),
            'material_description_ar': forms.TextInput(attrs={'class': 'form-control', 'dir': 'rtl'}),
            'manufacturer_part_number': forms.TextInput(attrs={'class': 'form-control'}),
            'manufacturer_oem_number': forms.TextInput(attrs={'class': 'form-control'}),
            
            # Classification
            'category': forms.Select(attrs={'class': 'form-select'}),
            'brand': forms.Select(attrs={'class': 'form-select'}),
            'material_type': forms.TextInput(attrs={'class': 'form-control'}),
            'material_group': forms.TextInput(attrs={'class': 'form-control'}),
            'division': forms.TextInput(attrs={'class': 'form-control'}),
            
            # Weights & Dimensions
            'base_unit_of_measure': forms.TextInput(attrs={'class': 'form-control'}),
            'gross_weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'net_weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'weight_of_unit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'size_dimensions': forms.TextInput(attrs={'class': 'form-control'}),
            
            # Pricing & Valuation
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'standard_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'moving_average_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valuation_class': forms.TextInput(attrs={'class': 'form-control'}),
            'price_control_indicator': forms.Select(attrs={'class': 'form-select'}),
            'price_unit_peinh': forms.NumberInput(attrs={'class': 'form-control'}),
            
            # Logistics
            'plant': forms.TextInput(attrs={'class': 'form-control'}),
            'storage_location': forms.TextInput(attrs={'class': 'form-control'}),
            'warehouse_number': forms.TextInput(attrs={'class': 'form-control'}),
            'storage_bin': forms.TextInput(attrs={'class': 'form-control'}),
            'minimum_order_quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'safety_stock': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'minimum_safety_stock': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'reorder_point': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'lot_size': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            
            # Planning
            'mrp_type': forms.TextInput(attrs={'class': 'form-control'}),
            'mrp_controller': forms.TextInput(attrs={'class': 'form-control'}),
            'mrp_group': forms.TextInput(attrs={'class': 'form-control'}),
            'procurement_type': forms.Select(attrs={'class': 'form-select'}),
            'planned_delivery_time_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'goods_receipt_processing_time_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'total_replenishment_lead_time': forms.NumberInput(attrs={'class': 'form-control'}),
            
            # Sales
            'sales_organization': forms.TextInput(attrs={'class': 'form-control'}),
            'distribution_channel': forms.TextInput(attrs={'class': 'form-control'}),
            'material_pricing_group': forms.TextInput(attrs={'class': 'form-control'}),
            'account_assignment_group': forms.TextInput(attrs={'class': 'form-control'}),
            'item_category_group': forms.TextInput(attrs={'class': 'form-control'}),
            'general_item_category_group': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_classification_material': forms.TextInput(attrs={'class': 'form-control'}),
            'transportation_group': forms.TextInput(attrs={'class': 'form-control'}),
            'loading_group': forms.TextInput(attrs={'class': 'form-control'}),
            'profit_center': forms.TextInput(attrs={'class': 'form-control'}),
            'purchasing_group': forms.TextInput(attrs={'class': 'form-control'}),
            'availability_check': forms.TextInput(attrs={'class': 'form-control'}),
            
            # Status
            'status': forms.Select(attrs={'class': 'form-select'}),
            'abc_indicator': forms.Select(attrs={'class': 'form-select'}),
            'valuation_category': forms.TextInput(attrs={'class': 'form-control'}),
            
            # Media
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'image_url': forms.URLInput(attrs={'class': 'form-control'}),
            
            # Other
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'old_material_number': forms.TextInput(attrs={'class': 'form-control'}),
            'expiration_xchpf': forms.TextInput(attrs={'class': 'form-control'}),
            'external_material_group': forms.TextInput(attrs={'class': 'form-control'}),
            'industry_sector': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.vendor = kwargs.pop('vendor', None)
        super().__init__(*args, **kwargs)

        # Make important fields required
        self.fields['parts_number'].required = True
        self.fields['material_description'].required = True
        self.fields['category'].required = True
        self.fields['brand'].required = True

        # Always show all active brands and all categories
        self.fields['category'].queryset = Category.objects.all().order_by('name')
        self.fields['brand'].queryset = Brand.objects.filter(is_active=True).order_by('name')

        if hasattr(self.fields['category'], 'empty_label'):
            self.fields['category'].empty_label = "Select Category"
        if hasattr(self.fields['brand'], 'empty_label'):
            self.fields['brand'].empty_label = "Select Make"
        
        # Add help texts where needed
        self.fields['parts_number'].help_text = "Unique identifier for this part"
        self.fields['material_description'].help_text = "Short descriptive name"

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.vendor:
            instance.vendor = self.vendor
            preferred_currency = getattr(getattr(self.vendor, 'vendor_profile', None), 'preferred_currency', None)
            submitted_currency = None
            if hasattr(self, 'cleaned_data'):
                submitted_currency = self.cleaned_data.get('original_currency')
            if not submitted_currency and preferred_currency:
                instance.original_currency = preferred_currency
        if commit:
            instance.save()
        return instance


class VendorPartBulkImportForm(forms.Form):
    """
    Form for bulk importing vendor parts from CSV or Excel files.
    Supports comprehensive validation and error reporting.
    """
    
    file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.xlsx,.xls',
            'id': 'bulk-import-file'
        }),
        help_text='Upload CSV or Excel file with part data. Maximum file size: 10MB'
    )

    import_status = forms.ChoiceField(
        required=False,
        initial='published',
        choices=[
            ('published', 'Publish'),
            ('draft', 'Draft'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Status for newly created parts in this import'
    )
    
    update_existing = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Update existing parts if they already exist (based on parts number)'
    )
    
    validate_only = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Only validate the file without importing (useful for testing)'
    )

    chunk_size = forms.IntegerField(
        required=False,
        initial=5000,
        min_value=500,
        max_value=50000,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text='Rows per write batch (500–50000)'
    )
    
    def clean_file(self):
        """Validate uploaded file"""
        file = self.cleaned_data.get('file')
        
        if not file:
            raise ValidationError(_('Please select a file to upload.'))
        
        max_size_mb = 500
        if file.size > max_size_mb * 1024 * 1024:
            raise ValidationError(_(f'File size must be less than {max_size_mb}MB.'))
        
        # Check file extension
        allowed_extensions = ['.csv', '.xlsx']
        file_extension = os.path.splitext(file.name)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise ValidationError(
                _('Invalid file format. Please upload CSV or XLSX files only.')
            )
        
        return file


class VendorPartExportForm(forms.Form):
    """
    Form for configuring part export options.
    """
    
    export_format = forms.ChoiceField(
        choices=[
            ('csv', 'CSV'),
            ('xlsx', 'Excel (XLSX)'),
        ],
        initial='xlsx',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    include_inactive = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label=_('Include Inactive Parts'),
        help_text=_('Include parts that are marked as inactive or out of stock')
    )

    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Filter by Category'),
        help_text=_('Export only parts from specific category')
    )


class VendorLoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-black focus:border-black focus:z-10 sm:text-sm',
        'placeholder': 'Email address'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-black focus:border-black focus:z-10 sm:text-sm',
        'placeholder': 'Password'
    }))


class Vendor2FAForm(forms.Form):
    token = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'shadow-sm focus:ring-black focus:border-black block w-full sm:text-sm border-gray-300 rounded-md text-center tracking-widest text-2xl font-mono',
            'placeholder': '000000',
            'autocomplete': 'one-time-code',
            'pattern': '[0-9]*',
            'inputmode': 'numeric'
        }),
        help_text='Enter the 6-digit code from your authenticator app'
    )


class VendorPasswordResetForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-black focus:border-black sm:text-sm',
        'placeholder': 'Email address'
    }))


class VendorSettingsForm(forms.Form):
    # Basic Information
    business_name = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-black focus:ring-1 focus:ring-black text-sm transition-colors'}))
    registration_number = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-black focus:ring-1 focus:ring-black text-sm transition-colors'}))
    business_structure = forms.ChoiceField(choices=VendorProfile.BUSINESS_TYPES, required=False, widget=forms.Select(attrs={'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-black focus:ring-1 focus:ring-black text-sm transition-colors'}))
    establishment_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-black focus:ring-1 focus:ring-black text-sm transition-colors', 'type': 'date'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-black focus:ring-1 focus:ring-black text-sm transition-colors', 'rows': 4}), required=False)
    
    # Contact Details
    contact_person_name = forms.CharField(max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-black focus:ring-1 focus:ring-black text-sm transition-colors'}))
    contact_person_title = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-black focus:ring-1 focus:ring-black text-sm transition-colors'}))
    contact_email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-black focus:ring-1 focus:ring-black text-sm transition-colors'}))
    contact_phone = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-black focus:ring-1 focus:ring-black text-sm transition-colors'}))
    
    # Address
    address = forms.CharField(widget=forms.Textarea(attrs={'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-black focus:ring-1 focus:ring-black text-sm transition-colors', 'rows': 3}))
    city = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-black focus:ring-1 focus:ring-black text-sm transition-colors'}))
    zip_code = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-black focus:ring-1 focus:ring-black text-sm transition-colors'}))
    
    # Logo & Documents
    logo = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'absolute inset-0 w-full h-full opacity-0 cursor-pointer'}))
    cr_document = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control-file'}))
    business_license = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control-file'}))
    vat_certificate = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control-file'}))
    commercial_invoice_sample = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control-file'}))
    quality_certificate = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control-file'}))
    insurance_certificate = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control-file'}))
    supplier_certification = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control-file'}))
    
    # Bank Details
    bank_name = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-black focus:ring-1 focus:ring-black text-sm transition-colors'}))
    bank_branch = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-black focus:ring-1 focus:ring-black text-sm transition-colors'}))
    account_holder_name = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-black focus:ring-1 focus:ring-black text-sm transition-colors'}))
    account_number = forms.CharField(max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-black focus:ring-1 focus:ring-black text-sm transition-colors'}))
    iban = forms.CharField(max_length=34, required=False, widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-black focus:ring-1 focus:ring-black text-sm transition-colors'}))
    swift_code = forms.CharField(max_length=11, required=False, widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-black focus:ring-1 focus:ring-black text-sm transition-colors'}))
    
    # Business Details (Financial & Additional)
    tax_id = forms.CharField(max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-black focus:ring-1 focus:ring-black text-sm transition-colors'}))
    preferred_currency = forms.ChoiceField(choices=(), required=False, widget=forms.Select(attrs={'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-black focus:ring-1 focus:ring-black text-sm transition-colors'}))
    payment_terms = forms.ChoiceField(choices=[('net_15', 'Net 15 days'), ('net_30', 'Net 30 days'), ('net_45', 'Net 45 days'), ('net_60', 'Net 60 days'), ('cod', 'Cash on Delivery'), ('prepaid', 'Prepaid')], required=False, widget=forms.Select(attrs={'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-black focus:ring-1 focus:ring-black text-sm transition-colors'}))
    
    # Additional Info
    expected_monthly_volume = forms.DecimalField(required=False, widget=forms.NumberInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-black focus:ring-1 focus:ring-black text-sm transition-colors'}))
    years_in_business = forms.IntegerField(required=False, widget=forms.NumberInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-black focus:ring-1 focus:ring-black text-sm transition-colors'}))
    product_categories = forms.CharField(widget=forms.Textarea(attrs={'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-black focus:ring-1 focus:ring-black text-sm transition-colors', 'rows': 3}), required=False)
    references = forms.CharField(widget=forms.Textarea(attrs={'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-black focus:ring-1 focus:ring-black text-sm transition-colors', 'rows': 3}), required=False)

    def __init__(self, *args, **kwargs):
        self.business_partner = kwargs.pop('business_partner', None)
        super().__init__(*args, **kwargs)
        if self.business_partner:
            self.fields['business_name'].initial = self.business_partner.name
            self.fields['registration_number'].initial = self.business_partner.legal_identifier
            self.fields['description'].initial = self.business_partner.description
            
            primary_contact_email = self.business_partner.contacts.filter(contact_type='email', is_primary=True).first()
            if primary_contact_email:
                self.fields['contact_email'].initial = primary_contact_email.value
                
            primary_contact_phone = self.business_partner.contacts.filter(contact_type='phone', is_primary=True).first()
            if primary_contact_phone:
                self.fields['contact_phone'].initial = primary_contact_phone.value
                
            primary_address = self.business_partner.addresses.filter(is_primary=True).first()
            if primary_address:
                self.fields['address'].initial = primary_address.street
                self.fields['city'].initial = primary_address.city
                self.fields['zip_code'].initial = primary_address.postal_code
            
            # Initialize vendor profile fields
            if hasattr(self.business_partner, 'vendor_profile'):
                vendor_profile = self.business_partner.vendor_profile
                self.fields['tax_id'].initial = vendor_profile.tax_id
                self.fields['preferred_currency'].initial = vendor_profile.preferred_currency
                self.fields['payment_terms'].initial = vendor_profile.payment_terms
                
                # New fields initialization
                self.fields['business_structure'].initial = vendor_profile.business_structure
                self.fields['establishment_date'].initial = vendor_profile.establishment_date
                self.fields['contact_person_name'].initial = vendor_profile.contact_person_name
                self.fields['contact_person_title'].initial = vendor_profile.contact_person_title
                self.fields['swift_code'].initial = vendor_profile.swift_code
                self.fields['expected_monthly_volume'].initial = vendor_profile.expected_monthly_volume
                self.fields['product_categories'].initial = vendor_profile.product_categories
                self.fields['years_in_business'].initial = vendor_profile.years_in_business
                self.fields['references'].initial = vendor_profile.references
                
                # Parse bank details from text field
                if vendor_profile.bank_account_details:
                    bank_lines = vendor_profile.bank_account_details.strip().split('\n')
                    for line in bank_lines:
                        if line.startswith('Bank:'):
                            self.fields['bank_name'].initial = line.replace('Bank:', '').strip()
                        elif line.startswith('Branch:'):
                            self.fields['bank_branch'].initial = line.replace('Branch:', '').strip()
                        elif line.startswith('Account Holder:'):
                            self.fields['account_holder_name'].initial = line.replace('Account Holder:', '').strip()
                        elif line.startswith('Account Number:'):
                            self.fields['account_number'].initial = line.replace('Account Number:', '').strip()
                        elif line.startswith('IBAN:'):
                            self.fields['iban'].initial = line.replace('IBAN:', '').strip()
                
                # Initialize document fields with existing files
                document_fields = [
                    'cr_document', 'business_license', 'vat_certificate',
                    'commercial_invoice_sample', 'quality_certificate',
                    'insurance_certificate', 'supplier_certification'
                ]
                for field_name in document_fields:
                    document_file = getattr(vendor_profile, field_name, None)
                    if document_file:
                        # For file fields, we need to set the initial value to show existing file
                        self.fields[field_name].initial = document_file

        try:
            from core.models import Currency

            active_currencies = Currency.objects.filter(is_active=True).order_by('code')
            currency_choices = [(currency.code, f"{currency.code} - {currency.name}") for currency in active_currencies]

            initial_currency = self.fields['preferred_currency'].initial
            if initial_currency and initial_currency not in dict(currency_choices):
                # Find the currency object to get full name for initial currency
                try:
                    initial_currency_obj = Currency.objects.get(code=initial_currency)
                    initial_display = f"{initial_currency_obj.code} - {initial_currency_obj.name}"
                except Currency.DoesNotExist:
                    initial_display = initial_currency
                currency_choices = [(initial_currency, initial_display)] + currency_choices

            self.fields['preferred_currency'].choices = currency_choices
        except ImportError:
            # Fallback to 6 common currencies if core app is not available
            self.fields['preferred_currency'].choices = [
                ('USD', 'US Dollar (USD)'), ('EUR', 'Euro (EUR)'), ('GBP', 'British Pound (GBP)'),
                ('AED', 'UAE Dirham (AED)'), ('SAR', 'Saudi Riyal (SAR)'), ('KWD', 'Kuwaiti Dinar (KWD)')
            ]
        except Exception as e:
            # Log the error and provide fallback currencies
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error loading currency choices: {e}")
            self.fields['preferred_currency'].choices = [
                ('USD', 'US Dollar (USD)'), ('EUR', 'Euro (EUR)'), ('GBP', 'British Pound (GBP)'),
                ('AED', 'UAE Dirham (AED)'), ('SAR', 'Saudi Riyal (SAR)'), ('KWD', 'Kuwaiti Dinar (KWD)')
            ]

    def save(self):
        if not self.business_partner:
            return
            
        self.business_partner.name = self.cleaned_data['business_name']
        self.business_partner.legal_identifier = self.cleaned_data['registration_number']
        self.business_partner.description = self.cleaned_data['description']
        if self.cleaned_data.get('logo'):
            self.business_partner.logo = self.cleaned_data['logo']
        self.business_partner.save()
        
        # Update contacts
        from .models import ContactInfo, Address
        
        # Email
        ContactInfo.objects.update_or_create(
            business_partner=self.business_partner,
            contact_type='email',
            is_primary=True,
            defaults={'value': self.cleaned_data['contact_email']}
        )
        
        # Phone
        ContactInfo.objects.update_or_create(
            business_partner=self.business_partner,
            contact_type='phone',
            is_primary=True,
            defaults={'value': self.cleaned_data['contact_phone']}
        )
        
        # Address
        Address.objects.update_or_create(
            business_partner=self.business_partner,
            is_primary=True,
            defaults={
                'street': self.cleaned_data['address'],
                'city': self.cleaned_data['city'],
                'postal_code': self.cleaned_data['zip_code'],
                'country': 'Saudi Arabia', # Default
                'address_type': 'office' # Default
            }
        )
        
        # Update vendor profile fields
        if hasattr(self.business_partner, 'vendor_profile'):
            vendor_profile = self.business_partner.vendor_profile
            vendor_profile.tax_id = self.cleaned_data['tax_id']
            vendor_profile.preferred_currency = self.cleaned_data['preferred_currency']
            vendor_profile.payment_terms = self.cleaned_data['payment_terms']
            
            # Save new fields
            vendor_profile.business_structure = self.cleaned_data['business_structure']
            vendor_profile.establishment_date = self.cleaned_data['establishment_date']
            vendor_profile.contact_person_name = self.cleaned_data['contact_person_name']
            vendor_profile.contact_person_title = self.cleaned_data['contact_person_title']
            vendor_profile.swift_code = self.cleaned_data['swift_code']
            vendor_profile.expected_monthly_volume = self.cleaned_data['expected_monthly_volume']
            vendor_profile.product_categories = self.cleaned_data['product_categories']
            vendor_profile.years_in_business = self.cleaned_data['years_in_business']
            vendor_profile.references = self.cleaned_data['references']
            
            if self.cleaned_data.get('cr_document'):
                vendor_profile.cr_document = self.cleaned_data['cr_document']
            if self.cleaned_data.get('business_license'):
                vendor_profile.business_license = self.cleaned_data['business_license']
            
            # Save additional documents
            if self.cleaned_data.get('vat_certificate'):
                vendor_profile.vat_certificate = self.cleaned_data['vat_certificate']
            if self.cleaned_data.get('commercial_invoice_sample'):
                vendor_profile.commercial_invoice_sample = self.cleaned_data['commercial_invoice_sample']
            if self.cleaned_data.get('quality_certificate'):
                vendor_profile.quality_certificate = self.cleaned_data['quality_certificate']
            if self.cleaned_data.get('insurance_certificate'):
                vendor_profile.insurance_certificate = self.cleaned_data['insurance_certificate']
            if self.cleaned_data.get('supplier_certification'):
                vendor_profile.supplier_certification = self.cleaned_data['supplier_certification']
            
            # Build bank details from form fields
            bank_details = []
            if self.cleaned_data['bank_name']:
                bank_details.append(f"Bank: {self.cleaned_data['bank_name']}")
            if self.cleaned_data['bank_branch']:
                bank_details.append(f"Branch: {self.cleaned_data['bank_branch']}")
            if self.cleaned_data['account_holder_name']:
                bank_details.append(f"Account Holder: {self.cleaned_data['account_holder_name']}")
            if self.cleaned_data['account_number']:
                bank_details.append(f"Account Number: {self.cleaned_data['account_number']}")
            if self.cleaned_data['iban']:
                bank_details.append(f"IBAN: {self.cleaned_data['iban']}")
            
            vendor_profile.bank_account_details = '\n'.join(bank_details) if bank_details else None
            vendor_profile.save()


class VendorApplicationReviewForm(forms.Form):
    """Form for reviewing vendor applications"""
    
    REVIEW_ACTIONS = [
        ('approve', 'Approve Application'),
        ('reject', 'Reject Application'),
        ('request_info', 'Request Additional Information'),
        ('escalate', 'Escalate for Review'),
    ]
    
    action = forms.ChoiceField(
        choices=REVIEW_ACTIONS,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label="Review Action"
    )
    
    review_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Enter your review notes and observations...'
        }),
        required=False,
        label="Review Notes"
    )
    
    rejection_reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'If rejecting, provide detailed reason...'
        }),
        required=False,
        label="Rejection Reason (if applicable)"
    )
    
    required_info = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Specify what additional information is needed...'
        }),
        required=False,
        label="Required Information (if requesting info)"
    )
    
    escalation_reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Explain why this case needs escalation...'
        }),
        required=False,
        label="Escalation Reason (if escalating)"
    )
    
    escalation_level = forms.ChoiceField(
        choices=[(1, 'Level 1 - Senior Reviewer'), (2, 'Level 2 - Manager'), 
                (3, 'Level 3 - Director'), (4, 'Level 4 - Executive')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Escalation Level"
    )
    
    def clean(self):
        """Validate form based on selected action"""
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        
        if action == 'reject' and not cleaned_data.get('rejection_reason'):
            raise ValidationError("Rejection reason is required when rejecting an application.")
        
        if action == 'request_info' and not cleaned_data.get('required_info'):
            raise ValidationError("Required information details are needed.")
        
        if action == 'escalate' and not cleaned_data.get('escalation_reason'):
            raise ValidationError("Escalation reason is required.")
        
        return cleaned_data
