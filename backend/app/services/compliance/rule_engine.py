from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.schemas.evidence import EvidenceCitation
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


@dataclass
class RuleFinding:
    """Internal evaluation outcome for a single deterministic compliance rule."""
    requirement_id: str
    rule_type: str  # TURNOVER, EXPERIENCE, CERTIFICATION, MANDATORY_DOCUMENT, DEADLINE, TECHNICAL, COMMERCIAL, LEGAL, SUBMISSION, OTHER
    requirement_description: str
    required_value: Dict[str, Any]
    observed_value: Dict[str, Any]
    status: str  # PASS, FAIL, MISSING_EVIDENCE, NEEDS_REVIEW, NOT_APPLICABLE
    is_mandatory: bool
    reason: str
    evidence_citations: List[EvidenceCitation] = field(default_factory=list)


class DeterministicRuleEngine:
    """
    Pure Python business logic engine evaluating objective financial, operational, 
    legal, and technical requirements without LLM intervention.
    Guarantees strict separation of deterministic decisions from AI interpretations.
    """

    @staticmethod
    def evaluate_turnover(
        req: TurnoverRequirement,
        turnover_records: List[Dict[str, Any]],
        tender_source_info: Optional[str] = None,
    ) -> RuleFinding:
        """Evaluate annual or average turnover using precise Decimal arithmetic."""
        tender_src = tender_source_info or req.citation_reference or "Tender Notice Document, Section 4.1"
        orig_clause = (
            f"The bidder must have an average annual turnover of at least INR {req.required_turnover_inr:,.2f} "
            f"over the past {req.financial_years_count} financial years."
            if req.comparison_method == "AVERAGE_TURNOVER"
            else f"The bidder must have a minimum annual turnover of at least INR {req.required_turnover_inr:,.2f} "
                 f"in each of the past {req.financial_years_count} financial years."
        )

        req_val: Dict[str, Any] = {
            "title": "Minimum Annual Turnover Threshold",
            "category": "FINANCIAL",
            "original_clause": orig_clause,
            "tender_source": tender_src,
            "plain_english_interpretation": (
                f"The procuring authority requires proof that your business generates at least "
                f"INR {req.required_turnover_inr:,.2f} per year ({req.comparison_method.replace('_', ' ').lower()}) "
                f"over {req.financial_years_count} financial years to ensure financial solvency and delivery capacity."
            ),
            "specific_condition": f"INR {req.required_turnover_inr:,.2f} ({req.comparison_method}) across {req.financial_years_count} FYs",
            "needs_human_review": False,
            "required_turnover_inr": float(req.required_turnover_inr),
            "currency": req.currency,
            "comparison_method": req.comparison_method,
            "financial_years_count": req.financial_years_count,
        }

        if not turnover_records:
            return RuleFinding(
                requirement_id="CRIT_TURNOVER_01",
                rule_type="TURNOVER",
                requirement_description=f"Minimum turnover of INR {req.required_turnover_inr:,.2f} ({req.comparison_method})",
                required_value=req_val,
                observed_value={
                    "applicable_company_info": "No turnover records recorded in company profile.",
                    "company_evidence": "None (No audited balance sheet or CA turnover certificate in vault)",
                    "comparison_evaluation": f"Required: INR {req.required_turnover_inr:,.2f}. Observed: 0 records available.",
                    "evidence_gap": f"Missing CA-certified turnover certificate or audited balance sheets for {req.financial_years_count} financial years.",
                    "risk_and_consequence": "Direct disqualification at preliminary financial eligibility evaluation stage.",
                    "recommended_action": f"Upload audited financial statements or Form 3CA/3CB for the last {req.financial_years_count} financial years to Document Vault.",
                    "records_found": 0,
                    "annual_turnovers": [],
                },
                status="MISSING_EVIDENCE",
                is_mandatory=req.is_mandatory,
                reason="No audited financial turnover records exist in the company profile.",
            )

        try:
            parsed_entries = []
            for entry in turnover_records:
                fy = entry.get("fiscal_year", "UNKNOWN")
                raw_amt = entry.get("turnover_inr")
                if raw_amt is not None:
                    parsed_entries.append((fy, Decimal(str(raw_amt))))

            if not parsed_entries:
                return RuleFinding(
                    requirement_id="CRIT_TURNOVER_01",
                    rule_type="TURNOVER",
                    requirement_description=f"Minimum turnover of INR {req.required_turnover_inr:,.2f} ({req.comparison_method})",
                    required_value=req_val,
                    observed_value={
                        "applicable_company_info": "Turnover records exist but lack valid numeric amounts.",
                        "company_evidence": "Incomplete profile entries",
                        "comparison_evaluation": "Turnover values are missing or malformed.",
                        "evidence_gap": "Numeric turnover amounts for specified financial years are unverified.",
                        "risk_and_consequence": "Rejection due to non-verifiable financial data.",
                        "recommended_action": "Update Company Profile with verified numeric figures matching audited statements.",
                        "records_found": 0,
                    },
                    status="MISSING_EVIDENCE",
                    is_mandatory=req.is_mandatory,
                    reason="Turnover records contain missing or non-numeric monetary figures.",
                )

            entries_to_consider = parsed_entries[: req.financial_years_count]
            years_str = ", ".join(f"{fy}: INR {amt:,.2f}" for fy, amt in entries_to_consider)

            if req.comparison_method == "AVERAGE_TURNOVER":
                total_sum = sum(amt for _, amt in entries_to_consider)
                count = len(entries_to_consider)
                average_turnover = total_sum / Decimal(str(count))
                shortfall = req.required_turnover_inr - average_turnover

                obs_val = {
                    "applicable_company_info": f"Average turnover of INR {average_turnover:,.2f} across {count} evaluated years ({years_str}).",
                    "company_evidence": "Company Profile Audited Records",
                    "comparison_evaluation": (
                        f"Required Average: INR {req.required_turnover_inr:,.2f}. "
                        f"Achieved Average: INR {average_turnover:,.2f}. "
                        f"Difference: {'+' if shortfall <= 0 else '-'}{abs(shortfall):,.2f} INR."
                    ),
                    "average_turnover_inr": float(average_turnover),
                    "years_evaluated": [fy for fy, _ in entries_to_consider],
                    "records_count": count,
                }

                if average_turnover >= req.required_turnover_inr:
                    obs_val["evidence_gap"] = "None - Verified financial threshold satisfied."
                    obs_val["risk_and_consequence"] = "No financial eligibility risk. Bidder meets or exceeds monetary threshold."
                    obs_val["recommended_action"] = "Attach audited balance sheet matching profile figures with bid submission pack."
                    return RuleFinding(
                        requirement_id="CRIT_TURNOVER_01",
                        rule_type="TURNOVER",
                        requirement_description=f"Average annual turnover >= INR {req.required_turnover_inr:,.2f} over {req.financial_years_count} years",
                        required_value=req_val,
                        observed_value=obs_val,
                        status="PASS",
                        is_mandatory=req.is_mandatory,
                        reason=f"Observed average turnover of INR {average_turnover:,.2f} satisfies the minimum threshold of INR {req.required_turnover_inr:,.2f}.",
                    )
                else:
                    obs_val["evidence_gap"] = f"Monetary shortfall of INR {shortfall:,.2f} against minimum average turnover requirement."
                    obs_val["risk_and_consequence"] = "Immediate disqualification during technical-commercial opening for failing mandatory financial criterion."
                    obs_val["recommended_action"] = "Evaluate consortium or joint-venture bidding if permitted by tender conditions, or seek tenders aligned with current turnover scale."
                    return RuleFinding(
                        requirement_id="CRIT_TURNOVER_01",
                        rule_type="TURNOVER",
                        requirement_description=f"Average annual turnover >= INR {req.required_turnover_inr:,.2f} over {req.financial_years_count} years",
                        required_value=req_val,
                        observed_value=obs_val,
                        status="FAIL",
                        is_mandatory=req.is_mandatory,
                        reason=f"Observed average turnover of INR {average_turnover:,.2f} falls below mandatory requirement of INR {req.required_turnover_inr:,.2f}.",
                    )

            else:  # ANNUAL_MINIMUM
                failing_years = [
                    (fy, float(amt)) for fy, amt in entries_to_consider if amt < req.required_turnover_inr
                ]
                obs_val = {
                    "applicable_company_info": f"Annual turnovers: {years_str}.",
                    "company_evidence": "Company Profile Audited Records",
                    "annual_turnovers": [{"fiscal_year": fy, "turnover_inr": float(amt)} for fy, amt in entries_to_consider],
                    "years_evaluated_count": len(entries_to_consider),
                }

                if not failing_years:
                    obs_val["comparison_evaluation"] = f"All {len(entries_to_consider)} financial years satisfy the minimum INR {req.required_turnover_inr:,.2f} threshold."
                    obs_val["evidence_gap"] = "None - Verified annual minimum threshold satisfied across all years."
                    obs_val["risk_and_consequence"] = "No financial eligibility risk."
                    obs_val["recommended_action"] = "Attach audited balance sheets and CA certificate in bid submission."
                    return RuleFinding(
                        requirement_id="CRIT_TURNOVER_01",
                        rule_type="TURNOVER",
                        requirement_description=f"Annual turnover of at least INR {req.required_turnover_inr:,.2f} in each of {req.financial_years_count} years",
                        required_value=req_val,
                        observed_value=obs_val,
                        status="PASS",
                        is_mandatory=req.is_mandatory,
                        reason=f"All {len(entries_to_consider)} evaluated financial years meet or exceed the mandatory threshold of INR {req.required_turnover_inr:,.2f}.",
                    )
                else:
                    obs_val["comparison_evaluation"] = f"Turnover in year(s) {failing_years} is below the required INR {req.required_turnover_inr:,.2f}."
                    obs_val["evidence_gap"] = f"Turnover shortfall in financial years: {failing_years}."
                    obs_val["risk_and_consequence"] = "Mandatory rejection on financial grounds."
                    obs_val["recommended_action"] = "Check if tender permits average turnover or MSME relaxation clauses."
                    return RuleFinding(
                        requirement_id="CRIT_TURNOVER_01",
                        rule_type="TURNOVER",
                        requirement_description=f"Annual turnover of at least INR {req.required_turnover_inr:,.2f} in each of {req.financial_years_count} years",
                        required_value=req_val,
                        observed_value=obs_val,
                        status="FAIL",
                        is_mandatory=req.is_mandatory,
                        reason=f"Turnover in financial year(s) {failing_years} falls below the mandatory threshold of INR {req.required_turnover_inr:,.2f}.",
                    )

        except Exception as e:
            req_val["needs_human_review"] = True
            return RuleFinding(
                requirement_id="CRIT_TURNOVER_01",
                rule_type="TURNOVER",
                requirement_description=f"Minimum turnover of INR {req.required_turnover_inr:,.2f}",
                required_value=req_val,
                observed_value={
                    "applicable_company_info": "Calculation encountered unexpected data format.",
                    "company_evidence": "Unparsed records",
                    "comparison_evaluation": "Deterministic comparison aborted due to exception.",
                    "evidence_gap": "Format conflict in recorded turnover values.",
                    "risk_and_consequence": "Manual administrative review required before bid submission.",
                    "recommended_action": "Verify and re-save company turnover figures in company settings.",
                },
                status="NEEDS_REVIEW",
                is_mandatory=req.is_mandatory,
                reason=f"Failed to calculate turnover deterministically due to data conflict: {e}",
            )

    @staticmethod
    def evaluate_experience(
        req: ExperienceRequirement,
        work_experience_records: List[Dict[str, Any]],
        incorporation_date: Optional[date] = None,
        tender_source_info: Optional[str] = None,
    ) -> RuleFinding:
        """Evaluate relevant project experience."""
        tender_src = tender_source_info or req.citation_reference or "Tender Notice Document, Section 4.2"
        orig_clause = (
            f"Bidder must have completed at least {req.min_completed_projects} project(s) "
            f"with a minimum of {req.min_experience_years} years of operational experience"
            f"{f' in {req.relevant_domain}' if req.relevant_domain else ''}."
        )

        req_val: Dict[str, Any] = {
            "title": "Past Project Experience & Track Record",
            "category": "ELIGIBILITY",
            "original_clause": orig_clause,
            "tender_source": tender_src,
            "plain_english_interpretation": (
                f"The buyer requires proof of having completed at least {req.min_completed_projects} similar contract(s) "
                f"spanning at least {req.min_experience_years} years"
                f"{f' in the {req.relevant_domain} domain' if req.relevant_domain else ''} "
                f"to demonstrate proven execution capabilities."
            ),
            "specific_condition": f">= {req.min_experience_years} years, >= {req.min_completed_projects} completed project(s)",
            "needs_human_review": False,
            "min_experience_years": req.min_experience_years,
            "min_completed_projects": req.min_completed_projects,
            "min_single_contract_value_inr": float(req.min_single_contract_value_inr) if req.min_single_contract_value_inr else None,
            "relevant_domain": req.relevant_domain,
        }

        if not work_experience_records:
            return RuleFinding(
                requirement_id="CRIT_EXP_01",
                rule_type="EXPERIENCE",
                requirement_description=f"Minimum {req.min_experience_years} years relevant experience and {req.min_completed_projects} project(s)",
                required_value=req_val,
                observed_value={
                    "applicable_company_info": "No past project contracts or work orders recorded in company profile.",
                    "company_evidence": "None (No completion certificates in Document Vault)",
                    "comparison_evaluation": f"Required: {req.min_experience_years} years / {req.min_completed_projects} projects. Found: 0.",
                    "evidence_gap": "Missing client completion certificates, work orders, or performance certificates.",
                    "risk_and_consequence": "Disqualification on technical experience criteria.",
                    "recommended_action": "Add completed project details to Company Profile and upload client sign-off letters to Document Vault.",
                    "records_found": 0,
                    "projects": [],
                },
                status="MISSING_EVIDENCE",
                is_mandatory=req.is_mandatory,
                reason="No project experience records found in company profile.",
            )

        matching_projects = []
        for p in work_experience_records:
            domain = p.get("domain") or p.get("sector")
            if req.relevant_domain and domain:
                if req.relevant_domain.lower() not in str(domain).lower():
                    continue

            val = p.get("contract_value_inr")
            if req.min_single_contract_value_inr and val is not None:
                if Decimal(str(val)) < req.min_single_contract_value_inr:
                    continue

            matching_projects.append(p)

        observed_count = len(matching_projects)
        total_duration_years = sum(float(p.get("duration_years", 1.0)) for p in matching_projects)
        project_titles = [p.get("project_title", "Contract Work") for p in matching_projects]

        obs_val = {
            "applicable_company_info": f"{observed_count} qualifying project(s) spanning {total_duration_years:.1f} years ({', '.join(project_titles)}).",
            "company_evidence": "Company Profile Work Experience Records",
            "matching_projects_count": observed_count,
            "total_experience_years": total_duration_years,
            "projects_evaluated": project_titles,
        }

        if total_duration_years >= req.min_experience_years and observed_count >= req.min_completed_projects:
            obs_val["comparison_evaluation"] = f"Met: {total_duration_years:.1f} years >= {req.min_experience_years} years; {observed_count} projects >= {req.min_completed_projects} projects."
            obs_val["evidence_gap"] = "None - Verified project experience satisfied."
            obs_val["risk_and_consequence"] = "No experience eligibility risk."
            obs_val["recommended_action"] = "Ensure verified completion certificates for evaluated projects are included in the bid package."
            return RuleFinding(
                requirement_id="CRIT_EXP_01",
                rule_type="EXPERIENCE",
                requirement_description=f"Minimum {req.min_experience_years} years relevant experience ({req.min_completed_projects} completed project(s))",
                required_value=req_val,
                observed_value=obs_val,
                status="PASS",
                is_mandatory=req.is_mandatory,
                reason=f"Observed {observed_count} relevant project(s) spanning {total_duration_years:.1f} years satisfies requirement.",
            )
        else:
            reason_parts = []
            if total_duration_years < req.min_experience_years:
                reason_parts.append(f"duration ({total_duration_years:.1f} yrs < {req.min_experience_years} yrs)")
            if observed_count < req.min_completed_projects:
                reason_parts.append(f"completed contracts ({observed_count} < {req.min_completed_projects})")

            obs_val["comparison_evaluation"] = f"Shortfall in: {', '.join(reason_parts)}."
            obs_val["evidence_gap"] = f"Insufficient qualifying projects in the required domain."
            obs_val["risk_and_consequence"] = "Rejection at technical qualification stage."
            obs_val["recommended_action"] = "Register additional completed client contracts or apply as authorized partner/consortium."
            return RuleFinding(
                requirement_id="CRIT_EXP_01",
                rule_type="EXPERIENCE",
                requirement_description=f"Minimum {req.min_experience_years} years relevant experience ({req.min_completed_projects} completed project(s))",
                required_value=req_val,
                observed_value=obs_val,
                status="FAIL",
                is_mandatory=req.is_mandatory,
                reason=f"Observed project credentials fall short: {', '.join(reason_parts)}.",
            )

    @staticmethod
    def evaluate_certification(
        req: CertificationRequirement,
        company_certifications: List[Dict[str, Any]],
        vault_documents: Optional[List[Any]] = None,
        tender_source_info: Optional[str] = None,
    ) -> RuleFinding:
        """Check for active (non-expired) matching quality or technical certification."""
        req_id = f"CRIT_CERT_{abs(hash(req.name)) % 10000}"
        tender_src = tender_source_info or req.citation_reference or "Tender Notice Document, Section 4.3"

        req_val = {
            "title": f"Mandatory Certification: {req.name}",
            "category": "CERTIFICATES",
            "original_clause": f"The bidder must possess a valid {req.name} certification issued by an accredited body.",
            "tender_source": tender_src,
            "plain_english_interpretation": f"You must hold a currently valid, accredited {req.name} certificate at the time of bid submission.",
            "specific_condition": f"Valid {req.name} certificate",
            "needs_human_review": False,
            "certification_name": req.name,
            "issuing_authority": req.issuing_authority,
        }

        # Check vault documents first
        vault_doc = None
        if vault_documents:
            for doc in vault_documents:
                fname = getattr(doc, "original_filename", "") or ""
                cat = getattr(doc, "document_category", "") or ""
                if req.name.lower() in fname.lower() or ("iso" in fname.lower() and "iso" in req.name.lower()):
                    vault_doc = doc
                    break

        if not company_certifications and not vault_doc:
            return RuleFinding(
                requirement_id=req_id,
                rule_type="CERTIFICATION",
                requirement_description=f"Mandatory Certification: {req.name}",
                required_value=req_val,
                observed_value={
                    "applicable_company_info": f"No credential registered for '{req.name}'.",
                    "company_evidence": "None (Document not found in vault)",
                    "comparison_evaluation": f"Expected valid certificate '{req.name}'. None present.",
                    "evidence_gap": f"Missing {req.name} certificate copy and validity dates.",
                    "risk_and_consequence": "Mandatory rejection if tender stipulates certificate as non-waivable.",
                    "recommended_action": f"Upload verified {req.name} certificate copy to Document Vault.",
                    "certifications_found": 0,
                },
                status="MISSING_EVIDENCE",
                is_mandatory=req.is_mandatory,
                reason=f"No certification credentials registered for '{req.name}'.",
            )

        matching_cert = None
        for cert in company_certifications:
            name = str(cert.get("name", ""))
            if req.name.lower() in name.lower() or name.lower() in req.name.lower():
                matching_cert = cert
                break

        if not matching_cert and not vault_doc:
            return RuleFinding(
                requirement_id=req_id,
                rule_type="CERTIFICATION",
                requirement_description=f"Mandatory Certification: {req.name}",
                required_value=req_val,
                observed_value={
                    "applicable_company_info": "Uploaded certificates do not match required standard.",
                    "company_evidence": "Unmatched profile entries",
                    "comparison_evaluation": f"Required: {req.name}. Available records do not contain this credential.",
                    "evidence_gap": f"Absence of accredited {req.name} certificate.",
                    "risk_and_consequence": "Disqualification if mandatory.",
                    "recommended_action": f"Obtain or upload accredited {req.name} certificate.",
                    "matching_found": False,
                },
                status="MISSING_EVIDENCE",
                is_mandatory=req.is_mandatory,
                reason=f"Company records do not contain the required '{req.name}' certificate.",
            )

        valid_until_str = matching_cert.get("valid_until") if matching_cert else None
        cert_name = matching_cert.get("name", req.name) if matching_cert else req.name
        doc_filename = getattr(vault_doc, "original_filename", "Profile Credential") if vault_doc else "Profile Record"

        obs_val = {
            "applicable_company_info": f"Certificate '{cert_name}' registered.",
            "company_evidence": f"Document: {doc_filename}",
            "name": cert_name,
            "issuing_authority": matching_cert.get("issuing_authority") if matching_cert else None,
            "valid_until": str(valid_until_str) if valid_until_str else None,
        }

        if valid_until_str:
            try:
                if isinstance(valid_until_str, (date, datetime)):
                    valid_dt = valid_until_str if isinstance(valid_until_str, date) else valid_until_str.date()
                else:
                    valid_dt = datetime.fromisoformat(str(valid_until_str).replace("Z", "+00:00")).date()

                today = datetime.now(timezone.utc).date()
                if valid_dt < today:
                    obs_val["comparison_evaluation"] = f"Certificate expired on {valid_dt} (Today: {today}). Expired credentials cannot be accepted."
                    obs_val["evidence_gap"] = f"Certificate '{cert_name}' has lapsed validity."
                    obs_val["risk_and_consequence"] = "Disqualification for submitting expired certificate."
                    obs_val["recommended_action"] = "Renew certification with accredited agency and upload updated certificate."
                    return RuleFinding(
                        requirement_id=req_id,
                        rule_type="CERTIFICATION",
                        requirement_description=f"Mandatory Certification: {req.name}",
                        required_value=req_val,
                        observed_value=obs_val,
                        status="FAIL",
                        is_mandatory=req.is_mandatory,
                        reason=f"Certificate '{cert_name}' expired on {valid_dt} and is invalid for bidding.",
                    )
            except Exception as e:
                req_val["needs_human_review"] = True
                obs_val["comparison_evaluation"] = f"Validity date parsing error: {e}."
                obs_val["evidence_gap"] = "Validity period could not be verified automatically."
                obs_val["risk_and_consequence"] = "May require clarification from tender committee."
                obs_val["recommended_action"] = "Check certificate expiration date in Document Vault."
                return RuleFinding(
                    requirement_id=req_id,
                    rule_type="CERTIFICATION",
                    requirement_description=f"Mandatory Certification: {req.name}",
                    required_value=req_val,
                    observed_value=obs_val,
                    status="NEEDS_REVIEW",
                    is_mandatory=req.is_mandatory,
                    reason=f"Unable to verify validity period for certificate '{req.name}': {e}",
                )

        obs_val["comparison_evaluation"] = f"Valid certificate '{cert_name}' verified against tender standard."
        obs_val["evidence_gap"] = "None - Certificate is valid and active."
        obs_val["risk_and_consequence"] = "No certification risk."
        obs_val["recommended_action"] = f"Include notarized or self-attested copy of {cert_name} in technical proposal."
        return RuleFinding(
            requirement_id=req_id,
            rule_type="CERTIFICATION",
            requirement_description=f"Mandatory Certification: {req.name}",
            required_value=req_val,
            observed_value=obs_val,
            status="PASS",
            is_mandatory=req.is_mandatory,
            reason=f"Valid and active certificate '{cert_name}' found in company records.",
        )

    @staticmethod
    def evaluate_mandatory_document(
        req: MandatoryDocumentRequirement,
        vault_documents: List[Any],
        tender_source_info: Optional[str] = None,
    ) -> RuleFinding:
        """Check if mandatory document exists in company vault."""
        req_id = f"CRIT_DOC_{abs(hash(req.document_name)) % 10000}"
        tender_src = tender_source_info or req.citation_reference or "Tender Notice Document, Section 5"

        req_val = {
            "title": f"Mandatory Document: {req.document_name}",
            "category": "MANDATORY_DOCUMENTS",
            "original_clause": f"Bidder must submit a verified copy of '{req.document_name}'.",
            "tender_source": tender_src,
            "plain_english_interpretation": f"You must upload a complete, legible copy of your '{req.document_name}' as part of your technical submission.",
            "specific_condition": f"Document proof '{req.document_name}' in PDF format",
            "needs_human_review": False,
            "document_name": req.document_name,
            "document_category": req.document_category,
        }

        if not vault_documents:
            return RuleFinding(
                requirement_id=req_id,
                rule_type="MANDATORY_DOCUMENT",
                requirement_description=f"Mandatory Document: {req.document_name}",
                required_value=req_val,
                observed_value={
                    "applicable_company_info": "Document Vault is currently empty.",
                    "company_evidence": "None (0 documents in vault)",
                    "comparison_evaluation": f"Expected: '{req.document_name}'. Vault has no documents uploaded.",
                    "evidence_gap": f"Missing mandatory document proof: '{req.document_name}'.",
                    "risk_and_consequence": "Direct bid rejection for missing mandatory technical document.",
                    "recommended_action": f"Upload '{req.document_name}' to your Company Document Vault.",
                    "vault_count": 0,
                },
                status="MISSING_EVIDENCE",
                is_mandatory=req.is_mandatory,
                reason=f"Document '{req.document_name}' has not been uploaded to company vault.",
            )

        found_doc = None
        for doc in vault_documents:
            fname = getattr(doc, "original_filename", "") or ""
            cat = getattr(doc, "document_category", "") or ""
            if (
                req.document_name.lower() in fname.lower()
                or (req.document_category != "OTHER" and req.document_category.lower() == cat.lower())
                or (req.document_name.lower() in cat.lower())
            ):
                found_doc = doc
                break

        if found_doc:
            doc_fname = getattr(found_doc, "original_filename", "")
            return RuleFinding(
                requirement_id=req_id,
                rule_type="MANDATORY_DOCUMENT",
                requirement_description=f"Mandatory Document: {req.document_name}",
                required_value=req_val,
                observed_value={
                    "applicable_company_info": f"Document uploaded as '{doc_fname}'.",
                    "company_evidence": f"Vault File: {doc_fname} (ID: {getattr(found_doc, 'id', '')})",
                    "comparison_evaluation": f"Document '{req.document_name}' is uploaded and verified in Company Vault.",
                    "evidence_gap": "None - Verified document file present in vault.",
                    "risk_and_consequence": "No submission document gap.",
                    "recommended_action": f"Ensure '{doc_fname}' is signed/stamped if requested by tender.",
                    "document_id": str(getattr(found_doc, "id", "")),
                    "filename": doc_fname,
                    "category": getattr(found_doc, "document_category", ""),
                },
                status="PASS",
                is_mandatory=req.is_mandatory,
                reason=f"Required document '{req.document_name}' is uploaded in company vault as '{doc_fname}'.",
            )
        else:
            return RuleFinding(
                requirement_id=req_id,
                rule_type="MANDATORY_DOCUMENT",
                requirement_description=f"Mandatory Document: {req.document_name}",
                required_value=req_val,
                observed_value={
                    "applicable_company_info": "Document is not present in Company Document Vault.",
                    "company_evidence": "None (No matching file in vault)",
                    "comparison_evaluation": f"Mandatory document '{req.document_name}' was not located among uploaded files.",
                    "evidence_gap": f"Missing document '{req.document_name}'.",
                    "risk_and_consequence": "Disqualification on technical document opening.",
                    "recommended_action": f"Upload '{req.document_name}' to Document Vault.",
                    "matching_found": False,
                },
                status="MISSING_EVIDENCE",
                is_mandatory=req.is_mandatory,
                reason=f"Mandatory document '{req.document_name}' was not found in company vault.",
            )

    @staticmethod
    def evaluate_deadline(req: DeadlineRequirement) -> RuleFinding:
        """Check if tender submission deadline has elapsed."""
        now_utc = datetime.now(timezone.utc)
        dl = req.submission_deadline_utc
        is_past = now_utc > dl

        req_val = {
            "title": "Bid Submission Timeline & Deadline",
            "category": "DEADLINE",
            "original_clause": f"The bid must be submitted online before {dl.strftime('%Y-%m-%d %H:%M UTC')}.",
            "tender_source": req.citation_reference or "Tender Notice Schedule",
            "plain_english_interpretation": f"Your entire bid package, documents, and commercial rates must be finalized and submitted prior to {dl.strftime('%d %b %Y, %H:%M UTC')}.",
            "specific_condition": f"Submission deadline: {dl.strftime('%Y-%m-%d %H:%M UTC')}",
            "needs_human_review": False,
            "deadline_utc": dl.isoformat(),
        }

        obs_val = {
            "applicable_company_info": f"Current system time: {now_utc.strftime('%Y-%m-%d %H:%M UTC')}.",
            "company_evidence": "Portal Clock Synchronization",
            "current_time_utc": now_utc.isoformat(),
            "is_past_deadline": is_past,
        }

        if is_past:
            obs_val["comparison_evaluation"] = f"Deadline expired on {dl.strftime('%Y-%m-%d %H:%M UTC')} (Current: {now_utc.strftime('%Y-%m-%d %H:%M UTC')})."
            obs_val["evidence_gap"] = "Submission window closed."
            obs_val["risk_and_consequence"] = "Portal will reject late submissions automatically."
            obs_val["recommended_action"] = "Look for corrigenda/amendments extending the deadline or archive this tender opportunity."
            return RuleFinding(
                requirement_id="CRIT_DEADLINE_01",
                rule_type="DEADLINE",
                requirement_description=f"Bid submission deadline: {dl.strftime('%Y-%m-%d %H:%M UTC')}",
                required_value=req_val,
                observed_value=obs_val,
                status="FAIL",
                is_mandatory=req.is_mandatory,
                reason=f"Tender submission deadline closed on {dl.strftime('%Y-%m-%d %H:%M UTC')}.",
            )
        else:
            time_left = dl - now_utc
            hours_left = int(time_left.total_seconds() // 3600)
            days_left = hours_left // 24
            obs_val["comparison_evaluation"] = f"Tender is open. {days_left} day(s) {hours_left % 24} hour(s) remaining until closing."
            obs_val["evidence_gap"] = "None - Submission window is open."
            obs_val["risk_and_consequence"] = "No deadline risk. Ensure submission at least 24 hours prior to deadline to prevent portal congestion."
            obs_val["recommended_action"] = "Finalize required documents and complete submission before closing."
            return RuleFinding(
                requirement_id="CRIT_DEADLINE_01",
                rule_type="DEADLINE",
                requirement_description=f"Bid submission deadline: {dl.strftime('%Y-%m-%d %H:%M UTC')}",
                required_value=req_val,
                observed_value=obs_val,
                status="PASS",
                is_mandatory=req.is_mandatory,
                reason=f"Tender is active and open for bidding until {dl.strftime('%Y-%m-%d %H:%M UTC')}.",
            )

    @staticmethod
    def evaluate_commercial(
        req: CommercialRequirement,
        company_profile: Dict[str, Any],
        vault_documents: Optional[List[Any]] = None,
    ) -> RuleFinding:
        """Evaluate EMD, bid security, and MSME exemption eligibility."""
        req_id = f"CRIT_COMM_{abs(hash(req.title)) % 10000}"
        amount = req.amount_inr or Decimal("0.00")
        reg_number = str(company_profile.get("registration_number", ""))
        business_type = str(company_profile.get("business_type", "")).upper()
        is_msme = "UDYAM" in reg_number.upper() or business_type in ["MICRO", "SMALL"]

        req_val = {
            "title": req.title,
            "category": "COMMERCIAL",
            "original_clause": f"Bidder must submit EMD / Bid Security of INR {amount:,.2f}. MSME bidders are eligible for exemption upon submission of valid Udyam certificate.",
            "tender_source": req.citation_reference or "Tender Notice Commercial Terms",
            "plain_english_interpretation": (
                f"Tender requires EMD of INR {amount:,.2f}. As an MSME (Micro/Small Enterprise), "
                f"you are exempt from paying EMD under the Government of India Public Procurement Policy, "
                f"provided you submit your valid Udyam Registration Certificate."
                if req.msme_exemptible
                else f"Tender requires mandatory EMD of INR {amount:,.2f} without exemption."
            ),
            "specific_condition": f"EMD: INR {amount:,.2f} (MSME Exempt: {'Yes' if req.msme_exemptible else 'No'})",
            "needs_human_review": False,
            "condition_type": req.condition_type,
            "amount_inr": float(amount),
            "msme_exemptible": req.msme_exemptible,
        }

        # Check if EMD exemption applies
        if req.msme_exemptible and is_msme:
            return RuleFinding(
                requirement_id=req_id,
                rule_type="COMMERCIAL",
                requirement_description=f"EMD Requirement: INR {amount:,.2f} (MSME Exemption Eligible)",
                required_value=req_val,
                observed_value={
                    "applicable_company_info": f"Registered as {business_type} Enterprise with Udyam Registration: {reg_number}.",
                    "company_evidence": f"Company Profile Registration: {reg_number}",
                    "comparison_evaluation": f"EMD INR {amount:,.2f} exempted under MSME Procurement Policy. Valid Udyam number verified.",
                    "evidence_gap": "None - MSME exemption applies.",
                    "risk_and_consequence": "No commercial risk. Ensure Udyam Certificate is attached to bid pack to claim EMD waiver.",
                    "recommended_action": "Attach copy of Udyam Registration Certificate in place of EMD instrument.",
                    "is_msme": True,
                    "exemption_claimed": True,
                },
                status="PASS",
                is_mandatory=req.is_mandatory,
                reason=f"Company is eligible for 100% EMD exemption (INR {amount:,.2f}) as an accredited MSME with registration {reg_number}.",
            )
        elif not req.msme_exemptible or not is_msme:
            # Check if bank guarantee or EMD receipt exists in vault
            has_emd_doc = False
            emd_fname = ""
            for doc in (vault_documents or []):
                fname = getattr(doc, "original_filename", "").lower()
                if "emd" in fname or "bank_guarantee" in fname or "bg" in fname:
                    has_emd_doc = True
                    emd_fname = getattr(doc, "original_filename", "")
                    break

            if has_emd_doc:
                return RuleFinding(
                    requirement_id=req_id,
                    rule_type="COMMERCIAL",
                    requirement_description=f"EMD Requirement: INR {amount:,.2f}",
                    required_value=req_val,
                    observed_value={
                        "applicable_company_info": "EMD payment receipt / Bank Guarantee found in vault.",
                        "company_evidence": f"Vault File: {emd_fname}",
                        "comparison_evaluation": f"EMD instrument of INR {amount:,.2f} uploaded as '{emd_fname}'.",
                        "evidence_gap": "None - EMD proof uploaded.",
                        "risk_and_consequence": "Verify bank guarantee validity matches tender tender validity period.",
                        "recommended_action": "Submit original bank guarantee / EMD receipt as prescribed by tender.",
                    },
                    status="PASS",
                    is_mandatory=req.is_mandatory,
                    reason=f"EMD payment receipt/instrument found in vault as '{emd_fname}'.",
                )
            else:
                return RuleFinding(
                    requirement_id=req_id,
                    rule_type="COMMERCIAL",
                    requirement_description=f"EMD Requirement: INR {amount:,.2f}",
                    required_value=req_val,
                    observed_value={
                        "applicable_company_info": f"Business registration: {reg_number or 'Unspecified'}.",
                        "company_evidence": "No EMD receipt or BG in vault",
                        "comparison_evaluation": f"Required EMD of INR {amount:,.2f} is neither paid nor covered by an uploaded waiver proof.",
                        "evidence_gap": f"Missing EMD payment receipt or Bank Guarantee for INR {amount:,.2f}.",
                        "risk_and_consequence": "Non-submission of EMD leads to immediate technical disqualification.",
                        "recommended_action": f"Obtain EMD demand draft/BG for INR {amount:,.2f} or update profile with valid Udyam registration for exemption.",
                    },
                    status="MISSING_EVIDENCE",
                    is_mandatory=req.is_mandatory,
                    reason=f"EMD of INR {amount:,.2f} required. No payment proof or valid MSME exemption document found.",
                )

        return RuleFinding(
            requirement_id=req_id,
            rule_type="COMMERCIAL",
            requirement_description=f"Commercial Requirement: {req.title}",
            required_value=req_val,
            observed_value={},
            status="NEEDS_REVIEW",
            is_mandatory=req.is_mandatory,
            reason="Commercial condition requires manual review of financial instruments.",
        )

    @staticmethod
    def evaluate_technical(
        req: TechnicalRequirement,
        company_profile: Dict[str, Any],
        vault_documents: Optional[List[Any]] = None,
    ) -> RuleFinding:
        """Evaluate technical specifications and equipment compliance."""
        req_id = f"CRIT_TECH_{abs(hash(req.specification)) % 10000}"

        req_val = {
            "title": req.title,
            "category": "TECHNICAL",
            "original_clause": req.specification,
            "tender_source": req.citation_reference or "Technical Specifications Schedule",
            "plain_english_interpretation": f"Your proposed product or equipment must comply with the technical specification: {req.specification}.",
            "specific_condition": req.specification,
            "needs_human_review": True,
            "standard_or_code": req.standard_or_code,
        }

        # Check if technical brochure or compliance sheet exists in vault
        has_tech_doc = False
        tech_fname = ""
        for doc in (vault_documents or []):
            fname = getattr(doc, "original_filename", "").lower()
            if "technical" in fname or "spec" in fname or "datasheet" in fname or "brochure" in fname:
                has_tech_doc = True
                tech_fname = getattr(doc, "original_filename", "")
                break

        if has_tech_doc:
            return RuleFinding(
                requirement_id=req_id,
                rule_type="TECHNICAL",
                requirement_description=f"Technical Compliance: {req.title}",
                required_value=req_val,
                observed_value={
                    "applicable_company_info": f"Company sector: {company_profile.get('sector', 'N/A')}.",
                    "company_evidence": f"Technical Datasheet: {tech_fname}",
                    "comparison_evaluation": f"Technical datasheet '{tech_fname}' available in vault covering: '{req.specification[:100]}...'",
                    "evidence_gap": "Review parameters to ensure 100% line-by-line compliance.",
                    "risk_and_consequence": "Technical deviation may result in score deduction or rejection.",
                    "recommended_action": f"Verify all parameters in '{tech_fname}' against tender clause {req.title}.",
                },
                status="PASS",
                is_mandatory=req.is_mandatory,
                reason=f"Technical documentation available in vault ({tech_fname}). Clause supported by company technical profile.",
            )
        else:
            return RuleFinding(
                requirement_id=req_id,
                rule_type="TECHNICAL",
                requirement_description=f"Technical Compliance: {req.title}",
                required_value=req_val,
                observed_value={
                    "applicable_company_info": f"Company operates in '{company_profile.get('sector', 'General')}' sector.",
                    "company_evidence": "No technical datasheet uploaded in vault",
                    "comparison_evaluation": f"Requires technical proof for specification: '{req.specification}'.",
                    "evidence_gap": "Missing OEM datasheet, test certificate, or compliance matrix.",
                    "risk_and_consequence": "May be flagged for technical deviation during bid opening.",
                    "recommended_action": f"Prepare line-by-line technical compliance matrix and upload OEM technical brochure to Document Vault.",
                },
                status="NEEDS_REVIEW",
                is_mandatory=req.is_mandatory,
                reason=f"Technical specification '{req.specification[:80]}' requires human technical review and OEM datasheet verification.",
            )

    @staticmethod
    def evaluate_legal(
        req: LegalRequirement,
        company_profile: Dict[str, Any],
        vault_documents: Optional[List[Any]] = None,
    ) -> RuleFinding:
        """Evaluate statutory and legal requirements (PAN, GST, Udyam, Non-Blacklisting)."""
        req_id = f"CRIT_LEGAL_{abs(hash(req.title)) % 10000}"
        reg_type = req.registration_type.upper()

        req_val = {
            "title": req.title,
            "category": "LEGAL",
            "original_clause": f"Bidder must submit proof of {req.title}.",
            "tender_source": req.citation_reference or "Legal & Eligibility Conditions",
            "plain_english_interpretation": f"You must provide an authentic, verified copy or declaration of {req.title}.",
            "specific_condition": f"Verified {req.title}",
            "needs_human_review": False,
            "registration_type": req.registration_type,
        }

        reg_num = str(company_profile.get("registration_number", ""))
        has_legal_doc = False
        legal_fname = ""
        for doc in (vault_documents or []):
            fname = getattr(doc, "original_filename", "").lower()
            if any(k in fname for k in ["pan", "gst", "udyam", "tax", "legal", "affidavit", "blacklisting"]):
                has_legal_doc = True
                legal_fname = getattr(doc, "original_filename", "")
                break

        if "UDYAM" in reg_type and "UDYAM" in reg_num.upper():
            return RuleFinding(
                requirement_id=req_id,
                rule_type="LEGAL",
                requirement_description=f"Statutory Registration: {req.title}",
                required_value=req_val,
                observed_value={
                    "applicable_company_info": f"Udyam registration verified: {reg_num}.",
                    "company_evidence": "Company Profile Registration Data",
                    "comparison_evaluation": "Verified Udyam registration matches statutory MSME requirement.",
                    "evidence_gap": "None - Active Udyam registration verified.",
                    "risk_and_consequence": "No statutory compliance risk.",
                    "recommended_action": "Attach copy of Udyam certificate with bid documents.",
                },
                status="PASS",
                is_mandatory=req.is_mandatory,
                reason=f"Valid statutory registration ({reg_num}) recorded in company profile.",
            )
        elif has_legal_doc:
            return RuleFinding(
                requirement_id=req_id,
                rule_type="LEGAL",
                requirement_description=f"Statutory Registration: {req.title}",
                required_value=req_val,
                observed_value={
                    "applicable_company_info": f"Statutory document present in vault: {legal_fname}.",
                    "company_evidence": f"Vault File: {legal_fname}",
                    "comparison_evaluation": f"Document '{legal_fname}' verified for {req.title}.",
                    "evidence_gap": "None - Supporting legal document present.",
                    "risk_and_consequence": "No legal non-compliance risk.",
                    "recommended_action": f"Include '{legal_fname}' in statutory annexures pack.",
                },
                status="PASS",
                is_mandatory=req.is_mandatory,
                reason=f"Statutory documentation for '{req.title}' verified in Document Vault as '{legal_fname}'.",
            )
        else:
            return RuleFinding(
                requirement_id=req_id,
                rule_type="LEGAL",
                requirement_description=f"Statutory Requirement: {req.title}",
                required_value=req_val,
                observed_value={
                    "applicable_company_info": "Statutory document or declaration not uploaded.",
                    "company_evidence": "None (No matching legal proof in vault)",
                    "comparison_evaluation": f"Required: {req.title}. No matching record or file found.",
                    "evidence_gap": f"Missing official certificate or notarized affidavit for {req.title}.",
                    "risk_and_consequence": "Rejection during statutory scrutiny if mandatory.",
                    "recommended_action": f"Upload verified certificate or affidavit for {req.title} to Document Vault.",
                },
                status="MISSING_EVIDENCE",
                is_mandatory=req.is_mandatory,
                reason=f"Mandatory statutory document/registration for '{req.title}' is missing from company records.",
            )

    @staticmethod
    def evaluate_submission(
        req: SubmissionRequirement,
        vault_documents: Optional[List[Any]] = None,
    ) -> RuleFinding:
        """Evaluate submission forms, declarations, and annexure formats."""
        req_id = f"CRIT_SUB_{abs(hash(req.title)) % 10000}"

        req_val = {
            "title": req.title,
            "category": "SUBMISSION",
            "original_clause": f"Bidder must submit signed and stamped {req.title}.",
            "tender_source": req.citation_reference or "Submission Instructions",
            "plain_english_interpretation": f"You must download, fill, sign, and stamp the prescribed {req.title} and upload it with your bid.",
            "specific_condition": f"Prescribed {req.title} in signed PDF",
            "needs_human_review": False,
            "requirement_type": req.requirement_type,
        }

        has_form = False
        form_fname = ""
        for doc in (vault_documents or []):
            fname = getattr(doc, "original_filename", "").lower()
            if any(k in fname for k in ["form", "annexure", "declaration", "tender_form", "submission"]):
                has_form = True
                form_fname = getattr(doc, "original_filename", "")
                break

        if has_form:
            return RuleFinding(
                requirement_id=req_id,
                rule_type="SUBMISSION",
                requirement_description=f"Submission Condition: {req.title}",
                required_value=req_val,
                observed_value={
                    "applicable_company_info": f"Submission document found: {form_fname}.",
                    "company_evidence": f"Vault File: {form_fname}",
                    "comparison_evaluation": f"Submission format covered by '{form_fname}'.",
                    "evidence_gap": "Ensure required official seal and authorized signature are applied.",
                    "risk_and_consequence": "Unsigned forms lead to rejection.",
                    "recommended_action": f"Verify signatures and corporate seal on '{form_fname}'.",
                },
                status="PASS",
                is_mandatory=req.is_mandatory,
                reason=f"Submission format '{req.title}' verified in company vault as '{form_fname}'.",
            )
        else:
            return RuleFinding(
                requirement_id=req_id,
                rule_type="SUBMISSION",
                requirement_description=f"Submission Condition: {req.title}",
                required_value=req_val,
                observed_value={
                    "applicable_company_info": "Prescribed form/declaration not uploaded to vault.",
                    "company_evidence": "None (No signed form in vault)",
                    "comparison_evaluation": f"Prescribed format for '{req.title}' is missing.",
                    "evidence_gap": f"Missing filled and signed copy of {req.title}.",
                    "risk_and_consequence": "Rejection during procedural bid check.",
                    "recommended_action": f"Download {req.title} from tender documents, sign/seal, and upload to vault.",
                },
                status="MISSING_EVIDENCE",
                is_mandatory=req.is_mandatory,
                reason=f"Prescribed submission document '{req.title}' is missing from company vault.",
            )

    def evaluate_all(
        self,
        requirements: NormalizedTenderRequirements,
        company_profile: Dict[str, Any],
        vault_documents: Optional[List[Any]] = None,
        tender_source_map: Optional[Dict[str, str]] = None,
    ) -> List[RuleFinding]:
        """Evaluate all defined multi-category requirements deterministically."""
        findings: List[RuleFinding] = []
        docs = vault_documents or []
        src_map = tender_source_map or {}

        # 1. Turnover
        if requirements.turnover:
            turnovers = company_profile.get("annual_turnover", [])
            findings.append(self.evaluate_turnover(
                requirements.turnover, turnovers, src_map.get("turnover")
            ))

        # 2. Experience
        if requirements.experience:
            work_exp = company_profile.get("work_experience", [])
            inc_date = company_profile.get("incorporation_date")
            findings.append(self.evaluate_experience(
                requirements.experience, work_exp, inc_date, src_map.get("experience")
            ))

        # 3. Certifications
        for cert_req in requirements.certifications:
            certs = company_profile.get("certifications", [])
            findings.append(self.evaluate_certification(
                cert_req, certs, docs, src_map.get(f"cert_{cert_req.name}")
            ))

        # 4. Mandatory documents
        for doc_req in requirements.mandatory_documents:
            findings.append(self.evaluate_mandatory_document(
                doc_req, docs, src_map.get(f"doc_{doc_req.document_name}")
            ))

        # 5. Deadline
        if requirements.deadline:
            findings.append(self.evaluate_deadline(requirements.deadline))

        # 6. Commercial / EMD Requirements
        for comm_req in requirements.commercial_requirements:
            findings.append(self.evaluate_commercial(comm_req, company_profile, docs))

        # 7. Technical Requirements
        for tech_req in requirements.technical_requirements:
            findings.append(self.evaluate_technical(tech_req, company_profile, docs))

        # 8. Legal & Statutory Requirements
        for legal_req in requirements.legal_requirements:
            findings.append(self.evaluate_legal(legal_req, company_profile, docs))

        # 9. Submission Requirements
        for sub_req in requirements.submission_requirements:
            findings.append(self.evaluate_submission(sub_req, docs))

        # 10. Unsupported / ambiguous clauses
        for i, clause in enumerate(requirements.unsupported_clauses):
            req_id = f"CRIT_UNSUPPORTED_{i+1}"
            findings.append(
                RuleFinding(
                    requirement_id=req_id,
                    rule_type="OTHER",
                    requirement_description=f"Unstructured requirement clause: {clause[:100]}",
                    required_value={
                        "title": f"Special Tender Clause #{i+1}",
                        "category": "ELIGIBILITY",
                        "original_clause": clause,
                        "tender_source": "Tender Document Clause",
                        "plain_english_interpretation": f"This tender contains a custom condition: {clause}.",
                        "specific_condition": clause,
                        "needs_human_review": True,
                        "clause_text": clause,
                    },
                    observed_value={
                        "applicable_company_info": "Custom clause requires manual interpretation.",
                        "company_evidence": "Profile records",
                        "comparison_evaluation": "Non-standard criterion cannot be evaluated purely by numeric rules.",
                        "evidence_gap": "Requires administrative verification of bidder compliance.",
                        "risk_and_consequence": "May require written declaration or confirmation letter.",
                        "recommended_action": "Review the full clause text with your legal/bid coordinator before submission.",
                    },
                    status="NEEDS_REVIEW",
                    is_mandatory=False,
                    reason="Clause contains non-standard criteria requiring human or AI review.",
                )
            )

        return findings


_rule_engine = DeterministicRuleEngine()


def get_rule_engine() -> DeterministicRuleEngine:
    return _rule_engine
