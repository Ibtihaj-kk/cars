/**
 * Intersection Observer Animations for Vendor Portal
 * Cars Portal - Scroll-triggered animations
 */

(function() {
    'use strict';

    class ScrollAnimations {
        constructor() {
            this.observer = null;
            this.animationElements = [];
            this.init();
        }

        init() {
            // Check if IntersectionObserver is supported
            if (!('IntersectionObserver' in window)) {
                // Fallback: show all elements immediately
                this.showAllElements();
                return;
            }

            this.setupObserver();
            this.findAnimationElements();
            this.observeElements();
        }

        setupObserver() {
            const options = {
                root: null, // viewport
                rootMargin: '0px 0px -50px 0px', // Trigger when element is 50px from viewport
                threshold: 0.1 // Trigger when 10% of element is visible
            };

            this.observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        this.animateElement(entry.target);
                        this.observer.unobserve(entry.target);
                    }
                });
            }, options);
        }

        findAnimationElements() {
            // Find elements with scroll animation classes
            this.animationElements = document.querySelectorAll(
                '.ym-fade-in-scroll, .ym-scale-in-scroll, .ym-slide-in-left'
            );
        }

        observeElements() {
            this.animationElements.forEach(element => {
                this.observer.observe(element);
            });
        }

        animateElement(element) {
            // Add visible class to trigger animation
            element.classList.add('ym-visible');
            
            // Add custom animation based on element type
            if (element.classList.contains('ym-card')) {
                this.addCardAnimation(element);
            } else if (element.classList.contains('ym-nav-item')) {
                this.addNavItemAnimation(element);
            }
            
            // Track analytics if available
            this.trackAnimation(element);
        }

        addCardAnimation(element) {
            // Add staggered delay for card grids
            const cards = element.parentElement?.querySelectorAll('.ym-card');
            if (cards) {
                const index = Array.from(cards).indexOf(element);
                element.style.animationDelay = `${index * 100}ms`;
            }
        }

        addNavItemAnimation(element) {
            // Add subtle bounce to navigation items
            element.style.animation = 'navItemStagger var(--ym-animation-normal) var(--ym-ease-bounce) forwards';
        }

        trackAnimation(element) {
            if (window.VendorPortal && window.VendorPortal.analytics) {
                window.VendorPortal.analytics.track('element_animated', {
                    element_type: element.className,
                    timestamp: new Date().toISOString(),
                    viewport_position: this.getElementViewportPosition(element)
                });
            }
        }

        getElementViewportPosition(element) {
            const rect = element.getBoundingClientRect();
            return {
                top: rect.top,
                left: rect.left,
                bottom: rect.bottom,
                right: rect.right,
                width: rect.width,
                height: rect.height
            };
        }

        showAllElements() {
            // Fallback for browsers without IntersectionObserver
            this.animationElements.forEach(element => {
                element.classList.add('ym-visible');
                element.style.opacity = '1';
                element.style.transform = 'none';
            });
        }

        // Public method to refresh animations
        refresh() {
            this.findAnimationElements();
            this.observeElements();
        }

        // Public method to manually trigger an element
        triggerElement(element) {
            if (element && this.animationElements.includes(element)) {
                this.animateElement(element);
                this.observer.unobserve(element);
            }
        }

        // Cleanup method
        destroy() {
            if (this.observer) {
                this.observer.disconnect();
            }
        }
    }

    // Enhanced scroll performance with throttling
    class ScrollPerformance {
        constructor() {
            this.ticking = false;
            this.init();
        }

        init() {
            window.addEventListener('scroll', this.throttle(() => {
                this.requestTick();
            }, 16)); // ~60fps
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

        requestTick() {
            if (!this.ticking) {
                requestAnimationFrame(this.updateScrollEffects.bind(this));
                this.ticking = true;
            }
        }

        updateScrollEffects() {
            // Add parallax effects for header
            const scrolled = window.pageYOffset;
            const header = document.querySelector('.ym-header-modern');
            
            if (header && scrolled > 50) {
                header.classList.add('scrolled');
                header.style.transform = `translateY(-${scrolled * 0.1}px)`;
            } else if (header) {
                header.classList.remove('scrolled');
                header.style.transform = '';
            }

            // Add subtle parallax to brand logo
            const logo = document.querySelector('.ym-brand-logo-svg');
            if (logo) {
                logo.style.transform = `translateY(-${scrolled * 0.05}px)`;
            }

            this.ticking = false;
        }
    }

    // Initialize everything when DOM is ready
    function initScrollAnimations() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
        } else {
            init();
        }

        function init() {
            // Initialize scroll animations
            window.vendorScrollAnimations = new ScrollAnimations();
            
            // Initialize scroll performance optimization
            window.vendorScrollPerformance = new ScrollPerformance();
            
            // Add CSS custom properties for scroll position
            const updateScrollProperties = () => {
                const scrollY = window.pageYOffset;
                const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
                const scrollPercent = maxScroll > 0 ? (scrollY / maxScroll) * 100 : 0;
                
                document.documentElement.style.setProperty('--scroll-y', `${scrollY}px`);
                document.documentElement.style.setProperty('--scroll-percent', `${scrollPercent}%`);
                
                requestAnimationFrame(updateScrollProperties);
            };
            
            requestAnimationFrame(updateScrollProperties);
        }
    }

    // Auto-initialize
    initScrollAnimations();

    // Export for global access
    window.ScrollAnimations = ScrollAnimations;
    window.ScrollPerformance = ScrollPerformance;

})();