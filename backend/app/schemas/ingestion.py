import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class IngestionTriggerRequest(BaseModel):
    source_portal: Optional[str] = Field(
        default="ALL",
        description="Portal to synchronize: ALL, GEM, CPPP, OPEN_GOV, or TENDERKART",
    )
    force: bool = Field(
        default=False,
        description="Whether to force re-evaluation of tenders even if already synced",
    )
    batch_size: Optional[int] = Field(
        default=50,
        ge=1,
        le=200,
        description="Maximum tenders to ingest per portal source",
    )


class IngestionRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_portal: str
    status: str
    tenders_found: int
    tenders_ingested: int
    tenders_updated: int
    tenders_skipped: int
    error_message: Optional[str] = None
    run_metadata: Optional[Dict[str, Any]] = None
    started_at: datetime
    completed_at: Optional[datetime] = None


class IngestionPortalStatus(BaseModel):
    portal_name: str
    portal_title: str
    status: str  # ACTIVE, MOCK_FALLBACK, BLOCKED, AUTH_REQUIRED
    official_url: str
    access_mode: str
    blocker_details: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    total_tenders_ingested: int = 0


class IngestionStatusOverviewResponse(BaseModel):
    scheduler_running: bool
    scheduler_interval_seconds: int
    portals: List[IngestionPortalStatus]
    latest_runs: List[IngestionRunResponse] = []
