import asyncio
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set
import httpx

from app.core.config import get_settings
from app.services.ingestion.base_connector import BaseTenderConnector, RawTenderRecord

logger = logging.getLogger(__name__)

# Canonical high-fidelity GeM tender catalog for automated ingestion & offline resiliency
CANONICAL_GEM_TENDERS: List[Dict[str, Any]] = [
    {
        "source_tender_id": "GEM-2026-B-892101",
        "tender_reference": "GEM/2026/B/892101",
        "title": "Supply, Installation & Commissioning of Industrial IoT Gateway Nodes and Telemetry Sensors",
        "issuing_authority": "Bharat Heavy Electricals Limited (BHEL) - Electronics Division",
        "sector": "Industrial Electronics & Telemetry",
        "estimated_budget_inr": Decimal("4850000.00"),
        "emd_amount_inr": Decimal("97000.00"),
        "msme_emd_exemption": True,
        "days_to_deadline": 14,
        "official_portal_url": "https://bidplus.gem.gov.in/showbidDocument/GEM-2026-B-892101",
        "structured_requirements": {
            "minimum_annual_turnover_inr": 2500000.0,
            "required_experience_years": 2,
            "mandatory_certifications": ["ISO 9001:2015", "CE Certification", "RoHS Compliance"],
            "mandatory_documents": [
                "GST Registration Certificate",
                "Udyam MSME Registration Certificate",
                "OEM Authorization Certificate",
                "Last 2 Years Audited Balance Sheet",
            ],
            "technical_clauses": [
                "Gateway must support dual SIM 4G/LTE failover and Modbus RTU/TCP protocols.",
                "Enclosure ingress protection must be minimum IP65 rated for industrial outdoor installation.",
            ],
        },
        "ingestion_metadata": {
            "gem_category": "Electronics & Information Technology Goods",
            "gem_bid_type": "Custom Bid for Services and Goods",
            "delivery_location": "BHEL Haridwar & Bengaluru Units",
            "consignee_reporting_officer": "DGM (Materials Management)",
            "is_fixture": True,
            "data_source_mode": "CANONICAL_SCHEMA_FIXTURE",
        },
    },
    {
        "source_tender_id": "GEM-2026-B-892102",
        "tender_reference": "GEM/2026/B/892102",
        "title": "Turnkey Implementation of Rooftop Grid-Tied Solar Photovoltaic Power Plant (150 kWp)",
        "issuing_authority": "National Institute of Technology (NIT) Durgapur",
        "sector": "Renewable Energy & Solar Infrastructure",
        "estimated_budget_inr": Decimal("8200000.00"),
        "emd_amount_inr": Decimal("164000.00"),
        "msme_emd_exemption": True,
        "days_to_deadline": 21,
        "official_portal_url": "https://bidplus.gem.gov.in/showbidDocument/GEM-2026-B-892102",
        "structured_requirements": {
            "minimum_annual_turnover_inr": 4000000.0,
            "required_experience_years": 3,
            "mandatory_certifications": ["ISO 9001:2015", "MNRE Empanelled Vendor", "IEC 61215/61730"],
            "mandatory_documents": [
                "GST Registration Certificate",
                "Udyam MSME Registration",
                "Electrical Contractor License Grade A",
                "Solar PV System Past Performance Certificates",
            ],
            "technical_clauses": [
                "Mono-crystalline PERC modules with minimum 21% module efficiency.",
                "5-year comprehensive on-site operation and maintenance warranty.",
            ],
        },
        "ingestion_metadata": {
            "gem_category": "Solar Energy Equipment & Turnkey Projects",
            "gem_bid_type": "Packet Bid (Technical + Financial)",
            "delivery_location": "NIT Durgapur Campus, West Bengal",
            "consignee_reporting_officer": "Superintending Engineer (Electrical)",
            "is_fixture": True,
            "data_source_mode": "CANONICAL_SCHEMA_FIXTURE",
        },
    },
    {
        "source_tender_id": "GEM-2026-B-892103",
        "tender_reference": "GEM/2026/B/892103",
        "title": "Comprehensive Annual Maintenance Contract for Hospital Diagnostic Ultrasound Systems",
        "issuing_authority": "All India Institute of Medical Sciences (AIIMS) Rishikesh",
        "sector": "Healthcare & Biomedical Equipment",
        "estimated_budget_inr": Decimal("3100000.00"),
        "emd_amount_inr": Decimal("62000.00"),
        "msme_emd_exemption": True,
        "days_to_deadline": 9,
        "official_portal_url": "https://bidplus.gem.gov.in/showbidDocument/GEM-2026-B-892103",
        "structured_requirements": {
            "minimum_annual_turnover_inr": 1800000.0,
            "required_experience_years": 2,
            "mandatory_certifications": ["ISO 13485:2016", "AERB Authorization"],
            "mandatory_documents": [
                "GST Registration Certificate",
                "Udyam MSME Registration",
                "Manufacturer Authorized Service Provider Certificate",
                "Biomedical Service Engineer Qualification Records",
            ],
            "technical_clauses": [
                "Guaranteed uptime of 95% with 24-hour maximum on-site breakdown response.",
                "Quarterly preventive maintenance and calibration with traceable certificates.",
            ],
        },
        "ingestion_metadata": {
            "gem_category": "Medical Equipment Maintenance & Repair Services",
            "gem_bid_type": "Service Contract",
            "delivery_location": "AIIMS Rishikesh Hospital Complex",
            "consignee_reporting_officer": "Store Officer (Biomedical Engineering)",
            "is_fixture": True,
            "data_source_mode": "CANONICAL_SCHEMA_FIXTURE",
        },
    },
    {
        "source_tender_id": "GEM-2026-B-892104",
        "tender_reference": "GEM/2026/B/892104",
        "title": "Procurement of Ruggedized Enterprise Laptops & High-Performance Workstations for CAD Labs",
        "issuing_authority": "Indian Institute of Space Science and Technology (IIST)",
        "sector": "Information Technology & Hardware",
        "estimated_budget_inr": Decimal("6400000.00"),
        "emd_amount_inr": Decimal("128000.00"),
        "msme_emd_exemption": True,
        "days_to_deadline": 18,
        "official_portal_url": "https://bidplus.gem.gov.in/showbidDocument/GEM-2026-B-892104",
        "structured_requirements": {
            "minimum_annual_turnover_inr": 3500000.0,
            "required_experience_years": 2,
            "mandatory_certifications": ["ISO 9001:2015", "EPEAT Gold / Energy Star 8.0"],
            "mandatory_documents": [
                "GST Registration Certificate",
                "Udyam MSME Certificate",
                "OEM Authorization Form (MAF)",
                "Manufacturer Warranty Commitment Letter (3 Years On-site NBD)",
            ],
            "technical_clauses": [
                "Workstations must have minimum 64GB DDR5 ECC RAM and NVIDIA RTX A4000 GPU.",
                "Laptops must meet MIL-STD-810H environmental durability standards.",
            ],
        },
        "ingestion_metadata": {
            "gem_category": "Computer Equipment and Accessories",
            "gem_bid_type": "Standard Product Bid",
            "delivery_location": "IIST Valiamala Campus, Thiruvananthapuram",
            "consignee_reporting_officer": "Head, Computer Center",
            "is_fixture": True,
            "data_source_mode": "CANONICAL_SCHEMA_FIXTURE",
        },
    },
]


class GeMTenderConnector(BaseTenderConnector):
    """
    Official Government e-Marketplace (GeM) Procurement Connector.
    Supports both:
    1. Real-time public tender discovery from GeM Bidding Portal (bidplus.gem.gov.in/all-bids-data)
       with automatic CSRF extraction, pagination, and official PDF document URL generation.
    2. Resilient fallback to verified canonical GeM procurement notices for offline/test environments.
    """

    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.GEM_API_KEY
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        }
        self.last_sync_checkpoint: Optional[str] = None
        self.last_crawl_metadata: Optional[Dict[str, Any]] = None

    @property
    def portal_name(self) -> str:
        return "GEM"

    @property
    def portal_title(self) -> str:
        return "Government e-Marketplace (GeM)"

    @property
    def official_url(self) -> str:
        return "https://bidplus.gem.gov.in/all-bids"

    async def check_availability(self) -> Dict[str, Any]:
        """Probe GeM portal accessibility and document operational status."""
        status_info = {
            "portal_name": self.portal_name,
            "portal_title": self.portal_title,
            "official_url": self.official_url,
            "authenticated": bool(self.api_key),
            "access_mode": "Live GeM Public Listing & Document Portal" if not self.api_key else "Direct Partner REST API",
            "online": True,
            "status": "ACTIVE",
            "blocker_details": None,
        }

        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, headers=self.headers) as client:
                resp = await client.get(self.official_url)
                if resp.status_code < 400:
                    status_info["online"] = True
                    status_info["status"] = "ACTIVE"
                else:
                    status_info["status"] = "DEGRADED"
                    status_info["blocker_details"] = f"GeM returned HTTP {resp.status_code}"
        except Exception as e:
            logger.debug("GeM online probe notice: %s", e)
            status_info["online"] = False
            status_info["status"] = "OFFLINE_FALLBACK"
            status_info["blocker_details"] = str(e)

        return status_info

    async def fetch_tenders(
        self,
        limit: int = 50,
        start_page: int = 1,
        mode: str = "live",
        fallback_to_fixture: bool = False,
        max_pages: Optional[int] = None,
    ) -> List[RawTenderRecord]:
        """
        Fetch and normalize live GeM tender notices with pagination.

        Live mode (default, mode="live"):
        - Queries live GeM portal with CSRF session and pagination.
        - Preserves genuine live records.
        - Does NOT silently substitute fixture data on network/parsing errors.
        - Reports partial crawls or honest exceptions.

        Fixture mode (mode="fixture" or fallback_to_fixture=True):
        - Provides verified canonical GeM catalog notices for regression testing and offline demo mode.
        """
        if mode == "fixture":
            return self._fetch_canonical_fallback(limit=limit)

        try:
            live_records = await self._fetch_live_gem_bids(
                limit=limit,
                start_page=start_page,
                max_pages=max_pages,
            )
            if not live_records:
                if fallback_to_fixture:
                    logger.warning("[GeM Connector] Live GeM fetch returned 0 records. Falling back to canonical catalog.")
                    return self._fetch_canonical_fallback(limit=limit)
                raise RuntimeError("GeM live portal returned 0 records for requested pages.")
            return live_records
        except Exception as exc:
            if fallback_to_fixture:
                logger.warning("[GeM Connector] Live GeM fetch failed (%s). Falling back to canonical catalog.", exc)
                return self._fetch_canonical_fallback(limit=limit)
            logger.error("[GeM Connector] Live GeM fetch failed: %s", exc)
            raise

    @staticmethod
    def _parse_portal_datetime(raw_str: str, default: datetime) -> datetime:
        """Parse GeM portal datetime strings preserving UTC precision."""
        if not raw_str or raw_str.startswith("-"):
            return default
        raw = raw_str.strip()
        try:
            clean = raw.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(clean)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            if parsed.year >= 2024:
                return parsed
        except Exception:
            pass

        for fmt in ("%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%d-%m-%Y", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
            try:
                parsed = datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
                if parsed.year >= 2024:
                    return parsed
            except Exception:
                pass

        return default

    async def _fetch_live_gem_bids(
        self,
        limit: int = 50,
        start_page: int = 1,
        max_pages: Optional[int] = None,
    ) -> List[RawTenderRecord]:
        """
        Fetch ongoing bids directly from bidplus.gem.gov.in/all-bids-data using live pagination.
        - Obtains CSRF and session cookies from initial listing.
        - Determines dynamic total record count from GeM Solr numFound.
        - Crawls pages starting from start_page.
        - Deduplicates bids across pages using unique b_id / b_bid_number.
        - Updates checkpoint and crawl metadata.
        """
        records: List[RawTenderRecord] = []
        seen_bid_ids: Set[str] = set()
        unretrieved_pages: List[int] = []
        errors_encountered: List[str] = []
        now = datetime.now(timezone.utc)

        total_portal_records = 0
        total_portal_pages = 0

        # Calculate pages to fetch in this batch (GeM yields 10 bids per page)
        effective_limit = max(1, limit) if limit else 50
        pages_needed = max(1, (effective_limit + 9) // 10)
        if max_pages is not None:
            pages_needed = min(pages_needed, max_pages)
        # Cap batch to prevent socket timeout (max 100 pages = 1000 tenders per batch)
        pages_needed = min(pages_needed, 100)

        end_page = start_page + pages_needed - 1

        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True, headers=self.headers) as client:
            # Step 1: Request all-bids page to obtain CSRF token and session cookies
            init_resp = await client.get(self.official_url)
            if init_resp.status_code != 200:
                raise RuntimeError(f"GeM initial page returned HTTP {init_resp.status_code}")

            csrf_match = re.search(r"'csrf_bd_gem_nk':\s*'([a-f0-9]+)'", init_resp.text)
            if not csrf_match:
                raise RuntimeError("Could not extract CSRF token from GeM portal page")

            csrf_token = csrf_match.group(1)

            # Step 2: Iterate across pages
            last_crawled_page = start_page - 1
            for page_num in range(start_page, end_page + 1):
                if len(records) >= effective_limit:
                    break
                if total_portal_pages > 0 and page_num > total_portal_pages:
                    logger.info("[GeM Connector] Reached end of GeM catalog at page %d (total %d)", page_num, total_portal_pages)
                    break

                # Safe request pacing between pages
                if page_num > start_page:
                    await asyncio.sleep(0.15)

                postdata = {
                    "page": page_num,
                    "param": {"searchBid": "", "searchType": "fullText"},
                    "filter": {
                        "bidStatusType": "ongoing_bids",
                        "byType": "all",
                        "highBidValue": "",
                        "byEndDate": {},
                        "sort": "Bid-End-Date-Oldest",
                    },
                }

                try:
                    resp = await client.post(
                        "https://bidplus.gem.gov.in/all-bids-data",
                        data={"payload": json.dumps(postdata), "csrf_bd_gem_nk": csrf_token},
                        headers={
                            "X-Requested-With": "XMLHttpRequest",
                            "Referer": self.official_url,
                            "Origin": "https://bidplus.gem.gov.in",
                        },
                    )
                except Exception as req_err:
                    logger.warning("[GeM Connector] Page %d network error: %s", page_num, req_err)
                    unretrieved_pages.append(page_num)
                    errors_encountered.append(f"Page {page_num}: {str(req_err)}")
                    if not records:
                        raise RuntimeError(f"GeM network error on page {page_num}: {str(req_err)}")
                    break

                if resp.status_code != 200:
                    logger.warning("[GeM Connector] Page %d returned HTTP %d", page_num, resp.status_code)
                    unretrieved_pages.append(page_num)
                    errors_encountered.append(f"Page {page_num}: HTTP {resp.status_code}")
                    if not records:
                        raise RuntimeError(f"GeM page {page_num} returned HTTP {resp.status_code}")
                    break

                try:
                    payload = resp.json()
                except Exception as json_err:
                    logger.warning("[GeM Connector] Page %d response was not valid JSON", page_num)
                    unretrieved_pages.append(page_num)
                    errors_encountered.append(f"Page {page_num}: Invalid JSON")
                    if not records:
                        raise RuntimeError(f"GeM page {page_num} returned non-JSON response")
                    break

                resp_sub = payload.get("response", {}).get("response", {})
                num_found = resp_sub.get("numFound", 0)
                if num_found > 0:
                    total_portal_records = num_found
                    total_portal_pages = (total_portal_records + 9) // 10

                docs = resp_sub.get("docs", [])
                if not docs:
                    logger.info("[GeM Connector] No documents returned on page %d; pagination reached end of results", page_num)
                    last_crawled_page = page_num
                    break

                last_crawled_page = page_num

                for doc in docs:
                    if len(records) >= effective_limit:
                        break

                    b_id = doc.get("b_id", [doc.get("id")])[0]
                    b_bid_number = doc.get("b_bid_number", [""])[0]
                    if not b_bid_number or not b_id:
                        continue

                    str_bid_id = str(b_id)
                    if str_bid_id in seen_bid_ids:
                        continue
                    seen_bid_ids.add(str_bid_id)

                    category = doc.get("b_category_name", [""])[0]
                    quantity = doc.get("b_total_quantity", [None])[0]
                    b_bid_type = doc.get("b_bid_type", [0])[0]
                    b_eval_type = doc.get("b_eval_type", [0])[0]
                    min_name = doc.get("ba_official_details_minName", [""])[0]
                    dept_name = doc.get("ba_official_details_deptName", [""])[0]
                    start_str = doc.get("final_start_date_sort", [""])[0]
                    end_str = doc.get("final_end_date_sort", [""])[0]

                    # Document URL classification following GeM frontend rules
                    is_ra = (b_bid_type in (2, 5)) or ("/R/" in b_bid_number) or ("/RA/" in b_bid_number)
                    if b_bid_type == 5:
                        doc_path = "showdirectradocumentPdf"
                    elif b_bid_type == 2:
                        doc_path = "list-ra-schedules" if b_eval_type > 0 else "showradocumentPdf"
                    elif is_ra:
                        doc_path = "showradocumentPdf"
                    else:
                        doc_path = "showbidDocument"

                    official_doc_url = f"https://bidplus.gem.gov.in/{doc_path}/{b_id}"

                    # Parse submission deadline
                    default_deadline = now + timedelta(days=14)
                    deadline = self._parse_portal_datetime(end_str, default_deadline)

                    # Parse publication date
                    default_pub = now - timedelta(days=1)
                    pub_date = self._parse_portal_datetime(start_str, default_pub)

                    authority = f"{min_name} - {dept_name}".strip(" -") or "Government e-Marketplace (GeM)"
                    title = category or f"Procurement Notice: {b_bid_number}"

                    record = RawTenderRecord(
                        tender_reference=b_bid_number,
                        title=title[:255],
                        issuing_authority=authority[:255],
                        sector="Public Procurement & Supplies",
                        submission_deadline=deadline,
                        source_portal=self.portal_name,
                        source_tender_id=str_bid_id,
                        estimated_budget_inr=None,
                        emd_amount_inr=None,
                        msme_emd_exemption=True,
                        publication_date=pub_date,
                        official_portal_url=official_doc_url,
                        structured_requirements={
                            "category": category,
                            "quantity": quantity,
                            "is_reverse_auction": is_ra,
                            "mandatory_documents": [
                                "GST Registration Certificate",
                                "Udyam MSME Registration Certificate",
                            ],
                        },
                        ingestion_metadata={
                            "gem_bid_id": str_bid_id,
                            "gem_category": category,
                            "gem_quantity": quantity,
                            "gem_bid_type": b_bid_type,
                            "is_reverse_auction": is_ra,
                            "ministry": min_name,
                            "department": dept_name,
                            "total_portal_records": total_portal_records,
                            "page_discovered": page_num,
                            "is_fixture": False,
                            "data_source_mode": "LIVE_GEM_PORTAL",
                            "last_retrieved_at": now.isoformat(),
                            "raw_payload": {
                                "bidId": str_bid_id,
                                "bidNumber": b_bid_number,
                                "category": category,
                                "quantity": quantity,
                                "ministry": min_name,
                                "department": dept_name,
                                "documentUrl": official_doc_url,
                                "tenderUrl": official_doc_url,
                                "pdfUrl": official_doc_url,
                            },
                        },
                    )
                    records.append(record)

        # Step 3: Compute checkpoint & crawl metadata
        crawl_exhausted = bool(total_portal_pages > 0 and last_crawled_page >= total_portal_pages)
        next_page = 1 if crawl_exhausted else last_crawled_page + 1

        self.last_sync_checkpoint = json.dumps({
            "next_page": next_page,
            "last_page": last_crawled_page,
            "total_records": total_portal_records,
        })

        pages_processed = max(0, last_crawled_page - start_page + 1)
        self.last_crawl_metadata = {
            "total_portal_records": total_portal_records,
            "total_pages_available": total_portal_pages,
            "start_page": start_page,
            "end_page_crawled": last_crawled_page,
            "next_page": next_page,
            "pages_processed": pages_processed,
            "unique_bids_discovered": len(records),
            "unretrieved_pages": unretrieved_pages,
            "errors_encountered": errors_encountered,
            "crawl_completed": crawl_exhausted,
            "is_partial": not crawl_exhausted,
            "last_retrieved_at": now.isoformat(),
        }

        return records

    def _fetch_canonical_fallback(self, limit: int = 50) -> List[RawTenderRecord]:
        """Ingest canonical high-fidelity GeM notices for offline resilience."""
        records: List[RawTenderRecord] = []
        now = datetime.now(timezone.utc)

        for item in CANONICAL_GEM_TENDERS[:limit]:
            deadline = now + timedelta(days=item["days_to_deadline"])
            pub_date = now - timedelta(days=2)

            record = RawTenderRecord(
                tender_reference=item["tender_reference"],
                title=item["title"],
                issuing_authority=item["issuing_authority"],
                sector=item["sector"],
                submission_deadline=deadline,
                source_portal=self.portal_name,
                source_tender_id=item["source_tender_id"],
                estimated_budget_inr=item["estimated_budget_inr"],
                emd_amount_inr=item["emd_amount_inr"],
                msme_emd_exemption=item["msme_emd_exemption"],
                publication_date=pub_date,
                official_portal_url=item["official_portal_url"],
                structured_requirements=item["structured_requirements"],
                ingestion_metadata=item["ingestion_metadata"],
            )
            records.append(record)

        logger.info("[GeM Connector] Retrieved %d canonical fallback records.", len(records))
        return records
