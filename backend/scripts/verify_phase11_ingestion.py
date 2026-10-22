"""
Verification script for Phase 11 Ingestion Acceptance Test.
Tests live PostgreSQL ingestion, scheduler run history, idempotency,
new tender ingestion path, and API retrieval.
"""
import asyncio
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import select, func

from app.db.session import AsyncSessionLocal
from app.models.ingestion_run import IngestionRun
from app.models.tender import Tender
from app.services.ingestion.base_connector import BaseTenderConnector, RawTenderRecord
from app.services.ingestion.ingestion_service import TenderIngestionService


class DynamicControlledConnector(BaseTenderConnector):
    """Controlled connector simulating discovery of an authorized new tender notice."""

    @property
    def portal_name(self) -> str:
        return "GEM"

    @property
    def portal_title(self) -> str:
        return "Government e-Marketplace (GeM) - Controlled Ingestion Channel"

    @property
    def official_url(self) -> str:
        return "https://gem.gov.in"

    async def check_availability(self):
        return {"portal_name": "GEM", "status": "ACTIVE", "access_mode": "Controlled Verified Ingestion"}

    async def fetch_tenders(self, limit: int = 50):
        now = datetime.now(timezone.utc)
        return [
            RawTenderRecord(
                tender_reference="GEM/2026/B/999888",
                title="Automated Supply of Edge AI Telemetry Computing Units for Smart Grid Substations",
                issuing_authority="Power Grid Corporation of India Limited (POWERGRID)",
                sector="Smart Grid Telemetry & AI Hardware",
                submission_deadline=now + timedelta(days=20),
                source_portal="GEM",
                source_tender_id="GEM-2026-B-999888",
                estimated_budget_inr=Decimal("9500000.00"),
                emd_amount_inr=Decimal("190000.00"),
                msme_emd_exemption=True,
                publication_date=now - timedelta(days=1),
                official_portal_url="https://bidplus.gem.gov.in/showbidDocument/GEM-2026-B-999888",
                structured_requirements={
                    "minimum_annual_turnover_inr": 4750000.0,
                    "required_experience_years": 3,
                    "mandatory_certifications": ["ISO 9001:2015", "IEC 61850 Certified"],
                    "mandatory_documents": ["GST Registration", "Udyam MSME Certificate"],
                },
                ingestion_metadata={"procurement_type": "High-Priority Grid Infrastructure"},
            )
        ]


async def run_verification():
    print("=" * 70)
    print("PHASE 11 LIVE INGESTION ACCEPTANCE TEST SUITE")
    print("=" * 70)

    async with AsyncSessionLocal() as session:
        # 1. Inspect existing Ingestion Runs
        run_res = await session.execute(
            select(IngestionRun).order_by(IngestionRun.started_at.desc())
        )
        runs = run_res.scalars().all()
        print(f"\n[Step 1] Ingestion Runs Audit Log in PostgreSQL: {len(runs)} run(s) recorded.")
        for r in runs[:3]:
            print(f" - Run ID: {r.id}")
            print(f"   Portal: {r.source_portal} | Status: {r.status}")
            print(f"   Found: {r.tenders_found} | Ingested: {r.tenders_ingested} | Updated: {r.tenders_updated} | Skipped: {r.tenders_skipped}")
            print(f"   Started: {r.started_at} | Completed: {r.completed_at}")

        # 2. Inspect Ingested Tenders
        tenders_res = await session.execute(
            select(Tender).where(Tender.source_portal.is_not(None)).order_by(Tender.created_at.desc())
        )
        ingested_tenders = tenders_res.scalars().all()
        print(f"\n[Step 2] Ingested Tenders currently committed in PostgreSQL: {len(ingested_tenders)} tender(s).")
        for t in ingested_tenders:
            print(f" - [{t.source_portal}] {t.tender_reference} | ExtID: {t.source_tender_id}")
            print(f"   Title: {t.title[:65]}...")
            print(f"   Authority: {t.issuing_authority}")
            print(f"   Budget: INR {t.estimated_budget_inr:,.2f} | Deadline: {t.submission_deadline}")
            print(f"   Official URL: {t.official_portal_url}")
            print(f"   Last Synced: {t.last_synced_at}")

        # 3. Test Idempotency (Re-running sync on existing catalogue)
        print("\n[Step 3] Testing Synchronization Idempotency on existing data...")
        service = TenderIngestionService(session)
        t0 = time.time()
        idemp_run = await service.sync_portal(source_portal="ALL", force=False)
        dur = time.time() - t0
        print(f" - Sync execution time: {dur:.3f}s")
        print(f" - Status: {idemp_run.status}")
        print(f" - Tenders Found: {idemp_run.tenders_found}")
        print(f" - Tenders Newly Ingested: {idemp_run.tenders_ingested} (MUST BE 0)")
        print(f" - Tenders Skipped (Deduplicated): {idemp_run.tenders_skipped}")
        assert idemp_run.tenders_ingested == 0, f"Expected 0 new insertions, got {idemp_run.tenders_ingested}"
        print(" -> IDEMPOTENCY VERIFIED: Repeated sync did not create duplicates.")

        # 4. Test New Tender Path with Controlled Dynamic Discovery
        print("\n[Step 4] Testing Full New-Tender Ingestion Path...")
        # Check if test tender already exists and clean it up for pristine test
        existing_test = (await session.execute(
            select(Tender).where(Tender.source_tender_id == "GEM-2026-B-999888")
        )).scalar_one_or_none()
        if existing_test:
            await session.delete(existing_test)
            await session.commit()

        initial_count = (await session.execute(select(func.count(Tender.id)))).scalar_one()

        dynamic_service = TenderIngestionService(
            session,
            connectors=[DynamicControlledConnector()],
        )
        t_start = time.time()
        new_run = await dynamic_service.sync_portal(source_portal="GEM", force=False)
        sync_dur = time.time() - t_start

        print(f" - Discovery Execution Time: {sync_dur:.3f}s")
        print(f" - Records Discovered: {new_run.tenders_found}")
        print(f" - Newly Inserted: {new_run.tenders_ingested}")
        print(f" - Updated: {new_run.tenders_updated}")
        print(f" - Skipped: {new_run.tenders_skipped}")
        assert new_run.tenders_ingested == 1, f"Expected 1 new tender, got {new_run.tenders_ingested}"

        # Verify in PostgreSQL
        committed = (await session.execute(
            select(Tender).where(Tender.source_tender_id == "GEM-2026-B-999888")
        )).scalar_one_or_none()
        assert committed is not None, "Tender was not committed to PostgreSQL"
        print(f" - Committed Tender in DB: {committed.id}")
        print(f"   Reference: {committed.tender_reference}")
        print(f"   Title: {committed.title}")
        print(f"   Portal: {committed.source_portal} | External ID: {committed.source_tender_id}")
        print(f"   Official URL: {committed.official_portal_url}")
        print(f"   Created At: {committed.created_at} | Last Synced: {committed.last_synced_at}")

        # Check total count increased by 1
        new_count = (await session.execute(select(func.count(Tender.id)))).scalar_one()
        assert new_count == initial_count + 1, f"Expected count {initial_count + 1}, got {new_count}"
        print(f" -> Database Count correctly transitioned: {initial_count} -> {new_count}")

        # Re-sync to verify that new tender is also idempotent
        re_run = await dynamic_service.sync_portal(source_portal="GEM", force=False)
        assert re_run.tenders_ingested == 0, "Second sync duplicated the new tender"
        assert re_run.tenders_skipped == 1, "Expected newly inserted tender to be skipped on 2nd sync"
        print(" -> NEW TENDER IDEMPOTENCY VERIFIED: Repeated sync skipped without duplicate.")

    print("\n" + "=" * 70)
    print("ALL LIVE INGESTION ACCEPTANCE CHECKS PASSED SUCCESSFULLY.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_verification())
