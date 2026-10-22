from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
import re
from pydantic import BaseModel, ConfigDict, Field, field_validator


MAX_FINANCIAL_VALUE_INR = 100_000_000_000.0  # 10,000 Crores cap to prevent scientific notation overflow


def _parse_and_validate_amount(v: Any, allow_negative: bool = False) -> Optional[float]:
    """Helper to parse currency values, stripping formatting and blocking scientific notation."""
    if v is None:
        return None
    if isinstance(v, str):
        v_clean = v.strip().replace(",", "").replace(" ", "").replace("₹", "")
        if not v_clean:
            return 0.0 if not allow_negative else None
        # Reject scientific notation like '1e+25' or '1E10'
        if "e" in v_clean.lower():
            raise ValueError("Scientific notation is not permitted for financial values")
        try:
            val = float(v_clean)
        except ValueError:
            raise ValueError(f"Invalid numeric financial value: '{v}'")
    elif isinstance(v, (int, float)):
        val = float(v)
    else:
        raise ValueError(f"Unsupported financial value type: {type(v)}")

    if not allow_negative and val < 0:
        raise ValueError("Financial value cannot be negative")

    if abs(val) > MAX_FINANCIAL_VALUE_INR:
        raise ValueError(f"Value ₹{val:,.2f} exceeds allowable financial threshold (₹10,000 Cr)")

    return round(val, 2)


class TurnoverRecord(BaseModel):
    """Annual audited turnover and financial metric entry."""
    fiscal_year: str = Field(description="e.g. 2024-2025")
    turnover_inr: float = Field(default=0.0, description="Audited turnover in INR")
    net_worth_inr: Optional[float] = Field(default=None, description="Net worth in INR")
    profit_after_tax_inr: Optional[float] = Field(default=None, description="Profit / (Loss) After Tax in INR")
    currency: str = Field(default="INR")
    document_id: Optional[UUID] = Field(default=None, description="Vault Document ID of CA certificate / Balance sheet")

    @field_validator("turnover_inr", mode="before")
    @classmethod
    def validate_turnover(cls, v: Any) -> float:
        parsed = _parse_and_validate_amount(v, allow_negative=False)
        return parsed if parsed is not None else 0.0

    @field_validator("net_worth_inr", "profit_after_tax_inr", mode="before")
    @classmethod
    def validate_net_worth_pat(cls, v: Any) -> Optional[float]:
        return _parse_and_validate_amount(v, allow_negative=True)


class CertificationRecord(BaseModel):
    """Corporate certification credential."""
    name: str = Field(description="e.g. ISO 9001:2015, BIS, CE")
    certificate_number: Optional[str] = Field(default=None, description="Official registration / cert number")
    issuing_authority: Optional[str] = Field(default=None, description="e.g. Bureau Veritas, TUV, BSI")
    valid_from: Optional[date] = Field(default=None)
    valid_until: Optional[date] = Field(default=None)
    verification_status: Optional[str] = Field(default="VERIFIED_VALID")
    document_id: Optional[UUID] = Field(default=None, description="Vault Document ID")


class WorkExperienceRecord(BaseModel):
    """Past completed or ongoing work contract."""
    project_title: str
    client_name: str
    client_type: Optional[str] = Field(default="CENTRAL_GOVT")  # CENTRAL_GOVT, STATE_GOVT, PSU, DEFENSE_RAILWAYS, PRIVATE, OTHER
    contract_value_inr: float = Field(default=0.0)
    work_order_number: Optional[str] = Field(default=None)
    start_date: Optional[date] = None
    completion_date: Optional[date] = None
    status: Optional[str] = Field(default="COMPLETED")  # COMPLETED, ONGOING
    document_id: Optional[UUID] = Field(default=None, description="Vault Document ID for PO / Completion Cert")

    @field_validator("contract_value_inr", mode="before")
    @classmethod
    def validate_contract_value(cls, v: Any) -> float:
        parsed = _parse_and_validate_amount(v, allow_negative=False)
        return parsed if parsed is not None else 0.0


class AddressRecord(BaseModel):
    """Registered corporate address details."""
    line1: Optional[str] = Field(default="", max_length=255)
    line2: Optional[str] = Field(default="", max_length=255)
    city: Optional[str] = Field(default="", max_length=100)
    state: Optional[str] = Field(default="", max_length=100)
    pincode: Optional[str] = Field(default="", max_length=20)
    country: Optional[str] = Field(default="India", max_length=100)


class ContactDetailsRecord(BaseModel):
    """Primary contact & authorized signatory details."""
    signatory_name: Optional[str] = Field(default="", max_length=255)
    designation: Optional[str] = Field(default="", max_length=100)
    email: Optional[str] = Field(default="", max_length=255)
    phone: Optional[str] = Field(default="", max_length=50)
    website: Optional[str] = Field(default="", max_length=255)


class TechnicalCapabilitiesRecord(BaseModel):
    """Manufacturing, OEM status, and operational domain credentials."""
    core_domains: List[str] = Field(default_factory=list)
    products: List[Dict[str, Any]] = Field(default_factory=list)  # [{name, hsn_code, capacity_per_month}]
    services: List[Dict[str, Any]] = Field(default_factory=list)  # [{name, sac_code, description}]
    oem_status: Optional[str] = Field(default="OEM")  # OEM, AUTHORIZED_DEALER, SYSTEM_INTEGRATOR, SERVICE_PROVIDER
    testing_facilities: Optional[str] = Field(default="")
    service_coverage: Optional[str] = Field(default="PAN_INDIA")  # PAN_INDIA, REGIONAL, STATE


class WorkforceMetricsRecord(BaseModel):
    """Employee count, engineering capacity, and key personnel."""
    total_employees: Optional[int] = Field(default=0, ge=0)
    engineers_count: Optional[int] = Field(default=0, ge=0)
    technicians_count: Optional[int] = Field(default=0, ge=0)
    project_managers_count: Optional[int] = Field(default=0, ge=0)
    service_centers_count: Optional[int] = Field(default=0, ge=0)
    emergency_support: Optional[bool] = Field(default=True)
    key_personnel: List[Dict[str, Any]] = Field(default_factory=list)  # [{name, designation, experience_years, qualification}]


class TenderExemptionsRecord(BaseModel):
    """MSME, DPIIT startup, and Make in India exemption claims."""
    msme_category: Optional[str] = Field(default="SMALL")  # MICRO, SMALL, MEDIUM
    emd_exemption: Optional[bool] = Field(default=True)
    tender_fee_exemption: Optional[bool] = Field(default=True)
    turnover_relaxation: Optional[bool] = Field(default=True)
    experience_relaxation: Optional[bool] = Field(default=True)
    is_dpiit_startup: Optional[bool] = Field(default=False)
    mii_class: Optional[str] = Field(default="CLASS_1")  # CLASS_1, CLASS_2, NON_LOCAL
    mii_percentage: Optional[float] = Field(default=50.0, ge=0.0, le=100.0)
    emd_document_id: Optional[UUID] = None


class DeclarationsRecord(BaseModel):
    """Self-declarations and statutory affidavits."""
    non_blacklisted: Optional[bool] = Field(default=True)
    no_conflict_of_interest: Optional[bool] = Field(default=True)
    mii_compliant: Optional[bool] = Field(default=True)
    updated_at: Optional[str] = None


class CompanyCreateRequest(BaseModel):
    """Payload to create an MSME company profile."""
    legal_name: str = Field(min_length=2, max_length=255)
    trade_name: Optional[str] = Field(default=None, max_length=255)
    registration_number: str = Field(min_length=3, max_length=100)
    business_type: str = Field(default="SMALL")  # MICRO, SMALL, MEDIUM
    sector: str = Field(min_length=2, max_length=100)
    incorporation_date: date
    constitution: Optional[str] = Field(default="PRIVATE_LIMITED")
    pan_number: Optional[str] = Field(default=None, max_length=10)
    gstin: Optional[str] = Field(default=None, max_length=15)
    udyam_number: Optional[str] = Field(default=None, max_length=50)
    dpiit_recognition_number: Optional[str] = Field(default=None, max_length=50)

    address: Optional[AddressRecord] = None
    contact_details: Optional[ContactDetailsRecord] = None
    technical_capabilities: Optional[TechnicalCapabilitiesRecord] = None
    workforce_metrics: Optional[WorkforceMetricsRecord] = None
    tender_exemptions: Optional[TenderExemptionsRecord] = None
    declarations: Optional[DeclarationsRecord] = None

    annual_turnover: List[TurnoverRecord] = Field(default_factory=list)
    certifications: List[CertificationRecord] = Field(default_factory=list)
    work_experience: List[WorkExperienceRecord] = Field(default_factory=list)

    @field_validator("pan_number")
    @classmethod
    def format_pan(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        v = v.strip().upper()
        if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", v):
            raise ValueError("PAN must be a valid 10-character alphanumeric identifier (e.g. ABCDE1234F)")
        return v

    @field_validator("gstin")
    @classmethod
    def format_gstin(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        v = v.strip().upper()
        if not re.match(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$", v):
            raise ValueError("GSTIN must be a valid 15-character alphanumeric identifier")
        return v


class CompanyUpdateRequest(BaseModel):
    """Payload to update an MSME company profile."""
    legal_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    trade_name: Optional[str] = Field(default=None, max_length=255)
    registration_number: Optional[str] = Field(default=None, min_length=3, max_length=100)
    business_type: Optional[str] = None
    sector: Optional[str] = Field(default=None, min_length=2, max_length=100)
    incorporation_date: Optional[date] = None
    constitution: Optional[str] = None
    pan_number: Optional[str] = Field(default=None, max_length=10)
    gstin: Optional[str] = Field(default=None, max_length=15)
    udyam_number: Optional[str] = Field(default=None, max_length=50)
    dpiit_recognition_number: Optional[str] = Field(default=None, max_length=50)

    address: Optional[AddressRecord] = None
    contact_details: Optional[ContactDetailsRecord] = None
    technical_capabilities: Optional[TechnicalCapabilitiesRecord] = None
    workforce_metrics: Optional[WorkforceMetricsRecord] = None
    tender_exemptions: Optional[TenderExemptionsRecord] = None
    declarations: Optional[DeclarationsRecord] = None

    annual_turnover: Optional[List[TurnoverRecord]] = None
    certifications: Optional[List[CertificationRecord]] = None
    work_experience: Optional[List[WorkExperienceRecord]] = None

    @field_validator("pan_number")
    @classmethod
    def format_pan(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        v = v.strip().upper()
        if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", v):
            raise ValueError("PAN must be a valid 10-character alphanumeric identifier (e.g. ABCDE1234F)")
        return v

    @field_validator("gstin")
    @classmethod
    def format_gstin(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        v = v.strip().upper()
        if not re.match(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$", v):
            raise ValueError("GSTIN must be a valid 15-character alphanumeric identifier")
        return v


class CompanyResponse(BaseModel):
    """Outbound representation of an MSME company profile."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    legal_name: str
    trade_name: Optional[str] = None
    registration_number: str
    business_type: str
    sector: str
    incorporation_date: date
    years_in_business: int
    constitution: Optional[str] = "PRIVATE_LIMITED"
    pan_number: Optional[str] = None
    gstin: Optional[str] = None
    udyam_number: Optional[str] = None
    dpiit_recognition_number: Optional[str] = None

    address: Dict[str, Any] = Field(default_factory=dict)
    contact_details: Dict[str, Any] = Field(default_factory=dict)
    technical_capabilities: Dict[str, Any] = Field(default_factory=dict)
    workforce_metrics: Dict[str, Any] = Field(default_factory=dict)
    tender_exemptions: Dict[str, Any] = Field(default_factory=dict)
    declarations: Dict[str, Any] = Field(default_factory=dict)

    annual_turnover: List[Dict[str, Any]]
    certifications: List[Dict[str, Any]]
    work_experience: List[Dict[str, Any]]

    created_at: datetime
    updated_at: datetime


class MissingItemGap(BaseModel):
    """Actionable recommendation for a missing capability / document."""
    category: str
    item: str
    severity: str  # HIGH, MEDIUM, LOW
    recommendation: str
    section_tab: str


class ReadinessScoreBreakdown(BaseModel):
    """Category breakdown of compliance and capability readiness."""
    identity_and_registration: int
    financial_capability: int
    technical_capabilities: int
    certifications_and_standards: int
    past_experience: int
    workforce_and_operations: int
    statutory_and_exemptions: int


class CompanyReadinessResponse(BaseModel):
    """Data-driven profile completeness and bid readiness evaluation."""
    overall_score: int
    readiness_stage: str  # CRITICAL_GAPS, PARTIALLY_READY, BID_READY
    breakdown: ReadinessScoreBreakdown
    satisfied_items: List[str]
    missing_items: List[MissingItemGap]
    calculated_at: datetime


class CapabilityStatementResponse(BaseModel):
    """Formatted company capability statement suitable for export or bid annexures."""
    generated_at: datetime
    company: CompanyResponse
    metrics: Dict[str, Any]
    summary_text: str
