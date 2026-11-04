from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from app.modules.identity.enums import PermissionKey
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from uuid import UUID
from app.modules.identity.models import User
from app.modules.drawings_boq.takeoff.reading_report.service import ReadingReportService
from app.modules.drawings_boq.takeoff.reading_report.schemas import (CompletenessResponse, MisreadOut, MisreadRequest, OverrideListResponse, OverrideOut, OverrideRequest, ReadingReportResponse,
  SheetItemsResponse)

router = APIRouter()
_READ = PermissionKey.DRAWING_READ
_EDIT = PermissionKey.BOQ_UPDATE

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

@router.get("/drawings/{drawing_id}/reading-report", response_model=ReadingReportResponse, response_model_by_alias=True)
async def reading_report(drawing_id: UUID, include_items: bool = Query(default=False, description="Put every item, with its place on the sheet, inside each sheet card."),
  current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await ReadingReportService(session).report(_org(current_user), drawing_id, include_items)

@router.get("/drawings/{drawing_id}/reading-report/sheets/{sheet_id}/items", response_model=SheetItemsResponse, response_model_by_alias=True)
async def reading_report_items(drawing_id: UUID, sheet_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await ReadingReportService(session).sheet_items(_org(current_user), drawing_id, sheet_id)

@router.get("/projects/{project_id}/input-completeness", response_model=CompletenessResponse)
async def input_completeness(project_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await ReadingReportService(session).completeness(_org(current_user), project_id)

@router.get("/drawings/{drawing_id}/reading-overrides", response_model=OverrideListResponse)
async def list_overrides(drawing_id: UUID, sheet_id: UUID | None = None, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await ReadingReportService(session).list_overrides(_org(current_user), drawing_id, sheet_id)

@router.post("/drawings/{drawing_id}/reading-overrides", response_model=OverrideOut, status_code=201)
async def add_override(drawing_id: UUID, payload: OverrideRequest, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db)):
  return await ReadingReportService(session).add_override(_org(current_user), current_user.id, drawing_id, payload)

@router.delete("/drawings/{drawing_id}/reading-overrides/{override_id}", response_model=OverrideOut)
async def withdraw_override(drawing_id: UUID, override_id: UUID, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db)):
  return await ReadingReportService(session).withdraw_override(_org(current_user), drawing_id, override_id)

@router.get("/drawings/{drawing_id}/misread-reports", response_model=list[MisreadOut])
async def list_misreads(drawing_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await ReadingReportService(session).list_misreads(_org(current_user), drawing_id)

@router.post("/drawings/{drawing_id}/misread-reports", response_model=MisreadOut, status_code=201)
async def add_misread(drawing_id: UUID, payload: MisreadRequest, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await ReadingReportService(session).add_misread(_org(current_user), current_user.id, drawing_id, payload)
