import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.ingestion_runs import IngestionRunRepository
from app.db.repositories.tenders import TenderRepository
from app.models.ingestion_run import IngestionRun
from app.models.tender import Tender
from app.schemas.ingestion import (
    IngestionPortalStatus,
    IngestionRunResponse,
    IngestionStatusOverviewResponse,
)
from app.services.ingestion.base_connector import BaseTenderConnector, RawTenderRecord
from app.services.ingestion.apify_connector import ApifyTenderConnector
from app.services.ingestion.cppp_connector import CPPPTenderConnector
from app.services.ingestion.gem_connector import GeMTenderConnector
from app.services.ingestion.open_gov_connector import OpenGovDataConnector
from app.services.ingestion.tenderkart_connector import TenderKartConnector

logger = logging.getLogger(__name__)


def _normalize_tz(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class TenderIngestionService:
    """
    Central orchestration service for automated government tender ingestion,
    deduplication, normalization, and PostgreSQL synchronization.
    """

    def __init__(
        self,
        session: AsyncSession,
        connectors: Optional[List[BaseTenderConnector]] = None,
    ):
        self.session = session
        self.tender_repo = TenderRepository(session)
        self.run_repo = IngestionRunRepository(session)
        self.connectors: Dict[str, BaseTenderConnector] = {}

        configured_connectors = connectors or [
            GeMTenderConnector(),
            CPPPTenderConnector(),
            OpenGovDataConnector(),
            TenderKartConnector(),
            ApifyTenderConnector(),
        ]
        for conn in configured_connectors:
            self.connectors[conn.portal_name] = conn

    async def get_overview(
        self,
        scheduler_running: bool = False,
        scheduler_interval_seconds: int = 3600,
    ) -> IngestionStatusOverviewResponse:
        """Collect real-time health, legal access modes, and sync status for all portals."""
        portal_counts = await self.run_repo.count_tenders_by_portal()
        portal_statuses: List[IngestionPortalStatus] = []

        for name, connector in self.connectors.items():
            avail = await connector.check_availability()
            latest_run = await self.run_repo.get_latest_by_portal(name)

            portal_statuses.append(
                IngestionPortalStatus(
                    portal_name=name,
                    portal_title=connector.portal_title,
                    status=avail.get("status", "ACTIVE"),
                    official_url=connector.official_url,
                    access_mode=avail.get("access_mode", "Automated Connector"),
                    blocker_details=avail.get("blocker_details"),
                    last_synced_at=latest_run.completed_at if latest_run else None,
                    total_tenders_ingested=portal_counts.get(name, 0),
                )
            )

        latest_runs = await self.run_repo.list_runs(limit=10)

        return IngestionStatusOverviewResponse(
            scheduler_running=scheduler_running,
            scheduler_interval_seconds=scheduler_interval_seconds,
            portals=portal_statuses,
            latest_runs=[IngestionRunResponse.model_validate(r) for r in latest_runs],
        )

    async def sync_portal(
        self,
        source_portal: str = "ALL",
        limit: int = 50,
        force: bool = False,
    ) -> IngestionRun:
        """
        Execute discovery and normalization tick across selected or all procurement portals.
        Performs idempotent atomic upserts in PostgreSQL.
        """
        target_connectors: List[BaseTenderConnector] = []
        if source_portal.upper() == "ALL":
            target_connectors = list(self.connectors.values())
        elif source_portal.upper() in self.connectors:
            target_connectors = [self.connectors[source_portal.upper()]]
        else:
            raise ValueError(
                f"Unknown source portal '{source_portal}'. Supported: ALL, {', '.join(self.connectors.keys())}"
            )

        run = await self.run_repo.create_run(
            source_portal=source_portal.upper(),
            run_metadata={
                "limit_per_portal": limit,
                "force": force,
                "connectors": [c.portal_name for c in target_connectors],
            },
        )
        run_id = run.id

        total_found = 0
        total_ingested = 0
        total_updated = 0
        total_skipped = 0
        total_fixtures = 0
        total_live = 0
        now = datetime.now(timezone.utc)
        error_msg: Optional[str] = None
        sync_checkpoints: Dict[str, str] = {}

        try:
            for connector in target_connectors:
                logger.info(
                    "[TenderIngestionService] Syncing portal %s (%s)...",
                    connector.portal_name,
                    connector.portal_title,
                )
                try:
                    # Incremental sync checkpoint lookup
                    updated_after = None
                    if connector.portal_name == "TENDERKART":
                        latest_success = await self.run_repo.get_latest_successful_run(connector.portal_name)
                        if latest_success and latest_success.run_metadata:
                            saved_filter_checkpoints = latest_success.run_metadata.get("filter_checkpoints", {})
                            target_f_id = getattr(connector, "default_filter_id", None)
                            if target_f_id and target_f_id in saved_filter_checkpoints:
                                updated_after = saved_filter_checkpoints[target_f_id]
                            else:
                                updated_after = latest_success.run_metadata.get("next_updated_after")
                        records = await connector.fetch_tenders(limit=limit, updated_after=updated_after)
                        checkpoint = getattr(connector, "last_sync_checkpoint", None)
                        if checkpoint:
                            sync_checkpoints[connector.portal_name] = checkpoint
                    else:
                        records = await connector.fetch_tenders(limit=limit)

                    total_found += len(records)

                    for rec in records:
                        # Track fixture vs live counts
                        is_fix = bool(rec.ingestion_metadata and rec.ingestion_metadata.get("is_fixture"))
                        if is_fix:
                            total_fixtures += 1
                        else:
                            total_live += 1

                        # 1. Primary deduplication check: portal + external tender ID
                        existing = await self.tender_repo.get_by_source_portal_and_id(
                            rec.source_portal, rec.source_tender_id
                        )

                        # 2. Fallback deduplication: tender_reference (ONLY for direct government sources, NOT TenderKart or Apify)
                        # Spec invariant: Third-party providers use stable external IDs, never solely repeating references
                        if not existing and rec.source_portal not in ("TENDERKART", "APIFY"):
                            existing = await self.tender_repo.get_by_reference(rec.tender_reference)

                        if existing:
                            # Update dynamically closing deadlines or sync timestamp
                            existing_dl = _normalize_tz(existing.submission_deadline)
                            rec_dl = _normalize_tz(rec.submission_deadline)
                            deadline_changed = (
                                existing_dl is None
                                or rec_dl is None
                                or abs((existing_dl - rec_dl).total_seconds()) > 60
                            )
                            if force or deadline_changed:
                                existing.submission_deadline = rec.submission_deadline
                                existing.official_portal_url = rec.official_portal_url
                                existing.last_synced_at = now
                                if rec.structured_requirements:
                                    existing.structured_requirements = rec.structured_requirements
                                if rec.ingestion_metadata:
                                    existing.ingestion_metadata = rec.ingestion_metadata
                                total_updated += 1
                            else:
                                existing.last_synced_at = now
                                total_skipped += 1
                        else:
                            # Avoid tender_reference collisions across portals to satisfy DB unique constraint
                            candidate_ref = rec.tender_reference
                            ref_collision = await self.tender_repo.get_by_reference(candidate_ref)
                            if ref_collision:
                                prefix = "TK" if rec.source_portal == "TENDERKART" else rec.source_portal
                                candidate_ref = f"{rec.tender_reference} ({prefix}-{rec.source_tender_id[:8]})"

                            # Insert newly discovered tender opportunity
                            new_tender = Tender(
                                id=uuid.uuid4(),
                                tender_reference=candidate_ref,
                                title=rec.title,
                                issuing_authority=rec.issuing_authority,
                                sector=rec.sector,
                                estimated_budget_inr=rec.estimated_budget_inr,
                                emd_amount_inr=rec.emd_amount_inr,
                                msme_emd_exemption=rec.msme_emd_exemption,
                                publication_date=rec.publication_date,
                                submission_deadline=rec.submission_deadline,
                                official_portal_url=rec.official_portal_url,
                                source_portal=rec.source_portal,
                                source_tender_id=rec.source_tender_id,
                                last_synced_at=now,
                                ingestion_metadata=rec.ingestion_metadata,
                                structured_requirements=rec.structured_requirements,
                                processing_status="PENDING",
                            )
                            self.session.add(new_tender)
                            total_ingested += 1

                    await self.session.commit()

                except Exception as p_err:
                    logger.error(
                        "[TenderIngestionService] Error syncing portal %s: %s",
                        connector.portal_name,
                        p_err,
                        exc_info=True,
                    )
                    await self.session.rollback()
                    error_msg = f"{connector.portal_name}: {str(p_err)}"

            final_status = "PARTIAL" if error_msg and (total_ingested > 0 or total_updated > 0) else (
                "FAILED" if error_msg else "SUCCESS"
            )

            run_meta = {
                "limit_per_portal": limit,
                "force": force,
                "fixture_records_count": total_fixtures,
                "live_records_count": total_live,
                "completed_at": now.isoformat(),
            }
            if final_status == "SUCCESS":
                if sync_checkpoints:
                    run_meta["checkpoints"] = sync_checkpoints
                    if "TENDERKART" in sync_checkpoints:
                        run_meta["next_updated_after"] = sync_checkpoints["TENDERKART"]
                tk_conn = self.connectors.get("TENDERKART")
                if tk_conn and getattr(tk_conn, "filter_checkpoints", None):
                    existing_run = await self.run_repo.get_latest_successful_run("TENDERKART")
                    merged_filters = {}
                    if existing_run and existing_run.run_metadata and "filter_checkpoints" in existing_run.run_metadata:
                        merged_filters.update(existing_run.run_metadata["filter_checkpoints"])
                    merged_filters.update(tk_conn.filter_checkpoints)
                    run_meta["filter_checkpoints"] = merged_filters

                apify_conn = self.connectors.get("APIFY")
                if apify_conn and getattr(apify_conn, "last_run_metadata", None):
                    run_meta["apify"] = apify_conn.last_run_metadata

            updated_run = await self.run_repo.update_run(
                run_id=run_id,
                status=final_status,
                tenders_found=total_found,
                tenders_ingested=total_ingested,
                tenders_updated=total_updated,
                tenders_skipped=total_skipped,
                error_message=error_msg,
                run_metadata=run_meta,
            )
            return updated_run

        except Exception as top_err:
            logger.critical("[TenderIngestionService] Ingestion failed: %s", top_err, exc_info=True)
            await self.session.rollback()
            updated_run = await self.run_repo.update_run(
                run_id=run_id,
                status="FAILED",
                tenders_found=total_found,
                tenders_ingested=total_ingested,
                tenders_updated=total_updated,
                tenders_skipped=total_skipped,
                error_message=str(top_err),
            )
            return updated_run
