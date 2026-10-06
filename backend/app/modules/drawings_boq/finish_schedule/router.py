from __future__ import annotations
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from app.core.database import get_db
from app.modules.identity.models import User
from uuid import UUID
from app.modules.identity.enums import PermissionKey
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.space_service import SpaceService
from app.dependencies.permissions import require_permission
from app.modules.drawings_boq.finish_schedule.schemas import (BulkReviewRequest, BulkReviewResponse, ConfirmImportRequest, ConfirmImportResponse, FinishPreviewResponse, NoteRequest, ScheduleFromPdfRequest, ScheduleImportDetailResponse,
  ScheduleImportResponse, ScheduleKind, ScheduleManualCreateRequest, ScheduleRowCreateRequest, ScheduleRowResponse, ScheduleRowUpdateRequest, SpaceBoundariesRequest, SpaceCreateRequest, 
  SpaceDetailResponse, SpaceFinishCreateRequest, SpaceFinishResponse, SpaceResponse, SpaceUpdateRequest,
)
from app.modules.drawings_boq.schedule_service import ScheduleService

router = APIRouter()

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

@router.get("/projects/{project_id}/spaces", response_model=list[SpaceResponse])
async def list_spaces(
  project_id: UUID, drawing_id: UUID | None = Query(default=None), level_id: UUID | None = Query(default=None),
  category: str | None = Query(default=None, max_length=40), include_inactive: bool = Query(default=False),
  current_only: bool = Query(default=True),
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)), session: AsyncSession = Depends(get_db),
):
  return await SpaceService(session).list_spaces(_org(current_user), project_id, drawing_id=drawing_id,
    level_id=level_id, category=category, include_inactive=include_inactive, current_only=current_only)

@router.post("/projects/{project_id}/spaces", response_model=SpaceResponse, status_code=201)
async def create_space(
  project_id: UUID, payload: SpaceCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.SPACE_MANAGE)), session: AsyncSession = Depends(get_db),
):
  return await SpaceService(session).create_space(_org(current_user), project_id, current_user.id, payload)

@router.get("/spaces/{space_id}", response_model=SpaceDetailResponse)
async def get_space(
  space_id: UUID, current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await SpaceService(session).get_detail(_org(current_user), space_id)

@router.patch("/spaces/{space_id}", response_model=SpaceResponse)
async def update_space(
  space_id: UUID, payload: SpaceUpdateRequest,
  current_user: User = Depends(require_permission(PermissionKey.SPACE_MANAGE)), session: AsyncSession = Depends(get_db),
):
  return await SpaceService(session).update_space(_org(current_user), space_id, current_user.id, payload)

@router.delete("/spaces/{space_id}", status_code=204)
async def delete_space(
  space_id: UUID, current_user: User = Depends(require_permission(PermissionKey.SPACE_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  await SpaceService(session).delete_space(_org(current_user), space_id, current_user.id)

@router.put("/spaces/{space_id}/boundaries")
async def set_space_boundaries(
  space_id: UUID, payload: SpaceBoundariesRequest,
  current_user: User = Depends(require_permission(PermissionKey.SPACE_MANAGE)), session: AsyncSession = Depends(get_db),
):
  count = await SpaceService(session).set_boundaries(_org(current_user), space_id, current_user.id, payload.element_ids)
  return {"boundary_count": count}

@router.get("/spaces/{space_id}/finishes", response_model=list[SpaceFinishResponse])
async def list_space_finishes(
  space_id: UUID, current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await SpaceService(session).list_finishes(_org(current_user), space_id)

@router.post("/spaces/{space_id}/finishes", response_model=SpaceFinishResponse, status_code=201)
async def set_space_finish(
  space_id: UUID, payload: SpaceFinishCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.FINISH_MANAGE)), session: AsyncSession = Depends(get_db),
):
  return await SpaceService(session).upsert_finish(_org(current_user), space_id, current_user.id, payload)

@router.delete("/space-finishes/{finish_id}", status_code=204)
async def delete_space_finish(
  finish_id: UUID, current_user: User = Depends(require_permission(PermissionKey.FINISH_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  await SpaceService(session).delete_finish(_org(current_user), finish_id, current_user.id)

@router.get("/spaces/{space_id}/finish-preview", response_model=FinishPreviewResponse)
async def preview_space_finishes(
  space_id: UUID, rule_set_code: str | None = Query(default=None, max_length=50),
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)), session: AsyncSession = Depends(get_db),
):
  return await SpaceService(session).preview_finishes(_org(current_user), space_id, rule_set_code)

@router.get("/projects/{project_id}/schedule-imports", response_model=list[ScheduleImportResponse])
async def list_schedule_imports(
  project_id: UUID, status: str | None = Query(default=None, max_length=20),
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)), session: AsyncSession = Depends(get_db),
):
  return await ScheduleService(session).list_imports(_org(current_user), project_id, status)

@router.post("/projects/{project_id}/schedule-imports/file", response_model=ScheduleImportResponse, status_code=201)
async def import_schedule_file(
  project_id: UUID, file: UploadFile = File(...), schedule_kind: ScheduleKind = Form(...),
  notes: str | None = Form(default=None),
  current_user: User = Depends(require_permission(PermissionKey.SCHEDULE_IMPORT)), session: AsyncSession = Depends(get_db),
):
  return await ScheduleService(session).create_from_file(_org(current_user), project_id, current_user.id,
    schedule_kind, file, notes)

@router.post("/projects/{project_id}/schedule-imports/from-pdf", response_model=ScheduleImportResponse, status_code=201)
async def import_schedule_from_pdf(
  project_id: UUID, payload: ScheduleFromPdfRequest,
  current_user: User = Depends(require_permission(PermissionKey.SCHEDULE_IMPORT)), session: AsyncSession = Depends(get_db),
):
  return await ScheduleService(session).create_from_pdf(_org(current_user), project_id, current_user.id,
    payload.drawing_id, payload.schedule_kind, payload.notes, payload.method)

@router.post("/projects/{project_id}/schedule-imports", response_model=ScheduleImportResponse, status_code=201)
async def create_manual_schedule_import(
  project_id: UUID, payload: ScheduleManualCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.SCHEDULE_IMPORT)), session: AsyncSession = Depends(get_db),
):
  return await ScheduleService(session).create_manual(_org(current_user), project_id, current_user.id,
    payload.schedule_kind, payload.notes)

@router.get("/schedule-imports/{import_id}", response_model=ScheduleImportDetailResponse)
async def get_schedule_import(
  import_id: UUID, current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await ScheduleService(session).get_detail(_org(current_user), import_id)

@router.post("/schedule-imports/{import_id}/rows", response_model=ScheduleRowResponse, status_code=201)
async def add_schedule_row(
  import_id: UUID, payload: ScheduleRowCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.SCHEDULE_IMPORT)), session: AsyncSession = Depends(get_db),
):
  return await ScheduleService(session).add_row(_org(current_user), import_id, current_user.id, payload)

@router.patch("/schedule-rows/{row_id}", response_model=ScheduleRowResponse)
async def update_schedule_row(
  row_id: UUID, payload: ScheduleRowUpdateRequest,
  current_user: User = Depends(require_permission(PermissionKey.SCHEDULE_IMPORT)), session: AsyncSession = Depends(get_db),
):
  return await ScheduleService(session).update_row(_org(current_user), row_id, current_user.id, payload)

@router.post("/schedule-imports/{import_id}/rows/bulk-review", response_model=BulkReviewResponse)
async def bulk_review_schedule_rows(
  import_id: UUID, payload: BulkReviewRequest,
  current_user: User = Depends(require_permission(PermissionKey.SCHEDULE_IMPORT)), session: AsyncSession = Depends(get_db),
):
  return await ScheduleService(session).bulk_review(_org(current_user), import_id, current_user.id,
    payload.row_ids, payload.review_status)

@router.post("/schedule-imports/{import_id}/confirm", response_model=ConfirmImportResponse)
async def confirm_schedule_import(
  import_id: UUID, payload: ConfirmImportRequest | None = None,
  current_user: User = Depends(require_permission(PermissionKey.SCHEDULE_IMPORT)), session: AsyncSession = Depends(get_db),
):
  return await ScheduleService(session).confirm_import(_org(current_user), import_id, current_user.id,
    payload.reject_pending if payload else False)

@router.post("/schedule-imports/{import_id}/reject", response_model=ScheduleImportResponse)
async def reject_schedule_import(
  import_id: UUID, payload: NoteRequest | None = None,
  current_user: User = Depends(require_permission(PermissionKey.SCHEDULE_IMPORT)), session: AsyncSession = Depends(get_db),
):
  return await ScheduleService(session).reject_import(_org(current_user), import_id, current_user.id,
    payload.note if payload else None)

@router.post("/schedule-imports/{import_id}/archive", response_model=ScheduleImportResponse)
async def archive_schedule_import(
  import_id: UUID, current_user: User = Depends(require_permission(PermissionKey.SCHEDULE_IMPORT)),
  session: AsyncSession = Depends(get_db),
):
  return await ScheduleService(session).archive_import(_org(current_user), import_id, current_user.id)

@router.post("/schedule-imports/{import_id}/rematch")
async def rematch_schedule_import(
  import_id: UUID, current_user: User = Depends(require_permission(PermissionKey.SCHEDULE_IMPORT)),
  session: AsyncSession = Depends(get_db),
):
  return await ScheduleService(session).rematch(_org(current_user), import_id, current_user.id)