/**
 * Enhanced Mobile Navigation with Swipe Gestures and Accessibility
 * Cars Portal Vendor Portal - Mobile Navigation System
 */

(function() {
    'use strict';

    class MobileNavigation {
        constructor() {
            this.mobileNav = document.querySelector('[data-mobile-nav]');
            this.mobileOverlay = document.querySelector('[data-mobile-overlay]');
            this.mobileToggle = document.querySelector('[data-mobile-toggle]');
            this.mobileClose = document.querySelector('[data-mobile-close]');
            this.swipeIndicator = document.querySelector('[data-swipe-indicator]');
            
            this.isOpen = false;
            this.touchStartX = 0;
            this.touchEndX = 0;
            this.swipeThreshold = 50;
            this.isAnimating = false;
            
            this.init();
        }

        init() {
            this.bindEvents();
            this.setupSwipeGestures();
            this.setupKeyboardNavigation();
            this.setupFocusManagement();
            this.hideSwipeIndicatorAfterDelay();
        }

        bindEvents() {
            // Toggle button events
            if (this.mobileToggle) {
                this.mobileToggle.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.toggle();
                });
            }

            // Close button events
            if (this.mobileClose) {
                this.mobileClose.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.close();
                });
            }

            // Overlay click to close
            if (this.mobileOverlay) {
                this.mobileOverlay.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.close();
                });
            }

            // Window resize - close mobile nav on desktop
            window.addEventListener('resize', this.debounce(() => {
                if (window.innerWidth >= 768 && this.isOpen) {
                    this.close();
                }
            }, 250));
        }

        setupSwipeGestures() {
            if (!this.mobileNav && !this.swipeIndicator) return;

            // Touch events for swipe gestures
            document.addEventListener('touchstart', (e) => {
                this.touchStartX = e.changedTouches[0].screenX;
            }, { passive: true });

            document.addEventListener('touchend', (e) => {
                this.touchEndX = e.changedTouches[0].screenX;
                this.handleSwipeGesture();
            }, { passive: true });
        }

        handleSwipeGesture() {
            const swipeDistance = this.touchEndX - this.touchStartX;
            
            // Swipe right to open (from left edge)
            if (swipeDistance > this.swipeThreshold && this.touchStartX < 50 && !this.isOpen) {
                this.open();
            }
            
            // Swipe left to close (when nav is open)
            if (swipeDistance < -this.swipeThreshold && this.isOpen) {
                this.close();
            }
        }

        setupKeyboardNavigation() {
            // Escape key to close mobile nav and return focus
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && this.isOpen) {
                    this.close();
                    if (this.mobileToggle) {
                        this.mobileToggle.focus();
                    }
                }
            });
        }

        setupFocusManagement() {
            // Focus management for accessibility
            if (!this.mobileNav) return;
            
            // Get all focusable elements in the mobile nav
            const focusableElements = this.mobileNav.querySelectorAll(
                'a[href], button, textarea, input[type="text"], input[type="radio"], input[type="checkbox"], select'
            );
            
            if (focusableElements.length === 0) return;
            
            this.firstFocusableElement = focusableElements[0];
            this.lastFocusableElement = focusableElements[focusableElements.length - 1];
            
            // Add focus trap
            this.mobileNav.addEventListener('keydown', (e) => {
                if (e.key === 'Tab') {
                    if (e.shiftKey) {
                        // Shift + Tab
                        if (document.activeElement === this.firstFocusableElement) {
                            this.lastFocusableElement.focus();
                            e.preventDefault();
                        }
                    } else {
                        // Tab
                        if (document.activeElement === this.lastFocusableElement) {
                            this.firstFocusableElement.focus();
                            e.preventDefault();
                        }
                    }
                }
            });
        }

        hideSwipeIndicatorAfterDelay() {
            if (this.swipeIndicator) {
                setTimeout(() => {
                    this.swipeIndicator.style.display = 'none';
                }, 5000);
            }
        }

        toggle() {
            if (this.isOpen) {
                this.close();
            } else {
                this.open();
            }
        }

        open() {
            if (this.isAnimating || this.isOpen) return;
            
            this.isAnimating = true;
            this.isOpen = true;

            // Update ARIA attributes
            if (this.mobileToggle) {
                this.mobileToggle.setAttribute('aria-expanded', 'true');
            }
            
            if (this.mobileNav) {
                this.mobileNav.setAttribute('aria-hidden', 'false');
            }
            
            if (this.mobileOverlay) {
                this.mobileOverlay.classList.remove('ym-hidden');
                this.mobileOverlay.setAttribute('aria-hidden', 'false');
            }

            // Hide swipe indicator
            if (this.swipeIndicator) {
                this.swipeIndicator.style.display = 'none';
            }

            setTimeout(() => {
                this.isAnimating = false;
            }, 300);
        }

        close() {
            if (this.isAnimating || !this.isOpen) return;
            
            this.isAnimating = true;
            this.isOpen = false;

            // Update ARIA attributes
            if (this.mobileToggle) {
                this.mobileToggle.setAttribute('aria-expanded', 'false');
            }
            
            if (this.mobileNav) {
                this.mobileNav.setAttribute('aria-hidden', 'true');
            }
            
            if (this.mobileOverlay) {
                this.mobileOverlay.classList.add('ym-hidden');
                this.mobileOverlay.setAttribute('aria-hidden', 'true');
            }

            setTimeout(() => {
                this.isAnimating = false;
            }, 300);
        }

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
    }

    // Initialize mobile navigation
    document.addEventListener('DOMContentLoaded', function() {
        window.vendorMobileNavigation = new MobileNavigation();
    });

})();