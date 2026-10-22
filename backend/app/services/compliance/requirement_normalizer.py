import logging
from decimal import Decimal
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.schemas.requirements import (
    CertificationRequirement,
    CommercialRequirement,
    DeadlineRequirement,
    ExperienceRequirement,
    LegalRequirement,
    MandatoryDocumentRequirement,
    NormalizedTenderRequirements,
    SubmissionRequirement,
    TechnicalRequirement,
    TurnoverRequirement,
)

logger = logging.getLogger(__name__)


class RequirementNormalizer:
    """Normalizes and validates raw tender structured requirements into typed Pydantic models."""

    @staticmethod
    def normalize(
        raw_dict: Optional[Dict[str, Any]],
        tender_deadline: Optional[datetime] = None,
        tender_emd_inr: Optional[Decimal] = None,
        msme_emd_exemption: bool = True,
    ) -> NormalizedTenderRequirements:
        """Parse raw JSONB dictionary (flat or nested) into strict NormalizedTenderRequirements."""
        if not raw_dict:
            raw_dict = {}

        # 1. Turnover requirement
        turnover_req: Optional[TurnoverRequirement] = None
        t_nested = raw_dict.get("turnover") if isinstance(raw_dict.get("turnover"), dict) else {}
        min_turnover = (
            raw_dict.get("min_annual_turnover_inr")
            or raw_dict.get("min_turnover_inr")
            or t_nested.get("required_turnover_inr")
            or t_nested.get("min_annual_turnover_inr")
        )
        if min_turnover is not None:
            try:
                comp_method = str(
                    t_nested.get("comparison_method")
                    or raw_dict.get("turnover_comparison_method", "ANNUAL_MINIMUM")
                ).upper()
                years_count = int(
                    t_nested.get("financial_years_count")
                    or raw_dict.get("turnover_years_count", 3)
                )
                is_mand = bool(
                    t_nested.get("is_mandatory", raw_dict.get("turnover_is_mandatory", True))
                )
                citation = t_nested.get("citation_reference") or raw_dict.get("turnover_citation")
                curr = t_nested.get("currency", "INR")

                turnover_req = TurnoverRequirement(
                    required_turnover_inr=Decimal(str(min_turnover)),
                    currency=curr,
                    comparison_method=comp_method,
                    financial_years_count=years_count,
                    is_mandatory=is_mand,
                    citation_reference=citation,
                )
            except Exception as e:
                logger.warning(f"Failed to normalize turnover requirement: {e}")

        # 2. Experience requirement
        exp_req: Optional[ExperienceRequirement] = None
        e_nested = raw_dict.get("experience") if isinstance(raw_dict.get("experience"), dict) else {}
        min_exp = (
            raw_dict.get("min_experience_years")
            or e_nested.get("min_experience_years")
            or e_nested.get("min_years")
        )
        if min_exp is not None:
            try:
                min_val = e_nested.get("min_single_contract_value_inr") or raw_dict.get("min_single_contract_value_inr")
                exp_req = ExperienceRequirement(
                    min_experience_years=int(min_exp),
                    min_completed_projects=int(e_nested.get("min_completed_projects") or raw_dict.get("min_completed_projects", 1)),
                    min_single_contract_value_inr=Decimal(str(min_val)) if min_val else None,
                    relevant_domain=e_nested.get("relevant_domain") or raw_dict.get("relevant_domain"),
                    is_mandatory=bool(e_nested.get("is_mandatory", raw_dict.get("experience_is_mandatory", True))),
                    citation_reference=e_nested.get("citation_reference") or raw_dict.get("experience_citation"),
                )
            except Exception as e:
                logger.warning(f"Failed to normalize experience requirement: {e}")

        # 3. Certifications
        certs = []
        raw_certs = (
            raw_dict.get("mandatory_certifications")
            or raw_dict.get("required_certifications")
            or raw_dict.get("certifications")
            or []
        )
        for c in raw_certs:
            if isinstance(c, str) and c.strip():
                certs.append(CertificationRequirement(name=c.strip(), is_mandatory=True))
            elif isinstance(c, dict) and "name" in c:
                certs.append(
                    CertificationRequirement(
                        name=c["name"],
                        issuing_authority=c.get("issuing_authority"),
                        is_mandatory=bool(c.get("is_mandatory", True)),
                        citation_reference=c.get("citation_reference"),
                    )
                )

        # 4. Mandatory documents
        docs = []
        raw_docs = (
            raw_dict.get("required_documents")
            or raw_dict.get("mandatory_documents")
            or []
        )
        for d in raw_docs:
            if isinstance(d, str) and d.strip():
                docs.append(MandatoryDocumentRequirement(document_name=d.strip(), is_mandatory=True))
            elif isinstance(d, dict) and "document_name" in d:
                docs.append(
                    MandatoryDocumentRequirement(
                        document_name=d["document_name"],
                        document_category=d.get("document_category") or d.get("document_type", "OTHER"),
                        is_mandatory=bool(d.get("is_mandatory", True)),
                        citation_reference=d.get("citation_reference"),
                    )
                )

        # 5. Deadline
        deadline_req: Optional[DeadlineRequirement] = None
        if tender_deadline:
            dl_utc = tender_deadline if tender_deadline.tzinfo else tender_deadline.replace(tzinfo=timezone.utc)
            deadline_req = DeadlineRequirement(submission_deadline_utc=dl_utc, is_mandatory=True)

        # 6. Technical Requirements
        tech_reqs: List[TechnicalRequirement] = []
        raw_tech = (
            raw_dict.get("technical_clauses")
            or raw_dict.get("technical_requirements")
            or raw_dict.get("technical_specifications")
            or []
        )
        for i, t in enumerate(raw_tech):
            if isinstance(t, str) and t.strip():
                tech_reqs.append(
                    TechnicalRequirement(
                        title=f"Technical Specification #{i+1}",
                        specification=t.strip(),
                        is_mandatory=True,
                    )
                )
            elif isinstance(t, dict) and ("specification" in t or "title" in t):
                tech_reqs.append(
                    TechnicalRequirement(
                        title=t.get("title", f"Technical Specification #{i+1}"),
                        specification=t.get("specification", t.get("description", "")),
                        standard_or_code=t.get("standard_or_code"),
                        is_mandatory=bool(t.get("is_mandatory", True)),
                        citation_reference=t.get("citation_reference"),
                    )
                )

        # 7. Commercial Requirements (EMD & Bid Security)
        comm_reqs: List[CommercialRequirement] = []
        raw_emd = raw_dict.get("emd_amount_inr") or tender_emd_inr
        if raw_emd is not None and Decimal(str(raw_emd)) > Decimal("0"):
            comm_reqs.append(
                CommercialRequirement(
                    title="Earnest Money Deposit (EMD) / Bid Security",
                    condition_type="EMD",
                    amount_inr=Decimal(str(raw_emd)),
                    msme_exemptible=msme_emd_exemption,
                    is_mandatory=True,
                    citation_reference=raw_dict.get("emd_citation"),
                )
            )

        # 8. Legal & Statutory Requirements
        legal_reqs: List[LegalRequirement] = []
        raw_legal = raw_dict.get("legal_requirements") or raw_dict.get("statutory_requirements") or []
        for i, l in enumerate(raw_legal):
            if isinstance(l, str) and l.strip():
                legal_reqs.append(
                    LegalRequirement(
                        title=l.strip(),
                        registration_type=l.strip().upper(),
                        is_mandatory=True,
                    )
                )
            elif isinstance(l, dict) and "title" in l:
                legal_reqs.append(
                    LegalRequirement(
                        title=l["title"],
                        registration_type=l.get("registration_type", "REGISTRATION"),
                        is_mandatory=bool(l.get("is_mandatory", True)),
                        citation_reference=l.get("citation_reference"),
                    )
                )

        # 9. Submission Requirements
        sub_reqs: List[SubmissionRequirement] = []
        raw_sub = raw_dict.get("submission_requirements") or raw_dict.get("submission_conditions") or []
        for i, s in enumerate(raw_sub):
            if isinstance(s, str) and s.strip():
                sub_reqs.append(
                    SubmissionRequirement(
                        title=s.strip(),
                        requirement_type="FORM",
                        is_mandatory=True,
                    )
                )
            elif isinstance(s, dict) and "title" in s:
                sub_reqs.append(
                    SubmissionRequirement(
                        title=s["title"],
                        requirement_type=s.get("requirement_type", "FORM"),
                        is_mandatory=bool(s.get("is_mandatory", True)),
                        citation_reference=s.get("citation_reference"),
                    )
                )

        unsupported = raw_dict.get("unsupported_clauses", [])

        return NormalizedTenderRequirements(
            turnover=turnover_req,
            experience=exp_req,
            certifications=certs,
            mandatory_documents=docs,
            deadline=deadline_req,
            technical_requirements=tech_reqs,
            commercial_requirements=comm_reqs,
            legal_requirements=legal_reqs,
            submission_requirements=sub_reqs,
            unsupported_clauses=unsupported,
        )
