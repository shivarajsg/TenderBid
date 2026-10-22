import hashlib
import json
import logging
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from langgraph.graph import StateGraph, START, END
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.company import Company
from app.models.compliance_finding import ComplianceFinding
from app.models.compliance_report import ComplianceReport
from app.models.document import Document
from app.models.tender import Tender
from app.schemas.evidence import EvidenceCitation
from app.services.ai.compliance_analyzer import ComplianceAnalyzer, get_compliance_analyzer
from app.services.compliance.reconciliation_guard import ReconciliationGuard
from app.services.compliance.report_builder import ReportBuilder
from app.services.compliance.requirement_normalizer import RequirementNormalizer
from app.services.compliance.rule_engine import DeterministicRuleEngine, RuleFinding, get_rule_engine
from app.services.retrieval.citation_validator import CitationValidator
from app.services.retrieval.hybrid_retriever import HybridRetriever
from app.services.workflows.compliance_state import ComplianceState

logger = logging.getLogger(__name__)
settings = get_settings()


def _make_json_safe(val: Any) -> Any:
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, dict):
        return {k: _make_json_safe(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_make_json_safe(x) for x in val]
    return val


class ComplianceWorkflowOrchestrator:
    """Coordinates the LangGraph compliance workflow with database persistence, hybrid RAG, and security guards."""

    def __init__(
        self,
        session: AsyncSession,
        rule_engine: Optional[DeterministicRuleEngine] = None,
        analyzer: Optional[ComplianceAnalyzer] = None,
        hybrid_retriever: Optional[HybridRetriever] = None,
        citation_validator: Optional[CitationValidator] = None,
    ):
        self.session = session
        self.rule_engine = rule_engine or get_rule_engine()
        self.analyzer = analyzer or get_compliance_analyzer()
        self.retriever = hybrid_retriever or HybridRetriever(session)
        self.validator = citation_validator or CitationValidator(session)
        self.graph = self._build_graph()

    def _build_graph(self):
        """Construct the compiled LangGraph compliance workflow."""
        builder = StateGraph(ComplianceState)

        builder.add_node("input_validation", self._node_input_validation)
        builder.add_node("load_context", self._node_load_context)
        builder.add_node("validate_requirements", self._node_validate_requirements)
        builder.add_node("deterministic_checks", self._node_deterministic_checks)
        builder.add_node("hybrid_retrieval", self._node_hybrid_retrieval)
        builder.add_node("evidence_analysis", self._node_evidence_analysis)
        builder.add_node("reconciliation_guard", self._node_reconciliation_guard)
        builder.add_node("report_synthesis", self._node_report_synthesis)
        builder.add_node("persist_report", self._node_persist_report)

        builder.add_edge(START, "input_validation")
        builder.add_edge("input_validation", "load_context")
        builder.add_edge("load_context", "validate_requirements")
        builder.add_edge("validate_requirements", "deterministic_checks")
        builder.add_edge("deterministic_checks", "hybrid_retrieval")
        builder.add_edge("hybrid_retrieval", "evidence_analysis")
        builder.add_edge("evidence_analysis", "reconciliation_guard")
        builder.add_edge("reconciliation_guard", "report_synthesis")
        builder.add_edge("report_synthesis", "persist_report")
        builder.add_edge("persist_report", END)

        return builder.compile()

    # =========================================================================
    # Workflow Node Implementations
    # =========================================================================

    async def _node_input_validation(self, state: ComplianceState) -> Dict[str, Any]:
        """Node 1: Validate input parameters and basic authorization preconditions."""
        errors = list(state.get("errors", []))
        if not state.get("tender_id"):
            errors.append("Tender ID is required.")
        if not state.get("company_id"):
            errors.append("Company ID is required.")
        return {"errors": errors}

    async def _node_load_context(self, state: ComplianceState) -> Dict[str, Any]:
        """Node 2: Load authoritative database records for tender, company, attached tender docs, and vault documents."""
        tender_id = state["tender_id"]
        company_id = state["company_id"]
        errors = list(state.get("errors", []))
        limitations: List[str] = []

        # 1. Fetch Tender
        t_stmt = select(Tender).where(Tender.id == tender_id)
        t_res = await self.session.execute(t_stmt)
        tender = t_res.scalar_one_or_none()

        if not tender:
            errors.append(f"Tender {tender_id} not found.")
            return {"errors": errors}

        # 2. Fetch Company
        c_stmt = select(Company).where(Company.id == company_id)
        c_res = await self.session.execute(c_stmt)
        company = c_res.scalar_one_or_none()

        if not company:
            errors.append(f"Company {company_id} not found.")
            return {"errors": errors}

        # 3. Fetch Company Documents from Vault
        d_stmt = select(Document).where(Document.company_id == company_id)
        d_res = await self.session.execute(d_stmt)
        vault_docs = list(d_res.scalars().all())

        # 4. Fetch Attached Tender Documents
        td_stmt = select(Document).where(Document.tender_id == tender_id)
        td_res = await self.session.execute(td_stmt)
        tender_docs = list(td_res.scalars().all())

        indexed_tender_docs = [d for d in tender_docs if d.processing_status == "INDEXED"]
        has_usable_tender_docs = len(indexed_tender_docs) > 0

        # Section 3: Handle 0 files indexed or partial documents explicitly
        if not has_usable_tender_docs:
            limitations.append(
                "Full compliance analysis is unavailable because no usable tender documents have been indexed. "
                "Upload or process the tender documents to evaluate the actual eligibility conditions."
            )
            doc_coverage = {
                "total_documents": len(tender_docs),
                "indexed_documents": 0,
                "coverage_status": "UNAVAILABLE",
                "summary": "No usable tender documents have been indexed.",
            }
        elif len(indexed_tender_docs) < len(tender_docs):
            limitations.append(
                f"Partial tender document coverage: {len(indexed_tender_docs)} of {len(tender_docs)} documents indexed. "
                f"Some tender specifications could not be verified from documents."
            )
            doc_coverage = {
                "total_documents": len(tender_docs),
                "indexed_documents": len(indexed_tender_docs),
                "coverage_status": "PARTIAL",
                "summary": f"{len(indexed_tender_docs)} of {len(tender_docs)} files indexed.",
            }
        else:
            doc_coverage = {
                "total_documents": len(tender_docs),
                "indexed_documents": len(indexed_tender_docs),
                "coverage_status": "FULL",
                "summary": f"All {len(tender_docs)} tender documents indexed and available for retrieval.",
            }

        # Compute stable snapshot hashes
        t_raw = f"{tender.id}_{tender.updated_at}_{tender.structured_requirements}"
        c_raw = f"{company.id}_{company.updated_at}_{len(vault_docs)}"
        t_hash = hashlib.sha256(t_raw.encode("utf-8")).hexdigest()
        c_hash = hashlib.sha256(c_raw.encode("utf-8")).hexdigest()

        company_dict = {
            "id": company.id,
            "legal_name": company.legal_name,
            "registration_number": company.registration_number,
            "business_type": company.business_type,
            "sector": company.sector,
            "annual_turnover": company.annual_turnover,
            "work_experience": company.work_experience,
            "certifications": company.certifications,
            "incorporation_date": company.incorporation_date,
        }

        tender_dict = {
            "id": tender.id,
            "tender_reference": tender.tender_reference,
            "title": tender.title,
            "issuing_authority": tender.issuing_authority,
            "sector": tender.sector,
            "estimated_budget_inr": tender.estimated_budget_inr,
            "emd_amount_inr": tender.emd_amount_inr,
            "msme_emd_exemption": tender.msme_emd_exemption,
            "submission_deadline": tender.submission_deadline,
            "structured_requirements": tender.structured_requirements,
        }

        return {
            "tender_data": tender_dict,
            "company_data": company_dict,
            "tender_version_hash": t_hash,
            "company_version_hash": c_hash,
            "vault_documents_count": len(vault_docs),
            "vault_documents": vault_docs,
            "tender_documents_count": len(tender_docs),
            "tender_indexed_documents_count": len(indexed_tender_docs),
            "tender_documents": tender_docs,
            "has_usable_tender_documents": has_usable_tender_docs,
            "document_coverage": doc_coverage,
            "limitations": limitations,
            "errors": errors,
        }

    async def _node_validate_requirements(self, state: ComplianceState) -> Dict[str, Any]:
        """Node 3: Normalize structured tender criteria across all categories into typed schemas."""
        tender_data = state.get("tender_data", {})
        structured = tender_data.get("structured_requirements") if tender_data else {}
        deadline = tender_data.get("submission_deadline") if tender_data else None
        emd_amt = tender_data.get("emd_amount_inr") if tender_data else None
        msme_ex = tender_data.get("msme_emd_exemption", True) if tender_data else True

        normalized = None
        try:
            normalized = RequirementNormalizer.normalize(
                raw_dict=structured,
                tender_deadline=deadline,
                tender_emd_inr=emd_amt,
                msme_emd_exemption=msme_ex,
            )
        except Exception as e:
            logger.warning(f"Requirement normalization notice: {e}")

        return {"normalized_requirements": normalized}

    async def _node_deterministic_checks(self, state: ComplianceState) -> Dict[str, Any]:
        """Node 4: Execute pure Python business rules against company records."""
        reqs = state.get("normalized_requirements")
        comp = state.get("company_data", {})
        docs = state.get("vault_documents", [])
        has_usable = state.get("has_usable_tender_documents", True)

        findings: List[RuleFinding] = []
        if reqs:
            findings = self.rule_engine.evaluate_all(
                requirements=reqs,
                company_profile=comp,
                vault_documents=docs,
            )

        # If tender has NO usable documents and no structured criteria were found:
        if not has_usable and not findings:
            findings.append(
                RuleFinding(
                    requirement_id="CRIT_BLOCKED_01",
                    rule_type="OTHER",
                    requirement_description="Tender Document Indexing & Extraction Status",
                    required_value={
                        "title": "Usable Tender Documents Required",
                        "category": "ELIGIBILITY",
                        "original_clause": "Tender notices and eligibility specifications must be indexed.",
                        "tender_source": "Platform Document Repository",
                        "plain_english_interpretation": "Evaluation cannot proceed because no tender documents have been processed.",
                        "specific_condition": ">= 1 indexed tender document",
                        "needs_human_review": True,
                    },
                    observed_value={
                        "applicable_company_info": f"Company: {comp.get('legal_name', 'MSME')}.",
                        "company_evidence": "None (No tender documents available to evaluate against)",
                        "comparison_evaluation": "0 usable tender documents indexed.",
                        "evidence_gap": "No usable tender documents have been indexed for this procurement notice.",
                        "risk_and_consequence": "Inability to verify tender eligibility conditions.",
                        "recommended_action": "Upload or process the tender RFP documents on the Tender Details screen.",
                    },
                    status="NEEDS_REVIEW",
                    is_mandatory=True,
                    reason="Full compliance analysis is unavailable because no usable tender documents have been indexed.",
                )
            )

        return {
            "deterministic_findings": findings,
            "deterministic_analysis_status": "SUCCESS",
        }

    async def _node_hybrid_retrieval(self, state: ComplianceState) -> Dict[str, Any]:
        """Node 5: Execute requirement-specific hybrid lexical & semantic retrieval for supporting evidence."""
        tender_id = state["tender_id"]
        company_id = state["company_id"]
        findings = state.get("deterministic_findings", [])
        has_usable = state.get("has_usable_tender_documents", True)

        all_citations: List[EvidenceCitation] = []
        retrieval_status = "SUCCESS"

        try:
            for finding in findings:
                req = finding.required_value or {}
                # Build targeted search query for each specific requirement
                q_terms = [finding.requirement_description]
                if req.get("title"):
                    q_terms.append(req["title"])
                if req.get("specific_condition"):
                    q_terms.append(str(req["specific_condition"]))

                target_query = " ".join(q_terms)

                # 1. Retrieve tender evidence if tender docs are indexed
                f_citations: List[EvidenceCitation] = []
                if has_usable:
                    t_cits = await self.retriever.search(query=target_query, tender_id=tender_id, limit=2)
                    f_citations.extend(t_cits)

                # 2. Retrieve authorized company evidence
                c_cits = await self.retriever.search(query=target_query, company_id=company_id, limit=2)
                f_citations.extend(c_cits)

                # 3. Validate citations against authorization scope and page bounds
                valid_cits, _ = await self.validator.validate_citations(
                    f_citations, authorized_tender_id=tender_id, authorized_company_id=company_id
                )

                # Attach validated citations directly to this finding
                finding.evidence_citations = valid_cits
                all_citations.extend(valid_cits)

        except Exception as e:
            logger.warning(f"Hybrid retrieval encountered notice: {e}")
            retrieval_status = "PARTIAL"

        return {
            "retrieved_evidence": all_citations,
            "retrieval_status": retrieval_status,
        }

    async def _node_evidence_analysis(self, state: ComplianceState) -> Dict[str, Any]:
        """Node 6: Use Gemini to explain findings with evidence grounding without mutating rule outcomes."""
        findings = state.get("deterministic_findings", [])
        evidence = state.get("retrieved_evidence", [])
        include_ai = state.get("include_ai_explanation", True)

        explanations: Dict[str, str] = {}
        ai_status = "COMPLETED"

        if include_ai and findings:
            try:
                explanations = self.analyzer.explain_findings(findings, evidence)
            except Exception as e:
                logger.warning(f"AI explanation generator fallback: {e}")
                ai_status = "FALLBACK"
                for f in findings:
                    obs = f.observed_value or {}
                    explanations[f.requirement_id] = f"{f.reason} Next step: {obs.get('recommended_action', '')}".strip()
        else:
            ai_status = "DISABLED" if not include_ai else "FALLBACK"
            for f in findings:
                obs = f.observed_value or {}
                explanations[f.requirement_id] = f"{f.reason} Next step: {obs.get('recommended_action', '')}".strip()

        return {
            "ai_explanations": explanations,
            "ai_analysis_status": ai_status,
        }

    async def _node_reconciliation_guard(self, state: ComplianceState) -> Dict[str, Any]:
        """Node 7: Ensure AI output strictly respects deterministic checks and never overrides rule outcomes."""
        findings = state.get("deterministic_findings", [])
        ai_exps = state.get("ai_explanations", {})
        evidence = state.get("retrieved_evidence", [])

        reconciled, alerts = ReconciliationGuard.reconcile(
            deterministic_findings=findings,
            ai_explanations=ai_exps,
            retrieved_evidence=evidence,
        )

        return {
            "reconciled_findings": reconciled,
            "reconciliation_alerts": alerts,
        }

    async def _node_report_synthesis(self, state: ComplianceState) -> Dict[str, Any]:
        """Node 8: Synthesize overall status, executive summary, checklist, action plan, and comparisons."""
        findings = state.get("reconciled_findings", [])
        evidence = state.get("retrieved_evidence", [])
        has_usable = state.get("has_usable_tender_documents", True)

        overall_status, overall_score, summary = ReportBuilder.derive_overall_status(
            findings=findings,
            has_usable_tender_documents=has_usable,
        )

        # Build structured components
        missing_docs = ReportBuilder.build_missing_documents_checklist(findings)
        priority_actions = ReportBuilder.build_priority_actions(findings, overall_status)
        tech_fin_comparisons = ReportBuilder.build_technical_financial_comparisons(findings)
        risks = ReportBuilder.build_compliance_risks(findings)

        # Enhance summary with AI executive recommendations if enabled and tender documents exist
        if state.get("include_ai_explanation", True) and has_usable and findings:
            try:
                ai_summary = self.analyzer.synthesize_executive_summary(overall_status, findings, evidence)
                if ai_summary and len(ai_summary.strip()) > 10:
                    summary = f"{summary}\n\nExecutive Intelligence Recommendations:\n{ai_summary}"
            except Exception as e:
                logger.warning(f"AI executive summary fallback: {e}")

        # Unique source references
        src_refs: List[Dict[str, Any]] = []
        seen_refs = set()
        for e in evidence:
            key = f"{e.source_filename}_{e.page_number}"
            if key not in seen_refs:
                seen_refs.add(key)
                src_refs.append({
                    "source_type": e.source_type,
                    "document_id": str(e.document_id),
                    "filename": e.source_filename,
                    "page_number": e.page_number,
                    "retrieval_method": e.retrieval_method,
                    "relevance_score": e.relevance_score,
                })

        return {
            "overall_status": overall_status,
            "overall_score": overall_score,
            "summary": summary,
            "missing_documents": missing_docs,
            "priority_actions": priority_actions,
            "technical_financial_comparisons": tech_fin_comparisons,
            "compliance_risks": risks,
            "source_references": src_refs,
        }

    async def _node_persist_report(self, state: ComplianceState) -> Dict[str, Any]:
        """Node 9: Store versioned compliance report and individual findings in PostgreSQL."""
        tender_id = state["tender_id"]
        company_id = state["company_id"]
        user_id = state.get("user_id")
        overall_status = state.get("overall_status", "NEEDS_REVIEW")
        overall_score = state.get("overall_score", Decimal("0.00"))
        summary = state.get("summary", "")
        t_hash = state.get("tender_version_hash", "")
        c_hash = state.get("company_version_hash", "")
        findings = state.get("reconciled_findings", [])
        ai_exps = state.get("ai_explanations", {})

        report_id = uuid.uuid4()
        processing_metadata = {
            "retrieval_status": state.get("retrieval_status", "SUCCESS"),
            "reconciliation_alerts": state.get("reconciliation_alerts", []),
            "evidence_citations_count": len(state.get("retrieved_evidence", [])),
            "document_coverage": state.get("document_coverage", {}),
            "analysis_completeness": "BLOCKED" if overall_status == "ANALYSIS_BLOCKED_NO_DOCUMENTS" else "COMPLETE",
            "requirements_identified": len(findings),
            "requirements_evaluated": len(findings),
            "status_counts": {
                "pass": sum(1 for f in findings if f.status == "PASS"),
                "fail": sum(1 for f in findings if f.status == "FAIL"),
                "missing_evidence": sum(1 for f in findings if f.status == "MISSING_EVIDENCE"),
                "needs_review": sum(1 for f in findings if f.status == "NEEDS_REVIEW"),
                "not_applicable": sum(1 for f in findings if f.status == "NOT_APPLICABLE"),
            },
            "executive_summary": summary,
            "critical_findings": [
                {
                    "requirement_id": f.requirement_id,
                    "title": f.requirement_description,
                    "status": f.status,
                    "reason": f.reason,
                    "action": f.observed_value.get("recommended_action", ""),
                }
                for f in findings
                if f.status in ["FAIL", "MISSING_EVIDENCE"]
            ],
            "missing_documents": state.get("missing_documents", []),
            "priority_actions": state.get("priority_actions", []),
            "technical_financial_comparisons": state.get("technical_financial_comparisons", []),
            "risks": state.get("compliance_risks", []),
            "source_references": state.get("source_references", []),
            "deterministic_analysis_status": state.get("deterministic_analysis_status", "SUCCESS"),
            "ai_analysis_status": state.get("ai_analysis_status", "COMPLETED"),
            "limitations": state.get("limitations", []),
        }

        report = ComplianceReport(
            id=report_id,
            tender_id=tender_id,
            company_id=company_id,
            generated_by=user_id,
            overall_status=overall_status,
            overall_score=overall_score,
            summary=summary,
            rule_engine_version=settings.RULE_ENGINE_VERSION,
            tender_version_hash=t_hash,
            company_version_hash=c_hash,
            processing_metadata=_make_json_safe(processing_metadata),
        )
        self.session.add(report)

        # Persist individual findings with 17 fields in required_value and observed_value
        for f in findings:
            cits_data = [c.model_dump(mode="json") for c in f.evidence_citations]
            finding_row = ComplianceFinding(
                id=uuid.uuid4(),
                report_id=report_id,
                requirement_id=f.requirement_id,
                rule_type=f.rule_type,
                requirement_description=f.requirement_description,
                required_value=_make_json_safe(f.required_value),
                observed_value=_make_json_safe(f.observed_value),
                status=f.status,
                is_mandatory=f.is_mandatory,
                reason=f.reason,
                ai_explanation=ai_exps.get(f.requirement_id),
                evidence_citations=cits_data,
            )
            self.session.add(finding_row)

        await self.session.commit()
        await self.session.refresh(report)

        return {"report_id": report_id}

    async def execute(
        self,
        tender_id: uuid.UUID,
        company_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        include_ai_explanation: bool = True,
    ) -> ComplianceState:
        """Run the end-to-end compiled compliance graph asynchronously."""
        initial_state: ComplianceState = {
            "tender_id": tender_id,
            "company_id": company_id,
            "user_id": user_id,
            "include_ai_explanation": include_ai_explanation,
            "errors": [],
            "warnings": [],
            "limitations": [],
            "retrieved_evidence": [],
            "deterministic_findings": [],
            "ai_explanations": {},
            "reconciled_findings": [],
            "reconciliation_alerts": [],
            "missing_documents": [],
            "priority_actions": [],
            "technical_financial_comparisons": [],
            "compliance_risks": [],
            "source_references": [],
        }

        result = await self.graph.ainvoke(initial_state)
        return result
