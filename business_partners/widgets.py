"""
Custom widgets for business partners forms.
"""
from django import forms
from django.utils.safestring import mark_safe
import json


class VehicleVariantMultiSelectWidget(forms.SelectMultiple):
    """
    Custom widget for vehicle variant multi-select with search functionality.
    Provides a searchable dropdown with hierarchical display (Make > Model > Variant).
    """
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'form-control vehicle-variant-multiselect',
            'data-placeholder': 'Search and select compatible vehicles...',
            'data-allow-clear': 'true',
            'data-close-on-select': 'false',
            'multiple': 'multiple',
            'style': 'width: 100%;'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)
    
    def format_value(self, value):
        """Format the value for display."""
        if value is None:
            return []
        if not isinstance(value, (list, tuple)):
            value = [value]
        return [str(v) for v in value]
    
    class Media:
        css = {
            'all': (
                'https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css',
                'business_partners/css/vehicle-variant-widget.css',
            )
        }
        js = (
            'https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js',
            'business_partners/js/vehicle-variant-widget.js',
        )


class ProfitMarginCalculatorWidget(forms.NumberInput):
    """
    Widget for price fields that includes profit margin calculation.
    """
    
    def __init__(self, attrs=None, cost_field_id='cost-price'):
        default_attrs = {
            'class': 'form-control profit-calculator',
            'step': '0.01',
            'data-cost-field': cost_field_id
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)
    
    class Media:
        js = (
            'https://unpkg.com/htmx.org@1.9.10',
            'business_partners/js/profit-calculator.js',
        )


class InventoryThresholdWidget(forms.NumberInput):
    """
    Widget for inventory fields with threshold validation.
    """
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'form-control inventory-threshold',
            'min': '0',
            'data-inventory-field': 'true'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)
    
    class Media:
        js = (
            'https://unpkg.com/htmx.org@1.9.10',
            'business_partners/js/inventory-validator.js',
        )


class SearchableSelectWidget(forms.Select):
    """
    Generic searchable select widget using Select2.
    """
    
    def __init__(self, attrs=None, search_url=None):
        default_attrs = {
            'class': 'form-control searchable-select',
            'data-placeholder': 'Search...',
            'data-allow-clear': 'true',
            'style': 'width: 100%;'
        }
        if search_url:
            default_attrs['data-ajax-url'] = search_url
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)
    
    class Media:
        css = {
            'all': (
                'https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css',
            )
        }
        js = (
            'https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js',
            'business_partners/js/searchable-select.js',
        )