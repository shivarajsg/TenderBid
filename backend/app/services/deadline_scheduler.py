"""
=============================================================================
Proactive Deadline Alert Background Scheduler
Project: Agentic AI-Powered Tender Intelligence & Compliance Management for MSMEs
=============================================================================

This module provides a reliable, asynchronous background scheduler that
periodically evaluates closing tender deadlines against active tracked bids
(and explicit watches), generating persistent, idempotent notifications 48 hours
prior to closing without requiring user HTTP interaction.

Architectural Guarantees:
1. Non-blocking Async Loop: Runs as a background asyncio task managed via FastAPI lifespan.
2. Fresh Session per Tick: Each scan executes in an isolated database session with cleanup.
3. Overlap Prevention: Concurrent execution guard prevents overlapping ticks.
4. Error Resiliency: Unhandled exceptions are logged without terminating the worker.
5. Graceful Lifecycle: Responds cleanly to asyncio shutdown signals.
6. Deployment Safety: Database uniqueness constraint (uq_company_tender_notification)
   ensures idempotency even if multiple worker processes execute concurrently.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Callable, Optional
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.services.alert_service import DeadlineAlertService

logger = logging.getLogger(__name__)


class DeadlineAlertScheduler:
    """
    Background worker orchestrating automated periodic deadline evaluations.
    """

    def __init__(
        self,
        session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
        interval_seconds: Optional[int] = None,
        clock_fn: Optional[Callable[[], datetime]] = None,
        enabled: Optional[bool] = None,
    ):
        settings = get_settings()
        self.session_factory = session_factory or AsyncSessionLocal
        self.interval_seconds = (
            interval_seconds
            if interval_seconds is not None
            else settings.DEADLINE_ALERT_INTERVAL_SECONDS
        )
        self.enabled = (
            enabled
            if enabled is not None
            else settings.DEADLINE_ALERT_ENABLED
        )
        self.clock_fn = clock_fn or (lambda: datetime.now(timezone.utc))

        self._task: Optional[asyncio.Task] = None
        self._stop_event: asyncio.Event = asyncio.Event()
        self._lock: asyncio.Lock = asyncio.Lock()
        self._execution_count: int = 0
        self._last_scan_time: Optional[datetime] = None
        self._last_alerts_generated: int = 0

    @property
    def is_running(self) -> bool:
        """True if the scheduler task is currently active and not finished."""
        return self._task is not None and not self._task.done()

    @property
    def execution_count(self) -> int:
        return self._execution_count

    @property
    def last_alerts_generated(self) -> int:
        return self._last_alerts_generated

    async def tick(self) -> int:
        """
        Execute a single deadline evaluation scan.
        Guarded against overlapping runs.
        Returns the number of alerts generated.
        """
        if self._lock.locked():
            logger.warning("[DeadlineAlertScheduler] Previous tick still running; skipping tick to avoid overlap.")
            return 0

        async with self._lock:
            alerts_created = 0
            async with self.session_factory() as session:
                try:
                    service = DeadlineAlertService(
                        session=session,
                        clock_fn=self.clock_fn,
                    )
                    alerts_created = await service.scan_and_generate_alerts(threshold_hours=48)
                    self._last_alerts_generated = alerts_created
                    self._last_scan_time = self.clock_fn()
                    self._execution_count += 1
                    logger.debug(
                        "[DeadlineAlertScheduler] Tick completed. Alerts generated: %d (total ticks: %d)",
                        alerts_created,
                        self._execution_count,
                    )
                except Exception as exc:
                    logger.error(
                        "[DeadlineAlertScheduler] Unexpected error during deadline alert scan: %s",
                        exc,
                        exc_info=True,
                    )
            return alerts_created

    async def _run_loop(self) -> None:
        """Continuous execution loop until stop_event is signaled."""
        logger.info(
            "[DeadlineAlertScheduler] Background worker started (interval: %ds, enabled: %s).",
            self.interval_seconds,
            self.enabled,
        )

        while not self._stop_event.is_set():
            try:
                await self.tick()
            except Exception as exc:
                logger.error("[DeadlineAlertScheduler] Unhandled loop exception: %s", exc, exc_info=True)

            # Wait for interval or until stopped early
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=float(self.interval_seconds))
            except asyncio.TimeoutError:
                pass

        logger.info("[DeadlineAlertScheduler] Background worker loop exiting.")

    def start(self) -> None:
        """Start the background scheduler task if enabled."""
        if not self.enabled:
            logger.info("[DeadlineAlertScheduler] Worker disabled by configuration (DEADLINE_ALERT_ENABLED=False).")
            return

        if self.is_running:
            logger.warning("[DeadlineAlertScheduler] Worker already running; start() ignored.")
            return

        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop())
        logger.info("[DeadlineAlertScheduler] Task scheduled successfully.")

    async def stop(self, timeout: float = 5.0) -> None:
        """Signal the worker to stop and await clean termination."""
        if not self.is_running:
            return

        logger.info("[DeadlineAlertScheduler] Stopping background worker...")
        self._stop_event.set()

        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=timeout)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                logger.warning("[DeadlineAlertScheduler] Worker did not stop within timeout; cancelling task.")
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass

        self._task = None
        logger.info("[DeadlineAlertScheduler] Worker stopped cleanly.")


# Singleton instance for application lifecycle
_scheduler_instance: Optional[DeadlineAlertScheduler] = None


def get_deadline_scheduler() -> DeadlineAlertScheduler:
    """Retrieve or initialize the global DeadlineAlertScheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = DeadlineAlertScheduler()
    return _scheduler_instance
