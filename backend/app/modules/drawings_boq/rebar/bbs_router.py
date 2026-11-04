from __future__ import annotations
from fastapi import APIRouter, Depends, File, Query, UploadFile
from uuid import UUID
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.rebar.bbs_service import BbsService
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.modules.drawings_boq.rebar.bbs_schemas import AuditRunOut, BbsDetailResponse, BbsDocumentOut, BbsUploadResponse, FindingDecisionRequest, FindingListResponse, FindingOut

router = APIRouter(tags=["Bar bending schedule audit"])
_READ = PermissionKey.DRAWING_READ
_WRITE = PermissionKey.SCHEDULE_IMPORT

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

@router.post("/projects/{project_id}/bbs", response_model=BbsUploadResponse, status_code=201)
async def upload_bbs(project_id: UUID, file: UploadFile = File(...), current_user: User = Depends(require_permission(_WRITE)),
  session: AsyncSession = Depends(get_db)):
  return await BbsService(session).upload(_org(current_user), project_id, current_user.id, file)

@router.get("/projects/{project_id}/bbs", response_model=list[BbsDocumentOut])
async def list_bbs(project_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await BbsService(session).list_documents(_org(current_user), project_id)

@router.get("/bbs/{document_id}", response_model=BbsDetailResponse)
async def get_bbs(document_id: UUID, sheet: int | None = Query(default=None, ge=0), page: int = Query(default=1, ge=1), page_size: int = Query(default=100, ge=1, le=500),
  current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await BbsService(session).get(_org(current_user), document_id, sheet, page, page_size)

@router.post("/bbs/{document_id}/audit", response_model=AuditRunOut, status_code=201)
async def run_bbs_audit(document_id: UUID, current_user: User = Depends(require_permission(_WRITE)), session: AsyncSession = Depends(get_db)):
  return await BbsService(session).run_audit(_org(current_user), document_id, current_user.id)

@router.get("/bbs/{document_id}/audit", response_model=AuditRunOut | None)
async def latest_bbs_audit(document_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await BbsService(session).latest_run(_org(current_user), document_id)

@router.get("/bbs/{document_id}/findings", response_model=FindingListResponse)
async def list_bbs_findings(document_id: UUID, finding_class: str | None = Query(default=None, max_length=14), code: str | None = Query(default=None, max_length=40),
  sheet: int | None = Query(default=None, ge=0), status: str | None = Query(default=None, max_length=10), page: int = Query(default=1, ge=1),
  page_size: int = Query(default=100, ge=1, le=500), current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await BbsService(session).findings(_org(current_user), document_id, finding_class, code, sheet, status, page, page_size)

@router.patch("/findings/{finding_id}", response_model=FindingOut)
async def decide_bbs_finding(finding_id: UUID, payload: FindingDecisionRequest, current_user: User = Depends(require_permission(_WRITE)),
  session: AsyncSession = Depends(get_db)):
  return await BbsService(session).decide(_org(current_user), finding_id, current_user.id, payload.status, payload.reason)
