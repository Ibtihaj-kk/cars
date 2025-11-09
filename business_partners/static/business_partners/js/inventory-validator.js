/**
 * Inventory Threshold Validator Widget
 * Provides real-time inventory validation and alerts
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeInventoryValidators();
});

function initializeInventoryValidators() {
    const inventoryFields = document.querySelectorAll('.inventory-threshold, [data-inventory-field]');
    
    inventoryFields.forEach(function(field) {
        setupInventoryValidator(field);
    });
    
    // Create inventory alerts container if it doesn't exist
    createInventoryAlertsContainer();
}

function setupInventoryValidator(field) {
    field.addEventListener('input', function() {
        validateInventoryLevels();
    });
    
    field.addEventListener('blur', function() {
        validateInventoryLevels();
    });
    
    // Initial validation
    setTimeout(() => validateInventoryLevels(), 100);
}

function validateInventoryLevels() {
    const quantity = parseFloat(document.getElementById('id_quantity')?.value) || 0;
    const safetyStock = parseFloat(document.getElementById('id_safety_stock')?.value) || 0;
    const minimumSafetyStock = parseFloat(document.getElementById('id_minimum_safety_stock')?.value) || 0;
    const reorderPoint = parseFloat(document.getElementById('id_reorder_point')?.value) || 0;
    const inventoryThreshold = parseFloat(document.getElementById('id_inventory_threshold')?.value) || 0;
    
    const alertsContainer = document.getElementById('inventory-alerts');
    if (!alertsContainer) return;
    
    const alerts = [];
    
    // Check stock levels
    if (quantity <= 0) {
        alerts.push({
            type: 'danger',
            icon: 'fa-exclamation-triangle',
            title: 'Out of Stock',
            message: 'Current quantity is zero or negative. This part is out of stock.'
        });
    } else if (inventoryThreshold > 0 && quantity <= inventoryThreshold) {
        alerts.push({
            type: 'warning',
            icon: 'fa-exclamation-circle',
            title: 'Low Stock Alert',
            message: `Current stock (${quantity}) is at or below the threshold (${inventoryThreshold}). Consider reordering.`
        });
    } else if (reorderPoint > 0 && quantity <= reorderPoint) {
        alerts.push({
            type: 'info',
            icon: 'fa-info-circle',
            title: 'Reorder Point Reached',
            message: `Current stock (${quantity}) has reached the reorder point (${reorderPoint}).`
        });
    }
    
    // Check safety stock levels
    if (safetyStock > 0 && quantity <= safetyStock) {
        alerts.push({
            type: 'warning',
            icon: 'fa-shield-alt',
            title: 'Safety Stock Level',
            message: `Current stock (${quantity}) is at or below safety stock level (${safetyStock}).`
        });
    }
    
    // Validate relationships between stock levels
    if (safetyStock > 0 && minimumSafetyStock > 0 && safetyStock < minimumSafetyStock) {
        alerts.push({
            type: 'danger',
            icon: 'fa-exclamation-triangle',
            title: 'Invalid Safety Stock',
            message: `Safety stock (${safetyStock}) cannot be less than minimum safety stock (${minimumSafetyStock}).`
        });
    }
    
    if (reorderPoint > 0 && safetyStock > 0 && reorderPoint <= safetyStock) {
        alerts.push({
            type: 'info',
            icon: 'fa-info-circle',
            title: 'Reorder Point Notice',
            message: `Reorder point (${reorderPoint}) should typically be higher than safety stock (${safetyStock}).`
        });
    }
    
    // Display alerts or success message
    if (alerts.length === 0) {
        alertsContainer.innerHTML = `
            <div class="alert alert-success alert-sm">
                <i class="fas fa-check-circle"></i>
                <strong>Inventory Levels Look Good</strong>
                <div class="inventory-summary">
                    <small class="text-muted">
                        Current: ${quantity} | Safety: ${safetyStock} | Reorder: ${reorderPoint}
                    </small>
                </div>
            </div>
        `;
    } else {
        const alertsHTML = alerts.map(alert => `
            <div class="alert alert-${alert.type} alert-sm">
                <i class="fas ${alert.icon}"></i>
                <strong>${alert.title}</strong>
                <div>${alert.message}</div>
            </div>
        `).join('');
        
        alertsContainer.innerHTML = alertsHTML;
    }
    
    // Update field validation states
    updateFieldValidationStates(quantity, safetyStock, reorderPoint, inventoryThreshold);
    
    // Calculate and display inventory metrics
    displayInventoryMetrics(quantity, safetyStock, reorderPoint, inventoryThreshold);
}

function updateFieldValidationStates(quantity, safetyStock, reorderPoint, inventoryThreshold) {
    const quantityField = document.getElementById('id_quantity');
    const safetyStockField = document.getElementById('id_safety_stock');
    const reorderPointField = document.getElementById('id_reorder_point');
    const thresholdField = document.getElementById('id_inventory_threshold');
    
    // Clear existing validation classes
    [quantityField, safetyStockField, reorderPointField, thresholdField].forEach(field => {
        if (field) {
            field.classList.remove('is-valid', 'is-invalid');
        }
    });
    
    // Quantity validation
    if (quantityField) {
        if (quantity <= 0) {
            quantityField.classList.add('is-invalid');
        } else if (inventoryThreshold > 0 && quantity > inventoryThreshold * 2) {
            quantityField.classList.add('is-valid');
        }
    }
    
    // Safety stock validation
    if (safetyStockField && safetyStock >= 0) {
        safetyStockField.classList.add('is-valid');
    }
    
    // Reorder point validation
    if (reorderPointField && reorderPoint > safetyStock) {
        reorderPointField.classList.add('is-valid');
    }
    
    // Threshold validation
    if (thresholdField && inventoryThreshold > 0) {
        thresholdField.classList.add('is-valid');
    }
}

function displayInventoryMetrics(quantity, safetyStock, reorderPoint, inventoryThreshold) {
    const metricsContainer = document.getElementById('inventory-metrics');
    if (!metricsContainer) return;
    
    const stockStatus = getStockStatus(quantity, safetyStock, reorderPoint, inventoryThreshold);
    const daysOfStock = calculateDaysOfStock(quantity, safetyStock);
    
    metricsContainer.innerHTML = `
        <div class="inventory-metrics-card">
            <div class="metrics-header">
                <h6 class="metrics-title">
                    <i class="fas fa-chart-line"></i>
                    Inventory Metrics
                </h6>
                <span class="badge badge-${stockStatus.class}">${stockStatus.text}</span>
            </div>
            <div class="metrics-grid">
                <div class="metric-item">
                    <span class="metric-label">Current Stock</span>
                    <span class="metric-value">${quantity}</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">Days of Stock</span>
                    <span class="metric-value">${daysOfStock}</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">Stock Turn Rate</span>
                    <span class="metric-value">${calculateStockTurnRate(quantity, safetyStock)}</span>
                </div>
            </div>
        </div>
    `;
}

function getStockStatus(quantity, safetyStock, reorderPoint, inventoryThreshold) {
    if (quantity <= 0) {
        return { class: 'danger', text: 'Out of Stock' };
    } else if (inventoryThreshold > 0 && quantity <= inventoryThreshold) {
        return { class: 'warning', text: 'Low Stock' };
    } else if (reorderPoint > 0 && quantity <= reorderPoint) {
        return { class: 'info', text: 'Reorder Soon' };
    } else if (safetyStock > 0 && quantity > safetyStock * 3) {
        return { class: 'success', text: 'Well Stocked' };
    } else {
        return { class: 'success', text: 'In Stock' };
    }
}

function calculateDaysOfStock(quantity, safetyStock) {
    // Simple estimation based on safety stock
    if (safetyStock <= 0) return 'N/A';
    
    const estimatedDailyUsage = safetyStock / 30; // Assume safety stock covers 30 days
    const daysOfStock = Math.floor(quantity / estimatedDailyUsage);
    
    return daysOfStock > 365 ? '365+' : daysOfStock.toString();
}

function calculateStockTurnRate(quantity, safetyStock) {
    if (safetyStock <= 0 || quantity <= 0) return 'N/A';
    
    const turnRate = (quantity / safetyStock).toFixed(1);
    return `${turnRate}x`;
}

function createInventoryAlertsContainer() {
    // Check if container already exists
    if (document.getElementById('inventory-alerts')) {
        return;
    }
    
    // Find the inventory section
    const inventorySection = document.querySelector('[data-section="inventory"]') || 
                           document.getElementById('id_quantity')?.closest('.form-group');
    
    if (!inventorySection) return;
    
    // Create alerts container
    const alertsContainer = document.createElement('div');
    alertsContainer.id = 'inventory-alerts';
    alertsContainer.className = 'inventory-alerts mt-3';
    
    // Create metrics container
    const metricsContainer = document.createElement('div');
    metricsContainer.id = 'inventory-metrics';
    metricsContainer.className = 'inventory-metrics mt-2';
    
    // Insert after the inventory section
    const parentContainer = inventorySection.closest('.row') || inventorySection.parentElement;
    if (parentContainer) {
        parentContainer.appendChild(alertsContainer);
        parentContainer.appendChild(metricsContainer);
    }
}

// Utility functions for external use
window.InventoryValidator = {
    validate: validateInventoryLevels,
    refresh: initializeInventoryValidators
};