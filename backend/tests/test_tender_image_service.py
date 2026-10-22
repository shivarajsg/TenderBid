import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.tender import Tender
from app.models.user import User
from app.services.tender_image_service import (
    normalize_query_and_category,
    get_tender_image_service,
    PERMITTED_IMAGE_DOMAINS,
)


def test_normalize_query_and_category_examples():
    """Verify keyword and category normalization against prompt requirements."""
    # 1. Automotive component
    cat1, q1, slug1 = normalize_query_and_category("WHEEL HUB ASSY BEML TATRA", "Defence")
    assert cat1 == "automotive-machinery"
    assert "wheel" in q1
    assert "hub" in q1

    # 2. Laboratory Furniture
    cat2, q2, slug2 = normalize_query_and_category("Laboratory Furniture Workstation", "Medical")
    assert cat2 == "laboratory-furniture"

    # 3. Ultrasound Diagnostic Equipment
    cat3, q3, slug3 = normalize_query_and_category("Ultrasound Diagnostic Equipment", "Healthcare")
    assert cat3 == "medical-biomedical"

    # 4. Supply of Laptops
    cat4, q4, slug4 = normalize_query_and_category("Supply of Laptops & Computing Servers", "IT")
    assert cat4 == "computers-electronics"

    # 5. Solar Photovoltaic
    cat5, q5, slug5 = normalize_query_and_category("Solar Photovoltaic Water Pump and Switchgear", "Renewable")
    assert cat5 == "solar-electrical"

    # 6. Housekeeping Services
    cat6, q6, slug6 = normalize_query_and_category("Housekeeping and Sanitation Services", "Facility")
    assert cat6 == "cleaning-housekeeping"


def test_permitted_domain_whitelist():
    """Verify that permitted domains whitelist is strictly maintained."""
    assert "upload.wikimedia.org" in PERMITTED_IMAGE_DOMAINS
    assert "commons.wikimedia.org" in PERMITTED_IMAGE_DOMAINS
    assert "arbitrary-scraped-site.com" not in PERMITTED_IMAGE_DOMAINS


@pytest.mark.asyncio
async def test_tender_image_meta_endpoint(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Verify GET /api/v1/tenders/{tender_id}/image-meta returns valid category and image URL."""
    tender = Tender(
        id=uuid.uuid4(),
        tender_reference="GEM/2026/B/8147726",
        title="WHEEL HUB ASSY BEML TATRA",
        issuing_authority="Ministry of Defence - Department of Military Affairs",
        sector="Automotive",
        submission_deadline=datetime(2026, 12, 31, 14, 30, tzinfo=timezone.utc),
        processing_status="INDEXED",
    )
    db_session.add(tender)
    await db_session.commit()

    resp = await client.get(f"/api/v1/tenders/{tender.id}/image-meta")
    assert resp.status_code == 200
    data = resp.json()
    assert data["category_key"] == "automotive-machinery"
    assert "image_url" in data
    assert data["source"] in ("CATEGORY_FALLBACK", "LOCAL_CACHE", "DOCUMENT_EXTRACTED")
