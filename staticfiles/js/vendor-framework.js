/**
 * Vendor Management Framework JavaScript
 * Modern, responsive interactions and utilities
 */

class VendorFramework {
    constructor() {
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupAnimations();
        this.setupTooltips();
        this.setupDarkMode();
        this.setupFormValidation();
        this.setupNotifications();
    }

    setupEventListeners() {
        // Mobile navigation toggle
        const mobileToggle = document.querySelector('.mobile-nav-toggle');
        if (mobileToggle) {
            mobileToggle.addEventListener('click', () => {
                document.body.classList.toggle('mobile-nav-open');
            });
        }

        // Auto-dismiss alerts
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(alert => {
            setTimeout(() => {
                this.fadeOut(alert);
            }, 5000);
        });

        // Smooth scrolling for anchor links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', (e) => {
                e.preventDefault();
                const target = document.querySelector(anchor.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });

        // Form validation on blur
        document.querySelectorAll('.form-control').forEach(input => {
            input.addEventListener('blur', () => {
                this.validateField(input);
            });
        });

        // File upload drag and drop
        document.querySelectorAll('.file-upload-area').forEach(area => {
            this.setupFileUpload(area);
        });

        // Auto-refresh toggles
        document.querySelectorAll('.auto-refresh-toggle input').forEach(toggle => {
            toggle.addEventListener('change', (e) => {
                this.handleAutoRefresh(e.target);
            });
        });
    }

    setupAnimations() {
        // Intersection Observer for scroll animations
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                }
            });
        }, observerOptions);

        // Observe elements for animation
        document.querySelectorAll('.dashboard-card, .stat-card, .alert-item').forEach(el => {
            observer.observe(el);
        });

        // Add initial animation classes
        document.querySelectorAll('.dashboard-card').forEach((card, index) => {
            card.style.animationDelay = `${index * 0.1}s`;
        });
    }

    setupTooltips() {
        // Initialize Bootstrap tooltips if available
        if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        }

        // Custom tooltips for elements without Bootstrap
        document.querySelectorAll('[data-tooltip]').forEach(element => {
            element.addEventListener('mouseenter', (e) => {
                this.showTooltip(e.target, e.target.dataset.tooltip);
            });
            element.addEventListener('mouseleave', (e) => {
                this.hideTooltip(e.target);
            });
        });
    }

    setupDarkMode() {
        // Check for saved dark mode preference or system preference
        const savedTheme = localStorage.getItem('theme');
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        
        if (savedTheme === 'dark' || (!savedTheme && systemPrefersDark)) {
            document.body.classList.add('dark-mode');
        }

        // Dark mode toggle button
        const darkModeToggle = document.querySelector('.dark-mode-toggle');
        if (darkModeToggle) {
            darkModeToggle.addEventListener('click', () => {
                this.toggleDarkMode();
            });
        }

        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem('theme')) {
                if (e.matches) {
                    document.body.classList.add('dark-mode');
                } else {
                    document.body.classList.remove('dark-mode');
                }
            }
        });
    }

    setupFormValidation() {
        // Custom validation patterns
        this.validationPatterns = {
            email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
            phone: /^[\+]?[1-9][\d]{0,15}$/,
            url: /^https?:\/\/.+/,
            numeric: /^\d+$/,
            alphanumeric: /^[a-zA-Z0-9]+$/,
            company: /^[a-zA-Z0-9\s\&\.\-\,]+$/
        };

        // Real-time validation for specific fields
        document.querySelectorAll('[data-validate]').forEach(field => {
            field.addEventListener('input', () => {
                this.validateField(field);
            });
        });
    }

    setupNotifications() {
        // Create notification container if it doesn't exist
        if (!document.querySelector('.notification-container')) {
            const container = document.createElement('div');
            container.className = 'notification-container';
            document.body.appendChild(container);
        }
    }

    // Utility Methods
    showNotification(message, type = 'info', duration = 3000) {
        const container = document.querySelector('.notification-container');
        const notification = document.createElement('div');
        notification.className = `notification-toast notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-${this.getNotificationIcon(type)}"></i>
                <div>
                    <div class="notification-message">${message}</div>
                </div>
            </div>
            <button class="notification-close">&times;</button>
        `;

        container.appendChild(notification);

        // Animate in
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);

        // Auto-dismiss
        setTimeout(() => {
            this.dismissNotification(notification);
        }, duration);

        // Manual dismiss
        notification.querySelector('.notification-close').addEventListener('click', () => {
            this.dismissNotification(notification);
        });
    }

    dismissNotification(notification) {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }

    getNotificationIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    }

    validateField(field) {
        const validationType = field.dataset.validate;
        const value = field.value.trim();
        let isValid = true;

        if (validationType && this.validationPatterns[validationType]) {
            isValid = this.validationPatterns[validationType].test(value);
        }

        if (field.hasAttribute('required') && !value) {
            isValid = false;
        }

        if (field.type === 'email' && value) {
            isValid = this.validationPatterns.email.test(value);
        }

        if (field.type === 'tel' && value) {
            isValid = this.validationPatterns.phone.test(value);
        }

        if (field.type === 'url' && value) {
            isValid = this.validationPatterns.url.test(value);
        }

        if (field.hasAttribute('minlength') && value.length < parseInt(field.minLength)) {
            isValid = false;
        }

        if (field.hasAttribute('maxlength') && value.length > parseInt(field.maxLength)) {
            isValid = false;
        }

        this.updateFieldValidation(field, isValid);
        return isValid;
    }

    updateFieldValidation(field, isValid) {
        const formGroup = field.closest('.form-group') || field.parentElement;
        const errorElement = formGroup.querySelector('.invalid-feedback') || formGroup.querySelector('.field-error');

        if (isValid) {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
            if (errorElement) {
                errorElement.style.display = 'none';
            }
        } else {
            field.classList.remove('is-valid');
            field.classList.add('is-invalid');
            if (errorElement) {
                errorElement.style.display = 'block';
            }
        }
    }

    setupFileUpload(area) {
        const fileInput = area.querySelector('input[type="file"]');
        const fileList = area.querySelector('.file-list');

        area.addEventListener('dragover', (e) => {
            e.preventDefault();
            area.classList.add('drag-over');
        });

        area.addEventListener('dragleave', () => {
            area.classList.remove('drag-over');
        });

        area.addEventListener('drop', (e) => {
            e.preventDefault();
            area.classList.remove('drag-over');
            const files = Array.from(e.dataTransfer.files);
            this.handleFileUpload(files, fileInput, fileList);
        });

        fileInput.addEventListener('change', (e) => {
            const files = Array.from(e.target.files);
            this.handleFileUpload(files, fileInput, fileList);
        });
    }

    handleFileUpload(files, fileInput, fileList) {
        // Validate file types and sizes
        const validFiles = files.filter(file => {
            const isValidType = this.validateFileType(file);
            const isValidSize = this.validateFileSize(file);
            
            if (!isValidType) {
                this.showNotification(`Invalid file type: ${file.name}`, 'error');
            }
            if (!isValidSize) {
                this.showNotification(`File too large: ${file.name}`, 'error');
            }
            
            return isValidType && isValidSize;
        });

        // Update file list display
        if (fileList && validFiles.length > 0) {
            fileList.innerHTML = validFiles.map(file => `
                <div class="file-item">
                    <i class="fas fa-file"></i>
                    <span>${file.name}</span>
                    <small>(${(file.size / 1024 / 1024).toFixed(2)} MB)</small>
                    <button class="btn-remove-file" data-file-name="${file.name}">&times;</button>
                </div>
            `).join('');

            // Add remove file functionality
            fileList.querySelectorAll('.btn-remove-file').forEach(btn => {
                btn.addEventListener('click', () => {
                    this.removeFile(btn.dataset.fileName, fileInput, fileList);
                });
            });
        }

        this.showNotification(`${validFiles.length} file(s) selected`, 'success');
    }

    validateFileType(file) {
        const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf', 'text/plain'];
        const allowedExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.txt', '.doc', '.docx'];
        
        const extension = '.' + file.name.split('.').pop().toLowerCase();
        
        return allowedTypes.includes(file.type) || allowedExtensions.includes(extension);
    }

    validateFileSize(file) {
        const maxSize = 10 * 1024 * 1024; // 10MB
        return file.size <= maxSize;
    }

    handleAutoRefresh(toggle) {
        const card = toggle.closest('.dashboard-card');
        const refreshIndicator = card.querySelector('.refresh-indicator');
        
        if (toggle.checked) {
            // Start auto-refresh
            this.startAutoRefresh(card, refreshIndicator);
        } else {
            // Stop auto-refresh
            this.stopAutoRefresh(card);
        }
    }

    startAutoRefresh(card, indicator) {
        const interval = setInterval(() => {
            if (indicator) {
                indicator.style.display = 'block';
            }
            
            // Simulate refresh (replace with actual API call)
            setTimeout(() => {
                if (indicator) {
                    indicator.style.display = 'none';
                }
                this.showNotification('Dashboard refreshed', 'info', 2000);
            }, 1000);
        }, 30000); // Refresh every 30 seconds

        card.dataset.refreshInterval = interval;
    }

    stopAutoRefresh(card) {
        const interval = card.dataset.refreshInterval;
        if (interval) {
            clearInterval(interval);
            delete card.dataset.refreshInterval;
        }
    }

    toggleDarkMode() {
        const isDarkMode = document.body.classList.toggle('dark-mode');
        localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');
        
        this.showNotification(
            isDarkMode ? 'Dark mode enabled' : 'Light mode enabled',
            'info',
            2000
        );
    }

    showTooltip(element, text) {
        const tooltip = document.createElement('div');
        tooltip.className = 'custom-tooltip';
        tooltip.textContent = text;
        document.body.appendChild(tooltip);

        const rect = element.getBoundingClientRect();
        tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
        tooltip.style.top = rect.top - tooltip.offsetHeight - 10 + 'px';

        setTimeout(() => {
            tooltip.classList.add('show');
        }, 10);
    }

    hideTooltip(element) {
        const tooltip = document.querySelector('.custom-tooltip');
        if (tooltip) {
            tooltip.classList.remove('show');
            setTimeout(() => {
                tooltip.remove();
            }, 300);
        }
    }

    fadeOut(element) {
        element.style.opacity = '1';
        const fadeEffect = setInterval(() => {
            if (element.style.opacity > '0') {
                element.style.opacity -= '0.1';
            } else {
                clearInterval(fadeEffect);
                element.remove();
            }
        }, 50);
    }

    // AJAX Helpers
    async makeRequest(url, options = {}) {
        const defaultOptions = {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': this.getCsrfToken()
            }
        };

        const finalOptions = { ...defaultOptions, ...options };

        try {
            const response = await fetch(url, finalOptions);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            } else {
                return await response.text();
            }
        } catch (error) {
            console.error('Request failed:', error);
            this.showNotification('Request failed. Please try again.', 'error');
            throw error;
        }
    }

    getCsrfToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    // Utility methods
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
}

// Initialize the framework when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.vendorFramework = new VendorFramework();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VendorFramework;
}