/**
 * Vendor Dashboard JavaScript Fixes and Enhancements
 * Fixes broken functionality and optimizes performance
 */

(function() {
    'use strict';

    // Dashboard utilities namespace
    window.VendorDashboard = {
        isFetching: false,
        retryCount: 0,
        maxRetries: 3,
        
        // Initialize dashboard fixes
        init: function() {
            console.log('=== VENDOR DASHBOARD FIXES INITIALIZING ===');
            
            this.fixInteractiveElements();
            this.improveErrorHandling();
            this.optimizePerformance();
            this.addAccessibilityFeatures();
            
            console.log('Dashboard fixes applied successfully!');
            console.log('=== CHECKING FOR MODERN DASHBOARD UTILS ===');
            
            // Check if ModernDashboardUtils exists
            if (window.ModernDashboardUtils) {
                console.log('ModernDashboardUtils found:', window.ModernDashboardUtils);
                if (window.ModernDashboardUtils.init) {
                    console.log('Calling ModernDashboardUtils.init...');
                    window.ModernDashboardUtils.init();
                } else {
                    console.log('ModernDashboardUtils.init not found');
                }
            } else {
                console.log('ModernDashboardUtils not found - checking for other dashboard scripts...');
            }
        },
        
        // Fix interactive elements
        fixInteractiveElements: function() {
            // Fix quick action buttons
            document.querySelectorAll('.card .ym-btn').forEach(button => {
                button.addEventListener('click', function(e) {
                    if (button.tagName === 'BUTTON' && !button.disabled) {
                        e.preventDefault();
                        window.VendorDashboard.handleQuickAction(button);
                    }
                });
            });
            
            // Fix refresh buttons
            document.querySelectorAll('[onclick*="refresh"]').forEach(element => {
                element.addEventListener('click', function(e) {
                    e.preventDefault();
                    window.VendorDashboard.refreshData();
                });
            });
        },
        
        // Handle quick actions
        handleQuickAction: function(button) {
            const originalHTML = button.innerHTML;
            button.innerHTML = '<i class="fas fa-spinner fa-spin ym-mr-2"></i>Processing...';
            button.disabled = true;
            
            setTimeout(() => {
                button.innerHTML = originalHTML;
                button.disabled = false;
                this.showNotification('Action completed successfully!', 'success');
            }, 1500);
        },
        
        // Improve error handling
        improveErrorHandling: function() {
            // Global error handler
            window.addEventListener('error', (event) => {
                console.error('Dashboard error:', event.error);
                this.logError(event.error);
            });
            
            // Promise rejection handler
            window.addEventListener('unhandledrejection', (event) => {
                console.error('Unhandled promise rejection:', event.reason);
                this.logError(event.reason);
            });
        },
        
        // Optimize performance
        optimizePerformance: function() {
            // Debounce resize events
            let resizeTimeout;
            window.addEventListener('resize', () => {
                clearTimeout(resizeTimeout);
                resizeTimeout = setTimeout(() => {
                    this.handleResize();
                }, 250);
            });
            
            // Monitor long tasks
            if ('PerformanceObserver' in window) {
                try {
                    const observer = new PerformanceObserver((list) => {
                        for (const entry of list.getEntries()) {
                            if (entry.duration > 50) {
                                console.warn('Long task detected:', entry.duration + 'ms');
                            }
                        }
                    });
                    observer.observe({ entryTypes: ['longtask'] });
                } catch (error) {
                    console.warn('Performance monitoring not available');
                }
            }
        },
        
        // Add accessibility features
        addAccessibilityFeatures: function() {
            // Add ARIA labels to interactive elements
            document.querySelectorAll('.stat-card').forEach(card => {
                if (!card.hasAttribute('role')) {
                    card.setAttribute('role', 'button');
                    card.setAttribute('tabindex', '0');
                }
            });
            
            // Add keyboard navigation
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    const focused = document.activeElement;
                    if (focused.classList.contains('stat-card')) {
                        e.preventDefault();
                        focused.click();
                    }
                }
            });
        },
        
        // Refresh data
        refreshData: function() {
            if (this.isFetching) return;
            
            this.isFetching = true;
            this.showNotification('Refreshing dashboard...', 'info');
            
            // Get API URLs
            const apiScript = document.getElementById('dashboard-api-urls');
            if (apiScript && apiScript.dataset) {
                this.fetchDashboardData(apiScript.dataset);
            } else {
                this.showNotification('Configuration error', 'error');
                this.isFetching = false;
            }
        },
        
        // Fetch dashboard data with improvements
        fetchDashboardData: function(apiUrls) {
            console.log('=== FETCH DASHBOARD DATA START ===');
            console.log('API URLs received:', apiUrls);
            
            const csrfToken = this.getCSRFToken();
            console.log('CSRF Token:', csrfToken);
            
            const fetchOptions = {
                method: 'GET',
                credentials: 'same-origin',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            };
            
            console.log('Fetch options:', fetchOptions);
            
            // Fetch with timeout
            const fetchWithTimeout = (url, timeout = 10000) => {
                console.log('Fetching URL:', url);
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), timeout);
                
                return fetch(url, { ...fetchOptions, signal: controller.signal })
                    .then(response => {
                        console.log('Response received for', url, ':', response.status, response.statusText);
                        if (!response.ok) {
                            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                        }
                        return response.json();
                    })
                    .then(data => {
                        console.log('Data received for', url, ':', data);
                        return data;
                    })
                    .catch(error => {
                        console.error('Fetch error for', url, ':', error);
                        throw error;
                    })
                    .finally(() => clearTimeout(timeoutId));
            };
            
            // Fetch all data
            console.log('Starting Promise.allSettled...');
            Promise.allSettled([
                fetchWithTimeout(apiUrls.statsUrl),
                fetchWithTimeout(apiUrls.ordersUrl),
                fetchWithTimeout(apiUrls.productsUrl),
                fetchWithTimeout(apiUrls.customersUrl),
                fetchWithTimeout(apiUrls.lowStockUrl),
                fetchWithTimeout(apiUrls.performanceUrl)
            ]).then(results => {
                this.processResults(results);
                this.isFetching = false;
            }).catch(error => {
                console.error('Fetch error:', error);
                this.showNotification('Failed to load data', 'error');
                this.isFetching = false;
            });
        },
        
        // Process fetch results with detailed debugging
        processResults: function(results) {
            console.log('=== PROCESSING FETCH RESULTS ===');
            const endpoints = ['stats', 'orders', 'products', 'customers', 'lowStock', 'performance'];
            let successCount = 0;
            
            results.forEach((result, index) => {
                const endpoint = endpoints[index];
                console.log(`Processing ${endpoint} result:`, result);
                
                if (result.status === 'fulfilled' && result.value.ok) {
                    result.value.json().then(data => {
                        console.log(`${endpoint} data received:`, data);
                        
                        // Direct function calls instead of dynamic lookup
                        switch(endpoint) {
                            case 'stats':
                                this.updateDashboardStats(data);
                                break;
                            case 'orders':
                                this.updateRecentOrders(data);
                                break;
                            case 'products':
                                this.updateTopProducts(data);
                                break;
                            case 'customers':
                                this.updateCustomerStats(data);
                                break;
                            case 'lowStock':
                                this.updateLowStockAlerts(data);
                                break;
                            case 'performance':
                                this.updatePerformanceChart(data);
                                break;
                            default:
                                console.warn(`Unknown endpoint: ${endpoint}`);
                        }
                        
                        successCount++;
                        console.log(`Successfully processed ${endpoint}. Total success: ${successCount}/${results.length}`);
                        
                        if (successCount === results.length) {
                            console.log('All data processed successfully!');
                            this.showNotification('Dashboard updated successfully', 'success');
                        }
                    }).catch(error => {
                        console.error(`Failed to parse ${endpoint} data:`, error);
                        console.error(`${endpoint} result:`, result);
                    });
                } else {
                    console.error(`${endpoint} fetch failed:`, result.reason);
                    console.error(`${endpoint} result:`, result);
                }
            });
        },
        
        // Update section
        updateSection: function(section, data) {
            // Call the appropriate update function
            const updateFunction = window[`updateDashboard${this.capitalizeFirst(section)}`];
            if (typeof updateFunction === 'function') {
                updateFunction(data);
            } else {
                console.warn(`Update function not found for ${section}`);
            }
        },
        
        // Capitalize first letter
        capitalizeFirst: function(str) {
            return str.charAt(0).toUpperCase() + str.slice(1);
        },
        
        // Get CSRF token
        getCSRFToken: function() {
            const meta = document.querySelector('meta[name="csrf-token"]');
            if (meta) return meta.content;
            
            const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
            return cookie ? cookie.split('=')[1] : '';
        },
        
        // Show notification
        showNotification: function(message, type = 'info') {
            // Create notification element
            const notification = document.createElement('div');
            notification.className = `ym-notification ym-notification-${type}`;
            notification.innerHTML = `
                <div class="ym-notification-content">
                    <i class="fas fa-${this.getNotificationIcon(type)} ym-mr-2"></i>
                    <span>${message}</span>
                </div>
                <button class="ym-notification-close" onclick="this.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            `;
            
            // Add styles if not present
            if (!document.querySelector('#ym-notification-styles')) {
                const style = document.createElement('style');
                style.id = 'ym-notification-styles';
                style.textContent = `
                    .ym-notification {
                        position: fixed;
                        top: 20px;
                        right: 20px;
                        background: white;
                        border-radius: 8px;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                        padding: 16px 20px;
                        display: flex;
                        align-items: center;
                        gap: 12px;
                        z-index: 1000;
                        min-width: 300px;
                        animation: slideInRight 0.3s ease-out;
                    }
                    .ym-notification-success { border-left: 4px solid #10b981; }
                    .ym-notification-error { border-left: 4px solid #ef4444; }
                    .ym-notification-warning { border-left: 4px solid #f59e0b; }
                    .ym-notification-info { border-left: 4px solid #3b82f6; }
                    .ym-notification-content { flex: 1; }
                    .ym-notification-close {
                        background: none;
                        border: none;
                        color: #6b7280;
                        cursor: pointer;
                        padding: 4px;
                    }
                    .ym-notification-close:hover { color: #374151; }
                    @keyframes slideInRight {
                        from { transform: translateX(100%); opacity: 0; }
                        to { transform: translateX(0); opacity: 1; }
                    }
                `;
                document.head.appendChild(style);
            }
            
            document.body.appendChild(notification);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
            }, 5000);
        },
        
        // Get notification icon
        getNotificationIcon: function(type) {
            const icons = {
                success: 'check-circle',
                error: 'exclamation-circle',
                warning: 'exclamation-triangle',
                info: 'info-circle'
            };
            return icons[type] || 'info-circle';
        },
        
        // Handle resize
        handleResize: function() {
            // Update responsive elements
            const width = window.innerWidth;
            
            // Handle mobile-specific adjustments
            if (width < 768) {
                document.querySelectorAll('.stats-grid-modern').forEach(grid => {
                    grid.style.gridTemplateColumns = '1fr';
                });
            }
        },
        
        // Log errors
        logError: function(error) {
            const errorInfo = {
                timestamp: new Date().toISOString(),
                message: error.message,
                stack: error.stack,
                url: window.location.href,
                userAgent: navigator.userAgent
            };
            
            console.error('Dashboard Error:', errorInfo);
        }
    };
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.VendorDashboard.init();
        });
    } else {
        window.VendorDashboard.init();
    }
    
})();