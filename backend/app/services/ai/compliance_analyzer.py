import logging
from typing import Dict, List, Optional

from app.schemas.evidence import EvidenceCitation
from app.services.ai.gemini_client import GeminiClient, get_gemini_client
from app.services.compliance.rule_engine import RuleFinding

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert AI Tender Intelligence and MSME Compliance Analyst.
Your duty is to explain tender eligibility findings clearly, factually, objectively, and concisely.

MANDATORY RULES:
1. NEVER alter, contradict, or override a deterministic PASS, FAIL, MISSING_EVIDENCE, or NEEDS_REVIEW status.
2. Only reference facts directly supported by the provided document excerpts and company profile data.
3. If an item failed, explain the exact threshold gap and what document or credential is required.
4. If an item is missing evidence, clearly distinguish missing company documents from confirmed disqualification.
5. Use professional, clear Indian procurement terminology (e.g., INR, Financial Year, Udyam, Chartered Accountant).
6. Never expose internal chain-of-thought. Keep each explanation professional, actionable, and under 3 sentences.
"""


class ComplianceAnalyzer:
    """Uses Gemini to interpret retrieved evidence, explain gaps, and formulate recommendations."""

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.gemini = gemini_client or get_gemini_client()

    def explain_findings(
        self,
        findings: List[RuleFinding],
        evidence: List[EvidenceCitation],
    ) -> Dict[str, str]:
        """Generate human-readable explanations for each evaluated criterion."""
        explanations: Dict[str, str] = {}

        if not self.gemini.is_configured():
            for f in findings:
                obs = f.observed_value or {}
                explanations[f.requirement_id] = (
                    f"{f.reason} {obs.get('comparison_evaluation', '')} Next Step: {obs.get('recommended_action', '')}".strip()
                )
            return explanations

        # Index evidence by filename or requirement
        evidence_snippets = []
        for e in evidence[:15]:
            evidence_snippets.append(f"[{e.source_type} - {e.source_filename} p.{e.page_number}]: \"{e.excerpt.strip()}\"")
        evidence_text = "\n".join(evidence_snippets)

        for f in findings:
            req = f.required_value or {}
            obs = f.observed_value or {}

            # Specific evidence attached to this finding if any
            finding_cits = getattr(f, "evidence_citations", [])
            f_evidence_text = "\n".join(
                f"[{c.source_type} - {c.source_filename} p.{c.page_number}]: \"{c.excerpt.strip()}\""
                for c in finding_cits[:3]
            ) if finding_cits else evidence_text[:600]

            prompt = f"""
Requirement Title: {req.get('title', f.requirement_description)}
Category: {req.get('category', f.rule_type)}
Authoritative Deterministic Status: {f.status} (Mandatory: {f.is_mandatory})
Rule Decision Rationale: {f.reason}
Tender Condition: {req.get('specific_condition', str(req))}
Observed Company Facts: {obs.get('applicable_company_info', str(obs))}
Company Evidence: {obs.get('company_evidence', 'None')}
Comparison Evaluation: {obs.get('comparison_evaluation', '')}
Evidence Gap: {obs.get('evidence_gap', '')}
Recommended Next Step: {obs.get('recommended_action', '')}

Supporting Document Excerpts:
{f_evidence_text if f_evidence_text else "None verified"}

Task: Provide a concise (2-3 sentences), evidence-grounded explanation for the MSME bidder.
Explain exactly why this requirement passes, fails, lacks evidence, or needs review, citing the verified document/page where available, and stating the clear next action.
"""
            try:
                explanation = self.gemini.generate_text(prompt=prompt, system_instruction=SYSTEM_PROMPT)
                if explanation and len(explanation.strip()) > 10:
                    explanations[f.requirement_id] = explanation.strip()
                else:
                    explanations[f.requirement_id] = f"{f.reason} {obs.get('recommended_action', '')}".strip()
            except Exception as e:
                logger.warning(f"Failed to generate explanation for {f.requirement_id}: {e}")
                explanations[f.requirement_id] = f"{f.reason} {obs.get('recommended_action', '')}".strip()

        return explanations

    def synthesize_executive_summary(
        self,
        overall_status: str,
        findings: List[RuleFinding],
        evidence: List[EvidenceCitation],
    ) -> str:
        """Synthesize overall executive summary with actionable recommendations."""
        failing = [f for f in findings if f.status == "FAIL"]
        missing = [f for f in findings if f.status == "MISSING_EVIDENCE"]
        passed = [f for f in findings if f.status == "PASS"]
        review = [f for f in findings if f.status == "NEEDS_REVIEW"]

        if not self.gemini.is_configured():
            if overall_status == "ANALYSIS_BLOCKED_NO_DOCUMENTS":
                return "Full compliance analysis is unavailable because no usable tender documents have been indexed. Upload or process the tender documents to evaluate the actual eligibility conditions."
            elif overall_status == "NOT_ELIGIBLE":
                return (
                    f"Overall Assessment: DOES NOT MEET MANDATORY REQUIREMENTS. The company fails {len(failing)} mandatory "
                    f"condition(s): {', '.join(f.requirement_description for f in failing)}. Immediate remediation or alternative bidding structure required."
                )
            elif overall_status == "PARTIALLY_ELIGIBLE":
                return (
                    f"Overall Assessment: INCOMPLETE — EVIDENCE REQUIRED. {len(passed)} evaluated criteria pass, but {len(missing)} "
                    f"mandatory document proof(s) are missing from the vault: {', '.join(f.requirement_description for f in missing)}. Uploading these documents will complete compliance."
                )
            elif overall_status == "ELIGIBLE":
                return (
                    f"Overall Assessment: MEETS CHECKED REQUIREMENTS. Verified compliance across all {len(passed)} mandatory requirements. "
                    f"All checked parameters are backed by evidence in your company profile and document vault."
                )
            else:
                return (
                    f"Overall Assessment: REVIEW REQUIRED. {len(review)} requirement(s) require technical or administrative review: "
                    f"{', '.join(f.requirement_description for f in review)}."
                )

        prompt = f"""
Synthesize an executive summary for an MSME tender compliance assessment:
Overall Eligibility Status: {overall_status}
Total Evaluated Requirements: {len(findings)}
Passed Requirements ({len(passed)}): {[p.requirement_description for p in passed[:5]]}
Failing Requirements ({len(failing)}): {[f.requirement_description for f in failing[:5]]}
Missing Evidence Documents ({len(missing)}): {[m.requirement_description for m in missing[:5]]}
Needs Review Items ({len(review)}): {[r.requirement_description for r in review[:5]]}

Provide:
1. Executive summary explaining the overall outcome and its basis.
2. The key compliance strengths and critical gaps.
3. The immediate prioritized actions before bid submission.
Keep within 4 sentences, professional and actionable.
"""
        try:
            summary = self.gemini.generate_text(prompt=prompt, system_instruction=SYSTEM_PROMPT)
            if summary and len(summary.strip()) > 10:
                return summary.strip()
            return f"Overall Assessment: {overall_status}. Evaluation completed across {len(findings)} criteria."
        except Exception as e:
            logger.warning(f"Failed to synthesize executive summary: {e}")
            return f"Overall Assessment: {overall_status}. Evaluation completed across {len(findings)} criteria."


_compliance_analyzer = ComplianceAnalyzer()


def get_compliance_analyzer() -> ComplianceAnalyzer:
    return _compliance_analyzer
