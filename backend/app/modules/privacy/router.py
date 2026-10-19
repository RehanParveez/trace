from __future__ import annotations
from fastapi import APIRouter, Depends, Request, status
from app.modules.identity.models import User
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.privacy.service import PrivacyService, grant_response
from app.modules.privacy.schemas import SupportGrantResponse, DeletionRequestCreate, DeletionRequestResponse, ExportDownloadResponse, ExportJobResponse, PrivacyOverviewResponse, SupportDiagnosticsResponse, SupportGrantCreateRequest
from app.modules.identity.enums import PermissionKey
from app.modules.privacy.diagnostics import SupportDiagnostics
from app.dependencies.permissions import require_permission, require_platform_admin
from app.core.database import get_db

router = APIRouter(prefix="/privacy", tags=["Data privacy"])

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

def _ip(request: Request) -> str | None:
  return request.client.host if request.client else None

def _service(session: AsyncSession) -> PrivacyService:
  return PrivacyService(session)

MANAGE = PermissionKey.ORGANIZATION_MANAGE

@router.get("/overview", response_model=PrivacyOverviewResponse)
async def overview(current_user: User = Depends(require_permission(MANAGE)), session: AsyncSession = Depends(get_db)):
  return await _service(session).overview(_org(current_user))

@router.get("/support-grants", response_model=list[SupportGrantResponse])
async def list_support_grants(current_user: User = Depends(require_permission(MANAGE)), session: AsyncSession = Depends(get_db)):
  return [grant_response(g) for g in await _service(session).list_grants(_org(current_user))]

@router.post("/support-grants", response_model=SupportGrantResponse, status_code=status.HTTP_201_CREATED)
async def create_support_grant(payload: SupportGrantCreateRequest, request: Request, current_user: User = Depends(require_permission(MANAGE)),
  session: AsyncSession = Depends(get_db)):
  grant = await _service(session).create_grant(_org(current_user), current_user.id, payload.reason, payload.hours, _ip(request))
  return grant_response(grant)

@router.post("/support-grants/{grant_id}/revoke", response_model=SupportGrantResponse)
async def revoke_support_grant(grant_id: UUID, request: Request, current_user: User = Depends(require_permission(MANAGE)),
  session: AsyncSession = Depends(get_db)):
  grant = await _service(session).revoke_grant(_org(current_user), current_user.id, grant_id, _ip(request))
  return grant_response(grant)

@router.get("/exports", response_model=list[ExportJobResponse])
async def list_exports(current_user: User = Depends(require_permission(MANAGE)), session: AsyncSession = Depends(get_db)):
  return await _service(session).list_exports(_org(current_user))

@router.post("/exports", response_model=ExportJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def request_export(request: Request, current_user: User = Depends(require_permission(MANAGE)), session: AsyncSession = Depends(get_db)):
  return await _service(session).request_export(_org(current_user), current_user.id, _ip(request))

@router.get("/exports/{job_id}/download", response_model=ExportDownloadResponse)
async def export_download(job_id: UUID, request: Request, current_user: User = Depends(require_permission(MANAGE)), session: AsyncSession = Depends(get_db)):
  url, ttl = await _service(session).download_link(_org(current_user), current_user.id, job_id, _ip(request))
  return ExportDownloadResponse(url=url, expires_in_seconds=ttl)

@router.get("/deletion-request", response_model=DeletionRequestResponse | None)
async def get_deletion_request(current_user: User = Depends(require_permission(MANAGE)), session: AsyncSession = Depends(get_db)):
  return await _service(session).pending_deletion(_org(current_user))

@router.post("/deletion-request", response_model=DeletionRequestResponse, status_code=status.HTTP_201_CREATED)
async def request_deletion(payload: DeletionRequestCreate, request: Request, current_user: User = Depends(require_permission(MANAGE)),
  session: AsyncSession = Depends(get_db)):
  return await _service(session).request_deletion(_org(current_user), current_user.id, payload.confirm_name, payload.reason, _ip(request))

@router.post("/deletion-request/cancel", response_model=DeletionRequestResponse)
async def cancel_deletion(request: Request, current_user: User = Depends(require_permission(MANAGE)), session: AsyncSession = Depends(get_db)):
  return await _service(session).cancel_deletion(_org(current_user), current_user.id, _ip(request))

@router.get("/admin/support/{organization_id}/diagnostics", response_model=SupportDiagnosticsResponse)
async def support_diagnostics(organization_id: UUID, request: Request, admin: User = Depends(require_platform_admin()), session: AsyncSession = Depends(get_db)):
  return await SupportDiagnostics(session).summary(organization_id, admin.id, admin.email, _ip(request))