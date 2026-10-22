import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.evidence import EvidenceCitation


class ComplianceAnalyzeRequest(BaseModel):
    """Payload to trigger compliance evaluation for an authorized tender."""
    tender_id: uuid.UUID = Field(..., description="UUID of the tender notice to evaluate")
    include_ai_explanation: bool = Field(default=True, description="Whether to invoke Gemini for natural language explanation")


class ComplianceFindingResponse(BaseModel):
    """Structured compliance finding for a single requirement with 17 detailed fields."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    requirement_id: str
    rule_type: str
    requirement_description: str
    required_value: Optional[Dict[str, Any]] = None
    observed_value: Optional[Dict[str, Any]] = None
    status: str  # PASS, FAIL, MISSING_EVIDENCE, NEEDS_REVIEW, NOT_APPLICABLE
    is_mandatory: bool
    reason: str
    ai_explanation: Optional[str] = None
    evidence_citations: Optional[List[EvidenceCitation]] = None
    created_at: datetime

    # Section 6: Requirement-by-requirement detailed fields
    category: Optional[str] = None
    title: Optional[str] = None
    original_clause: Optional[str] = None
    tender_source: Optional[str] = None
    plain_english_interpretation: Optional[str] = None
    specific_condition: Optional[str] = None
    applicable_company_info: Optional[str] = None
    company_evidence: Optional[str] = None
    comparison_evaluation: Optional[str] = None
    evidence_gap: Optional[str] = None
    risk_and_consequence: Optional[str] = None
    recommended_action: Optional[str] = None
    needs_human_review: bool = False

    @model_validator(mode="after")
    def populate_detailed_fields(self) -> "ComplianceFindingResponse":
        req = self.required_value or {}
        obs = self.observed_value or {}

        if not self.category:
            self.category = req.get("category") or self.rule_type
        if not self.title:
            self.title = req.get("title") or self.requirement_description
        if not self.original_clause:
            self.original_clause = req.get("original_clause") or req.get("clause_text") or self.requirement_description
        if not self.tender_source:
            self.tender_source = req.get("tender_source") or "Tender Notice Document"
        if not self.plain_english_interpretation:
            self.plain_english_interpretation = req.get("plain_english_interpretation") or self.reason
        if not self.specific_condition:
            self.specific_condition = req.get("specific_condition") or str(req)
        if not self.applicable_company_info:
            self.applicable_company_info = obs.get("applicable_company_info") or "Company Profile Record"
        if not self.company_evidence:
            self.company_evidence = obs.get("company_evidence") or (f"Vault: {obs.get('filename')}" if obs.get("filename") else "None")
        if not self.comparison_evaluation:
            self.comparison_evaluation = obs.get("comparison_evaluation") or self.reason
        if not self.evidence_gap:
            self.evidence_gap = obs.get("evidence_gap") or ("None" if self.status == "PASS" else "Supporting documentation unverified.")
        if not self.risk_and_consequence:
            self.risk_and_consequence = obs.get("risk_and_consequence") or ("No risk" if self.status == "PASS" else "Risk of bid rejection during evaluation.")
        if not self.recommended_action:
            self.recommended_action = obs.get("recommended_action") or ("Maintain verified records." if self.status == "PASS" else "Upload missing verification document.")
        if "needs_human_review" in req:
            self.needs_human_review = bool(req["needs_human_review"])
        elif self.status == "NEEDS_REVIEW":
            self.needs_human_review = True

        return self


class ComplianceReportResponse(BaseModel):
    """Full versioned compliance report output with comprehensive metadata."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tender_id: uuid.UUID
    company_id: uuid.UUID
    overall_status: str  # ELIGIBLE, NOT_ELIGIBLE, PARTIALLY_ELIGIBLE, NEEDS_REVIEW, ANALYSIS_BLOCKED_NO_DOCUMENTS
    overall_score: Optional[Decimal] = None
    summary: Optional[str] = None
    rule_engine_version: str
    tender_version_hash: str
    company_version_hash: str
    processing_metadata: Optional[Dict[str, Any]] = None
    findings: List[ComplianceFindingResponse] = []

    # Section 10: Structured Top-Level Attributes
    analysis_completeness: str = "COMPLETE"
    document_coverage: Optional[Dict[str, Any]] = None
    requirements_identified: int = 0
    requirements_evaluated: int = 0
    status_counts: Optional[Dict[str, int]] = None
    executive_summary: Optional[str] = None
    critical_findings: Optional[List[Dict[str, Any]]] = None
    missing_documents: Optional[List[Dict[str, Any]]] = None
    priority_actions: Optional[List[Dict[str, Any]]] = None
    risks: Optional[List[Dict[str, Any]]] = None
    source_references: Optional[List[Dict[str, Any]]] = None
    technical_financial_comparisons: Optional[List[Dict[str, Any]]] = None
    deterministic_analysis_status: str = "SUCCESS"
    ai_analysis_status: str = "COMPLETED"
    limitations: Optional[List[str]] = None

    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def populate_metadata_views(self) -> "ComplianceReportResponse":
        meta = self.processing_metadata or {}

        if "document_coverage" in meta and not self.document_coverage:
            self.document_coverage = meta["document_coverage"]
        if "analysis_completeness" in meta:
            self.analysis_completeness = meta["analysis_completeness"]
        if "status_counts" in meta and not self.status_counts:
            self.status_counts = meta["status_counts"]
        if "critical_findings" in meta and not self.critical_findings:
            self.critical_findings = meta["critical_findings"]
        if "missing_documents" in meta and not self.missing_documents:
            self.missing_documents = meta["missing_documents"]
        if "priority_actions" in meta and not self.priority_actions:
            self.priority_actions = meta["priority_actions"]
        if "risks" in meta and not self.risks:
            self.risks = meta["risks"]
        if "source_references" in meta and not self.source_references:
            self.source_references = meta["source_references"]
        if "technical_financial_comparisons" in meta and not self.technical_financial_comparisons:
            self.technical_financial_comparisons = meta["technical_financial_comparisons"]
        if "limitations" in meta and not self.limitations:
            self.limitations = meta["limitations"]
        if "deterministic_analysis_status" in meta:
            self.deterministic_analysis_status = meta["deterministic_analysis_status"]
        if "ai_analysis_status" in meta:
            self.ai_analysis_status = meta["ai_analysis_status"]

        if not self.executive_summary:
            self.executive_summary = meta.get("executive_summary") or self.summary

        if self.findings:
            self.requirements_evaluated = len(self.findings)
            self.requirements_identified = meta.get("requirements_identified", len(self.findings))

            if not self.status_counts:
                self.status_counts = {
                    "pass": sum(1 for f in self.findings if f.status == "PASS"),
                    "fail": sum(1 for f in self.findings if f.status == "FAIL"),
                    "missing_evidence": sum(1 for f in self.findings if f.status == "MISSING_EVIDENCE"),
                    "needs_review": sum(1 for f in self.findings if f.status == "NEEDS_REVIEW"),
                    "not_applicable": sum(1 for f in self.findings if f.status == "NOT_APPLICABLE"),
                }

        return self


class ComplianceReportListResponse(BaseModel):
    """Paginated collection of historical compliance reports."""
    items: List[ComplianceReportResponse]
    total: int
    skip: int
    limit: int
