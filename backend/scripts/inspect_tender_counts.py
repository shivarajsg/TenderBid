import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import AsyncSessionLocal
from sqlalchemy import text

async def query_tenders():
    async with AsyncSessionLocal() as session:
        # Total count
        total_res = await session.execute(text("SELECT count(*) FROM tenders"))
        total = total_res.scalar()

        # Grouped by source portal
        group_res = await session.execute(text("""
            SELECT 
                source_portal, 
                count(*) as total_count,
                count(*) FILTER (WHERE (ingestion_metadata->>'is_fixture')::boolean = true) as fixture_count,
                count(*) FILTER (WHERE (ingestion_metadata->>'is_fixture')::boolean = false) as live_count,
                count(*) FILTER (WHERE ingestion_metadata->>'is_fixture' IS NULL) as unflagged_count
            FROM tenders 
            GROUP BY source_portal 
            ORDER BY total_count DESC
        """))
        rows = group_res.fetchall()

        print(f"TOTAL_PERSISTED_TENDERS: {total}")
        print("--- GROUPED BY SOURCE PORTAL ---")
        for r in rows:
            portal = r[0] or "NONE"
            print(f"Portal: {portal:<15} Total: {r[1]:<5} Fixtures: {r[2]:<5} Live: {r[3]:<5} Unflagged: {r[4]:<5}")

if __name__ == "__main__":
    asyncio.run(query_tenders())
