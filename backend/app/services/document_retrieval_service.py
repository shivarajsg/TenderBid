"""
=============================================================================
Tender Document Retrieval & Verification Service
Project: Agentic AI-Powered Tender Intelligence & Compliance Management for MSMEs
=============================================================================

Secure, authenticated document retrieval pipeline:
1. URL Examination & Classification:
   - Differentiates direct PDF documents, interactive official HTML bid pages,
     and restricted/unavailable links.
2. Enterprise Security & SSRF Protection:
   - Domain whitelisting (*.gov.in, *.nic.in, tenderkart.in, apify.com).
   - Blocks private/loopback/link-local IPv4/IPv6 ranges and metadata services.
   - Strict connection/read timeouts and chunked stream capping (50 MB limit).
3. Format & Integrity Verification:
   - Verifies response status and Content-Type.
   - Enforces file signature validation (magic bytes %PDF-).
   - Validates internal PDF document structure and page count with PyMuPDF.
4. Vault Storage & Deduplication:
   - Non-destructive deduplication via SHA-256 and (tender_id, sha256).
   - Avoids silent overwrites of already stored documents.
5. Ingestion into Vector & Relational Storage:
   - Triggers extraction, physical page tracking, recursive chunking,
     and indexing into ChromaDB and PostgreSQL document_chunks.
"""

from dataclasses import dataclass
import hashlib
import io
import ipaddress
import logging
import socket
from typing import Any, Dict, List, Optional, Set, Tuple
import urllib.parse
import uuid

import fitz  # PyMuPDF
from fastapi import HTTPException, status
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.document import Document
from app.models.tender import Tender
from app.models.user import User
from app.schemas.tender import FetchTenderDocumentsResponse, TenderDocumentResponse
from app.services.storage_service import LocalStorageService, get_storage_service
from app.services.tender_service import TenderService

logger = logging.getLogger(__name__)

# Default allowed domain suffixes for official procurement sources
DEFAULT_ALLOWED_DOMAINS = [
    ".gov.in",
    ".nic.in",
    "gov.in",
    "nic.in",
    "tenderkart.in",
    ".tenderkart.in",
    "apify.com",
    ".apify.com",
]


@dataclass
class DocumentRetrievalResult:
    """Internal result envelope for a single URL download/classification attempt."""
    url: str
    classification: str  # "PDF_DOCUMENT", "HTML_PORTAL_PAGE", "RESTRICTED_ACCESS", "UNAVAILABLE", "MALFORMED_PDF", "OVERSIZED_DOWNLOAD", "BLOCKED_SSRF", "NON_PDF_RESOURCE"
    status: str          # "DOWNLOADED", "HTML_PAGE", "RESTRICTED", "NOT_FOUND", "ERROR"
    content: Optional[bytes] = None
    sha256_hash: Optional[str] = None
    file_size: int = 0
    total_pages: Optional[int] = None
    suggested_filename: Optional[str] = None
    message: Optional[str] = None
    error_details: Optional[str] = None


class TenderDocumentRetrievalService:
    """
    Orchestrates secure URL inspection, automatic PDF download, validation,
    deduplication, and document intelligence indexing for public tenders.
    """

    # In-memory lock set to prevent concurrent retrieval runs on the same tender
    _active_fetches: Set[uuid.UUID] = set()

    def __init__(
        self,
        session: AsyncSession,
        storage_service: Optional[LocalStorageService] = None,
        tender_service: Optional[TenderService] = None,
        custom_client: Optional[httpx.AsyncClient] = None,
    ):
        self.session = session
        self.settings = get_settings()
        self.storage = storage_service or get_storage_service()
        self.tender_service = tender_service or TenderService(session, storage_service=self.storage)
        self.custom_client = custom_client

    @classmethod
    def is_fetch_active(cls, tender_id: uuid.UUID) -> bool:
        """Check whether a background retrieval run is currently active for this tender."""
        return tender_id in cls._active_fetches

    def is_safe_url(self, url: str, allow_test_hosts: bool = False) -> Tuple[bool, str]:
        """
        SSRF and URL safety validation:
        - Must be http or https scheme.
        - Hostname must not resolve to private, loopback, multicast, or link-local IPs.
        - Hostname must match allowed government or authorized third-party provider domains.
        """
        if not url or not isinstance(url, str):
            return False, "URL is empty or invalid"

        try:
            parsed = urllib.parse.urlparse(url.strip())
        except Exception as e:
            return False, f"Invalid URL structure: {e}"

        if parsed.scheme.lower() not in ("http", "https"):
            return False, f"Scheme '{parsed.scheme}' is not permitted (must be http or https)"

        hostname = (parsed.hostname or "").lower().strip()
        if not hostname:
            return False, "URL is missing a valid hostname"

        # Explicitly forbidden hostnames
        forbidden_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata.google.internal"}
        if hostname in forbidden_hosts and not allow_test_hosts:
            return False, f"Host '{hostname}' is forbidden by SSRF security policy"

        # Allow testserver / mock domains during automated test execution
        if allow_test_hosts and hostname in ("testserver", "localhost", "127.0.0.1", "test.local"):
            return True, "Allowed test environment host"

        # Check domain suffix against allowed domains
        allowed_domains = getattr(self.settings, "ALLOWED_DOCUMENT_DOMAINS", DEFAULT_ALLOWED_DOMAINS)
        domain_matches = any(
            hostname == dom.lstrip(".") or hostname.endswith(f".{dom.lstrip('.')}")
            for dom in allowed_domains
        )

        if not domain_matches and not allow_test_hosts:
            return False, f"Domain '{hostname}' is not an authorized official tender portal domain"

        # Check if hostname itself is an IP address
        try:
            ip_obj = ipaddress.ip_address(hostname)
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast:
                return False, f"Direct access to private or reserved IP '{hostname}' is forbidden"
        except ValueError:
            # Not an IP literal; proceed to DNS resolution check
            pass

        # Validate resolved IP addresses to prevent DNS rebinding attacks
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            for _, _, _, _, sockaddr in addr_info:
                ip_str = sockaddr[0]
                try:
                    ip_obj = ipaddress.ip_address(ip_str)
                    if (
                        ip_obj.is_private
                        or ip_obj.is_loopback
                        or ip_obj.is_link_local
                        or ip_obj.is_multicast
                    ) and not allow_test_hosts:
                        return False, f"Host '{hostname}' resolves to restricted IP '{ip_str}'"
                except ValueError:
                    pass
        except Exception:
            # If DNS resolution fails here in non-test mode, httpx will fail cleanly later
            pass

        return True, "URL passed security checks"

    async def classify_and_download(
        self,
        url: str,
        timeout: float = 25.0,
        max_bytes: int = 50 * 1024 * 1024,
        allow_test_hosts: bool = False,
    ) -> DocumentRetrievalResult:
        """
        Probe and stream a document URL:
        1. SSRF check.
        2. Stream response inspecting status and Content-Type.
        3. Verify file signature (%PDF).
        4. Detect HTML portal pages and prevent treating them as corrupted PDFs.
        5. Enforce size limits and PyMuPDF integrity check.
        """
        is_safe, reason = self.is_safe_url(url, allow_test_hosts=allow_test_hosts)
        if not is_safe:
            return DocumentRetrievalResult(
                url=url,
                classification="BLOCKED_SSRF",
                status="ERROR",
                error_details=reason,
                message="Retrieval blocked by security policy (SSRF prevention).",
            )

        headers = {
            "User-Agent": "TenderBidComplianceBot/1.0 (+https://tenderbid.msme; MSME Procurement Assistant)",
            "Accept": "application/pdf, text/html, application/xhtml+xml, */*",
        }

        client_to_use = self.custom_client

        try:
            if client_to_use:
                return await self._execute_download_stream(
                    client_to_use, url, headers, max_bytes
                )
            else:
                async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                    return await self._execute_download_stream(
                        client, url, headers, max_bytes
                    )
        except httpx.TimeoutException:
            return DocumentRetrievalResult(
                url=url,
                classification="UNAVAILABLE",
                status="NOT_FOUND",
                error_details="Connection to remote tender portal timed out.",
                message="Tender source server did not respond within the allocated timeout.",
            )
        except httpx.RequestError as exc:
            return DocumentRetrievalResult(
                url=url,
                classification="UNAVAILABLE",
                status="NOT_FOUND",
                error_details=f"Network error communicating with portal: {exc}",
                message="Failed to establish a network connection to the document source.",
            )
        except Exception as exc:
            logger.error("Unexpected error retrieving document from %s: %s", url, exc, exc_info=True)
            return DocumentRetrievalResult(
                url=url,
                classification="UNAVAILABLE",
                status="ERROR",
                error_details=str(exc),
                message="An unexpected error occurred during document retrieval.",
            )

    async def _execute_download_stream(
        self,
        client: httpx.AsyncClient,
        url: str,
        headers: Dict[str, str],
        max_bytes: int,
    ) -> DocumentRetrievalResult:
        """Helper to stream response bytes and evaluate PDF vs HTML signature."""
        async with client.stream("GET", url, headers=headers) as response:
            status_code = response.status_code

            # Access controls & HTTP errors
            if status_code in (401, 403):
                return DocumentRetrievalResult(
                    url=url,
                    classification="RESTRICTED_ACCESS",
                    status="RESTRICTED",
                    error_details=f"Access denied by remote portal (HTTP {status_code}). WAF or login required.",
                    message="Official portal restricts direct public downloads. Please use the official tender page link.",
                )
            if status_code == 404:
                return DocumentRetrievalResult(
                    url=url,
                    classification="UNAVAILABLE",
                    status="NOT_FOUND",
                    error_details="Remote document not found (HTTP 404).",
                    message="Document notice could not be found at the published URL.",
                )
            if status_code == 429:
                return DocumentRetrievalResult(
                    url=url,
                    classification="RESTRICTED_ACCESS",
                    status="RESTRICTED",
                    error_details="Remote portal rate limit exceeded (HTTP 429).",
                    message="Official portal rate limit encountered. Please retry later.",
                )
            if status_code >= 400:
                return DocumentRetrievalResult(
                    url=url,
                    classification="UNAVAILABLE",
                    status="ERROR",
                    error_details=f"Remote server returned error HTTP {status_code}.",
                    message=f"Official server returned HTTP status {status_code}.",
                )

            content_type = response.headers.get("content-type", "").lower()

            # Read initial chunk to inspect magic bytes
            initial_chunk = b""
            async for chunk in response.aiter_bytes():
                initial_chunk += chunk
                if len(initial_chunk) >= 2048:
                    break

            if not initial_chunk:
                return DocumentRetrievalResult(
                    url=url,
                    classification="UNAVAILABLE",
                    status="NOT_FOUND",
                    error_details="Remote server returned empty 0-byte response.",
                    message="No data returned from tender document source.",
                )

            # Examine file signature: PDF magic bytes (%PDF)
            if not initial_chunk.startswith(b"%PDF"):
                lower_preview = initial_chunk[:1024].lower()
                if (
                    b"<html" in lower_preview
                    or b"<!doctype html" in lower_preview
                    or "text/html" in content_type
                ):
                    return DocumentRetrievalResult(
                        url=url,
                        classification="HTML_PORTAL_PAGE",
                        status="HTML_PAGE",
                        message="URL points to an interactive official web portal page rather than a direct PDF file.",
                        error_details="Source is an HTML bid notice page. Direct PDF download is not available at this link.",
                    )
                else:
                    return DocumentRetrievalResult(
                        url=url,
                        classification="NON_PDF_RESOURCE",
                        status="ERROR",
                        error_details=f"Remote file signature is not PDF (Content-Type: {content_type}).",
                        message="Remote resource is not a valid PDF document.",
                    )

            # Stream remaining bytes up to max_bytes
            buffer = io.BytesIO()
            buffer.write(initial_chunk)
            total_size = len(initial_chunk)

            async for chunk in response.aiter_bytes():
                total_size += len(chunk)
                if total_size > max_bytes:
                    return DocumentRetrievalResult(
                        url=url,
                        classification="OVERSIZED_DOWNLOAD",
                        status="ERROR",
                        error_details=f"Document exceeds maximum allowed size of {max_bytes // (1024 * 1024)} MB.",
                        message="Tender document is too large to download automatically.",
                    )
                buffer.write(chunk)

            pdf_bytes = buffer.getvalue()

            # Structural PDF validation using PyMuPDF
            try:
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                total_pages = doc.page_count
                doc.close()
                if total_pages <= 0:
                    return DocumentRetrievalResult(
                        url=url,
                        classification="MALFORMED_PDF",
                        status="ERROR",
                        error_details="PDF file opened but contains 0 pages.",
                        message="Corrupted or empty PDF file received from portal.",
                    )
            except Exception as exc:
                return DocumentRetrievalResult(
                    url=url,
                    classification="MALFORMED_PDF",
                    status="ERROR",
                    error_details=f"PDF integrity validation failed: {exc}",
                    message="File contains %PDF header but cannot be parsed by the PDF engine.",
                )

            # Deduplication hash
            sha256 = hashlib.sha256(pdf_bytes).hexdigest()

            # Derive suggested filename
            parsed_path = urllib.parse.urlparse(url).path
            suggested_name = parsed_path.split("/")[-1].split("?")[0]
            if not suggested_name or not suggested_name.lower().endswith(".pdf"):
                suggested_name = f"tender_document_{sha256[:8]}.pdf"

            return DocumentRetrievalResult(
                url=url,
                classification="PDF_DOCUMENT",
                status="DOWNLOADED",
                content=pdf_bytes,
                sha256_hash=sha256,
                file_size=len(pdf_bytes),
                total_pages=total_pages,
                suggested_filename=suggested_name,
                message="PDF successfully retrieved and verified.",
            )

    async def fetch_tender_documents(
        self,
        tender_id: uuid.UUID,
        user: Optional[User] = None,
        allow_test_hosts: bool = False,
    ) -> FetchTenderDocumentsResponse:
        """
        Orchestrate document retrieval for a selected tender:
        - Prevents duplicate concurrent fetches.
        - Identifies candidate URLs from tender metadata and official links.
        - Downloads and validates accessible PDFs.
        - Deduplicates against existing tender documents.
        - Triggers physical page extraction, OCR, and ChromaDB indexing.
        - Returns a structured outcome envelope for the React frontend.
        """
        if tender_id in self._active_fetches:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A document retrieval operation is already in progress for this tender.",
            )

        self._active_fetches.add(tender_id)

        try:
            # Load tender with existing documents
            stmt = select(Tender).where(Tender.id == tender_id).options(selectinload(Tender.documents))
            result = await self.session.execute(stmt)
            tender = result.scalar_one_or_none()

            if not tender:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tender with ID '{tender_id}' not found.",
                )

            candidate_urls = self._extract_candidate_urls(tender)

            if not candidate_urls:
                return FetchTenderDocumentsResponse(
                    tender_id=tender.id,
                    status="NO_DOCUMENTS_FOUND",
                    url_classification="NONE",
                    source_url=tender.official_portal_url,
                    documents_retrieved=0,
                    documents_indexed=len(tender.documents),
                    documents=[TenderDocumentResponse.model_validate(d) for d in tender.documents],
                    official_portal_url=tender.official_portal_url,
                    message="No document attachments or direct download URLs are published for this tender notice.",
                )

            downloaded_docs: List[Document] = []
            primary_classification = "NONE"
            primary_url = candidate_urls[0] if candidate_urls else None
            any_pdf_success = False
            overall_message = ""

            for url in candidate_urls:
                retrieval = await self.classify_and_download(
                    url=url,
                    allow_test_hosts=allow_test_hosts,
                )
                primary_classification = retrieval.classification

                if retrieval.classification == "PDF_DOCUMENT" and retrieval.content:
                    # Check deduplication by SHA-256
                    existing_doc = next(
                        (d for d in tender.documents if d.sha256_hash == retrieval.sha256_hash),
                        None,
                    )

                    if existing_doc:
                        logger.info(
                            "Document with hash %s already exists for tender %s. Skipping duplicate creation.",
                            retrieval.sha256_hash,
                            tender.id,
                        )
                        downloaded_docs.append(existing_doc)
                        any_pdf_success = True
                        overall_message = f"Document '{existing_doc.original_filename}' is already verified and indexed."
                        continue

                    # Save verified PDF stream to vault storage
                    doc_id = uuid.uuid4()
                    rel_storage_path = f"tenders/{tender.id}/{doc_id}.pdf"
                    saved_path, file_size, sha256_hash = await self.storage.save_pdf_stream(
                        file_obj=io.BytesIO(retrieval.content),
                        target_relative_path=rel_storage_path,
                    )

                    new_doc = Document(
                        id=doc_id,
                        tender_id=tender.id,
                        company_id=None,
                        entity_type="TENDER",
                        uploaded_by=user.id if user else None,
                        document_category="TENDER_NOTICE",
                        original_filename=retrieval.suggested_filename or "tender_notice.pdf",
                        storage_path=saved_path,
                        mime_type="application/pdf",
                        file_size_bytes=file_size,
                        sha256_hash=sha256_hash,
                        processing_status="PENDING",
                        verification_status="UNVERIFIED",
                    )
                    self.session.add(new_doc)
                    await self.session.commit()
                    await self.session.refresh(new_doc)

                    # Trigger extraction, chunking, and ChromaDB vector indexing
                    await self.tender_service.process_tender_documents(
                        tender_id=tender.id,
                        document_id=new_doc.id,
                    )
                    await self.session.refresh(new_doc)
                    downloaded_docs.append(new_doc)
                    any_pdf_success = True
                    overall_message = f"Successfully downloaded, verified, and indexed '{new_doc.original_filename}'."

                elif retrieval.classification == "HTML_PORTAL_PAGE":
                    # Store notice in tender ingestion metadata
                    metadata = dict(tender.ingestion_metadata or {})
                    metadata["document_source_status"] = "HTML_PORTAL_PAGE"
                    metadata["document_source_notice"] = (
                        "Tender notice is published as an interactive official web portal page. "
                        "Direct PDF download is not available on this endpoint. "
                        "Use the official portal link to view bid documents."
                    )
                    metadata["document_source_url"] = url
                    tender.ingestion_metadata = metadata
                    await self.session.commit()
                    overall_message = "The tender source is an official web portal page. Direct PDF is not published at this link."

                elif retrieval.classification == "RESTRICTED_ACCESS":
                    metadata = dict(tender.ingestion_metadata or {})
                    metadata["document_source_status"] = "RESTRICTED"
                    metadata["document_source_notice"] = retrieval.error_details
                    tender.ingestion_metadata = metadata
                    await self.session.commit()
                    overall_message = "Access to tender documents is restricted by portal access controls or authentication."

                elif retrieval.classification in ("UNAVAILABLE", "MALFORMED_PDF", "OVERSIZED_DOWNLOAD"):
                    overall_message = retrieval.message or retrieval.error_details or "Document could not be retrieved."

            # Re-fetch updated documents list
            docs_stmt = select(Document).where(Document.tender_id == tender.id).order_by(Document.created_at)
            docs_res = await self.session.execute(docs_stmt)
            all_tender_docs = list(docs_res.scalars().all())

            outcome_status = "COMPLETED" if any_pdf_success else (
                "HTML_PAGE_ONLY" if primary_classification == "HTML_PORTAL_PAGE" else (
                    "RESTRICTED" if primary_classification == "RESTRICTED_ACCESS" else "FAILED"
                )
            )

            return FetchTenderDocumentsResponse(
                tender_id=tender.id,
                status=outcome_status,
                url_classification=primary_classification,
                source_url=primary_url,
                documents_retrieved=len(downloaded_docs),
                documents_indexed=sum(1 for d in all_tender_docs if d.processing_status == "INDEXED"),
                documents=[TenderDocumentResponse.model_validate(d) for d in all_tender_docs],
                official_portal_url=tender.official_portal_url,
                message=overall_message or "Document retrieval completed.",
                error_details=None if any_pdf_success else (
                    "Source returned an interactive HTML page." if primary_classification == "HTML_PORTAL_PAGE" else None
                ),
            )

        finally:
            self._active_fetches.discard(tender_id)

    def _extract_candidate_urls(self, tender: Tender) -> List[str]:
        """Collect potential document URLs from tender fields and ingestion payload."""
        urls: List[str] = []
        raw_payload = {}
        if tender.ingestion_metadata and isinstance(tender.ingestion_metadata, dict):
            raw_payload = tender.ingestion_metadata.get("raw_payload", {}) or {}

        # 1. Dedicated document URLs in raw payload
        for key in ("pdfUrl", "documentUrl", "bidDocumentUrl"):
            val = raw_payload.get(key)
            if val and isinstance(val, str) and val.startswith("http"):
                urls.append(val.strip())

        # 2. List of document URLs
        for key in ("documentUrls", "document_urls", "attachments", "files"):
            val = raw_payload.get(key)
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, str) and item.startswith("http"):
                        urls.append(item.strip())
                    elif isinstance(item, dict) and item.get("url") and str(item["url"]).startswith("http"):
                        urls.append(str(item["url"]).strip())

        # 3. tenderUrl in raw payload
        tender_url = raw_payload.get("tenderUrl")
        if tender_url and isinstance(tender_url, str) and tender_url.startswith("http"):
            urls.append(tender_url.strip())

        # 4. Official portal URL on tender model
        if tender.official_portal_url and tender.official_portal_url.startswith("http"):
            urls.append(tender.official_portal_url.strip())

        # Deduplicate while preserving order
        seen = set()
        unique_urls = []
        for u in urls:
            if u not in seen:
                seen.add(u)
                unique_urls.append(u)

        return unique_urls
