/**
 * Vendor Stock Monitoring Dashboard Widget
 * Handles real-time stock monitoring and alerts
 */

class VendorStockMonitor {
    constructor() {
        this.refreshInterval = 30000; // 30 seconds
        this.autoRefresh = true;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadStockSummary();
        this.loadRecentAlerts();
        
        if (this.autoRefresh) {
            this.startAutoRefresh();
        }
    }

    setupEventListeners() {
        // Manual refresh buttons
        document.addEventListener('click', (e) => {
            if (e.target.matches('.refresh-stock-summary')) {
                e.preventDefault();
                this.loadStockSummary();
            }
            if (e.target.matches('.refresh-recent-alerts')) {
                e.preventDefault();
                this.loadRecentAlerts();
            }
            if (e.target.matches('.acknowledge-alert-btn')) {
                e.preventDefault();
                const notificationId = e.target.dataset.notificationId;
                this.acknowledgeAlert(notificationId);
            }
            if (e.target.matches('.mark-ordered-btn')) {
                e.preventDefault();
                const notificationId = e.target.dataset.notificationId;
                this.markOrdered(notificationId);
            }
        });

        // Auto-refresh toggle
        const autoRefreshToggle = document.getElementById('auto-refresh-toggle');
        if (autoRefreshToggle) {
            autoRefreshToggle.addEventListener('change', (e) => {
                this.autoRefresh = e.target.checked;
                if (this.autoRefresh) {
                    this.startAutoRefresh();
                } else {
                    this.stopAutoRefresh();
                }
            });
        }
    }

    startAutoRefresh() {
        this.refreshTimer = setInterval(() => {
            this.loadStockSummary();
            this.loadRecentAlerts();
        }, this.refreshInterval);
    }

    stopAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }

    async loadStockSummary() {
        try {
            const response = await fetch('/business-partners/api/vendor/stock-monitoring/summary/');
            const data = await response.json();
            
            if (data.success) {
                this.updateStockSummaryUI(data.data);
            } else {
                console.error('Failed to load stock summary:', data.error);
            }
        } catch (error) {
            console.error('Error loading stock summary:', error);
        }
    }

    async loadRecentAlerts() {
        try {
            const response = await fetch('/business-partners/api/vendor/stock-monitoring/notifications/?limit=10');
            const data = await response.json();
            
            if (data.success) {
                this.updateRecentAlertsUI(data.data);
            } else {
                console.error('Failed to load recent alerts:', data.error);
            }
        } catch (error) {
            console.error('Error loading recent alerts:', error);
        }
    }

    updateStockSummaryUI(summary) {
        // Update critical alerts card
        const criticalCard = document.querySelector('.critical-alerts-card');
        if (criticalCard) {
            const criticalCount = criticalCard.querySelector('.alert-count');
            if (criticalCount) {
                criticalCount.textContent = summary.critical_notifications;
            }
            
            // Update card styling based on critical count
            if (summary.critical_notifications > 0) {
                criticalCard.classList.add('danger-card');
                criticalCard.classList.remove('info-card');
            } else {
                criticalCard.classList.remove('danger-card');
                criticalCard.classList.add('info-card');
            }
        }

        // Update inventory health
        const healthCard = document.querySelector('.inventory-health-card');
        if (healthCard) {
            const healthPercentage = healthCard.querySelector('.health-percentage');
            const healthStatus = healthCard.querySelector('.health-status');
            
            if (healthPercentage) {
                healthPercentage.textContent = summary.inventory_health_percentage + '%';
            }
            if (healthStatus) {
                healthStatus.textContent = summary.health_status;
            }
            
            // Update card styling based on health
            healthCard.className = 'card inventory-health-card';
            if (summary.inventory_health_percentage >= 90) {
                healthCard.classList.add('success-card');
            } else if (summary.inventory_health_percentage >= 70) {
                healthCard.classList.add('warning-card');
            } else {
                healthCard.classList.add('danger-card');
            }
        }

        // Update stock status counts
        const totalParts = document.querySelector('.total-parts-count');
        const outOfStock = document.querySelector('.out-of-stock-count');
        const lowStock = document.querySelector('.low-stock-count');
        const belowSafety = document.querySelector('.below-safety-count');
        
        if (totalParts) totalParts.textContent = summary.total_parts;
        if (outOfStock) outOfStock.textContent = summary.out_of_stock;
        if (lowStock) lowStock.textContent = summary.low_stock;
        if (belowSafety) belowSafety.textContent = summary.below_safety_stock;

        // Update pending notifications count
        const pendingNotifications = document.querySelector('.pending-notifications-count');
        if (pendingNotifications) {
            pendingNotifications.textContent = summary.pending_notifications;
        }
    }

    updateRecentAlertsUI(alertsData) {
        const alertsContainer = document.querySelector('.recent-alerts-container');
        if (!alertsContainer) return;

        if (alertsData.notifications.length === 0) {
            alertsContainer.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-check-circle"></i>
                    No recent alerts. Your inventory is healthy!
                </div>
            `;
            return;
        }

        let alertsHTML = '';
        alertsData.notifications.forEach(alert => {
            const priorityClass = `priority-${alert.priority}`;
            const timeAgo = this.getTimeAgo(alert.created_at);
            
            alertsHTML += `
                <div class="alert-item ${priorityClass}">
                    <div class="alert-header">
                        <strong>${alert.part_name}</strong>
                        <span class="badge badge-${alert.priority}">${alert.priority.toUpperCase()}</span>
                    </div>
                    <div class="alert-details">
                        <small>Stock: ${alert.current_stock} | Suggested: ${alert.suggested_quantity}</small>
                        <small class="text-muted">${timeAgo}</small>
                    </div>
                    <div class="alert-actions">
                        <button class="btn btn-sm btn-primary acknowledge-alert-btn" 
                                data-notification-id="${alert.id}">
                            <i class="fas fa-check"></i> Acknowledge
                        </button>
                        <a href="/business_partners/vendor/reorder-notifications/${alert.id}/" 
                           class="btn btn-sm btn-outline-secondary">
                            View
                        </a>
                    </div>
                </div>
            `;
        });

        alertsContainer.innerHTML = alertsHTML;
    }

    async acknowledgeAlert(notificationId) {
        try {
            const response = await fetch('/business-partners/api/vendor/stock-monitoring/acknowledge-alert/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ notification_id: notificationId })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Alert acknowledged successfully', 'success');
                // Remove the acknowledged alert from UI
                const alertItem = document.querySelector(`[data-notification-id="${notificationId}"]`).closest('.alert-item');
                if (alertItem) {
                    alertItem.remove();
                }
                // Refresh summary
                this.loadStockSummary();
            } else {
                this.showNotification('Failed to acknowledge alert: ' + data.error, 'error');
            }
        } catch (error) {
            console.error('Error acknowledging alert:', error);
            this.showNotification('Error acknowledging alert', 'error');
        }
    }

    async markOrdered(notificationId) {
        try {
            const response = await fetch('/business-partners/api/vendor/stock-monitoring/mark-ordered/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ 
                    notification_id: notificationId,
                    order_reference: prompt('Enter order reference (optional):') || '',
                    expected_delivery: prompt('Enter expected delivery date (YYYY-MM-DD, optional):') || ''
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Item marked as ordered', 'success');
                // Refresh alerts and summary
                this.loadRecentAlerts();
                this.loadStockSummary();
            } else {
                this.showNotification('Failed to mark as ordered: ' + data.error, 'error');
            }
        } catch (error) {
            console.error('Error marking as ordered:', error);
            this.showNotification('Error marking as ordered', 'error');
        }
    }

    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
        notification.style.position = 'fixed';
        notification.style.top = '20px';
        notification.style.right = '20px';
        notification.style.zIndex = '9999';
        notification.style.minWidth = '300px';
        
        notification.innerHTML = `
            ${message}
            <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                <span aria-hidden="true">&times;</span>
            </button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }

    getTimeAgo(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const seconds = Math.floor((now - date) / 1000);
        
        if (seconds < 60) return 'just now';
        if (seconds < 3600) return Math.floor(seconds / 60) + ' minutes ago';
        if (seconds < 86400) return Math.floor(seconds / 3600) + ' hours ago';
        return Math.floor(seconds / 86400) + ' days ago';
    }
}

// Initialize stock monitoring when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if we're on a vendor dashboard or stock monitoring page
    if (document.querySelector('.vendor-dashboard') || document.querySelector('.stock-monitoring-widget')) {
        window.vendorStockMonitor = new VendorStockMonitor();
    }
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VendorStockMonitor;
}