import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from app.services.alert_service import DeadlineAlertService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications & Alerts"])


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="List persistent notifications for authenticated MSME company",
)
async def list_notifications(
    unread_only: bool = Query(False, description="Filter to only unread notifications"),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve in-app notifications including approaching deadline alerts."""
    service = DeadlineAlertService(session)
    return await service.list_notifications(
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Get count of unread notifications for navbar badge",
)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Fast unread count query for real-time header bell indicator."""
    service = DeadlineAlertService(session)
    count = await service.get_unread_count(user_id=current_user.id)
    return UnreadCountResponse(unread_count=count)


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark a notification as read",
)
async def mark_as_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Acknowledge and mark a notification as read with tenant isolation."""
    service = DeadlineAlertService(session)
    updated = await service.mark_as_read(user_id=current_user.id, notification_id=notification_id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification '{notification_id}' not found.",
        )
    return updated


@router.post(
    "/mark-all-read",
    summary="Mark all company notifications as read",
)
async def mark_all_as_read(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Batch-mark all active company notifications as read."""
    service = DeadlineAlertService(session)
    updated_count = await service.mark_all_as_read(user_id=current_user.id)
    return {"message": f"Marked {updated_count} notifications as read."}


@router.post(
    "/trigger-check",
    summary="Trigger on-demand background deadline alert evaluation",
)
async def trigger_deadline_check(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Evaluate closing tender deadlines against all active tracked bids.
    Idempotently creates 48-hour alerts and overdue notices.
    """
    service = DeadlineAlertService(session)
    generated = await service.scan_and_generate_alerts(threshold_hours=48)
    return {
        "status": "COMPLETED",
        "alerts_generated": generated,
        "message": f"Evaluated deadlines; generated {generated} new notifications.",
    }
