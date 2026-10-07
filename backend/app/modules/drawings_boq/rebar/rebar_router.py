from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies.permissions import require_permission
from app.modules.drawings_boq.finish_schedule.schemas import BulkReviewRequest, BulkReviewResponse, ConfirmImportRequest
from app.modules.drawings_boq.rebar.rebar_service import RebarService
from app.modules.drawings_boq.schemas import (
  BarMarkResponse, BarSizeCreateRequest, BarSizeResponse, RebarConfirmResponse, RebarImportResponse, RebarScheduleRowResponse,
  RebarScheduleRowUpdateRequest, RebarShapeCreateRequest, RebarShapeResponse, RebarSummaryResponse,
)
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from pydantic import BaseModel, Field

router = APIRouter(prefix="/drawings-boq", tags=["Reinforcement"])

class RebarFromPdfRequest(BaseModel):
  drawing_id: UUID
  notes: str | None = Field(default=None, max_length=2000)

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

@router.get("/rebar/shapes", response_model=list[RebarShapeResponse])
async def list_rebar_shapes(current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)), session: AsyncSession = Depends(get_db)):
  return await RebarService(session).list_shapes(_org(current_user))

@router.post("/rebar/shapes", response_model=RebarShapeResponse, status_code=201)
async def create_rebar_shape(payload: RebarShapeCreateRequest, current_user: User = Depends(require_permission(PermissionKey.RULESET_MANAGE)),
  session: AsyncSession = Depends(get_db)):
  return await RebarService(session).create_shape(_org(current_user), current_user.id, payload)

@router.get("/rebar/bar-sizes", response_model=list[BarSizeResponse])
async def list_bar_sizes(current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)), session: AsyncSession = Depends(get_db)):
  return await RebarService(session).list_sizes(_org(current_user))

@router.post("/rebar/bar-sizes", response_model=BarSizeResponse, status_code=201)
async def create_bar_size(payload: BarSizeCreateRequest, current_user: User = Depends(require_permission(PermissionKey.RULESET_MANAGE)),
  session: AsyncSession = Depends(get_db)):
  return await RebarService(session).create_size(_org(current_user), current_user.id, payload)

@router.post("/projects/{project_id}/rebar-imports/file", response_model=RebarImportResponse, status_code=201)
async def import_rebar_file(project_id: UUID, file: UploadFile = File(...), notes: str | None = Form(default=None),
  current_user: User = Depends(require_permission(PermissionKey.SCHEDULE_IMPORT)), session: AsyncSession = Depends(get_db)):
  return await RebarService(session).create_from_file(_org(current_user), project_id, current_user.id, file, notes)

@router.post("/projects/{project_id}/rebar-imports/from-pdf", response_model=RebarImportResponse, status_code=201)
async def import_rebar_from_pdf(project_id: UUID, payload: RebarFromPdfRequest,
  current_user: User = Depends(require_permission(PermissionKey.SCHEDULE_IMPORT)), session: AsyncSession = Depends(get_db)):
  return await RebarService(session).create_from_pdf(_org(current_user), project_id, current_user.id, payload.drawing_id, payload.notes)

@router.get("/rebar-imports/{import_id}", response_model=RebarImportResponse)
async def get_rebar_import(import_id: UUID, current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db)):
  return await RebarService(session).get_import(_org(current_user), import_id)

@router.patch("/rebar-rows/{row_id}", response_model=RebarScheduleRowResponse)
async def update_rebar_row(row_id: UUID, payload: RebarScheduleRowUpdateRequest,
  current_user: User = Depends(require_permission(PermissionKey.SCHEDULE_IMPORT)), session: AsyncSession = Depends(get_db)):
  return await RebarService(session).update_row(_org(current_user), row_id, current_user.id, payload)

@router.post("/rebar-imports/{import_id}/rows/bulk-review", response_model=BulkReviewResponse)
async def bulk_review_rebar_rows(import_id: UUID, payload: BulkReviewRequest,
  current_user: User = Depends(require_permission(PermissionKey.SCHEDULE_IMPORT)), session: AsyncSession = Depends(get_db)):
  return await RebarService(session).bulk_review(_org(current_user), import_id, current_user.id, payload.row_ids, payload.review_status)

@router.post("/rebar-imports/{import_id}/confirm", response_model=RebarConfirmResponse)
async def confirm_rebar_import(import_id: UUID, payload: ConfirmImportRequest | None = None,
  current_user: User = Depends(require_permission(PermissionKey.SCHEDULE_IMPORT)), session: AsyncSession = Depends(get_db)):
  return await RebarService(session).confirm_import(_org(current_user), import_id, current_user.id, payload.reject_pending if payload else False)

@router.post("/rebar-imports/{import_id}/reject", response_model=RebarConfirmResponse)
async def reject_rebar_import(import_id: UUID, current_user: User = Depends(require_permission(PermissionKey.SCHEDULE_IMPORT)),
  session: AsyncSession = Depends(get_db)):
  return await RebarService(session).reject_import(_org(current_user), import_id, current_user.id)

@router.post("/rebar-imports/{import_id}/archive", response_model=RebarConfirmResponse)
async def archive_rebar_import(import_id: UUID, current_user: User = Depends(require_permission(PermissionKey.SCHEDULE_IMPORT)),
  session: AsyncSession = Depends(get_db)):
  return await RebarService(session).archive_import(_org(current_user), import_id, current_user.id)

@router.get("/calculation-runs/{run_id}/bar-marks", response_model=list[BarMarkResponse])
async def list_run_bar_marks(run_id: UUID, response: Response, limit: int = Query(default=500, ge=1, le=2000),
  after: UUID | None = Query(default=None), provenance: str | None = Query(default=None, max_length=20),
  role: str | None = Query(default=None, max_length=50),
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)), session: AsyncSession = Depends(get_db)):
  rows, nxt = await RebarService(session).list_bar_marks(_org(current_user), run_id, limit=limit, after=after, provenance=provenance, role=role)
  if nxt:
    response.headers["X-Next-Cursor"] = str(nxt)
  return rows

@router.get("/boq-versions/{boq_version_id}/rebar-summary", response_model=RebarSummaryResponse)
async def get_rebar_summary(boq_version_id: UUID, current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db)):
  return await RebarService(session).summary(_org(current_user), boq_version_id)
