"""
Verifies that normal TenderBid API returns the newly ingested tender
and metadata accurately.
"""
from datetime import timedelta
import httpx
import asyncio
from app.core.security import create_access_token

async def test_api():
    base_url = "http://127.0.0.1:8000"
    token = create_access_token(
        subject="b4c19058-8470-4219-a5fc-7e3b3d3d3f60",
        role="MSME_USER",
        expires_delta=timedelta(hours=2)
    )
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:

        # 2. Query normal tender-list API
        tenders_resp = await client.get("/api/v1/tenders?limit=50", headers=headers)
        assert tenders_resp.status_code == 200, f"Fetch tenders failed: {tenders_resp.text}"
        data = tenders_resp.json()
        items = data["items"]
        print(f"[API Verification] Retrieved {len(items)} tenders from API (Total in DB: {data['total']}).")

        # 3. Locate the new tender
        new_tender = next((t for t in items if t.get("source_tender_id") == "GEM-2026-B-999888"), None)
        assert new_tender is not None, "Newly ingested tender GEM-2026-B-999888 not found in tender list API response!"
        
        print("\n--- NEWLY INGESTED TENDER IN API ---")
        print(f"ID: {new_tender['id']}")
        print(f"Reference: {new_tender['tender_reference']}")
        print(f"Title: {new_tender['title']}")
        print(f"Issuing Authority: {new_tender['issuing_authority']}")
        print(f"Source Portal: {new_tender['source_portal']}")
        print(f"Source Tender ID: {new_tender['source_tender_id']}")
        print(f"Estimated Budget: INR {float(new_tender['estimated_budget_inr']):,.2f}")
        print(f"EMD Amount: INR {float(new_tender['emd_amount_inr']):,.2f}")
        print(f"MSME EMD Exemption: {new_tender['msme_emd_exemption']}")
        print(f"Submission Deadline: {new_tender['submission_deadline']}")
        print(f"Official Portal URL: {new_tender['official_portal_url']}")
        print(f"Last Synced At: {new_tender['last_synced_at']}")
        print(f"Ingestion Metadata: {new_tender.get('ingestion_metadata')}")
        print("------------------------------------")

        # 4. Filter by portal GEM
        gem_resp = await client.get("/api/v1/tenders?source_portal=GEM", headers=headers)
        gem_data = gem_resp.json()
        print(f"\n[Portal Filter Verification] Filter source_portal=GEM returned {len(gem_data['items'])} tenders.")
        for item in gem_data["items"]:
            assert item["source_portal"] == "GEM", f"Non-GEM tender returned: {item['source_portal']}"
            print(f" - [{item['source_portal']}] {item['source_tender_id']}: {item['title'][:50]}")

        print("\nAPI VERIFICATION SUCCESSFUL: Real new tender is accessible via normal API.")

if __name__ == "__main__":
    asyncio.run(test_api())
