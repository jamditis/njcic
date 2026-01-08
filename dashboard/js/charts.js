/**
 * NJCIC Dashboard - Chart Configurations
 * Chart.js chart configurations with NJCIC color scheme
 */

// NJCIC Color Palette
const NJCIC_COLORS = {
    teal: '#2dc8d2',
    dark: '#183642',
    light: '#e8f9fa',
    // Extended palette for charts
    palette: [
        '#2dc8d2', // NJCIC Teal
        '#183642', // NJCIC Dark
        '#4fd1c5', // Lighter Teal
        '#38b2ac', // Medium Teal
        '#285e61', // Dark Teal
        '#234e52', // Darker Teal
        '#1d4044', // Even Darker
        '#63b3ed', // Blue
        '#4299e1', // Medium Blue
        '#3182ce', // Darker Blue
    ],
    // Platform-specific colors
    platforms: {
        instagram: '#E4405F',
        tiktok: '#000000',
        youtube: '#FF0000',
        twitter: '#1DA1F2',
        facebook: '#1877F2',
        linkedin: '#0A66C2',
        threads: '#000000',
        bluesky: '#0085FF',
        default: '#6B7280'
    }
};

/**
 * Chart.js default configurations
 */
const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            display: false
        },
        tooltip: {
            backgroundColor: NJCIC_COLORS.dark,
            titleColor: '#ffffff',
            bodyColor: '#ffffff',
            borderColor: NJCIC_COLORS.teal,
            borderWidth: 1,
            cornerRadius: 8,
            padding: 12,
            titleFont: {
                family: 'Inter',
                size: 14,
                weight: '600'
            },
            bodyFont: {
                family: 'Inter',
                size: 13
            },
            callbacks: {
                label: function(context) {
                    let value = context.parsed || context.raw;
                    if (typeof value === 'object') {
                        value = value.y || value.x || 0;
                    }
                    return ' ' + formatNumber(value);
                }
            }
        }
    }
};

/**
 * Format large numbers with commas
 * @param {number} num - Number to format
 * @returns {string} Formatted number string
 */
function formatNumber(num) {
    if (num === null || num === undefined) return '0';
    return new Intl.NumberFormat('en-US').format(Math.round(num));
}

/**
 * Format large numbers with abbreviations (K, M, B)
 * @param {number} num - Number to format
 * @returns {string} Abbreviated number string
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
 * Get platform color
 * @param {string} platform - Platform name
 * @returns {string} Hex color code
 */
function getPlatformColor(platform) {
    const normalizedPlatform = platform.toLowerCase().replace(/\s+/g, '');
    return NJCIC_COLORS.platforms[normalizedPlatform] || NJCIC_COLORS.platforms.default;
}

/**
 * Create Platform Distribution Donut Chart
 * @param {HTMLCanvasElement} ctx - Canvas context
 * @param {Object} data - Platform data { platform: count }
 * @returns {Chart} Chart.js instance
 */
function createPlatformChart(ctx, data) {
    const labels = Object.keys(data);
    const values = Object.values(data);
    const colors = labels.map(label => getPlatformColor(label));

    // Create custom legend
    const legendContainer = document.getElementById('platform-legend');
    if (legendContainer) {
        legendContainer.innerHTML = labels.map((label, index) => `
            <div class="legend-item">
                <span class="legend-color" style="background-color: ${colors[index]}"></span>
                <span>${label}</span>
                <span class="font-semibold">${formatAbbreviated(values[index])}</span>
            </div>
        `).join('');
    }

    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderColor: '#ffffff',
                borderWidth: 3,
                hoverBorderWidth: 4,
                hoverOffset: 8
            }]
        },
        options: {
            ...chartDefaults,
            cutout: '65%',
            plugins: {
                ...chartDefaults.plugins,
                tooltip: {
                    ...chartDefaults.plugins.tooltip,
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.raw / total) * 100).toFixed(1);
                            return ` ${context.label}: ${formatNumber(context.raw)} (${percentage}%)`;
                        }
                    }
                }
            },
            animation: {
                animateRotate: true,
                animateScale: true,
                duration: 1000,
                easing: 'easeOutQuart'
            }
        }
    });
}

/**
 * Create Top Grantees Horizontal Bar Chart
 * @param {HTMLCanvasElement} ctx - Canvas context
 * @param {Array} data - Array of { name, engagement } objects
 * @returns {Chart} Chart.js instance
 */
function createGranteesChart(ctx, data) {
    // Sort by engagement and take top 10
    const sortedData = [...data]
        .sort((a, b) => b.engagement - a.engagement)
        .slice(0, 10);

    const labels = sortedData.map(item => truncateLabel(item.name, 25));
    const values = sortedData.map(item => item.engagement);

    // Create gradient colors
    const gradientColors = values.map((_, index) => {
        const opacity = 1 - (index * 0.07);
        return `rgba(45, 200, 210, ${opacity})`;
    });

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: gradientColors,
                borderColor: NJCIC_COLORS.teal,
                borderWidth: 0,
                borderRadius: 4,
                borderSkipped: false,
                barThickness: 'flex',
                maxBarThickness: 30
            }]
        },
        options: {
            ...chartDefaults,
            indexAxis: 'y',
            scales: {
                x: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        font: {
                            family: 'Inter',
                            size: 11
                        },
                        color: '#6B7280',
                        callback: function(value) {
                            return formatAbbreviated(value);
                        }
                    }
                },
                y: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            family: 'Inter',
                            size: 12
                        },
                        color: NJCIC_COLORS.dark,
                        padding: 8
                    }
                }
            },
            plugins: {
                ...chartDefaults.plugins,
                tooltip: {
                    ...chartDefaults.plugins.tooltip,
                    callbacks: {
                        title: function(context) {
                            // Get full name from original data
                            const index = context[0].dataIndex;
                            return sortedData[index].name;
                        },
                        label: function(context) {
                            return ` Engagement: ${formatNumber(context.raw)}`;
                        }
                    }
                }
            },
            animation: {
                duration: 1000,
                easing: 'easeOutQuart',
                delay: function(context) {
                    return context.dataIndex * 100;
                }
            }
        }
    });
}

/**
 * Truncate label text with ellipsis
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length
 * @returns {string} Truncated text
 */
function truncateLabel(text, maxLength) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength - 3) + '...';
}

/**
 * Update chart with new data
 * @param {Chart} chart - Chart.js instance
 * @param {Object|Array} newData - New data to display
 */
function updateChartData(chart, newData) {
    if (!chart) return;

    if (Array.isArray(newData)) {
        chart.data.labels = newData.map(item => item.label || item.name);
        chart.data.datasets[0].data = newData.map(item => item.value || item.engagement);
    } else {
        chart.data.labels = Object.keys(newData);
        chart.data.datasets[0].data = Object.values(newData);
    }

    chart.update('active');
}

/**
 * Destroy chart instance safely
 * @param {Chart} chart - Chart.js instance
 */
function destroyChart(chart) {
    if (chart && typeof chart.destroy === 'function') {
        chart.destroy();
    }
}

// Export functions for use in app.js
window.NJCICCharts = {
    COLORS: NJCIC_COLORS,
    formatNumber,
    formatAbbreviated,
    getPlatformColor,
    createPlatformChart,
    createGranteesChart,
    updateChartData,
    destroyChart
};
