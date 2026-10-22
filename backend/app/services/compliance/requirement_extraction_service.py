import json
import logging
import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.models.document import Document
from app.models.document_chunk import DocumentChunkModel
from app.models.tender import Tender
from app.schemas.requirements import (
    CertificationRequirement,
    DeadlineRequirement,
    ExperienceRequirement,
    MandatoryDocumentRequirement,
    NormalizedTenderRequirements,
    TurnoverRequirement,
)
from app.schemas.tender import ProposedCriterionItem, ProposedRequirementsBundle
from app.services.ai.gemini_client import GeminiClient, get_gemini_client
from app.services.compliance.requirement_normalizer import RequirementNormalizer

logger = logging.getLogger(__name__)


class RequirementExtractionError(Exception):
    """Base exception for requirement extraction errors."""
    pass


class RequirementExtractionService:
    """
    Extracts candidate tender criteria from physical document page text and OCR output.
    Enforces deterministic validation, provenance tracking, conflict detection,
    and administrator review before requirements become authoritative.
    """

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.gemini_client = gemini_client or get_gemini_client()

    def extract_from_chunks(
        self,
        tender: Tender,
        chunks: List[DocumentChunkModel],
    ) -> ProposedRequirementsBundle:
        """
        Analyze tender document chunks and propose structured requirements.
        Preserves document IDs, filenames, page numbers, and exact excerpts.
        """
        if not chunks:
            return ProposedRequirementsBundle(
                tender_id=tender.id,
                extraction_status="NEEDS_REVIEW",
                criteria=[],
                conflicts=["No document chunks available for requirement extraction."],
                unsupported_clauses=[],
                normalized_preview=None,
                extracted_at=datetime.now(timezone.utc),
            )

        criteria: List[ProposedCriterionItem] = []
        conflicts: List[str] = []
        unsupported: List[str] = []

        # 1. Attempt LLM-assisted extraction if Gemini is configured
        llm_criteria = None
        if self.gemini_client.is_configured():
            try:
                llm_criteria = self._extract_with_llm(tender, chunks)
            except Exception as e:
                logger.warning(f"LLM extraction failed, falling back to deterministic extraction: {e}")

        # 2. Extract using deterministic heuristics (or augment LLM output)
        if llm_criteria:
            criteria.extend(llm_criteria)
        else:
            det_criteria, det_unsupported, det_conflicts = self._extract_deterministic(chunks)
            criteria.extend(det_criteria)
            unsupported.extend(det_unsupported)
            conflicts.extend(det_conflicts)

        # 3. Conflict Detection & Provenance Validation
        validated_criteria, detected_conflicts = self._validate_and_detect_conflicts(criteria)
        conflicts.extend(detected_conflicts)

        # 4. Determine overall extraction status
        if any(c.status == "NEEDS_REVIEW" for c in validated_criteria) or conflicts:
            overall_status = "NEEDS_REVIEW"
        elif len(validated_criteria) > 0:
            overall_status = "COMPLETED"
        else:
            overall_status = "PARTIAL"

        # 5. Build normalized preview dictionary (for admin review)
        normalized_preview = self._build_normalized_preview(validated_criteria, tender.submission_deadline)

        return ProposedRequirementsBundle(
            tender_id=tender.id,
            extraction_status=overall_status,
            criteria=validated_criteria,
            conflicts=conflicts,
            unsupported_clauses=unsupported,
            normalized_preview=normalized_preview,
            extracted_at=datetime.now(timezone.utc),
        )

    def _extract_deterministic(
        self,
        chunks: List[DocumentChunkModel],
    ) -> Tuple[List[ProposedCriterionItem], List[str], List[str]]:
        """
        Pure deterministic pattern and regex extractor for objective criteria.
        Scans chunk text for financial turnover, experience, certifications, and deadlines.
        """
        criteria: List[ProposedCriterionItem] = []
        unsupported: List[str] = []
        conflicts: List[str] = []

        turnover_candidates: List[Tuple[Decimal, str, int, str, Optional[uuid.UUID]]] = []
        exp_candidates: List[Tuple[int, str, int, str, Optional[uuid.UUID]]] = []
        seen_certs = set()
        seen_docs = set()

        for chunk in chunks:
            text = chunk.chunk_text
            page = chunk.page_number
            fname = chunk.source_filename
            doc_id = str(chunk.document_id) if chunk.document_id else None

            # --- Turnover pattern ---
            # e.g., "annual turnover of Rs. 5 Crore", "average annual turnover of at least Rs. 5 Crore"
            turnover_matches = re.finditer(
                r'(?:average\s+annual\s+turnover|annual\s+turnover|average\s+turnover|turnover)'
                r'[\s\w,]{0,40}?'
                r'(?:Rs\.?|INR)?\s*([\d,]+(?:\.\d+)?)\s*(crore|cr|lakh|lakhs)?',
                text,
                re.IGNORECASE,
            )
            for m in turnover_matches:
                raw_num_str = m.group(1).replace(',', '')
                unit = (m.group(2) or '').lower()
                try:
                    num = Decimal(raw_num_str)
                    if 'crore' in unit or 'cr' in unit:
                        num = num * Decimal('10000000')
                    elif 'lakh' in unit:
                        num = num * Decimal('100000')
                    excerpt = self._extract_surrounding_excerpt(text, m.start(), m.end())
                    turnover_candidates.append((num, excerpt, page, fname, doc_id))
                except Exception:
                    pass

            # --- Experience pattern ---
            # e.g., "5 years of experience", "minimum 3 years in domain"
            exp_matches = re.finditer(
                r'(?:minimum|at\s+least)?\s*(\d+)\s*(?:years|yrs)\s+(?:of\s+)?(?:relevant\s+)?(?:experience|track\s+record)',
                text,
                re.IGNORECASE,
            )
            for m in exp_matches:
                try:
                    years = int(m.group(1))
                    excerpt = self._extract_surrounding_excerpt(text, m.start(), m.end())
                    exp_candidates.append((years, excerpt, page, fname, doc_id))
                except Exception:
                    pass

            # --- Certifications ---
            cert_patterns = [
                (r'\b(ISO\s*9001(?::2015)?)\b', "ISO 9001:2015 Quality Management"),
                (r'\b(ISO\s*27001(?::2013|:2022)?)\b', "ISO 27001 Information Security"),
                (r'\b(ISO\s*14001(?::2015)?)\b', "ISO 14001 Environmental Management"),
                (r'\b(CMMI\s*(?:Level\s*)?[345])\b', "CMMI Capability Maturity"),
                (r'\b(BIS\s*(?:Certification|Standard)?)\b', "Bureau of Indian Standards (BIS)"),
            ]
            for pat, std_name in cert_patterns:
                m = re.search(pat, text, re.IGNORECASE)
                if m and std_name not in seen_certs:
                    seen_certs.add(std_name)
                    excerpt = self._extract_surrounding_excerpt(text, m.start(), m.end())
                    criteria.append(
                        ProposedCriterionItem(
                            criterion_type="CERTIFICATION",
                            title=f"Mandatory Certification: {std_name}",
                            extracted_value={"name": std_name, "is_mandatory": True},
                            source_filename=fname,
                            page_number=page,
                            document_id=doc_id,
                            supporting_excerpt=excerpt,
                            status="PROPOSED",
                            confidence=0.95,
                        )
                    )

            # --- Mandatory Documents ---
            doc_patterns = [
                (r'\b(GST\s*(?:Registration\s*Certificate)?)\b', "GST Registration Certificate", "TAX_REGISTRATION"),
                (r'\b(PAN\s*(?:Card)?)\b', "Permanent Account Number (PAN)", "TAX_REGISTRATION"),
                (r'\b(Audited\s+Balance\s+Sheets?)\b', "Audited Balance Sheets (3 Years)", "FINANCIAL_STATEMENT"),
                (r'\b(MSME\s*Certificate|Udyam\s*Registration)\b', "Udyam Registration Certificate", "MSME_CERTIFICATE"),
                (r'\b(Power\s+of\s+Attorney)\b', "Power of Attorney", "LEGAL"),
            ]
            for pat, doc_name, cat in doc_patterns:
                m = re.search(pat, text, re.IGNORECASE)
                if m and doc_name not in seen_docs:
                    seen_docs.add(doc_name)
                    excerpt = self._extract_surrounding_excerpt(text, m.start(), m.end())
                    criteria.append(
                        ProposedCriterionItem(
                            criterion_type="MANDATORY_DOCUMENT",
                            title=f"Mandatory Document: {doc_name}",
                            extracted_value={
                                "document_name": doc_name,
                                "document_category": cat,
                                "is_mandatory": True,
                            },
                            source_filename=fname,
                            page_number=page,
                            document_id=doc_id,
                            supporting_excerpt=excerpt,
                            status="PROPOSED",
                            confidence=0.90,
                        )
                    )

            # --- EMD & MSME Exemption ---
            emd_match = re.search(
                r'(?:EMD|Earnest\s+Money\s+Deposit)[\s\w]{0,25}?(?:Rs\.?|INR)?\s*([\d,]+(?:\.\d+)?)',
                text,
                re.IGNORECASE,
            )
            if emdd := emd_match:
                raw_emd = emdd.group(1).replace(',', '')
                try:
                    emd_val = Decimal(raw_emd)
                    msme_exempt = bool(re.search(r'MSME.*(?:exempt|exemption)', text, re.IGNORECASE))
                    excerpt = self._extract_surrounding_excerpt(text, emdd.start(), emdd.end())
                    criteria.append(
                        ProposedCriterionItem(
                            criterion_type="EMD",
                            title=f"EMD Requirement (INR {emd_val:,.2f})",
                            extracted_value={
                                "emd_amount_inr": float(emd_val),
                                "msme_emd_exemption": msme_exempt,
                            },
                            source_filename=fname,
                            page_number=page,
                            document_id=doc_id,
                            supporting_excerpt=excerpt,
                            status="PROPOSED",
                            confidence=0.92,
                        )
                    )
                except Exception:
                    pass

        # Evaluate Turnover Candidates
        if turnover_candidates:
            # Check for conflict
            distinct_amounts = {tc[0] for tc in turnover_candidates}
            if len(distinct_amounts) > 1:
                # Ambiguous/conflicting turnover threshold found
                primary = turnover_candidates[0]
                conflicts_str = ", ".join(f"INR {amt:,.2f}" for amt in sorted(distinct_amounts))
                conflicts.append(f"Conflicting turnover thresholds detected across pages: {conflicts_str}.")
                criteria.append(
                    ProposedCriterionItem(
                        criterion_type="TURNOVER",
                        title="Minimum Annual Turnover Requirement (Conflicting)",
                        extracted_value={
                            "required_turnover_inr": float(primary[0]),
                            "comparison_method": "ANNUAL_MINIMUM",
                            "financial_years_count": 3,
                            "is_mandatory": True,
                        },
                        source_filename=primary[3],
                        page_number=primary[2],
                        document_id=primary[4],
                        supporting_excerpt=primary[1],
                        status="NEEDS_REVIEW",
                        confidence=0.50,
                        review_notes=f"Conflicting turnover thresholds detected across pages: {conflicts_str}. Administrator confirmation required.",
                    )
                )
            else:
                primary = turnover_candidates[0]
                criteria.append(
                    ProposedCriterionItem(
                        criterion_type="TURNOVER",
                        title=f"Minimum Annual Turnover Requirement (INR {primary[0]:,.2f})",
                        extracted_value={
                            "required_turnover_inr": float(primary[0]),
                            "comparison_method": "ANNUAL_MINIMUM",
                            "financial_years_count": 3,
                            "is_mandatory": True,
                        },
                        source_filename=primary[3],
                        page_number=primary[2],
                        document_id=primary[4],
                        supporting_excerpt=primary[1],
                        status="PROPOSED",
                        confidence=0.95,
                    )
                )

        # Evaluate Experience Candidates
        if exp_candidates:
            distinct_years = {ec[0] for ec in exp_candidates}
            primary = exp_candidates[0]
            if len(distinct_years) > 1:
                criteria.append(
                    ProposedCriterionItem(
                        criterion_type="EXPERIENCE",
                        title="Work Experience Requirement (Conflicting)",
                        extracted_value={
                            "min_experience_years": primary[0],
                            "min_completed_projects": 1,
                            "is_mandatory": True,
                        },
                        source_filename=primary[3],
                        page_number=primary[2],
                        document_id=primary[4],
                        supporting_excerpt=primary[1],
                        status="NEEDS_REVIEW",
                        confidence=0.60,
                        review_notes=f"Multiple experience criteria found: {sorted(distinct_years)} years. Admin review needed.",
                    )
                )
            else:
                criteria.append(
                    ProposedCriterionItem(
                        criterion_type="EXPERIENCE",
                        title=f"Work Experience Requirement ({primary[0]} Years)",
                        extracted_value={
                            "min_experience_years": primary[0],
                            "min_completed_projects": 1,
                            "is_mandatory": True,
                        },
                        source_filename=primary[3],
                        page_number=primary[2],
                        document_id=primary[4],
                        supporting_excerpt=primary[1],
                        status="PROPOSED",
                        confidence=0.95,
                    )
                )

        return criteria, unsupported, conflicts

    def _extract_with_llm(
        self,
        tender: Tender,
        chunks: List[DocumentChunkModel],
    ) -> List[ProposedCriterionItem]:
        """
        Use Gemini with strict schema instructions and page provenance enforcement.
        """
        context_chunks = []
        for c in chunks[:12]:  # Send first 12 representative chunks (e.g. eligibility and RFP intro)
            context_chunks.append(
                f"[Doc: {c.source_filename} | Page {c.page_number} | DocID: {c.document_id}]\n{c.chunk_text}"
            )
        corpus = "\n\n---\n\n".join(context_chunks)

        prompt = (
            f"Tender Reference: {tender.tender_reference}\n"
            f"Title: {tender.title}\n\n"
            "Analyze the following tender document excerpts and extract structured eligibility requirements.\n"
            "Return a strict JSON object with a 'criteria' array where each item has:\n"
            "- 'criterion_type': 'TURNOVER', 'EXPERIENCE', 'CERTIFICATION', 'MANDATORY_DOCUMENT', or 'EMD'\n"
            "- 'title': short descriptive title\n"
            "- 'extracted_value': dictionary matching the requirement schema\n"
            "- 'source_filename': exact source filename from the excerpt header\n"
            "- 'page_number': integer physical page number from the excerpt header\n"
            "- 'document_id': document ID from the excerpt header\n"
            "- 'supporting_excerpt': verbatim quotation from text\n"
            "- 'status': 'PROPOSED' if clear, 'NEEDS_REVIEW' if ambiguous or disputed\n"
            "- 'review_notes': explanation if status is NEEDS_REVIEW\n\n"
            "Do not invent values. If not explicitly found in text, do not include it.\n\n"
            f"Document Excerpts:\n{corpus}"
        )

        response_text = self.gemini_client.generate_text(
            prompt=prompt,
            system_instruction="You are a strict legal and procurement compliance parser. Extract only verified clauses in JSON.",
        )

        # Parse JSON
        clean_json = response_text.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:]
        if clean_json.endswith("```"):
            clean_json = clean_json[:-3]
        clean_json = clean_json.strip()

        parsed = json.loads(clean_json)
        raw_items = parsed.get("criteria", [])
        criteria: List[ProposedCriterionItem] = []
        for item in raw_items:
            try:
                criteria.append(ProposedCriterionItem.model_validate(item))
            except Exception as e:
                logger.warning(f"Failed to validate LLM proposed criterion item: {e}")

        return criteria

    def _validate_and_detect_conflicts(
        self,
        criteria: List[ProposedCriterionItem],
    ) -> Tuple[List[ProposedCriterionItem], List[str]]:
        """
        Validates typed schemas and flags ambiguous, conflicting or invalid items.
        """
        validated: List[ProposedCriterionItem] = []
        conflicts: List[str] = []

        turnover_items = [c for c in criteria if c.criterion_type == "TURNOVER"]
        if len(turnover_items) > 1:
            vals = [t.extracted_value.get("required_turnover_inr") for t in turnover_items]
            if len(set(vals)) > 1:
                conflicts.append(f"Conflicting turnover thresholds proposed: {vals}")
                for t in turnover_items:
                    t.status = "NEEDS_REVIEW"
                    t.review_notes = "Conflict with other proposed turnover values."

        for item in criteria:
            # Validate typed schema
            try:
                if item.criterion_type == "TURNOVER":
                    TurnoverRequirement.model_validate(item.extracted_value)
                elif item.criterion_type == "EXPERIENCE":
                    ExperienceRequirement.model_validate(item.extracted_value)
                elif item.criterion_type == "CERTIFICATION":
                    CertificationRequirement.model_validate(item.extracted_value)
                elif item.criterion_type == "MANDATORY_DOCUMENT":
                    MandatoryDocumentRequirement.model_validate(item.extracted_value)
            except Exception as err:
                item.status = "NEEDS_REVIEW"
                item.review_notes = f"Schema validation warning: {err}"
                conflicts.append(f"Criterion '{item.title}' failed schema validation: {err}")

            # Verify page provenance and supporting excerpt
            if not item.supporting_excerpt or len(item.supporting_excerpt.strip()) < 5:
                item.status = "NEEDS_REVIEW"
                item.review_notes = "Missing or insufficient supporting text excerpt for provenance."
                conflicts.append(f"Criterion '{item.title}' has no verbatim supporting excerpt.")

            validated.append(item)

        return validated, conflicts

    def _build_normalized_preview(
        self,
        criteria: List[ProposedCriterionItem],
        tender_deadline: Optional[datetime],
    ) -> Dict[str, Any]:
        """
        Construct a preview JSON dictionary compatible with NormalizedTenderRequirements.
        """
        raw_dict: Dict[str, Any] = {
            "certifications": [],
            "mandatory_documents": [],
            "unsupported_clauses": [],
        }

        for c in criteria:
            if c.criterion_type == "TURNOVER":
                raw_dict["turnover"] = c.extracted_value
            elif c.criterion_type == "EXPERIENCE":
                raw_dict["experience"] = c.extracted_value
            elif c.criterion_type == "CERTIFICATION":
                raw_dict["certifications"].append(c.extracted_value)
            elif c.criterion_type == "MANDATORY_DOCUMENT":
                raw_dict["mandatory_documents"].append(c.extracted_value)

        try:
            normalized = RequirementNormalizer.normalize(raw_dict, tender_deadline=tender_deadline)
            return normalized.model_dump(mode="json")
        except Exception as e:
            logger.warning(f"Could not build normalized preview: {e}")
            return raw_dict

    @staticmethod
    def _extract_surrounding_excerpt(text: str, start: int, end: int, window: int = 150) -> str:
        """Extract a readable sentence window around a regex match."""
        s = max(0, start - window)
        e = min(len(text), end + window)
        prefix = "..." if s > 0 else ""
        suffix = "..." if e < len(text) else ""
        return f"{prefix}{text[s:e].strip()}{suffix}"
