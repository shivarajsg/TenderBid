from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from app.services.compliance.rule_engine import RuleFinding


class ReportBuilder:
    """
    Constructs the final compliance report and computes overall eligibility,
    status metrics, missing document checklists, risk assessments, and action plans
    strictly according to the documented decision policy.
    """

    @staticmethod
    def derive_overall_status(
        findings: List[RuleFinding],
        has_usable_tender_documents: bool = True,
    ) -> Tuple[str, Decimal, str]:
        """
        Derive overall status, percentage score, and human-readable summary.
        Returns: (overall_status, overall_score, summary)
        """
        # Blocked when no substantive eligibility criteria could be evaluated due to missing usable documents
        substantive_findings = [
            f for f in findings
            if f.rule_type != "DEADLINE" and not f.requirement_id.startswith("CRIT_BLOCKED")
        ]
        if not has_usable_tender_documents and not substantive_findings:
            return (
                "ANALYSIS_BLOCKED_NO_DOCUMENTS",
                Decimal("0.00"),
                "Full compliance analysis is unavailable because no usable tender documents have been indexed. "
                "Upload or process the tender documents to evaluate the actual eligibility conditions.",
            )

        total_criteria = len(findings)
        pass_count = sum(1 for f in findings if f.status == "PASS")
        fail_mandatory = [f for f in findings if f.status == "FAIL" and f.is_mandatory]
        missing_mandatory = [f for f in findings if f.status == "MISSING_EVIDENCE" and f.is_mandatory]
        needs_review = [f for f in findings if f.status == "NEEDS_REVIEW"]

        # Calculate score percentage
        score_val = (Decimal(str(pass_count)) / Decimal(str(total_criteria))) * Decimal("100.00")
        score = Decimal(f"{score_val:.2f}")

        # Core non-negotiable policy:
        # 1. Any mandatory FAIL => NOT_ELIGIBLE (DOES NOT MEET MANDATORY REQUIREMENTS)
        if fail_mandatory:
            status = "NOT_ELIGIBLE"
            failing_items = [f"{f.requirement_id} ({f.requirement_description})" for f in fail_mandatory]
            summary = (
                f"DOES NOT MEET MANDATORY REQUIREMENTS. The company is NOT ELIGIBLE because {len(fail_mandatory)} mandatory "
                f"requirement(s) failed deterministic verification: {'; '.join(failing_items)}. Bidding with current credentials carries "
                f"high risk of summary disqualification during initial technical scrutiny."
            )
            if not has_usable_tender_documents:
                summary += " (Notice: Evaluated against structured tender parameters. No physical tender documents were indexed.)"
            return status, score, summary

        # 2. Missing mandatory evidence => PARTIALLY_ELIGIBLE (INCOMPLETE — EVIDENCE REQUIRED)
        if missing_mandatory:
            status = "PARTIALLY_ELIGIBLE"
            missing_names = ", ".join(f.requirement_description for f in missing_mandatory)
            summary = (
                f"INCOMPLETE — EVIDENCE REQUIRED. Core qualifications appear viable, but {len(missing_mandatory)} mandatory "
                f"document proof(s) or certificates are missing from the company vault: {missing_names}. "
                f"Uploading these verified documents is required prior to bid submission."
            )
            if not has_usable_tender_documents:
                summary += " (Notice: Evaluated against structured tender parameters. No physical tender documents were indexed.)"
            return status, score, summary

        # 3. Any condition needing review => NEEDS_REVIEW (REVIEW REQUIRED)
        if needs_review:
            status = "NEEDS_REVIEW"
            review_reasons = "; ".join(f"{f.requirement_id}: {f.reason}" for f in needs_review)
            summary = (
                f"REVIEW REQUIRED. Tender compliance requires manual administrative review due to "
                f"ambiguous specifications, unmapped technical clauses, or verification gaps: {review_reasons}"
            )
            return status, score, summary

        # 4. All mandatory pass, no missing mandatory => ELIGIBLE (MEETS CHECKED REQUIREMENTS)
        status = "ELIGIBLE"
        summary = (
            f"MEETS CHECKED REQUIREMENTS. The company satisfies all {pass_count} evaluated mandatory criteria "
            f"with verified supporting evidence in the company vault. Assessment is based on available evidence "
            f"and does not constitute an official award guarantee by the procuring entity."
        )
        if not has_usable_tender_documents:
            summary += " (Notice: Evaluated against structured tender parameters. No physical tender documents were indexed.)"
        return status, score, summary

    @staticmethod
    def build_missing_documents_checklist(findings: List[RuleFinding]) -> List[Dict[str, Any]]:
        """
        Generate a deduplicated checklist of missing or questionable documents.
        """
        checklist: List[Dict[str, Any]] = []
        seen_docs = set()

        for f in findings:
            if f.status in ["MISSING_EVIDENCE", "FAIL"]:
                req = f.required_value or {}
                obs = f.observed_value or {}
                doc_name = (
                    req.get("document_name")
                    or req.get("certification_name")
                    or f.requirement_description
                )

                if doc_name.lower() in seen_docs:
                    continue
                seen_docs.add(doc_name.lower())

                priority = "HIGH" if f.is_mandatory else "MEDIUM"
                action = obs.get("recommended_action") or f"Upload verified copy of {doc_name} to Document Vault."
                why = f.reason

                checklist.append({
                    "requirement_id": f.requirement_id,
                    "document_name": doc_name,
                    "category": req.get("category", f.rule_type),
                    "why_required": why,
                    "tender_clause": req.get("original_clause", f.requirement_description),
                    "tender_source": req.get("tender_source", "Tender RFP Document"),
                    "available_doc_checked": obs.get("company_evidence", "None"),
                    "action_to_resolve": action,
                    "priority": priority,
                    "is_mandatory": f.is_mandatory,
                })

        return checklist

    @staticmethod
    def build_priority_actions(findings: List[RuleFinding], overall_status: str) -> List[Dict[str, Any]]:
        """
        Generate numbered, prioritized next steps grounded in actual findings.
        """
        actions: List[Dict[str, Any]] = []
        step_number = 1

        # Priority 1: Mandatory Failures
        failing_mandatory = [f for f in findings if f.status == "FAIL" and f.is_mandatory]
        if failing_mandatory:
            for f in failing_mandatory:
                actions.append({
                    "step": step_number,
                    "title": f"Address Mandatory Failure: {f.requirement_description}",
                    "priority": "CRITICAL",
                    "action": f.observed_value.get("recommended_action", f.reason),
                    "impact": "Direct disqualification if unaddressed.",
                })
                step_number += 1

        # Priority 2: Missing Mandatory Proofs
        missing_mandatory = [f for f in findings if f.status == "MISSING_EVIDENCE" and f.is_mandatory]
        if missing_mandatory:
            for f in missing_mandatory:
                actions.append({
                    "step": step_number,
                    "title": f"Upload Missing Mandatory Document: {f.requirement_description}",
                    "priority": "HIGH",
                    "action": f.observed_value.get("recommended_action", "Upload document to Document Vault."),
                    "impact": "Required for technical bid admission.",
                })
                step_number += 1

        # Priority 3: Technical & Administrative Reviews
        needs_review = [f for f in findings if f.status == "NEEDS_REVIEW"]
        if needs_review:
            for f in needs_review:
                actions.append({
                    "step": step_number,
                    "title": f"Review Technical / Ambiguous Clause: {f.requirement_description}",
                    "priority": "MEDIUM",
                    "action": f.observed_value.get("recommended_action", "Review clause details with technical coordinator."),
                    "impact": "Eliminate ambiguity and prevent technical deviation marks.",
                })
                step_number += 1

        # Priority 4: Verified submission pack preparation
        if overall_status == "ELIGIBLE" or (not failing_mandatory and not missing_mandatory):
            actions.append({
                "step": step_number,
                "title": "Assemble Final Technical & Commercial Submission Pack",
                "priority": "FINAL_SUBMISSION",
                "action": "Ensure all documents in Document Vault are digitally signed and uploaded to the official procurement portal at least 24 hours prior to deadline.",
                "impact": "Ensures timely bid submission without portal network latency risks.",
            })

        return actions

    @staticmethod
    def build_technical_financial_comparisons(findings: List[RuleFinding]) -> List[Dict[str, Any]]:
        """
        Extract numerical and objective parameter comparisons.
        """
        comparisons: List[Dict[str, Any]] = []

        for f in findings:
            req = f.required_value or {}
            obs = f.observed_value or {}

            if f.rule_type == "TURNOVER":
                req_amt = req.get("required_turnover_inr")
                obs_amt = obs.get("average_turnover_inr")
                if req_amt is not None:
                    shortfall = (req_amt - obs_amt) if obs_amt is not None else req_amt
                    comparisons.append({
                        "parameter": f"Turnover ({req.get('comparison_method', 'Annual')})",
                        "required_value": f"INR {req_amt:,.2f}",
                        "observed_value": f"INR {obs_amt:,.2f}" if obs_amt is not None else "No data",
                        "difference": f"{'-' if shortfall > 0 else '+'}{abs(shortfall):,.2f} INR" if obs_amt is not None else "Missing",
                        "status": f.status,
                        "source": req.get("tender_source", "Tender Clause 4.1"),
                    })

            elif f.rule_type == "EXPERIENCE":
                req_yrs = req.get("min_experience_years")
                obs_yrs = obs.get("total_experience_years")
                if req_yrs is not None:
                    diff = (obs_yrs - req_yrs) if obs_yrs is not None else -req_yrs
                    comparisons.append({
                        "parameter": "Operational Experience (Years)",
                        "required_value": f"{req_yrs} Years",
                        "observed_value": f"{obs_yrs:.1f} Years" if obs_yrs is not None else "0 Years",
                        "difference": f"{'+' if diff >= 0 else ''}{diff:.1f} Years",
                        "status": f.status,
                        "source": req.get("tender_source", "Tender Clause 4.2"),
                    })

            elif f.rule_type == "COMMERCIAL" and req.get("amount_inr"):
                amt = req.get("amount_inr")
                comparisons.append({
                    "parameter": "Earnest Money Deposit (EMD)",
                    "required_value": f"INR {amt:,.2f}",
                    "observed_value": "Exempt (MSME / Udyam)" if obs.get("exemption_claimed") else ("Paid" if f.status == "PASS" else "Unpaid"),
                    "difference": "Waived under MSME Policy" if obs.get("exemption_claimed") else ("0.00" if f.status == "PASS" else f"-{amt:,.2f} INR"),
                    "status": f.status,
                    "source": req.get("tender_source", "Commercial Schedule"),
                })

        return comparisons

    @staticmethod
    def build_compliance_risks(findings: List[RuleFinding]) -> List[Dict[str, Any]]:
        """
        Identify specific compliance and disqualification risks.
        """
        risks: List[Dict[str, Any]] = []

        for f in findings:
            obs = f.observed_value or {}
            risk_text = obs.get("risk_and_consequence")

            if f.status in ["FAIL", "MISSING_EVIDENCE", "NEEDS_REVIEW"] and risk_text:
                severity = "CRITICAL" if (f.status == "FAIL" and f.is_mandatory) else ("HIGH" if f.status == "MISSING_EVIDENCE" else "MEDIUM")
                risks.append({
                    "requirement_id": f.requirement_id,
                    "title": f.requirement_description,
                    "severity": severity,
                    "description": risk_text,
                    "mitigation": obs.get("recommended_action", "Provide verified documentation."),
                })

        return risks
