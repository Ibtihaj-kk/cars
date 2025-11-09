/**
 * Profit Margin Calculator Widget
 * Provides real-time profit margin calculation for pricing fields
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeProfitCalculators();
});

function initializeProfitCalculators() {
    const profitCalculators = document.querySelectorAll('.profit-calculator');
    
    profitCalculators.forEach(function(calculator) {
        setupProfitCalculator(calculator);
    });
    
    // Create profit margin display if it doesn't exist
    createProfitMarginDisplay();
}

function setupProfitCalculator(priceInput) {
    const costFieldId = priceInput.getAttribute('data-cost-field') || 'cost-price';
    const costInput = document.getElementById(costFieldId);
    
    if (!costInput) {
        console.warn('Cost price input not found for profit calculator');
        return;
    }
    
    // Add event listeners for real-time calculation
    priceInput.addEventListener('input', function() {
        calculateProfitMargin(priceInput, costInput);
    });
    
    costInput.addEventListener('input', function() {
        calculateProfitMargin(priceInput, costInput);
    });
    
    // Initial calculation
    calculateProfitMargin(priceInput, costInput);
}

function calculateProfitMargin(priceInput, costInput) {
    const sellingPrice = parseFloat(priceInput.value) || 0;
    const costPrice = parseFloat(costInput.value) || 0;
    
    const displayContainer = document.getElementById('profit-margin-display');
    if (!displayContainer) return;
    
    if (sellingPrice <= 0 || costPrice <= 0) {
        displayContainer.innerHTML = `
            <div class="profit-margin-info">
                <span class="text-muted">Enter both cost and selling price to calculate margin</span>
            </div>
        `;
        return;
    }
    
    const profitAmount = sellingPrice - costPrice;
    const profitMargin = ((profitAmount / sellingPrice) * 100);
    const markup = ((profitAmount / costPrice) * 100);
    
    // Determine status and styling
    let statusClass = 'success';
    let statusIcon = 'fa-check-circle';
    let statusText = 'Good margin';
    
    if (profitMargin < 10) {
        statusClass = 'danger';
        statusIcon = 'fa-exclamation-triangle';
        statusText = 'Low margin';
    } else if (profitMargin < 20) {
        statusClass = 'warning';
        statusIcon = 'fa-exclamation-circle';
        statusText = 'Fair margin';
    } else if (profitMargin > 50) {
        statusClass = 'info';
        statusIcon = 'fa-info-circle';
        statusText = 'High margin';
    }
    
    displayContainer.innerHTML = `
        <div class="profit-margin-card">
            <div class="profit-margin-header">
                <h6 class="margin-title">
                    <i class="fas ${statusIcon} text-${statusClass}"></i>
                    Profit Analysis
                </h6>
                <span class="badge badge-${statusClass}">${statusText}</span>
            </div>
            <div class="profit-margin-details">
                <div class="margin-row">
                    <span class="margin-label">Profit Amount:</span>
                    <span class="margin-value ${profitAmount >= 0 ? 'text-success' : 'text-danger'}">
                        ${profitAmount >= 0 ? '+' : ''}${profitAmount.toFixed(2)} SAR
                    </span>
                </div>
                <div class="margin-row">
                    <span class="margin-label">Profit Margin:</span>
                    <span class="margin-value text-${statusClass}">
                        ${profitMargin.toFixed(1)}%
                    </span>
                </div>
                <div class="margin-row">
                    <span class="margin-label">Markup:</span>
                    <span class="margin-value text-info">
                        ${markup.toFixed(1)}%
                    </span>
                </div>
            </div>
            ${getProfitMarginRecommendations(profitMargin, markup)}
        </div>
    `;
    
    // Update form validation
    updateProfitValidation(priceInput, profitMargin);
}

function getProfitMarginRecommendations(profitMargin, markup) {
    let recommendations = [];
    
    if (profitMargin < 10) {
        recommendations.push('Consider increasing the selling price for better profitability');
    } else if (profitMargin > 50) {
        recommendations.push('High margin - ensure price remains competitive');
    }
    
    if (markup < 25) {
        recommendations.push('Low markup - review cost structure');
    }
    
    if (recommendations.length === 0) {
        recommendations.push('Profit margin looks healthy');
    }
    
    return `
        <div class="margin-recommendations">
            <small class="text-muted">
                <i class="fas fa-lightbulb"></i>
                ${recommendations.join('. ')}
            </small>
        </div>
    `;
}

function updateProfitValidation(priceInput, profitMargin) {
    // Remove existing validation classes
    priceInput.classList.remove('is-valid', 'is-invalid');
    
    // Add appropriate validation class
    if (profitMargin >= 10) {
        priceInput.classList.add('is-valid');
    } else if (profitMargin < 5) {
        priceInput.classList.add('is-invalid');
    }
}

function createProfitMarginDisplay() {
    // Check if display already exists
    if (document.getElementById('profit-margin-display')) {
        return;
    }
    
    // Find the pricing section or price input
    const priceInput = document.getElementById('selling-price') || document.querySelector('.profit-calculator');
    if (!priceInput) return;
    
    // Create display container
    const displayContainer = document.createElement('div');
    displayContainer.id = 'profit-margin-display';
    displayContainer.className = 'profit-margin-display mt-3';
    
    // Insert after the price input's parent container
    const priceContainer = priceInput.closest('.form-group') || priceInput.closest('.col') || priceInput.parentElement;
    if (priceContainer && priceContainer.parentElement) {
        priceContainer.parentElement.insertBefore(displayContainer, priceContainer.nextSibling);
    }
}

// Utility functions for external use
window.ProfitCalculator = {
    calculate: calculateProfitMargin,
    refresh: initializeProfitCalculators
};