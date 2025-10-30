from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
import os

from config.settings import settings
from core.database import engine, Base
from api.routes import auth, users, inventory, playbooks, kubernetes, credentials, executions

# Import all models to ensure they are registered with SQLAlchemy
from modules.users.models import User
from modules.inventory.models import Inventory
from modules.playbooks.models import Playbook
from modules.kubernetes.models import KubernetesCluster, ClusterNode
from modules.credentials.models import SSHKey, Credential
from modules.executions.models import JobExecution

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting Ansible Platform...")
    print(f"📊 Project: {settings.PROJECT_NAME} v{settings.VERSION}")
    
    print("📁 Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")
    
    print("📁 Application directories:")
    print(f"   - Ansible Roles: {settings.ansible_roles_directory.absolute()}")
    print(f"   - Playbooks: {settings.playbooks_base_directory.absolute()}")
    print(f"   - Kubeconfigs: {settings.kubeconfig_storage_directory.absolute()}")
    print("✅ Application ready")
    
    yield
    
    # Shutdown
    print("👋 Shutting down Ansible Platform...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="A comprehensive Ansible automation platform with Kubernetes cluster management",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=settings.API_PREFIX, tags=["authentication"])
app.include_router(users.router, prefix=settings.API_PREFIX, tags=["users"])
app.include_router(inventory.router, prefix=settings.API_PREFIX, tags=["inventory"])
app.include_router(playbooks.router, prefix=settings.API_PREFIX, tags=["playbooks"])
app.include_router(kubernetes.router, prefix=settings.API_PREFIX, tags=["kubernetes"])
app.include_router(credentials.router, prefix=settings.API_PREFIX, tags=["credentials"])
app.include_router(executions.router, prefix=settings.API_PREFIX, tags=["executions"])

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    """Serve the main dashboard"""
    html_file_path = "index.html"
    if os.path.exists(html_file_path):
        return FileResponse(html_file_path)
    else:
        return {
            "message": f"Welcome to {settings.PROJECT_NAME} v{settings.VERSION}",
            "status": "running",
            "docs": "/docs"
        }

#@app.get("/")
#async def root():
#    return {
#        "message": f"Welcome to {settings.PROJECT_NAME} v{settings.VERSION}",
#        "status": "running",
#        "docs": "/docs",
#        "ui_pages": {
#            "login": "/login",
#            "clusters_dashboard": "/clusters-dashboard", 
#            "upload_form": "/upload"
#        }
#    }

@app.get("/login")
async def login_page():
    """Serve the login page"""
    html_file_path = "login.html"
    if os.path.exists(html_file_path):
        return FileResponse(html_file_path)
    else:
        return {
            "error": "Login page not found",
            "message": "Please ensure login.html exists in the project root directory"
        }

# ADD THESE NEW ROUTES:
@app.get("/clusters-dashboard")
async def clusters_dashboard():
    """Serve the clusters dashboard page"""
    html_file_path = "clusters-dashboard.html"
    if os.path.exists(html_file_path):
        return FileResponse(html_file_path)
    else:
        return {
            "error": "Clusters dashboard not found",
            "message": "Please ensure clusters-dashboard.html exists in the project root directory"
        }

@app.get("/cluster-details")
async def cluster_details_page():
    """Serve the cluster details page"""
    html_file_path = "cluster-details.html"
    if os.path.exists(html_file_path):
        return FileResponse(html_file_path)
    else:
        return {
            "error": "Cluster details page not found", 
            "message": "Please ensure cluster-details.html exists in the project root directory"
        }

@app.get("/upload")
async def upload_form():
    """Serve the kubeconfig upload form"""
    html_file_path = "upload.html"
    if os.path.exists(html_file_path):
        return FileResponse(html_file_path)
    else:
        return {
            "error": "Upload form not found",
            "message": "Please ensure upload.html exists in the project root directory",
            "alternative": "You can use the API endpoint directly at POST /api/clusters/register/upload"
        }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": "postgresql"
    }

@app.get("/config")
async def get_config():
    """Get application configuration (safe version without secrets)"""
    return settings.to_dict()

@app.get("/api")
async def api_info():
    """API information endpoint"""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "endpoints": {
            "authentication": f"{settings.API_PREFIX}/auth",
            "users": f"{settings.API_PREFIX}/users",
            "inventory": f"{settings.API_PREFIX}/inventory",
            "playbooks": f"{settings.API_PREFIX}/playbooks",
            "kubernetes": f"{settings.API_PREFIX}/clusters",
            "credentials": f"{settings.API_PREFIX}/credentials",
            "executions": f"{settings.API_PREFIX}/executions"
        },
        "ui_pages": {
            "login": "/login",
            "clusters_dashboard": "/clusters-dashboard",
            "cluster_details": "/cluster-details", 
            "upload": "/upload"
        },
        "documentation": "/docs"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
