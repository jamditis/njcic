/**
 * NJCIC Grantee Detail Page - Application Logic
 * Handles data loading, rendering, and chart initialization for individual grantee pages
 */

(function() {
    'use strict';

    // Calculate base path (handle /grantees/ subfolder)
    const isInGranteesFolder = window.location.pathname.includes('/grantees/');
    const basePath = isInGranteesFolder ? '../' : '';

    // Configuration
    const CONFIG = {
        granteeDataPath: `${basePath}data/grantees/`,
        dashboardDataPath: `${basePath}data/dashboard-data.json`,
        retryAttempts: 3,
        retryDelay: 1000
    };

    // Platform colors (matching charts.js)
    const PLATFORM_COLORS = {
        instagram: '#E4405F',
        tiktok: '#000000',
        youtube: '#FF0000',
        twitter: '#1DA1F2',
        facebook: '#1877F2',
        linkedin: '#0A66C2',
        threads: '#000000',
        bluesky: '#0085FF',
        default: '#6B7280'
    };

    // Platform icons (SVG paths)
    const PLATFORM_ICONS = {
        tiktok: '<svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5 20.1a6.34 6.34 0 0 0 10.86-4.43v-7a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.1z"/></svg>',
        bluesky: '<svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M12 10.8c-1.087-2.114-4.046-6.053-6.798-7.995C2.566.944 1.561 1.266.902 1.565.139 1.908 0 3.08 0 3.768c0 .69.378 5.65.624 6.479.815 2.736 3.713 3.66 6.383 3.364.136-.02.275-.039.415-.056-.138.022-.276.04-.415.056-3.912.58-7.387 2.005-2.83 7.078 5.013 5.19 6.87-1.113 7.823-4.308.953 3.195 2.05 9.271 7.733 4.308 4.267-4.308 1.172-6.498-2.74-7.078a8.741 8.741 0 0 1-.415-.056c.14.017.279.036.415.056 2.67.297 5.568-.628 6.383-3.364.246-.828.624-5.79.624-6.478 0-.69-.139-1.861-.902-2.206-.659-.298-1.664-.62-4.3 1.24C16.046 4.748 13.087 8.687 12 10.8z"/></svg>',
        instagram: '<svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>',
        youtube: '<svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>',
        twitter: '<svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>',
        facebook: '<svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>',
        linkedin: '<svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>',
        threads: '<svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M12.186 24h-.007c-3.581-.024-6.334-1.205-8.184-3.509C2.35 18.44 1.5 15.586 1.472 12.01v-.017c.03-3.579.879-6.43 2.525-8.482C5.845 1.205 8.6.024 12.18 0h.014c2.746.02 5.043.725 6.826 2.098 1.677 1.29 2.858 3.13 3.509 5.467l-2.04.569c-1.104-3.96-3.898-5.984-8.304-6.015-2.91.022-5.11.936-6.54 2.717C4.307 6.504 3.616 8.914 3.59 12c.025 3.086.718 5.496 2.057 7.164 1.43 1.783 3.631 2.698 6.54 2.717 2.623-.02 4.358-.631 5.8-2.045 1.647-1.613 1.618-3.593 1.09-4.798-.31-.71-.873-1.3-1.634-1.75-.192 1.352-.622 2.446-1.284 3.272-.886 1.102-2.14 1.704-3.73 1.79-1.202.065-2.361-.218-3.259-.801-1.063-.689-1.685-1.74-1.752-2.96-.065-1.182.408-2.256 1.33-3.022.858-.712 2.04-1.175 3.42-1.339.966-.115 1.953-.105 2.897.03.012-.636-.048-1.222-.189-1.632-.23-.664-.693-1.157-1.228-1.463-.652-.373-1.498-.475-2.213-.475-1.322 0-2.086.405-2.404.747-.337.363-.455.837-.423 1.267l-2.057.14c-.078-1.009.287-1.978 1.028-2.728.915-.926 2.353-1.429 4.102-1.429.882 0 1.87.133 2.748.582.994.51 1.77 1.339 2.18 2.335.21.509.33 1.08.378 1.778.62.306 1.182.69 1.67 1.145 1.02.955 1.703 2.208 1.975 3.634.272 1.428.13 2.973-.632 4.444-.9 1.736-2.427 3.078-4.418 3.881-1.532.618-3.296.933-5.243.933-.011 0-.022 0-.033 0zm1.838-8.83c-.657-.08-1.325-.09-1.977-.028-.934.09-1.686.366-2.18.8-.421.372-.62.82-.59 1.33.027.484.273.918.693 1.22.536.387 1.262.575 2.042.53 1.053-.057 1.878-.443 2.453-1.15.403-.495.689-1.131.866-1.897-.408-.132-.84-.26-1.307-.355z"/></svg>'
    };

    // State
    let granteeData = null;
    let dashboardData = null;
    let charts = {};

    /**
     * Get grantee slug from data attribute, path, or query parameter
     * @returns {string|null} Grantee slug or null if not found
     */
    function getGranteeSlug() {
        // First check for data-slug attribute on body (for static pages)
        const bodySlug = document.body.dataset.slug;
        if (bodySlug) return bodySlug;

        // Check for window.GRANTEE_SLUG variable
        if (window.GRANTEE_SLUG) return window.GRANTEE_SLUG;

        // Check URL path for /grantees/slug.html pattern
        const pathMatch = window.location.pathname.match(/\/grantees\/([^\/]+)\.html$/);
        if (pathMatch) return pathMatch[1];

        // Fallback to query parameters
        const params = new URLSearchParams(window.location.search);
        return params.get('grantee') || params.get('slug');
    }

    /**
     * Initialize the grantee page
     */
    async function init() {
        try {
            const slug = getGranteeSlug();

            if (!slug) {
                showError('No grantee specified. Please select a grantee from the dashboard.');
                return;
            }

            // Load data
            const [grantee, dashboard] = await Promise.all([
                loadGranteeData(slug),
                loadDashboardData()
            ]);

            granteeData = grantee;
            dashboardData = dashboard;

            // Hide loading, show content
            hideLoading();

            // Render page content
            renderGranteeInfo();
            renderPlatformIcons();
            renderSummaryStats();
            renderGrantInfo();
            renderPlatformCards();
            renderCharts();
            renderTopPosts();
            renderTimeline();
            renderRanking();
            updateLastUpdated();

            console.log('Grantee page initialized successfully for:', granteeData.name);
        } catch (error) {
            console.error('Grantee page initialization failed:', error);
            showError(error.message);
        }
    }

    /**
     * Load grantee-specific data
     * @param {string} slug - Grantee slug
     * @returns {Promise<Object>} Grantee data
     */
    async function loadGranteeData(slug) {
        const cacheBuster = `?v=${Date.now()}`;
        let lastError = null;

        for (let attempt = 1; attempt <= CONFIG.retryAttempts; attempt++) {
            try {
                const response = await fetch(`${CONFIG.granteeDataPath}${slug}.json${cacheBuster}`);

                if (!response.ok) {
                    if (response.status === 404) {
                        throw new Error(`Grantee "${slug}" not found.`);
                    }
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const data = await response.json();
                return normalizeGranteeData(data, slug);

            } catch (error) {
                lastError = error;
                console.warn(`Grantee data load attempt ${attempt} failed:`, error.message);

                if (attempt < CONFIG.retryAttempts && !error.message.includes('not found')) {
                    await sleep(CONFIG.retryDelay);
                } else {
                    break;
                }
            }
        }

        // Return sample data for demonstration if file doesn't exist
        console.log('Using sample grantee data for demonstration');
        return getSampleGranteeData(slug);
    }

    /**
     * Load dashboard data for rankings comparison
     * @returns {Promise<Object>} Dashboard data
     */
    async function loadDashboardData() {
        try {
            const response = await fetch(`${CONFIG.dashboardDataPath}?v=${Date.now()}`);
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.warn('Could not load dashboard data for comparison:', error.message);
        }
        return null;
    }

    /**
     * Normalize grantee data to expected format
     * Handles both simple format and detailed scraper output format
     * @param {Object} data - Raw grantee data
     * @param {string} slug - Grantee slug
     * @returns {Object} Normalized data
     */
    function normalizeGranteeData(data, slug) {
        // Check if data is in scraper output format (has summary object)
        if (data.summary && data.summary.total_posts !== undefined) {
            return normalizeScraperFormat(data, slug);
        }

        // Simple format - ensure required fields exist
        return {
            slug: data.slug || slug,
            name: data.name || slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
            website: data.website || null,
            description: data.description || null,
            logo: data.logo || null,
            grantInfo: data.grantInfo || null,
            totalPosts: data.totalPosts || data.posts || 0,
            totalEngagement: data.totalEngagement || data.engagement || 0,
            platforms: data.platforms || {},
            topPosts: data.topPosts || [],
            recentActivity: data.recentActivity || [],
            lastUpdated: data.lastUpdated || new Date().toISOString()
        };
    }

    /**
     * Normalize scraper output format to internal format
     * @param {Object} data - Scraper format data
     * @param {string} slug - Grantee slug
     * @returns {Object} Normalized data
     */
    function normalizeScraperFormat(data, slug) {
        const summary = data.summary || {};

        // Convert platforms from scraper format
        const platforms = {};
        if (data.platforms) {
            Object.entries(data.platforms).forEach(([platform, platformData]) => {
                const topPosts = platformData.top_posts || [];
                const topPost = topPosts[0];

                platforms[platform] = {
                    posts: platformData.posts || 0,
                    engagement: platformData.engagement || 0,
                    followers: platformData.followers || null,
                    views: platformData.views || null,
                    engagementRate: platformData.engagement_rate || null,
                    topPost: topPost ? {
                        engagement: topPost.engagement?.total || 0,
                        date: topPost.date || null,
                        url: topPost.url || null,
                        preview: topPost.text || null,
                        thumbnail: topPost.thumbnail || null
                    } : null,
                    frequency: platformData.frequency || null,
                    timeSeries: platformData.time_series || []
                };
            });
        }

        // Convert top posts from scraper format
        const topPosts = (data.top_posts || []).map(post => ({
            id: post.id,
            platform: detectPlatformFromUrl(post.url),
            engagement: post.engagement?.total || 0,
            likes: post.engagement?.likes || 0,
            comments: post.engagement?.comments || 0,
            shares: post.engagement?.shares || 0,
            views: post.engagement?.views || 0,
            date: post.date || null,
            url: post.url || null,
            preview: post.text || null,
            thumbnail: post.thumbnail || null
        }));

        // Convert time series to recent activity
        const recentActivity = (data.time_series || [])
            .filter(item => item.posts > 0)
            .sort((a, b) => new Date(b.date) - new Date(a.date))
            .slice(0, 10)
            .map(item => {
                // Find the platform for this date if there's only one platform
                const platformNames = Object.keys(data.platforms || {});
                const platform = platformNames.length === 1 ? platformNames[0] : 'multiple';

                return {
                    platform: platform,
                    date: item.date,
                    engagement: item.engagement || 0,
                    posts: item.posts,
                    preview: `${item.posts} post${item.posts > 1 ? 's' : ''} with ${formatNumber(item.engagement)} engagements`
                };
            });

        return {
            slug: data.slug || slug,
            name: data.name || slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
            website: data.website || null,
            description: data.description || null,
            logo: data.logo || null,
            grantInfo: data.grantInfo || null,
            totalPosts: summary.total_posts || 0,
            totalEngagement: summary.total_engagement || 0,
            totalFollowers: summary.total_followers || 0,
            platformsActive: summary.platforms_active || Object.keys(platforms).length,
            engagementRate: summary.engagement_rate || null,
            platforms: platforms,
            topPosts: topPosts,
            recentActivity: recentActivity,
            overallFrequency: data.overall_frequency || null,
            lastUpdated: summary.last_updated || new Date().toISOString()
        };
    }

    /**
     * Detect platform from URL
     * @param {string} url - Post URL
     * @returns {string} Platform name
     */
    function detectPlatformFromUrl(url) {
        if (!url) return 'unknown';
        const lowerUrl = url.toLowerCase();
        if (lowerUrl.includes('tiktok.com')) return 'tiktok';
        if (lowerUrl.includes('instagram.com')) return 'instagram';
        if (lowerUrl.includes('youtube.com') || lowerUrl.includes('youtu.be')) return 'youtube';
        if (lowerUrl.includes('twitter.com') || lowerUrl.includes('x.com')) return 'twitter';
        if (lowerUrl.includes('facebook.com')) return 'facebook';
        if (lowerUrl.includes('linkedin.com')) return 'linkedin';
        if (lowerUrl.includes('bsky.app') || lowerUrl.includes('bluesky')) return 'bluesky';
        if (lowerUrl.includes('threads.net')) return 'threads';
        return 'unknown';
    }

    /**
     * Get sample grantee data for demonstration
     * @param {string} slug - Grantee slug
     * @returns {Object} Sample grantee data
     */
    function getSampleGranteeData(slug) {
        const name = slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        return {
            slug: slug,
            name: name,
            website: null,
            totalPosts: 51,
            totalEngagement: 8623,
            platforms: {
                tiktok: {
                    posts: 26,
                    engagement: 7123,
                    followers: null,
                    topPost: {
                        engagement: 1250,
                        date: '2026-01-05',
                        url: null,
                        preview: 'Sample top TikTok post content preview...'
                    }
                },
                bluesky: {
                    posts: 25,
                    engagement: 1500,
                    followers: null,
                    topPost: {
                        engagement: 350,
                        date: '2026-01-03',
                        url: null,
                        preview: 'Sample top BlueSky post content preview...'
                    }
                }
            },
            topPosts: [
                { platform: 'tiktok', engagement: 1250, date: '2026-01-05', preview: 'Breaking: Local news coverage...', url: null },
                { platform: 'bluesky', engagement: 350, date: '2026-01-03', preview: 'Community update on...', url: null },
                { platform: 'tiktok', engagement: 890, date: '2026-01-02', preview: 'Behind the scenes...', url: null }
            ],
            recentActivity: [
                { platform: 'tiktok', date: '2026-01-07', engagement: 156, preview: 'Latest update...' },
                { platform: 'bluesky', date: '2026-01-06', engagement: 45, preview: 'Community discussion...' },
                { platform: 'tiktok', date: '2026-01-05', engagement: 1250, preview: 'Breaking coverage...' }
            ],
            lastUpdated: new Date().toISOString()
        };
    }

    /**
     * Get grantee logo path from slug or data
     * @param {Object} data - Grantee data object
     * @returns {string} Path to logo image
     */
    function getGranteeLogoPath(data) {
        // Use logo from data if available
        if (data.logo) {
            return data.logo;
        }
        // Fallback to generated path
        const logoMap = {
            'hopeloft-inc': 'hopeloft',
            'the-daily-targum-targum-publishing-co': 'daily-targum'
        };
        const logoSlug = logoMap[data.slug] || data.slug;
        return `../../branding/logos/grantees-web/${logoSlug}.png`;
    }

    /**
     * Render grantee basic info (name, breadcrumb, website, logo, description)
     */
    function renderGranteeInfo() {
        // Update page title
        document.title = `${granteeData.name} - NJCIC Social Media Dashboard`;

        // Update breadcrumb
        const breadcrumbName = document.getElementById('breadcrumb-name');
        if (breadcrumbName) {
            breadcrumbName.textContent = granteeData.name;
        }

        // Update hero name
        const granteeName = document.getElementById('grantee-name');
        if (granteeName) {
            granteeName.textContent = granteeData.name;
        }

        // Add logo to hero section
        const logoContainer = document.getElementById('grantee-logo');
        if (logoContainer && granteeData.logo) {
            const logoPath = getGranteeLogoPath(granteeData);
            logoContainer.innerHTML = `
                <img src="${logoPath}" alt="${granteeData.name}"
                     class="max-h-20 w-auto object-contain mx-auto"
                     loading="lazy"
                     onerror="this.parentElement.classList.add('hidden')">
            `;
            logoContainer.classList.remove('hidden');
        }

        // Render description if available
        const descriptionContainer = document.getElementById('grantee-description');
        if (descriptionContainer && granteeData.description) {
            descriptionContainer.innerHTML = `
                <p class="text-gray-300 text-base sm:text-lg leading-relaxed max-w-3xl mx-auto">
                    ${escapeHtml(granteeData.description)}
                </p>
            `;
            descriptionContainer.classList.remove('hidden');
        }

        // Update website link if available - render as prominent button
        const websiteContainer = document.getElementById('grantee-website');
        if (websiteContainer && granteeData.website) {
            let displayUrl = 'Visit website';
            try {
                const url = new URL(granteeData.website);
                displayUrl = url.hostname.replace('www.', '');
            } catch {
                // Use default text
            }

            websiteContainer.innerHTML = `
                <a href="${escapeHtml(granteeData.website)}"
                   target="_blank"
                   rel="noopener noreferrer"
                   class="inline-flex items-center gap-2 px-5 py-2.5 bg-njcic-teal hover:bg-njcic-orange text-white font-medium rounded-full transition-all duration-300 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/>
                    </svg>
                    <span>${displayUrl}</span>
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                    </svg>
                </a>
            `;
            websiteContainer.classList.remove('hidden');
        }
    }

    /**
     * Render platform icons in hero section
     */
    function renderPlatformIcons() {
        const container = document.getElementById('platform-icons');
        if (!container || !granteeData.platforms) return;

        const platforms = Object.keys(granteeData.platforms);

        container.innerHTML = platforms.map(platform => {
            const color = PLATFORM_COLORS[platform.toLowerCase()] || PLATFORM_COLORS.default;
            const icon = PLATFORM_ICONS[platform.toLowerCase()] || '';

            return `
                <div class="w-10 h-10 rounded-full flex items-center justify-center text-white"
                     style="background-color: ${color}"
                     title="${capitalizeFirst(platform)}">
                    ${icon}
                </div>
            `;
        }).join('');
    }

    /**
     * Render summary statistics
     */
    function renderSummaryStats() {
        const platforms = granteeData.platforms ? Object.keys(granteeData.platforms).length : 0;
        const avgEngagement = granteeData.totalPosts > 0
            ? Math.round(granteeData.totalEngagement / granteeData.totalPosts)
            : 0;

        document.getElementById('stat-posts').textContent = formatNumber(granteeData.totalPosts);
        document.getElementById('stat-engagement').textContent = formatNumber(granteeData.totalEngagement);
        document.getElementById('stat-platforms').textContent = platforms;
        document.getElementById('stat-rate').textContent = formatNumber(avgEngagement);
    }

    /**
     * Render grant information section
     */
    function renderGrantInfo() {
        const container = document.getElementById('grant-info-section');
        if (!container) return;

        const grantInfo = granteeData.grantInfo;
        if (!grantInfo || !grantInfo.grants || grantInfo.grants.length === 0) {
            container.classList.add('hidden');
            return;
        }

        container.classList.remove('hidden');

        // Build focus area badges
        const focusAreas = grantInfo.focusArea ? grantInfo.focusArea.split(';').map(a => a.trim()) : [];
        const focusAreaBadges = focusAreas.map(area => {
            // Color coding based on focus area type
            let bgColor = 'bg-njcic-teal';
            if (area.toLowerCase().includes('journalism pipeline')) {
                bgColor = 'bg-purple-500';
            } else if (area.toLowerCase().includes('civic engagement')) {
                bgColor = 'bg-green-500';
            } else if (area.toLowerCase().includes('blue engine') || area.toLowerCase().includes('accelerator')) {
                bgColor = 'bg-orange-500';
            }
            return `<span class="inline-block px-3 py-1 ${bgColor} text-white text-xs font-medium rounded-full">${escapeHtml(area)}</span>`;
        }).join('');

        // Build location and status info
        const locationParts = [];
        if (grantInfo.city) locationParts.push(grantInfo.city);
        if (grantInfo.county) locationParts.push(grantInfo.county);
        const locationStr = locationParts.join(', ');

        // Build years string
        const yearsStr = grantInfo.years && grantInfo.years.length > 0
            ? grantInfo.years.join(', ')
            : '';

        // Status badge
        const statusBadge = grantInfo.status === 'active'
            ? '<span class="inline-flex items-center gap-1 px-2 py-0.5 bg-green-100 text-green-700 text-xs font-medium rounded-full"><span class="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></span>Active</span>'
            : '<span class="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-100 text-gray-600 text-xs font-medium rounded-full">Completed</span>';

        // Header with summary info
        let html = `
            <div class="bg-gradient-to-r from-njcic-light to-white rounded-2xl p-6 sm:p-8 border border-gray-100">
                <div class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-6">
                    <div>
                        <h4 class="text-xl sm:text-2xl font-bold text-njcic-dark mb-2">
                            NJCIC Grant${grantInfo.grantCount > 1 ? 's' : ''}
                        </h4>
                        <div class="flex flex-wrap gap-2 mb-3">
                            ${focusAreaBadges}
                        </div>
                        ${locationStr ? `<p class="text-gray-500 text-sm"><svg class="w-4 h-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/></svg>${escapeHtml(locationStr)}</p>` : ''}
                    </div>
                    <div class="text-left sm:text-right">
                        <div class="text-3xl sm:text-4xl font-bold text-njcic-teal mb-1">
                            ${grantInfo.formattedFunding || formatCurrency(grantInfo.totalFunding)}
                        </div>
                        <div class="text-sm text-gray-500 mb-2">Total funding</div>
                        <div class="flex items-center gap-2 justify-start sm:justify-end">
                            ${statusBadge}
                            ${yearsStr ? `<span class="text-xs text-gray-400">${yearsStr}</span>` : ''}
                        </div>
                    </div>
                </div>
        `;

        // Render individual grants
        if (grantInfo.grants.length === 1) {
            // Single grant - show description prominently
            const grant = grantInfo.grants[0];
            if (grant.description) {
                html += `
                    <div class="prose prose-gray max-w-none">
                        <p class="text-gray-700 leading-relaxed">${escapeHtml(grant.description)}</p>
                    </div>
                `;
            }
        } else {
            // Multiple grants - show as cards
            html += `
                <div class="grid gap-4 mt-4">
                    ${grantInfo.grants.map((grant, index) => {
                        const grantYears = grant.years && grant.years.length > 0 ? grant.years.join(', ') : '';
                        const grantStatus = grant.status === 'active'
                            ? '<span class="w-2 h-2 bg-green-500 rounded-full"></span>'
                            : '<span class="w-2 h-2 bg-gray-400 rounded-full"></span>';

                        return `
                            <div class="bg-white rounded-xl p-5 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
                                <div class="flex flex-wrap items-center justify-between gap-2 mb-3">
                                    <div class="flex items-center gap-2">
                                        ${grantStatus}
                                        <span class="font-semibold text-njcic-dark">Grant ${index + 1}</span>
                                        ${grant.focusArea ? `<span class="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded">${escapeHtml(grant.focusArea)}</span>` : ''}
                                    </div>
                                    <div class="flex items-center gap-3">
                                        <span class="text-lg font-bold text-njcic-teal">${grant.formattedAmount || formatCurrency(grant.amount)}</span>
                                        ${grantYears ? `<span class="text-xs text-gray-400">${grantYears}</span>` : ''}
                                    </div>
                                </div>
                                ${grant.description ? `<p class="text-gray-600 text-sm leading-relaxed">${escapeHtml(grant.description)}</p>` : ''}
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        }

        // Link to grantees map
        html += `
                <div class="mt-6 pt-4 border-t border-gray-200">
                    <a href="https://njcivicinfo.org/map/"
                       target="_blank"
                       rel="noopener noreferrer"
                       class="inline-flex items-center gap-2 text-sm text-njcic-teal hover:text-njcic-dark transition-colors">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
                        </svg>
                        View all NJCIC grantees on the map
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                        </svg>
                    </a>
                </div>
            </div>
        `;

        container.innerHTML = html;
    }

    /**
     * Format currency helper
     */
    function formatCurrency(amount) {
        if (!amount) return '$0';
        if (amount >= 1000000) {
            return '$' + (amount / 1000000).toFixed(1).replace(/\.0$/, '') + 'M';
        }
        if (amount >= 1000) {
            return '$' + (amount / 1000).toFixed(0) + 'K';
        }
        return '$' + amount.toLocaleString();
    }

    /**
     * Render platform breakdown cards
     */
    function renderPlatformCards() {
        const container = document.getElementById('platform-cards');
        if (!container || !granteeData.platforms) return;

        const platforms = Object.entries(granteeData.platforms);

        if (platforms.length === 0) {
            container.innerHTML = '<p class="text-gray-500 col-span-full text-center py-8">No platform data available.</p>';
            return;
        }

        container.innerHTML = platforms.map(([platform, data]) => {
            const color = PLATFORM_COLORS[platform.toLowerCase()] || PLATFORM_COLORS.default;
            const icon = PLATFORM_ICONS[platform.toLowerCase()] || '';
            const topPost = data.topPost || {};

            // Build additional stats if available
            let additionalStats = '';
            if (data.views) {
                additionalStats += `
                    <div>
                        <div class="text-lg font-bold text-njcic-dark">${formatAbbreviated(data.views)}</div>
                        <div class="text-xs text-gray-500">Views</div>
                    </div>
                `;
            }
            if (data.engagementRate) {
                additionalStats += `
                    <div>
                        <div class="text-lg font-bold text-njcic-dark">${data.engagementRate.toFixed(1)}</div>
                        <div class="text-xs text-gray-500">Eng. Rate</div>
                    </div>
                `;
            }

            // Build frequency info if available
            let frequencyInfo = '';
            if (data.frequency) {
                const postsPerWeek = data.frequency.posts_per_week?.toFixed(1) || '0';
                frequencyInfo = `
                    <div class="text-xs text-gray-400 mt-2">
                        ~${postsPerWeek} posts/week
                    </div>
                `;
            }

            return `
                <div class="bg-white rounded-2xl shadow-lg p-6 border-t-4 hover:shadow-xl transition-shadow"
                     style="border-top-color: ${color}">
                    <div class="flex items-center gap-3 mb-4">
                        <div class="w-10 h-10 rounded-full flex items-center justify-center text-white"
                             style="background-color: ${color}">
                            ${icon}
                        </div>
                        <h4 class="text-lg font-bold text-njcic-dark">${capitalizeFirst(platform)}</h4>
                    </div>

                    <div class="grid grid-cols-2 gap-4 mb-4">
                        <div>
                            <div class="text-2xl font-bold text-njcic-dark">${formatNumber(data.posts || 0)}</div>
                            <div class="text-sm text-gray-500">Posts</div>
                        </div>
                        <div>
                            <div class="text-2xl font-bold text-njcic-dark">${formatAbbreviated(data.engagement || 0)}</div>
                            <div class="text-sm text-gray-500">Engagement</div>
                        </div>
                        ${additionalStats}
                    </div>
                    ${frequencyInfo}

                    ${topPost.preview ? `
                        <div class="border-t pt-4 mt-4">
                            <div class="text-xs text-gray-400 mb-1">Top post preview</div>
                            <p class="text-sm text-gray-600 line-clamp-2">${escapeHtml(topPost.preview)}</p>
                            <div class="flex items-center justify-between mt-2">
                                ${topPost.engagement ? `
                                    <span class="text-xs text-njcic-teal font-medium">
                                        ${formatNumber(topPost.engagement)} engagements
                                    </span>
                                ` : ''}
                                ${topPost.url ? `
                                    <a href="${escapeHtml(topPost.url)}" target="_blank" rel="noopener noreferrer"
                                       class="text-xs text-njcic-teal hover:underline">
                                        View
                                    </a>
                                ` : ''}
                            </div>
                        </div>
                    ` : ''}
                </div>
            `;
        }).join('');
    }

    /**
     * Render charts
     */
    function renderCharts() {
        if (!granteeData.platforms || Object.keys(granteeData.platforms).length === 0) {
            return;
        }

        renderEngagementPieChart();
        renderPostsBarChart();
        renderPerformanceStats();
    }

    /**
     * Render engagement pie/donut chart
     */
    function renderEngagementPieChart() {
        const ctx = document.getElementById('engagementPieChart');
        if (!ctx) return;

        const platforms = Object.entries(granteeData.platforms);
        const labels = platforms.map(([name]) => capitalizeFirst(name));
        const values = platforms.map(([, data]) => data.engagement || 0);
        const colors = platforms.map(([name]) =>
            PLATFORM_COLORS[name.toLowerCase()] || PLATFORM_COLORS.default
        );

        // Create legend
        const legendContainer = document.getElementById('engagement-pie-legend');
        if (legendContainer) {
            legendContainer.innerHTML = labels.map((label, index) => `
                <div class="flex items-center gap-2 px-3 py-1 bg-gray-50 rounded-full text-sm">
                    <span class="w-3 h-3 rounded-full" style="background-color: ${colors[index]}"></span>
                    <span>${label}</span>
                    <span class="font-semibold">${formatAbbreviated(values[index])}</span>
                </div>
            `).join('');
        }

        charts.engagementPie = new Chart(ctx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderColor: '#ffffff',
                    borderWidth: 3,
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '60%',
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((context.raw / total) * 100).toFixed(1);
                                return ` ${context.label}: ${formatNumber(context.raw)} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * Render posts bar chart
     */
    function renderPostsBarChart() {
        const ctx = document.getElementById('postsBarChart');
        if (!ctx) return;

        const platforms = Object.entries(granteeData.platforms);
        const labels = platforms.map(([name]) => capitalizeFirst(name));
        const values = platforms.map(([, data]) => data.posts || 0);
        const colors = platforms.map(([name]) =>
            PLATFORM_COLORS[name.toLowerCase()] || PLATFORM_COLORS.default
        );

        charts.postsBar = new Chart(ctx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderRadius: 6,
                    borderSkipped: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return ` ${formatNumber(context.raw)} posts`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(0, 0, 0, 0.05)' },
                        ticks: {
                            callback: function(value) {
                                return formatAbbreviated(value);
                            }
                        }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });
    }

    /**
     * Render performance stats below charts
     */
    function renderPerformanceStats() {
        // Average engagement per post
        const avgPerPost = granteeData.totalPosts > 0
            ? Math.round(granteeData.totalEngagement / granteeData.totalPosts)
            : 0;
        document.getElementById('avg-engagement-per-post').textContent = formatNumber(avgPerPost);

        // Best performing platform
        let bestPlatform = '--';
        let maxEngagement = 0;
        let topPostEngagement = 0;

        Object.entries(granteeData.platforms || {}).forEach(([name, data]) => {
            if ((data.engagement || 0) > maxEngagement) {
                maxEngagement = data.engagement;
                bestPlatform = capitalizeFirst(name);
            }
            if (data.topPost && (data.topPost.engagement || 0) > topPostEngagement) {
                topPostEngagement = data.topPost.engagement;
            }
        });

        // Also check topPosts array for highest engagement
        (granteeData.topPosts || []).forEach(post => {
            if ((post.engagement || 0) > topPostEngagement) {
                topPostEngagement = post.engagement;
            }
        });

        document.getElementById('best-platform').textContent = bestPlatform;
        document.getElementById('top-post-engagement').textContent = formatNumber(topPostEngagement);
    }

    /**
     * Render top posts grid
     */
    function renderTopPosts() {
        const container = document.getElementById('top-posts-grid');
        const noPostsMessage = document.getElementById('no-posts-message');

        if (!container) return;

        const posts = granteeData.topPosts || [];

        if (posts.length === 0) {
            container.classList.add('hidden');
            if (noPostsMessage) noPostsMessage.classList.remove('hidden');
            return;
        }

        container.classList.remove('hidden');
        if (noPostsMessage) noPostsMessage.classList.add('hidden');

        container.innerHTML = posts.slice(0, 9).map(post => {
            const color = PLATFORM_COLORS[post.platform?.toLowerCase()] || PLATFORM_COLORS.default;
            const icon = PLATFORM_ICONS[post.platform?.toLowerCase()] || '';
            const date = post.date ? formatDate(post.date) : '';

            // Build engagement breakdown if available
            let engagementBreakdown = '';
            if (post.likes || post.comments || post.shares) {
                const parts = [];
                if (post.likes) parts.push(`${formatAbbreviated(post.likes)} likes`);
                if (post.comments) parts.push(`${formatAbbreviated(post.comments)} comments`);
                if (post.shares) parts.push(`${formatAbbreviated(post.shares)} shares`);
                engagementBreakdown = `
                    <div class="text-xs text-gray-400 mt-1">${parts.join(' / ')}</div>
                `;
            }

            // Views display
            let viewsDisplay = '';
            if (post.views) {
                viewsDisplay = `
                    <div class="flex items-center gap-1 text-gray-500">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                        </svg>
                        <span class="text-xs">${formatAbbreviated(post.views)}</span>
                    </div>
                `;
            }

            return `
                <div class="bg-white rounded-2xl shadow-lg p-5 hover:shadow-xl transition-shadow border border-gray-100">
                    <div class="flex items-center justify-between mb-3">
                        <div class="flex items-center gap-2">
                            <div class="w-8 h-8 rounded-full flex items-center justify-center text-white"
                                 style="background-color: ${color}">
                                ${icon}
                            </div>
                            <span class="text-sm font-medium text-gray-600">${capitalizeFirst(post.platform || 'Unknown')}</span>
                        </div>
                        ${date ? `<span class="text-xs text-gray-400">${date}</span>` : ''}
                    </div>

                    ${post.preview ? `
                        <p class="text-sm text-gray-700 line-clamp-3 mb-3">${escapeHtml(post.preview)}</p>
                    ` : '<p class="text-sm text-gray-400 italic mb-3">No preview available</p>'}

                    <div class="pt-3 border-t border-gray-100">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center gap-3">
                                <div class="flex items-center gap-1 text-njcic-teal">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/>
                                    </svg>
                                    <span class="text-sm font-semibold">${formatNumber(post.engagement || 0)}</span>
                                </div>
                                ${viewsDisplay}
                            </div>
                            ${post.url ? `
                                <a href="${escapeHtml(post.url)}" target="_blank" rel="noopener noreferrer"
                                   class="text-xs text-njcic-teal hover:underline flex items-center gap-1">
                                    View
                                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                                    </svg>
                                </a>
                            ` : ''}
                        </div>
                        ${engagementBreakdown}
                    </div>
                </div>
            `;
        }).join('');
    }

    /**
     * Render activity timeline
     */
    function renderTimeline() {
        const container = document.getElementById('timeline-items');
        const noTimelineMessage = document.getElementById('no-timeline-message');
        const timelineSection = document.getElementById('timeline-section');

        if (!container) return;

        const activities = granteeData.recentActivity || [];

        if (activities.length === 0) {
            if (timelineSection) {
                // Hide timeline line
                const timelineLine = timelineSection.querySelector('.absolute');
                if (timelineLine) timelineLine.classList.add('hidden');
            }
            container.classList.add('hidden');
            if (noTimelineMessage) noTimelineMessage.classList.remove('hidden');
            return;
        }

        container.classList.remove('hidden');
        if (noTimelineMessage) noTimelineMessage.classList.add('hidden');

        container.innerHTML = activities.slice(0, 10).map(activity => {
            const color = PLATFORM_COLORS[activity.platform?.toLowerCase()] || PLATFORM_COLORS.default;
            const icon = PLATFORM_ICONS[activity.platform?.toLowerCase()] || '';
            const date = activity.date ? formatDate(activity.date) : '';

            return `
                <div class="relative pl-12 sm:pl-16">
                    <div class="absolute left-0 w-8 h-8 sm:w-12 sm:h-12 rounded-full flex items-center justify-center text-white z-10"
                         style="background-color: ${color}">
                        ${icon}
                    </div>
                    <div class="bg-white rounded-xl shadow p-4 hover:shadow-md transition-shadow">
                        <div class="flex items-center justify-between mb-2">
                            <span class="text-sm font-medium text-gray-700">${capitalizeFirst(activity.platform || 'Post')}</span>
                            ${date ? `<span class="text-xs text-gray-400">${date}</span>` : ''}
                        </div>
                        ${activity.preview ? `
                            <p class="text-sm text-gray-600 line-clamp-2">${escapeHtml(activity.preview)}</p>
                        ` : ''}
                        <div class="mt-2 text-xs text-njcic-teal font-medium">
                            ${formatNumber(activity.engagement || 0)} engagements
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    /**
     * Render ranking comparison
     */
    function renderRanking() {
        const rankingText = document.getElementById('ranking-text');
        const rankNumber = document.getElementById('rank-number');
        const totalGranteesEl = document.getElementById('total-grantees');

        if (!dashboardData || !dashboardData.topGrantees) {
            if (rankingText) rankingText.textContent = 'Data unavailable';
            return;
        }

        const allGrantees = dashboardData.topGrantees;
        const totalGrantees = allGrantees.length;

        // Find this grantee's rank
        const granteeIndex = allGrantees.findIndex(g =>
            g.name.toLowerCase() === granteeData.name.toLowerCase()
        );

        if (granteeIndex === -1) {
            if (rankingText) rankingText.textContent = 'Not Ranked';
            if (totalGranteesEl) totalGranteesEl.textContent = `${totalGrantees} grantees`;
            return;
        }

        const rank = granteeIndex + 1;
        const percentile = Math.round(((totalGrantees - rank + 1) / totalGrantees) * 100);

        if (rankingText) {
            if (rank === 1) {
                rankingText.textContent = '#1 Top Performer';
            } else if (percentile >= 90) {
                rankingText.textContent = `Top ${100 - percentile + 1}%`;
            } else if (percentile >= 75) {
                rankingText.textContent = `Top ${100 - percentile + 1}%`;
            } else if (percentile >= 50) {
                rankingText.textContent = 'Above Average';
            } else {
                rankingText.textContent = 'Building Presence';
            }
        }

        if (rankNumber) rankNumber.textContent = `#${rank}`;
        if (totalGranteesEl) totalGranteesEl.textContent = `${totalGrantees} grantees`;
    }

    /**
     * Update last updated timestamp
     */
    function updateLastUpdated() {
        const element = document.getElementById('last-updated');
        if (!element) return;

        const date = new Date(granteeData.lastUpdated || new Date());
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

    // Utility functions

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
        if (num >= 1000000000) {
            return (num / 1000000000).toFixed(1).replace(/\.0$/, '') + 'B';
        }
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1).replace(/\.0$/, '') + 'M';
        }
        if (num >= 1000) {
            return (num / 1000).toFixed(1).replace(/\.0$/, '') + 'K';
        }
        return num.toString();
    }

    /**
     * Format date string
     */
    function formatDate(dateStr) {
        try {
            const date = new Date(dateStr);
            return date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: date.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined
            });
        } catch {
            return dateStr;
        }
    }

    /**
     * Capitalize first letter
     */
    function capitalizeFirst(str) {
        if (!str) return '';
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    /**
     * Sleep utility
     */
    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Export public API
    window.NJCICGrantee = {
        getData: () => granteeData,
        getDashboardData: () => dashboardData
    };

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
