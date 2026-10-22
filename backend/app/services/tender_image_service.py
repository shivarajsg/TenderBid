import asyncio
import hashlib
import io
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import httpx
from PIL import Image

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

UPLOAD_DIR = Path(settings.UPLOAD_DIR).resolve()
TENDER_IMAGES_DIR = UPLOAD_DIR / "tender_images"
TENDER_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Negative cache for failed lookups (expires in 24 hours)
_negative_cache: Dict[str, float] = {}
# Concurrency locks per normalized key to deduplicate simultaneous lookups
_key_locks: Dict[str, asyncio.Lock] = {}
_global_lock = asyncio.Lock()

# Permitted source whitelist (strictly open Wikimedia Commons / Open Public Domain)
PERMITTED_IMAGE_DOMAINS = {
    "upload.wikimedia.org",
    "commons.wikimedia.org",
}

# Category mapping keywords
CATEGORY_KEYWORDS: List[Tuple[str, List[str]]] = [
    ("automotive-machinery", ["wheel", "hub", "brakes", "axle", "engine", "gear", "transmission", "tatra", "beml", "chassis", "bearing", "machinery", "automotive", "motor", "clutch", "radiator", "suspension"]),
    ("medical-biomedical", ["medical", "ultrasound", "biomedical", "patient", "diagnostic", "hospital", "cardiac", "surgical", "ventilator", "ecg", "gloves", "urine", "mask", "stethoscope", "pharma", "medicines", "diagnostic kit", "oxygen"]),
    ("laboratory-furniture", ["laboratory", "workbench", "cleanroom", "centrifuge", "balance", "pipette", "fume hood", "spectrophotometer", "microscope", "incubator", "autoclave", "lab equipment"]),
    ("computers-electronics", ["laptop", "computer", "server", "iot", "gateway", "processor", "desktop", "cctv", "camera", "microcontroller", "switch", "router", "networking", "workstation", "ups", "monitor", "display"]),
    ("solar-electrical", ["solar", "photovoltaic", "switchgear", "transformer", "inverter", "substation", "generator", "rectifier", "battery", "cables", "electrical", "high-voltage", "lighting", "street light"]),
    ("construction-infrastructure", ["construction", "excavator", "crane", "infrastructure", "civil", "bridge", "road", "cement", "concrete", "steel", "scaffolding", "building", "earthmoving", "pipe", "pipeline"]),
    ("cleaning-housekeeping", ["cleaning", "housekeeping", "scrubber", "sweeper", "sanitation", "waste", "janitorial", "disinfectant", "vacuum", "polythe"]),
    ("vehicles-transportation", ["truck", "vehicle", "bus", "transportation", "ambulance", "car", "fleet", "trailer", "railway", "wagon", "locomotive"]),
    ("industrial-tools", ["lathe", "cnc", "tool", "milling", "drilling", "welding", "micrometer", "caliper", "abrasive", "cutting tool", "grinding", "workshop"]),
    ("agriculture-food", ["agriculture", "meat", "grain", "cold storage", "harvest", "fertilizer", "food", "dairy", "irrigation", "poultry"]),
    ("office-stationery", ["office", "furniture", "printer", "copier", "stationery", "paper", "chair", "desk", "filing", "cabin"]),
    ("logistics-maintenance", ["logistics", "maintenance", "forklift", "overhaul", "repair", "pallet", "warehouse", "depot", "handling", "crane service"]),
    ("professional-training", ["training", "education", "course", "symposium", "workshop", "consultancy", "instructor", "teaching"]),
]


def normalize_query_and_category(title: str, sector: Optional[str] = None) -> Tuple[str, str, str]:
    """
    Derive a clean normalized search query, slug, and category key from tender title and sector.
    Title takes precedence over broad sector.
    """
    title_lower = title.lower()
    sector_lower = (sector or "").lower()

    # Priority 1: Match specific category keywords directly in title using flexible word boundaries
    category_key = "general-procurement"
    for cat, kws in CATEGORY_KEYWORDS:
        if any(re.search(rf'\b{re.escape(kw)}(?:s|es|ing)?\b', title_lower) for kw in kws):
            category_key = cat
            break

    # Priority 2: Fall back to sector if title didn't match a specific category
    if category_key == "general-procurement" and sector_lower:
        for cat, kws in CATEGORY_KEYWORDS:
            if any(re.search(rf'\b{re.escape(kw)}(?:s|es|ing)?\b', sector_lower) for kw in kws):
                category_key = cat
                break

    # Clean title tokens for query
    cleaned = re.sub(r'gem/\d+/[a-z]/\d+|gem-\d+-[a-z]-\d+|\b(gem|cppp|bid|tender|supply|procurement|annual|maintenance|services|contract|rate|part|item|ltd|pvt)\b', ' ', title_lower, flags=re.IGNORECASE)
    tokens = re.findall(r'[a-zA-Z0-9]{3,}', cleaned)

    meaningful_tokens = [t for t in tokens if t not in ("the", "and", "for", "with", "all", "type", "qty", "nos", "version")]
    query_str = " ".join(meaningful_tokens[:5]) or category_key.replace("-", " ")
    query_slug = re.sub(r'[^a-z0-9]+', '-', query_str.lower()).strip('-')[:50] or category_key

    return category_key, query_str, query_slug


class TenderImageService:
    """
    Manages tender image acquisition, local persistent caching, deduplication,
    document image extraction, and category fallback.
    """

    def __init__(self):
        self.client_timeout = 8.0
        self.max_bytes = 2 * 1024 * 1024  # 2MB maximum file size
        self.min_bytes = 10 * 1024         # 10KB minimum file size
        self.min_width = 250
        self.min_height = 180

    async def _get_lock_for_key(self, key: str) -> asyncio.Lock:
        async with _global_lock:
            if key not in _key_locks:
                _key_locks[key] = asyncio.Lock()
            return _key_locks[key]

    def extract_image_from_tender_pdf(self, tender_id: str, pdf_path: str) -> Optional[str]:
        """
        Inspect authentic tender PDF and extract embedded high-resolution technical diagram
        or product photograph if available.
        """
        if not fitz or not os.path.exists(pdf_path):
            return None

        try:
            cached_filename = f"{tender_id}_extracted.jpg"
            dest_path = TENDER_IMAGES_DIR / cached_filename
            if dest_path.exists():
                return f"/api/v1/tenders/{tender_id}/image"

            doc = fitz.open(pdf_path)
            for page_idx in range(min(5, len(doc))):
                page = doc[page_idx]
                image_list = page.get_images(full=True)
                for img_info in image_list:
                    xref = img_info[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image.get("image")
                    ext = base_image.get("ext", "jpg")

                    if image_bytes and len(image_bytes) >= self.min_bytes:
                        try:
                            pil_img = Image.open(io.BytesIO(image_bytes))
                            w, h = pil_img.size
                            if w >= self.min_width and h >= self.min_height:
                                # Convert to RGB and save high quality JPEG
                                rgb_img = pil_img.convert("RGB")
                                rgb_img.save(str(dest_path), "JPEG", quality=85)
                                logger.info(f"Successfully extracted authentic image from tender PDF for {tender_id}")
                                return f"/api/v1/tenders/{tender_id}/image"
                        except Exception as e:
                            logger.debug(f"Failed to parse candidate image in PDF: {e}")
            doc.close()
        except Exception as e:
            logger.warning(f"Error extracting image from PDF for tender {tender_id}: {e}")

        return None

    async def fetch_permitted_online_image(self, category_key: str, query: str, query_slug: str) -> Optional[str]:
        """
        Fetch high-resolution open CC/Public Domain image from Wikimedia Commons API
        with deduplication, timeouts, and validation.
        """
        cached_filename = f"{query_slug}.jpg"
        dest_path = TENDER_IMAGES_DIR / cached_filename

        if dest_path.exists():
            return f"/api/v1/tender-images/{cached_filename}"

        # Check negative cache
        import time
        now = time.time()
        if query_slug in _negative_cache and (now - _negative_cache[query_slug]) < 86400:
            return None

        lock = await self._get_lock_for_key(query_slug)
        async with lock:
            if dest_path.exists():
                return f"/api/v1/tender-images/{cached_filename}"

            try:
                # Search Wikimedia Commons for freely usable product/equipment imagery
                api_url = "https://commons.wikimedia.org/w/api.php"
                params = {
                    "action": "query",
                    "format": "json",
                    "generator": "search",
                    "gsrsearch": f"file:{query} equipment OR machinery OR product",
                    "gsrnamespace": 6,
                    "gsrlimit": 3,
                    "prop": "imageinfo",
                    "iiprop": "url|mime|size|dimensions",
                    "iiurlwidth": 800,
                }
                headers = {"User-Agent": "ProcureX-TenderIntelligence/1.0 (MSME Compliance System)"}

                async with httpx.AsyncClient(timeout=self.client_timeout, follow_redirects=True) as client:
                    resp = await client.get(api_url, params=params, headers=headers)
                    if resp.status_code != 200:
                        _negative_cache[query_slug] = now
                        return None

                    data = resp.json()
                    pages = data.get("query", {}).get("pages", {})
                    if not pages:
                        _negative_cache[query_slug] = now
                        return None

                    # Find first acceptable image
                    selected_url = None
                    for page_id, page_data in pages.items():
                        imageinfo = page_data.get("imageinfo", [{}])[0]
                        mime = imageinfo.get("mime", "")
                        if mime in ("image/jpeg", "image/png", "image/webp"):
                            candidate_url = imageinfo.get("thumburl") or imageinfo.get("url")
                            if candidate_url:
                                # Validate allowed domain
                                from urllib.parse import urlparse
                                parsed = urlparse(candidate_url)
                                if parsed.netloc in PERMITTED_IMAGE_DOMAINS:
                                    selected_url = candidate_url
                                    break

                    if not selected_url:
                        _negative_cache[query_slug] = now
                        return None

                    # Download and validate image bytes
                    img_resp = await client.get(selected_url, headers=headers)
                    if img_resp.status_code != 200 or not img_resp.content:
                        _negative_cache[query_slug] = now
                        return None

                    content = img_resp.content
                    if len(content) < self.min_bytes or len(content) > self.max_bytes:
                        _negative_cache[query_slug] = now
                        return None

                    # Validate with PIL
                    pil_img = Image.open(io.BytesIO(content))
                    w, h = pil_img.size
                    if w < self.min_width or h < self.min_height:
                        _negative_cache[query_slug] = now
                        return None

                    # Save validated image
                    rgb_img = pil_img.convert("RGB")
                    rgb_img.save(str(dest_path), "JPEG", quality=85)
                    logger.info(f"Downloaded and cached permitted image for query '{query_slug}' ({w}x{h}, {len(content)} bytes)")
                    return f"/api/v1/tender-images/{cached_filename}"

            except Exception as e:
                logger.debug(f"Permitted image acquisition skipped for {query_slug}: {e}")
                _negative_cache[query_slug] = now

        return None

    def get_category_fallback_url(self, category_key: str) -> str:
        """Return the seeded monochrome category SVG URL."""
        return f"/images/tender-categories/{category_key}.svg"

    async def get_tender_image_meta(
        self,
        tender_id: str,
        title: str,
        sector: Optional[str] = None,
        downloaded_pdf_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Primary entry point resolving image URL with tiered fallback:
        1. Document-extracted image (genuine technical photo from tender PDF)
        2. Cached / permitted online image (deduplicated by normalized query)
        3. Seeded monochrome category SVG
        """
        category_key, query, query_slug = normalize_query_and_category(title, sector)

        # 1. Check if an extracted PDF image exists or can be extracted
        if downloaded_pdf_path:
            extracted_url = self.extract_image_from_tender_pdf(tender_id, downloaded_pdf_path)
            if extracted_url:
                return {
                    "image_url": extracted_url,
                    "category_key": category_key,
                    "source": "DOCUMENT_EXTRACTED",
                    "query": query,
                    "attribution": "Extracted from official tender specification document",
                    "license": "Government Tender Notice / Public Procurement",
                }

        # Check if an extracted image file already exists on disk
        extracted_file = TENDER_IMAGES_DIR / f"{tender_id}_extracted.jpg"
        if extracted_file.exists():
            return {
                "image_url": f"/api/v1/tenders/{tender_id}/image",
                "category_key": category_key,
                "source": "DOCUMENT_EXTRACTED",
                "query": query,
                "attribution": "Extracted from official tender specification document",
                "license": "Government Tender Notice / Public Procurement",
            }

        # 2. Check if a local cached image already exists for this query slug
        cached_file = TENDER_IMAGES_DIR / f"{query_slug}.jpg"
        if cached_file.exists():
            return {
                "image_url": f"/api/v1/tender-images/{query_slug}.jpg",
                "category_key": category_key,
                "source": "LOCAL_CACHE",
                "query": query,
                "attribution": "Permitted open educational & technical photography",
                "license": "Creative Commons / Public Domain",
            }

        # 3. Fallback immediately to high-quality seeded monochrome category asset
        fallback_url = self.get_category_fallback_url(category_key)
        return {
            "image_url": fallback_url,
            "category_key": category_key,
            "source": "CATEGORY_FALLBACK",
            "query": query,
            "attribution": "ProcureX Curated Technical Vector Architecture",
            "license": "Platform Seeded Asset",
        }


_tender_image_service: Optional[TenderImageService] = None


def get_tender_image_service() -> TenderImageService:
    global _tender_image_service
    if _tender_image_service is None:
        _tender_image_service = TenderImageService()
    return _tender_image_service
