from decimal import Decimal
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


class TurnoverRequirement(BaseModel):
    """Normalized structured requirement for company annual or average turnover."""
    required_turnover_inr: Decimal = Field(..., ge=0, description="Minimum turnover threshold in INR")
    currency: str = Field(default="INR", max_length=10)
    comparison_method: str = Field(
        default="ANNUAL_MINIMUM",
        description="Comparison rule: 'ANNUAL_MINIMUM' (each FY must meet threshold) or 'AVERAGE_TURNOVER' (average across FYs)",
    )
    financial_years_count: int = Field(default=3, ge=1, le=5)
    is_mandatory: bool = Field(default=True)
    citation_reference: Optional[str] = None


class ExperienceRequirement(BaseModel):
    """Normalized structured requirement for relevant past project experience."""
    min_experience_years: int = Field(..., ge=0, description="Minimum relevant project experience in years")
    min_completed_projects: int = Field(default=1, ge=0)
    min_single_contract_value_inr: Optional[Decimal] = Field(default=None, ge=0)
    relevant_domain: Optional[str] = None
    is_mandatory: bool = Field(default=True)
    citation_reference: Optional[str] = None


class CertificationRequirement(BaseModel):
    """Normalized structured requirement for mandatory quality or technical certifications."""
    name: str = Field(..., min_length=2, max_length=150, description="Official certification name (e.g. ISO 9001:2015)")
    issuing_authority: Optional[str] = None
    is_mandatory: bool = Field(default=True)
    citation_reference: Optional[str] = None


class MandatoryDocumentRequirement(BaseModel):
    """Normalized structured requirement for mandatory uploaded document proofs."""
    document_name: str = Field(..., min_length=2, max_length=200)
    document_category: str = Field(default="OTHER", max_length=50)
    is_mandatory: bool = Field(default=True)
    citation_reference: Optional[str] = None


class DeadlineRequirement(BaseModel):
    """Normalized structured requirement for submission timeline."""
    submission_deadline_utc: datetime
    is_mandatory: bool = Field(default=True)
    citation_reference: Optional[str] = None


class TechnicalRequirement(BaseModel):
    """Normalized requirement for equipment, performance, standard, or technical specification."""
    title: str = Field(..., min_length=2, max_length=255)
    specification: str = Field(..., min_length=2)
    standard_or_code: Optional[str] = None
    is_mandatory: bool = Field(default=True)
    citation_reference: Optional[str] = None


class CommercialRequirement(BaseModel):
    """Normalized requirement for EMD, bid security, fee, or payment conditions."""
    title: str = Field(..., min_length=2, max_length=255)
    condition_type: str = Field(default="EMD", description="EMD, TENDER_FEE, PBG, PAYMENT_TERMS")
    amount_inr: Optional[Decimal] = Field(default=None, ge=0)
    msme_exemptible: bool = Field(default=True)
    is_mandatory: bool = Field(default=True)
    citation_reference: Optional[str] = None


class LegalRequirement(BaseModel):
    """Normalized requirement for statutory registration, non-blacklisting, or legal declaration."""
    title: str = Field(..., min_length=2, max_length=255)
    registration_type: str = Field(default="REGISTRATION", description="GST, PAN, UDYAM, NON_BLACKLISTING, AFFIDAVIT")
    is_mandatory: bool = Field(default=True)
    citation_reference: Optional[str] = None


class SubmissionRequirement(BaseModel):
    """Normalized requirement for forms, annexures, formats, seals, or procedural instructions."""
    title: str = Field(..., min_length=2, max_length=255)
    requirement_type: str = Field(default="FORM", description="FORM, ANNEXURE, SIGNATURE_SEAL, FORMAT")
    is_mandatory: bool = Field(default=True)
    citation_reference: Optional[str] = None


class NormalizedTenderRequirements(BaseModel):
    """Consolidated normalized structured criteria bundle evaluated by the deterministic engine."""
    turnover: Optional[TurnoverRequirement] = None
    experience: Optional[ExperienceRequirement] = None
    certifications: List[CertificationRequirement] = Field(default_factory=list)
    mandatory_documents: List[MandatoryDocumentRequirement] = Field(default_factory=list)
    deadline: Optional[DeadlineRequirement] = None
    technical_requirements: List[TechnicalRequirement] = Field(default_factory=list)
    commercial_requirements: List[CommercialRequirement] = Field(default_factory=list)
    legal_requirements: List[LegalRequirement] = Field(default_factory=list)
    submission_requirements: List[SubmissionRequirement] = Field(default_factory=list)
    unsupported_clauses: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_has_at_least_one_criterion(self) -> "NormalizedTenderRequirements":
        has_any = (
            self.turnover is not None
            or self.experience is not None
            or len(self.certifications) > 0
            or len(self.mandatory_documents) > 0
            or self.deadline is not None
            or len(self.technical_requirements) > 0
            or len(self.commercial_requirements) > 0
            or len(self.legal_requirements) > 0
            or len(self.submission_requirements) > 0
        )
        if not has_any and not self.unsupported_clauses:
            raise ValueError("Structured requirements must contain at least one verifiable requirement or clause.")
        return self
