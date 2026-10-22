import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class BidApplicationCreate(BaseModel):
    tender_id: uuid.UUID
    notes: Optional[str] = Field(default=None, max_length=2000)
    target_submission_date: Optional[datetime] = None


class BidApplicationUpdate(BaseModel):
    status: Optional[str] = Field(
        default=None,
        description="Allowed stages: IDENTIFIED, PREPARING, READY, SUBMITTED, AWARDED, REJECTED",
    )
    notes: Optional[str] = Field(default=None, max_length=2000)
    target_submission_date: Optional[datetime] = None


class BidApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    tender_id: uuid.UUID
    status: str
    notes: Optional[str] = None
    target_submission_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    # Denormalized tender and compliance summary for frontend efficiency
    tender_title: Optional[str] = None
    tender_reference: Optional[str] = None
    submission_deadline: Optional[datetime] = None
    estimated_budget_inr: Optional[Decimal] = None
    sector: Optional[str] = None
    latest_report_id: Optional[uuid.UUID] = None
    latest_compliance_status: Optional[str] = None
    latest_compliance_score: Optional[Decimal] = None


class BidApplicationListResponse(BaseModel):
    items: List[BidApplicationResponse]
    total: int
