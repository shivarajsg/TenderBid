import pytest
from httpx import AsyncClient
from app.core.security import verify_password, UserRole
from app.db.repositories.users import UserRepository
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_admin_provisioning_logic(db_session: AsyncSession):
    """Verify administrator provisioning creates an ADMIN role with hashed credentials."""
    user_repo = UserRepository(db_session)
    from app.core.security import hash_password

    admin_email = "admin.root@tenderplatform.internal"
    admin_pw = "SuperSecureAdminSecret2026!"
    hashed_pw = hash_password(admin_pw)

    admin_user = await user_repo.create(
        email=admin_email,
        hashed_password=hashed_pw,
        full_name="Platform Administrator",
        role=UserRole.ADMIN.value,
    )
    assert admin_user.role == "ADMIN"
    assert verify_password(admin_pw, admin_user.hashed_password) is True

    # Verify duplicate is detected
    dup = await user_repo.get_by_email(admin_email)
    assert dup is not None
    assert dup.id == admin_user.id


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """Verify standard user registration with Argon2 hashing."""
    payload = {
        "email": "msme.user@example.com",
        "password": "StrongPassword123!",
        "full_name": "Ramesh Kumar",
        "company_name": "Kumar Precision Components",
        "registration_number": "UDYAM-MH-01-998877",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["email"] == "msme.user@example.com"
    assert body["data"]["role"] == "MSME_USER"
    assert "hashed_password" not in body["data"]


@pytest.mark.asyncio
async def test_register_duplicate_email_rejected(client: AsyncClient):
    """Verify duplicate email registration is rejected with 409 Conflict."""
    payload = {
        "email": "duplicate@example.com",
        "password": "StrongPassword123!",
        "full_name": "Test User",
    }
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    body = res2.json()
    assert body["success"] is False


@pytest.mark.asyncio
async def test_register_validation_failure(client: AsyncClient):
    """Verify weak password (<8 chars) is rejected with 422 Unprocessable Entity."""
    payload = {
        "email": "invalid@example.com",
        "password": "short",
        "full_name": "Short Pass User",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Verify login with correct credentials yields signed JWT token."""
    register_payload = {
        "email": "login.user@example.com",
        "password": "ValidPassword123!",
        "full_name": "Login User",
    }
    await client.post("/api/v1/auth/register", json=register_payload)

    login_payload = {
        "email": "login.user@example.com",
        "password": "ValidPassword123!",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "access_token" in body["data"]
    assert body["data"]["token_type"] == "bearer"
    assert body["data"]["user"]["email"] == "login.user@example.com"


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient):
    """Verify login with wrong password fails with generic error."""
    register_payload = {
        "email": "wrongpass@example.com",
        "password": "ValidPassword123!",
        "full_name": "User",
    }
    await client.post("/api/v1/auth/register", json=register_payload)

    login_payload = {
        "email": "wrongpass@example.com",
        "password": "IncorrectPassword999!",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["message"]


@pytest.mark.asyncio
async def test_get_current_user_profile(client: AsyncClient):
    """Verify /auth/me returns authenticated user details."""
    reg = {
        "email": "me.test@example.com",
        "password": "ValidPassword123!",
        "full_name": "Me User",
    }
    await client.post("/api/v1/auth/register", json=reg)

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "me.test@example.com", "password": "ValidPassword123!"},
    )
    token = login_res.json()["data"]["access_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["email"] == "me.test@example.com"


@pytest.mark.asyncio
async def test_public_registration_cannot_escalate_privileges(client: AsyncClient):
    """Verify public registration cannot grant administrator privileges."""
    payload = {
        "email": "hacker@example.com",
        "password": "Password123!",
        "full_name": "Privilege Escalation Attempt",
        "role": "ADMIN",  # Attempting to inject ADMIN role
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["data"]["role"] == "MSME_USER"  # Must strictly remain MSME_USER


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(client: AsyncClient):
    """Verify protected endpoints reject requests without token with 401."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
