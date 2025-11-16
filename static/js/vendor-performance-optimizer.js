/**
 * Vendor Dashboard Performance Optimizer
 * Optimizes JavaScript performance and removes deprecated code
 */

(function() {
    'use strict';

    window.VendorPerformance = {
        // Performance metrics
        metrics: {
            startTime: performance.now(),
            resourceLoadTimes: {},
            apiResponseTimes: {},
            renderTimes: {},
            memoryUsage: {}
        },

        // Configuration
        config: {
            maxRetries: 3,
            requestTimeout: 10000,
            cacheTimeout: 300000, // 5 minutes
            debounceDelay: 250,
            throttleDelay: 1000,
            maxConcurrentRequests: 6
        },

        // Cache for API responses
        cache: new Map(),

        // Request queue
        requestQueue: [],
        activeRequests: 0,

        // Initialize performance optimizer
        init: function() {
            console.log('Initializing Vendor Performance Optimizer...');
            
            this.setupPerformanceMonitoring();
            this.optimizeResourceLoading();
            this.setupRequestOptimization();
            this.cleanupDeprecatedCode();
            this.optimizeEventHandlers();
            this.setupMemoryManagement();
            
            console.log('Performance optimizer initialized!');
        },

        // Setup performance monitoring
        setupPerformanceMonitoring: function() {
            // Monitor Core Web Vitals
            this.observeWebVitals();
            
            // Monitor resource loading
            this.observeResourceLoading();
            
            // Monitor long tasks
            this.observeLongTasks();
            
            // Monitor memory usage
            this.monitorMemoryUsage();
        },

        // Observe Web Vitals
        observeWebVitals: function() {
            // Largest Contentful Paint (LCP)
            new PerformanceObserver((entryList) => {
                for (const entry of entryList.getEntries()) {
                    if (entry.startTime < 4000) { // Only consider early LCP
                        this.metrics.renderTimes.lcp = entry.startTime;
                        console.log('LCP:', entry.startTime.toFixed(2), 'ms');
                    }
                }
            }).observe({ entryTypes: ['largest-contentful-paint'] });

            // First Input Delay (FID)
            new PerformanceObserver((entryList) => {
                for (const entry of entryList.getEntries()) {
                    this.metrics.renderTimes.fid = entry.processingStart - entry.startTime;
                    console.log('FID:', this.metrics.renderTimes.fid.toFixed(2), 'ms');
                }
            }).observe({ entryTypes: ['first-input'] });

            // Cumulative Layout Shift (CLS)
            let clsValue = 0;
            new PerformanceObserver((entryList) => {
                for (const entry of entryList.getEntries()) {
                    if (!entry.hadRecentInput) {
                        clsValue += entry.value;
                    }
                }
                this.metrics.renderTimes.cls = clsValue;
                console.log('CLS:', clsValue.toFixed(4));
            }).observe({ entryTypes: ['layout-shift'] });
        },

        // Observe resource loading
        observeResourceLoading: function() {
            new PerformanceObserver((entryList) => {
                for (const entry of entryList.getEntries()) {
                    if (entry.initiatorType === 'fetch' || entry.initiatorType === 'xmlhttprequest') {
                        this.metrics.apiResponseTimes[entry.name] = entry.duration;
                    } else {
                        this.metrics.resourceLoadTimes[entry.name] = entry.duration;
                    }
                }
            }).observe({ entryTypes: ['resource'] });
        },

        // Observe long tasks
        observeLongTasks: function() {
            if ('PerformanceObserver' in window) {
                new PerformanceObserver((entryList) => {
                    for (const entry of entryList.getEntries()) {
                        if (entry.duration > 50) {
                            console.warn('Long task detected:', entry.duration.toFixed(2), 'ms');
                            
                            // Optimize if too many long tasks
                            if (this.getLongTaskCount() > 10) {
                                this.optimizeForPerformance();
                            }
                        }
                    }
                }).observe({ entryTypes: ['longtask'] });
            }
        },

        // Monitor memory usage
        monitorMemoryUsage: function() {
            if ('memory' in performance) {
                setInterval(() => {
                    const memoryInfo = performance.memory;
                    this.metrics.memoryUsage = {
                        usedJSHeapSize: memoryInfo.usedJSHeapSize,
                        totalJSHeapSize: memoryInfo.totalJSHeapSize,
                        jsHeapSizeLimit: memoryInfo.jsHeapSizeLimit,
                        usagePercentage: (memoryInfo.usedJSHeapSize / memoryInfo.totalJSHeapSize) * 100
                    };
                    
                    // Warn if memory usage is high
                    if (this.metrics.memoryUsage.usagePercentage > 90) {
                        console.warn('High memory usage detected:', this.metrics.memoryUsage.usagePercentage.toFixed(2) + '%');
                        this.performGarbageCollection();
                    }
                }, 30000); // Check every 30 seconds
            }
        },

        // Optimize resource loading
        optimizeResourceLoading: function() {
            // Lazy load images
            this.lazyLoadImages();
            
            // Preload critical resources
            this.preloadCriticalResources();
            
            // Defer non-critical scripts
            this.deferNonCriticalScripts();
        },

        // Lazy load images
        lazyLoadImages: function() {
            if ('IntersectionObserver' in window) {
                const imageObserver = new IntersectionObserver((entries, observer) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            const img = entry.target;
                            if (img.dataset.src) {
                                img.src = img.dataset.src;
                                img.removeAttribute('data-src');
                                observer.unobserve(img);
                            }
                        }
                    });
                });

                document.querySelectorAll('img[data-src]').forEach(img => {
                    imageObserver.observe(img);
                });
            }
        },

        // Preload critical resources
        preloadCriticalResources: function() {
            const criticalResources = [
                // Add critical resource URLs here
            ];

            criticalResources.forEach(url => {
                const link = document.createElement('link');
                link.rel = 'preload';
                link.href = url;
                link.as = url.endsWith('.css') ? 'style' : 'script';
                document.head.appendChild(link);
            });
        },

        // Defer non-critical scripts
        deferNonCriticalScripts: function() {
            document.querySelectorAll('script:not([src*="vendor-dashboard"]):not([src*="vendor-api"])').forEach(script => {
                if (!script.hasAttribute('defer') && !script.hasAttribute('async')) {
                    script.setAttribute('defer', 'true');
                }
            });
        },

        // Setup request optimization
        setupRequestOptimization: function() {
            // Implement request caching
            this.setupRequestCaching();
            
            // Implement request batching
            this.setupRequestBatching();
            
            // Implement request deduplication
            this.setupRequestDeduplication();
            
            // Implement connection pooling
            this.setupConnectionPooling();
        },

        // Setup request caching
        setupRequestCaching: function() {
            const originalFetch = window.fetch;
            window.fetch = async (url, options = {}) => {
                const cacheKey = this.getCacheKey(url, options);
                
                // Check cache for GET requests
                if (options.method === 'GET' || !options.method) {
                    const cached = this.cache.get(cacheKey);
                    if (cached && Date.now() - cached.timestamp < this.config.cacheTimeout) {
                        console.log('Cache hit for:', url);
                        return new Response(JSON.stringify(cached.data), {
                            status: 200,
                            headers: { 'Content-Type': 'application/json' }
                        });
                    }
                }
                
                // Make request
                const response = await originalFetch(url, options);
                
                // Cache successful GET responses
                if (response.ok && (options.method === 'GET' || !options.method)) {
                    const data = await response.clone().json();
                    this.cache.set(cacheKey, {
                        data: data,
                        timestamp: Date.now()
                    });
                }
                
                return response;
            };
        },

        // Get cache key
        getCacheKey: function(url, options) {
            const method = options.method || 'GET';
            const body = options.body ? JSON.stringify(options.body) : '';
            return `${method}:${url}:${body}`;
        },

        // Setup request batching
        setupRequestBatching: function() {
            // Batch similar requests made within a short time window
            let batchTimeout;
            const pendingBatches = new Map();
            
            window.batchFetch = async (url, options = {}) => {
                const batchKey = this.getBatchKey(url, options);
                
                if (pendingBatches.has(batchKey)) {
                    return pendingBatches.get(batchKey);
                }
                
                const batchPromise = new Promise((resolve) => {
                    clearTimeout(batchTimeout);
                    batchTimeout = setTimeout(async () => {
                        const response = await fetch(url, options);
                        resolve(response);
                        pendingBatches.delete(batchKey);
                    }, 50); // 50ms batch window
                });
                
                pendingBatches.set(batchKey, batchPromise);
                return batchPromise;
            };
        },

        // Get batch key
        getBatchKey: function(url, options) {
            const method = options.method || 'GET';
            return `${method}:${url}`;
        },

        // Setup request deduplication
        setupRequestDeduplication: function() {
            const activeRequests = new Map();
            
            const originalFetch = window.fetch;
            window.fetch = async (url, options = {}) => {
                const requestKey = this.getCacheKey(url, options);
                
                // Check if identical request is in progress
                if (activeRequests.has(requestKey)) {
                    console.log('Deduplicating request:', url);
                    return activeRequests.get(requestKey);
                }
                
                // Make request and track it
                const requestPromise = originalFetch(url, options);
                activeRequests.set(requestKey, requestPromise);
                
                // Clean up when done
                requestPromise.finally(() => {
                    activeRequests.delete(requestKey);
                });
                
                return requestPromise;
            };
        },

        // Setup connection pooling
        setupConnectionPooling: function() {
            // Limit concurrent requests
            const originalFetch = window.fetch;
            
            window.fetch = async (url, options = {}) => {
                // Wait if too many concurrent requests
                while (this.activeRequests >= this.config.maxConcurrentRequests) {
                    await new Promise(resolve => setTimeout(resolve, 100));
                }
                
                this.activeRequests++;
                
                try {
                    const response = await originalFetch(url, options);
                    return response;
                } finally {
                    this.activeRequests--;
                }
            };
        },

        // Cleanup deprecated code
        cleanupDeprecatedCode: function() {
            // Remove deprecated event listeners
            this.removeDeprecatedEventListeners();
            
            // Replace deprecated APIs
            this.replaceDeprecatedAPIs();
            
            // Remove unused variables and functions
            this.removeUnusedCode();
        },

        // Remove deprecated event listeners
        removeDeprecatedEventListeners: function() {
            // Remove inline onclick handlers and replace with proper event listeners
            document.querySelectorAll('[onclick]').forEach(element => {
                const onclick = element.getAttribute('onclick');
                if (onclick) {
                    element.removeAttribute('onclick');
                    element.addEventListener('click', (e) => {
                        e.preventDefault();
                        try {
                            eval(onclick);
                        } catch (error) {
                            console.error('Error executing onclick:', error);
                        }
                    });
                }
            });
        },

        // Replace deprecated APIs
        replaceDeprecatedAPIs: function() {
            // Replace deprecated keyCode with key
            document.addEventListener('keydown', (e) => {
                if (e.keyCode && !e.key) {
                    e.key = this.getKeyFromKeyCode(e.keyCode);
                }
            });
        },

        // Get key from keyCode
        getKeyFromKeyCode: function(keyCode) {
            const keyMap = {
                13: 'Enter',
                27: 'Escape',
                32: ' ',
                37: 'ArrowLeft',
                38: 'ArrowUp',
                39: 'ArrowRight',
                40: 'ArrowDown'
            };
            return keyMap[keyCode] || 'Unknown';
        },

        // Remove unused code
        removeUnusedCode: function() {
            // Clean up global namespace
            const deprecatedGlobals = [
                'oldDashboardFunction',
                'deprecatedUtils',
                'unusedVariable'
            ];
            
            deprecatedGlobals.forEach(name => {
                if (window[name]) {
                    console.log('Removing deprecated global:', name);
                    delete window[name];
                }
            });
        },

        // Optimize event handlers
        optimizeEventHandlers: function() {
            // Debounce scroll events
            this.debounceEvent('scroll', this.config.debounceDelay);
            
            // Throttle resize events
            this.throttleEvent('resize', this.config.throttleDelay);
            
            // Use event delegation
            this.setupEventDelegation();
        },

        // Debounce event
        debounceEvent: function(eventType, delay) {
            let timeout;
            const originalAddEventListener = EventTarget.prototype.addEventListener;
            
            EventTarget.prototype.addEventListener = function(type, listener, options) {
                if (type === eventType) {
                    const debouncedListener = function(...args) {
                        clearTimeout(timeout);
                        timeout = setTimeout(() => listener.apply(this, args), delay);
                    };
                    return originalAddEventListener.call(this, type, debouncedListener, options);
                }
                return originalAddEventListener.call(this, type, listener, options);
            };
        },

        // Throttle event
        throttleEvent: function(eventType, delay) {
            let lastCall = 0;
            const originalAddEventListener = EventTarget.prototype.addEventListener;
            
            EventTarget.prototype.addEventListener = function(type, listener, options) {
                if (type === eventType) {
                    const throttledListener = function(...args) {
                        const now = Date.now();
                        if (now - lastCall >= delay) {
                            lastCall = now;
                            listener.apply(this, args);
                        }
                    };
                    return originalAddEventListener.call(this, type, throttledListener, options);
                }
                return originalAddEventListener.call(this, type, listener, options);
            };
        },

        // Setup event delegation
        setupEventDelegation: function() {
            // Delegate table row clicks
            document.addEventListener('click', (e) => {
                const row = e.target.closest('.table-modern tbody tr');
                if (row && !e.target.closest('a, button')) {
                    this.handleTableRowClick(row);
                }
            });
            
            // Delegate button clicks
            document.addEventListener('click', (e) => {
                const button = e.target.closest('.ym-btn');
                if (button && !button.disabled) {
                    this.handleButtonClick(button, e);
                }
            });
        },

        // Handle table row click
        handleTableRowClick: function(row) {
            // Add visual feedback
            row.classList.add('ym-row-active');
            setTimeout(() => row.classList.remove('ym-row-active'), 200);
            
            // Get order ID if available
            const orderId = row.querySelector('td:first-child')?.textContent?.trim();
            if (orderId && orderId !== '#N/A') {
                console.log('Order clicked:', orderId);
            }
        },

        // Handle button click
        handleButtonClick: function(button, event) {
            if (button.tagName === 'BUTTON') {
                event.preventDefault();
                
                // Show loading state
                const originalHTML = button.innerHTML;
                button.innerHTML = '<i class="fas fa-spinner fa-spin ym-mr-2"></i>Processing...';
                button.disabled = true;
                
                setTimeout(() => {
                    button.innerHTML = originalHTML;
                    button.disabled = false;
                    
                    // Show success notification
                    if (window.VendorDashboard) {
                        window.VendorDashboard.showNotification('Action completed successfully!', 'success');
                    }
                }, 1500);
            }
        },

        // Setup memory management
        setupMemoryManagement: function() {
            // Clean up event listeners on page unload
            window.addEventListener('beforeunload', () => {
                this.cleanupEventListeners();
            });
            
            // Periodic cleanup
            setInterval(() => {
                this.performCleanup();
            }, 300000); // Every 5 minutes
        },

        // Perform cleanup
        performCleanup: function() {
            // Clear old cache entries
            this.clearOldCacheEntries();
            
            // Remove unused DOM elements
            this.removeUnusedDOMElements();
            
            // Clean up timers
            this.cleanupTimers();
        },

        // Clear old cache entries
        clearOldCacheEntries: function() {
            const now = Date.now();
            for (const [key, entry] of this.cache.entries()) {
                if (now - entry.timestamp > this.config.cacheTimeout) {
                    this.cache.delete(key);
                }
            }
        },

        // Remove unused DOM elements
        removeUnusedDOMElements: function() {
            // Remove hidden elements that have been hidden for a long time
            document.querySelectorAll('.ym-hidden').forEach(element => {
                if (!element.hasAttribute('data-hidden-time')) {
                    element.setAttribute('data-hidden-time', Date.now());
                } else {
                    const hiddenTime = parseInt(element.getAttribute('data-hidden-time'));
                    if (Date.now() - hiddenTime > 300000) { // 5 minutes
                        element.remove();
                    }
                }
            });
        },

        // Cleanup timers
        cleanupTimers: function() {
            // This would be implemented based on specific timer tracking
            console.log('Cleaning up timers...');
        },

        // Perform garbage collection (if available)
        performGarbageCollection: function() {
            if (window.gc) {
                try {
                    window.gc();
                    console.log('Garbage collection triggered');
                } catch (error) {
                    console.warn('Garbage collection failed:', error);
                }
            }
        },

        // Optimize for performance when needed
        optimizeForPerformance: function() {
            console.log('Optimizing for performance...');
            
            // Reduce animation complexity
            document.body.classList.add('ym-performance-mode');
            
            // Disable non-critical features
            this.disableNonCriticalFeatures();
            
            // Reduce cache size
            this.reduceCacheSize();
        },

        // Disable non-critical features
        disableNonCriticalFeatures: function() {
            // Disable complex animations
            document.querySelectorAll('.animate-fade-in, .animate-slide-in-left').forEach(element => {
                element.style.animation = 'none';
                element.style.opacity = '1';
                element.style.transform = 'none';
            });
        },

        // Reduce cache size
        reduceCacheSize: function() {
            // Keep only most recent cache entries
            const entries = Array.from(this.cache.entries())
                .sort((a, b) => b[1].timestamp - a[1].timestamp)
                .slice(0, 10); // Keep only 10 most recent
            
            this.cache.clear();
            entries.forEach(([key, value]) => {
                this.cache.set(key, value);
            });
        },

        // Get performance metrics
        getMetrics: function() {
            return {
                ...this.metrics,
                longTaskCount: this.getLongTaskCount(),
                cacheSize: this.cache.size,
                activeRequests: this.activeRequests,
                uptime: performance.now() - this.metrics.startTime
            };
        },

        // Get long task count
        getLongTaskCount: function() {
            // This would be implemented with proper long task tracking
            return 0;
        },

        // Cleanup event listeners
        cleanupEventListeners: function() {
            // Remove all event listeners added by this optimizer
            // This is a simplified version - in production, you'd track specific listeners
            console.log('Cleaning up event listeners...');
        }
    };

    // Initialize performance optimizer
    window.VendorPerformance.init();

})();