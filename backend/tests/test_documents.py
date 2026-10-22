import pytest
from httpx import AsyncClient


async def setup_company_user(client: AsyncClient, email: str, reg_no: str) -> str:
    """Helper registering user, creating company, and returning token."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "full_name": "Vault Tester"},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    await client.post(
        "/api/v1/company/profile",
        json={
            "legal_name": f"Company {reg_no}",
            "registration_number": reg_no,
            "business_type": "SMALL",
            "sector": "Manufacturing",
            "incorporation_date": "2019-01-01",
        },
        headers=headers,
    )
    return token


@pytest.mark.asyncio
async def test_register_and_list_documents(client: AsyncClient):
    """Verify document metadata can be registered and listed in vault."""
    token = await setup_company_user(client, "doc_user@vault.com", "UDYAM-MH-02-123456")
    headers = {"Authorization": f"Bearer {token}"}

    doc_payload = {
        "document_category": "FINANCIAL_AUDIT",
        "original_filename": "Audited_Turnover_FY24.pdf",
        "mime_type": "application/pdf",
        "file_size_bytes": 1048576,
        "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "valid_from": "2024-04-01",
        "valid_until": "2025-03-31",
    }
    create_res = await client.post("/api/v1/company/vault/documents", json=doc_payload, headers=headers)
    assert create_res.status_code == 201
    body = create_res.json()
    assert body["success"] is True
    doc_id = body["data"]["id"]
    assert body["data"]["document_category"] == "FINANCIAL_AUDIT"
    assert "storage_path" not in body["data"]  # Protected internal path not exposed

    # List documents
    list_res = await client.get("/api/v1/company/vault/documents", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) >= 1

    # Filter by category
    filter_res = await client.get("/api/v1/company/vault/documents?category=FINANCIAL_AUDIT", headers=headers)
    assert filter_res.status_code == 200
    assert len(filter_res.json()["data"]) >= 1

    # Get single document
    get_res = await client.get(f"/api/v1/company/vault/documents/{doc_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["id"] == doc_id


@pytest.mark.asyncio
async def test_invalid_mime_type_rejected(client: AsyncClient):
    """Verify non-PDF document uploads are rejected."""
    token = await setup_company_user(client, "mime_user@vault.com", "UDYAM-MH-02-987654")
    headers = {"Authorization": f"Bearer {token}"}

    bad_payload = {
        "document_category": "TAX_RECORD",
        "original_filename": "malware.exe",
        "mime_type": "application/x-dosexec",
        "file_size_bytes": 2048,
        "sha256_hash": "a" * 64,
    }
    res = await client.post("/api/v1/company/vault/documents", json=bad_payload, headers=headers)
    assert res.status_code == 400
    assert "Only PDF documents" in res.json()["message"]


@pytest.mark.asyncio
async def test_cross_company_document_isolation(client: AsyncClient):
    """Verify Tenant B cannot view or delete Tenant A's documents."""
    token_a = await setup_company_user(client, "tenant_a_doc@vault.com", "UDYAM-KL-01-111111")
    token_b = await setup_company_user(client, "tenant_b_doc@vault.com", "UDYAM-KL-01-222222")

    # Tenant A creates document
    doc_res = await client.post(
        "/api/v1/company/vault/documents",
        json={
            "document_category": "CERTIFICATION",
            "original_filename": "Confidential_Cert.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 500000,
            "sha256_hash": "b" * 64,
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )
    doc_id = doc_res.json()["data"]["id"]

    # Tenant B tries to access Tenant A's document
    unauth_get = await client.get(
        f"/api/v1/company/vault/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert unauth_get.status_code == 404

    # Tenant B tries to delete Tenant A's document
    unauth_delete = await client.delete(
        f"/api/v1/company/vault/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert unauth_delete.status_code == 404
