from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
import os
import logging
from slowapi.errors import RateLimitExceeded
from starlette.responses import JSONResponse
from backend.database import init_db
from backend.routes import router
from backend.scheduler import start_scheduler, stop_scheduler
from backend.security import limiter

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
        
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        if os.getenv("ENVIRONMENT") == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
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
    logger.info("Starting WiFi Tracker application")
    start_scheduler()
    yield
    logger.info("Shutting down WiFi Tracker application")
    stop_scheduler()

app = FastAPI(title="WiFi Payment Tracker", lifespan=lifespan)

# Attach limiter to app
app.state.limiter = limiter

# Rate limit exception handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded"}
    )

app.add_middleware(SecurityHeadersMiddleware)

# CORS configuration
allowed_origins = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[h.strip() for h in allowed_origins],
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