/**
 * Vehicle Variant Multi-Select Widget
 * Provides searchable multi-select functionality for vehicle compatibility
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all vehicle variant multi-select widgets
    const vehicleSelects = document.querySelectorAll('.vehicle-variant-multiselect');
    
    vehicleSelects.forEach(function(select) {
        initializeVehicleVariantSelect(select);
    });
});

function initializeVehicleVariantSelect(selectElement) {
    const $select = $(selectElement);
    
    // Initialize Select2 with custom configuration
    $select.select2({
        placeholder: 'Search and select compatible vehicles...',
        allowClear: true,
        closeOnSelect: false,
        width: '100%',
        templateResult: formatVehicleVariant,
        templateSelection: formatVehicleVariantSelection,
        escapeMarkup: function(markup) {
            return markup;
        },
        language: {
            noResults: function() {
                return '<div class="select2-no-results">No vehicles found. Try a different search term.</div>';
            },
            searching: function() {
                return '<div class="select2-searching">Searching vehicles...</div>';
            }
        }
    });
    
    // Add custom styling and behavior
    $select.on('select2:open', function() {
        // Focus on search input when opened
        setTimeout(function() {
            document.querySelector('.select2-search__field').focus();
        }, 100);
    });
    
    // Handle selection changes
    $select.on('change', function() {
        updateCompatibilityDisplay();
        validateVehicleSelection();
    });
}

function formatVehicleVariant(variant) {
    if (!variant.id) {
        return variant.text;
    }
    
    // Parse the variant text to extract make, model, variant, and year
    const parts = variant.text.split(' ');
    if (parts.length < 4) {
        return variant.text;
    }
    
    const make = parts[0];
    const model = parts[1];
    const variantName = parts.slice(2, -1).join(' ');
    const year = parts[parts.length - 1].replace(/[()]/g, '');
    
    return $(`
        <div class="vehicle-variant-option">
            <div class="vehicle-make">${make}</div>
            <div class="vehicle-details">
                <span class="vehicle-model">${model}</span>
                <span class="vehicle-variant">${variantName}</span>
                <span class="vehicle-year">(${year})</span>
            </div>
        </div>
    `);
}

function formatVehicleVariantSelection(variant) {
    if (!variant.id) {
        return variant.text;
    }
    
    // Show abbreviated format in selection
    const parts = variant.text.split(' ');
    if (parts.length >= 4) {
        const make = parts[0];
        const model = parts[1];
        const year = parts[parts.length - 1].replace(/[()]/g, '');
        return `${make} ${model} (${year})`;
    }
    
    return variant.text;
}

function updateCompatibilityDisplay() {
    const selectedVariants = $('.vehicle-variant-multiselect').val() || [];
    const compatibilityCount = document.getElementById('compatibility-count');
    
    if (compatibilityCount) {
        compatibilityCount.textContent = selectedVariants.length;
        
        // Update display based on selection count
        const compatibilitySection = document.querySelector('.compatibility-section');
        if (compatibilitySection) {
            if (selectedVariants.length > 0) {
                compatibilitySection.classList.add('has-selections');
            } else {
                compatibilitySection.classList.remove('has-selections');
            }
        }
    }
    
    // Update compatibility summary
    updateCompatibilitySummary(selectedVariants);
}

function updateCompatibilitySummary(selectedVariants) {
    const summaryContainer = document.getElementById('compatibility-summary');
    if (!summaryContainer || selectedVariants.length === 0) {
        if (summaryContainer) {
            summaryContainer.innerHTML = '<p class="text-muted">No vehicles selected</p>';
        }
        return;
    }
    
    // Group variants by make
    const variantsByMake = {};
    selectedVariants.forEach(function(variantId) {
        const option = document.querySelector(`option[value="${variantId}"]`);
        if (option) {
            const text = option.textContent;
            const make = text.split(' ')[0];
            if (!variantsByMake[make]) {
                variantsByMake[make] = [];
            }
            variantsByMake[make].push(text);
        }
    });
    
    // Create summary HTML
    let summaryHTML = '<div class="compatibility-summary-content">';
    Object.keys(variantsByMake).forEach(function(make) {
        summaryHTML += `
            <div class="make-group">
                <h6 class="make-name">${make} (${variantsByMake[make].length})</h6>
                <div class="variant-list">
                    ${variantsByMake[make].map(variant => `<span class="variant-tag">${variant}</span>`).join('')}
                </div>
            </div>
        `;
    });
    summaryHTML += '</div>';
    
    summaryContainer.innerHTML = summaryHTML;
}

function validateVehicleSelection() {
    const selectedVariants = $('.vehicle-variant-multiselect').val() || [];
    const validationContainer = document.getElementById('vehicle-validation');
    
    if (!validationContainer) return;
    
    // Clear previous validation messages
    validationContainer.innerHTML = '';
    
    if (selectedVariants.length === 0) {
        validationContainer.innerHTML = `
            <div class="alert alert-warning alert-sm">
                <i class="fas fa-exclamation-triangle"></i>
                Consider adding vehicle compatibility to help customers find this part.
            </div>
        `;
    } else if (selectedVariants.length > 50) {
        validationContainer.innerHTML = `
            <div class="alert alert-info alert-sm">
                <i class="fas fa-info-circle"></i>
                You've selected many vehicles (${selectedVariants.length}). Consider if this part is truly universal.
            </div>
        `;
    } else {
        validationContainer.innerHTML = `
            <div class="alert alert-success alert-sm">
                <i class="fas fa-check-circle"></i>
                Compatible with ${selectedVariants.length} vehicle variant${selectedVariants.length !== 1 ? 's' : ''}.
            </div>
        `;
    }
}

// Utility function to clear all selections
function clearVehicleSelections() {
    $('.vehicle-variant-multiselect').val(null).trigger('change');
}

// Utility function to select vehicles by make
function selectVehiclesByMake(makeName) {
    const $select = $('.vehicle-variant-multiselect');
    const options = $select.find('option');
    const toSelect = [];
    
    options.each(function() {
        const text = $(this).text();
        if (text.toLowerCase().startsWith(makeName.toLowerCase())) {
            toSelect.push($(this).val());
        }
    });
    
    $select.val(toSelect).trigger('change');
}

// Export functions for external use
window.VehicleVariantWidget = {
    clear: clearVehicleSelections,
    selectByMake: selectVehiclesByMake,
    updateDisplay: updateCompatibilityDisplay
};