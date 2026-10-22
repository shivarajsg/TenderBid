import logging
from typing import Any, Dict, List, Set, Tuple

from app.schemas.evidence import EvidenceCitation
from app.services.compliance.rule_engine import RuleFinding

logger = logging.getLogger(__name__)


class ReconciliationGuard:
    """
    Enforces the core non-negotiable architectural boundary:
    Python deterministic rules cannot be overridden by AI / LLM synthesis.
    """

    @staticmethod
    def reconcile(
        deterministic_findings: List[RuleFinding],
        ai_explanations: Dict[str, str],
        retrieved_evidence: List[EvidenceCitation],
    ) -> Tuple[List[RuleFinding], List[str]]:
        """
        Reconcile AI outputs with deterministic findings.
        Returns: (reconciled_findings, guard_alerts)
        """
        reconciled: List[RuleFinding] = []
        alerts: List[str] = []

        # Build index of valid evidence citations by evidence_id and chunk_id
        valid_evidence_ids: Set[str] = {e.evidence_id for e in retrieved_evidence}
        valid_chunk_ids: Set[str] = {e.chunk_id for e in retrieved_evidence if e.chunk_id}

        for finding in deterministic_findings:
            req_id = finding.requirement_id
            ai_text = ai_explanations.get(req_id, "")

            # Check if AI attempted to assert a pass on a mandatory failure
            if finding.status == "FAIL" and finding.is_mandatory:
                # Check for illicit override attempts in AI text
                lower_text = ai_text.lower()
                if "status: pass" in lower_text or "eligible" in lower_text and "not eligible" not in lower_text:
                    alert = f"Reconciliation Alert: AI proposed PASS for mandatory failing criterion {req_id}. Deterministic FAIL preserved."
                    alerts.append(alert)
                    logger.warning(alert)

            # Filter evidence citations to ensure no hallucinated/unverified sources
            validated_citations = []
            for cit in finding.evidence_citations:
                if cit.evidence_id in valid_evidence_ids or (cit.chunk_id and cit.chunk_id in valid_chunk_ids):
                    validated_citations.append(cit)
                else:
                    alerts.append(f"Citation Guard: Dropped unverified citation '{cit.evidence_id}' for requirement {req_id}.")

            finding.evidence_citations = validated_citations
            reconciled.append(finding)

        return reconciled, alerts
