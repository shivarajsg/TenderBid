from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.companies import CompanyRepository
from app.db.repositories.documents import DocumentRepository
from app.models.company import Company
from app.models.user import User
from app.schemas.company import (
    CapabilityStatementResponse,
    CompanyCreateRequest,
    CompanyReadinessResponse,
    CompanyResponse,
    CompanyUpdateRequest,
    MissingItemGap,
    ReadinessScoreBreakdown,
)


class CompanyNotFoundError(Exception):
    """Raised when an expected company profile is not found."""
    pass


class CompanyConflictError(Exception):
    """Raised when attempting duplicate company creation or registration number conflict."""
    pass


class CompanyService:
    """Service handling MSME profile creation, updates, readiness scoring, and metrics calculation."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.company_repo = CompanyRepository(session)
        self.doc_repo = DocumentRepository(session)

    @staticmethod
    def _calculate_years_in_business(incorporation_date: date) -> int:
        """Calculate whole completed years of operation."""
        today = date.today()
        years = today.year - incorporation_date.year
        if (today.month, today.day) < (incorporation_date.month, incorporation_date.day):
            years -= 1
        return max(0, years)

    def _to_response(self, company: Company) -> CompanyResponse:
        """Convert Company model to structured CompanyResponse."""
        years = self._calculate_years_in_business(company.incorporation_date)
        return CompanyResponse(
            id=company.id,
            owner_id=company.owner_id,
            legal_name=company.legal_name,
            trade_name=company.trade_name,
            registration_number=company.registration_number,
            business_type=company.business_type,
            sector=company.sector,
            incorporation_date=company.incorporation_date,
            years_in_business=years,
            constitution=company.constitution or "PRIVATE_LIMITED",
            pan_number=company.pan_number,
            gstin=company.gstin,
            udyam_number=company.udyam_number,
            dpiit_recognition_number=company.dpiit_recognition_number,
            address=company.address or {},
            contact_details=company.contact_details or {},
            technical_capabilities=company.technical_capabilities or {},
            workforce_metrics=company.workforce_metrics or {},
            tender_exemptions=company.tender_exemptions or {},
            declarations=company.declarations or {},
            annual_turnover=company.annual_turnover or [],
            certifications=company.certifications or [],
            work_experience=company.work_experience or [],
            created_at=company.created_at,
            updated_at=company.updated_at,
        )

    async def get_by_user(self, user: User) -> CompanyResponse:
        """Fetch the authenticated user's company profile."""
        company = await self.company_repo.get_by_owner_id(user.id)
        if not company:
            raise CompanyNotFoundError("Company profile has not been initialized for this account")
        return self._to_response(company)

    async def get_raw_company_by_user(self, user: User) -> Company:
        """Fetch raw Company model for internal operations."""
        company = await self.company_repo.get_by_owner_id(user.id)
        if not company:
            raise CompanyNotFoundError("Company profile has not been initialized for this account")
        return company

    async def create_profile(
        self,
        user: User,
        request: CompanyCreateRequest,
    ) -> CompanyResponse:
        """Create a new company profile for an authenticated user."""
        existing = await self.company_repo.get_by_owner_id(user.id)
        if existing:
            raise CompanyConflictError("User already has an associated company profile")

        reg_check = await self.company_repo.get_by_registration_number(request.registration_number)
        if reg_check:
            raise CompanyConflictError("A company with this registration number already exists")

        # Dump nested Pydantic models to dicts for JSON column storage
        turnover_data = [item.model_dump(mode="json") for item in request.annual_turnover]
        cert_data = [item.model_dump(mode="json") for item in request.certifications]
        work_data = [item.model_dump(mode="json") for item in request.work_experience]

        address_dict = request.address.model_dump(mode="json") if request.address else {}
        contact_dict = request.contact_details.model_dump(mode="json") if request.contact_details else {}
        tech_dict = request.technical_capabilities.model_dump(mode="json") if request.technical_capabilities else {}
        workforce_dict = request.workforce_metrics.model_dump(mode="json") if request.workforce_metrics else {}
        exemptions_dict = request.tender_exemptions.model_dump(mode="json") if request.tender_exemptions else {}
        declarations_dict = request.declarations.model_dump(mode="json") if request.declarations else {}

        company = await self.company_repo.create(
            owner_id=user.id,
            legal_name=request.legal_name,
            trade_name=request.trade_name,
            registration_number=request.registration_number,
            business_type=request.business_type,
            sector=request.sector,
            incorporation_date=request.incorporation_date,
            constitution=request.constitution,
            pan_number=request.pan_number,
            gstin=request.gstin,
            udyam_number=request.udyam_number,
            dpiit_recognition_number=request.dpiit_recognition_number,
            address=address_dict,
            contact_details=contact_dict,
            technical_capabilities=tech_dict,
            workforce_metrics=workforce_dict,
            tender_exemptions=exemptions_dict,
            declarations=declarations_dict,
            annual_turnover=turnover_data,
            certifications=cert_data,
            work_experience=work_data,
        )
        return self._to_response(company)

    async def update_profile(
        self,
        user: User,
        request: CompanyUpdateRequest,
    ) -> CompanyResponse:
        """Update existing company profile fields."""
        company = await self.company_repo.get_by_owner_id(user.id)
        if not company:
            raise CompanyNotFoundError("Company profile not found")

        if request.registration_number and request.registration_number.strip().upper() != company.registration_number:
            reg_check = await self.company_repo.get_by_registration_number(request.registration_number)
            if reg_check and reg_check.id != company.id:
                raise CompanyConflictError("Registration number is already in use by another company")
            company.registration_number = request.registration_number.strip().upper()

        if request.legal_name is not None:
            company.legal_name = request.legal_name.strip()
        if request.trade_name is not None:
            company.trade_name = request.trade_name.strip() if request.trade_name else None
        if request.business_type is not None:
            company.business_type = request.business_type.strip()
        if request.sector is not None:
            company.sector = request.sector.strip()
        if request.incorporation_date is not None:
            company.incorporation_date = request.incorporation_date
        if request.constitution is not None:
            company.constitution = request.constitution
        if request.pan_number is not None:
            company.pan_number = request.pan_number.strip().upper() if request.pan_number else None
        if request.gstin is not None:
            company.gstin = request.gstin.strip().upper() if request.gstin else None
        if request.udyam_number is not None:
            company.udyam_number = request.udyam_number.strip().upper() if request.udyam_number else None
        if request.dpiit_recognition_number is not None:
            company.dpiit_recognition_number = request.dpiit_recognition_number.strip() if request.dpiit_recognition_number else None

        if request.address is not None:
            company.address = request.address.model_dump(mode="json")
        if request.contact_details is not None:
            company.contact_details = request.contact_details.model_dump(mode="json")
        if request.technical_capabilities is not None:
            company.technical_capabilities = request.technical_capabilities.model_dump(mode="json")
        if request.workforce_metrics is not None:
            company.workforce_metrics = request.workforce_metrics.model_dump(mode="json")
        if request.tender_exemptions is not None:
            company.tender_exemptions = request.tender_exemptions.model_dump(mode="json")
        if request.declarations is not None:
            company.declarations = request.declarations.model_dump(mode="json")

        if request.annual_turnover is not None:
            company.annual_turnover = [item.model_dump(mode="json") for item in request.annual_turnover]
        if request.certifications is not None:
            company.certifications = [item.model_dump(mode="json") for item in request.certifications]
        if request.work_experience is not None:
            company.work_experience = [item.model_dump(mode="json") for item in request.work_experience]

        updated = await self.company_repo.update(company)
        return self._to_response(updated)

    async def get_readiness_score(self, user: User) -> CompanyReadinessResponse:
        """Compute an objective data-driven bid readiness score with gap analysis."""
        company = await self.company_repo.get_by_owner_id(user.id)
        if not company:
            raise CompanyNotFoundError("Company profile not found")

        satisfied_items: List[str] = []
        missing_items: List[MissingItemGap] = []

        # 1. Identity & Registration (Max 100)
        id_score = 0
        if company.legal_name:
            id_score += 20
            satisfied_items.append("Legal entity name recorded")
        if company.registration_number or company.udyam_number:
            id_score += 30
            satisfied_items.append(f"Business registration verified ({company.registration_number})")
        else:
            missing_items.append(MissingItemGap(
                category="Identity & Registrations",
                item="Udyam / Business Registration Number",
                severity="HIGH",
                recommendation="Provide official Udyam Registration number to qualify for MSME procurement benefits.",
                section_tab="identity",
            ))

        if company.pan_number:
            id_score += 20
            satisfied_items.append(f"Company PAN verified ({company.pan_number})")
        else:
            missing_items.append(MissingItemGap(
                category="Identity & Registrations",
                item="Corporate PAN",
                severity="HIGH",
                recommendation="Register 10-character PAN required for all statutory tender evaluations.",
                section_tab="identity",
            ))

        if company.gstin:
            id_score += 15
            satisfied_items.append("GSTIN registered")
        else:
            missing_items.append(MissingItemGap(
                category="Identity & Registrations",
                item="GSTIN Registration",
                severity="MEDIUM",
                recommendation="Register 15-character GSTIN for tax compliance checks.",
                section_tab="identity",
            ))

        addr = company.address or {}
        if addr.get("city") and addr.get("state") and addr.get("pincode"):
            id_score += 15
            satisfied_items.append("Registered address recorded")
        else:
            missing_items.append(MissingItemGap(
                category="Identity & Registrations",
                item="Complete Address Details",
                severity="LOW",
                recommendation="Complete registered office address with city, state, and pin code.",
                section_tab="identity",
            ))

        # 2. Financial Capability (Max 100)
        fin_score = 0
        turnovers = company.annual_turnover or []
        if len(turnovers) >= 3:
            fin_score += 50
            satisfied_items.append(f"3+ fiscal years turnover recorded ({len(turnovers)} years)")
        elif len(turnovers) > 0:
            fin_score += 25
            missing_items.append(MissingItemGap(
                category="Financial Capability",
                item="3-Year Turnover History",
                severity="HIGH",
                recommendation=f"Only {len(turnovers)} fiscal year(s) recorded. Most public tenders require 3 consecutive audited years.",
                section_tab="financials",
            ))
        else:
            missing_items.append(MissingItemGap(
                category="Financial Capability",
                item="Audited Annual Turnover",
                severity="HIGH",
                recommendation="Record audited turnover for past 3 fiscal years to pass financial qualification clauses.",
                section_tab="financials",
            ))

        docs_linked = sum(1 for t in turnovers if t.get("document_id"))
        if docs_linked >= 3:
            fin_score += 30
            satisfied_items.append("CA certificates or audited balance sheets linked to all fiscal years")
        elif docs_linked > 0:
            fin_score += 15
            missing_items.append(MissingItemGap(
                category="Financial Capability",
                item="CA Certificate / Balance Sheet Proof",
                severity="MEDIUM",
                recommendation="Link audited balance sheet or CA certificate from Document Vault for each fiscal year.",
                section_tab="financials",
            ))
        else:
            missing_items.append(MissingItemGap(
                category="Financial Capability",
                item="Vault Documents for Turnover",
                severity="HIGH",
                recommendation="Upload and link CA certificates to your turnover records to satisfy evidence requirements.",
                section_tab="financials",
            ))

        has_net_worth = any(t.get("net_worth_inr") is not None for t in turnovers)
        if has_net_worth:
            fin_score += 20
            satisfied_items.append("Net worth metrics recorded")
        else:
            missing_items.append(MissingItemGap(
                category="Financial Capability",
                item="Net Worth Assessment",
                severity="LOW",
                recommendation="Record audited net worth in turnover records to pass positive net worth criteria.",
                section_tab="financials",
            ))

        # 3. Technical Capabilities (Max 100)
        tech_score = 0
        tech = company.technical_capabilities or {}
        if company.sector:
            tech_score += 25
            satisfied_items.append(f"Primary domain specified: {company.sector}")
        if tech.get("products") and len(tech.get("products", [])) > 0:
            tech_score += 25
            satisfied_items.append(f"{len(tech.get('products'))} product(s) registered")
        if tech.get("services") and len(tech.get("services", [])) > 0:
            tech_score += 25
            satisfied_items.append(f"{len(tech.get('services'))} service(s) registered")
        if tech.get("oem_status"):
            tech_score += 15
            satisfied_items.append(f"OEM classification set ({tech.get('oem_status')})")
        if tech.get("testing_facilities"):
            tech_score += 10
            satisfied_items.append("Testing/QC facility details specified")
        if tech_score < 50:
            missing_items.append(MissingItemGap(
                category="Technical Capabilities",
                item="Products & Services Catalog",
                severity="MEDIUM",
                recommendation="List manufactured products or core services offered to improve tender item matching.",
                section_tab="technical",
            ))

        # 4. Certifications & Standards (Max 100)
        cert_score = 0
        certs = company.certifications or []
        if certs:
            cert_score += 50
            satisfied_items.append(f"{len(certs)} corporate certification(s) registered")
            has_cert_doc = any(c.get("document_id") for c in certs)
            if has_cert_doc:
                cert_score += 30
                satisfied_items.append("Certificate documents linked in vault")
            else:
                missing_items.append(MissingItemGap(
                    category="Certifications & Standards",
                    item="Certificate Proof Documents",
                    severity="MEDIUM",
                    recommendation="Attach official certificate PDFs from the Document Vault to your certifications.",
                    section_tab="certifications",
                ))
            # Check for expiring certs
            today = date.today()
            for c in certs:
                v_until = c.get("valid_until")
                if v_until:
                    if isinstance(v_until, str):
                        try:
                            v_until_date = date.fromisoformat(v_until)
                        except Exception:
                            v_until_date = None
                    else:
                        v_until_date = v_until
                    if v_until_date and v_until_date < today:
                        missing_items.append(MissingItemGap(
                            category="Certifications & Standards",
                            item=f"Expired Certificate ({c.get('name')})",
                            severity="HIGH",
                            recommendation=f"Certificate '{c.get('name')}' expired on {v_until_date}. Upload renewed certificate.",
                            section_tab="certifications",
                        ))
                    elif v_until_date and (v_until_date - today).days <= 60:
                        missing_items.append(MissingItemGap(
                            category="Certifications & Standards",
                            item=f"Expiring Soon: {c.get('name')}",
                            severity="LOW",
                            recommendation=f"Certificate '{c.get('name')}' expires within {(v_until_date - today).days} days.",
                            section_tab="certifications",
                        ))
            cert_score = min(100, cert_score + 20)
        else:
            missing_items.append(MissingItemGap(
                category="Certifications & Standards",
                item="Quality Certifications (e.g. ISO 9001)",
                severity="MEDIUM",
                recommendation="Register quality certifications (ISO 9001, BIS, etc.) frequently required by GeM/CPPP tenders.",
                section_tab="certifications",
            ))

        # 5. Past Experience (Max 100)
        exp_score = 0
        work = company.work_experience or []
        if len(work) >= 3:
            exp_score += 60
            satisfied_items.append(f"{len(work)} past contracts registered")
        elif len(work) > 0:
            exp_score += 35
            satisfied_items.append(f"{len(work)} past contract(s) registered")
            missing_items.append(MissingItemGap(
                category="Past Experience",
                item="3+ Past Completed Contracts",
                severity="MEDIUM",
                recommendation="Tenders typically require 3 similar completed works within past 5-7 years.",
                section_tab="experience",
            ))
        else:
            missing_items.append(MissingItemGap(
                category="Past Experience",
                item="Completed Projects & Work Orders",
                severity="HIGH",
                recommendation="Add completed past work orders to satisfy past experience criteria.",
                section_tab="experience",
            ))

        if any(w.get("document_id") for w in work):
            exp_score += 40
            satisfied_items.append("Work order / completion certificates linked")
        elif work:
            missing_items.append(MissingItemGap(
                category="Past Experience",
                item="Completion Certificates / PO Proof",
                severity="MEDIUM",
                recommendation="Link client completion certificates from Document Vault to verify past contracts.",
                section_tab="experience",
            ))

        # 6. Workforce & Operations (Max 100)
        workforce_score = 0
        wf = company.workforce_metrics or {}
        if wf.get("total_employees", 0) > 0:
            workforce_score += 40
            satisfied_items.append(f"Workforce registered: {wf.get('total_employees')} employees")
        if wf.get("engineers_count", 0) > 0 or wf.get("technicians_count", 0) > 0:
            workforce_score += 40
            satisfied_items.append(f"Technical staff recorded: {wf.get('engineers_count', 0)} engineers")
        if wf.get("service_centers_count", 0) > 0 or wf.get("emergency_support"):
            workforce_score += 20
        if workforce_score < 40:
            missing_items.append(MissingItemGap(
                category="Workforce & Operations",
                item="Technical Team Information",
                severity="LOW",
                recommendation="Declare number of engineers and technical personnel for technical evaluation.",
                section_tab="workforce",
            ))

        # 7. Statutory Declarations & Exemptions (Max 100)
        stat_score = 0
        ex = company.tender_exemptions or {}
        decl = company.declarations or {}
        if ex.get("emd_exemption") or company.business_type in ["MICRO", "SMALL"]:
            stat_score += 35
            satisfied_items.append("MSME EMD exemption status active")
        if ex.get("mii_class"):
            stat_score += 35
            satisfied_items.append(f"Make in India preference: {ex.get('mii_class')} ({ex.get('mii_percentage', 50)}% local content)")
        if decl.get("non_blacklisted"):
            stat_score += 30
            satisfied_items.append("Non-blacklisting declaration recorded")
        else:
            missing_items.append(MissingItemGap(
                category="Statutory & Exemptions",
                item="Non-Blacklisting Declaration",
                severity="HIGH",
                recommendation="Affirm self-declaration of non-blacklisting / debarment.",
                section_tab="exemptions",
            ))

        breakdown = ReadinessScoreBreakdown(
            identity_and_registration=min(100, id_score),
            financial_capability=min(100, fin_score),
            technical_capabilities=min(100, tech_score),
            certifications_and_standards=min(100, cert_score),
            past_experience=min(100, exp_score),
            workforce_and_operations=min(100, workforce_score),
            statutory_and_exemptions=min(100, stat_score),
        )

        # Weighted Overall Score
        overall = int(
            breakdown.identity_and_registration * 0.15
            + breakdown.financial_capability * 0.25
            + breakdown.technical_capabilities * 0.15
            + breakdown.certifications_and_standards * 0.15
            + breakdown.past_experience * 0.15
            + breakdown.workforce_and_operations * 0.05
            + breakdown.statutory_and_exemptions * 0.10
        )
        overall = max(0, min(100, overall))

        if overall >= 80:
            stage = "BID_READY"
        elif overall >= 50:
            stage = "PARTIALLY_READY"
        else:
            stage = "CRITICAL_GAPS"

        return CompanyReadinessResponse(
            overall_score=overall,
            readiness_stage=stage,
            breakdown=breakdown,
            satisfied_items=satisfied_items,
            missing_items=missing_items,
            calculated_at=datetime.now(timezone.utc),
        )

    async def get_capability_statement(self, user: User) -> CapabilityStatementResponse:
        """Generate structured capability statement data."""
        company = await self.company_repo.get_by_owner_id(user.id)
        if not company:
            raise CompanyNotFoundError("Company profile not found")

        resp = self._to_response(company)
        turnovers = company.annual_turnover or []
        total_turnover = sum(float(t.get("turnover_inr", 0)) for t in turnovers)
        avg_turnover = (total_turnover / len(turnovers)) if turnovers else 0.0

        latest_turnover = turnovers[-1] if turnovers else {}
        latest_net_worth = latest_turnover.get("net_worth_inr")

        metrics = {
            "years_in_business": resp.years_in_business,
            "recorded_fiscal_years": len(turnovers),
            "average_turnover_inr": round(avg_turnover, 2),
            "latest_turnover_inr": latest_turnover.get("turnover_inr", 0.0),
            "latest_net_worth_inr": latest_net_worth,
            "certifications_count": len(company.certifications or []),
            "completed_contracts_count": len(company.work_experience or []),
            "total_contract_value_inr": sum(float(w.get("contract_value_inr", 0)) for w in (company.work_experience or [])),
            "employee_count": (company.workforce_metrics or {}).get("total_employees", 0),
            "engineers_count": (company.workforce_metrics or {}).get("engineers_count", 0),
        }

        summary_text = (
            f"{company.legal_name} is an MSME {company.business_type.capitalize()} enterprise "
            f"incorporated on {company.incorporation_date.strftime('%d-%b-%Y')} ({resp.years_in_business} years in business), "
            f"specializing in {company.sector}. The company maintains an audited 3-year average turnover of "
            f"₹{avg_turnover:,.2f} INR with {len(company.certifications or [])} verified quality credentials and "
            f"{len(company.work_experience or [])} completed government and enterprise contracts."
        )

        return CapabilityStatementResponse(
            generated_at=datetime.now(timezone.utc),
            company=resp,
            metrics=metrics,
            summary_text=summary_text,
        )
