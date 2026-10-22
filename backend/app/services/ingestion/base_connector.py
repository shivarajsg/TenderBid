import abc
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass
class RawTenderRecord:
    """Standardized normalized representation of a public government tender notice."""

    tender_reference: str
    title: str
    issuing_authority: str
    sector: str
    submission_deadline: datetime
    source_portal: str  # GEM, CPPP, OPEN_GOV
    source_tender_id: str
    estimated_budget_inr: Optional[Decimal] = None
    emd_amount_inr: Optional[Decimal] = None
    msme_emd_exemption: bool = True
    publication_date: Optional[datetime] = None
    official_portal_url: Optional[str] = None
    structured_requirements: Optional[Dict[str, Any]] = None
    ingestion_metadata: Dict[str, Any] = field(default_factory=dict)


class BaseTenderConnector(abc.ABC):
    """Abstract interface for government procurement data connectors."""

    @property
    @abc.abstractmethod
    def portal_name(self) -> str:
        """Short identifier: GEM, CPPP, OPEN_GOV."""
        pass

    @property
    @abc.abstractmethod
    def portal_title(self) -> str:
        """Human-readable portal name: Government e-Marketplace, etc."""
        pass

    @property
    @abc.abstractmethod
    def official_url(self) -> str:
        """Base URL of official government portal."""
        pass

    @abc.abstractmethod
    async def check_availability(self) -> Dict[str, Any]:
        """
        Probe portal endpoint accessibility and authentication status.
        Must report transparently on CAPTCHA blockers, auth requirements, or open availability.
        """
        pass

    @abc.abstractmethod
    async def fetch_tenders(self, limit: int = 50) -> List[RawTenderRecord]:
        """
        Discover and normalize active public tenders within ethical and legal boundaries.
        Returns list of standardized RawTenderRecord instances.
        """
        pass
