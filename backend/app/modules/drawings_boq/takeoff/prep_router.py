from __future__ import annotations
from app.modules.identity.models import User
from app.modules.identity.enums import PermissionKey
from app.core.exceptions import TraceException
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.permissions import require_permission
from fastapi import APIRouter, Depends, Query
from app.core.database import get_db
from app.modules.drawings_boq.takeoff.prep_service import PrepService
from app.modules.drawings_boq.takeoff.schemas import SheetResponse
from app.modules.drawings_boq.takeoff.prep_schemas import (PrepareRequest, AnalysisResponse, AutoCalibrateRequest, AutoCalibrateResponse, PickRequest,
  PickResponse, PrepareResponse, FactsResponse, ShapeDetailResponse, ShapeListResponse, SnapRequest, SnapResponse, TagDetailResponse,
  TagListResponse, TextResponse, VectorResponse)
from app.modules.drawings_boq.takeoff.extract.project_schemas import ProjectFactsResponse, ProjectMarksResponse, SetMarkRequest
from typing import Literal

router = APIRouter()

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

_READ = PermissionKey.DRAWING_READ
_EDIT = PermissionKey.BOQ_UPDATE

def _bbox(x0, y0, x1, y1):
  vals = (x0, y0, x1, y1)
  if all(v is None for v in vals):
    return None
  if any(v is None for v in vals):
    raise TraceException("Give all four of x0, y0, x1, y1 or none of them.", status_code=422, code="BBOX_INCOMPLETE")
  return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))

@router.post("/drawings/{drawing_id}/takeoff/prepare", response_model=PrepareResponse)
async def prepare_drawing(
  drawing_id: UUID, payload: PrepareRequest | None = None,
  current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await PrepService(session).prepare_drawing(_org(current_user), drawing_id, current_user.id, payload or PrepareRequest())

@router.get("/projects/{project_id}/takeoff/project-facts", response_model=ProjectFactsResponse)
async def get_project_facts(
  project_id: UUID, exclude_superseded: bool = Query(True), current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  return await PrepService(session).project_facts_view(_org(current_user), project_id, exclude_superseded=exclude_superseded)

@router.get("/projects/{project_id}/takeoff/marks", response_model=ProjectMarksResponse)
async def get_project_marks(
  project_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  return await PrepService(session).marks_view(_org(current_user), project_id)

@router.put("/projects/{project_id}/takeoff/marks", response_model=ProjectMarksResponse)
async def set_project_mark(
  project_id: UUID, payload: SetMarkRequest, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await PrepService(session).set_mark(_org(current_user), current_user.id, project_id, payload.discipline, payload.mark, payload.category)

@router.get("/drawings/{drawing_id}/takeoff/facts", response_model=FactsResponse)
async def get_drawing_facts(
  drawing_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  return await PrepService(session).drawing_facts(_org(current_user), drawing_id)

@router.post("/takeoff/sheets/{sheet_id}/prepare", response_model=SheetResponse)
async def prepare_sheet(
  sheet_id: UUID, force: bool = False,
  current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await PrepService(session).prepare_sheet(_org(current_user), sheet_id, current_user.id, force)

@router.get("/takeoff/sheets/{sheet_id}/analysis", response_model=AnalysisResponse)
async def get_analysis(
  sheet_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  return await PrepService(session).analysis(_org(current_user), sheet_id)

@router.post("/takeoff/sheets/{sheet_id}/auto-calibrate", response_model=AutoCalibrateResponse)
async def auto_calibrate(
  sheet_id: UUID, payload: AutoCalibrateRequest | None = None,
  current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await PrepService(session).auto_calibrate(_org(current_user), sheet_id, current_user.id, payload or AutoCalibrateRequest())

@router.get("/takeoff/sheets/{sheet_id}/vector", response_model=VectorResponse)
async def get_vector(
  sheet_id: UUID, x0: float | None = None, y0: float | None = None, x1: float | None = None, y1: float | None = None,
  max_segments: int = Query(default=20000, ge=100, le=60000),
  current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  return await PrepService(session).vector_window(_org(current_user), sheet_id, _bbox(x0, y0, x1, y1), max_segments)

@router.get("/takeoff/sheets/{sheet_id}/text", response_model=TextResponse)
async def get_text(
  sheet_id: UUID, q: str | None = Query(default=None, max_length=60), mode: Literal["TAG", "WORD", "CONTAINS"] = "TAG",
  x0: float | None = None, y0: float | None = None, x1: float | None = None, y1: float | None = None,
  current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  return await PrepService(session).text(_org(current_user), sheet_id, q, mode, _bbox(x0, y0, x1, y1))

@router.post("/takeoff/sheets/{sheet_id}/snap", response_model=SnapResponse)
async def snap_points(
  sheet_id: UUID, payload: SnapRequest,
  current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  return await PrepService(session).snap(_org(current_user), sheet_id, payload)

@router.post("/takeoff/sheets/{sheet_id}/pick", response_model=PickResponse)
async def pick_point(
  sheet_id: UUID, payload: PickRequest,
  current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  return await PrepService(session).pick(_org(current_user), sheet_id, payload)

@router.get("/takeoff/sheets/{sheet_id}/tags", response_model=TagListResponse)
async def list_tags(
  sheet_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  return await PrepService(session).tags(_org(current_user), sheet_id)

@router.get("/takeoff/sheets/{sheet_id}/tags/{tag}", response_model=TagDetailResponse)
async def get_tag(
  sheet_id: UUID, tag: str, include_dense: bool = False,
  current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  return await PrepService(session).tag_detail(_org(current_user), sheet_id, tag, include_dense)

@router.get("/takeoff/sheets/{sheet_id}/shapes", response_model=ShapeListResponse)
async def list_shapes(
  sheet_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  return await PrepService(session).shapes(_org(current_user), sheet_id)

@router.get("/takeoff/sheets/{sheet_id}/shapes/{group_id}", response_model=ShapeDetailResponse)
async def get_shape(
  sheet_id: UUID, group_id: str, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  return await PrepService(session).shape_detail(_org(current_user), sheet_id, group_id)
