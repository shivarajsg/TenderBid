from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.db.session import check_db_connectivity
from app.schemas.common import ResponseEnvelope

router = APIRouter(tags=["Health & Readiness"])
settings = get_settings()


@router.get("/health", response_model=ResponseEnvelope[dict])
async def liveness_check():
    """Liveness probe reporting process status without exposing sensitive credentials."""
    return ResponseEnvelope(
        success=True,
        message="Application process is running",
        data={
            "status": "healthy",
            "app_name": settings.APP_NAME,
            "environment": settings.APP_ENV,
        },
    )


@router.get("/health/ready", response_model=ResponseEnvelope[dict])
async def readiness_check():
    """Readiness probe verifying PostgreSQL database connectivity."""
    is_ready = await check_db_connectivity()
    if not is_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "success": False,
                "error_code": "DATABASE_UNAVAILABLE",
                "message": "PostgreSQL database is currently unreachable",
                "details": None,
            },
        )
    return ResponseEnvelope(
        success=True,
        message="All backend subsystems are ready",
        data={"database": "connected"},
    )
