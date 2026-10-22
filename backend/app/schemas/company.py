from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class TurnoverRecord(BaseModel):
    """Annual audited turnover entry."""
    fiscal_year: str = Field(description="e.g. 2024-2025")
    turnover_inr: float = Field(ge=0, description="Audited turnover in INR")
    currency: str = Field(default="INR")


class CertificationRecord(BaseModel):
    """Corporate certification credential."""
    name: str = Field(description="e.g. ISO 9001:2015")
    issuing_authority: Optional[str] = Field(default=None)
    valid_until: Optional[date] = Field(default=None)
    document_id: Optional[UUID] = Field(default=None)


class WorkExperienceRecord(BaseModel):
    """Past completed work contract."""
    project_title: str
    client_name: str
    contract_value_inr: float = Field(ge=0)
    completion_date: Optional[date] = None


class CompanyCreateRequest(BaseModel):
    """Payload to create an MSME company profile."""
    legal_name: str = Field(min_length=2, max_length=255)
    registration_number: str = Field(min_length=3, max_length=100)
    business_type: str = Field(default="SMALL")  # MICRO, SMALL, MEDIUM
    sector: str = Field(min_length=2, max_length=100)
    incorporation_date: date
    annual_turnover: List[TurnoverRecord] = Field(default_factory=list)
    certifications: List[CertificationRecord] = Field(default_factory=list)
    work_experience: List[WorkExperienceRecord] = Field(default_factory=list)


class CompanyUpdateRequest(BaseModel):
    """Payload to update an MSME company profile."""
    legal_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    registration_number: Optional[str] = Field(default=None, min_length=3, max_length=100)
    business_type: Optional[str] = None
    sector: Optional[str] = Field(default=None, min_length=2, max_length=100)
    incorporation_date: Optional[date] = None
    annual_turnover: Optional[List[TurnoverRecord]] = None
    certifications: Optional[List[CertificationRecord]] = None
    work_experience: Optional[List[WorkExperienceRecord]] = None


class CompanyResponse(BaseModel):
    """Outbound representation of an MSME company profile."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    legal_name: str
    registration_number: str
    business_type: str
    sector: str
    incorporation_date: date
    years_in_business: int
    annual_turnover: List[Dict[str, Any]]
    certifications: List[Dict[str, Any]]
    work_experience: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
