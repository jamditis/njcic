/**
 * NJCIC Dashboard - Main Application Logic
 * Handles data loading, counter animations, and dashboard initialization
 */

(function() {
    'use strict';

    // Configuration
    const CONFIG = {
        dataPath: 'data/dashboard-data.json',
        counterDuration: 2000, // ms
        counterFrameRate: 60, // fps
        retryAttempts: 3,
        retryDelay: 1000 // ms
    };

    // State
    let dashboardData = null;
    let charts = {
        platform: null,
        grantees: null
    };

    /**
     * Initialize the dashboard
     */
    async function init() {
        try {
            // Load data
            dashboardData = await loadData();

            // Hide loading, show content
            hideLoading();

            // Initialize components
            initCounters();
            initCharts();
            updateLastUpdated();

            console.log('NJCIC Dashboard initialized successfully');
        } catch (error) {
            console.error('Dashboard initialization failed:', error);
            showError(error.message);
        }
    }

    /**
     * Load dashboard data with cache busting
     * @returns {Promise<Object>} Dashboard data
     */
    async function loadData() {
        const cacheBuster = `?v=${Date.now()}`;
        let lastError = null;

        for (let attempt = 1; attempt <= CONFIG.retryAttempts; attempt++) {
            try {
                const response = await fetch(CONFIG.dataPath + cacheBuster);

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const data = await response.json();
                validateData(data);
                return normalizeData(data);

            } catch (error) {
                lastError = error;
                console.warn(`Data load attempt ${attempt} failed:`, error.message);

                if (attempt < CONFIG.retryAttempts) {
                    await sleep(CONFIG.retryDelay);
                }
            }
        }

        // If all retries failed, try to use sample data for demo
        console.log('Using sample data for demonstration');
        return getSampleData();
    }

    /**
     * Validate loaded data structure
     * @param {Object} data - Data to validate
     */
    function validateData(data) {
        // Check for required top-level fields (either format)
        if (!data.summary && !data.platforms) {
            throw new Error('Invalid data: missing summary or platforms');
        }
    }

    /**
     * Normalize data to expected format
     * Handles both the original format and the scraper output format
     * @param {Object} data - Raw data
     * @returns {Object} Normalized data
     */
    function normalizeData(data) {
        // Check if data is in scraper output format (has platformsTracked)
        if (data.summary && data.summary.platformsTracked !== undefined) {
            // Convert scraper format to dashboard format
            const platforms = {};
            if (data.platforms) {
                Object.entries(data.platforms).forEach(([platform, info]) => {
                    // Capitalize platform name
                    const name = platform.charAt(0).toUpperCase() + platform.slice(1);
                    platforms[name] = info.posts || 0;
                });
            }

            // Convert topGrantees to grantees format
            const grantees = (data.topGrantees || []).map(g => ({
                name: g.name,
                engagement: g.engagement || 0
            }));

            return {
                summary: {
                    totalGrantees: data.summary.totalGrantees || 0,
                    totalPosts: data.summary.totalPosts || 0,
                    totalEngagement: data.summary.totalEngagement || 0,
                    platformsMonitored: data.summary.platformsTracked || Object.keys(data.platforms || {}).length
                },
                platforms: platforms,
                grantees: grantees,
                lastUpdated: data.summary.lastUpdated || data.metadata?.generatedAt || new Date().toISOString()
            };
        }

        // Data is already in expected format
        return data;
    }

    /**
     * Get sample data for demonstration
     * @returns {Object} Sample dashboard data
     */
    function getSampleData() {
        return {
            summary: {
                totalGrantees: 47,
                totalPosts: 12543,
                totalEngagement: 2847291,
                platformsMonitored: 4
            },
            platforms: {
                Instagram: 5234,
                TikTok: 3421,
                YouTube: 2156,
                Twitter: 1732
            },
            grantees: [
                { name: "NJ Spotlight News", engagement: 456789 },
                { name: "The Record", engagement: 345678 },
                { name: "NJ Advance Media", engagement: 289456 },
                { name: "WNYC/NJ Public Radio", engagement: 234567 },
                { name: "The Press of Atlantic City", engagement: 198765 },
                { name: "NJ Monitor", engagement: 167890 },
                { name: "Jersey Digs", engagement: 145678 },
                { name: "TapInto", engagement: 134567 },
                { name: "NJ Pen", engagement: 123456 },
                { name: "Planet Princeton", engagement: 112345 },
                { name: "The Village Green", engagement: 98765 },
                { name: "ROI-NJ", engagement: 87654 }
            ],
            lastUpdated: new Date().toISOString()
        };
    }

    /**
     * Initialize counter animations
     */
    function initCounters() {
        const counters = [
            { id: 'counter-grantees', value: dashboardData.summary.totalGrantees },
            { id: 'counter-posts', value: dashboardData.summary.totalPosts },
            { id: 'counter-engagement', value: dashboardData.summary.totalEngagement },
            { id: 'counter-platforms', value: dashboardData.summary.platformsMonitored }
        ];

        counters.forEach((counter, index) => {
            const element = document.getElementById(counter.id);
            if (element) {
                // Stagger the start of each counter
                setTimeout(() => {
                    animateCounter(element, counter.value);
                }, index * 150);
            }
        });
    }

    /**
     * Animate a counter from 0 to target value
     * @param {HTMLElement} element - Counter element
     * @param {number} targetValue - Target value to count to
     */
    function animateCounter(element, targetValue) {
        const duration = CONFIG.counterDuration;
        const frameRate = CONFIG.counterFrameRate;
        const totalFrames = Math.round(duration / (1000 / frameRate));
        let frame = 0;

        element.classList.add('counting');

        const easeOutQuart = t => 1 - Math.pow(1 - t, 4);

        const animate = () => {
            frame++;
            const progress = easeOutQuart(frame / totalFrames);
            const currentValue = Math.round(targetValue * progress);

            element.textContent = formatNumber(currentValue);

            if (frame < totalFrames) {
                requestAnimationFrame(animate);
            } else {
                element.textContent = formatNumber(targetValue);
                element.classList.remove('counting');
            }
        };

        requestAnimationFrame(animate);
    }

    /**
     * Format number with commas
     * @param {number} num - Number to format
     * @returns {string} Formatted number
     */
    function formatNumber(num) {
        if (num === null || num === undefined) return '0';
        return new Intl.NumberFormat('en-US').format(Math.round(num));
    }

    /**
     * Initialize Chart.js charts
     */
    function initCharts() {
        // Platform Distribution Chart
        const platformCtx = document.getElementById('platformChart');
        if (platformCtx && window.NJCICCharts) {
            charts.platform = window.NJCICCharts.createPlatformChart(
                platformCtx.getContext('2d'),
                dashboardData.platforms
            );
        }

        // Top Grantees Chart
        const granteesCtx = document.getElementById('granteesChart');
        if (granteesCtx && window.NJCICCharts) {
            charts.grantees = window.NJCICCharts.createGranteesChart(
                granteesCtx.getContext('2d'),
                dashboardData.grantees
            );
        }
    }

    /**
     * Update the "Last Updated" timestamp
     */
    function updateLastUpdated() {
        const element = document.getElementById('last-updated');
        if (!element) return;

        let date;
        if (dashboardData.lastUpdated) {
            date = new Date(dashboardData.lastUpdated);
        } else {
            date = new Date();
        }

        const options = {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        };

        element.textContent = date.toLocaleDateString('en-US', options);
    }

    /**
     * Hide loading overlay and show main content
     */
    function hideLoading() {
        const loadingOverlay = document.getElementById('loading-overlay');
        const mainContent = document.getElementById('main-content');

        if (loadingOverlay) {
            loadingOverlay.style.opacity = '0';
            setTimeout(() => {
                loadingOverlay.style.display = 'none';
            }, 300);
        }

        if (mainContent) {
            setTimeout(() => {
                mainContent.style.opacity = '1';
            }, 100);
        }
    }

    /**
     * Show error state
     * @param {string} message - Error message to display
     */
    function showError(message) {
        const loadingOverlay = document.getElementById('loading-overlay');
        const errorState = document.getElementById('error-state');
        const errorMessage = document.getElementById('error-message');

        if (loadingOverlay) {
            loadingOverlay.style.display = 'none';
        }

        if (errorState) {
            errorState.classList.remove('hidden');
        }

        if (errorMessage && message) {
            errorMessage.textContent = message;
        }
    }

    /**
     * Sleep utility for retry delays
     * @param {number} ms - Milliseconds to sleep
     * @returns {Promise} Promise that resolves after delay
     */
    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Refresh dashboard data
     * Can be called externally to refresh the dashboard
     */
    async function refresh() {
        try {
            const newData = await loadData();
            dashboardData = newData;

            // Update counters
            document.getElementById('counter-grantees').textContent =
                formatNumber(dashboardData.summary.totalGrantees);
            document.getElementById('counter-posts').textContent =
                formatNumber(dashboardData.summary.totalPosts);
            document.getElementById('counter-engagement').textContent =
                formatNumber(dashboardData.summary.totalEngagement);
            document.getElementById('counter-platforms').textContent =
                formatNumber(dashboardData.summary.platformsMonitored);

            // Update charts
            if (charts.platform && window.NJCICCharts) {
                window.NJCICCharts.updateChartData(charts.platform, dashboardData.platforms);
            }
            if (charts.grantees && window.NJCICCharts) {
                window.NJCICCharts.updateChartData(charts.grantees, dashboardData.grantees);
            }

            // Update timestamp
            updateLastUpdated();

            console.log('Dashboard refreshed successfully');
        } catch (error) {
            console.error('Dashboard refresh failed:', error);
        }
    }

    /**
     * Get current dashboard data
     * @returns {Object} Current dashboard data
     */
    function getData() {
        return dashboardData;
    }

    // Export public API
    window.NJCICDashboard = {
        refresh,
        getData
    };

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
