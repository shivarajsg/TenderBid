from app.api.routes.health import router as health_router
from app.api.routes.auth import router as auth_router
from app.api.routes.companies import router as companies_router
from app.api.routes.documents import router as documents_router
from app.api.routes.tenders import router as tenders_router
from app.api.routes.compliance import router as compliance_router
from app.api.routes.bid_applications import router as applications_router
from app.api.routes.notifications import router as notifications_router

__all__ = [
    "health_router",
    "auth_router",
    "companies_router",
    "documents_router",
    "tenders_router",
    "compliance_router",
    "applications_router",
    "notifications_router",
]
