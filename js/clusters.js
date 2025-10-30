// API Base URL - Update this to match your environment
const API_BASE_URL = 'http://localhost:8000';

// Authentication functions
function checkAuth() {
    const token = localStorage.getItem('ansible_token');
    const username = localStorage.getItem('ansible_username');
    
    if (token && username) {
        document.getElementById('loginPrompt')?.classList.add('hidden');
        document.getElementById('dashboardContent')?.classList.remove('hidden');
        document.getElementById('usernameDisplay')?.textContent = username;
        return token;
    } else {
        document.getElementById('loginPrompt')?.classList.remove('hidden');
        document.getElementById('dashboardContent')?.classList.add('hidden');
        return null;
    }
}

function goToLogin() {
    window.location.href = 'http://localhost:8000/login';
}

function logout() {
    localStorage.removeItem('ansible_token');
    localStorage.removeItem('ansible_username');
    window.location.href = 'clusters-dashboard.html';
}

// API Helper Functions
async function apiCall(endpoint, options = {}) {
    const token = localStorage.getItem('ansible_token');
    if (!token) {
        throw new Error('Not authenticated');
    }

    const url = `${API_BASE_URL}${endpoint}`;
    const config = {
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            ...options.headers
        },
        ...options
    };

    const response = await fetch(url, config);
    
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }

    return await response.json();
}

async function apiGet(endpoint) {
    return await apiCall(endpoint);
}

async function apiPost(endpoint, data) {
    return await apiCall(endpoint, {
        method: 'POST',
        body: JSON.stringify(data)
    });
}

async function apiPut(endpoint, data) {
    return await apiCall(endpoint, {
        method: 'PUT',
        body: JSON.stringify(data)
    });
}

async function apiDelete(endpoint) {
    return await apiCall(endpoint, {
        method: 'DELETE'
    });
}

// UI Helper Functions
function showLoading() {
    document.getElementById('loadingState')?.classList.remove('hidden');
    document.getElementById('errorState')?.classList.add('hidden');
    document.getElementById('clustersGrid')?.classList.add('hidden');
    document.getElementById('clusterDetails')?.classList.add('hidden');
}

function showError(message) {
    document.getElementById('loadingState')?.classList.add('hidden');
    document.getElementById('errorState')?.classList.remove('hidden');
    document.getElementById('errorMessage').textContent = message;
    document.getElementById('clustersGrid')?.classList.add('hidden');
    document.getElementById('clusterDetails')?.classList.add('hidden');
}

function showContent() {
    document.getElementById('loadingState')?.classList.add('hidden');
    document.getElementById('errorState')?.classList.add('hidden');
    document.getElementById('clustersGrid')?.classList.remove('hidden');
    document.getElementById('clusterDetails')?.classList.remove('hidden');
}

function hideError() {
    document.getElementById('errorState')?.classList.add('hidden');
}

function showNotification(message, type = 'info') {
    // Remove existing notification
    const existingNotification = document.querySelector('.notification');
    if (existingNotification) {
        existingNotification.remove();
    }

    // Create new notification
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    // Auto remove after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Cluster Management Functions (for dashboard)
async function loadClusters() {
    showLoading();
    hideError();

    try {
        const clusters = await apiGet('/api/clusters');
        displayClusters(clusters);
        showContent();
    } catch (error) {
        showError(`Failed to load clusters: ${error.message}`);
    }
}

function displayClusters(clusters) {
    const clustersList = document.getElementById('clustersList');
    const emptyState = document.getElementById('emptyState');

    if (!clusters || clusters.length === 0) {
        clustersList.innerHTML = '';
        emptyState.classList.remove('hidden');
        return;
    }

    emptyState.classList.add('hidden');

    const clustersHtml = clusters.map(cluster => `
        <div class="cluster-card" onclick="viewClusterDetails('${cluster.id}')">
            <div class="cluster-card-header">
                <div>
                    <div class="cluster-name">${cluster.name}</div>
                    <div class="cluster-description">${cluster.description || 'No description'}</div>
                </div>
                <span class="status-badge status-${cluster.status.toLowerCase()}">${cluster.status}</span>
            </div>
            
            <div class="cluster-meta">
                <div class="meta-item">
                    <label>Type:</label>
                    <span>${cluster.cluster_type}</span>
                </div>
                <div class="meta-item">
                    <label>Auth:</label>
                    <span>${cluster.auth_type || 'kubeconfig'}</span>
                </div>
                <div class="meta-item">
                    <label>Masters:</label>
                    <span>${cluster.master_nodes}</span>
                </div>
                <div class="meta-item">
                    <label>Workers:</label>
                    <span>${cluster.worker_nodes}</span>
                </div>
            </div>

            <div class="cluster-actions">
                <button onclick="event.stopPropagation(); viewClusterDetails('${cluster.id}')" 
                        class="btn-primary" style="width: 100%">
                    View Details
                </button>
            </div>
        </div>
    `).join('');

    clustersList.innerHTML = clustersHtml;
}

function viewClusterDetails(clusterId) {
    window.location.href = `cluster-details.html?id=${clusterId}`;
}
