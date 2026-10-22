import pytest
from httpx import AsyncClient


async def get_auth_token(client: AsyncClient, email: str) -> str:
    """Helper creating user and returning JWT token."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "full_name": "Test Company Owner"},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    return login_res.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_create_and_get_company_profile(client: AsyncClient):
    """Verify MSME user can create and retrieve company profile."""
    token = await get_auth_token(client, "owner1@company.com")
    headers = {"Authorization": f"Bearer {token}"}

    create_payload = {
        "legal_name": "Apex Engineering Solutions Pvt Ltd",
        "registration_number": "UDYAM-DL-01-0012345",
        "business_type": "SMALL",
        "sector": "Precision Fabrication",
        "incorporation_date": "2018-04-10",
        "annual_turnover": [
            {"fiscal_year": "2023-2024", "turnover_inr": 25000000.0, "currency": "INR"},
            {"fiscal_year": "2024-2025", "turnover_inr": 31000000.0, "currency": "INR"},
        ],
        "certifications": [
            {"name": "ISO 9001:2015", "issuing_authority": "BSI"}
        ],
        "work_experience": [
            {"project_title": "Supply of CNC Flanges", "client_name": "BHEL", "contract_value_inr": 8500000.0}
        ],
    }

    create_res = await client.post("/api/v1/company/profile", json=create_payload, headers=headers)
    assert create_res.status_code == 201
    body = create_res.json()
    assert body["success"] is True
    assert body["data"]["legal_name"] == "Apex Engineering Solutions Pvt Ltd"
    assert body["data"]["years_in_business"] >= 7

    # Retrieve profile
    get_res = await client.get("/api/v1/company/profile", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["registration_number"] == "UDYAM-DL-01-0012345"


@pytest.mark.asyncio
async def test_update_company_profile(client: AsyncClient):
    """Verify company profile can be updated."""
    token = await get_auth_token(client, "update_owner@company.com")
    headers = {"Authorization": f"Bearer {token}"}

    create_payload = {
        "legal_name": "Beta Labs",
        "registration_number": "UDYAM-KA-02-0054321",
        "business_type": "MICRO",
        "sector": "Information Technology",
        "incorporation_date": "2020-01-01",
    }
    await client.post("/api/v1/company/profile", json=create_payload, headers=headers)

    update_payload = {
        "legal_name": "Beta Labs Advanced Technologies",
        "business_type": "SMALL",
    }
    update_res = await client.put("/api/v1/company/profile", json=update_payload, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json()["data"]["legal_name"] == "Beta Labs Advanced Technologies"
    assert update_res.json()["data"]["business_type"] == "SMALL"


@pytest.mark.asyncio
async def test_cross_company_isolation(client: AsyncClient):
    """Verify Tenant A cannot access or modify Tenant B's company data."""
    token_a = await get_auth_token(client, "tenant_a@msme.com")
    token_b = await get_auth_token(client, "tenant_b@msme.com")

    # Tenant A creates company
    await client.post(
        "/api/v1/company/profile",
        json={
            "legal_name": "Tenant A Enterprises",
            "registration_number": "UDYAM-TN-01-111111",
            "business_type": "SMALL",
            "sector": "Textiles",
            "incorporation_date": "2015-05-15",
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )

    # Tenant B tries to get profile before creating their own
    res_b = await client.get("/api/v1/company/profile", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 404
    assert "not been initialized" in res_b.json()["message"]


@pytest.mark.asyncio
async def test_create_enhanced_company_capability_profile(client: AsyncClient):
    """Verify full 10-section capability profile fields persist and retrieve accurately."""
    token = await get_auth_token(client, "full_profile@msme.com")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "legal_name": "Zenith Defense & Aerospace Pvt Ltd",
        "trade_name": "Zenith Aero",
        "registration_number": "UDYAM-KA-03-9988776",
        "business_type": "SMALL",
        "sector": "Aerospace & Defense Electronics",
        "incorporation_date": "2017-08-15",
        "constitution": "PRIVATE_LIMITED",
        "pan_number": "AAACZ1234D",
        "gstin": "29AAACZ1234D1Z5",
        "udyam_number": "UDYAM-KA-03-9988776",
        "dpiit_recognition_number": "DIPP98765",
        "address": {
            "line1": "Plot 42, Electronic City Phase II",
            "city": "Bengaluru",
            "state": "Karnataka",
            "pincode": "560100",
            "country": "India",
        },
        "contact_details": {
            "signatory_name": "Rajesh Sharma",
            "designation": "Managing Director",
            "email": "contact@zenithaero.com",
            "phone": "+91 9876543210",
        },
        "technical_capabilities": {
            "core_domains": ["Avionics", "Radar Components", "Telemetry Systems"],
            "products": [{"name": "Telemetry Transceiver Unit", "hsn_code": "8526", "capacity_per_month": "100 units"}],
            "services": [{"name": "Environmental Stress Testing", "sac_code": "9983"}],
            "oem_status": "OEM",
            "testing_facilities": "In-house MIL-STD-810G Environmental Screening Chamber with NABL certified calibration.",
            "service_coverage": "PAN_INDIA",
        },
        "workforce_metrics": {
            "total_employees": 45,
            "engineers_count": 22,
            "technicians_count": 14,
            "service_centers_count": 3,
            "emergency_support": True,
        },
        "tender_exemptions": {
            "msme_category": "SMALL",
            "emd_exemption": True,
            "tender_fee_exemption": True,
            "turnover_relaxation": True,
            "experience_relaxation": True,
            "mii_class": "CLASS_1",
            "mii_percentage": 75.0,
        },
        "declarations": {
            "non_blacklisted": True,
            "no_conflict_of_interest": True,
            "mii_compliant": True,
        },
        "annual_turnover": [
            {"fiscal_year": "2021-2022", "turnover_inr": "18000000", "net_worth_inr": "12000000", "profit_after_tax_inr": "2500000"},
            {"fiscal_year": "2022-2023", "turnover_inr": "24000000", "net_worth_inr": "16500000", "profit_after_tax_inr": "3800000"},
            {"fiscal_year": "2023-2024", "turnover_inr": "32000000", "net_worth_inr": "22000000", "profit_after_tax_inr": "5100000"},
        ],
        "certifications": [
            {"name": "ISO 9001:2015", "certificate_number": "ISO-IND-9912", "issuing_authority": "TUV Rheinland", "valid_until": "2027-12-31"},
            {"name": "AS9100D", "certificate_number": "AS-2024-88", "issuing_authority": "DNV", "valid_until": "2026-11-30"},
        ],
        "work_experience": [
            {
                "project_title": "Supply of S-Band Receiver Modules",
                "client_name": "ISRO Telemetry Network",
                "client_type": "CENTRAL_GOVT",
                "contract_value_inr": 12500000.0,
                "status": "COMPLETED",
                "completion_date": "2023-03-20",
            }
        ],
    }

    res = await client.post("/api/v1/company/profile", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["trade_name"] == "Zenith Aero"
    assert data["gstin"] == "29AAACZ1234D1Z5"
    assert data["pan_number"] == "AAACZ1234D"
    assert data["address"]["city"] == "Bengaluru"
    assert data["workforce_metrics"]["engineers_count"] == 22
    assert len(data["annual_turnover"]) == 3
    assert data["annual_turnover"][0]["turnover_inr"] == 18000000.0


@pytest.mark.asyncio
async def test_financial_scientific_notation_and_validation(client: AsyncClient):
    """Verify scientific notation like 1e+25 and invalid strings are rejected."""
    token = await get_auth_token(client, "scientific_test@msme.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Test scientific notation rejection
    bad_payload = {
        "legal_name": "Invalid Financials Corp",
        "registration_number": "UDYAM-DL-09-1234567",
        "business_type": "SMALL",
        "sector": "Finance",
        "incorporation_date": "2020-01-01",
        "annual_turnover": [
            {"fiscal_year": "2023-2024", "turnover_inr": "1e+25", "currency": "INR"}
        ],
    }
    res = await client.post("/api/v1/company/profile", json=bad_payload, headers=headers)
    assert res.status_code == 422
    assert "scientific notation" in res.text.lower()


@pytest.mark.asyncio
async def test_readiness_scoring_and_gap_analysis(client: AsyncClient):
    """Verify data-driven readiness score and missing item checklist."""
    token = await get_auth_token(client, "readiness_owner@msme.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Create profile with complete identity and partial turnover
    create_payload = {
        "legal_name": "Pro Active Systems",
        "registration_number": "UDYAM-MH-01-4455667",
        "business_type": "MICRO",
        "sector": "Renewable Energy",
        "incorporation_date": "2021-06-01",
        "pan_number": "AAABP4455C",
        "gstin": "27AAABP4455C1Z2",
        "annual_turnover": [
            {"fiscal_year": "2023-2024", "turnover_inr": 15000000.0}
        ],
    }
    await client.post("/api/v1/company/profile", json=create_payload, headers=headers)

    res = await client.get("/api/v1/company/readiness", headers=headers)
    assert res.status_code == 200
    readiness = res.json()["data"]
    assert "overall_score" in readiness
    assert "readiness_stage" in readiness
    assert "breakdown" in readiness
    assert len(readiness["satisfied_items"]) > 0
    # Should flag missing 3-year turnover
    missing_items = [m["item"] for m in readiness["missing_items"]]
    assert any("3-Year Turnover" in item for item in missing_items)


@pytest.mark.asyncio
async def test_capability_statement_generation(client: AsyncClient):
    """Verify structured capability statement generation endpoint."""
    token = await get_auth_token(client, "statement_owner@msme.com")
    headers = {"Authorization": f"Bearer {token}"}

    create_payload = {
        "legal_name": "Bharat Solar Infra Pvt Ltd",
        "registration_number": "UDYAM-GJ-04-1122334",
        "business_type": "SMALL",
        "sector": "Solar EPC & Renewable Energy",
        "incorporation_date": "2019-03-15",
        "annual_turnover": [
            {"fiscal_year": "2022-2023", "turnover_inr": 40000000.0},
            {"fiscal_year": "2023-2024", "turnover_inr": 60000000.0},
        ],
    }
    await client.post("/api/v1/company/profile", json=create_payload, headers=headers)

    res = await client.get("/api/v1/company/capability-statement", headers=headers)
    assert res.status_code == 200
    stmt = res.json()["data"]
    assert "summary_text" in stmt
    assert "Bharat Solar Infra" in stmt["summary_text"]
    assert stmt["metrics"]["average_turnover_inr"] == 50000000.0
