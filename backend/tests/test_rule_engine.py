from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import pytest

from app.schemas.requirements import (
    CertificationRequirement,
    DeadlineRequirement,
    ExperienceRequirement,
    MandatoryDocumentRequirement,
    NormalizedTenderRequirements,
    TurnoverRequirement,
)
from app.services.compliance.rule_engine import DeterministicRuleEngine


@pytest.fixture
def rule_engine():
    return DeterministicRuleEngine()


# ============================================================================
# Turnover Rule Tests
# ============================================================================

def test_turnover_above_threshold(rule_engine):
    """Verify turnover strictly above threshold returns PASS."""
    req = TurnoverRequirement(
        required_turnover_inr=Decimal("50000000.00"),  # 5 Cr
        comparison_method="ANNUAL_MINIMUM",
        financial_years_count=3,
    )
    records = [
        {"fiscal_year": "2023-2024", "turnover_inr": 60000000.0},
        {"fiscal_year": "2022-2023", "turnover_inr": 55000000.0},
        {"fiscal_year": "2021-2022", "turnover_inr": 52000000.0},
    ]
    finding = rule_engine.evaluate_turnover(req, records)
    assert finding.status == "PASS"
    assert finding.rule_type == "TURNOVER"
    assert finding.is_mandatory is True
    assert "meet or exceed" in finding.reason.lower()


def test_turnover_exactly_at_threshold(rule_engine):
    """Verify turnover exactly at boundary threshold returns PASS."""
    req = TurnoverRequirement(
        required_turnover_inr=Decimal("50000000.00"),
        comparison_method="ANNUAL_MINIMUM",
        financial_years_count=1,
    )
    records = [{"fiscal_year": "2023-2024", "turnover_inr": 50000000.0}]
    finding = rule_engine.evaluate_turnover(req, records)
    assert finding.status == "PASS"


def test_turnover_below_threshold(rule_engine):
    """Verify turnover below mandatory threshold returns FAIL."""
    req = TurnoverRequirement(
        required_turnover_inr=Decimal("50000000.00"),
        comparison_method="ANNUAL_MINIMUM",
        financial_years_count=3,
    )
    records = [
        {"fiscal_year": "2023-2024", "turnover_inr": 60000000.0},
        {"fiscal_year": "2022-2023", "turnover_inr": 42000000.0},  # Below 5 Cr
        {"fiscal_year": "2021-2022", "turnover_inr": 51000000.0},
    ]
    finding = rule_engine.evaluate_turnover(req, records)
    assert finding.status == "FAIL"
    assert "falls below" in finding.reason.lower()


def test_average_turnover_method(rule_engine):
    """Verify AVERAGE_TURNOVER arithmetic average across years."""
    req = TurnoverRequirement(
        required_turnover_inr=Decimal("40000000.00"),  # 4 Cr avg
        comparison_method="AVERAGE_TURNOVER",
        financial_years_count=3,
    )
    # Total = 30 + 40 + 56 = 126 Cr / 3 = 42 Cr avg => PASS
    records = [
        {"fiscal_year": "2023-2024", "turnover_inr": 56000000.0},
        {"fiscal_year": "2022-2023", "turnover_inr": 40000000.0},
        {"fiscal_year": "2021-2022", "turnover_inr": 30000000.0},
    ]
    finding = rule_engine.evaluate_turnover(req, records)
    assert finding.status == "PASS"
    assert finding.observed_value["average_turnover_inr"] == 42000000.0


def test_missing_turnover_records(rule_engine):
    """Verify missing financial turnover records return MISSING_EVIDENCE."""
    req = TurnoverRequirement(
        required_turnover_inr=Decimal("30000000.00"),
    )
    finding = rule_engine.evaluate_turnover(req, [])
    assert finding.status == "MISSING_EVIDENCE"


# ============================================================================
# Experience Rule Tests
# ============================================================================

def test_experience_satisfied_with_relevant_projects(rule_engine):
    """Verify verified relevant work experience meets threshold."""
    req = ExperienceRequirement(
        min_experience_years=3,
        min_completed_projects=2,
        relevant_domain="Electrical",
    )
    records = [
        {
            "project_title": "Substation 220kV Supply",
            "domain": "Electrical Infrastructure",
            "contract_value_inr": 20000000.0,
            "duration_years": 2.0,
        },
        {
            "project_title": "Transformer Overhaul",
            "domain": "Electrical Services",
            "contract_value_inr": 15000000.0,
            "duration_years": 1.5,
        },
    ]
    finding = rule_engine.evaluate_experience(req, records)
    assert finding.status == "PASS"
    assert finding.observed_value["matching_projects_count"] == 2


def test_irrelevant_domain_projects_fail(rule_engine):
    """Verify projects in unrelated domains are not counted toward relevant experience."""
    req = ExperienceRequirement(
        min_experience_years=3,
        min_completed_projects=1,
        relevant_domain="Electrical",
    )
    records = [
        {
            "project_title": "Highway Road Surfacing",
            "domain": "Civil Infrastructure",  # Unrelated
            "duration_years": 5.0,
        }
    ]
    finding = rule_engine.evaluate_experience(req, records)
    assert finding.status == "FAIL"


def test_incorporation_age_does_not_substitute_project_experience(rule_engine):
    """Verify company incorporation date is NOT counted as relevant project experience."""
    req = ExperienceRequirement(min_experience_years=5, min_completed_projects=2)
    # Company incorporated 10 years ago, but has no project records
    inc_date = date(2014, 1, 1)
    finding = rule_engine.evaluate_experience(req, [], incorporation_date=inc_date)
    assert finding.status == "MISSING_EVIDENCE"


# ============================================================================
# Certification Rule Tests
# ============================================================================

def test_active_certification_pass(rule_engine):
    """Verify active matching certificate returns PASS."""
    req = CertificationRequirement(name="ISO 9001:2015")
    future_date = (datetime.now(timezone.utc) + timedelta(days=365)).date().isoformat()
    certs = [{"name": "ISO 9001:2015", "valid_until": future_date, "issuing_authority": "TUV Nord"}]

    finding = rule_engine.evaluate_certification(req, certs)
    assert finding.status == "PASS"


def test_expired_certification_fail(rule_engine):
    """Verify expired certificate fails deterministic verification."""
    req = CertificationRequirement(name="ISO 9001:2015")
    past_date = (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()
    certs = [{"name": "ISO 9001:2015", "valid_until": past_date}]

    finding = rule_engine.evaluate_certification(req, certs)
    assert finding.status == "FAIL"
    assert "expired" in finding.reason.lower()


def test_missing_certification_missing_evidence(rule_engine):
    """Verify missing certification returns MISSING_EVIDENCE."""
    req = CertificationRequirement(name="CPRI Type Test Certificate")
    finding = rule_engine.evaluate_certification(req, [])
    assert finding.status == "MISSING_EVIDENCE"


# ============================================================================
# Deadline Rule Tests
# ============================================================================

def test_active_future_deadline_pass(rule_engine):
    """Verify future deadline returns PASS."""
    future = datetime.now(timezone.utc) + timedelta(days=10)
    req = DeadlineRequirement(submission_deadline_utc=future)
    finding = rule_engine.evaluate_deadline(req)
    assert finding.status == "PASS"


def test_past_deadline_fail(rule_engine):
    """Verify past deadline returns FAIL."""
    past = datetime.now(timezone.utc) - timedelta(days=2)
    req = DeadlineRequirement(submission_deadline_utc=past)
    finding = rule_engine.evaluate_deadline(req)
    assert finding.status == "FAIL"
    assert "closed" in finding.reason.lower()
