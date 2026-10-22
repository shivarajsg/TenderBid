"""
=============================================================================
Automated Government Tender Ingestion Background Scheduler
Project: Agentic AI-Powered Tender Intelligence & Compliance Management for MSMEs
=============================================================================

This module provides a reliable, non-blocking asynchronous background scheduler that
periodically synchronizes public procurement notices from supported official government
sources (GeM, CPPP, Open Government Data) into PostgreSQL on a configurable schedule.

Guarantees:
1. Non-blocking Async Loop: Runs as a background asyncio task managed via FastAPI lifespan.
2. Fresh Session per Tick: Each sync tick executes in an isolated database session.
3. Overlap Prevention: Concurrent execution guard prevents overlapping sync cycles.
4. Error Resiliency: Unhandled exceptions are logged without terminating the worker.
5. Graceful Lifecycle: Cleanly shuts down on cancellation or application exit.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.ingestion_run import IngestionRun
from app.services.ingestion.ingestion_service import TenderIngestionService

logger = logging.getLogger(__name__)


class TenderIngestionScheduler:
    """Background worker orchestrating automated periodic government tender ingestion."""

    def __init__(
        self,
        session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
        interval_seconds: Optional[int] = None,
        enabled: Optional[bool] = None,
    ):
        settings = get_settings()
        self.session_factory = session_factory or AsyncSessionLocal
        self.interval_seconds = (
            interval_seconds
            if interval_seconds is not None
            else settings.INGESTION_INTERVAL_SECONDS
        )
        self.enabled = (
            enabled
            if enabled is not None
            else settings.INGESTION_ENABLED
        )

        self._task: Optional[asyncio.Task] = None
        self._stop_event: asyncio.Event = asyncio.Event()
        self._lock: asyncio.Lock = asyncio.Lock()
        self._execution_count: int = 0
        self._last_sync_time: Optional[datetime] = None
        self._last_ingested_count: int = 0

    @property
    def is_running(self) -> bool:
        """True if scheduler asyncio task is active."""
        return self._task is not None and not self._task.done()

    @property
    def execution_count(self) -> int:
        return self._execution_count

    @property
    def last_sync_time(self) -> Optional[datetime]:
        return self._last_sync_time

    @property
    def last_ingested_count(self) -> int:
        return self._last_ingested_count

    async def tick(self, force: bool = False) -> Optional[IngestionRun]:
        """
        Execute a single discovery and synchronization tick across all configured sources.
        Guarded against overlapping runs.
        """
        if self._lock.locked():
            logger.warning("[TenderIngestionScheduler] Previous sync still active; skipping tick to avoid overlap.")
            return None

        async with self._lock:
            async with self.session_factory() as session:
                try:
                    service = TenderIngestionService(session)
                    run = await service.sync_portal(source_portal="ALL", force=force)
                    self._last_sync_time = datetime.now(timezone.utc)
                    self._last_ingested_count = run.tenders_ingested
                    self._execution_count += 1
                    logger.info(
                        "[TenderIngestionScheduler] Tick completed: %d new tenders ingested, %d updated, %d skipped.",
                        run.tenders_ingested,
                        run.tenders_updated,
                        run.tenders_skipped,
                    )
                    return run
                except Exception as e:
                    logger.error("[TenderIngestionScheduler] Error during scheduled sync tick: %s", e, exc_info=True)
                    return None

    async def _run_loop(self) -> None:
        """Periodic background execution loop."""
        logger.info(
            "[TenderIngestionScheduler] Worker started (interval: %ds, enabled: %s).",
            self.interval_seconds,
            self.enabled,
        )

        # Optional initial sync on start if configured
        try:
            await self.tick()
        except Exception as e:
            logger.error("[TenderIngestionScheduler] Initial sync error: %s", e)

        while not self._stop_event.is_set():
            try:
                # Wait for interval or stop event
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=float(self.interval_seconds),
                )
                break
            except asyncio.TimeoutError:
                if not self.enabled:
                    continue
                try:
                    await self.tick()
                except Exception as e:
                    logger.error("[TenderIngestionScheduler] Uncaught error in scheduler loop: %s", e)

        logger.info("[TenderIngestionScheduler] Worker stopped.")

    def start(self) -> asyncio.Task:
        """Start the background ingestion scheduler task."""
        if self.is_running:
            logger.warning("[TenderIngestionScheduler] Worker already running.")
            return self._task

        self._stop_event.clear()
        loop = asyncio.get_event_loop()
        self._task = loop.create_task(self._run_loop(), name="tender_ingestion_scheduler")
        return self._task

    async def stop(self) -> None:
        """Signal worker to stop and await clean termination."""
        if not self.is_running:
            return

        self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None


# Module-level singleton instance
_global_ingestion_scheduler: Optional[TenderIngestionScheduler] = None


def get_ingestion_scheduler() -> TenderIngestionScheduler:
    """Retrieve or initialize the global TenderIngestionScheduler singleton."""
    global _global_ingestion_scheduler
    if _global_ingestion_scheduler is None:
        _global_ingestion_scheduler = TenderIngestionScheduler()
    return _global_ingestion_scheduler
