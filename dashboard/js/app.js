/**
 * NJCIC Dashboard - Main Application Logic
 * Handles data loading, counter animations, filtering, sorting, and dashboard initialization
 */

(function() {
    'use strict';

    // Configuration
    const CONFIG = {
        dataPath: 'data/dashboard-data.json',
        counterDuration: 2000, // ms
        counterFrameRate: 60, // fps
        retryAttempts: 3,
        retryDelay: 1000, // ms
        searchDebounce: 300 // ms
    };

    // State
    let dashboardData = null;
    let rawData = null;
    let charts = {
        platform: null,
        grantees: null,
        engagementByPlatform: null
    };
    let currentFilters = {
        search: '',
        platform: 'all',
        sort: 'engagement-desc'
    };
    let tableSort = {
        column: 'engagement',
        direction: 'desc'
    };

    /**
     * Initialize the dashboard
     */
    async function init() {
        try {
            // Load data
            rawData = await loadData();
            dashboardData = normalizeData(rawData);

            // Hide loading, show content
            hideLoading();

            // Initialize components
            initNavigation();
            initCounters();
            initCharts();
            initGranteesGrid();
            initRankingsTable();
            initSearch();
            initFilters();
            initTableSort();
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
                return data;

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
            const platformEngagement = {};
            if (data.platforms) {
                Object.entries(data.platforms).forEach(([platform, info]) => {
                    // Capitalize platform name
                    const name = platform.charAt(0).toUpperCase() + platform.slice(1);
                    platforms[name] = info.posts || 0;
                    platformEngagement[name] = info.engagement || 0;
                });
            }

            // Convert topGrantees to grantees format with full data
            const grantees = (data.topGrantees || []).map(g => ({
                name: g.name,
                posts: g.posts || 0,
                engagement: g.engagement || 0,
                topPlatform: g.topPlatform || '',
                platformsScraped: g.platformsScraped || 1,
                slug: createSlug(g.name)
            }));

            return {
                summary: {
                    totalGrantees: data.summary.totalGrantees || 0,
                    totalPosts: data.summary.totalPosts || 0,
                    totalEngagement: data.summary.totalEngagement || 0,
                    platformsMonitored: data.summary.platformsTracked || Object.keys(data.platforms || {}).length
                },
                platforms: platforms,
                platformEngagement: platformEngagement,
                grantees: grantees,
                engagementByPlatform: data.engagementByPlatform || [],
                lastUpdated: data.summary.lastUpdated || data.metadata?.generatedAt || new Date().toISOString(),
                metadata: data.metadata || {}
            };
        }

        // Data is already in expected format
        return data;
    }

    /**
     * Create URL-friendly slug from name
     * @param {string} name - Name to convert
     * @returns {string} URL-friendly slug
     */
    function createSlug(name) {
        return name
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, '-')
            .replace(/(^-|-$)/g, '');
    }

    /**
     * Get sample data for demonstration
     * @returns {Object} Sample dashboard data
     */
    function getSampleData() {
        return {
            summary: {
                totalGrantees: 14,
                totalPosts: 371,
                totalEngagement: 130252,
                platformsTracked: 2,
                lastUpdated: new Date().toISOString()
            },
            platforms: {
                tiktok: { posts: 196, engagement: 119632, grantees: 9 },
                bluesky: { posts: 175, engagement: 10620, grantees: 7 }
            },
            topGrantees: [
                { name: "HudPost", posts: 26, engagement: 103604, topPlatform: "tiktok", platformsScraped: 1 },
                { name: "The Jersey Vindicator", posts: 25, engagement: 9610, topPlatform: "bluesky", platformsScraped: 1 },
                { name: "NJ Spotlight News", posts: 51, engagement: 8623, topPlatform: "tiktok", platformsScraped: 2 },
                { name: "The College of New Jersey", posts: 26, engagement: 2966, topPlatform: "tiktok", platformsScraped: 1 },
                { name: "Slice of Culture Saint Peter's University", posts: 26, engagement: 1791, topPlatform: "tiktok", platformsScraped: 1 },
                { name: "Daily Targum", posts: 26, engagement: 1609, topPlatform: "tiktok", platformsScraped: 1 }
            ],
            engagementByPlatform: [
                { platform: "tiktok", engagement: 119632, posts: 196, color: "#000000" },
                { platform: "bluesky", engagement: 10620, posts: 175, color: "#0085FF" }
            ],
            metadata: {
                generatedAt: new Date().toISOString(),
                platformColors: {
                    twitter: "#1DA1F2",
                    youtube: "#FF0000",
                    instagram: "#E1306C",
                    facebook: "#1877F2",
                    linkedin: "#0A66C2",
                    tiktok: "#000000",
                    bluesky: "#0085FF",
                    threads: "#000000"
                }
            }
        };
    }

    /**
     * Initialize navigation (mobile menu, smooth scroll, active states)
     */
    function initNavigation() {
        // Mobile menu toggle
        const mobileMenuBtn = document.getElementById('mobile-menu-btn');
        const mobileMenu = document.getElementById('mobile-menu');

        if (mobileMenuBtn && mobileMenu) {
            mobileMenuBtn.addEventListener('click', () => {
                const isHidden = mobileMenu.classList.toggle('hidden');
                mobileMenuBtn.setAttribute('aria-expanded', !isHidden);
            });

            // Close menu when clicking a link
            mobileMenu.querySelectorAll('a').forEach(link => {
                link.addEventListener('click', () => {
                    mobileMenu.classList.add('hidden');
                    mobileMenuBtn.setAttribute('aria-expanded', 'false');
                });
            });
        }

        // Update active nav link on scroll
        const sections = document.querySelectorAll('section[id]');
        const navLinks = document.querySelectorAll('.nav-link');

        function updateActiveNav() {
            const scrollPosition = window.scrollY + 100;

            sections.forEach(section => {
                const sectionTop = section.offsetTop;
                const sectionHeight = section.offsetHeight;
                const sectionId = section.getAttribute('id');

                if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
                    navLinks.forEach(link => {
                        link.classList.remove('text-njcic-teal', 'bg-white/10');
                        if (link.getAttribute('href') === `#${sectionId}`) {
                            link.classList.add('text-njcic-teal', 'bg-white/10');
                        }
                    });
                }
            });
        }

        window.addEventListener('scroll', updateActiveNav);
        updateActiveNav();
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
        // Use abbreviated format for large numbers to prevent clipping
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1).replace(/\.0$/, '') + 'M';
        }
        return new Intl.NumberFormat('en-US').format(Math.round(num));
    }

    /**
     * Format number with abbreviation (K, M, B)
     * @param {number} num - Number to format
     * @returns {string} Abbreviated number
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

        // Engagement by Platform Chart
        const engagementCtx = document.getElementById('engagementByPlatformChart');
        if (engagementCtx && window.NJCICCharts) {
            charts.engagementByPlatform = window.NJCICCharts.createEngagementByPlatformChart(
                engagementCtx.getContext('2d'),
                dashboardData.engagementByPlatform || dashboardData.platformEngagement
            );
        }

        // Top Grantees Chart (with click handler)
        const granteesCtx = document.getElementById('granteesChart');
        if (granteesCtx && window.NJCICCharts) {
            charts.grantees = window.NJCICCharts.createGranteesChart(
                granteesCtx.getContext('2d'),
                dashboardData.grantees,
                handleGranteeChartClick
            );
        }
    }

    /**
     * Handle click on grantee chart bar
     * @param {Object} grantee - Clicked grantee data
     */
    function handleGranteeChartClick(grantee) {
        if (grantee && grantee.slug) {
            window.location.href = `grantees/${grantee.slug}.html`;
        }
    }

    /**
     * Initialize the grantees grid
     */
    function initGranteesGrid() {
        renderGranteesGrid(dashboardData.grantees);
        initPlatformButtons();
    }

    /**
     * Initialize platform filter buttons
     */
    function initPlatformButtons() {
        const container = document.getElementById('platform-buttons');
        if (!container) return;

        // Get unique platforms from grantees
        const platforms = new Set();
        dashboardData.grantees.forEach(g => {
            if (g.topPlatform) {
                platforms.add(g.topPlatform.toLowerCase());
            }
        });

        // Clear existing buttons except "All"
        const allBtn = container.querySelector('[data-platform="all"]');
        container.innerHTML = '';
        if (allBtn) container.appendChild(allBtn);

        // Add platform buttons
        platforms.forEach(platform => {
            const btn = document.createElement('button');
            btn.className = 'platform-btn px-4 py-2 rounded-full text-sm font-medium transition-all';
            btn.dataset.platform = platform;
            btn.innerHTML = `
                <span class="flex items-center gap-2">
                    ${getPlatformIcon(platform)}
                    ${platform.charAt(0).toUpperCase() + platform.slice(1)}
                </span>
            `;
            container.appendChild(btn);
        });

        // Add click handlers
        container.querySelectorAll('.platform-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                container.querySelectorAll('.platform-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentFilters.platform = btn.dataset.platform;

                // Sync with select dropdown
                const select = document.getElementById('platform-filter');
                if (select) select.value = currentFilters.platform;

                applyFilters();
            });
        });
    }

    /**
     * Get SVG icon for platform
     * @param {string} platform - Platform name
     * @returns {string} SVG icon HTML
     */
    function getPlatformIcon(platform) {
        const icons = {
            tiktok: `<svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-5.2 1.74 2.89 2.89 0 012.31-4.64 2.93 2.93 0 01.88.13V9.4a6.84 6.84 0 00-1-.05A6.33 6.33 0 005 20.1a6.34 6.34 0 0010.86-4.43v-7a8.16 8.16 0 004.77 1.52v-3.4a4.85 4.85 0 01-1-.1z"/></svg>`,
            bluesky: `<svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M12 10.8c-1.087-2.114-4.046-6.053-6.798-7.995C2.566.944 1.561 1.266.902 1.565.139 1.908 0 3.08 0 3.768c0 .69.378 5.65.624 6.479.815 2.736 3.713 3.66 6.383 3.364.136-.02.275-.039.415-.056-.138.022-.276.04-.415.056-3.912.58-7.387 2.005-2.83 7.078 5.013 5.19 6.87-1.113 7.823-4.308.953 3.195 2.05 9.271 7.733 4.308 4.267-4.308 1.172-6.498-2.74-7.078a8.741 8.741 0 01-.415-.056c.14.017.279.036.415.056 2.67.296 5.568-.628 6.383-3.364.246-.828.624-5.79.624-6.478 0-.69-.139-1.861-.902-2.206-.659-.298-1.664-.62-4.3 1.24C16.046 4.748 13.087 8.687 12 10.8z"/></svg>`,
            instagram: `<svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/></svg>`,
            youtube: `<svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M23.498 6.186a3.016 3.016 0 00-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 00.502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 002.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 002.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>`,
            twitter: `<svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>`,
            facebook: `<svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>`
        };
        return icons[platform.toLowerCase()] || '';
    }

    /**
     * Get grantee logo path from slug or logo URL
     * @param {string} slug - Grantee slug
     * @param {string} logoUrl - Optional logo URL from grantee data
     * @returns {string} Path to logo image
     */
    function getGranteeLogoPath(slug, logoUrl) {
        // Use logo URL from grantee data if available
        if (logoUrl) {
            return logoUrl;
        }
        // Map variant slugs to their logo files
        const logoMap = {
            'hopeloft-inc': 'hopeloft',
            'the-daily-targum-targum-publishing-co': 'daily-targum'
        };
        const logoSlug = logoMap[slug] || slug;
        return `../branding/logos/grantees-web/thumbs/${logoSlug}.png`;
    }

    /**
     * Render grantees grid with cards
     * @param {Array} grantees - Array of grantee objects
     */
    function renderGranteesGrid(grantees) {
        const grid = document.getElementById('grantees-grid');
        const noResults = document.getElementById('no-results');

        if (!grid) return;

        // Preserve scroll position to prevent auto-scroll on DOM update
        const scrollX = window.scrollX;
        const scrollY = window.scrollY;

        if (grantees.length === 0) {
            grid.innerHTML = '';
            noResults?.classList.remove('hidden');
            // Restore scroll position
            window.scrollTo(scrollX, scrollY);
            return;
        }

        noResults?.classList.add('hidden');

        grid.innerHTML = grantees.map((grantee, index) => {
            const engagementRate = grantee.posts > 0 ? (grantee.engagement / grantee.posts).toFixed(1) : 0;
            const platformColor = getPlatformColor(grantee.topPlatform);
            const logoPath = getGranteeLogoPath(grantee.slug, grantee.logo);

            return `
                <a href="grantees/${grantee.slug}.html" class="grantee-card group block" style="animation-delay: ${index * 50}ms">
                    <div class="p-5">
                        <!-- Header with logo -->
                        <div class="flex items-start gap-3 mb-4">
                            <div class="flex-shrink-0 w-12 h-12 rounded-lg bg-gray-50 flex items-center justify-center overflow-hidden">
                                <img src="${logoPath}" alt="${grantee.name}"
                                     class="max-w-full max-h-full object-contain"
                                     loading="lazy"
                                     onerror="this.parentElement.innerHTML='<span class=\\'text-lg font-bold text-gray-400\\'>${grantee.name.charAt(0)}</span>'">
                            </div>
                            <div class="flex-1 min-w-0">
                                <h3 class="font-bold text-njcic-dark group-hover:text-njcic-teal transition-colors line-clamp-2">${grantee.name}</h3>
                            </div>
                            <div class="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center" style="background-color: ${platformColor}20; color: ${platformColor}">
                                ${getPlatformIcon(grantee.topPlatform)}
                            </div>
                        </div>

                        <!-- Stats -->
                        <div class="grid grid-cols-2 gap-3 mb-4">
                            <div class="bg-slate-50 rounded-lg p-3 text-center">
                                <div class="text-lg font-bold text-njcic-dark">${formatAbbreviated(grantee.posts)}</div>
                                <div class="text-xs text-gray-500">posts</div>
                            </div>
                            <div class="bg-slate-50 rounded-lg p-3 text-center">
                                <div class="text-lg font-bold text-njcic-teal">${formatAbbreviated(grantee.engagement)}</div>
                                <div class="text-xs text-gray-500">engagement</div>
                            </div>
                        </div>

                        <!-- Footer -->
                        <div class="flex items-center justify-between text-sm">
                            <div class="flex items-center gap-1.5 text-gray-500">
                                ${getPlatformIcon(grantee.topPlatform)}
                                <span class="capitalize">${grantee.topPlatform || 'N/A'}</span>
                            </div>
                            <div class="text-gray-500 font-medium flex items-center gap-1" title="Average engagement per post (likes, comments, shares, views)">
                                <svg class="w-3.5 h-3.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
                                </svg>
                                <span>${engagementRate}</span>
                                <span class="text-xs text-gray-400">avg/post</span>
                            </div>
                        </div>
                    </div>
                </a>
            `;
        }).join('');

        // Restore scroll position to prevent auto-scroll on DOM update
        window.scrollTo(scrollX, scrollY);
    }

    /**
     * Get platform color
     * @param {string} platform - Platform name
     * @returns {string} Hex color
     */
    function getPlatformColor(platform) {
        const colors = {
            tiktok: '#000000',
            bluesky: '#0085FF',
            instagram: '#E4405F',
            youtube: '#FF0000',
            twitter: '#1DA1F2',
            facebook: '#1877F2'
        };
        return colors[platform?.toLowerCase()] || '#6B7280';
    }

    /**
     * Initialize the rankings table
     */
    function initRankingsTable() {
        renderRankingsTable(dashboardData.grantees);
        document.getElementById('rankings-count').textContent = dashboardData.grantees.length;
    }

    /**
     * Render rankings table rows
     * @param {Array} grantees - Array of grantee objects
     */
    function renderRankingsTable(grantees) {
        const tbody = document.getElementById('rankings-tbody');
        if (!tbody) return;

        // Sort by engagement for ranking
        const sorted = [...grantees].sort((a, b) => b.engagement - a.engagement);

        tbody.innerHTML = sorted.map((grantee, index) => {
            const engagementRate = grantee.posts > 0 ? (grantee.engagement / grantee.posts).toFixed(1) : 0;
            const rank = index + 1;

            // Medal colors for top 3
            let rankDisplay = rank;
            let rankClass = 'text-gray-600';
            if (rank === 1) {
                rankDisplay = '1';
                rankClass = 'text-yellow-500 font-bold';
            } else if (rank === 2) {
                rankDisplay = '2';
                rankClass = 'text-gray-400 font-bold';
            } else if (rank === 3) {
                rankDisplay = '3';
                rankClass = 'text-amber-600 font-bold';
            }

            const rowClass = rank <= 3 ? 'ranking-row top-3' : 'ranking-row';

            return `
                <tr class="${rowClass} cursor-pointer" onclick="window.location.href='grantees/${grantee.slug}.html'">
                    <td class="px-6 py-4 whitespace-nowrap text-center">
                        <span class="${rankClass}">${rankDisplay}</span>
                    </td>
                    <td class="px-6 py-4">
                        <div class="font-medium text-njcic-dark hover:text-njcic-teal transition-colors">${grantee.name}</div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-right">
                        <span class="text-gray-900">${formatNumber(grantee.posts)}</span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-right">
                        <span class="font-semibold text-njcic-teal">${formatNumber(grantee.engagement)}</span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap hidden sm:table-cell">
                        <div class="flex items-center gap-1">
                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize" style="background-color: ${getPlatformColor(grantee.topPlatform)}20; color: ${getPlatformColor(grantee.topPlatform)}">
                                ${grantee.topPlatform || 'N/A'}
                            </span>
                            ${grantee.platformsScraped > 1 ? `<span class="text-xs text-gray-400">+${grantee.platformsScraped - 1}</span>` : ''}
                        </div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-right text-gray-600 hidden md:table-cell">
                        ${engagementRate}
                    </td>
                </tr>
            `;
        }).join('');
    }

    /**
     * Initialize search functionality
     */
    function initSearch() {
        const searchInput = document.getElementById('grantee-search');
        if (!searchInput) return;

        let debounceTimer;

        searchInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                currentFilters.search = e.target.value.toLowerCase().trim();
                applyFilters();
            }, CONFIG.searchDebounce);
        });

        // Clear search on escape
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                searchInput.value = '';
                currentFilters.search = '';
                applyFilters();
            }
        });
    }

    /**
     * Initialize filter controls
     */
    function initFilters() {
        const platformFilter = document.getElementById('platform-filter');
        const sortOption = document.getElementById('sort-option');

        if (platformFilter) {
            platformFilter.addEventListener('change', (e) => {
                currentFilters.platform = e.target.value;

                // Sync with button state
                const buttons = document.querySelectorAll('.platform-btn');
                buttons.forEach(btn => {
                    btn.classList.toggle('active', btn.dataset.platform === currentFilters.platform);
                });

                applyFilters();
            });
        }

        if (sortOption) {
            sortOption.addEventListener('change', (e) => {
                currentFilters.sort = e.target.value;
                applyFilters();
            });
        }
    }

    /**
     * Initialize table column sorting
     */
    function initTableSort() {
        const table = document.getElementById('rankings-table');
        if (!table) return;

        table.querySelectorAll('th[data-sort]').forEach(th => {
            th.addEventListener('click', () => {
                const column = th.dataset.sort;

                if (tableSort.column === column) {
                    tableSort.direction = tableSort.direction === 'asc' ? 'desc' : 'asc';
                } else {
                    tableSort.column = column;
                    tableSort.direction = column === 'name' ? 'asc' : 'desc';
                }

                sortAndRenderTable();
            });
        });
    }

    /**
     * Sort table data and re-render
     */
    function sortAndRenderTable() {
        const sorted = [...dashboardData.grantees].sort((a, b) => {
            let aVal, bVal;

            switch (tableSort.column) {
                case 'name':
                    aVal = a.name.toLowerCase();
                    bVal = b.name.toLowerCase();
                    break;
                case 'posts':
                    aVal = a.posts;
                    bVal = b.posts;
                    break;
                case 'engagement':
                    aVal = a.engagement;
                    bVal = b.engagement;
                    break;
                case 'rate':
                    aVal = a.posts > 0 ? a.engagement / a.posts : 0;
                    bVal = b.posts > 0 ? b.engagement / b.posts : 0;
                    break;
                case 'rank':
                default:
                    aVal = a.engagement;
                    bVal = b.engagement;
                    break;
            }

            if (typeof aVal === 'string') {
                return tableSort.direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
            }
            return tableSort.direction === 'asc' ? aVal - bVal : bVal - aVal;
        });

        renderRankingsTable(sorted);
    }

    /**
     * Apply current filters and re-render grid
     */
    function applyFilters() {
        let filtered = [...dashboardData.grantees];

        // Apply search filter
        if (currentFilters.search) {
            filtered = filtered.filter(g =>
                g.name.toLowerCase().includes(currentFilters.search)
            );
        }

        // Apply platform filter
        if (currentFilters.platform !== 'all') {
            filtered = filtered.filter(g =>
                g.topPlatform?.toLowerCase() === currentFilters.platform
            );
        }

        // Apply sorting
        const [sortField, sortDir] = currentFilters.sort.split('-');
        filtered.sort((a, b) => {
            let aVal, bVal;

            switch (sortField) {
                case 'engagement':
                    aVal = a.engagement;
                    bVal = b.engagement;
                    break;
                case 'posts':
                    aVal = a.posts;
                    bVal = b.posts;
                    break;
                case 'name':
                    aVal = a.name.toLowerCase();
                    bVal = b.name.toLowerCase();
                    break;
                default:
                    aVal = a.engagement;
                    bVal = b.engagement;
            }

            if (typeof aVal === 'string') {
                return sortDir === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
            }
            return sortDir === 'asc' ? aVal - bVal : bVal - aVal;
        });

        renderGranteesGrid(filtered);
    }

    /**
     * Update the "Last Updated" timestamp
     */
    function updateLastUpdated() {
        const elements = [
            document.getElementById('last-updated'),
            document.getElementById('footer-last-updated')
        ];

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

        const formatted = date.toLocaleDateString('en-US', options);
        elements.forEach(el => {
            if (el) el.textContent = formatted;
        });
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
            const newRawData = await loadData();
            rawData = newRawData;
            dashboardData = normalizeData(newRawData);

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
            if (charts.engagementByPlatform && window.NJCICCharts) {
                window.NJCICCharts.updateChartData(charts.engagementByPlatform, dashboardData.engagementByPlatform);
            }

            // Update grids and tables
            applyFilters();
            sortAndRenderTable();

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
        getData,
        applyFilters
    };

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
