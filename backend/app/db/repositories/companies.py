from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.company import Company


class CompanyRepository:
    """Repository handling database operations for the Company entity."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, company_id: UUID) -> Optional[Company]:
        """Fetch company by UUID primary key."""
        stmt = (
            select(Company)
            .options(selectinload(Company.documents))
            .where(Company.id == company_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_owner_id(self, owner_id: UUID) -> Optional[Company]:
        """Fetch company owned by a specific user UUID."""
        stmt = (
            select(Company)
            .options(selectinload(Company.documents))
            .where(Company.owner_id == owner_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_registration_number(self, reg_num: str) -> Optional[Company]:
        """Fetch company by its registration number (e.g. Udyam / GSTIN)."""
        stmt = select(Company).where(Company.registration_number == reg_num.strip().upper())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        owner_id: UUID,
        legal_name: str,
        registration_number: str,
        business_type: str,
        sector: str,
        incorporation_date: date,
        trade_name: Optional[str] = None,
        constitution: Optional[str] = "PRIVATE_LIMITED",
        pan_number: Optional[str] = None,
        gstin: Optional[str] = None,
        udyam_number: Optional[str] = None,
        dpiit_recognition_number: Optional[str] = None,
        address: Optional[Dict[str, Any]] = None,
        contact_details: Optional[Dict[str, Any]] = None,
        technical_capabilities: Optional[Dict[str, Any]] = None,
        workforce_metrics: Optional[Dict[str, Any]] = None,
        tender_exemptions: Optional[Dict[str, Any]] = None,
        declarations: Optional[Dict[str, Any]] = None,
        annual_turnover: Optional[List[Dict[str, Any]]] = None,
        certifications: Optional[List[Dict[str, Any]]] = None,
        work_experience: Optional[List[Dict[str, Any]]] = None,
    ) -> Company:
        """Create and persist a new company record."""
        company = Company(
            owner_id=owner_id,
            legal_name=legal_name.strip(),
            trade_name=trade_name.strip() if trade_name else None,
            registration_number=registration_number.strip().upper(),
            business_type=business_type.strip(),
            sector=sector.strip(),
            incorporation_date=incorporation_date,
            constitution=constitution or "PRIVATE_LIMITED",
            pan_number=pan_number.strip().upper() if pan_number else None,
            gstin=gstin.strip().upper() if gstin else None,
            udyam_number=udyam_number.strip().upper() if udyam_number else None,
            dpiit_recognition_number=dpiit_recognition_number.strip() if dpiit_recognition_number else None,
            address=address or {},
            contact_details=contact_details or {},
            technical_capabilities=technical_capabilities or {},
            workforce_metrics=workforce_metrics or {},
            tender_exemptions=tender_exemptions or {},
            declarations=declarations or {},
            annual_turnover=annual_turnover or [],
            certifications=certifications or [],
            work_experience=work_experience or [],
        )
        self.session.add(company)
        await self.session.flush()
        await self.session.refresh(company)
        return company

    async def update(self, company: Company) -> Company:
        """Persist updates to an existing company record."""
        self.session.add(company)
        await self.session.flush()
        await self.session.refresh(company)
        return company
