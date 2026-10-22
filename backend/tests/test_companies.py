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
