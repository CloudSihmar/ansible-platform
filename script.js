let clusters = [];
let currentClusterNodes = {};

// Check authentication on page load
function checkAuth() {
    const token = localStorage.getItem('ansible_token');
    const username = localStorage.getItem('ansible_username');
    
    if (token && username) {
        document.getElementById('usernameDisplay').textContent = username;
        loadClusters();
        return token;
    } else {
        alert('Please login first');
        window.location.href = 'http://localhost:8000/login';
        return null;
    }
}

// Tab navigation
function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.content-section').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });

    // Show selected tab
    document.getElementById(tabName).classList.add('active');
    document.querySelector(`.tab[onclick="showTab('${tabName}')"]`).classList.add('active');
}

// Load clusters from API
async function loadClusters() {
    const token = checkAuth();
    if (!token) return;

    const clustersList = document.getElementById('clustersList');
    const overviewContent = document.getElementById('overviewContent');
    const statsGrid = document.getElementById('statsGrid');

    // Show loading
    clustersList.innerHTML = `
        <div class="loading">
            <div class="loading-spinner"></div>
            <p>Loading clusters...</p>
        </div>
    `;

    overviewContent.innerHTML = `
        <div class="loading">
            <div class="loading-spinner"></div>
            <p>Loading overview...</p>
        </div>
    `;

    try {
        const response = await fetch('http://localhost:8000/api/clusters', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        clusters = await response.json();
        displayClusters();
        displayOverview();
        loadAllClusterNodes();

    } catch (error) {
        clustersList.innerHTML = `
            <div class="error-message">
                <strong>Error loading clusters:</strong> ${error.message}
            </div>
        `;
        overviewContent.innerHTML = `
            <div class="error-message">
                <strong>Error loading overview:</strong> ${error.message}
            </div>
        `;
    }
}

// Display clusters in the clusters tab
function displayClusters() {
    const clustersList = document.getElementById('clustersList');
    
    if (clusters.length === 0) {
        clustersList.innerHTML = `
            <div class="no-clusters">
                <h3>No clusters found</h3>
                <p>You haven't registered any Kubernetes clusters yet.</p>
                <button class="btn btn-primary" onclick="goToUpload()">Register Your First Cluster</button>
            </div>
        `;
        return;
    }

    clustersList.innerHTML = clusters.map(cluster => `
        <div class="cluster-card">
            <div class="cluster-header">
                <div class="cluster-name">${cluster.name}</div>
                <div class="cluster-status status-${cluster.status}">${cluster.status}</div>
            </div>
            
            <div class="cluster-info">
                <div class="info-item">
                    <span class="info-label">ID</span>
                    <span class="info-value">${cluster.id}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Type</span>
                    <span class="info-value">${cluster.cluster_type}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Auth Type</span>
                    <span class="info-value">${cluster.auth_type || 'N/A'}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">API Server</span>
                    <span class="info-value">${cluster.api_server || 'N/A'}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Nodes</span>
                    <span class="info-value">${cluster.master_nodes || 0} master, ${cluster.worker_nodes || 0} worker</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Created</span>
                    <span class="info-value">${new Date(cluster.created_at).toLocaleDateString()}</span>
                </div>
            </div>

            ${cluster.description ? `
                <div class="info-item">
                    <span class="info-label">Description</span>
                    <span class="info-value">${cluster.description}</span>
                </div>
            ` : ''}

            <div class="cluster-actions">
                <button class="btn btn-primary" onclick="viewClusterNodes('${cluster.id}')">
                    👁️ View Nodes
                </button>
                <button class="btn btn-success" onclick="refreshClusterNodes('${cluster.id}')">
                    🔄 Refresh Nodes
                </button>
                <button class="btn btn-warning" onclick="getClusterHealth('${cluster.id}')">
                    ❤️ Health Check
                </button>
                <button class="btn btn-danger" onclick="deleteCluster('${cluster.id}')">
                    🗑️ Delete
                </button>
            </div>
        </div>
    `).join('');
}

// Display overview statistics
function displayOverview() {
    const statsGrid = document.getElementById('statsGrid');
    const overviewContent = document.getElementById('overviewContent');

    const totalClusters = clusters.length;
    const registeredClusters = clusters.filter(c => c.status === 'registered').length;
    const totalMasters = clusters.reduce((sum, cluster) => sum + (cluster.master_nodes || 0), 0);
    const totalWorkers = clusters.reduce((sum, cluster) => sum + (cluster.worker_nodes || 0), 0);

    statsGrid.innerHTML = `
        <div class="stat-card">
            <div class="stat-number">${totalClusters}</div>
            <div class="stat-label">Total Clusters</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${registeredClusters}</div>
            <div class="stat-label">Active Clusters</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${totalMasters}</div>
            <div class="stat-label">Master Nodes</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${totalWorkers}</div>
            <div class="stat-label">Worker Nodes</div>
        </div>
    `;

    overviewContent.innerHTML = `
        <h3>Recent Activity</h3>
        <p>Cluster management dashboard is active. You have ${totalClusters} cluster(s) registered.</p>
    `;
}

// Load all cluster nodes
async function loadAllClusterNodes() {
    const token = checkAuth();
    if (!token) return;

    const nodesGrid = document.getElementById('nodesGrid');
    
    nodesGrid.innerHTML = `
        <div class="loading">
            <div class="loading-spinner"></div>
            <p>Loading nodes...</p>
        </div>
    `;

    try {
        // This would typically call an API endpoint to get all nodes
        // For now, we'll simulate by aggregating nodes from all clusters
        let allNodes = [];
        
        for (const cluster of clusters) {
            const nodes = await fetchClusterNodes(cluster.id, token);
            if (nodes) {
                allNodes = allNodes.concat(nodes.map(node => ({
                    ...node,
                    clusterName: cluster.name
                })));
            }
        }

        displayAllNodes(allNodes);
    } catch (error) {
        nodesGrid.innerHTML = `
            <div class="error-message">
                <strong>Error loading nodes:</strong> ${error.message}
            </div>
        `;
    }
}

// Fetch nodes for a specific cluster
async function fetchClusterNodes(clusterId, token) {
    try {
        const response = await fetch(`http://localhost:8000/api/clusters/${clusterId}/nodes`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            return await response.json();
        }
        return null;
    } catch (error) {
        console.error(`Error fetching nodes for cluster ${clusterId}:`, error);
        return null;
    }
}

// Display all nodes in the nodes tab
function displayAllNodes(nodes) {
    const nodesGrid = document.getElementById('nodesGrid');
    
    if (nodes.length === 0) {
        nodesGrid.innerHTML = `
            <div class="no-clusters">
                <h3>No nodes found</h3>
                <p>No cluster nodes are currently available.</p>
            </div>
        `;
        return;
    }

    nodesGrid.innerHTML = nodes.map(node => `
        <div class="node-card ${node.role === 'master' ? 'master' : ''}">
            <div class="node-header">
                <div class="node-name">${node.name}</div>
                <div class="node-status status-${node.status?.toLowerCase() || 'unknown'}">
                    ${node.status || 'UNKNOWN'}
                </div>
            </div>
            <div class="node-info">
                <div class="info-item">
                    <span class="info-label">Cluster</span>
                    <span class="info-value">${node.clusterName}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Role</span>
                    <span class="node-role ${node.role}">${node.role}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">CPU</span>
                    <span class="info-value">${node.cpu || 'N/A'}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Memory</span>
                    <span class="info-value">${node.memory || 'N/A'}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">OS</span>
                    <span class="info-value">${node.os || 'N/A'}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Kernel</span>
                    <span class="info-value">${node.kernel || 'N/A'}</span>
                </div>
            </div>
        </div>
    `).join('');
}

// View nodes for a specific cluster
function viewClusterNodes(clusterId) {
    showTab('nodes');
    // Implementation would focus on showing nodes for this specific cluster
    console.log('Viewing nodes for cluster:', clusterId);
}

// Refresh nodes for a specific cluster
async function refreshClusterNodes(clusterId) {
    const token = checkAuth();
    if (!token) return;

    try {
        // Implementation to refresh nodes
        console.log('Refreshing nodes for cluster:', clusterId);
        // This would typically call an API to refresh node information
        alert('Refreshing nodes for cluster...');
    } catch (error) {
        alert('Error refreshing nodes: ' + error.message);
    }
}

// Get cluster health
async function getClusterHealth(clusterId) {
    const token = checkAuth();
    if (!token) return;

    try {
        // Implementation for health check
        console.log('Checking health for cluster:', clusterId);
        // This would typically call a health check API
        alert('Performing health check...');
    } catch (error) {
        alert('Error performing health check: ' + error.message);
    }
}

// Delete cluster
async function deleteCluster(clusterId) {
    const token = checkAuth();
    if (!token) return;

    if (confirm('Are you sure you want to delete this cluster? This action cannot be undone.')) {
        try {
            const response = await fetch(`http://localhost:8000/api/clusters/${clusterId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                alert('Cluster deleted successfully');
                loadClusters(); // Reload the clusters list
            } else {
                throw new Error('Failed to delete cluster');
            }
        } catch (error) {
            alert('Error deleting cluster: ' + error.message);
        }
    }
}

// Navigate to upload page
function goToUpload() {
    window.location.href = 'http://localhost:8000/upload';
}

// Logout user
function logout() {
    localStorage.removeItem('ansible_token');
    localStorage.removeItem('ansible_username');
    window.location.href = 'http://localhost:8000/login';
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    checkAuth();
});
