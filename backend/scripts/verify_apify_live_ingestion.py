"""
Live Acceptance Verification Script for Apify India Government Tenders Ingestion
Project: Agentic AI-Powered Tender Intelligence & Compliance Management for MSMEs
Phase: Phase 11 — Optional Automated Government Tender Ingestion (Apify Provider)
Actor: foxlabs/india-government-tenders
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from sqlalchemy import select, func

# Ensure backend root is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.ingestion_run import IngestionRun
from app.models.tender import Tender
from app.services.ingestion.apify_connector import ApifyTenderConnector
from app.services.ingestion.ingestion_service import TenderIngestionService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("verify_apify_live")


async def main():
    print("=" * 80)
    print("APIFY ACTOR LIVE INGESTION ACCEPTANCE TEST")
    print("Actor: foxlabs/india-government-tenders | Provider: APIFY")
    print("=" * 80)

    settings = get_settings()

    # Step 1: Environment & Token Check (Never expose token value)
    has_token = bool(settings.APIFY_API_TOKEN)
    token_len = len(settings.APIFY_API_TOKEN) if has_token else 0
    token_prefix = settings.APIFY_API_TOKEN[:10] + "..." if has_token else "NONE"

    print(f"[*] APIFY_ENABLED: {settings.APIFY_ENABLED}")
    print(f"[*] APIFY_API_TOKEN Configured: {has_token} (length: {token_len}, prefix: {token_prefix})")
    print(f"[*] APIFY_ACTOR_ID: {settings.APIFY_ACTOR_ID}")
    print(f"[*] APIFY_MODE: {settings.APIFY_MODE}")
    print(f"[*] APIFY_MAX_RESULTS: {settings.APIFY_MAX_RESULTS}")

    if not has_token:
        print("\n[!] FATAL: APIFY_API_TOKEN is not configured. Live test cannot proceed.")
        sys.exit(1)

    # Step 2: Live Availability Probe
    print("\n[+] Probing Apify API endpoint and credentials (/users/me)...")
    connector = ApifyTenderConnector()
    availability = await connector.check_availability()
    print(f"    Status: {availability.get('status')}")
    print(f"    Online: {availability.get('online')}")
    print(f"    Authenticated: {availability.get('authenticated')}")
    print(f"    Access Mode: {availability.get('access_mode')}")

    if availability.get("status") != "ACTIVE":
        print(f"\n[!] Probe failed: {availability.get('blocker_details')}")
        sys.exit(1)

    print("    [OK] Apify API credentials authorized and active.")

    # Step 3: Run Live Synchronization (Run 1: Initial Ingestion)
    print("\n[+] Executing live ingestion run 1 (limit=5, mode='list')...")
    async with AsyncSessionLocal() as session:
        service = TenderIngestionService(session, connectors=[connector])
        run_result_1 = await service.sync_portal(source_portal="APIFY", limit=5)

    print("\n--- RUN 1 SUMMARY ---")
    meta1 = run_result_1.run_metadata or {}
    print(f"Run ID: {run_result_1.id}")
    print(f"Status: {run_result_1.status}")
    print(f"Tenders Found: {run_result_1.tenders_found}")
    print(f"Tenders Ingested (New): {run_result_1.tenders_ingested}")
    print(f"Tenders Updated: {run_result_1.tenders_updated}")
    print(f"Tenders Skipped: {run_result_1.tenders_skipped}")
    print(f"Total Live Records: {meta1.get('live_records_count', 0)}")
    print(f"Total Fixtures: {meta1.get('fixture_records_count', 0)}")
    print(f"Run Metadata: {json.dumps(meta1, default=str, indent=2)}")

    assert run_result_1.status == "SUCCESS", f"Run 1 did not succeed: {run_result_1.status}"
    assert meta1.get("fixture_records_count", 0) == 0, "Expected zero fixtures in live authenticated mode"
    assert meta1.get("live_records_count", 0) > 0, "Expected at least 1 live record from Apify actor"

    # Step 4: Verify Persisted Database Records in PostgreSQL
    print("\n[+] Inspecting persisted PostgreSQL tender records for provider='APIFY'...")
    async with AsyncSessionLocal() as session:
        query = select(Tender).where(Tender.source_portal == "APIFY").order_by(Tender.last_synced_at.desc())
        result = await session.execute(query)
        apify_tenders = result.scalars().all()

        print(f"    Total tenders in DB with source_portal='APIFY': {len(apify_tenders)}")
        assert len(apify_tenders) > 0, "No tenders found in DB with source_portal='APIFY'"

        for idx, t in enumerate(apify_tenders[:5], 1):
            meta = t.ingestion_metadata or {}
            print(f"\n    [Record {idx}]")
            print(f"      ID (UUID): {t.id}")
            print(f"      Tender Ref: {t.tender_reference}")
            print(f"      Title: {t.title[:80]}...")
            print(f"      Authority: {t.issuing_authority}")
            print(f"      Sector: {t.sector}")
            print(f"      Budget INR: {t.estimated_budget_inr}")
            print(f"      EMD INR: {t.emd_amount_inr}")
            print(f"      Deadline: {t.submission_deadline}")
            print(f"      Portal URL: {t.official_portal_url}")
            print(f"      Source Tender ID: {t.source_tender_id}")
            print(f"      Provider: {meta.get('provider')}")
            print(f"      Actor ID: {meta.get('actor_id')}")
            print(f"      Origin Portal: {meta.get('origin_portal')}")
            print(f"      Is Fixture: {meta.get('is_fixture')}")
            print(f"      Data Source Mode: {meta.get('data_source_mode')}")
            print(f"      Has Full Documents: {meta.get('has_full_documents')}")
            print(f"      Document Names: {meta.get('document_names')}")

            # Critical assertions for live acceptance
            assert meta.get("is_fixture") is False, "Record must not be marked as fixture!"
            assert meta.get("data_source_mode") == "APIFY_ACTOR_LIVE", "Data source mode must be APIFY_ACTOR_LIVE"
            assert meta.get("provider") == "APIFY", "Provider metadata must be APIFY"
            assert meta.get("has_full_documents") is False, "Must document that full binary files are not included"
            assert isinstance(meta.get("document_names"), list), "document_names must be a list"

    # Step 5: Run Ingestion Run 2 (Idempotency and Duplicate Prevention Verification)
    print("\n[+] Executing live ingestion run 2 (Repeat sync to verify idempotency)...")
    async with AsyncSessionLocal() as session:
        service_2 = TenderIngestionService(session, connectors=[connector])
        run_result_2 = await service_2.sync_portal(source_portal="APIFY", limit=5)

    print("\n--- RUN 2 SUMMARY ---")
    meta2 = run_result_2.run_metadata or {}
    print(f"Run ID: {run_result_2.id}")
    print(f"Status: {run_result_2.status}")
    print(f"Tenders Found: {run_result_2.tenders_found}")
    print(f"Tenders Ingested (New): {run_result_2.tenders_ingested}")
    print(f"Tenders Updated: {run_result_2.tenders_updated}")
    print(f"Tenders Skipped: {run_result_2.tenders_skipped}")
    print(f"Total Live Records: {meta2.get('live_records_count', 0)}")
    print(f"Total Fixtures: {meta2.get('fixture_records_count', 0)}")

    # Critical idempotency assertion: zero new records should be inserted on repeat run
    assert run_result_2.tenders_ingested == 0, (
        f"Expected 0 newly ingested tenders on repeat sync, got {run_result_2.tenders_ingested}"
    )
    assert run_result_2.tenders_skipped + run_result_2.tenders_updated > 0, (
        "Expected existing records to be skipped or updated"
    )

    async with AsyncSessionLocal() as session:
        query_count = select(func.count(Tender.id)).where(Tender.source_portal == "APIFY")
        count_after = (await session.execute(query_count)).scalar()
        print(f"\n    [Deduplication Confirmed] Total APIFY tenders in DB remains: {count_after}")
        assert count_after == len(apify_tenders), "Tender table count grew unexpectedly during repeat sync!"

    print("\n" + "=" * 80)
    print("ALL APIFY LIVE ACCEPTANCE GATES PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
