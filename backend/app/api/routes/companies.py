from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.company import (
    CompanyCreateRequest,
    CompanyResponse,
    CompanyUpdateRequest,
)
from app.services.company_service import (
    CompanyConflictError,
    CompanyNotFoundError,
    CompanyService,
)

router = APIRouter(prefix="/company", tags=["Company Profile"])


@router.get(
    "/profile",
    response_model=ResponseEnvelope[CompanyResponse],
    status_code=status.HTTP_200_OK,
)
async def get_my_company_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve the authenticated MSME company profile and financial metrics."""
    service = CompanyService(session)
    try:
        profile = await service.get_by_user(current_user)
        return ResponseEnvelope(
            success=True,
            data=profile,
        )
    except CompanyNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post(
    "/profile",
    response_model=ResponseEnvelope[CompanyResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_my_company_profile(
    request: CompanyCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Create a company profile for the authenticated MSME account."""
    service = CompanyService(session)
    try:
        profile = await service.create_profile(current_user, request)
        return ResponseEnvelope(
            success=True,
            message="Company profile created successfully",
            data=profile,
        )
    except CompanyConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.put(
    "/profile",
    response_model=ResponseEnvelope[CompanyResponse],
    status_code=status.HTTP_200_OK,
)
async def update_my_company_profile(
    request: CompanyUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Update company details, turnover figures, or credentials."""
    service = CompanyService(session)
    try:
        profile = await service.update_profile(current_user, request)
        return ResponseEnvelope(
            success=True,
            message="Company profile updated successfully",
            data=profile,
        )
    except CompanyNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except CompanyConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
