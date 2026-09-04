from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies.permissions import require_permission
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from app.modules.verification.models import ProgressClaimStatus
from app.modules.verification.schemas import PhotoBOQLinkCreateRequest, PhotoBOQLinkResponse, ProgressClaimCreateRequest, ProgressClaimResponse, ProgressClaimReviewRequest, ProgressClaimUpdateRequest
from app.modules.verification.service import VerificationService

router = APIRouter(
  prefix="/verification",
  tags=["Verification"],
)

def _service(session: AsyncSession) -> VerificationService:
  return VerificationService(session)

@router.get(
  "/progress-claims",
  response_model=list[ProgressClaimResponse],
)
async def list_progress_claims(
  project_id: UUID | None = Query(default=None),
  claim_status: ProgressClaimStatus | None = Query(
    default=None,
    alias="status",
  ),
  skip: int = Query(default=0, ge=0),
  limit: int = Query(default=100, ge=1, le=100),
  current_user: User = Depends(
    require_permission(PermissionKey.PROGRESS_CLAIM_READ)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.list_claims(
    current_user.active_membership.organization_id,
    project_id=project_id,
    status=claim_status,
    skip=skip,
    limit=limit,
  )

@router.get(
  "/progress-claims/{claim_id}",
  response_model=ProgressClaimResponse,
)
async def get_progress_claim(
  claim_id: UUID,
  current_user: User = Depends(
    require_permission(PermissionKey.PROGRESS_CLAIM_READ)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  return await service.get_claim(
    current_user.active_membership.organization_id,
    claim_id,
  )

@router.post(
  "/progress-claims",
  response_model=ProgressClaimResponse,
  status_code=status.HTTP_201_CREATED,
)
async def create_progress_claim(
  payload: ProgressClaimCreateRequest,
  current_user: User = Depends(
    require_permission(PermissionKey.PROGRESS_CLAIM_CREATE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.create_claim(
    current_user.active_membership.organization_id,
    current_user.id,
    payload,
  )

@router.patch(
  "/progress-claims/{claim_id}",
  response_model=ProgressClaimResponse,
)
async def update_progress_claim(
  claim_id: UUID,
  payload: ProgressClaimUpdateRequest,
  current_user: User = Depends(
    require_permission(PermissionKey.PROGRESS_CLAIM_UPDATE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  return await service.update_claim(
    current_user.active_membership.organization_id,
    claim_id,
    payload,
  )

@router.post(
  "/progress-claims/{claim_id}/submit",
  response_model=ProgressClaimResponse,
)
async def submit_progress_claim(
  claim_id: UUID,
  current_user: User = Depends(
    require_permission(PermissionKey.PROGRESS_CLAIM_SUBMIT)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  return await service.submit_claim(
    current_user.active_membership.organization_id,
    claim_id,
    current_user.id,
  )

@router.post(
  "/progress-claims/{claim_id}/approve",
  response_model=ProgressClaimResponse,
)
async def approve_progress_claim(
  claim_id: UUID,
  payload: ProgressClaimReviewRequest,
  current_user: User = Depends(
    require_permission(PermissionKey.PROGRESS_CLAIM_REVIEW)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  return await service.approve_claim(
    current_user.active_membership.organization_id,
    claim_id,
    current_user.id,
    payload,
  )

@router.post(
  "/progress-claims/{claim_id}/reject",
  response_model=ProgressClaimResponse,
)
async def reject_progress_claim(
  claim_id: UUID,
  payload: ProgressClaimReviewRequest,
  current_user: User = Depends(
    require_permission(PermissionKey.PROGRESS_CLAIM_REVIEW)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  return await service.reject_claim(
    current_user.active_membership.organization_id,
    claim_id,
    current_user.id,
    payload,
  )

@router.get(
  "/photo-boq-links",
  response_model=list[PhotoBOQLinkResponse],
)
async def list_photo_boq_links(
  project_id: UUID | None = Query(default=None),
  progress_claim_id: UUID | None = Query(default=None),
  site_photo_id: UUID | None = Query(default=None),
  boq_item_id: UUID | None = Query(default=None),
  skip: int = Query(default=0, ge=0),
  limit: int = Query(default=100, ge=1, le=100),
  current_user: User = Depends(
    require_permission(PermissionKey.PHOTO_BOQ_LINK_READ)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  return await service.list_photo_boq_links(
    current_user.active_membership.organization_id,
    project_id=project_id,
    progress_claim_id=progress_claim_id,
    site_photo_id=site_photo_id,
    boq_item_id=boq_item_id,
    skip=skip,
    limit=limit,
  )

@router.post(
  "/photo-boq-links",
  response_model=PhotoBOQLinkResponse,
  status_code=status.HTTP_201_CREATED,
)
async def create_photo_boq_link(
  payload: PhotoBOQLinkCreateRequest,
  current_user: User = Depends(
    require_permission(PermissionKey.PHOTO_BOQ_LINK_MANAGE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  return await service.create_photo_boq_link(
    current_user.active_membership.organization_id,
    current_user.id,
    payload,
  )

@router.delete(
  "/photo-boq-links/{link_id}",
  status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_photo_boq_link(
  link_id: UUID,
  current_user: User = Depends(
    require_permission(PermissionKey.PHOTO_BOQ_LINK_MANAGE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  await service.delete_photo_boq_link(
    current_user.active_membership.organization_id,
    link_id,
  )