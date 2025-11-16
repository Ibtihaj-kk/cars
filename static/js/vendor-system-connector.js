/**
 * Vendor System Connector
 * Ensures all standardized vendor pages work together cohesively
 * Handles inter-page navigation, state management, and system-wide functionality
 */

(function() {
    'use strict';
    
    // System configuration
    const VENDOR_SYSTEM = {
        version: '1.0.0',
        debug: true,
        breakpoints: {
            xs: 640,
            sm: 768,
            md: 1024,
            lg: 1280
        },
        pages: {
            dashboard: '/business-partners/dashboard/',
            parts: '/business-partners/parts/',
            orders: '/business-partners/orders/',
            analytics: '/business-partners/analytics/',
            settings: '/business-partners/settings/'
        }
    };
    
    // Global state management
    const VendorState = {
        currentPage: null,
        userPreferences: {},
        notifications: [],
        cart: [],
        filters: {},
        
        // Initialize state from localStorage
        init: function() {
            this.loadUserPreferences();
            this.loadNotifications();
            this.loadCart();
            this.loadFilters();
            this.determineCurrentPage();
        },
        
        loadUserPreferences: function() {
            const saved = localStorage.getItem('vendor-preferences');
            this.userPreferences = saved ? JSON.parse(saved) : {
                theme: 'light',
                notifications: true,
                compactMode: false,
                language: 'en'
            };
        },
        
        saveUserPreferences: function() {
            localStorage.setItem('vendor-preferences', JSON.stringify(this.userPreferences));
        },
        
        loadNotifications: function() {
            const saved = localStorage.getItem('vendor-notifications');
            this.notifications = saved ? JSON.parse(saved) : [];
        },
        
        loadCart: function() {
            const saved = localStorage.getItem('vendor-cart');
            this.cart = saved ? JSON.parse(saved) : [];
        },
        
        loadFilters: function() {
            const saved = localStorage.getItem('vendor-filters');
            this.filters = saved ? JSON.parse(saved) : {};
        },
        
        determineCurrentPage: function() {
            const path = window.location.pathname;
            if (path.includes('dashboard')) this.currentPage = 'dashboard';
            else if (path.includes('parts')) this.currentPage = 'parts';
            else if (path.includes('orders')) this.currentPage = 'orders';
            else if (path.includes('analytics')) this.currentPage = 'analytics';
            else if (path.includes('settings')) this.currentPage = 'settings';
            else this.currentPage = 'unknown';
        }
    };
    
    // Navigation manager
    const VendorNavigation = {
        init: function() {
            this.setupNavigationLinks();
            this.setupBreadcrumbNavigation();
            this.setupQuickActions();
            this.highlightCurrentPage();
        },
        
        setupNavigationLinks: function() {
            // Add click handlers to main navigation links
            document.querySelectorAll('.ym-nav-link').forEach(link => {
                link.addEventListener('click', function(e) {
                    // Add loading state
                    document.body.classList.add('ym-page-loading');
                    
                    // Update active state
                    document.querySelectorAll('.ym-nav-link').forEach(l => l.classList.remove('ym-active'));
                    this.classList.add('ym-active');
                    
                    // Log navigation for analytics
                    if (VENDOR_SYSTEM.debug) {
                        console.log('Navigating to:', this.getAttribute('href'));
                    }
                });
            });
        },
        
        setupBreadcrumbNavigation: function() {
            // Make breadcrumb links interactive
            document.querySelectorAll('.ym-breadcrumb-link').forEach(link => {
                link.addEventListener('click', function(e) {
                    // Add smooth transitions
                    this.style.transition = 'all 0.3s ease';
                });
            });
        },
        
        setupQuickActions: function() {
            // Setup quick action buttons
            document.querySelectorAll('.ym-quick-action').forEach(button => {
                button.addEventListener('click', function(e) {
                    const action = this.getAttribute('data-action');
                    VendorActions.execute(action, this);
                });
            });
        },
        
        highlightCurrentPage: function() {
            // Highlight current page in navigation
            const currentPath = window.location.pathname;
            document.querySelectorAll('.ym-nav-link').forEach(link => {
                const href = link.getAttribute('href');
                if (href && currentPath.includes(href.replace('/', ''))) {
                    link.classList.add('ym-active');
                }
            });
        }
    };
    
    // Action handler
    const VendorActions = {
        execute: function(action, element) {
            switch(action) {
                case 'refresh-dashboard':
                    this.refreshDashboard();
                    break;
                case 'add-part':
                    this.addPart();
                    break;
                case 'bulk-update':
                    this.bulkUpdate();
                    break;
                case 'export-data':
                    this.exportData();
                    break;
                case 'import-data':
                    this.importData();
                    break;
                case 'print-report':
                    this.printReport();
                    break;
                default:
                    console.warn('Unknown action:', action);
            }
        },
        
        refreshDashboard: function() {
            if (VENDOR_SYSTEM.debug) console.log('Refreshing dashboard...');
            
            // Show loading state
            const loadingOverlay = document.getElementById('global-loading-overlay');
            if (loadingOverlay) {
                loadingOverlay.classList.remove('ym-hidden');
            }
            
            // Simulate refresh
            setTimeout(() => {
                if (loadingOverlay) {
                    loadingOverlay.classList.add('ym-hidden');
                }
                
                // Trigger dashboard refresh
                if (typeof refreshDashboardData === 'function') {
                    refreshDashboardData();
                }
                
                // Show success message
                VendorNotifications.show('Dashboard refreshed successfully', 'success');
            }, 1000);
        },
        
        addPart: function() {
            if (VENDOR_SYSTEM.debug) console.log('Adding new part...');
            
            // Open add part modal or navigate to add part page
            const modal = document.getElementById('add-part-modal');
            if (modal) {
                modal.classList.remove('ym-hidden');
                modal.setAttribute('aria-hidden', 'false');
            } else {
                window.location.href = VENDOR_SYSTEM.pages.parts + 'add/';
            }
        },
        
        bulkUpdate: function() {
            if (VENDOR_SYSTEM.debug) console.log('Opening bulk update...');
            VendorModals.open('bulk-update-modal');
        },
        
        exportData: function() {
            if (VENDOR_SYSTEM.debug) console.log('Exporting data...');
            
            // Trigger export functionality
            if (typeof exportVendorData === 'function') {
                exportVendorData();
            } else {
                VendorNotifications.show('Export functionality not available', 'warning');
            }
        },
        
        importData: function() {
            if (VENDOR_SYSTEM.debug) console.log('Opening import dialog...');
            VendorModals.open('import-data-modal');
        },
        
        printReport: function() {
            if (VENDOR_SYSTEM.debug) console.log('Preparing print...');
            window.print();
        }
    };
    
    // Modal manager
    const VendorModals = {
        open: function(modalId) {
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.classList.remove('ym-hidden');
                modal.setAttribute('aria-hidden', 'false');
                document.body.classList.add('ym-modal-open');
                
                // Focus management
                const focusableElements = modal.querySelectorAll('button, input, select, textarea, [tabindex]:not([tabindex="-1"])');
                if (focusableElements.length > 0) {
                    focusableElements[0].focus();
                }
            }
        },
        
        close: function(modalId) {
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.classList.add('ym-hidden');
                modal.setAttribute('aria-hidden', 'true');
                document.body.classList.remove('ym-modal-open');
            }
        }
    };
    
    // Notification system
    const VendorNotifications = {
        show: function(message, type = 'info', duration = 5000) {
            const notification = document.createElement('div');
            notification.className = `ym-notification ym-notification-${type}`;
            notification.innerHTML = `
                <div class="ym-notification-content">
                    <span class="ym-notification-message">${message}</span>
                    <button class="ym-notification-close" aria-label="Close notification">&times;</button>
                </div>
            `;
            
            // Add to notification container or body
            const container = document.getElementById('notification-container') || document.body;
            container.appendChild(notification);
            
            // Add to state
            VendorState.notifications.push({
                id: Date.now(),
                message: message,
                type: type,
                timestamp: new Date()
            });
            
            // Auto remove
            setTimeout(() => {
                this.remove(notification);
            }, duration);
            
            // Close button
            notification.querySelector('.ym-notification-close').addEventListener('click', () => {
                this.remove(notification);
            });
        },
        
        remove: function(notification) {
            notification.style.opacity = '0';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }
    };
    
    // Responsive utilities
    const VendorResponsive = {
        currentBreakpoint: null,
        
        init: function() {
            this.updateBreakpoint();
            window.addEventListener('resize', () => this.updateBreakpoint());
        },
        
        updateBreakpoint: function() {
            const width = window.innerWidth;
            let breakpoint = 'xs';
            
            if (width >= VENDOR_SYSTEM.breakpoints.xl) breakpoint = 'xl';
            else if (width >= VENDOR_SYSTEM.breakpoints.lg) breakpoint = 'lg';
            else if (width >= VENDOR_SYSTEM.breakpoints.md) breakpoint = 'md';
            else if (width >= VENDOR_SYSTEM.breakpoints.sm) breakpoint = 'sm';
            
            if (this.currentBreakpoint !== breakpoint) {
                this.currentBreakpoint = breakpoint;
                this.onBreakpointChange(breakpoint);
            }
        },
        
        onBreakpointChange: function(breakpoint) {
            if (VENDOR_SYSTEM.debug) {
                console.log('Breakpoint changed to:', breakpoint);
            }
            
            // Update body class
            document.body.className = document.body.className.replace(/ym-breakpoint-\w+/g, '');
            document.body.classList.add(`ym-breakpoint-${breakpoint}`);
            
            // Trigger custom event
            window.dispatchEvent(new CustomEvent('vendor:breakpoint-change', {
                detail: { breakpoint: breakpoint }
            }));
        },
        
        isMobile: function() {
            return this.currentBreakpoint === 'xs' || this.currentBreakpoint === 'sm';
        },
        
        isTablet: function() {
            return this.currentBreakpoint === 'md';
        },
        
        isDesktop: function() {
            return this.currentBreakpoint === 'lg' || this.currentBreakpoint === 'xl';
        }
    };
    
    // Form handler
    const VendorForms = {
        init: function() {
            this.setupFormValidation();
            this.setupAutoSave();
            this.setupFormHelpers();
        },
        
        setupFormValidation: function() {
            document.querySelectorAll('.ym-form').forEach(form => {
                form.addEventListener('submit', (e) => {
                    if (!this.validateForm(form)) {
                        e.preventDefault();
                        VendorNotifications.show('Please fix the errors in the form', 'error');
                    }
                });
            });
        },
        
        validateForm: function(form) {
            let isValid = true;
            const requiredFields = form.querySelectorAll('[required]');
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    field.classList.add('ym-error');
                    isValid = false;
                } else {
                    field.classList.remove('ym-error');
                }
            });
            
            return isValid;
        },
        
        setupAutoSave: function() {
            document.querySelectorAll('.ym-form-autosave').forEach(form => {
                let autoSaveTimeout;
                form.addEventListener('input', () => {
                    clearTimeout(autoSaveTimeout);
                    autoSaveTimeout = setTimeout(() => {
                        this.autoSaveForm(form);
                    }, 2000);
                });
            });
        },
        
        autoSaveForm: function(form) {
            const formData = new FormData(form);
            // Implement auto-save logic
            if (VENDOR_SYSTEM.debug) {
                console.log('Auto-saving form:', form.id);
            }
        },
        
        setupFormHelpers: function() {
            // Setup character counters
            document.querySelectorAll('[data-maxlength]').forEach(field => {
                const maxLength = parseInt(field.getAttribute('data-maxlength'));
                const counter = document.createElement('div');
                counter.className = 'ym-character-counter';
                field.parentNode.appendChild(counter);
                
                field.addEventListener('input', () => {
                    const remaining = maxLength - field.value.length;
                    counter.textContent = `${remaining} characters remaining`;
                    counter.style.color = remaining < 20 ? '#ef4444' : '#6b7280';
                });
            });
        }
    };
    
    // Initialize the system
    function initializeVendorSystem() {
        if (VENDOR_SYSTEM.debug) {
            console.log('Initializing Vendor System Connector v' + VENDOR_SYSTEM.version);
        }
        
        // Initialize all modules
        VendorState.init();
        VendorNavigation.init();
        VendorResponsive.init();
        VendorForms.init();
        
        // Add global loading state management
        document.addEventListener('DOMContentLoaded', () => {
            document.body.classList.remove('ym-loading');
            
            // Show welcome message on first visit
            if (!localStorage.getItem('vendor-welcome-shown')) {
                VendorNotifications.show('Welcome to the Vendor Portal! Your dashboard has been updated.', 'success', 8000);
                localStorage.setItem('vendor-welcome-shown', 'true');
            }
        });
        
        // Expose global functions for other scripts
        window.VendorSystem = {
            state: VendorState,
            navigation: VendorNavigation,
            actions: VendorActions,
            modals: VendorModals,
            notifications: VendorNotifications,
            responsive: VendorResponsive,
            forms: VendorForms
        };
    }
    
    // Start the system
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeVendorSystem);
    } else {
        initializeVendorSystem();
    }
    
})();