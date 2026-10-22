from datetime import date
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.companies import CompanyRepository
from app.models.company import Company
from app.models.user import User
from app.schemas.company import (
    CompanyCreateRequest,
    CompanyResponse,
    CompanyUpdateRequest,
)


class CompanyNotFoundError(Exception):
    """Raised when an expected company profile is not found."""
    pass


class CompanyConflictError(Exception):
    """Raised when attempting duplicate company creation or registration number conflict."""
    pass


class CompanyService:
    """Service handling MSME profile creation, updates, and metrics calculation."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.company_repo = CompanyRepository(session)

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
            registration_number=company.registration_number,
            business_type=company.business_type,
            sector=company.sector,
            incorporation_date=company.incorporation_date,
            years_in_business=years,
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

        company = await self.company_repo.create(
            owner_id=user.id,
            legal_name=request.legal_name,
            registration_number=request.registration_number,
            business_type=request.business_type,
            sector=request.sector,
            incorporation_date=request.incorporation_date,
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

        if request.registration_number and request.registration_number != company.registration_number:
            reg_check = await self.company_repo.get_by_registration_number(request.registration_number)
            if reg_check and reg_check.id != company.id:
                raise CompanyConflictError("Registration number is already in use by another company")
            company.registration_number = request.registration_number.strip().upper()

        if request.legal_name is not None:
            company.legal_name = request.legal_name.strip()
        if request.business_type is not None:
            company.business_type = request.business_type.strip()
        if request.sector is not None:
            company.sector = request.sector.strip()
        if request.incorporation_date is not None:
            company.incorporation_date = request.incorporation_date
        if request.annual_turnover is not None:
            company.annual_turnover = [item.model_dump(mode="json") for item in request.annual_turnover]
        if request.certifications is not None:
            company.certifications = [item.model_dump(mode="json") for item in request.certifications]
        if request.work_experience is not None:
            company.work_experience = [item.model_dump(mode="json") for item in request.work_experience]

        updated = await self.company_repo.update(company)
        return self._to_response(updated)
