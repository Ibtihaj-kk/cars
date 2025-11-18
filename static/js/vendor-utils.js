/**
 * Vendor Portal Utilities
 * Common utility functions for the Cars Portal Vendor Portal
 */

(function() {
    'use strict';

    // Utility object
    window.VendorUtils = {
        
        // Debounce function
        debounce: function(func, wait, immediate) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    timeout = null;
                    if (!immediate) func(...args);
                };
                const callNow = immediate && !timeout;
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
                if (callNow) func(...args);
            };
        },

        // Throttle function
        throttle: function(func, limit) {
            let inThrottle;
            return function(...args) {
                if (!inThrottle) {
                    func.apply(this, args);
                    inThrottle = true;
                    setTimeout(() => inThrottle = false, limit);
                }
            };
        },

        // Check if element is in viewport
        isInViewport: function(element, offset = 0) {
            if (!element) return false;
            const rect = element.getBoundingClientRect();
            return (
                rect.top >= -offset &&
                rect.left >= -offset &&
                rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) + offset &&
                rect.right <= (window.innerWidth || document.documentElement.clientWidth) + offset
            );
        },

        // Smooth scroll to element
        smoothScrollTo: function(target, duration = 1000, offset = 0) {
            if (!target) return;
            
            const targetPosition = typeof target === 'string' ? 
                document.querySelector(target).offsetTop - offset : 
                target.offsetTop - offset;
            
            const startPosition = window.pageYOffset;
            const distance = targetPosition - startPosition;
            let startTime = null;

            function animation(currentTime) {
                if (startTime === null) startTime = currentTime;
                const timeElapsed = currentTime - startTime;
                const run = ease(timeElapsed, startPosition, distance, duration);
                window.scrollTo(0, run);
                if (timeElapsed < duration) requestAnimationFrame(animation);
            }

            function ease(t, b, c, d) {
                t /= d / 2;
                if (t < 1) return c / 2 * t * t + b;
                t--;
                return -c / 2 * (t * (t - 2) - 1) + b;
            }

            requestAnimationFrame(animation);
        },

        // Get CSRF token from cookie
        getCsrfToken: function() {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, 'csrftoken'.length + 1) === ('csrftoken' + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring('csrftoken'.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        },

        // Create AJAX request
        ajax: function(options) {
            const xhr = new XMLHttpRequest();
            const defaults = {
                method: 'GET',
                headers: {},
                data: null,
                success: function() {},
                error: function() {}
            };

            const settings = Object.assign({}, defaults, options);
            
            // Add CSRF token for POST/PUT/DELETE requests
            if (['POST', 'PUT', 'DELETE'].includes(settings.method.toUpperCase())) {
                const csrfToken = this.getCsrfToken();
                if (csrfToken) {
                    settings.headers['X-CSRFToken'] = csrfToken;
                }
            }

            xhr.open(settings.method, settings.url);
            
            // Set headers
            Object.keys(settings.headers).forEach(key => {
                xhr.setRequestHeader(key, settings.headers[key]);
            });

            xhr.onload = function() {
                if (xhr.status >= 200 && xhr.status < 300) {
                    settings.success(xhr.responseText, xhr);
                } else {
                    settings.error(xhr.responseText, xhr);
                }
            };

            xhr.onerror = function() {
                settings.error(xhr.responseText, xhr);
            };

            xhr.send(settings.data);
        },

        // Show notification
        showNotification: function(message, type = 'info', duration = 5000) {
            const notification = document.createElement('div');
            notification.className = `vendor-notification vendor-notification-${type}`;
            notification.innerHTML = `
                <div class="vendor-notification-content">
                    <span class="vendor-notification-message">${message}</span>
                    <button class="vendor-notification-close" aria-label="Close notification">&times;</button>
                </div>
            `;

            document.body.appendChild(notification);

            // Auto remove after duration
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, duration);

            // Manual close button
            const closeBtn = notification.querySelector('.vendor-notification-close');
            closeBtn.addEventListener('click', () => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            });

            // Animate in
            requestAnimationFrame(() => {
                notification.classList.add('vendor-notification-show');
            });
        },

        // Format currency
        formatCurrency: function(amount, currency = 'AED') {
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: currency,
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(amount);
        },

        // Format number with commas
        formatNumber: function(number) {
            return new Intl.NumberFormat('en-US').format(number);
        },

        // Sanitize HTML
        sanitizeHtml: function(html) {
            const div = document.createElement('div');
            div.textContent = html;
            return div.innerHTML;
        },

        // Deep merge objects
        deepMerge: function(target, source) {
            const result = Object.assign({}, target);
            for (const key in source) {
                if (source.hasOwnProperty(key)) {
                    if (typeof source[key] === 'object' && source[key] !== null && !Array.isArray(source[key])) {
                        result[key] = this.deepMerge(result[key] || {}, source[key]);
                    } else {
                        result[key] = source[key];
                    }
                }
            }
            return result;
        },

        // Generate unique ID
        generateId: function(prefix = 'vendor') {
            return `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        },

        // Local storage with error handling
        localStorage: {
            set: function(key, value) {
                try {
                    localStorage.setItem(key, JSON.stringify(value));
                    return true;
                } catch (e) {
                    console.warn('LocalStorage set error:', e);
                    return false;
                }
            },
            get: function(key) {
                try {
                    const item = localStorage.getItem(key);
                    return item ? JSON.parse(item) : null;
                } catch (e) {
                    console.warn('LocalStorage get error:', e);
                    return null;
                }
            },
            remove: function(key) {
                try {
                    localStorage.removeItem(key);
                    return true;
                } catch (e) {
                    console.warn('LocalStorage remove error:', e);
                    return false;
                }
            }
        }
    };

    // Add CSS for notifications if not already present
    if (!document.querySelector('#vendor-utils-styles')) {
        const styles = document.createElement('style');
        styles.id = 'vendor-utils-styles';
        styles.textContent = `
            .vendor-notification {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                padding: 16px 20px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                transform: translateX(400px);
                transition: transform 0.3s ease;
                max-width: 400px;
                background: white;
            }
            
            .vendor-notification-show {
                transform: translateX(0);
            }
            
            .vendor-notification-success {
                border-left: 4px solid #10b981;
                background: #f0fdf4;
            }
            
            .vendor-notification-error {
                border-left: 4px solid #ef4444;
                background: #fef2f2;
            }
            
            .vendor-notification-warning {
                border-left: 4px solid #f59e0b;
                background: #fffbeb;
            }
            
            .vendor-notification-info {
                border-left: 4px solid #3b82f6;
                background: #eff6ff;
            }
            
            .vendor-notification-content {
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            
            .vendor-notification-message {
                flex: 1;
                margin-right: 12px;
                font-size: 14px;
                line-height: 1.4;
            }
            
            .vendor-notification-close {
                background: none;
                border: none;
                font-size: 20px;
                cursor: pointer;
                color: #6b7280;
                padding: 0;
                width: 24px;
                height: 24px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 4px;
                transition: all 0.2s ease;
            }
            
            .vendor-notification-close:hover {
                background: rgba(0, 0, 0, 0.1);
                color: #374151;
            }
        `;
        document.head.appendChild(styles);
    }

    console.log('Vendor Utils loaded successfully');

})();