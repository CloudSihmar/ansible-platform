-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'ansible_operator',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

-- Create inventory table
CREATE TABLE IF NOT EXISTS inventory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    inventory_type VARCHAR(20) DEFAULT 'static',
    content TEXT NOT NULL,
    variables JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create playbooks table
CREATE TABLE IF NOT EXISTS playbooks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    playbook_content TEXT,
    playbook_type VARCHAR(50) DEFAULT 'general',
    repository_url VARCHAR(500),
    local_path VARCHAR(500),
    variables_schema JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create ssh_keys table
CREATE TABLE IF NOT EXISTS ssh_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    private_key TEXT NOT NULL,
    public_key TEXT NOT NULL,
    passphrase TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create credentials table
CREATE TABLE IF NOT EXISTS credentials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    username TEXT,
    password TEXT,
    credential_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create kubernetes_clusters table
CREATE TABLE IF NOT EXISTS kubernetes_clusters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    cluster_type VARCHAR(20) NOT NULL,
    master_nodes INTEGER DEFAULT 1,
    worker_nodes INTEGER DEFAULT 2,
    kubeconfig TEXT,
    status VARCHAR(50) DEFAULT 'creating',
    inventory_id UUID REFERENCES inventory(id) ON DELETE SET NULL,
    playbook_id UUID REFERENCES playbooks(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create cluster_nodes table
CREATE TABLE IF NOT EXISTS cluster_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cluster_id UUID NOT NULL REFERENCES kubernetes_clusters(id) ON DELETE CASCADE,
    node_type VARCHAR(20) NOT NULL,
    hostname VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45),
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create job_executions table
CREATE TABLE IF NOT EXISTS job_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    playbook_id UUID REFERENCES playbooks(id) ON DELETE SET NULL,
    inventory_id UUID REFERENCES inventory(id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'running',
    output TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_inventory_user_id ON inventory(user_id);
CREATE INDEX IF NOT EXISTS idx_playbooks_user_id ON playbooks(user_id);
CREATE INDEX IF NOT EXISTS idx_kubernetes_clusters_user_id ON kubernetes_clusters(user_id);
CREATE INDEX IF NOT EXISTS idx_job_executions_user_id ON job_executions(user_id);
CREATE INDEX IF NOT EXISTS idx_cluster_nodes_cluster_id ON cluster_nodes(cluster_id);

-- Insert default admin user (password: admin123)
INSERT INTO users (username, email, password_hash, role) 
VALUES (
    'admin', 
    'admin@example.com', 
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj89OFGVwxyC', 
    'admin'
) ON CONFLICT (username) DO NOTHING;
