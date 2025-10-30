FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including Ansible
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    ssh-client \
    curl \
    gnupg \
    apt-transport-https \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install kubectl from Google Storage (more reliable)
RUN curl -LO "https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x ./kubectl && \
    mv ./kubectl /usr/local/bin/kubectl

# Verify kubectl installation
RUN kubectl version --client --output=yaml

# Install Ansible using pip (simpler approach)
RUN pip install ansible

# Install Ansible community general collection
RUN ansible-galaxy collection install community.general

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories first
RUN mkdir -p /app/ansible_roles /app/playbooks /app/kubeconfigs /app/.kube /app/static/css /app/static/js

# Copy application code FIRST (excluding static files)
COPY main.py .
COPY api/ /app/api/
COPY config/ /app/config/
COPY core/ /app/core/
COPY modules/ /app/modules/
COPY utils/ /app/utils/

# Copy static files to the correct locations
COPY css/dashboard.css /app/static/css/dashboard.css
COPY js/clusters.js /app/static/js/clusters.js
COPY js/dashboard.js /app/static/js/dashboard.js
# Copy HTML files last
COPY *.html /app/

# Create ansible.cfg with disabled host key checking
RUN mkdir -p /etc/ansible && \
    echo "[defaults]" > /etc/ansible/ansible.cfg && \
    echo "host_key_checking = False" >> /etc/ansible/ansible.cfg && \
    echo "retry_files_enabled = False" >> /etc/ansible/ansible.cfg

# Set proper permissions
RUN chmod 755 /app/.kube

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
