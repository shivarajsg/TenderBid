import logging
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.db.repositories.companies import CompanyRepository
from app.db.session import get_db
from app.models.compliance_finding import ComplianceFinding
from app.models.compliance_report import ComplianceReport
from app.models.document import Document
from app.models.tender import Tender
from app.models.user import User
from app.schemas.compliance import (
    ComplianceAnalyzeRequest,
    ComplianceFindingResponse,
    ComplianceReportListResponse,
    ComplianceReportResponse,
)
from app.services.workflows.compliance_graph import ComplianceWorkflowOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/compliance", tags=["Tender Compliance Intelligence"])


async def resolve_user_company_id(user: User, session: AsyncSession) -> uuid.UUID:
    """Helper resolving authenticated company ID or raising HTTP 403."""
    company_repo = CompanyRepository(session)
    company = await company_repo.get_by_owner_id(user.id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must create a registered company profile before running compliance analysis.",
        )
    return company.id


@router.post(
    "/analyze",
    response_model=ComplianceReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run deterministic and AI-powered compliance analysis on a tender",
)
async def analyze_tender_compliance(
    payload: ComplianceAnalyzeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Execute full LangGraph compliance intelligence pipeline:
    Python deterministic rule evaluation, hybrid evidence retrieval, 
    reconciliation guard enforcement, and optional Gemini analysis.
    """
    company_id = await resolve_user_company_id(current_user, session)

    # Invariant: Government portal tenders require at least one indexed tender document
    td_stmt = select(Document).where(
        Document.tender_id == payload.tender_id,
        Document.processing_status == "INDEXED",
    )
    td_res = await session.execute(td_stmt)
    indexed_tender_docs = list(td_res.scalars().all())

    t_stmt = select(Tender).where(Tender.id == payload.tender_id)
    t_res = await session.execute(t_stmt)
    target_tender = t_res.scalar_one_or_none()

    if target_tender and target_tender.source_portal in ("GEM", "CPPP", "APIFY", "TENDERKART") and not indexed_tender_docs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Compliance evaluation cannot be completed because no usable tender document "
                "has been downloaded and indexed for this bid. Retry document retrieval, "
                "open the official source, or upload the tender file manually."
            ),
        )

    orchestrator = ComplianceWorkflowOrchestrator(session)

    try:
        state = await orchestrator.execute(
            tender_id=payload.tender_id,
            company_id=company_id,
            user_id=current_user.id,
            include_ai_explanation=payload.include_ai_explanation,
        )

        if state.get("errors"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="; ".join(state["errors"]),
            )

        report_id = state.get("report_id")
        if not report_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Compliance analysis failed to generate a persisted report.",
            )

        # Fetch complete persisted report with eager findings
        stmt = (
            select(ComplianceReport)
            .options(selectinload(ComplianceReport.findings))
            .where(ComplianceReport.id == report_id)
        )
        res = await session.execute(stmt)
        report = res.scalar_one()

        return ComplianceReportResponse.model_validate(report)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Compliance analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Compliance evaluation error: {e}",
        )


@router.get(
    "/reports",
    response_model=ComplianceReportListResponse,
    summary="List historical compliance reports for authenticated company",
)
async def list_compliance_reports(
    tender_id: Optional[uuid.UUID] = Query(None, description="Filter by tender ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by overall status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve paginated historical compliance reports owned by the authenticated company."""
    company_id = await resolve_user_company_id(current_user, session)

    query = (
        select(ComplianceReport)
        .options(selectinload(ComplianceReport.findings))
        .where(ComplianceReport.company_id == company_id)
    )
    count_query = (
        select(func.count())
        .select_from(ComplianceReport)
        .where(ComplianceReport.company_id == company_id)
    )

    filters = []
    if tender_id:
        filters.append(ComplianceReport.tender_id == tender_id)
    if status_filter:
        filters.append(ComplianceReport.overall_status == status_filter)

    if filters:
        query = query.where(*filters)
        count_query = count_query.where(*filters)

    total_res = await session.execute(count_query)
    total = total_res.scalar_one()

    query = query.order_by(ComplianceReport.created_at.desc()).offset(skip).limit(limit)
    res = await session.execute(query)
    reports = list(res.scalars().all())

    return ComplianceReportListResponse(
        items=[ComplianceReportResponse.model_validate(r) for r in reports],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/reports/{report_id}",
    response_model=ComplianceReportResponse,
    summary="Get single compliance report with verified tenant isolation",
)
async def get_compliance_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Fetch compliance report verifying company ownership."""
    company_id = await resolve_user_company_id(current_user, session)

    stmt = (
        select(ComplianceReport)
        .options(selectinload(ComplianceReport.findings))
        .where(ComplianceReport.id == report_id, ComplianceReport.company_id == company_id)
    )
    res = await session.execute(stmt)
    report = res.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compliance report not found or unauthorized.",
        )

    return ComplianceReportResponse.model_validate(report)


@router.get(
    "/reports/{report_id}/findings",
    response_model=List[ComplianceFindingResponse],
    summary="List all criteria findings and citations for a report",
)
async def list_report_findings(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve detailed finding items for an authorized report."""
    company_id = await resolve_user_company_id(current_user, session)

    # Verify report ownership
    stmt = select(ComplianceReport.id).where(
        ComplianceReport.id == report_id, ComplianceReport.company_id == company_id
    )
    check_res = await session.execute(stmt)
    if not check_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compliance report not found or unauthorized.",
        )

    f_stmt = (
        select(ComplianceFinding)
        .where(ComplianceFinding.report_id == report_id)
        .order_by(ComplianceFinding.created_at.asc())
    )
    res = await session.execute(f_stmt)
    findings = list(res.scalars().all())

    return [ComplianceFindingResponse.model_validate(f) for f in findings]


@router.get(
    "/reports/{report_id}/findings/{finding_id}",
    response_model=ComplianceFindingResponse,
    summary="Inspect individual finding and attached evidence citations",
)
async def get_report_finding(
    report_id: uuid.UUID,
    finding_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Inspect single criterion finding with page-level citations."""
    company_id = await resolve_user_company_id(current_user, session)

    # Verify report ownership
    stmt = select(ComplianceReport.id).where(
        ComplianceReport.id == report_id, ComplianceReport.company_id == company_id
    )
    check_res = await session.execute(stmt)
    if not check_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compliance report not found or unauthorized.",
        )

    f_stmt = select(ComplianceFinding).where(
        ComplianceFinding.id == finding_id, ComplianceFinding.report_id == report_id
    )
    res = await session.execute(f_stmt)
    finding = res.scalar_one_or_none()

    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found for this report.",
        )

    return ComplianceFindingResponse.model_validate(finding)
