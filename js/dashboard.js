// API Configuration
const API_BASE_URL = 'http://localhost:8000';

// Authentication and Navigation
function checkAuth() {
    const token = localStorage.getItem('ansible_token');
    const username = localStorage.getItem('ansible_username');
    
    console.log('🔐 Auth Check - Token:', token ? 'Exists' : 'Missing');
    console.log('🔐 Auth Check - Username:', username);
    
    if (token && username) {
        document.getElementById('loginPage')?.classList.add('hidden');
        document.getElementById('dashboardPage')?.classList.remove('hidden');
        document.getElementById('usernameDisplay').textContent = username;
        return token;
    } else {
        document.getElementById('loginPage')?.classList.remove('hidden');
        document.getElementById('dashboardPage')?.classList.add('hidden');
        return null;
    }
}

function logout() {
    localStorage.removeItem('ansible_token');
    localStorage.removeItem('ansible_username');
    window.location.reload();
}

function navigateTo(section) {
    // Hide all sections
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.remove('active');
    });
    
    // Remove active class from all nav links
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    
    // Show target section and activate nav link
    document.getElementById(section).classList.add('active');
    document.querySelector(`[onclick="navigateTo('${section}')"]`).classList.add('active');
    
    // Load data for the section
    if (section === 'clustersSection') {
        loadClusters();
    } else if (section === 'nodesSection') {
        loadAllNodes();
    }
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

// UI Helper Functions
function showLoading(section = 'clustersSection') {
    document.getElementById(`${section}Loading`)?.classList.remove('hidden');
    document.getElementById(`${section}Error`)?.classList.add('hidden');
    document.getElementById(`${section}Content`)?.classList.add('hidden');
}

function showError(message, section = 'clustersSection') {
    document.getElementById(`${section}Loading`)?.classList.add('hidden');
    document.getElementById(`${section}Error`)?.classList.remove('hidden');
    document.getElementById(`${section}ErrorMessage`).textContent = message;
    document.getElementById(`${section}Content`)?.classList.add('hidden');
}

function showContent(section = 'clustersSection') {
    document.getElementById(`${section}Loading`)?.classList.add('hidden');
    document.getElementById(`${section}Error`)?.classList.add('hidden');
    document.getElementById(`${section}Content`)?.classList.remove('hidden');
}

function showNotification(message, type = 'info') {
    const existingNotification = document.querySelector('.notification');
    if (existingNotification) {
        existingNotification.remove();
    }

    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Login Functions
async function handleLogin(event) {
    event.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const loginBtn = document.getElementById('loginBtn');
    const resultDiv = document.getElementById('loginResult');
    
    showLoginResult('loading', 'Logging in...');
    loginBtn.disabled = true;
    loginBtn.innerHTML = '<div class="loading-spinner"></div> Logging in...';
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                password: password
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            const token = data.access_token;
            showLoginResult('success', 'Login successful! Redirecting...');
            
            localStorage.setItem('ansible_token', token);
            localStorage.setItem('ansible_username', username);
            
            setTimeout(() => {
                checkAuth();
                navigateTo('clustersSection');
            }, 1000);
            
        } else {
            showLoginResult('error', `Login failed: ${data.detail || 'Invalid credentials'}`);
        }
    } catch (error) {
        showLoginResult('error', `Network error: ${error.message}`);
    } finally {
        loginBtn.disabled = false;
        loginBtn.innerHTML = 'Login';
    }
}

function showLoginResult(type, message) {
    const resultDiv = document.getElementById('loginResult');
    resultDiv.className = `login-result ${type}`;
    if (type === 'loading') {
        resultDiv.innerHTML = `<div class="loading-spinner"></div> ${message}`;
    } else {
        resultDiv.innerHTML = message;
    }
    resultDiv.style.display = 'block';
}

// Cluster Management
async function loadClusters() {
    showLoading('clustersSection');
    
    try {
        const clusters = await apiGet('/api/clusters');
        displayClusters(clusters);
        showContent('clustersSection');
    } catch (error) {
        showError(`Failed to load clusters: ${error.message}`, 'clustersSection');
    }
}

function displayClusters(clusters) {
    const clustersList = document.getElementById('clustersList');
    const emptyState = document.getElementById('clustersEmpty');

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
                    <span id="masters-${cluster.id}">${cluster.master_nodes}</span>
                </div>
                <div class="meta-item">
                    <label>Workers:</label>
                    <span id="workers-${cluster.id}">${cluster.worker_nodes}</span>
                </div>
            </div>

            <div class="cluster-actions" style="display: flex; gap: 8px; margin-top: 12px;">
                <button onclick="event.stopPropagation(); refreshCluster('${cluster.id}', '${cluster.name}')" 
                        class="btn-refresh" style="flex: 1;">
                    🔄 Refresh
                </button>
                <button onclick="event.stopPropagation(); viewClusterDetails('${cluster.id}')" 
                        class="btn-primary" style="flex: 2;">
                    View Details
                </button>
            </div>
        </div>
    `).join('');

    clustersList.innerHTML = clustersHtml;
}

// Refresh individual cluster
async function refreshCluster(clusterId, clusterName) {
    try {
        showNotification(`Refreshing cluster ${clusterName}...`, 'info');
        
        const result = await apiPost(`/api/clusters/${clusterId}/refresh`, {});
        
        showNotification(`Cluster ${clusterName} refreshed successfully!`, 'success');
        
        // Reload the clusters list to show updated counts
        loadClusters();
        
    } catch (error) {
        showNotification(`Failed to refresh cluster: ${error.message}`, 'error');
    }
}

function viewClusterDetails(clusterId) {
    // For now, just show an alert. You can expand this to show a modal or dedicated section.
    showNotification(`Viewing cluster ${clusterId} - Feature coming soon!`, 'info');
}

// Node Management
async function loadAllNodes() {
    showLoading('nodesSection');
    
    try {
        // First get all clusters
        const clusters = await apiGet('/api/clusters');
        
        if (!clusters || clusters.length === 0) {
            document.getElementById('nodesEmpty').classList.remove('hidden');
            document.getElementById('nodesContent').classList.add('hidden');
            return;
        }

        // Get nodes for each cluster
        let allNodes = [];
        for (const cluster of clusters) {
            try {
                const nodes = await apiGet(`/api/clusters/${cluster.id}/nodes`);
                allNodes = allNodes.concat(nodes.map(node => ({
                    ...node,
                    cluster_name: cluster.name,
                    cluster_id: cluster.id
                })));
            } catch (error) {
                console.error(`Failed to load nodes for cluster ${cluster.name}:`, error);
            }
        }

        displayAllNodes(allNodes);
        showContent('nodesSection');
    } catch (error) {
        showError(`Failed to load nodes: ${error.message}`, 'nodesSection');
    }
}

function displayAllNodes(nodes) {
    const nodesList = document.getElementById('nodesList');
    const emptyState = document.getElementById('nodesEmpty');

    if (!nodes || nodes.length === 0) {
        nodesList.innerHTML = '';
        emptyState.classList.remove('hidden');
        return;
    }

    emptyState.classList.add('hidden');

    const nodesHtml = nodes.map(node => `
        <div class="node-item">
            <div class="node-header">
                <span class="node-name">${node.hostname}</span>
                <span class="node-type ${node.node_type}">${node.node_type}</span>
            </div>
            <div class="node-details">
                <span class="node-cluster">Cluster: ${node.cluster_name}</span>
                <span class="node-ip">IP: ${node.ip_address || 'Unknown'}</span>
                <span class="node-status status-${node.status.toLowerCase()}">${node.status}</span>
            </div>
        </div>
    `).join('');

    nodesList.innerHTML = nodesHtml;
}

// Cluster Registration
async function handleClusterRegistration(event) {
    event.preventDefault();
    
    const formData = new FormData();
    formData.append('name', document.getElementById('clusterName').value);
    formData.append('description', document.getElementById('clusterDescription').value);
    formData.append('kubeconfig_file', document.getElementById('kubeconfigFile').files[0]);
    
    const submitBtn = document.getElementById('registerClusterBtn');
    const resultDiv = document.getElementById('uploadResult');
    
    showUploadResult('loading', 'Uploading and validating kubeconfig file...');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<div class="loading-spinner"></div> Registering...';
    
    try {
        const token = localStorage.getItem('ansible_token');
        const response = await fetch(`${API_BASE_URL}/api/clusters/register/upload`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showUploadResult('success', 'Cluster registered successfully!');
            document.getElementById('uploadForm').reset();
            document.getElementById('fileName').textContent = 'No file chosen';
            document.getElementById('fileInputCustom').classList.remove('has-file');
            
            // Reload clusters list
            setTimeout(() => {
                loadClusters();
                navigateTo('clustersSection');
            }, 2000);
        } else {
            showUploadResult('error', `Error: ${data.detail || 'Unknown error occurred'}`);
        }
    } catch (error) {
        showUploadResult('error', `Network error: ${error.message}`);
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Register Cluster';
    }
}

function showUploadResult(type, message) {
    const resultDiv = document.getElementById('uploadResult');
    resultDiv.className = `upload-result ${type}`;
    if (type === 'loading') {
        resultDiv.innerHTML = `<div class="loading-spinner"></div> ${message}`;
    } else {
        resultDiv.innerHTML = message;
    }
    resultDiv.style.display = 'block';
}

// File input handling
function setupFileInput() {
    const fileInput = document.getElementById('kubeconfigFile');
    const fileInputCustom = document.getElementById('fileInputCustom');
    const fileName = document.getElementById('fileName');

    fileInput.addEventListener('change', function(e) {
        if (this.files.length > 0) {
            const file = this.files[0];
            fileName.textContent = file.name;
            fileInputCustom.classList.add('has-file');
        } else {
            fileName.textContent = 'No file chosen';
            fileInputCustom.classList.remove('has-file');
        }
    });
}

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    setupFileInput();
    checkAuth();
    
    // Auto-fill test credentials for easier testing
    document.getElementById('username').value = 'testuser';
    document.getElementById('password').value = 'testpassword';
});
