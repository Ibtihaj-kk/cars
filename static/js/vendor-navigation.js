/**
 * Vendor Navigation System
 * Integrated with Unified Design System
 */

class VendorNavigation {
    constructor(options = {}) {
        this.options = {
            sidebarSelector: '.ym-sidebar',
            navToggleSelector: '.ym-nav-toggle',
            navLinkSelector: '.ym-nav-link',
            submenuSelector: '.ym-nav-submenu',
            autoCollapse: true,
            rememberState: true,
            storageKey: 'vendor-nav-state',
            ...options
        };
        
        this.sidebar = document.querySelector(this.options.sidebarSelector);
        this.navToggle = document.querySelector(this.options.navToggleSelector);
        this.navLinks = document.querySelectorAll(this.options.navLinkSelector);
        
        this.init();
    }
    
    init() {
        if (!this.sidebar && !this.navToggle) {
            console.warn('Navigation elements not found');
            return;
        }
        
        this.bindEvents();
        this.setupSubmenus();
        this.restoreState();
        this.highlightCurrentPage();
        this.setupResponsive();
    }
    
    bindEvents() {
        // Mobile nav toggle
        if (this.navToggle) {
            this.navToggle.addEventListener('click', this.toggleSidebar.bind(this));
        }
        
        // Navigation links
        this.navLinks.forEach(link => {
            link.addEventListener('click', this.handleNavClick.bind(this));
        });
        
        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', this.handleOutsideClick.bind(this));
        
        // Handle window resize
        window.addEventListener('resize', this.handleResize.bind(this));
        
        // Handle escape key
        document.addEventListener('keydown', this.handleEscape.bind(this));
    }
    
    setupSubmenus() {
        const submenuTriggers = document.querySelectorAll('[data-toggle="submenu"]');
        
        submenuTriggers.forEach(trigger => {
            trigger.addEventListener('click', (e) => {
                e.preventDefault();
                const target = trigger.getAttribute('data-target');
                const submenu = document.querySelector(target);
                
                if (submenu) {
                    this.toggleSubmenu(trigger.parentElement, submenu);
                }
            });
        });
    }
    
    toggleSidebar() {
        if (!this.sidebar) return;
        
        const isOpen = this.sidebar.classList.contains('ym-open');
        
        if (isOpen) {
            this.closeSidebar();
        } else {
            this.openSidebar();
        }
        
        this.saveState();
    }
    
    openSidebar() {
        if (!this.sidebar) return;
        
        this.sidebar.classList.add('ym-open');
        document.body.classList.add('ym-sidebar-open');
        
        // Add overlay
        this.createOverlay();
        
        // Focus management
        this.sidebar.setAttribute('aria-hidden', 'false');
        this.navToggle?.setAttribute('aria-expanded', 'true');
        
        // Focus first focusable element
        const firstFocusable = this.sidebar.querySelector('a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])');
        if (firstFocusable) {
            firstFocusable.focus();
        }
        
        this.emit('sidebar:open');
    }
    
    closeSidebar() {
        if (!this.sidebar) return;
        
        this.sidebar.classList.remove('ym-open');
        document.body.classList.remove('ym-sidebar-open');
        
        // Remove overlay
        this.removeOverlay();
        
        // Focus management
        this.sidebar.setAttribute('aria-hidden', 'true');
        this.navToggle?.setAttribute('aria-expanded', 'false');
        this.navToggle?.focus();
        
        this.emit('sidebar:close');
    }
    
    createOverlay() {
        if (document.querySelector('.ym-nav-overlay')) return;
        
        const overlay = document.createElement('div');
        overlay.className = 'ym-nav-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            z-index: 99;
            opacity: 0;
            transition: opacity 0.3s ease;
        `;
        
        document.body.appendChild(overlay);
        
        // Animate in
        requestAnimationFrame(() => {
            overlay.style.opacity = '1';
        });
        
        overlay.addEventListener('click', this.closeSidebar.bind(this));
        
        this.overlay = overlay;
    }
    
    removeOverlay() {
        if (this.overlay) {
            this.overlay.style.opacity = '0';
            setTimeout(() => {
                this.overlay?.remove();
                this.overlay = null;
            }, 300);
        }
    }
    
    toggleSubmenu(parent, submenu) {
        const isExpanded = parent.classList.contains('ym-expanded');
        
        if (this.options.autoCollapse) {
            // Collapse other submenus
            document.querySelectorAll('.ym-nav-item.ym-expanded').forEach(item => {
                if (item !== parent) {
                    item.classList.remove('ym-expanded');
                    const otherSubmenu = item.querySelector('.ym-nav-submenu');
                    if (otherSubmenu) {
                        otherSubmenu.style.maxHeight = '0';
                    }
                }
            });
        }
        
        if (isExpanded) {
            parent.classList.remove('ym-expanded');
            submenu.style.maxHeight = '0';
            
            // Update ARIA attributes
            const trigger = parent.querySelector('[data-toggle="submenu"]');
            if (trigger) {
                trigger.setAttribute('aria-expanded', 'false');
            }
            
            this.emit('submenu:collapse', { parent, submenu });
        } else {
            parent.classList.add('ym-expanded');
            submenu.style.maxHeight = submenu.scrollHeight + 'px';
            
            // Update ARIA attributes
            const trigger = parent.querySelector('[data-toggle="submenu"]');
            if (trigger) {
                trigger.setAttribute('aria-expanded', 'true');
            }
            
            this.emit('submenu:expand', { parent, submenu });
        }
        
        this.saveState();
    }
    
    handleNavClick(e) {
        const link = e.target.closest('.ym-nav-link');
        if (!link) return;
        
        // Handle submenu triggers
        if (link.hasAttribute('data-toggle')) {
            return; // Already handled by setupSubmenus
        }
        
        // Update active state
        this.navLinks.forEach(l => l.classList.remove('ym-active'));
        link.classList.add('ym-active');
        
        // Close mobile sidebar
        if (window.innerWidth <= 768) {
            this.closeSidebar();
        }
        
        this.emit('nav:click', { link, href: link.getAttribute('href') });
    }
    
    handleOutsideClick(e) {
        if (!this.sidebar) return;
        
        const isOpen = this.sidebar.classList.contains('ym-open');
        const isClickInsideSidebar = this.sidebar.contains(e.target);
        const isClickOnToggle = this.navToggle && this.navToggle.contains(e.target);
        
        if (isOpen && !isClickInsideSidebar && !isClickOnToggle) {
            this.closeSidebar();
        }
    }
    
    handleResize() {
        // Auto-close sidebar on desktop
        if (window.innerWidth > 768 && this.sidebar?.classList.contains('ym-open')) {
            this.closeSidebar();
        }
    }
    
    handleEscape(e) {
        if (e.key === 'Escape' && this.sidebar?.classList.contains('ym-open')) {
            this.closeSidebar();
        }
    }
    
    highlightCurrentPage() {
        const currentPath = window.location.pathname;
        
        this.navLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href && currentPath.includes(href.replace(window.location.origin, ''))) {
                link.classList.add('ym-active');
                
                // Expand parent submenus
                let parent = link.closest('.ym-nav-submenu');
                while (parent) {
                    const parentItem = parent.closest('.ym-nav-item');
                    if (parentItem) {
                        parentItem.classList.add('ym-expanded');
                        parent.style.maxHeight = parent.scrollHeight + 'px';
                    }
                    parent = parent.parentElement?.closest('.ym-nav-submenu');
                }
            }
        });
    }
    
    setupResponsive() {
        // Add responsive classes based on screen size
        const updateResponsive = () => {
            if (window.innerWidth <= 768) {
                document.body.classList.add('ym-mobile-nav');
                document.body.classList.remove('ym-desktop-nav');
            } else {
                document.body.classList.remove('ym-mobile-nav');
                document.body.classList.add('ym-desktop-nav');
            }
        };
        
        updateResponsive();
        window.addEventListener('resize', updateResponsive);
    }
    
    saveState() {
        if (!this.options.rememberState) return;
        
        const state = {
            expandedItems: Array.from(document.querySelectorAll('.ym-nav-item.ym-expanded')).map(item => {
                const trigger = item.querySelector('[data-toggle="submenu"]');
                return trigger?.getAttribute('data-target');
            }).filter(Boolean)
        };
        
        localStorage.setItem(this.options.storageKey, JSON.stringify(state));
    }
    
    restoreState() {
        if (!this.options.rememberState) return;
        
        try {
            const savedState = localStorage.getItem(this.options.storageKey);
            if (savedState) {
                const state = JSON.parse(savedState);
                
                state.expandedItems.forEach(target => {
                    const submenu = document.querySelector(target);
                    const parent = submenu?.closest('.ym-nav-item');
                    const trigger = parent?.querySelector('[data-toggle="submenu"]');
                    
                    if (submenu && parent && trigger) {
                        parent.classList.add('ym-expanded');
                        submenu.style.maxHeight = submenu.scrollHeight + 'px';
                        trigger.setAttribute('aria-expanded', 'true');
                    }
                });
            }
        } catch (error) {
            console.warn('Failed to restore navigation state:', error);
        }
    }
    
    // Event system
    emit(eventName, data = {}) {
        const event = new CustomEvent(`vendor-nav:${eventName}`, {
            detail: data,
            bubbles: true
        });
        document.dispatchEvent(event);
    }
    
    on(eventName, callback) {
        document.addEventListener(`vendor-nav:${eventName}`, callback);
    }
    
    off(eventName, callback) {
        document.removeEventListener(`vendor-nav:${eventName}`, callback);
    }
    
    // Public API
    expandAll() {
        document.querySelectorAll('.ym-nav-item').forEach(item => {
            const submenu = item.querySelector('.ym-nav-submenu');
            if (submenu) {
                item.classList.add('ym-expanded');
                submenu.style.maxHeight = submenu.scrollHeight + 'px';
            }
        });
        this.saveState();
    }
    
    collapseAll() {
        document.querySelectorAll('.ym-nav-item.ym-expanded').forEach(item => {
            const submenu = item.querySelector('.ym-nav-submenu');
            if (submenu) {
                item.classList.remove('ym-expanded');
                submenu.style.maxHeight = '0';
            }
        });
        this.saveState();
    }
    
    setActive(href) {
        this.navLinks.forEach(link => {
            link.classList.remove('ym-active');
            if (link.getAttribute('href') === href) {
                link.classList.add('ym-active');
            }
        });
    }
    
    destroy() {
        // Remove event listeners
        this.navToggle?.removeEventListener('click', this.toggleSidebar);
        this.navLinks.forEach(link => {
            link.removeEventListener('click', this.handleNavClick);
        });
        document.removeEventListener('click', this.handleOutsideClick);
        document.removeEventListener('keydown', this.handleEscape);
        window.removeEventListener('resize', this.handleResize);
        
        // Remove classes and attributes
        this.sidebar?.classList.remove('ym-open');
        document.body.classList.remove('ym-sidebar-open', 'ym-mobile-nav', 'ym-desktop-nav');
        this.removeOverlay();
        
        // Remove storage
        if (this.options.rememberState) {
            localStorage.removeItem(this.options.storageKey);
        }
    }
}

// CSS for navigation system
const navigationCSS = `
.ym-nav-overlay {
    backdrop-filter: blur(2px);
}

@media (max-width: 768px) {
    body.ym-sidebar-open {
        overflow: hidden;
    }
    
    .ym-sidebar {
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    
    .ym-sidebar.ym-open {
        transform: translateX(0);
    }
}

@media (prefers-reduced-motion: reduce) {
    .ym-sidebar {
        transition: none;
    }
    
    .ym-nav-submenu {
        transition: none;
    }
}
`;

// Inject CSS
if (!document.querySelector('#ym-navigation-styles')) {
    const style = document.createElement('style');
    style.id = 'ym-navigation-styles';
    style.textContent = navigationCSS;
    document.head.appendChild(style);
}

// Export for use
window.VendorNavigation = VendorNavigation;

// Auto-initialize if elements are present
document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('.ym-sidebar, .ym-nav-toggle')) {
        new VendorNavigation();
    }
});