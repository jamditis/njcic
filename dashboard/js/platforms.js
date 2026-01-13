/**
 * NJCIC Dashboard - Platform Analytics
 * Handles platform-specific data loading and visualization
 */

(function() {
    'use strict';

    // Configuration
    const CONFIG = {
        platformAnalyticsPath: 'data/platform-analytics.json',
        dashboardDataPath: 'data/dashboard-data.json',
        retryAttempts: 3,
        retryDelay: 1000
    };

    // Platform metadata for platforms not yet in the data
    const PLATFORM_METADATA = {
        tiktok: { name: 'TikTok', color: '#000000' },
        bluesky: { name: 'Bluesky', color: '#0085FF' },
        youtube: { name: 'YouTube', color: '#FF0000' },
        twitter: { name: 'Twitter/X', color: '#1DA1F2' },
        instagram: { name: 'Instagram', color: '#E4405F' },
        facebook: { name: 'Facebook', color: '#1877F2' },
        linkedin: { name: 'LinkedIn', color: '#0A66C2' },
        threads: { name: 'Threads', color: '#000000' }
    };

    // State
    let platformData = null;
    let dashboardData = null;
    let charts = {};

    // Platform Icons (SVG paths)
    const PLATFORM_ICONS = {
        tiktok: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-6 h-6"><path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5 20.1a6.34 6.34 0 0 0 10.86-4.43v-7a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.1z"/></svg>`,
        bluesky: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-6 h-6"><path d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zm5.5 14.5c-1.5 1.5-4 1.5-5.5 0-1.5 1.5-4 1.5-5.5 0-1-1-1-2.5 0-3.5l5.5-5.5 5.5 5.5c1 1 1 2.5 0 3.5z"/></svg>`,
        youtube: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-6 h-6"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>`,
        twitter: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-6 h-6"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>`,
        instagram: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-6 h-6"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 1 0 0 12.324 6.162 6.162 0 0 0 0-12.324zM12 16a4 4 0 1 1 0-8 4 4 0 0 1 0 8zm6.406-11.845a1.44 1.44 0 1 0 0 2.881 1.44 1.44 0 0 0 0-2.881z"/></svg>`,
        facebook: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-6 h-6"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>`,
        linkedin: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-6 h-6"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>`,
        threads: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-6 h-6"><path d="M12.186 24h-.007c-3.581-.024-6.334-1.205-8.184-3.509C2.35 18.44 1.5 15.586 1.472 12.01v-.017c.03-3.579.879-6.43 2.525-8.482C5.845 1.205 8.6.024 12.18 0h.014c2.746.02 5.043.725 6.826 2.098 1.677 1.29 2.858 3.13 3.509 5.467l-2.04.569c-1.104-3.96-3.898-5.984-8.304-6.015-2.91.022-5.11.936-6.54 2.717C4.307 6.504 3.616 8.914 3.589 12c.027 3.086.718 5.496 2.057 7.164 1.43 1.783 3.631 2.698 6.54 2.717 2.623-.02 4.358-.631 5.8-2.045 1.647-1.613 1.618-3.593 1.09-4.798-.31-.71-.873-1.3-1.634-1.75-.192 1.352-.622 2.446-1.284 3.272-.886 1.102-2.14 1.704-3.73 1.79-1.202.065-2.361-.218-3.259-.801-1.063-.689-1.685-1.74-1.752-2.96-.065-1.182.408-2.256 1.332-3.023.88-.73 2.115-1.165 3.476-1.225 1.104-.049 2.146.064 3.116.313.019-.894-.09-1.648-.333-2.29-.36-.957-1.023-1.463-2.088-1.592-.725-.088-1.476.07-1.853.267l-.949-1.77c.654-.352 1.733-.612 2.936-.49 1.753.179 3.049 1.03 3.64 2.395.367.85.542 1.882.535 3.065l.001.133c.903.386 1.64.914 2.19 1.57.834.994 1.267 2.263 1.254 3.67-.018 1.893-.754 3.538-2.13 4.762-1.674 1.49-4.058 2.263-7.085 2.298zm-.21-8.39c-1.71.076-2.784.787-2.741 1.814.043.99 1.088 1.574 2.576 1.492 1.134-.063 2.007-.473 2.596-1.218.398-.503.66-1.161.787-1.973-.995-.203-2.088-.266-3.218-.115z"/></svg>`
    };

    // Insight Icons
    const INSIGHT_ICONS = {
        'chart-bar': `<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>`,
        'users': `<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"/></svg>`,
        'trophy': `<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/></svg>`,
        'trending-up': `<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/></svg>`,
        'lightbulb': `<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/></svg>`,
        'zap': `<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>`
    };

    /**
     * Normalize platform data to a consistent format
     */
    function normalizePlatformData(rawData) {
        const normalized = {
            platforms: {},
            comparison: rawData.comparison || null,
            generated_at: rawData.generated_at || new Date().toISOString()
        };

        // Process each platform from the raw data
        if (rawData.platforms) {
            Object.entries(rawData.platforms).forEach(([key, platform]) => {
                normalized.platforms[key] = {
                    name: PLATFORM_METADATA[key]?.name || key.charAt(0).toUpperCase() + key.slice(1),
                    color: platform.color || PLATFORM_METADATA[key]?.color || '#6B7280',
                    posts: platform.total_posts || platform.posts || 0,
                    engagement: platform.total_engagement || platform.engagement || 0,
                    grantees: platform.grantees || 0,
                    avgEngagementPerPost: platform.avg_engagement_per_post || platform.avgEngagementPerPost || 0,
                    avgPostsPerGrantee: platform.avg_posts_per_grantee || 0,
                    followers: platform.total_followers || 0,
                    contentTypes: platform.content_types || null,
                    topGrantees: platform.top_grantees || platform.topGrantees || []
                };
            });
        }

        // Add placeholder platforms that aren't in the data yet
        Object.keys(PLATFORM_METADATA).forEach(key => {
            if (!normalized.platforms[key]) {
                normalized.platforms[key] = {
                    name: PLATFORM_METADATA[key].name,
                    color: PLATFORM_METADATA[key].color,
                    posts: 0,
                    engagement: 0,
                    grantees: 0,
                    avgEngagementPerPost: 0,
                    avgPostsPerGrantee: 0,
                    followers: 0,
                    contentTypes: null,
                    topGrantees: []
                };
            }
        });

        return normalized;
    }

    /**
     * Generate insights from the data
     */
    function generateInsights(data) {
        const insights = [];
        const platforms = Object.entries(data.platforms).filter(([_, p]) => p.engagement > 0);

        if (platforms.length === 0) return insights;

        // Total engagement
        const totalEngagement = platforms.reduce((sum, [_, p]) => sum + p.engagement, 0);

        // Find dominant platform
        const [topPlatformKey, topPlatform] = platforms.sort((a, b) => b[1].engagement - a[1].engagement)[0];
        const dominancePercent = Math.round((topPlatform.engagement / totalEngagement) * 100);

        insights.push({
            type: 'dominance',
            icon: 'chart-bar',
            message: `${topPlatform.name} drives ${dominancePercent}% of total engagement`,
            value: dominancePercent,
            platform: topPlatformKey
        });

        // Active grantees on each platform
        platforms.forEach(([key, platform]) => {
            if (platform.grantees > 0) {
                insights.push({
                    type: 'adoption',
                    icon: 'users',
                    message: `${platform.grantees} grantees are active on ${platform.name}`,
                    value: platform.grantees,
                    platform: key
                });
            }
        });

        // Top performer on each platform
        platforms.forEach(([key, platform]) => {
            if (platform.topGrantees && platform.topGrantees.length > 0) {
                const topGrantee = platform.topGrantees[0];
                insights.push({
                    type: 'leader',
                    icon: 'trophy',
                    message: `${topGrantee.name} leads ${platform.name} with ${formatAbbreviated(topGrantee.engagement)} engagement`,
                    value: topGrantee.engagement,
                    platform: key
                });
            }
        });

        // Efficiency insight
        const [mostEfficientKey, mostEfficient] = platforms.sort((a, b) => b[1].avgEngagementPerPost - a[1].avgEngagementPerPost)[0];
        if (mostEfficient.avgEngagementPerPost > 0) {
            insights.push({
                type: 'efficiency',
                icon: 'zap',
                message: `${mostEfficient.name} averages ${formatNumber(Math.round(mostEfficient.avgEngagementPerPost))} engagements per post`,
                value: mostEfficient.avgEngagementPerPost,
                platform: mostEfficientKey
            });
        }

        return insights.slice(0, 6); // Limit to 6 insights
    }

    /**
     * Generate grantee matrix from platform data
     */
    function generateGranteeMatrix(data) {
        const granteeMap = new Map();

        // Collect all grantees from all platforms
        Object.entries(data.platforms).forEach(([platformKey, platform]) => {
            if (platform.topGrantees) {
                platform.topGrantees.forEach(grantee => {
                    if (!granteeMap.has(grantee.name)) {
                        granteeMap.set(grantee.name, {
                            name: grantee.name,
                            platforms: {}
                        });
                    }
                    granteeMap.get(grantee.name).platforms[platformKey] = true;
                });
            }
        });

        // Convert to array and fill in missing platforms
        const platformKeys = Object.keys(PLATFORM_METADATA);
        return Array.from(granteeMap.values()).map(grantee => {
            platformKeys.forEach(key => {
                if (grantee.platforms[key] === undefined) {
                    grantee.platforms[key] = false;
                }
            });
            return grantee;
        });
    }

    /**
     * Initialize the platform analytics page
     */
    async function init() {
        try {
            // Load data
            const rawPlatformData = await loadData(CONFIG.platformAnalyticsPath);
            dashboardData = await loadData(CONFIG.dashboardDataPath).catch(() => null);

            // Normalize the data
            platformData = normalizePlatformData(rawPlatformData);

            // Generate derived data
            platformData.insights = generateInsights(platformData);
            platformData.granteeMatrix = generateGranteeMatrix(platformData);

            // Hide loading, show content
            hideLoading();

            // Initialize components
            renderPlatformOverviewCards();
            renderPlatformDetails();
            renderCrossComparisonCharts();
            renderMetricsTable();
            renderPlatformAdoption();
            renderInsights();
            updateLastUpdated();

            console.log('Platform Analytics initialized successfully');
        } catch (error) {
            console.error('Platform Analytics initialization failed:', error);
            showError(error.message);
        }
    }

    /**
     * Load data with retry logic
     */
    async function loadData(path) {
        const cacheBuster = `?v=${Date.now()}`;
        let lastError = null;

        for (let attempt = 1; attempt <= CONFIG.retryAttempts; attempt++) {
            try {
                const response = await fetch(path + cacheBuster);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return await response.json();
            } catch (error) {
                lastError = error;
                console.warn(`Data load attempt ${attempt} for ${path} failed:`, error.message);
                if (attempt < CONFIG.retryAttempts) {
                    await sleep(CONFIG.retryDelay);
                }
            }
        }
        throw lastError;
    }

    /**
     * Render platform overview cards
     */
    function renderPlatformOverviewCards() {
        const container = document.getElementById('platform-overview-cards');
        if (!container || !platformData?.platforms) return;

        // Order platforms: active first, then by engagement
        const platformsArray = Object.entries(platformData.platforms)
            .sort((a, b) => {
                const aActive = a[1].posts > 0 || a[1].engagement > 0;
                const bActive = b[1].posts > 0 || b[1].engagement > 0;
                if (aActive && !bActive) return -1;
                if (!aActive && bActive) return 1;
                return b[1].engagement - a[1].engagement;
            });

        container.innerHTML = platformsArray.map(([key, platform]) => {
            const hasData = platform.posts > 0 || platform.engagement > 0;
            const opacity = hasData ? '' : 'opacity-60';

            return `
                <a href="#platform-${key}" class="platform-card bg-white bg-opacity-10 backdrop-blur rounded-xl p-4 text-center cursor-pointer ${opacity}">
                    <div class="platform-icon mx-auto mb-3" style="background-color: ${platform.color}20">
                        <span style="color: ${platform.color}">${PLATFORM_ICONS[key] || ''}</span>
                    </div>
                    <h3 class="text-white font-semibold text-sm mb-2">${platform.name}</h3>
                    <div class="text-xs text-gray-300 space-y-1">
                        <div>${formatNumber(platform.posts)} posts</div>
                        <div>${formatAbbreviated(platform.engagement)} engagement</div>
                        <div>${platform.grantees} grantees</div>
                    </div>
                    ${hasData ? '<div class="mt-2 inline-block px-2 py-0.5 bg-green-500 bg-opacity-20 text-green-300 text-xs rounded-full">Active</div>' : '<div class="mt-2 inline-block px-2 py-0.5 bg-gray-500 bg-opacity-20 text-gray-400 text-xs rounded-full">No data</div>'}
                </a>
            `;
        }).join('');
    }

    /**
     * Render platform detail sections
     */
    function renderPlatformDetails() {
        const container = document.getElementById('platform-details');
        if (!container || !platformData?.platforms) return;

        const platformsWithData = Object.entries(platformData.platforms)
            .filter(([_, p]) => p.posts > 0 || p.engagement > 0);

        if (platformsWithData.length === 0) {
            container.innerHTML = `
                <div class="bg-white rounded-2xl shadow-lg p-8 text-center">
                    <p class="text-gray-500">No platform data available yet. Data will appear once scraping is complete.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = platformsWithData.map(([key, platform]) => `
            <div id="platform-${key}" class="bg-white rounded-2xl shadow-lg overflow-hidden scroll-mt-24">
                <div class="p-6 sm:p-8 border-b border-gray-100" style="border-left: 4px solid ${platform.color}">
                    <div class="flex items-center gap-4 mb-6">
                        <div class="platform-icon" style="background-color: ${platform.color}20">
                            <span style="color: ${platform.color}">${PLATFORM_ICONS[key] || ''}</span>
                        </div>
                        <div>
                            <h3 class="text-xl font-bold text-njcic-dark">${platform.name}</h3>
                            <p class="text-sm text-gray-500">${platform.grantees} grantees active on this platform</p>
                        </div>
                    </div>

                    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
                        <div class="bg-gray-50 rounded-lg p-4 text-center">
                            <div class="text-2xl font-bold text-njcic-dark">${formatNumber(platform.posts)}</div>
                            <div class="text-xs text-gray-500">Total posts</div>
                        </div>
                        <div class="bg-gray-50 rounded-lg p-4 text-center">
                            <div class="text-2xl font-bold text-njcic-dark">${formatAbbreviated(platform.engagement)}</div>
                            <div class="text-xs text-gray-500">Total engagement</div>
                        </div>
                        <div class="bg-gray-50 rounded-lg p-4 text-center">
                            <div class="text-2xl font-bold text-njcic-dark">${platform.grantees}</div>
                            <div class="text-xs text-gray-500">Active grantees</div>
                        </div>
                        <div class="bg-gray-50 rounded-lg p-4 text-center">
                            <div class="text-2xl font-bold text-njcic-dark">${formatNumber(Math.round(platform.avgEngagementPerPost))}</div>
                            <div class="text-xs text-gray-500">Avg per post</div>
                        </div>
                    </div>

                    ${platform.followers > 0 ? `
                        <div class="mb-6 bg-blue-50 rounded-lg p-4 flex items-center gap-3">
                            <svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>
                            </svg>
                            <span class="text-blue-800 font-medium">${formatNumber(platform.followers)} combined followers</span>
                        </div>
                    ` : ''}

                    ${platform.contentTypes ? `
                        <div class="mb-6">
                            <h4 class="text-sm font-semibold text-gray-700 mb-3">Content types</h4>
                            <div class="flex flex-wrap gap-2">
                                ${Object.entries(platform.contentTypes).map(([type, data]) => `
                                    <span class="inline-flex items-center px-3 py-1 rounded-full text-sm bg-gray-100 text-gray-700">
                                        ${type.charAt(0).toUpperCase() + type.slice(1)}: ${data.count} (${data.percentage}%)
                                    </span>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}

                    ${platform.topGrantees && platform.topGrantees.length > 0 ? `
                        <div>
                            <h4 class="text-sm font-semibold text-gray-700 mb-3">Top grantees on ${platform.name}</h4>
                            <div class="space-y-2">
                                ${platform.topGrantees.slice(0, 5).map((g, i) => `
                                    <div class="flex items-center justify-between bg-gray-50 rounded-lg px-4 py-2">
                                        <div class="flex items-center gap-3">
                                            <span class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white" style="background-color: ${platform.color}">${i + 1}</span>
                                            <span class="font-medium text-sm text-gray-800">${truncate(g.name, 30)}</span>
                                        </div>
                                        <div class="text-right">
                                            <span class="font-semibold text-sm" style="color: ${platform.color}">${formatAbbreviated(g.engagement)}</span>
                                            <span class="text-xs text-gray-400 ml-2">${g.posts} posts</span>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}
                </div>
            </div>
        `).join('');
    }

    /**
     * Render cross-platform comparison charts
     */
    function renderCrossComparisonCharts() {
        if (!platformData?.platforms) return;

        const platforms = Object.entries(platformData.platforms)
            .filter(([_, p]) => p.posts > 0 || p.engagement > 0);

        if (platforms.length === 0) return;

        const labels = platforms.map(([_, p]) => p.name);
        const colors = platforms.map(([_, p]) => p.color);
        const engagements = platforms.map(([_, p]) => p.engagement);
        const posts = platforms.map(([_, p]) => p.posts);

        // Engagement Comparison Chart
        const engagementCtx = document.getElementById('engagementComparisonChart');
        if (engagementCtx) {
            charts.engagement = new Chart(engagementCtx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        data: engagements,
                        backgroundColor: colors,
                        borderRadius: 8,
                        maxBarThickness: 60
                    }]
                },
                options: {
                    ...getChartDefaults(),
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: value => formatAbbreviated(value)
                            }
                        }
                    }
                }
            });
        }

        // Posts Comparison Chart
        const postsCtx = document.getElementById('postsComparisonChart');
        if (postsCtx) {
            charts.posts = new Chart(postsCtx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        data: posts,
                        backgroundColor: colors,
                        borderRadius: 8,
                        maxBarThickness: 60
                    }]
                },
                options: {
                    ...getChartDefaults(),
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }

        // Posts vs Engagement Scatter Plot
        const scatterCtx = document.getElementById('postsVsEngagementChart');
        if (scatterCtx) {
            const scatterData = platforms.map(([key, p]) => ({
                x: p.posts,
                y: p.engagement,
                label: p.name,
                color: p.color
            }));

            charts.scatter = new Chart(scatterCtx, {
                type: 'scatter',
                data: {
                    datasets: [{
                        data: scatterData.map(d => ({ x: d.x, y: d.y })),
                        backgroundColor: scatterData.map(d => d.color),
                        pointRadius: 12,
                        pointHoverRadius: 15
                    }]
                },
                options: {
                    ...getChartDefaults(),
                    scales: {
                        x: {
                            title: { display: true, text: 'Posts' },
                            beginAtZero: true
                        },
                        y: {
                            title: { display: true, text: 'Engagement' },
                            beginAtZero: true,
                            ticks: {
                                callback: value => formatAbbreviated(value)
                            }
                        }
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const platform = scatterData[context.dataIndex];
                                    return `${platform.label}: ${context.parsed.x} posts, ${formatNumber(context.parsed.y)} engagement`;
                                }
                            }
                        }
                    }
                }
            });
        }
    }

    /**
     * Render metrics comparison table
     */
    function renderMetricsTable() {
        const tbody = document.getElementById('metrics-table-body');
        if (!tbody || !platformData?.platforms) return;

        const platforms = Object.entries(platformData.platforms)
            .sort((a, b) => b[1].engagement - a[1].engagement);

        tbody.innerHTML = platforms.map(([key, p]) => {
            const rowOpacity = p.posts > 0 || p.engagement > 0 ? '' : 'opacity-50';
            return `
                <tr class="border-b border-gray-100 ${rowOpacity}">
                    <td class="py-3 px-2">
                        <div class="flex items-center gap-2">
                            <span class="w-3 h-3 rounded-full" style="background-color: ${p.color}"></span>
                            <span class="font-medium">${p.name}</span>
                        </div>
                    </td>
                    <td class="text-right py-3 px-2">${formatNumber(p.posts)}</td>
                    <td class="text-right py-3 px-2 font-semibold">${formatAbbreviated(p.engagement)}</td>
                    <td class="text-right py-3 px-2">${p.grantees}</td>
                    <td class="text-right py-3 px-2">${formatNumber(Math.round(p.avgEngagementPerPost))}</td>
                </tr>
            `;
        }).join('');
    }

    /**
     * Render platform adoption charts and matrix
     */
    function renderPlatformAdoption() {
        if (!platformData?.platforms) return;

        // Grantees per Platform Pie Chart
        const pieCtx = document.getElementById('granteesPerPlatformChart');
        const legendContainer = document.getElementById('grantees-platform-legend');

        if (pieCtx) {
            const platforms = Object.entries(platformData.platforms)
                .filter(([_, p]) => p.grantees > 0);
            const labels = platforms.map(([_, p]) => p.name);
            const data = platforms.map(([_, p]) => p.grantees);
            const colors = platforms.map(([_, p]) => p.color);

            charts.granteesPie = new Chart(pieCtx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
                        backgroundColor: colors,
                        borderWidth: 2,
                        borderColor: '#ffffff'
                    }]
                },
                options: {
                    ...getChartDefaults(),
                    cutout: '60%'
                }
            });

            // Custom legend
            if (legendContainer) {
                legendContainer.innerHTML = platforms.map(([_, p], i) => `
                    <div class="flex items-center gap-2 px-3 py-1 bg-gray-50 rounded-full text-sm">
                        <span class="w-3 h-3 rounded-full" style="background-color: ${colors[i]}"></span>
                        <span>${p.name}: ${p.grantees}</span>
                    </div>
                `).join('');
            }
        }

        // Grantee Platform Matrix
        const matrixBody = document.getElementById('grantee-matrix-body');
        if (matrixBody && platformData?.granteeMatrix && platformData.granteeMatrix.length > 0) {
            const platformOrder = ['tiktok', 'bluesky', 'youtube', 'twitter', 'instagram', 'facebook', 'linkedin', 'threads'];
            const platformColors = {
                tiktok: '#000000',
                bluesky: '#0085FF',
                youtube: '#FF0000',
                twitter: '#1DA1F2',
                instagram: '#E4405F',
                facebook: '#1877F2',
                linkedin: '#0A66C2',
                threads: '#000000'
            };

            matrixBody.innerHTML = platformData.granteeMatrix.map(grantee => `
                <tr class="border-b border-gray-50 hover:bg-gray-50">
                    <td class="py-2 px-1 text-xs font-medium text-gray-700 sticky left-0 bg-white max-w-[150px] truncate" title="${grantee.name}">
                        ${truncate(grantee.name, 20)}
                    </td>
                    ${platformOrder.map(platform => {
                        const isActive = grantee.platforms[platform];
                        return `
                            <td class="py-2 px-1 text-center">
                                <span class="grantee-matrix-cell inline-block ${isActive ? '' : 'bg-gray-100'}"
                                      style="${isActive ? `background-color: ${platformColors[platform]}` : ''}"
                                      title="${platform}: ${isActive ? 'Yes' : 'No'}">
                                </span>
                            </td>
                        `;
                    }).join('')}
                </tr>
            `).join('');
        } else if (matrixBody) {
            matrixBody.innerHTML = `
                <tr>
                    <td colspan="9" class="py-4 text-center text-gray-500 text-sm">
                        Grantee matrix data will appear once more platforms are scraped.
                    </td>
                </tr>
            `;
        }
    }

    /**
     * Render insights section
     */
    function renderInsights() {
        const container = document.getElementById('insights-container');
        if (!container) return;

        const insights = platformData?.insights || [];

        if (insights.length === 0) {
            container.innerHTML = `
                <div class="col-span-full bg-white rounded-xl p-6 shadow-md text-center text-gray-500">
                    Insights will appear once more data is collected.
                </div>
            `;
            return;
        }

        const insightColors = {
            dominance: '#2dc8d2',
            adoption: '#0085FF',
            leader: '#FFD700',
            growth: '#10B981',
            opportunity: '#F59E0B',
            efficiency: '#8B5CF6'
        };

        container.innerHTML = insights.map(insight => {
            const color = insightColors[insight.type] || '#6B7280';
            return `
                <div class="insight-card bg-white rounded-xl p-6 shadow-md" style="border-left-color: ${color}">
                    <div class="flex items-start gap-4">
                        <div class="w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0" style="background-color: ${color}20; color: ${color}">
                            ${INSIGHT_ICONS[insight.icon] || INSIGHT_ICONS['lightbulb']}
                        </div>
                        <div>
                            <p class="text-gray-800 font-medium">${insight.message}</p>
                            <p class="text-sm text-gray-500 mt-1 capitalize">${insight.platform || insight.type} insight</p>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    /**
     * Update last updated timestamp
     */
    function updateLastUpdated() {
        const element = document.getElementById('footer-last-updated');
        if (!element) return;

        const timestamp = platformData?.generated_at || new Date().toISOString();
        const date = new Date(timestamp);

        element.textContent = date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        });
    }

    /**
     * Get default chart options
     */
    function getChartDefaults() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#183642',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    borderColor: '#2dc8d2',
                    borderWidth: 1,
                    cornerRadius: 8,
                    padding: 12
                }
            }
        };
    }

    /**
     * Format number with commas
     */
    function formatNumber(num) {
        if (num === null || num === undefined) return '0';
        return new Intl.NumberFormat('en-US').format(Math.round(num));
    }

    /**
     * Format number with abbreviations
     */
    function formatAbbreviated(num) {
        if (num === null || num === undefined) return '0';
        if (num >= 1000000) return (num / 1000000).toFixed(1).replace(/\.0$/, '') + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1).replace(/\.0$/, '') + 'K';
        return num.toString();
    }

    /**
     * Truncate text with ellipsis
     */
    function truncate(text, maxLength) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength - 3) + '...';
    }

    /**
     * Hide loading overlay
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
     */
    function showError(message) {
        const loadingOverlay = document.getElementById('loading-overlay');
        const errorState = document.getElementById('error-state');
        const errorMessage = document.getElementById('error-message');

        if (loadingOverlay) loadingOverlay.style.display = 'none';
        if (errorState) errorState.classList.remove('hidden');
        if (errorMessage && message) errorMessage.textContent = message;
    }

    /**
     * Sleep utility
     */
    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Export public API
    window.NJCICPlatforms = {
        getData: () => ({ platformData, dashboardData }),
        refresh: init
    };

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
