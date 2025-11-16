/**
 * Vendor Header Navigation System
 * Handles mobile menu, user dropdown, and responsive navigation
 */

class VendorHeaderNavigation {
    constructor() {
        this.mobileMenuToggle = document.querySelector('.ym-mobile-menu-toggle');
        this.mobileNav = document.querySelector('.ym-mobile-nav');
        this.mobileNavOverlay = document.querySelector('#mobile-nav-overlay');
        this.mobileNavClose = document.querySelector('.ym-mobile-nav-close');
        this.userDropdownTrigger = document.querySelector('.ym-user-dropdown-trigger');
        this.userDropdownMenu = document.querySelector('.ym-user-dropdown-menu');
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.setupResponsive();
        this.setupDropdown();
    }
    
    bindEvents() {
        // Mobile menu toggle
        if (this.mobileMenuToggle) {
            this.mobileMenuToggle.addEventListener('click', this.toggleMobileMenu.bind(this));
        }
        
        // Mobile menu close
        if (this.mobileNavClose) {
            this.mobileNavClose.addEventListener('click', this.closeMobileMenu.bind(this));
        }
        
        // Overlay click to close
        if (this.mobileNavOverlay) {
            this.mobileNavOverlay.addEventListener('click', this.closeMobileMenu.bind(this));
        }
        
        // User dropdown
        if (this.userDropdownTrigger) {
            this.userDropdownTrigger.addEventListener('click', this.toggleUserDropdown.bind(this));
        }
        
        // Close dropdown when clicking outside
        document.addEventListener('click', this.handleOutsideClick.bind(this));
        
        // Escape key to close menus
        document.addEventListener('keydown', this.handleEscapeKey.bind(this));
        
        // Window resize
        window.addEventListener('resize', this.handleResize.bind(this));
    }
    
    toggleMobileMenu() {
        const isOpen = this.mobileMenuToggle.getAttribute('aria-expanded') === 'true';
        
        if (isOpen) {
            this.closeMobileMenu();
        } else {
            this.openMobileMenu();
        }
    }
    
    openMobileMenu() {
        this.mobileMenuToggle.setAttribute('aria-expanded', 'true');
        this.mobileNav.classList.remove('ym-hidden');
        this.mobileNavOverlay.classList.remove('ym-hidden');
        this.mobileNav.setAttribute('aria-hidden', 'false');
        
        // Prevent body scroll
        document.body.style.overflow = 'hidden';
        
        // Focus management
        this.mobileNavClose.focus();
        
        // Analytics tracking
        this.trackEvent('mobile_menu_opened');
    }
    
    closeMobileMenu() {
        this.mobileMenuToggle.setAttribute('aria-expanded', 'false');
        this.mobileNav.classList.add('ym-hidden');
        this.mobileNavOverlay.classList.add('ym-hidden');
        this.mobileNav.setAttribute('aria-hidden', 'true');
        
        // Restore body scroll
        document.body.style.overflow = '';
        
        // Focus management
        this.mobileMenuToggle.focus();
        
        // Analytics tracking
        this.trackEvent('mobile_menu_closed');
    }
    
    toggleUserDropdown(event) {
        event.stopPropagation();
        
        const isOpen = this.userDropdownTrigger.getAttribute('aria-expanded') === 'true';
        
        if (isOpen) {
            this.closeUserDropdown();
        } else {
            this.openUserDropdown();
        }
    }
    
    openUserDropdown() {
        this.userDropdownTrigger.setAttribute('aria-expanded', 'true');
        this.userDropdownMenu.setAttribute('aria-hidden', 'false');
        this.userDropdownMenu.classList.add('ym-dropdown-open');
        
        // Analytics tracking
        this.trackEvent('user_dropdown_opened');
    }
    
    closeUserDropdown() {
        this.userDropdownTrigger.setAttribute('aria-expanded', 'false');
        this.userDropdownMenu.setAttribute('aria-hidden', 'true');
        this.userDropdownMenu.classList.remove('ym-dropdown-open');
        
        // Analytics tracking
        this.trackEvent('user_dropdown_closed');
    }
    
    handleOutsideClick(event) {
        // Close user dropdown when clicking outside
        if (this.userDropdownTrigger && 
            !this.userDropdownTrigger.contains(event.target) && 
            !this.userDropdownMenu.contains(event.target)) {
            this.closeUserDropdown();
        }
    }
    
    handleEscapeKey(event) {
        if (event.key === 'Escape') {
            // Close mobile menu if open
            if (this.mobileMenuToggle.getAttribute('aria-expanded') === 'true') {
                this.closeMobileMenu();
            }
            
            // Close user dropdown if open
            if (this.userDropdownTrigger.getAttribute('aria-expanded') === 'true') {
                this.closeUserDropdown();
            }
        }
    }
    
    handleResize() {
        // Close mobile menu when resizing to desktop
        if (window.innerWidth >= 768 && this.mobileMenuToggle.getAttribute('aria-expanded') === 'true') {
            this.closeMobileMenu();
        }
    }
    
    setupResponsive() {
        // Add responsive behavior
        const mediaQuery = window.matchMedia('(max-width: 768px)');
        
        const handleMediaChange = (e) => {
            if (!e.matches) {
                // Desktop view - ensure menus are closed
                this.closeMobileMenu();
            }
        };
        
        mediaQuery.addListener(handleMediaChange);
        handleMediaChange(mediaQuery);
    }
    
    setupDropdown() {
        // Add dropdown-specific styles if not already present
        if (!document.querySelector('#vendor-header-styles')) {
            const style = document.createElement('style');
            style.id = 'vendor-header-styles';
            style.textContent = `
                .ym-dropdown-open {
                    opacity: 1 !important;
                    visibility: visible !important;
                    transform: translateY(0) !important;
                }
                
                .ym-mobile-nav:not(.ym-hidden) {
                    right: 0 !important;
                }
                
                .ym-mobile-nav-overlay:not(.ym-hidden) {
                    opacity: 1 !important;
                    visibility: visible !important;
                }
            `;
            document.head.appendChild(style);
        }
    }
    
    trackEvent(eventName, data = {}) {
        // Track navigation events for analytics
        if (window.VendorPortal && window.VendorPortal.analytics) {
            window.VendorPortal.analytics.track(eventName, {
                component: 'header_navigation',
                timestamp: new Date().toISOString(),
                ...data
            });
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    new VendorHeaderNavigation();
});

// Export for use in other scripts
window.VendorHeaderNavigation = VendorHeaderNavigation;