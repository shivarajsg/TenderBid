import logging
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.bid_application import (
    BidApplicationCreate,
    BidApplicationListResponse,
    BidApplicationResponse,
    BidApplicationUpdate,
)
from app.services.bid_tracking_service import (
    BidApplicationConflictError,
    BidApplicationNotFoundError,
    BidTrackingError,
    BidTrackingService,
    InvalidStateTransitionError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/applications", tags=["Bid Tracking"])


@router.get(
    "",
    response_model=BidApplicationListResponse,
    summary="List all tracked tender applications for the authenticated MSME",
)
async def list_applications(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: IDENTIFIED, PREPARING, READY, SUBMITTED, AWARDED, REJECTED"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve all bids tracked by the current MSME company with stage and compliance metadata."""
    service = BidTrackingService(session)
    items = await service.list_bid_applications(user_id=current_user.id, status=status_filter)
    return BidApplicationListResponse(items=items, total=len(items))


@router.post(
    "",
    response_model=BidApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Track a new tender opportunity in the MSME bid pipeline",
)
async def create_application(
    app_in: BidApplicationCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Add a tender to internal preparation pipeline starting at IDENTIFIED stage."""
    service = BidTrackingService(session)
    try:
        return await service.create_bid_application(user_id=current_user.id, app_in=app_in)
    except BidApplicationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BidApplicationConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except BidTrackingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/{application_id}",
    response_model=BidApplicationResponse,
    summary="Get details of a tracked tender application",
)
async def get_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Fetch tracked bid details, enforcing tenant isolation."""
    service = BidTrackingService(session)
    try:
        return await service.get_bid_application(user_id=current_user.id, application_id=application_id)
    except BidApplicationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch(
    "/{application_id}",
    response_model=BidApplicationResponse,
    summary="Update stage or notes for a tracked bid application",
)
async def update_application(
    application_id: uuid.UUID,
    app_update: BidApplicationUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Transition pipeline stage (validating legal transitions) or update preparation notes."""
    service = BidTrackingService(session)
    try:
        return await service.update_bid_application(
            user_id=current_user.id,
            application_id=application_id,
            app_update=app_update,
        )
    except BidApplicationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except BidTrackingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a tender application from the preparation pipeline",
)
async def delete_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Untrack a tender application (tenant-isolated)."""
    service = BidTrackingService(session)
    try:
        await service.delete_bid_application(user_id=current_user.id, application_id=application_id)
    except BidApplicationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
