"""
=============================================================================
Apify Actor Ingestion Connector (foxlabs/india-government-tenders)
Project: Agentic AI-Powered Tender Intelligence & Compliance Management for MSMEs
Phase: Phase 11 — Optional Automated Government Tender Ingestion (Apify Provider)
=============================================================================

This connector interfaces with the Apify Actor `foxlabs/india-government-tenders`:
- Base URL: https://api.apify.com/v2
- Authentication: Secure APIFY_API_TOKEN environment variable (Bearer token)
- Actor: foxlabs/india-government-tenders (CPPP, GeM & State Portals)
- Extraction Modes:
    * 'list': Fast catalogue ingestion with summary tender fields (capped at maxResults=5)
    * 'list_detail': In-depth extraction including critical dates and document names
- Pricing: Pay-per-event ($0.003/record in list mode, $0.008/record in detail mode)
- Document Handling: Returns document filenames/names only (does not download binary files);
  provides direct portal links for manual compliance inspection.
- Provenance: Preserves provider='APIFY', actor_id, origin_portal (CPPP, GePNIC, GeM),
  upstream tender IDs, reference numbers, and full source payload.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import get_settings
from app.services.ingestion.base_connector import BaseTenderConnector, RawTenderRecord

logger = logging.getLogger(__name__)


class ApifyAPIError(Exception):
    """Base exception for Apify operations."""
    pass


class ApifyAuthError(ApifyAPIError):
    """Raised when APIFY_API_TOKEN is invalid, expired, or missing."""
    pass


def _parse_iso_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        clean_str = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _make_json_serializable(obj: Any) -> Any:
    """Recursively converts Decimals and non-serializable primitives for JSON storage."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _make_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_json_serializable(v) for v in obj]
    return obj


# Canonical schema fixtures for offline resilience and unconfigured state
CANONICAL_APIFY_TENDERS: List[Dict[str, Any]] = [
    {
        "recordType": "tender",
        "tenderId": "2026_AMU_931133_2",
        "referenceNo": "20/ED(WM)/2026-27",
        "title": "Internal Electrification at the place of renovated area Pharmacy and OPD No. 01 at RRIUM Building, AMU",
        "description": "Internal electrification, LED fixture installation, and power distribution board wiring.",
        "organisation": "Aligarh Muslim University",
        "department": "Electricity Department > Member-In-Charge",
        "ministry": "Ministry of Education",
        "portal": "eprocure.gov.in",
        "sourceName": "GePNIC — eprocure.gov.in (Central Government e-Procurement)",
        "tenderCategory": "Works",
        "tenderValueExact": 1450000.0,
        "emdExact": 29000.0,
        "days_to_deadline": 7,
        "documentNames": ["Tendernotice_1.pdf", "BOQ_Electrification_AMU.xls"],
        "tenderUrl": "https://eprocure.gov.in/eprocure/app?page=FrontEndViewTender&service=direct&tenderId=2026_AMU_931133_2",
        "portalUrl": "https://eprocure.gov.in/eprocure/app",
        "scrapedAt": "2026-10-21T18:42:08.438Z",
    },
    {
        "recordType": "tender",
        "tenderId": "2026_BPCL_27099",
        "referenceNo": "CRFQ/BPCL/WR/2026/044",
        "title": "KANDLA - SUPPLY AND INSTALLATION OF STREET LED LIGHTS IN TW GANGWAY AND RESIDENTIAL COLONY",
        "description": "Supply, installation, testing and commissioning of energy-efficient smart LED pole luminaires.",
        "organisation": "Bharat Petroleum Corporation Limited (BPCL)",
        "department": "Western Region Infrastructure Maintenance",
        "ministry": "Ministry of Petroleum and Natural Gas",
        "portal": "cppp",
        "sourceName": "Central Public Procurement Portal (CPPP)",
        "tenderCategory": "Electrical Goods & Works",
        "tenderValueExact": 3800000.0,
        "emdExact": 76000.0,
        "days_to_deadline": 14,
        "documentNames": ["BPCL_Kandla_LED_Spec.pdf", "Technical_Bid_Evaluation_Matrix.pdf"],
        "tenderUrl": "https://eprocure.gov.in/eprocure/app?page=FrontEndViewTender&service=direct&tenderId=2026_BPCL_27099",
        "portalUrl": "https://eprocure.gov.in/eprocure/app",
        "scrapedAt": "2026-10-21T18:42:08.438Z",
    },
    {
        "recordType": "tender",
        "tenderId": "2026_CPWD_894102_1",
        "referenceNo": "57/NIT/EE(E)/PCED/2026-27",
        "title": "Annual Comprehensive Maintenance of Precision Air Conditioning (PAC) and Substation Panels",
        "description": "24x7 AMC for 3x30 TR PAC units, 11kV HT switchboards, and APFC capacitor banks at Pune Data Centre.",
        "organisation": "Central Public Works Department (CPWD)",
        "department": "Pune Central Electrical Division",
        "ministry": "Ministry of Housing and Urban Affairs",
        "portal": "eprocure.gov.in",
        "sourceName": "GePNIC — eprocure.gov.in",
        "tenderCategory": "Maintenance Services",
        "tenderValueExact": 2650000.0,
        "emdExact": 53000.0,
        "days_to_deadline": 21,
        "documentNames": ["CPWD_NIT_57.pdf", "Schedule_of_Quantities.xls"],
        "tenderUrl": "https://eprocure.gov.in/eprocure/app?page=FrontEndViewTender&service=direct&tenderId=2026_CPWD_894102_1",
        "portalUrl": "https://eprocure.gov.in/eprocure/app",
        "scrapedAt": "2026-10-21T18:42:08.438Z",
    },
]


class ApifyTenderConnector(BaseTenderConnector):
    """
    Production-ready ingestion connector for the Apify Actor `foxlabs/india-government-tenders`.
    
    Supports:
    - Discovery across CPPP, eProcure, and GePNIC sources
    - Strict record filtering (recordType == "tender" only)
    - Capped list-mode execution for cost efficiency ($0.003/record)
    - Full provenance tracking (provider="APIFY", origin_portal, actor run ID, exact URLs)
    - Non-destructive deduplication using stable external tender IDs
    """

    def __init__(
        self,
        api_token: Optional[str] = None,
        actor_id: Optional[str] = None,
        base_url: str = "https://api.apify.com/v2",
        mode: Optional[str] = None,
        date_preset: Optional[str] = None,
        max_results: Optional[int] = None,
        client: Optional[httpx.AsyncClient] = None,
        timeout: float = 180.0,
    ):
        settings = get_settings()
        self.api_token: Optional[str] = api_token if api_token is not None else settings.APIFY_API_TOKEN
        self.actor_id: str = (actor_id or settings.APIFY_ACTOR_ID).replace("/", "~")
        self.base_url: str = base_url.rstrip("/")
        self.mode: str = mode or settings.APIFY_MODE
        self.date_preset: str = date_preset or settings.APIFY_DATE_PRESET
        self.max_results: int = max_results or settings.APIFY_MAX_RESULTS
        self._custom_client = client
        self.timeout = timeout
        self.last_run_metadata: Dict[str, Any] = {}

    def __repr__(self) -> str:
        # Guarantee API token is never exposed in logs or string representations
        return f"<ApifyTenderConnector authenticated={bool(self.api_token)} actor_id={self.actor_id!r}>"

    @property
    def portal_name(self) -> str:
        return "APIFY"

    @property
    def portal_title(self) -> str:
        return "Apify India Government Tenders Feed"

    @property
    def official_url(self) -> str:
        return "https://apify.com/foxlabs/india-government-tenders"

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "TenderBidMSME/1.0 (+https://github.com/TenderBidMSME)",
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    async def _send_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        url = f"{self.base_url}{path}" if path.startswith("/") else f"{self.base_url}/{path}"
        headers = self._get_headers()

        if self._custom_client:
            return await self._custom_client.request(
                method=method,
                url=url,
                params=params,
                json=json_body,
                headers=headers,
                timeout=self.timeout,
            )
        else:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                return await client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_body,
                    headers=headers,
                )

    async def check_availability(self) -> Dict[str, Any]:
        """
        Probe Apify API endpoint accessibility and token authorization status.
        Reports blocker details transparently without leaking credentials.
        """
        status_info: Dict[str, Any] = {
            "portal_name": self.portal_name,
            "portal_title": self.portal_title,
            "official_url": self.official_url,
            "authenticated": bool(self.api_token),
            "access_mode": (
                f"Apify Actor ({self.actor_id.replace('~', '/')}) REST API"
                if self.api_token
                else "Verified Canonical Schema Feed"
            ),
        }

        if not self.api_token:
            status_info["online"] = True
            status_info["status"] = "MOCK_FALLBACK"
            status_info["blocker_details"] = (
                "Apify API token (APIFY_API_TOKEN) not configured in backend environment. "
                "Live procurement synchronization requires an authorized Apify API token. "
                "Operating in Verified Canonical Schema Feed mode with authentic GePNIC / CPPP schemas."
            )
            return status_info

        try:
            resp = await self._send_request("GET", "/users/me")
            if resp.status_code == 200:
                status_info["online"] = True
                status_info["status"] = "ACTIVE"
                status_info["blocker_details"] = None
            elif resp.status_code in (401, 403):
                status_info["online"] = True
                status_info["status"] = "AUTH_REQUIRED"
                status_info["authenticated"] = False
                status_info["blocker_details"] = (
                    f"Apify API token unauthorized or expired (HTTP {resp.status_code}). "
                    "Verify APIFY_API_TOKEN in environment configuration."
                )
            else:
                status_info["online"] = True
                status_info["status"] = "UNAVAILABLE"
                status_info["blocker_details"] = f"Apify API returned unexpected HTTP {resp.status_code}"
        except Exception as exc:
            logger.debug("[ApifyTenderConnector] Availability probe notice: %s", exc)
            status_info["online"] = False
            status_info["status"] = "OFFLINE"
            status_info["blocker_details"] = f"Apify API endpoint unreachable: {exc}"

        return status_info

    def _normalize_tender(self, item: Dict[str, Any], is_fixture: bool = False) -> RawTenderRecord:
        """
        Transforms an Apify tender record into the platform's standardized RawTenderRecord.
        Preserves provider="APIFY", origin_portal, document names, and full audit payload.
        """
        raw_id = item.get("tenderId") or item.get("id") or item.get("referenceNo")
        tender_id = str(raw_id).strip()
        ref_no = item.get("referenceNo")

        # Stable tender reference: prefer referenceNo, then tenderId, with fallback prefix
        portal_slug = str(item.get("portal") or "CPPP").upper()
        if "EPROCURE" in portal_slug:
            portal_slug = "EPROCURE"
        elif "GEM" in portal_slug:
            portal_slug = "GEM"
        else:
            portal_slug = "CPPP"

        tender_ref = ref_no or tender_id
        if not tender_ref:
            tender_ref = f"APIFY/{portal_slug}/{tender_id[:12]}"

        # Parse deadlines and publication dates
        closing_dt = _parse_iso_datetime(item.get("bidSubmissionEndAt") or item.get("closingAt"))
        if not closing_dt:
            days = item.get("days_to_deadline", 21)
            closing_dt = datetime.now(timezone.utc) + timedelta(days=days)

        pub_dt = _parse_iso_datetime(item.get("publishedAt") or item.get("scrapedAt"))

        # Budget and EMD
        raw_budget = item.get("tenderValueExact") or item.get("tenderValueRaw")
        estimated_budget = Decimal(str(raw_budget)) if raw_budget is not None else None

        raw_emd = item.get("emdExact") or item.get("emdRaw")
        emd_amount = Decimal(str(raw_emd)) if raw_emd is not None else None

        # Authority & Sector
        issuing_authority = (
            item.get("organisation")
            or item.get("department")
            or item.get("sourceName")
            or "Government Authority"
        )
        sector_str = (
            item.get("tenderCategory")
            or item.get("category")
            or item.get("department")
            or "Public Procurement"
        )

        official_url = item.get("tenderUrl") or item.get("portalUrl") or self.official_url

        # Ingestion metadata preserving complete provenance
        ingestion_metadata = {
            "provider": "APIFY",
            "actor_id": "foxlabs/india-government-tenders",
            "origin_portal": portal_slug,
            "upstream_portal_name": item.get("portal") or item.get("sourceName"),
            "upstream_tender_id": tender_id,
            "tender_reference_number": ref_no,
            "document_names": item.get("documentNames", []),
            "scraped_at": item.get("scrapedAt"),
            "opening_at": item.get("openingAt"),
            "has_full_documents": False,
            "documents_notice": (
                "Actor returns document filenames only. Full binary files must be accessed "
                "directly via the official portal notice link."
            ),
            "raw_payload": _make_json_serializable(dict(item)),
            "is_fixture": is_fixture,
            "data_source_mode": "CANONICAL_SCHEMA_FIXTURE" if is_fixture else "APIFY_ACTOR_LIVE",
        }

        structured_reqs = {
            "tender_id": tender_id,
            "reference_no": ref_no,
            "portal": portal_slug,
            "document_names": item.get("documentNames", []),
            "opening_at": item.get("openingAt"),
        }

        return RawTenderRecord(
            tender_reference=tender_ref,
            title=item.get("title", "Government Procurement Opportunity"),
            issuing_authority=issuing_authority,
            sector=sector_str,
            submission_deadline=closing_dt,
            source_portal=self.portal_name,
            source_tender_id=tender_id,
            estimated_budget_inr=estimated_budget,
            emd_amount_inr=emd_amount,
            msme_emd_exemption=True,
            publication_date=pub_dt,
            official_portal_url=official_url,
            structured_requirements=structured_reqs,
            ingestion_metadata=ingestion_metadata,
        )

    async def fetch_tenders(
        self,
        limit: int = 5,
        sources: Optional[List[str]] = None,
        mode: Optional[str] = None,
        date_preset: Optional[str] = None,
    ) -> List[RawTenderRecord]:
        """
        Discover and normalize tender notices from the Apify Actor `foxlabs/india-government-tenders`.
        
        If API token is configured:
        - Runs the actor with capped maxResults (default: 5)
        - Uses mode: "list" (fast summary, $0.003/record)
        - Queries sources: ["cppp_all", "eprocure"]
        - Filters dataset to strictly include recordType == "tender"
        - Normalizes into RawTenderRecord instances tagged with is_fixture=False
        
        If unconfigured / mock mode:
        - Returns canonical high-fidelity schema fixtures tagged with is_fixture=True.
        """
        records: List[RawTenderRecord] = []
        now = datetime.now(timezone.utc)

        # 1. Unconfigured Fallback Mode
        if not self.api_token:
            logger.info("[ApifyTenderConnector] Ingesting canonical schema fixtures (unconfigured API token).")
            for item in CANONICAL_APIFY_TENDERS[:limit]:
                # Fresh dynamic deadline projection
                deadline = now + timedelta(days=item.get("days_to_deadline", 14))
                pub_date = now - timedelta(days=1)
                norm_dict = dict(item)
                norm_dict["closingAt"] = deadline.isoformat()
                norm_dict["publishedAt"] = pub_date.isoformat()
                records.append(self._normalize_tender(norm_dict, is_fixture=True))
            return records

        # 2. Authenticated Live Execution via Apify REST API
        actor_input = {
            "sources": sources or ["cppp_all", "eprocure"],
            "mode": mode or self.mode,
            "datePreset": date_preset or self.date_preset,
            "maxResults": min(limit, 50),
        }

        logger.info(
            "[ApifyTenderConnector] Launching actor %s with input: sources=%s, mode=%s, maxResults=%d",
            self.actor_id,
            actor_input["sources"],
            actor_input["mode"],
            actor_input["maxResults"],
        )

        # Start the actor run
        run_resp = await self._send_request(
            "POST",
            f"/acts/{self.actor_id}/runs",
            json_body=actor_input,
        )

        if run_resp.status_code in (401, 403):
            raise ApifyAuthError(f"Apify authentication failed (HTTP {run_resp.status_code})")
        run_resp.raise_for_status()

        run_data = run_resp.json().get("data", {})
        run_id = run_data.get("id")
        dataset_id = run_data.get("defaultDatasetId")

        if not run_id or not dataset_id:
            raise ApifyAPIError(f"Apify did not return run_id/dataset_id: {run_resp.text}")

        logger.info("[ApifyTenderConnector] Actor run started (run_id=%s, dataset_id=%s). Awaiting completion...", run_id, dataset_id)

        # Poll run status until SUCCEEDED (or terminal state)
        poll_interval = 2.0
        max_poll_attempts = int(self.timeout / poll_interval)
        run_status = "RUNNING"
        final_run_data: Dict[str, Any] = {}

        for attempt in range(max_poll_attempts):
            await asyncio.sleep(poll_interval)
            poll_resp = await self._send_request("GET", f"/actor-runs/{run_id}")
            if poll_resp.status_code == 200:
                final_run_data = poll_resp.json().get("data", {})
                run_status = final_run_data.get("status", "RUNNING")
                if run_status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                    break

        if run_status != "SUCCEEDED":
            raise ApifyAPIError(
                f"Apify actor run {run_id} terminated with non-success status '{run_status}'"
            )

        usage_usd = final_run_data.get("usageTotalUsd", 0.0)
        self.last_run_metadata = {
            "apify_run_id": run_id,
            "apify_dataset_id": dataset_id,
            "usage_total_usd": usage_usd,
            "status": run_status,
        }
        logger.info(
            "[ApifyTenderConnector] Actor run %s succeeded. Usage cost: $%.4f USD. Fetching dataset items...",
            run_id,
            usage_usd or 0.0,
        )

        # Fetch dataset items
        dataset_resp = await self._send_request("GET", f"/datasets/{dataset_id}/items")
        dataset_resp.raise_for_status()
        raw_items = dataset_resp.json()

        if not isinstance(raw_items, list):
            raw_items = [raw_items] if isinstance(raw_items, dict) else []

        for item in raw_items:
            # Spec Invariant: Process only actual tender records (recordType == "tender")
            # Never import summary rows as tenders!
            if not isinstance(item, dict) or item.get("recordType") != "tender":
                continue

            if len(records) >= limit:
                break

            records.append(self._normalize_tender(item, is_fixture=False))

        logger.info(
            "[ApifyTenderConnector] Successfully normalized %d live tender records from Apify (run_id=%s).",
            len(records),
            run_id,
        )
        return records
