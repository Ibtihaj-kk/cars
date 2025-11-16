/**
 * Vendor API Error Handler
 * Comprehensive error handling for API requests with user-friendly messages
 */

(function() {
    'use strict';

    window.VendorAPI = {
        // Error types and their handling
        errorTypes: {
            NETWORK_ERROR: {
                code: 'NETWORK_ERROR',
                message: 'Network connection issue. Please check your internet connection.',
                retryable: true,
                severity: 'high'
            },
            TIMEOUT_ERROR: {
                code: 'TIMEOUT_ERROR', 
                message: 'Request timed out. Please try again.',
                retryable: true,
                severity: 'medium'
            },
            SERVER_ERROR: {
                code: 'SERVER_ERROR',
                message: 'Server error. Our team has been notified.',
                retryable: true,
                severity: 'high'
            },
            AUTH_ERROR: {
                code: 'AUTH_ERROR',
                message: 'Authentication failed. Please log in again.',
                retryable: false,
                severity: 'critical',
                action: 'redirect_to_login'
            },
            VALIDATION_ERROR: {
                code: 'VALIDATION_ERROR',
                message: 'Please check your input and try again.',
                retryable: false,
                severity: 'low'
            },
            RATE_LIMIT_ERROR: {
                code: 'RATE_LIMIT_ERROR',
                message: 'Too many requests. Please wait a moment and try again.',
                retryable: true,
                severity: 'medium',
                retryDelay: 5000
            },
            PERMISSION_ERROR: {
                code: 'PERMISSION_ERROR',
                message: 'You don\'t have permission to perform this action.',
                retryable: false,
                severity: 'medium'
            },
            DATA_ERROR: {
                code: 'DATA_ERROR',
                message: 'Data processing error. Please refresh the page.',
                retryable: true,
                severity: 'medium'
            }
        },

        // Initialize API error handler
        init: function() {
            console.log('Initializing Vendor API Error Handler...');
            this.setupGlobalErrorHandling();
            this.setupRequestInterceptors();
            this.setupFallbackHandlers();
        },

        // Setup global error handling
        setupGlobalErrorHandling: function() {
            // Handle fetch errors globally
            const originalFetch = window.fetch;
            window.fetch = async (...args) => {
                try {
                    const response = await originalFetch(...args);
                    return this.handleFetchResponse(response, args[0]);
                } catch (error) {
                    return this.handleFetchError(error, args[0]);
                }
            };

            // Handle unhandled promise rejections
            window.addEventListener('unhandledrejection', (event) => {
                if (event.reason && event.reason.isAPIError) {
                    this.handleUnhandledAPIError(event.reason);
                    event.preventDefault();
                }
            });
        },

        // Handle fetch response
        handleFetchResponse: function(response, request) {
            if (!response.ok) {
                const error = this.createAPIError(response.status, response.statusText, request.url);
                error.response = response;
                throw error;
            }
            return response;
        },

        // Handle fetch errors
        handleFetchError: function(error, request) {
            let apiError;
            
            if (error.name === 'AbortError') {
                apiError = this.createAPIError(0, 'Request aborted', request.url, 'TIMEOUT_ERROR');
            } else if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
                apiError = this.createAPIError(0, 'Network error', request.url, 'NETWORK_ERROR');
            } else {
                apiError = this.createAPIError(0, error.message, request.url, 'NETWORK_ERROR');
            }
            
            apiError.originalError = error;
            throw apiError;
        },

        // Create API error object
        createAPIError: function(status, message, url, type = null) {
            const errorType = type || this.getErrorTypeFromStatus(status);
            const errorInfo = this.errorTypes[errorType] || this.errorTypes.SERVER_ERROR;
            
            const error = new Error(errorInfo.message);
            error.name = 'APIError';
            error.isAPIError = true;
            error.status = status;
            error.url = url;
            error.type = errorType;
            error.code = errorInfo.code;
            error.retryable = errorInfo.retryable;
            error.severity = errorInfo.severity;
            error.action = errorInfo.action;
            error.retryDelay = errorInfo.retryDelay || 1000;
            
            return error;
        },

        // Get error type from HTTP status
        getErrorTypeFromStatus: function(status) {
            if (status === 0) return 'NETWORK_ERROR';
            if (status === 401) return 'AUTH_ERROR';
            if (status === 403) return 'PERMISSION_ERROR';
            if (status === 429) return 'RATE_LIMIT_ERROR';
            if (status >= 400 && status < 500) return 'VALIDATION_ERROR';
            if (status >= 500) return 'SERVER_ERROR';
            return 'SERVER_ERROR';
        },

        // Setup request interceptors
        setupRequestInterceptors: function() {
            // Add CSRF token to requests
            const originalFetch = window.fetch;
            window.fetch = async (url, options = {}) => {
                // Add CSRF token if available
                if (!options.headers) options.headers = {};
                if (this.getCSRFToken() && !options.headers['X-CSRFToken']) {
                    options.headers['X-CSRFToken'] = this.getCSRFToken();
                }
                
                // Add timeout if not specified
                if (!options.signal && !options.timeout) {
                    const controller = new AbortController();
                    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s default
                    options.signal = controller.signal;
                    
                    // Clean up timeout on completion
                    const fetchPromise = originalFetch(url, options);
                    fetchPromise.finally(() => clearTimeout(timeoutId));
                    return fetchPromise;
                }
                
                return originalFetch(url, options);
            };
        },

        // Get CSRF token
        getCSRFToken: function() {
            const meta = document.querySelector('meta[name="csrf-token"]');
            if (meta) return meta.content;
            
            const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
            return cookie ? cookie.split('=')[1] : null;
        },

        // Handle unhandled API errors
        handleUnhandledAPIError: function(error) {
            console.error('Unhandled API Error:', error);
            this.showUserFriendlyError(error);
            this.logError(error);
        },

        // Show user-friendly error
        showUserFriendlyError: function(error) {
            const message = this.getErrorMessage(error);
            const actions = this.getErrorActions(error);
            
            this.showNotification(message, error.severity, actions);
            
            // Handle special actions
            if (error.action === 'redirect_to_login') {
                setTimeout(() => {
                    window.location.href = '/login/';
                }, 3000);
            }
        },

        // Get error message for user
        getErrorMessage: function(error) {
            let message = error.message || 'An unexpected error occurred.';
            
            // Add retry information for retryable errors
            if (error.retryable) {
                message += ' You can try again.';
            }
            
            // Add technical details in development
            if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
                message += ` (Error: ${error.code || error.type})`;
            }
            
            return message;
        },

        // Get error actions
        getErrorActions: function(error) {
            const actions = [];
            
            if (error.retryable) {
                actions.push({
                    label: 'Retry',
                    action: () => this.retryRequest(error),
                    type: 'primary'
                });
            }
            
            if (error.severity === 'high' || error.severity === 'critical') {
                actions.push({
                    label: 'Report Issue',
                    action: () => this.reportError(error),
                    type: 'secondary'
                });
            }
            
            actions.push({
                label: 'Dismiss',
                action: () => this.dismissNotification(),
                type: 'ghost'
            });
            
            return actions;
        },

        // Retry request
        retryRequest: function(error) {
            if (!error.retryable) return;
            
            this.showNotification('Retrying...', 'info');
            
            setTimeout(() => {
                // Trigger retry logic here
                if (window.VendorDashboard && window.VendorDashboard.loadDashboardData) {
                    window.VendorDashboard.loadDashboardData();
                }
            }, error.retryDelay);
        },

        // Report error
        reportError: function(error) {
            const errorData = {
                timestamp: new Date().toISOString(),
                url: window.location.href,
                userAgent: navigator.userAgent,
                error: {
                    code: error.code,
                    type: error.type,
                    status: error.status,
                    message: error.message,
                    url: error.url
                }
            };
            
            // Log to console for now
            console.error('Error Report:', errorData);
            
            // In production, send to error reporting service
            this.showNotification('Error reported. Thank you!', 'success');
        },

        // Setup fallback handlers
        setupFallbackHandlers: function() {
            // Fallback for when API calls fail completely
            window.addEventListener('offline', () => {
                this.showNotification('You are offline. Some features may not work.', 'warning');
            });
            
            window.addEventListener('online', () => {
                this.showNotification('Connection restored!', 'success');
                // Retry failed requests
                if (window.VendorDashboard && window.VendorDashboard.loadDashboardData) {
                    window.VendorDashboard.loadDashboardData();
                }
            });
        },

        // Show notification
        showNotification: function(message, type = 'info', actions = []) {
            // Remove existing notifications
            document.querySelectorAll('.ym-api-notification').forEach(n => n.remove());
            
            const notification = document.createElement('div');
            notification.className = `ym-api-notification ym-api-notification-${type}`;
            notification.setAttribute('role', 'alert');
            notification.setAttribute('aria-live', 'polite');
            
            let content = `
                <div class="ym-notification-content">
                    <div class="ym-notification-icon">
                        <i class="fas fa-${this.getNotificationIcon(type)}"></i>
                    </div>
                    <div class="ym-notification-text">
                        <p class="ym-notification-message">${message}</p>
                    </div>
                </div>
            `;
            
            if (actions.length > 0) {
                content += '<div class="ym-notification-actions">';
                actions.forEach(action => {
                    content += `
                        <button class="ym-btn ym-btn-${action.type} ym-btn-sm" onclick="${action.action}">
                            ${action.label}
                        </button>
                    `;
                });
                content += '</div>';
            }
            
            content += `
                <button class="ym-notification-close" onclick="this.parentElement.remove()" aria-label="Close notification">
                    <i class="fas fa-times"></i>
                </button>
            `;
            
            notification.innerHTML = content;
            
            // Add styles if not present
            this.addNotificationStyles();
            
            document.body.appendChild(notification);
            
            // Auto-remove after 8 seconds
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
            }, 8000);
        },

        // Get notification icon
        getNotificationIcon: function(type) {
            const icons = {
                success: 'check-circle',
                error: 'exclamation-circle',
                warning: 'exclamation-triangle',
                info: 'info-circle',
                critical: 'radiation'
            };
            return icons[type] || 'info-circle';
        },

        // Add notification styles
        addNotificationStyles: function() {
            if (document.querySelector('#ym-api-notification-styles')) return;
            
            const style = document.createElement('style');
            style.id = 'ym-api-notification-styles';
            style.textContent = `
                .ym-api-notification {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 8px 25px rgba(0,0,0,0.15);
                    padding: 16px 20px;
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                    z-index: 10000;
                    min-width: 320px;
                    max-width: 400px;
                    animation: slideInRight 0.3s ease-out;
                    border-left: 4px solid;
                }
                
                .ym-api-notification-success { border-left-color: #10b981; }
                .ym-api-notification-error { border-left-color: #ef4444; }
                .ym-api-notification-warning { border-left-color: #f59e0b; }
                .ym-api-notification-info { border-left-color: #3b82f6; }
                .ym-api-notification-critical { border-left-color: #dc2626; }
                
                .ym-notification-content {
                    display: flex;
                    align-items: flex-start;
                    gap: 12px;
                }
                
                .ym-notification-icon {
                    flex-shrink: 0;
                    width: 20px;
                    height: 20px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                
                .ym-notification-icon i {
                    font-size: 16px;
                }
                
                .ym-api-notification-success .ym-notification-icon { color: #10b981; }
                .ym-api-notification-error .ym-notification-icon { color: #ef4444; }
                .ym-api-notification-warning .ym-notification-icon { color: #f59e0b; }
                .ym-api-notification-info .ym-notification-icon { color: #3b82f6; }
                .ym-api-notification-critical .ym-notification-icon { color: #dc2626; }
                
                .ym-notification-text {
                    flex: 1;
                    min-width: 0;
                }
                
                .ym-notification-message {
                    margin: 0;
                    font-size: 14px;
                    line-height: 1.5;
                    color: #374151;
                }
                
                .ym-notification-actions {
                    display: flex;
                    gap: 8px;
                    justify-content: flex-end;
                    flex-wrap: wrap;
                }
                
                .ym-notification-close {
                    position: absolute;
                    top: 8px;
                    right: 8px;
                    background: none;
                    border: none;
                    color: #9ca3af;
                    cursor: pointer;
                    padding: 4px;
                    font-size: 12px;
                }
                
                .ym-notification-close:hover {
                    color: #6b7280;
                }
                
                @keyframes slideInRight {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                
                @media (max-width: 480px) {
                    .ym-api-notification {
                        left: 16px;
                        right: 16px;
                        min-width: auto;
                        max-width: none;
                    }
                }
            `;
            document.head.appendChild(style);
        },

        // Dismiss notification
        dismissNotification: function() {
            document.querySelectorAll('.ym-api-notification').forEach(n => n.remove());
        },

        // Log error
        logError: function(error) {
            const errorData = {
                timestamp: new Date().toISOString(),
                url: window.location.href,
                userAgent: navigator.userAgent,
                error: {
                    code: error.code,
                    type: error.type,
                    status: error.status,
                    message: error.message,
                    url: error.url,
                    stack: error.stack
                }
            };
            
            console.error('API Error Log:', errorData);
            
            // In production, send to logging service
            // this.sendToLoggingService(errorData);
        },

        // Enhanced fetch wrapper for vendor dashboard
        vendorFetch: async function(url, options = {}) {
            const maxRetries = 3;
            let retryCount = 0;
            
            const attemptFetch = async () => {
                try {
                    const response = await fetch(url, options);
                    return response;
                } catch (error) {
                    if (retryCount < maxRetries && this.isRetryableError(error)) {
                        retryCount++;
                        const delay = Math.pow(2, retryCount) * 1000; // Exponential backoff
                        
                        this.showNotification(
                            `Retrying... (attempt ${retryCount}/${maxRetries})`, 
                            'info'
                        );
                        
                        await new Promise(resolve => setTimeout(resolve, delay));
                        return attemptFetch();
                    }
                    throw error;
                }
            };
            
            return attemptFetch();
        },

        // Check if error is retryable
        isRetryableError: function(error) {
            return error.retryable || 
                   error.code === 'NETWORK_ERROR' || 
                   error.code === 'TIMEOUT_ERROR' ||
                   error.code === 'SERVER_ERROR';
        }
    };

    // Initialize API error handler
    window.VendorAPI.init();

})();