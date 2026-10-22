from datetime import date
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
    UserRole,
)
from app.db.repositories.companies import CompanyRepository
from app.db.repositories.users import UserRepository
from app.models.user import User
from app.schemas.auth import TokenResponse, UserLoginRequest, UserRegisterRequest
from app.schemas.user import UserResponse

settings = get_settings()


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class UserConflictError(Exception):
    """Raised when a user registration encounters a duplicate email."""
    pass


class AuthService:
    """Service orchestrating user identity, password hashing, and token issuance."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.company_repo = CompanyRepository(session)

    async def register(self, request: UserRegisterRequest) -> UserResponse:
        """Register a new MSME account, optionally initializing an associated company."""
        existing_user = await self.user_repo.get_by_email(request.email)
        if existing_user:
            raise UserConflictError("An account with this email address already exists")

        # Public registrations are strictly MSME_USER; never allow privilege escalation to ADMIN
        hashed_pw = hash_password(request.password)
        user = await self.user_repo.create(
            email=request.email,
            hashed_password=hashed_pw,
            full_name=request.full_name,
            role=UserRole.MSME_USER.value,
        )

        # If company credentials provided during sign-up, create associated company
        company_id = None
        if request.company_name and request.registration_number:
            existing_company = await self.company_repo.get_by_registration_number(
                request.registration_number
            )
            if existing_company:
                raise UserConflictError("A company with this registration number already exists")

            company = await self.company_repo.create(
                owner_id=user.id,
                legal_name=request.company_name,
                registration_number=request.registration_number,
                business_type="SMALL",
                sector="General",
                incorporation_date=date.today(),
            )
            company_id = company.id

        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            company_id=company_id,
            is_active=user.is_active,
            created_at=user.created_at,
        )

    async def login(self, request: UserLoginRequest) -> TokenResponse:
        """Authenticate user credentials and issue signed JWT access token."""
        user = await self.user_repo.get_by_email(request.email)
        generic_error = "Invalid email or password"

        if not user or not user.is_active:
            raise AuthenticationError(generic_error)

        if not verify_password(request.password, user.hashed_password):
            raise AuthenticationError(generic_error)

        company_id = user.company.id if user.company else None

        token = create_access_token(
            subject=str(user.id),
            role=user.role,
            company_id=str(company_id) if company_id else None,
        )

        user_resp = UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            company_id=company_id,
            is_active=user.is_active,
            created_at=user.created_at,
        )

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_resp,
        )
