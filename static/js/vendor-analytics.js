/**
 * Vendor Analytics System
 * Provides comprehensive analytics tracking for vendor portal
 */
(function() {
    'use strict';
    
    // Wait for VendorSystem to be available
    function initAnalytics() {
        if (!window.VendorSystem) {
            setTimeout(initAnalytics, 100);
            return;
        }
        
        // Add analytics to VendorSystem
        window.VendorSystem.analytics = {
            // Track events
            track: function(eventName, eventData = {}) {
                const event = {
                    name: eventName,
                    data: eventData,
                    timestamp: new Date().toISOString(),
                    page: window.location.pathname,
                    userAgent: navigator.userAgent,
                    sessionId: sessionStorage.getItem('vendor_session_id') || generateSessionId()
                };
                
                console.log('Analytics Event:', event);
                
                // Store in localStorage for batch processing
                const events = JSON.parse(localStorage.getItem('vendor_analytics_events') || '[]');
                events.push(event);
                localStorage.setItem('vendor_analytics_events', JSON.stringify(events));
                
                // Send to server if configured
                if (window.VENDOR_SYSTEM_CONFIG && window.VENDOR_SYSTEM_CONFIG.analyticsEndpoint) {
                    sendAnalyticsEvent(event);
                }
            },
            
            // Get stored events
            getEvents: function() {
                return JSON.parse(localStorage.getItem('vendor_analytics_events') || '[]');
            },
            
            // Clear stored events
            clearEvents: function() {
                localStorage.removeItem('vendor_analytics_events');
            },
            
            // Track page views
            trackPageView: function(pageName, additionalData = {}) {
                this.track('page_view', {
                    page_name: pageName,
                    referrer: document.referrer,
                    ...additionalData
                });
            },
            
            // Track user interactions
            trackInteraction: function(element, action, additionalData = {}) {
                this.track('user_interaction', {
                    element: element.tagName + (element.id ? '#' + element.id : ''),
                    element_text: element.textContent?.trim().substring(0, 50),
                    action: action,
                    ...additionalData
                });
            },
            
            // Track errors
            trackError: function(error, context = {}) {
                this.track('error', {
                    error_message: error.message || error,
                    error_stack: error.stack,
                    context: context
                });
            }
        };
        
        // Generate session ID
        function generateSessionId() {
            const sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            sessionStorage.setItem('vendor_session_id', sessionId);
            return sessionId;
        }
        
        // Send analytics to server
        function sendAnalyticsEvent(event) {
            if (navigator.sendBeacon) {
                navigator.sendBeacon(window.VENDOR_SYSTEM_CONFIG.analyticsEndpoint, JSON.stringify(event));
            } else {
                // Fallback for older browsers
                const xhr = new XMLHttpRequest();
                xhr.open('POST', window.VENDOR_SYSTEM_CONFIG.analyticsEndpoint, true);
                xhr.setRequestHeader('Content-Type', 'application/json');
                xhr.send(JSON.stringify(event));
            }
        }
        
        // Auto-track common interactions
        document.addEventListener('DOMContentLoaded', function() {
            // Track clicks on buttons and links
            document.addEventListener('click', function(e) {
                const target = e.target.closest('a, button, .btn, [role="button"]');
                if (target) {
                    window.VendorSystem.analytics.trackInteraction(target, 'click', {
                        href: target.href,
                        button_text: target.textContent?.trim().substring(0, 30)
                    });
                }
            });
            
            // Track form submissions
            document.addEventListener('submit', function(e) {
                const form = e.target.closest('form');
                if (form) {
                    window.VendorSystem.analytics.track('form_submit', {
                        form_id: form.id,
                        form_action: form.action,
                        form_method: form.method
                    });
                }
            });
            
            // Track page view
            window.VendorSystem.analytics.trackPageView(document.title);
        });
        
        // Track JavaScript errors
        window.addEventListener('error', function(e) {
            window.VendorSystem.analytics.trackError(e.error || e.message, {
                filename: e.filename,
                lineno: e.lineno,
                colno: e.colno
            });
        });
        
        console.log('Vendor Analytics System initialized');
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAnalytics);
    } else {
        initAnalytics();
    }
})();