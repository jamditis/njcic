/**
 * NJCIC Dashboard - Rankings Page Logic
 * Handles data loading, sorting, filtering, comparison tool, and chart rendering
 */

(function() {
    'use strict';

    // Configuration
    const CONFIG = {
        dataPath: 'data/dashboard-data.json',
        rankingsPath: 'data/rankings.json',
        retryAttempts: 3,
        retryDelay: 1000
    };

    // State
    let dashboardData = null;
    let rankingsData = null;
    let grantees = [];
    let filteredGrantees = [];
    let currentSort = { column: 'engagement', direction: 'desc' };
    let selectedPlatform = null;
    let comparisonChart = null;

    /**
     * Initialize the rankings page
     */
    async function init() {
        try {
            // Load data
            await loadAllData();

            // Process grantees data
            processGranteesData();

            // Hide loading, show content
            hideLoading();

            // Initialize components
            initStats();
            initLeaderboards();
            initPlatformTabs();
            initRankingsTable();
            initComparisonTool();
            updateLastUpdated();

            // Set up event listeners
            setupEventListeners();

            console.log('NJCIC Rankings page initialized successfully');
        } catch (error) {
            console.error('Rankings page initialization failed:', error);
            showError(error.message);
        }
    }

    /**
     * Load all required data files
     */
    async function loadAllData() {
        const cacheBuster = `?v=${Date.now()}`;

        // Try to load dashboard data
        try {
            const response = await fetch(CONFIG.dataPath + cacheBuster);
            if (response.ok) {
                dashboardData = await response.json();
            }
        } catch (e) {
            console.warn('Could not load dashboard data:', e);
        }

        // Try to load rankings data (optional)
        try {
            const response = await fetch(CONFIG.rankingsPath + cacheBuster);
            if (response.ok) {
                rankingsData = await response.json();
            }
        } catch (e) {
            console.log('Rankings data not available, using dashboard data');
        }

        // If no data loaded, use sample data
        if (!dashboardData && !rankingsData) {
            console.log('Using sample data for demonstration');
            dashboardData = getSampleData();
        }
    }

    /**
     * Process grantees data from available sources
     */
    function processGranteesData() {
        // Use rankings.json if available with by_engagement format
        if (rankingsData && rankingsData.by_engagement) {
            // Build grantees from rankings data - need to merge with dashboard data for full info
            const engagementMap = {};
            const postsMap = {};
            const rateMap = {};

            rankingsData.by_engagement.forEach(g => { engagementMap[g.slug] = g.value; });
            if (rankingsData.by_posts) {
                rankingsData.by_posts.forEach(g => { postsMap[g.slug] = g.value; });
            }
            if (rankingsData.by_engagement_rate) {
                rankingsData.by_engagement_rate.forEach(g => { rateMap[g.slug] = g.value; });
            }

            grantees = rankingsData.by_engagement.map((g, index) => ({
                rank: index + 1,
                name: g.name,
                slug: g.slug,
                posts: postsMap[g.slug] || 0,
                engagement: g.value || 0,
                engagementRate: rateMap[g.slug] || (postsMap[g.slug] > 0 ? (g.value / postsMap[g.slug]).toFixed(1) : 0),
                platforms: 1,
                bestPlatform: 'unknown',
                platformData: {}
            }));

            // Merge with dashboard data for additional info
            if (dashboardData && dashboardData.topGrantees) {
                const dashboardMap = {};
                dashboardData.topGrantees.forEach(g => {
                    dashboardMap[g.slug] = g;
                });
                grantees.forEach(g => {
                    const dash = dashboardMap[g.slug];
                    if (dash) {
                        g.platforms = dash.platformsScraped || 1;
                        g.bestPlatform = dash.topPlatform || 'unknown';
                    }
                });
            }
        } else if (dashboardData && dashboardData.topGrantees) {
            grantees = dashboardData.topGrantees.map((g, index) => ({
                rank: index + 1,
                name: g.name,
                slug: g.slug,
                posts: g.posts || 0,
                engagement: g.engagement || 0,
                engagementRate: g.posts > 0 ? (g.engagement / g.posts).toFixed(1) : 0,
                platforms: g.platformsScraped || 1,
                bestPlatform: g.topPlatform || 'unknown',
                platformData: g.platformData || {}
            }));
        } else if (dashboardData && dashboardData.grantees) {
            grantees = dashboardData.grantees.map((g, index) => ({
                rank: index + 1,
                name: g.name,
                slug: g.slug,
                posts: g.posts || 0,
                engagement: g.engagement || 0,
                engagementRate: g.posts > 0 ? (g.engagement / g.posts).toFixed(1) : 0,
                platforms: g.platforms || 1,
                bestPlatform: g.bestPlatform || 'unknown',
                platformData: g.platformData || {}
            }));
        }

        // Sort by engagement initially
        grantees.sort((a, b) => b.engagement - a.engagement);

        // Reassign ranks after sorting
        grantees.forEach((g, index) => {
            g.rank = index + 1;
        });

        filteredGrantees = [...grantees];
    }

    /**
     * Get sample data for demonstration
     */
    function getSampleData() {
        return {
            summary: {
                totalGrantees: 14,
                totalPosts: 371,
                totalEngagement: 130252,
                platformsTracked: 2
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
                { name: "Slice of Culture - Saint Peter's University", posts: 26, engagement: 1791, topPlatform: "tiktok", platformsScraped: 1 },
                { name: "Daily Targum", posts: 26, engagement: 1609, topPlatform: "tiktok", platformsScraped: 1 },
                { name: "South Jersey Climate News Project", posts: 38, engagement: 847, topPlatform: "tiktok", platformsScraped: 2 },
                { name: "Inside Climate News", posts: 25, engagement: 675, topPlatform: "bluesky", platformsScraped: 1 },
                { name: "Clinton Hill Community Action", posts: 26, engagement: 301, topPlatform: "tiktok", platformsScraped: 1 },
                { name: "Chalkbeat Newark (Civic News Company)", posts: 25, engagement: 113, topPlatform: "bluesky", platformsScraped: 1 },
                { name: "Public Square Amplified", posts: 25, engagement: 58, topPlatform: "bluesky", platformsScraped: 1 },
                { name: "Montclair Local Nonprofit News", posts: 25, engagement: 38, topPlatform: "bluesky", platformsScraped: 1 }
            ],
            metadata: {
                generatedAt: new Date().toISOString()
            }
        };
    }

    /**
     * Initialize aggregate statistics
     */
    function initStats() {
        const sourceData = dashboardData || rankingsData;

        // Calculate stats
        const totalEngagement = grantees.reduce((sum, g) => sum + g.engagement, 0);
        const avgEngagement = grantees.length > 0 ? Math.round(totalEngagement / grantees.length) : 0;

        // Calculate median posts
        const sortedPosts = grantees.map(g => g.posts).sort((a, b) => a - b);
        const medianPosts = sortedPosts.length > 0
            ? sortedPosts[Math.floor(sortedPosts.length / 2)]
            : 0;

        // Platform count
        const platformsTracked = sourceData?.summary?.platformsTracked
            || sourceData?.summary?.platformsMonitored
            || Object.keys(sourceData?.platforms || {}).length;

        // Estimated total reach (engagement * multiplier)
        const totalReach = totalEngagement * 3; // Conservative estimate

        // Update UI
        document.getElementById('stat-avg-engagement').textContent = formatNumber(avgEngagement);
        document.getElementById('stat-median-posts').textContent = formatNumber(medianPosts);
        document.getElementById('stat-platform-adoption').textContent = platformsTracked;
        document.getElementById('stat-total-reach').textContent = formatAbbreviated(totalReach);
    }

    /**
     * Initialize leaderboard sections
     */
    function initLeaderboards() {
        // Top by Engagement
        const topEngagement = [...grantees].sort((a, b) => b.engagement - a.engagement).slice(0, 5);
        renderLeaderboard('leaderboard-engagement', topEngagement, 'engagement');

        // Top by Posts
        const topPosts = [...grantees].sort((a, b) => b.posts - a.posts).slice(0, 5);
        renderLeaderboard('leaderboard-posts', topPosts, 'posts');

        // Top by Engagement Rate
        const topRate = [...grantees]
            .filter(g => g.posts > 0)
            .sort((a, b) => parseFloat(b.engagementRate) - parseFloat(a.engagementRate))
            .slice(0, 5);
        renderLeaderboard('leaderboard-rate', topRate, 'rate');
    }

    /**
     * Render a leaderboard
     */
    function renderLeaderboard(containerId, items, metric) {
        const container = document.getElementById(containerId);
        if (!container) return;

        container.innerHTML = items.map((item, index) => {
            const rankClass = index === 0 ? 'gold' : index === 1 ? 'silver' : index === 2 ? 'bronze' : 'default';
            let value;

            switch (metric) {
                case 'engagement':
                    value = formatAbbreviated(item.engagement);
                    break;
                case 'posts':
                    value = formatNumber(item.posts);
                    break;
                case 'rate':
                    value = parseFloat(item.engagementRate).toFixed(1) + '/post';
                    break;
                default:
                    value = '';
            }

            return `
                <div class="leaderboard-item">
                    <div class="leaderboard-rank ${rankClass}">${index + 1}</div>
                    <div class="flex-1 min-w-0">
                        <div class="font-medium text-njcic-dark truncate">${escapeHtml(item.name)}</div>
                        <div class="text-sm text-gray-500">${value}</div>
                    </div>
                    <span class="platform-badge ${item.bestPlatform}">${item.bestPlatform}</span>
                </div>
            `;
        }).join('');
    }

    /**
     * Initialize platform tabs
     */
    function initPlatformTabs() {
        const sourceData = dashboardData || rankingsData;
        const platforms = Object.keys(sourceData?.platforms || {});

        const tabsContainer = document.getElementById('platform-tabs');
        if (!tabsContainer || platforms.length === 0) return;

        tabsContainer.innerHTML = platforms.map((platform, index) => `
            <button class="platform-tab ${index === 0 ? 'active' : ''}" data-platform="${platform}">
                ${capitalizeFirst(platform)}
            </button>
        `).join('');

        // Set initial platform
        selectedPlatform = platforms[0];
        updatePlatformLeaderboard(selectedPlatform);

        // Add click handlers
        tabsContainer.querySelectorAll('.platform-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                tabsContainer.querySelectorAll('.platform-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                selectedPlatform = tab.dataset.platform;
                updatePlatformLeaderboard(selectedPlatform);
            });
        });
    }

    /**
     * Update platform-specific leaderboard
     */
    function updatePlatformLeaderboard(platform) {
        const container = document.getElementById('platform-leaderboard-list');
        if (!container) return;

        // Filter grantees by platform
        const platformGrantees = grantees
            .filter(g => g.bestPlatform.toLowerCase() === platform.toLowerCase())
            .sort((a, b) => b.engagement - a.engagement);

        if (platformGrantees.length === 0) {
            container.innerHTML = `
                <div class="col-span-2 text-center py-8 text-gray-500">
                    No grantees tracked on ${capitalizeFirst(platform)} yet.
                </div>
            `;
            return;
        }

        container.innerHTML = platformGrantees.map((g, index) => `
            <div class="bg-white rounded-xl p-4 flex items-center gap-4">
                <div class="leaderboard-rank ${index === 0 ? 'gold' : index === 1 ? 'silver' : index === 2 ? 'bronze' : 'default'}">
                    ${index + 1}
                </div>
                <div class="flex-1 min-w-0">
                    <div class="font-medium text-njcic-dark truncate">${escapeHtml(g.name)}</div>
                    <div class="text-sm text-gray-500">
                        ${formatNumber(g.posts)} posts | ${formatAbbreviated(g.engagement)} engagement
                    </div>
                </div>
            </div>
        `).join('');
    }

    /**
     * Initialize rankings table
     */
    function initRankingsTable() {
        renderTable();
        setupTableSorting();
    }

    /**
     * Render the rankings table
     */
    function renderTable() {
        const tbody = document.getElementById('rankings-tbody');
        if (!tbody) return;

        tbody.innerHTML = filteredGrantees.map(g => `
            <tr class="hover:bg-njcic-light transition-colors">
                <td class="px-4 py-3 text-sm font-semibold text-njcic-teal">#${g.rank}</td>
                <td class="px-4 py-3">
                    <div class="font-medium text-njcic-dark">${escapeHtml(g.name)}</div>
                </td>
                <td class="px-4 py-3 text-sm text-gray-700">${formatNumber(g.posts)}</td>
                <td class="px-4 py-3 text-sm font-semibold text-gray-900">${formatNumber(g.engagement)}</td>
                <td class="px-4 py-3 text-sm text-gray-700">${g.engagementRate}/post</td>
                <td class="px-4 py-3 text-sm text-gray-700">${g.platforms}</td>
                <td class="px-4 py-3">
                    <span class="platform-badge ${g.bestPlatform}">${capitalizeFirst(g.bestPlatform)}</span>
                </td>
            </tr>
        `).join('');

        // Update table info
        const tableInfo = document.getElementById('table-info');
        if (tableInfo) {
            if (filteredGrantees.length === grantees.length) {
                tableInfo.textContent = `Showing all ${grantees.length} grantees`;
            } else {
                tableInfo.textContent = `Showing ${filteredGrantees.length} of ${grantees.length} grantees`;
            }
        }
    }

    /**
     * Set up table column sorting
     */
    function setupTableSorting() {
        const headers = document.querySelectorAll('#rankings-table th[data-sort]');
        headers.forEach(header => {
            header.addEventListener('click', () => {
                const column = header.dataset.sort;

                // Toggle direction if same column
                if (currentSort.column === column) {
                    currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
                } else {
                    currentSort.column = column;
                    currentSort.direction = 'desc';
                }

                // Update header classes
                headers.forEach(h => h.classList.remove('sorted-asc', 'sorted-desc'));
                header.classList.add(`sorted-${currentSort.direction}`);

                // Sort data
                sortGrantees(column, currentSort.direction);
                renderTable();
            });
        });
    }

    /**
     * Sort grantees by column
     */
    function sortGrantees(column, direction) {
        const modifier = direction === 'asc' ? 1 : -1;

        filteredGrantees.sort((a, b) => {
            let aVal, bVal;

            switch (column) {
                case 'rank':
                    aVal = a.rank;
                    bVal = b.rank;
                    break;
                case 'name':
                    aVal = a.name.toLowerCase();
                    bVal = b.name.toLowerCase();
                    return aVal.localeCompare(bVal) * modifier;
                case 'posts':
                    aVal = a.posts;
                    bVal = b.posts;
                    break;
                case 'engagement':
                    aVal = a.engagement;
                    bVal = b.engagement;
                    break;
                case 'rate':
                    aVal = parseFloat(a.engagementRate);
                    bVal = parseFloat(b.engagementRate);
                    break;
                case 'platforms':
                    aVal = a.platforms;
                    bVal = b.platforms;
                    break;
                case 'bestPlatform':
                    aVal = a.bestPlatform.toLowerCase();
                    bVal = b.bestPlatform.toLowerCase();
                    return aVal.localeCompare(bVal) * modifier;
                default:
                    return 0;
            }

            return (aVal - bVal) * modifier;
        });
    }

    /**
     * Filter grantees by search term
     */
    function filterGrantees(searchTerm) {
        const term = searchTerm.toLowerCase().trim();

        if (!term) {
            filteredGrantees = [...grantees];
        } else {
            filteredGrantees = grantees.filter(g =>
                g.name.toLowerCase().includes(term) ||
                g.bestPlatform.toLowerCase().includes(term)
            );
        }

        renderTable();
    }

    /**
     * Initialize comparison tool
     */
    function initComparisonTool() {
        const selects = ['compare-select-1', 'compare-select-2', 'compare-select-3'];

        selects.forEach(selectId => {
            const select = document.getElementById(selectId);
            if (!select) return;

            // Populate options
            const options = grantees.map(g =>
                `<option value="${escapeHtml(g.name)}">${escapeHtml(g.name)}</option>`
            ).join('');

            const defaultOption = selectId === 'compare-select-3'
                ? '<option value="">Select Grantee 3 (optional)</option>'
                : `<option value="">Select Grantee ${selectId.slice(-1)}</option>`;

            select.innerHTML = defaultOption + options;
        });
    }

    /**
     * Update comparison view
     */
    function updateComparison() {
        const select1 = document.getElementById('compare-select-1');
        const select2 = document.getElementById('compare-select-2');
        const select3 = document.getElementById('compare-select-3');

        const selected = [
            grantees.find(g => g.name === select1?.value),
            grantees.find(g => g.name === select2?.value),
            grantees.find(g => g.name === select3?.value)
        ].filter(Boolean);

        if (selected.length < 2) {
            alert('Please select at least 2 grantees to compare.');
            return;
        }

        renderComparisonCards(selected);
        renderComparisonChart(selected);
    }

    /**
     * Clear comparison selection
     */
    function clearComparison() {
        document.getElementById('compare-select-1').value = '';
        document.getElementById('compare-select-2').value = '';
        document.getElementById('compare-select-3').value = '';

        document.getElementById('comparison-cards').innerHTML = `
            <div class="comparison-card flex items-center justify-center min-h-[300px] text-gray-400">
                <p>Select grantees above to compare</p>
            </div>
        `;

        document.getElementById('comparison-chart-container').classList.add('hidden');

        if (comparisonChart) {
            comparisonChart.destroy();
            comparisonChart = null;
        }
    }

    /**
     * Render comparison cards
     */
    function renderComparisonCards(granteeList) {
        const container = document.getElementById('comparison-cards');
        if (!container) return;

        container.innerHTML = granteeList.map((g, index) => `
            <div class="comparison-card selected">
                <div class="flex items-center justify-between mb-4">
                    <span class="text-sm font-medium text-gray-500">Grantee ${index + 1}</span>
                    <span class="platform-badge ${g.bestPlatform}">${capitalizeFirst(g.bestPlatform)}</span>
                </div>
                <h3 class="text-lg font-bold text-njcic-dark mb-4">${escapeHtml(g.name)}</h3>
                <div class="space-y-3">
                    <div class="flex justify-between">
                        <span class="text-gray-600">Rank</span>
                        <span class="font-semibold text-njcic-teal">#${g.rank}</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-gray-600">Total Posts</span>
                        <span class="font-semibold">${formatNumber(g.posts)}</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-gray-600">Total Engagement</span>
                        <span class="font-semibold">${formatNumber(g.engagement)}</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-gray-600">Engagement Rate</span>
                        <span class="font-semibold">${g.engagementRate}/post</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-gray-600">Platforms</span>
                        <span class="font-semibold">${g.platforms}</span>
                    </div>
                </div>
            </div>
        `).join('');
    }

    /**
     * Render comparison chart
     */
    function renderComparisonChart(granteeList) {
        const container = document.getElementById('comparison-chart-container');
        const canvas = document.getElementById('comparison-chart');
        if (!container || !canvas) return;

        container.classList.remove('hidden');

        // Destroy existing chart
        if (comparisonChart) {
            comparisonChart.destroy();
        }

        const ctx = canvas.getContext('2d');
        const labels = granteeList.map(g => truncateLabel(g.name, 20));

        const colors = ['#2dc8d2', '#183642', '#4fd1c5'];

        comparisonChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Total Posts', 'Total Engagement', 'Engagement Rate'],
                datasets: granteeList.map((g, index) => ({
                    label: truncateLabel(g.name, 15),
                    data: [
                        g.posts,
                        g.engagement,
                        parseFloat(g.engagementRate)
                    ],
                    backgroundColor: colors[index % colors.length],
                    borderRadius: 4
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            font: {
                                family: 'Inter',
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: '#183642',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        borderColor: '#2dc8d2',
                        borderWidth: 1,
                        cornerRadius: 8,
                        padding: 12
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            font: {
                                family: 'Inter',
                                size: 12
                            }
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            font: {
                                family: 'Inter',
                                size: 11
                            },
                            callback: function(value) {
                                return formatAbbreviated(value);
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * Set up event listeners
     */
    function setupEventListeners() {
        // Search input
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                filterGrantees(e.target.value);
            });
        }
    }

    /**
     * Update the "Last Updated" timestamp
     */
    function updateLastUpdated() {
        const element = document.getElementById('last-updated');
        if (!element) return;

        const sourceData = dashboardData || rankingsData;
        let date;

        if (sourceData?.summary?.lastUpdated) {
            date = new Date(sourceData.summary.lastUpdated);
        } else if (sourceData?.metadata?.generatedAt) {
            date = new Date(sourceData.metadata.generatedAt);
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
     * Format numbers with abbreviations (K, M, B)
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
     * Capitalize first letter
     */
    function capitalizeFirst(str) {
        if (!str) return '';
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    /**
     * Truncate label text
     */
    function truncateLabel(text, maxLength) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength - 3) + '...';
    }

    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Export public API
    window.NJCICRankings = {
        updateComparison,
        clearComparison,
        filterGrantees,
        getData: () => ({ grantees, dashboardData, rankingsData })
    };

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
