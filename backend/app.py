from dotenv import load_dotenv
load_dotenv()

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from backend.api.routes.admin import router as admin_router
from backend.api.routes.public import router as public_router
from backend.core.security import limiter
from backend.db.session import init_db
from backend.infrastructure.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)

REQUIRED_ENV_VARS = [
    "ADMIN_USERNAME",
    "ADMIN_PASSWORD",
    "SECRET_KEY",
    "ENVIRONMENT",
]


def validate_required_env_vars():
    missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Please check your .env file."
        )
    logger.info("All required environment variables validated")


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
            "script-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com https://static.cloudflareinsights.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self' https://cloudflareinsights.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_required_env_vars()
    logger.info("Starting WiFi Tracker application")
    start_scheduler()
    yield
    logger.info("Shutting down WiFi Tracker application")
    stop_scheduler()


environment = os.getenv("ENVIRONMENT", "development").lower()
is_production = environment == "production"

app = FastAPI(
    title="WiFi Payment Tracker",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded"}
    )

app.add_middleware(SecurityHeadersMiddleware)

allowed_origins = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[h.strip() for h in allowed_origins],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)

init_db()

app.include_router(public_router)
app.include_router(admin_router)

static_path = os.path.join(os.path.dirname(__file__), "../frontend/static")
app.mount("/static", StaticFiles(directory=static_path), name="static")
