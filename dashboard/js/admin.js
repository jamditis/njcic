/**
 * NJCIC Grantees Editor - Admin Interface
 *
 * This script provides functionality for:
 * - Password-protected access
 * - Loading and displaying grantee data
 * - CRUD operations for grantees
 * - Exporting changes as downloadable files
 */

// Configuration
const CONFIG = {
    // Simple password hash (SHA-256 of the password)
    // Default password: "njcic2024" - Change this hash for a different password
    // To generate a new hash, run in console: crypto.subtle.digest('SHA-256', new TextEncoder().encode('your-password')).then(h => console.log(Array.from(new Uint8Array(h)).map(b => b.toString(16).padStart(2, '0')).join('')))
    passwordHash: '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', // "admin"
    sessionKey: 'njcic_admin_session',
    dataPath: 'data/grantees/',
    dashboardDataPath: 'data/dashboard-data.json'
};

// State management
const state = {
    grantees: [],
    originalData: new Map(), // Store original data to track changes
    deletedSlugs: new Set(),
    newSlugs: new Set(),
    modifiedSlugs: new Set(),
    currentEditSlug: null
};

// DOM Elements
const elements = {
    loginScreen: document.getElementById('login-screen'),
    editorScreen: document.getElementById('editor-screen'),
    loginForm: document.getElementById('login-form'),
    loginError: document.getElementById('login-error'),
    passwordInput: document.getElementById('password'),
    granteesList: document.getElementById('grantees-list'),
    searchInput: document.getElementById('search-input'),
    filterStatus: document.getElementById('filter-status'),
    statTotal: document.getElementById('stat-total'),
    statModified: document.getElementById('stat-modified'),
    statNew: document.getElementById('stat-new'),
    statDeleted: document.getElementById('stat-deleted'),
    btnAddGrantee: document.getElementById('btn-add-grantee'),
    btnExport: document.getElementById('btn-export'),
    btnRebuild: document.getElementById('btn-rebuild'),
    btnLogout: document.getElementById('btn-logout'),
    modalGrantee: document.getElementById('modal-grantee'),
    modalRebuild: document.getElementById('modal-rebuild'),
    modalDelete: document.getElementById('modal-delete'),
    modalExport: document.getElementById('modal-export'),
    granteeForm: document.getElementById('grantee-form'),
    modalTitle: document.getElementById('modal-title'),
    toastContainer: document.getElementById('toast-container')
};

// ============================================
// Utility Functions
// ============================================

async function hashPassword(password) {
    const encoder = new TextEncoder();
    const data = encoder.encode(password);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

function slugify(text) {
    return text
        .toLowerCase()
        .replace(/[^\w\s-]/g, '')
        .replace(/[\s_]+/g, '-')
        .replace(/-+/g, '-')
        .trim()
        .replace(/^-+|-+$/g, '');
}

function formatCurrency(amount) {
    if (!amount) return '$0';
    if (amount >= 1000000) return `$${(amount / 1000000).toFixed(1)}M`;
    if (amount >= 1000) return `$${Math.round(amount / 1000)}K`;
    return `$${amount}`;
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    elements.toastContainer.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function debounce(func, wait) {
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

// ============================================
// Authentication
// ============================================

async function checkAuth() {
    const session = sessionStorage.getItem(CONFIG.sessionKey);
    if (session === 'authenticated') {
        showEditor();
        return true;
    }
    return false;
}

async function login(password) {
    const hash = await hashPassword(password);
    if (hash === CONFIG.passwordHash) {
        sessionStorage.setItem(CONFIG.sessionKey, 'authenticated');
        showEditor();
        return true;
    }
    return false;
}

function logout() {
    sessionStorage.removeItem(CONFIG.sessionKey);
    location.reload();
}

function showEditor() {
    elements.loginScreen.style.display = 'none';
    elements.editorScreen.style.display = 'block';
    loadGrantees();
}

// ============================================
// Data Loading
// ============================================

async function loadGrantees() {
    try {
        // First, load the dashboard data to get the list of grantees
        const dashboardResponse = await fetch(CONFIG.dashboardDataPath);
        const dashboardData = await dashboardResponse.json();

        // Get all grantee slugs from top grantees
        const slugs = dashboardData.topGrantees?.map(g => g.slug) || [];

        // Load each grantee's data
        const granteePromises = slugs.map(async (slug) => {
            try {
                const response = await fetch(`${CONFIG.dataPath}${slug}.json`);
                if (response.ok) {
                    return await response.json();
                }
            } catch (e) {
                console.warn(`Failed to load grantee: ${slug}`, e);
            }
            return null;
        });

        const granteeData = await Promise.all(granteePromises);
        state.grantees = granteeData.filter(g => g !== null);

        // Store original data for change tracking
        state.grantees.forEach(g => {
            state.originalData.set(g.slug, JSON.stringify(g));
        });

        renderGrantees();
        updateStats();

    } catch (error) {
        console.error('Failed to load grantees:', error);
        elements.granteesList.innerHTML = `
            <div class="text-center py-12 text-red-500">
                <p class="font-medium">Failed to load grantee data</p>
                <p class="text-sm mt-2">${error.message}</p>
            </div>
        `;
    }
}

// ============================================
// Rendering
// ============================================

function renderGrantees() {
    const searchTerm = elements.searchInput.value.toLowerCase();
    const statusFilter = elements.filterStatus.value;

    let filtered = state.grantees.filter(g => {
        // Search filter
        if (searchTerm && !g.name.toLowerCase().includes(searchTerm)) {
            return false;
        }

        // Status filter
        if (statusFilter === 'modified' && !state.modifiedSlugs.has(g.slug)) {
            return false;
        }
        if (statusFilter === 'new' && !state.newSlugs.has(g.slug)) {
            return false;
        }
        if (statusFilter === 'active' && g.grantInfo?.status !== 'active') {
            return false;
        }
        if (statusFilter === 'completed' && g.grantInfo?.status !== 'completed') {
            return false;
        }

        return true;
    });

    // Sort alphabetically
    filtered.sort((a, b) => a.name.localeCompare(b.name));

    if (filtered.length === 0) {
        elements.granteesList.innerHTML = `
            <div class="text-center py-12 text-gray-500">
                <p>No grantees found</p>
            </div>
        `;
        return;
    }

    elements.granteesList.innerHTML = filtered.map(grantee => {
        const isModified = state.modifiedSlugs.has(grantee.slug);
        const isNew = state.newSlugs.has(grantee.slug);
        const status = grantee.grantInfo?.status || 'unknown';
        const funding = formatCurrency(grantee.grantInfo?.totalFunding);
        const socialPlatforms = Object.keys(grantee.social || {}).filter(k => grantee.social[k]);

        return `
            <div class="grantee-card bg-white rounded-xl p-6 shadow-sm border ${isModified ? 'border-njcic-orange' : isNew ? 'border-green-400' : 'border-gray-200'}" data-slug="${grantee.slug}">
                <div class="flex items-start justify-between">
                    <div class="flex-1">
                        <div class="flex items-center gap-3 mb-2">
                            <h3 class="text-lg font-semibold text-njcic-dark">${escapeHtml(grantee.name)}</h3>
                            ${isNew ? '<span class="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full font-medium">New</span>' : ''}
                            ${isModified ? '<span class="px-2 py-0.5 bg-njcic-orange/10 text-njcic-orange text-xs rounded-full font-medium">Modified</span>' : ''}
                            <span class="px-2 py-0.5 ${status === 'active' ? 'bg-njcic-teal/10 text-njcic-teal' : 'bg-gray-100 text-gray-600'} text-xs rounded-full font-medium capitalize">${status}</span>
                        </div>

                        <div class="text-sm text-gray-500 space-y-1">
                            ${grantee.website ? `<p><a href="${escapeHtml(grantee.website)}" target="_blank" class="text-njcic-teal hover:underline">${escapeHtml(grantee.website)}</a></p>` : ''}
                            <p>
                                ${grantee.grantInfo?.city ? escapeHtml(grantee.grantInfo.city) : ''}${grantee.grantInfo?.city && grantee.grantInfo?.county ? ', ' : ''}${grantee.grantInfo?.county ? escapeHtml(grantee.grantInfo.county) : ''}
                                ${funding !== '$0' ? ` &bull; ${funding} total funding` : ''}
                            </p>
                        </div>

                        ${socialPlatforms.length > 0 ? `
                        <div class="flex gap-2 mt-3">
                            ${socialPlatforms.map(platform => `
                                <span class="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded capitalize">${platform}</span>
                            `).join('')}
                        </div>
                        ` : '<p class="text-sm text-gray-400 mt-3 italic">No social media accounts</p>'}
                    </div>

                    <div class="flex gap-2 ml-4">
                        <button
                            onclick="editGrantee('${grantee.slug}')"
                            class="p-2 text-gray-400 hover:text-njcic-teal hover:bg-gray-50 rounded-lg transition"
                            title="Edit"
                        >
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                            </svg>
                        </button>
                        <button
                            onclick="confirmDelete('${grantee.slug}')"
                            class="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition"
                            title="Delete"
                        >
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function updateStats() {
    elements.statTotal.textContent = state.grantees.length;
    elements.statModified.textContent = state.modifiedSlugs.size;
    elements.statNew.textContent = state.newSlugs.size;
    elements.statDeleted.textContent = state.deletedSlugs.size;
}

// ============================================
// CRUD Operations
// ============================================

function openAddGranteeModal() {
    state.currentEditSlug = null;
    elements.modalTitle.textContent = 'Add new grantee';
    elements.granteeForm.reset();
    elements.granteeForm.querySelector('[name="isNew"]').value = 'true';
    elements.granteeForm.querySelector('[name="slug"]').value = '';
    elements.modalGrantee.classList.remove('hidden');
}

function editGrantee(slug) {
    const grantee = state.grantees.find(g => g.slug === slug);
    if (!grantee) return;

    state.currentEditSlug = slug;
    elements.modalTitle.textContent = 'Edit grantee';

    const form = elements.granteeForm;
    form.querySelector('[name="name"]').value = grantee.name || '';
    form.querySelector('[name="website"]').value = grantee.website || '';
    form.querySelector('[name="city"]').value = grantee.grantInfo?.city || '';
    form.querySelector('[name="county"]').value = grantee.grantInfo?.county || '';
    form.querySelector('[name="status"]').value = grantee.grantInfo?.status || 'active';
    form.querySelector('[name="focusArea"]').value = grantee.grantInfo?.focusArea || '';
    form.querySelector('[name="totalFunding"]').value = grantee.grantInfo?.totalFunding || '';
    form.querySelector('[name="years"]').value = (grantee.grantInfo?.years || []).join(', ');

    // Get grant description from first grant if available
    const firstGrant = grantee.grantInfo?.grants?.[0];
    form.querySelector('[name="grantDescription"]').value = firstGrant?.description || '';

    // Social media
    form.querySelector('[name="social_twitter"]').value = grantee.social?.twitter || '';
    form.querySelector('[name="social_facebook"]').value = grantee.social?.facebook || '';
    form.querySelector('[name="social_instagram"]').value = grantee.social?.instagram || '';
    form.querySelector('[name="social_youtube"]').value = grantee.social?.youtube || '';
    form.querySelector('[name="social_tiktok"]').value = grantee.social?.tiktok || '';
    form.querySelector('[name="social_linkedin"]').value = grantee.social?.linkedin || '';
    form.querySelector('[name="social_threads"]').value = grantee.social?.threads || '';
    form.querySelector('[name="social_bluesky"]').value = grantee.social?.bluesky || '';

    form.querySelector('[name="slug"]').value = slug;
    form.querySelector('[name="isNew"]').value = state.newSlugs.has(slug) ? 'true' : 'false';

    elements.modalGrantee.classList.remove('hidden');
}

function saveGrantee(formData) {
    const isNew = formData.get('isNew') === 'true';
    const existingSlug = formData.get('slug');
    const name = formData.get('name').trim();
    const slug = existingSlug || slugify(name);

    // Build grantee object
    const years = formData.get('years')
        .split(',')
        .map(y => y.trim())
        .filter(y => y);

    const totalFunding = parseInt(formData.get('totalFunding')) || 0;

    const social = {};
    ['twitter', 'facebook', 'instagram', 'youtube', 'tiktok', 'linkedin', 'threads', 'bluesky'].forEach(platform => {
        const url = formData.get(`social_${platform}`)?.trim();
        if (url) social[platform] = url;
    });

    // Find existing grantee or create new base
    let grantee = state.grantees.find(g => g.slug === slug);

    if (!grantee) {
        // New grantee - create base structure
        grantee = {
            name: name,
            slug: slug,
            summary: {
                total_posts: 0,
                total_engagement: 0,
                total_followers: 0,
                platforms_active: Object.keys(social).length,
                engagement_rate: 0,
                last_updated: new Date().toISOString()
            },
            platform_breakdown: {},
            platforms: {},
            top_posts: [],
            overall_frequency: {
                posts_per_day: 0,
                posts_per_week: 0,
                date_range_days: 0,
                first_post: null,
                last_post: null
            },
            time_series: []
        };
        state.grantees.push(grantee);
        state.newSlugs.add(slug);
    }

    // Update grantee fields
    grantee.name = name;
    grantee.website = formData.get('website')?.trim() || null;
    grantee.social = social;

    // Update grant info
    grantee.grantInfo = {
        ...(grantee.grantInfo || {}),
        totalFunding: totalFunding,
        formattedFunding: formatCurrency(totalFunding),
        years: years,
        status: formData.get('status') || 'active',
        county: formData.get('county')?.trim() || null,
        city: formData.get('city')?.trim() || null,
        focusArea: formData.get('focusArea')?.trim() || null
    };

    // Update grants array if description provided
    const grantDescription = formData.get('grantDescription')?.trim();
    if (grantDescription) {
        if (!grantee.grantInfo.grants || grantee.grantInfo.grants.length === 0) {
            grantee.grantInfo.grants = [{
                id: 1,
                years: years,
                amount: totalFunding,
                description: grantDescription,
                focusArea: grantee.grantInfo.focusArea,
                status: grantee.grantInfo.status
            }];
        } else {
            grantee.grantInfo.grants[0].description = grantDescription;
        }
    }

    // Track modification
    if (!state.newSlugs.has(slug)) {
        const originalJson = state.originalData.get(slug);
        if (originalJson !== JSON.stringify(grantee)) {
            state.modifiedSlugs.add(slug);
        } else {
            state.modifiedSlugs.delete(slug);
        }
    }

    renderGrantees();
    updateStats();
    closeModal();
    showToast(isNew ? 'Grantee added successfully' : 'Grantee updated successfully', 'success');
}

function confirmDelete(slug) {
    const grantee = state.grantees.find(g => g.slug === slug);
    if (!grantee) return;

    state.currentEditSlug = slug;
    document.getElementById('delete-message').textContent =
        `Are you sure you want to delete "${grantee.name}"? This action will be included in the next export.`;
    elements.modalDelete.classList.remove('hidden');
}

function deleteGrantee() {
    const slug = state.currentEditSlug;
    if (!slug) return;

    // Remove from grantees array
    state.grantees = state.grantees.filter(g => g.slug !== slug);

    // Track deletion (only if it wasn't a new grantee)
    if (state.newSlugs.has(slug)) {
        state.newSlugs.delete(slug);
    } else {
        state.deletedSlugs.add(slug);
        state.modifiedSlugs.delete(slug);
    }

    renderGrantees();
    updateStats();
    closeModal();
    showToast('Grantee deleted', 'success');
}

// ============================================
// Export Functions
// ============================================

function openExportModal() {
    document.getElementById('export-modified').textContent = state.modifiedSlugs.size;
    document.getElementById('export-new').textContent = state.newSlugs.size;
    document.getElementById('export-deleted').textContent = state.deletedSlugs.size;
    elements.modalExport.classList.remove('hidden');
}

async function exportAllGrantees() {
    try {
        const zip = await createZip(state.grantees);
        downloadBlob(zip, 'njcic-grantees-all.zip');
        showToast('Export complete!', 'success');
    } catch (error) {
        console.error('Export failed:', error);
        showToast('Export failed: ' + error.message, 'error');
    }
}

async function exportChangesOnly() {
    const changedGrantees = state.grantees.filter(g =>
        state.modifiedSlugs.has(g.slug) || state.newSlugs.has(g.slug)
    );

    if (changedGrantees.length === 0 && state.deletedSlugs.size === 0) {
        showToast('No changes to export', 'info');
        return;
    }

    try {
        const zip = await createZip(changedGrantees, true);
        downloadBlob(zip, 'njcic-grantees-changes.zip');
        showToast('Export complete!', 'success');
    } catch (error) {
        console.error('Export failed:', error);
        showToast('Export failed: ' + error.message, 'error');
    }
}

async function createZip(grantees, includeDeleteList = false) {
    // Simple ZIP file creation without external library
    // For a production system, you'd want to use JSZip or similar

    // For now, create individual JSON files as a downloadable archive
    const files = [];

    grantees.forEach(grantee => {
        const json = JSON.stringify(grantee, null, 2);
        files.push({
            name: `${grantee.slug}.json`,
            content: json
        });
    });

    if (includeDeleteList && state.deletedSlugs.size > 0) {
        files.push({
            name: '_deleted.txt',
            content: Array.from(state.deletedSlugs).join('\n')
        });
    }

    // Create a simple combined JSON for easy processing
    const combinedData = {
        exportDate: new Date().toISOString(),
        grantees: grantees,
        deleted: Array.from(state.deletedSlugs),
        modified: Array.from(state.modifiedSlugs),
        new: Array.from(state.newSlugs)
    };

    files.push({
        name: '_export-manifest.json',
        content: JSON.stringify(combinedData, null, 2)
    });

    // For simplicity, we'll just download a JSON file with all data
    // A real implementation would use JSZip
    return new Blob([JSON.stringify(combinedData, null, 2)], { type: 'application/json' });
}

function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename.replace('.zip', '.json'); // Using JSON instead of ZIP for simplicity
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ============================================
// Modal Management
// ============================================

function closeModal() {
    elements.modalGrantee.classList.add('hidden');
    elements.modalDelete.classList.add('hidden');
    elements.modalRebuild.classList.add('hidden');
    elements.modalExport.classList.add('hidden');
    state.currentEditSlug = null;
}

// ============================================
// Event Listeners
// ============================================

// Login form
elements.loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const password = elements.passwordInput.value;

    if (await login(password)) {
        elements.loginError.classList.add('hidden');
    } else {
        elements.loginError.classList.remove('hidden');
        elements.passwordInput.value = '';
        elements.passwordInput.focus();
    }
});

// Grantee form
elements.granteeForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const formData = new FormData(elements.granteeForm);
    saveGrantee(formData);
});

// Search and filter
elements.searchInput.addEventListener('input', debounce(() => {
    renderGrantees();
}, 300));

elements.filterStatus.addEventListener('change', () => {
    renderGrantees();
});

// Buttons
elements.btnAddGrantee.addEventListener('click', openAddGranteeModal);
elements.btnExport.addEventListener('click', openExportModal);
elements.btnRebuild.addEventListener('click', () => {
    elements.modalRebuild.classList.remove('hidden');
});
elements.btnLogout.addEventListener('click', logout);

// Modal close buttons
document.getElementById('modal-close')?.addEventListener('click', closeModal);
document.getElementById('btn-cancel')?.addEventListener('click', closeModal);
document.getElementById('btn-close-rebuild')?.addEventListener('click', closeModal);
document.getElementById('btn-cancel-delete')?.addEventListener('click', closeModal);
document.getElementById('btn-confirm-delete')?.addEventListener('click', deleteGrantee);
document.getElementById('btn-close-export')?.addEventListener('click', closeModal);
document.getElementById('btn-export-all')?.addEventListener('click', exportAllGrantees);
document.getElementById('btn-export-changes')?.addEventListener('click', exportChangesOnly);

// Close modals on backdrop click
[elements.modalGrantee, elements.modalDelete, elements.modalRebuild, elements.modalExport].forEach(modal => {
    modal?.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });
});

// Escape key to close modals
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});

// Make functions available globally for onclick handlers
window.editGrantee = editGrantee;
window.confirmDelete = confirmDelete;

// ============================================
// Initialize
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
});
