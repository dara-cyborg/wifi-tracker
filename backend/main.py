from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
import os
import logging
from backend.database import init_db
from backend.routes import router
from backend.scheduler import start_scheduler, stop_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS (only in production)
        if os.getenv("ENVIRONMENT") == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # CSP (Content Security Policy)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        
        return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting WiFi Tracker application")
    start_scheduler()
    yield
    # Shutdown
    logger.info("Shutting down WiFi Tracker application")
    stop_scheduler()

app = FastAPI(title="WiFi Payment Tracker", lifespan=lifespan)

# Add security middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add CORS middleware - restrict to specific origins
allowed_hosts = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=allowed_hosts
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[host.strip() for host in allowed_hosts],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)

# Initialize database
init_db()

# Include routes
app.include_router(router)

# Paths
static_path = os.path.join(os.path.dirname(__file__), "../frontend/static")
templates_path = os.path.join(os.path.dirname(__file__), "../frontend/templates")

# Mount static files (CSS, JS, images, etc)
app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/")
def root():
    logger.info("Root page accessed")
    return FileResponse(os.path.join(templates_path, "index.html"))


@app.get("/login.html")
def login_page():
    logger.info("Login page accessed")
    return FileResponse(os.path.join(templates_path, "login.html"))


@app.get("/add.html")
def add_client():
    logger.info("Add client page accessed")
    return FileResponse(os.path.join(templates_path, "add.html"))


@app.get("/edit.html")
def edit_client():
    logger.info("Edit client page accessed")
    return FileResponse(os.path.join(templates_path, "edit.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
