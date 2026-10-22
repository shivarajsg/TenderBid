import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional, TypedDict

from app.schemas.evidence import EvidenceCitation
from app.schemas.requirements import NormalizedTenderRequirements
from app.services.compliance.rule_engine import RuleFinding


class ComplianceState(TypedDict, total=False):
    """Strongly typed state schema tracking data flow across LangGraph compliance nodes."""

    # Context & Identifiers
    tender_id: uuid.UUID
    company_id: uuid.UUID
    user_id: Optional[uuid.UUID]
    include_ai_explanation: bool

    # Domain Data & Snapshots
    tender_data: Optional[Dict[str, Any]]
    company_data: Optional[Dict[str, Any]]
    tender_version_hash: str
    company_version_hash: str
    vault_documents_count: int
    vault_documents: List[Any]
    tender_documents_count: int
    tender_indexed_documents_count: int
    tender_documents: List[Any]
    has_usable_tender_documents: bool

    # Scope, Coverage & Limitations
    document_coverage: Dict[str, Any]
    limitations: List[str]

    # Requirements & Rules
    normalized_requirements: Optional[NormalizedTenderRequirements]
    deterministic_findings: List[RuleFinding]

    # Retrieval & Evidence
    retrieved_evidence: List[EvidenceCitation]
    retrieval_status: str  # "SUCCESS", "PARTIAL", "FAILED"

    # AI & Reconciliation
    ai_explanations: Dict[str, str]
    reconciled_findings: List[RuleFinding]
    reconciliation_alerts: List[str]

    # Structured Dashboard Metadata
    missing_documents: List[Dict[str, Any]]
    priority_actions: List[Dict[str, Any]]
    technical_financial_comparisons: List[Dict[str, Any]]
    compliance_risks: List[Dict[str, Any]]
    source_references: List[Dict[str, Any]]
    deterministic_analysis_status: str
    ai_analysis_status: str

    # Final Synthesis & Persistence
    overall_status: str  # ELIGIBLE, NOT_ELIGIBLE, PARTIALLY_ELIGIBLE, NEEDS_REVIEW, ANALYSIS_BLOCKED_NO_DOCUMENTS
    overall_score: Decimal
    summary: str
    report_id: Optional[uuid.UUID]

    # Diagnostic Traces
    errors: List[str]
    warnings: List[str]
