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


class VendorPartForm(forms.ModelForm):
    """
    Comprehensive form for vendor part management with ALL fields from Excel Parts sheet.
    Organized in sections: Basic Info, Inventory, Pricing, Compatibility, Advanced
    """
    
    # Additional fields not in the Part model but needed for vendor management
    cost_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        help_text="Cost price for profit margin calculation",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Cost price',
            'data-section': 'pricing',
            'id': 'cost-price',
            'hx-trigger': 'keyup changed delay:300ms',
            'hx-post': '/vendor/calculate-profit-margin/',
            'hx-target': '#profit-margin-display',
            'hx-include': '#selling-price'
        })
    )
    
    inventory_threshold = forms.IntegerField(
        required=False,
        help_text="Alert when stock falls below this level",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'placeholder': 'Low stock alert threshold',
            'data-section': 'inventory'
        })
    )

    class Meta:
        model = Part
        fields = [
            # ==================== BASIC INFO SECTION ====================
            'parts_number', 'material_description', 'material_description_ar',
            'manufacturer_part_number', 'manufacturer_oem_number', 'category', 'brand',
            'base_unit_of_measure', 'gross_weight', 'net_weight', 'size_dimensions',
            'image', 'image_url', 'warranty_period',
            
            # ==================== INVENTORY SECTION ====================
            'quantity', 'safety_stock', 'minimum_safety_stock', 'reorder_point',
            'minimum_order_quantity', 'storage_location', 'warehouse_number',
            'storage_bin', 'plant', 'abc_indicator',
            
            # ==================== PRICING SECTION ====================
            'price', 'standard_price', 'moving_average_price', 'price_unit_peinh',
            'valuation_class', 'price_control_indicator',
            
            # ==================== COMPATIBILITY SECTION ====================
            'vehicle_variants',
            
            # ==================== ADVANCED SECTION ====================
            'material_type', 'material_group', 'external_material_group', 'division',
            'old_material_number', 'expiration_xchpf', 'planned_delivery_time_days',
            'goods_receipt_processing_time_days', 'weight_of_unit', 'sales_organization',
            'distribution_channel', 'tax_classification_material', 'industry_sector',
            'material_pricing_group', 'account_assignment_group', 'general_item_category_group',
            'item_category_group', 'availability_check', 'transportation_group',
            'loading_group', 'profit_center', 'purchasing_group', 'mrp_group',
            'mrp_type', 'lot_size', 'mrp_controller', 'procurement_type',
            'total_replenishment_lead_time', 'forecast_model', 'period_indicator',
            'historical_periods', 'forecast_periods', 'initialization_indicator',
            'valuation_category',
            
            # ==================== STATUS FIELDS ====================
            'slug', 'is_active', 'is_featured',
        ]
    
    def __init__(self, *args, **kwargs):
        self.vendor = kwargs.pop('vendor', None)
        super().__init__(*args, **kwargs)
        
        # Filter vehicle variants to show only active ones
        if 'vehicle_variants' in self.fields:
            from vehicles.models import VehicleVariant
            self.fields['vehicle_variants'].queryset = VehicleVariant.objects.filter(
                is_active=True
            ).select_related('model__make').order_by('model__make__name', 'model__name', 'name')
            
        # Set initial values for new parts
        if not self.instance.pk:
            self.fields['is_active'].initial = True
    
    def clean_parts_number(self):
        """Validate parts number uniqueness for the vendor"""
        parts_number = self.cleaned_data.get('parts_number')
        if not parts_number:
            return parts_number
            
        # Check for uniqueness within vendor's parts
        queryset = Part.objects.filter(
            parts_number=parts_number,
            vendor=self.vendor
        )
        
        # Exclude current instance if editing
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
            
        if queryset.exists():
            raise forms.ValidationError(
                f"A part with number '{parts_number}' already exists in your inventory."
            )
            
        return parts_number
    
    def clean_price(self):
        """Validate selling price"""
        price = self.cleaned_data.get('price')
        cost_price = self.cleaned_data.get('cost_price')
        
        if price is not None and price <= 0:
            raise forms.ValidationError("Selling price must be greater than 0.")
            
        # Warn if selling price is lower than cost price
        if price and cost_price and price < cost_price:
            raise forms.ValidationError(
                f"Selling price ({price}) is lower than cost price ({cost_price}). "
                "This will result in a loss."
            )
            
        return price
    
    def clean_cost_price(self):
        """Validate cost price"""
        cost_price = self.cleaned_data.get('cost_price')
        
        if cost_price is not None and cost_price < 0:
            raise forms.ValidationError("Cost price cannot be negative.")
            
        return cost_price
    
    def clean_inventory_threshold(self):
        """Validate inventory threshold"""
        threshold = self.cleaned_data.get('inventory_threshold')
        quantity = self.cleaned_data.get('quantity', 0)
        
        if threshold is not None and threshold < 0:
            raise forms.ValidationError("Inventory threshold cannot be negative.")
            
        # Warn if current quantity is below threshold
        if threshold and quantity < threshold:
            # This is a warning, not an error - we'll handle it in the view
            pass
            
        return threshold
    
    def clean_quantity(self):
        """Validate quantity"""
        quantity = self.cleaned_data.get('quantity')
        
        if quantity is not None and quantity < 0:
            raise forms.ValidationError("Quantity cannot be negative.")
            
        return quantity
    
    def clean_safety_stock(self):
        """Validate safety stock"""
        safety_stock = self.cleaned_data.get('safety_stock')
        minimum_safety_stock = self.cleaned_data.get('minimum_safety_stock')
        
        if safety_stock is not None and safety_stock < 0:
            raise forms.ValidationError("Safety stock cannot be negative.")
            
        if (safety_stock and minimum_safety_stock and 
            safety_stock < minimum_safety_stock):
            raise forms.ValidationError(
                "Safety stock cannot be less than minimum safety stock."
            )
            
        return safety_stock
    
    def clean_reorder_point(self):
        """Validate reorder point"""
        reorder_point = self.cleaned_data.get('reorder_point')
        safety_stock = self.cleaned_data.get('safety_stock')
        
        if reorder_point is not None and reorder_point < 0:
            raise forms.ValidationError("Reorder point cannot be negative.")
            
        # Reorder point should typically be higher than safety stock
        if (reorder_point and safety_stock and 
            reorder_point < safety_stock):
            raise forms.ValidationError(
                "Reorder point should typically be higher than safety stock."
            )
            
        return reorder_point
    
    def save(self, commit=True):
        """Custom save method to handle vendor assignment and calculations"""
        instance = super().save(commit=False)
        
        # Set vendor if provided
        if self.vendor:
            instance.vendor = self.vendor
            
        # Auto-generate slug if not provided
        if not instance.slug and instance.parts_number:
            from django.utils.text import slugify
            base_slug = slugify(f"{instance.parts_number}-{instance.material_description}")
            instance.slug = base_slug
            
        # Calculate profit margin if both prices are available
        if hasattr(instance, 'cost_price') and instance.cost_price and instance.price:
            instance.profit_margin = ((instance.price - instance.cost_price) / instance.cost_price) * 100
            
        if commit:
            instance.save()
            self.save_m2m()
            
        return instance


class VendorPartSearchForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make required fields
        required_fields = [
            'company_name', 'business_type', 
            'commercial_registration_number', 'legal_identifier'
        ]
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True
        
        # Add help text and placeholders
        self.fields['company_name'].widget.attrs.update({
            'placeholder': 'Enter your legal company name'
        })
        self.fields['commercial_registration_number'].widget.attrs.update({
            'placeholder': 'Enter CR number (e.g., 1010123456)'
        })
        self.fields['legal_identifier'].widget.attrs.update({
            'placeholder': 'Tax ID, VAT number, or other legal identifier'
        })
    
    def clean_commercial_registration_number(self):
        """Validate commercial registration number format"""
        cr_number = self.cleaned_data.get('commercial_registration_number')
        if cr_number:
            # Remove spaces and validate format (Saudi CR format: 10 digits)
            cr_number = re.sub(r'\s+', '', cr_number)
            if not re.match(r'^\d{10}$', cr_number):
                raise ValidationError(
                    'Commercial Registration number must be 10 digits.'
                )
        return cr_number
    
    def clean_company_name(self):
        """Validate company name uniqueness"""
        company_name = self.cleaned_data.get('company_name')
        if company_name:
            # Check if company name already exists in approved applications
            existing = VendorApplication.objects.filter(
                company_name__iexact=company_name,
                status='approved'
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing.exists():
                raise ValidationError(
                    'A vendor with this company name is already registered.'
                )
        return company_name
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.current_step = 1
        if instance.is_step_completed(1):
            instance.status = 'business_details_completed'
        if commit:
            instance.save()
        return instance


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
    
    def clean_file(self):
        """Validate uploaded file"""
        file = self.cleaned_data.get('file')
        
        if not file:
            raise ValidationError(_('Please select a file to upload.'))
        
        # Check file size (10MB limit)
        if file.size > 10 * 1024 * 1024:
            raise ValidationError(_('File size must be less than 10MB.'))
        
        # Check file extension
        allowed_extensions = ['.csv', '.xlsx', '.xls']
        file_extension = os.path.splitext(file.name)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise ValidationError(
                _('Invalid file format. Please upload CSV or Excel files only.')
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
        help_text='Include inactive parts in export'
    )
    
    include_images = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Include image URLs in export'
    )
    
    date_range_start = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        help_text='Export parts created after this date'
    )
    
    date_range_end = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        help_text='Export parts created before this date'
    )
    
    def clean(self):
        """Validate date range"""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('date_range_start')
        end_date = cleaned_data.get('date_range_end')
        
        if start_date and end_date and start_date > end_date:
            raise ValidationError(_('Start date must be before end date.'))
        
        return cleaned_data


class VendorPartForm(forms.ModelForm):
    """
    Comprehensive form for vendors to manage their parts with ALL Excel fields.
    Organized in sections: Basic Info, Inventory, Pricing, Compatibility, Advanced.
    Includes vehicle compatibility multi-select and real-time profit margin calculation.
    """
    
    # Additional fields for enhanced functionality
    cost_price = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Cost price for profit calculation',
            'id': 'cost-price',
            'hx-trigger': 'keyup changed delay:300ms',
            'hx-post': '/vendor/calculate-profit-margin/',
            'hx-target': '#profit-margin-display',
            'hx-include': '#selling-price'
        }),
        help_text="Enter cost price to calculate profit margin automatically"
    )
    
    inventory_threshold = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'placeholder': 'Low stock alert threshold'
        }),
        help_text="Alert when stock falls below this level"
    )
    
    class Meta:
        model = Part
        fields = [
            # BASIC INFO SECTION
            'parts_number', 'material_description', 'material_description_ar',
            'manufacturer_part_number', 'manufacturer_oem_number', 'category', 'brand',
            'base_unit_of_measure', 'gross_weight', 'net_weight', 'size_dimensions',
            'image', 'image_url', 'warranty_period',
            
            # INVENTORY SECTION
            'quantity', 'safety_stock', 'minimum_safety_stock', 'reorder_point',
            'minimum_order_quantity', 'storage_location', 'warehouse_number', 'storage_bin',
            'plant', 'abc_indicator',
            
            # PRICING SECTION
            'price', 'standard_price', 'moving_average_price', 'price_unit_peinh',
            'valuation_class', 'price_control_indicator',
            
            # COMPATIBILITY SECTION
            'vehicle_variants',
            
            # ADVANCED SECTION
            'material_type', 'material_group', 'division', 'external_material_group',
            'old_material_number', 'expiration_xchpf', 'planned_delivery_time_days',
            'goods_receipt_processing_time_days', 'mrp_type', 'mrp_group', 'mrp_controller',
            'procurement_type', 'total_replenishment_lead_time', 'forecast_model',
            'period_indicator', 'historical_periods', 'forecast_periods',
            'initialization_indicator', 'valuation_category', 'weight_of_unit',
            'sales_organization', 'distribution_channel', 'tax_classification_material',
            'industry_sector', 'material_pricing_group', 'account_assignment_group',
            'general_item_category_group', 'item_category_group', 'availability_check',
            'transportation_group', 'loading_group', 'profit_center', 'purchasing_group',
            'lot_size',
            
            # STATUS FIELDS
            'slug', 'is_active', 'is_featured'
        ]
        
        widgets = {
            # ==================== BASIC INFO SECTION ====================
            'parts_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Unique parts identification number',
                'data-section': 'basic-info'
            }),
            'material_description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Short description of the material/part',
                'data-section': 'basic-info'
            }),
            'material_description_ar': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Arabic description (optional)',
                'data-section': 'basic-info'
            }),
            'manufacturer_part_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Manufacturer part number (up to 40 digits)',
                'data-section': 'basic-info'
            }),
            'manufacturer_oem_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'OEM number',
                'data-section': 'basic-info'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control',
                'data-section': 'basic-info'
            }),
            'brand': forms.Select(attrs={
                'class': 'form-control',
                'data-section': 'basic-info'
            }),
            'base_unit_of_measure': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'EA, KG, L, etc.',
                'data-section': 'basic-info'
            }),
            'gross_weight': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.001',
                'placeholder': 'Gross weight in kg',
                'data-section': 'basic-info'
            }),
            'net_weight': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.001',
                'placeholder': 'Net weight in kg',
                'data-section': 'basic-info'
            }),
            'size_dimensions': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Physical dimensions',
                'data-section': 'basic-info'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'data-section': 'basic-info'
            }),
            'image_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Alternative image URL',
                'data-section': 'basic-info'
            }),
            'warranty_period': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'Warranty period in months',
                'data-section': 'basic-info'
            }),
            
            # ==================== INVENTORY SECTION ====================
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'Available quantity',
                'data-section': 'inventory',
                'hx-trigger': 'keyup changed delay:300ms',
                'hx-post': '/vendor/validate-inventory/',
                'hx-target': '#inventory-alerts',
                'hx-include': '[data-section="inventory"]'
            }),
            'safety_stock': InventoryThresholdWidget(attrs={
                'step': '0.001',
                'placeholder': 'Safety stock quantity',
                'data-section': 'inventory',
                'data-inventory-field': 'safety_stock'
            }),
            'minimum_safety_stock': InventoryThresholdWidget(attrs={
                'step': '0.001',
                'placeholder': 'Minimum safety stock',
                'data-section': 'inventory',
                'data-inventory-field': 'minimum_safety_stock'
            }),
            'reorder_point': InventoryThresholdWidget(attrs={
                'step': '0.001',
                'placeholder': 'Reorder point quantity',
                'data-section': 'inventory',
                'data-inventory-field': 'reorder_point'
            }),
            'inventory_threshold': InventoryThresholdWidget(attrs={
                'step': '0.001',
                'placeholder': 'Inventory threshold for alerts',
                'data-section': 'inventory',
                'data-inventory-field': 'inventory_threshold'
            }),
            'minimum_order_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.001',
                'placeholder': 'Minimum order quantity',
                'data-section': 'inventory'
            }),
            'storage_location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Storage location code',
                'data-section': 'inventory'
            }),
            'warehouse_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Warehouse number',
                'data-section': 'inventory'
            }),
            'storage_bin': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Storage bin location',
                'data-section': 'inventory'
            }),
            'plant': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Plant code',
                'data-section': 'inventory'
            }),
            'abc_indicator': forms.Select(attrs={
                'class': 'form-control',
                'data-section': 'inventory'
            }),
            
            # ==================== PRICING SECTION ====================
            'price': ProfitMarginCalculatorWidget(attrs={
                'min': '0.01',
                'placeholder': 'Selling price',
                'data-section': 'pricing',
                'id': 'selling-price',
            }),
            'standard_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Standard price',
                'data-section': 'pricing'
            }),
            'moving_average_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Moving average price',
                'data-section': 'pricing'
            }),
            'price_unit_peinh': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.001',
                'placeholder': 'Price unit (PEINH)',
                'data-section': 'pricing'
            }),
            'valuation_class': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Valuation class code',
                'data-section': 'pricing'
            }),
            'price_control_indicator': forms.Select(attrs={
                'class': 'form-control',
                'data-section': 'pricing'
            }),
            
            # ==================== COMPATIBILITY SECTION ====================
            'vehicle_variants': VehicleVariantMultiSelectWidget(attrs={
                'data-section': 'compatibility',
                'data-placeholder': 'Search and select compatible vehicle variants...',
            }),
            
            # ==================== ADVANCED SECTION ====================
            'material_type': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'FERT, HAWA, etc.',
                'data-section': 'advanced'
            }),
            'material_group': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Material group classification',
                'data-section': 'advanced'
            }),
            'external_material_group': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'External material group',
                'data-section': 'advanced'
            }),
            'division': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Division code',
                'data-section': 'advanced'
            }),
            'old_material_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Previous material number',
                'data-section': 'advanced'
            }),
            'expiration_xchpf': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Expiration indicator',
                'data-section': 'advanced'
            }),
            'planned_delivery_time_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'Delivery time in days',
                'data-section': 'advanced'
            }),
            'goods_receipt_processing_time_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'Processing time in days',
                'data-section': 'advanced'
            }),
            'weight_of_unit': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.001',
                'placeholder': 'Weight of unit',
                'data-section': 'advanced'
            }),
            'sales_organization': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Sales organization code',
                'data-section': 'advanced'
            }),
            'distribution_channel': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Distribution channel',
                'data-section': 'advanced'
            }),
            'tax_classification_material': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tax classification',
                'data-section': 'advanced'
            }),
            'industry_sector': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Industry sector',
                'data-section': 'advanced'
            }),
            'material_pricing_group': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Material pricing group',
                'data-section': 'advanced'
            }),
            'account_assignment_group': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Account assignment group',
                'data-section': 'advanced'
            }),
            'general_item_category_group': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'General item category group',
                'data-section': 'advanced'
            }),
            'item_category_group': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Item category group',
                'data-section': 'advanced'
            }),
            'availability_check': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Availability check',
                'data-section': 'advanced'
            }),
            'transportation_group': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Transportation group',
                'data-section': 'advanced'
            }),
            'loading_group': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Loading group',
                'data-section': 'advanced'
            }),
            'profit_center': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Profit center',
                'data-section': 'advanced'
            }),
            'purchasing_group': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Purchasing group',
                'data-section': 'advanced'
            }),
            'mrp_group': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'MRP group',
                'data-section': 'advanced'
            }),
            'mrp_type': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'MRP type',
                'data-section': 'advanced'
            }),
            'lot_size': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.001',
                'placeholder': 'Lot size',
                'data-section': 'advanced'
            }),
            'mrp_controller': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'MRP controller',
                'data-section': 'advanced'
            }),
            'procurement_type': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Procurement type',
                'data-section': 'advanced'
            }),
            'total_replenishment_lead_time': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'Total replenishment lead time',
                'data-section': 'advanced'
            }),
            'forecast_model': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Forecast model',
                'data-section': 'advanced'
            }),
            'period_indicator': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Period indicator',
                'data-section': 'advanced'
            }),
            'historical_periods': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'Historical periods',
                'data-section': 'advanced'
            }),
            'forecast_periods': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'Forecast periods',
                'data-section': 'advanced'
            }),
            'initialization_indicator': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Initialization indicator',
                'data-section': 'advanced'
            }),
            'valuation_category': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Valuation category',
                'data-section': 'advanced'
            }),
            
            # ==================== STATUS FIELDS ====================
            'slug': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'URL-friendly identifier (auto-generated if empty)',
                'data-section': 'status'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'data-section': 'status'
            }),
            'is_featured': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'data-section': 'status'
            }),
        }

    def __init__(self, *args, **kwargs):
        vendor = kwargs.pop('vendor', None)
        super().__init__(*args, **kwargs)
        
        # Filter category and brand choices based on vendor if provided
        if vendor:
            # Filter categories and brands based on vendor's parts if needed
            pass


class VendorPartSearchForm(forms.Form):
    """
    Advanced search form for vendors to filter their parts.
    Includes all Excel fields for comprehensive filtering.
    """
    
    # Basic search
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search parts, descriptions, numbers...'
        })
    )
    
    # Category and Brand filters
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
    
    # Status filters
    is_active = forms.ChoiceField(
        choices=[('', 'All'), ('true', 'Active'), ('false', 'Inactive')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    is_featured = forms.ChoiceField(
        choices=[('', 'All'), ('true', 'Featured'), ('false', 'Not Featured')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Stock filters
    stock_status = forms.ChoiceField(
        choices=[
            ('', 'All Stock Levels'),
            ('in_stock', 'In Stock'),
            ('low_stock', 'Low Stock'),
            ('out_of_stock', 'Out of Stock')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Price range
    min_price = forms.DecimalField(
        required=False,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min price',
            'step': '0.01'
        })
    )
    
    max_price = forms.DecimalField(
        required=False,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max price',
            'step': '0.01'
        })
    )
    
    # Vendor-specific filters (Excel fields)
    material_type = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Material type (FERT, HAWA, etc.)'
        })
    )
    
    plant = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Plant code'
        })
    )
    
    material_group = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Material group'
        })
    )
    
    abc_indicator = forms.ChoiceField(
        choices=[('', 'All'), ('A', 'A'), ('B', 'B'), ('C', 'C')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Sorting
    sort_by = forms.ChoiceField(
        choices=[
            ('-created_at', 'Newest First'),
            ('created_at', 'Oldest First'),
            ('parts_number', 'Parts Number A-Z'),
            ('-parts_number', 'Parts Number Z-A'),
            ('material_description', 'Description A-Z'),
            ('-material_description', 'Description Z-A'),
            ('price', 'Price Low to High'),
            ('-price', 'Price High to Low'),
            ('quantity', 'Stock Low to High'),
            ('-quantity', 'Stock High to Low'),
        ],
        required=False,
        initial='-created_at',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        """Validate price range"""
        cleaned_data = super().clean()
        min_price = cleaned_data.get('min_price')
        max_price = cleaned_data.get('max_price')
        
        if min_price and max_price and min_price > max_price:
            raise ValidationError(_('Minimum price cannot be greater than maximum price.'))
        
        return cleaned_data


class VendorPartBulkUpdateForm(forms.Form):
    """
    Form for bulk updating vendor parts.
    Allows vendors to update multiple parts at once.
    """
    
    # Fields that can be bulk updated
    price_adjustment_type = forms.ChoiceField(
        choices=[
            ('', 'No Price Change'),
            ('percentage_increase', 'Percentage Increase'),
            ('percentage_decrease', 'Percentage Decrease'),
            ('fixed_amount_increase', 'Fixed Amount Increase'),
            ('fixed_amount_decrease', 'Fixed Amount Decrease'),
            ('set_price', 'Set Fixed Price'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    price_adjustment_value = forms.DecimalField(
        required=False,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Adjustment value',
            'step': '0.01'
        })
    )
    
    quantity_adjustment_type = forms.ChoiceField(
        choices=[
            ('', 'No Quantity Change'),
            ('add', 'Add to Current Stock'),
            ('subtract', 'Subtract from Current Stock'),
            ('set', 'Set Fixed Quantity'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    quantity_adjustment_value = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Quantity value'
        })
    )
    
    # Status updates
    set_active_status = forms.ChoiceField(
        choices=[('', 'No Change'), ('true', 'Set Active'), ('false', 'Set Inactive')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    set_featured_status = forms.ChoiceField(
        choices=[('', 'No Change'), ('true', 'Set Featured'), ('false', 'Remove Featured')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Vendor-specific bulk updates
    update_material_type = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Set material type for selected parts'
        })
    )
    
    update_plant = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Set plant code for selected parts'
        })
    )
    
    update_material_group = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Set material group for selected parts'
        })
    )
    
    def clean(self):
        """Validate bulk update form"""
        cleaned_data = super().clean()
        
        # Validate price adjustment
        price_type = cleaned_data.get('price_adjustment_type')
        price_value = cleaned_data.get('price_adjustment_value')
        
        if price_type and not price_value:
            raise ValidationError(_('Price adjustment value is required when price adjustment type is selected.'))
        
        # Validate quantity adjustment
        quantity_type = cleaned_data.get('quantity_adjustment_type')
        quantity_value = cleaned_data.get('quantity_adjustment_value')
        
        if quantity_type and quantity_value is None:
            raise ValidationError(_('Quantity adjustment value is required when quantity adjustment type is selected.'))
        
        return cleaned_data


# Authentication forms for vendor login and password reset
class VendorLoginForm(forms.Form):
    """Vendor login form with email and password fields"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')
        
        if email and password:
            # Check if user exists and has vendor profile
            try:
                user = User.objects.get(email=email)
                vendor_profile = get_vendor_profile(user)
                
                # Check if vendor profile exists and is approved
                if not vendor_profile:
                    raise ValidationError(
                        'Vendor profile not found. Please complete your vendor registration.'
                    )
                elif not vendor_profile.is_approved:
                    raise ValidationError(
                        'Your vendor application is still under review. Please wait for approval.'
                    )
                
                # Authenticate user
                user = authenticate(username=email, password=password)
                if not user:
                    raise ValidationError('Invalid email or password.')
                    
            except User.DoesNotExist:
                raise ValidationError('Invalid email or password.')
            except VendorProfile.DoesNotExist:
                raise ValidationError('Vendor profile not found.')
        
        return cleaned_data


class VendorPasswordResetForm(forms.Form):
    """Vendor password reset form"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address'
        })
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        
        # Check if user exists and has vendor profile
        try:
            user = User.objects.get(email=email)
            vendor_profile = get_vendor_profile(user)
            
            if not vendor_profile:
                raise ValidationError(
                    'Vendor profile not found. Please complete your vendor registration.'
                )
            elif not vendor_profile.is_approved:
                raise ValidationError(
                    'Your vendor application is still under review. Please wait for approval.'
                )
                
        except User.DoesNotExist:
            raise ValidationError('No account found with this email address.')
        except VendorProfile.DoesNotExist:
            raise ValidationError('Vendor profile not found.')
        
        return email


class Vendor2FAForm(forms.Form):
    """Vendor 2FA verification form"""
    token = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter 6-digit code',
            'autocomplete': 'off'
        })
    )
    
    def clean_token(self):
        token = self.cleaned_data.get('token')
        
        # Validate that token contains only digits
        if not token.isdigit():
            raise ValidationError('Token must contain only digits.')
        
        return token


# Admin forms for reviewing applications
class VendorApplicationReviewForm(forms.ModelForm):
    """Form for admin to review and approve/reject vendor applications"""
    
    REVIEW_ACTIONS = [
        ('approve', 'Approve Application'),
        ('reject', 'Reject Application'),
        ('request_changes', 'Request Changes'),
    ]
    
    action = forms.ChoiceField(
        choices=REVIEW_ACTIONS,
        widget=forms.RadioSelect,
        required=True
    )
    
    class Meta:
        model = VendorApplication
        fields = ['review_notes', 'rejection_reason']
        widgets = {
            'review_notes': forms.Textarea(
                attrs={'rows': 4, 'class': 'form-control'}
            ),
            'rejection_reason': forms.Textarea(
                attrs={'rows': 4, 'class': 'form-control'}
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['review_notes'].required = False
        self.fields['rejection_reason'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        rejection_reason = cleaned_data.get('rejection_reason')
        
        # Require rejection reason for reject and request_changes actions
        if action in ['reject', 'request_changes'] and not rejection_reason:
            raise ValidationError(
                'Rejection reason is required when rejecting or requesting changes.'
            )
        
        return cleaned_data