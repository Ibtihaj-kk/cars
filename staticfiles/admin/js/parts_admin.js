// Parts Admin Custom JavaScript

(function($) {
    'use strict';
    
    $(document).ready(function() {
        // Add helpful tooltips for complex fields
        const fieldHelp = {
            'material_type': 'Type of material (FERT, HALB, ROH, etc.)',
            'abc_indicator': 'ABC analysis classification (A=high value, B=medium, C=low)',
            'procurement_type': 'F=In-house production, E=External procurement, B=Both',
            'mrp_type': 'Material Requirements Planning type',
            'price_control_indicator': 'S=Standard Price, V=Moving Average Price'
        };
        
        // Add tooltips to fields
        Object.keys(fieldHelp).forEach(function(fieldName) {
            const field = $('.field-' + fieldName + ' input, .field-' + fieldName + ' select');
            if (field.length) {
                field.attr('title', fieldHelp[fieldName]);
            }
        });
        
        // Highlight user-visible vs vendor-only fields
        $('.field-material_description, .field-material_description_ar, .field-base_unit_of_measure, .field-gross_weight, .field-net_weight, .field-weight_of_unit, .field-size_dimensions, .field-manufacturer_part_number, .field-manufacturer_oem_number').addClass('user-visible-field');
        
        // Add visual indicators
        $('.user-visible-field').prepend('<span class="field-indicator user-visible" title="Visible to end users">👁️</span>');
        
        // Collapsible fieldsets enhancement
        $('.collapse h2').click(function() {
            $(this).next('.form-row, .fieldBox').slideToggle();
        });
        
        // Auto-generate slug from parts_number if name is empty
        $('#id_parts_number').on('input', function() {
            const partsNumber = $(this).val();
            const nameField = $('#id_name');
            if (!nameField.val() && partsNumber) {
                nameField.val(partsNumber);
                // Trigger slug generation if available
                if (typeof window.URLify !== 'undefined') {
                    $('#id_slug').val(window.URLify(partsNumber, 50));
                }
            }
        });
    });
    
})(django.jQuery);