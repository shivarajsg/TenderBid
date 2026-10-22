from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import TokenResponse, UserLoginRequest, UserRegisterRequest
from app.schemas.common import ResponseEnvelope
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService, AuthenticationError, UserConflictError

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])


@router.post(
    "/register",
    response_model=ResponseEnvelope[UserResponse],
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: UserRegisterRequest,
    session: AsyncSession = Depends(get_db),
):
    """Public registration for MSME accounts with Argon2 password hashing."""
    service = AuthService(session)
    try:
        user_resp = await service.register(request)
        return ResponseEnvelope(
            success=True,
            message="Account registered successfully",
            data=user_resp,
        )
    except UserConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.post(
    "/login",
    response_model=ResponseEnvelope[TokenResponse],
    status_code=status.HTTP_200_OK,
)
async def login(
    request: UserLoginRequest,
    session: AsyncSession = Depends(get_db),
):
    """Authenticate credentials and issue signed JWT access token."""
    service = AuthService(session)
    try:
        token_resp = await service.login(request)
        return ResponseEnvelope(
            success=True,
            message="Authentication successful",
            data=token_resp,
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get(
    "/me",
    response_model=ResponseEnvelope[UserResponse],
    status_code=status.HTTP_200_OK,
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Retrieve profile and role information for the authenticated user."""
    company_id = current_user.company.id if current_user.company else None
    user_resp = UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        company_id=company_id,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )
    return ResponseEnvelope(
        success=True,
        data=user_resp,
    )
