import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ingestion_run import IngestionRun
from app.models.tender import Tender


class IngestionRunRepository:
    """Async database repository for managing tender ingestion execution records."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_run(
        self,
        source_portal: str,
        run_metadata: Optional[Dict[str, Any]] = None,
    ) -> IngestionRun:
        """Create and persist a new running ingestion audit record."""
        run = IngestionRun(
            source_portal=source_portal,
            status="RUNNING",
            run_metadata=run_metadata,
        )
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def update_run(
        self,
        run_id: uuid.UUID,
        status: str,
        tenders_found: int = 0,
        tenders_ingested: int = 0,
        tenders_updated: int = 0,
        tenders_skipped: int = 0,
        error_message: Optional[str] = None,
        run_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[IngestionRun]:
        """Finalize or update status and counts for an ingestion run."""
        stmt = select(IngestionRun).where(IngestionRun.id == run_id)
        result = await self.session.execute(stmt)
        run = result.scalar_one_or_none()
        if not run:
            return None

        run.status = status
        run.tenders_found = tenders_found
        run.tenders_ingested = tenders_ingested
        run.tenders_updated = tenders_updated
        run.tenders_skipped = tenders_skipped
        run.error_message = error_message
        if run_metadata:
            run.run_metadata = run_metadata
        if status in ("SUCCESS", "PARTIAL", "FAILED"):
            run.completed_at = datetime.now(timezone.utc)

        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def list_runs(self, limit: int = 20) -> List[IngestionRun]:
        """Fetch latest ingestion runs ordered by descending start time."""
        stmt = (
            select(IngestionRun)
            .order_by(IngestionRun.started_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_by_portal(self, source_portal: str) -> Optional[IngestionRun]:
        """Fetch most recent run for a specific portal or ALL."""
        stmt = (
            select(IngestionRun)
            .where(IngestionRun.source_portal == source_portal)
            .order_by(IngestionRun.started_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_successful_run(self, source_portal: str) -> Optional[IngestionRun]:
        """Fetch most recent successful run for a specific portal to read checkpoint cursors."""
        stmt = (
            select(IngestionRun)
            .where(
                IngestionRun.source_portal == source_portal,
                IngestionRun.status == "SUCCESS",
            )
            .order_by(IngestionRun.started_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_tenders_by_portal(self) -> Dict[str, int]:
        """Group count of active tenders indexed by source portal."""
        stmt = select(Tender.source_portal, func.count(Tender.id)).group_by(Tender.source_portal)
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}
