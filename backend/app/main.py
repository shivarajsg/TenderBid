import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import (
    applications_router,
    auth_router,
    companies_router,
    compliance_router,
    documents_router,
    health_router,
    notifications_router,
    tenders_router,
)
from app.core.config import get_settings
from app.core.middleware import InMemoryRateLimiter, SecurityHeadersMiddleware
from app.db.session import close_db_connection
from app.services.deadline_scheduler import get_deadline_scheduler
from app.services.ingestion_scheduler import get_ingestion_scheduler

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("tender_app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management handling startup initialization and clean shutdown."""
    logger.info("Initializing Tender Intelligence Platform API [%s mode]", settings.APP_ENV)
    
    # Ensure protected storage directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Start background deadline alert scheduler (if enabled and not in testing environment)
    scheduler = get_deadline_scheduler()
    if settings.APP_ENV != "test" and settings.DEADLINE_ALERT_ENABLED:
        scheduler.start()

    # Start background government tender ingestion scheduler
    ingestion_scheduler = get_ingestion_scheduler()
    if settings.APP_ENV != "test" and settings.INGESTION_ENABLED:
        ingestion_scheduler.start()
    
    yield
    
    # Gracefully shut down background workers
    if scheduler.is_running:
        logger.info("Stopping background deadline scheduler...")
        await scheduler.stop()

    if ingestion_scheduler.is_running:
        logger.info("Stopping background tender ingestion scheduler...")
        await ingestion_scheduler.stop()

    logger.info("Shutting down API: disposing database connection pool...")
    await close_db_connection()
    logger.info("Shutdown complete.")


app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API foundation for MSME Tender Intelligence & Compliance Management",
    version="0.1.0",
    docs_url="/docs" if settings.DEBUG or settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.DEBUG or settings.APP_ENV != "production" else None,
    lifespan=lifespan,
)

# Configure CORS with explicit allowed frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
# Defense-in-depth security response headers
app.add_middleware(SecurityHeadersMiddleware)
# Proportionate in-memory rate limiter on sensitive endpoints
app.add_middleware(
    InMemoryRateLimiter,
    auth_limit_per_minute=60,
    analyze_limit_per_minute=30,
    global_limit_per_minute=600,
    enabled=settings.APP_ENV != "test",
)


# Centralized Exception Handlers returning standardized ErrorEnvelope
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation failures with structured error payload."""
    errors = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err.get("loc", []))
        errors.append({
            "field": field,
            "message": err.get("msg", "Invalid input"),
            "type": err.get("type", "value_error"),
        })
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": "The submitted payload failed validation",
            "details": errors,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Standardize HTTP exceptions across all endpoints."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "details": None,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch unhandled errors, log securely, and return sanitized message."""
    logger.exception("Unhandled server exception encountered on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected server error occurred. Please try again later.",
            "details": None,
        },
    )


# Mount versioned API routes under /api/v1
API_PREFIX = "/api/v1"
app.include_router(health_router, prefix=API_PREFIX)
app.include_router(health_router)  # Also expose /health at root for container probes
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(companies_router, prefix=API_PREFIX)
app.include_router(documents_router, prefix=API_PREFIX)
app.include_router(tenders_router, prefix=API_PREFIX)
app.include_router(compliance_router, prefix=API_PREFIX)
app.include_router(applications_router, prefix=API_PREFIX)
app.include_router(notifications_router, prefix=API_PREFIX)


@app.get("/", tags=["Root"])
async def root():
    """Root info endpoint."""
    return {
        "app": settings.APP_NAME,
        "status": "online",
        "api_version": "v1",
        "docs_url": "/docs" if settings.DEBUG or settings.APP_ENV != "production" else None,
    }
