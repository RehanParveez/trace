from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.core.exceptions import TraceException
from app.modules.drawings_boq.rebar.bbs_steel_service import SteelFiguresService
from app.modules.drawings_boq.rebar import bbs_audited as BA
from app.modules.drawings_boq.rebar.bbs_steel_schemas import SteelFiguresOut, SteelSourceIn, SteelSourceOut

router = APIRouter(tags=["Audited steel"])
_READ = PermissionKey.DRAWING_READ
_WRITE = PermissionKey.SCHEDULE_IMPORT
MAX_WASTAGE_PCT = 15.0

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

@router.get("/calculation-runs/{run_id}/steel-figures", response_model=SteelFiguresOut)
async def steel_figures(run_id: UUID, source: str | None = Query(default=None, max_length=20), wastage_pct: float | None = Query(default=None, ge=0, le=MAX_WASTAGE_PCT),
  current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  if source is not None and source not in BA.SOURCES:
    raise TraceException(f"source is one of {', '.join(BA.SOURCES)}.", status_code=422, code="STEEL_SOURCE_INVALID")
  return await SteelFiguresService(session).figures(_org(current_user), run_id, source, wastage_pct)

@router.get("/projects/{project_id}/steel-source", response_model=SteelSourceOut)
async def get_steel_source(project_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await SteelFiguresService(session).get_source(_org(current_user), project_id)

@router.put("/projects/{project_id}/steel-source", response_model=SteelSourceOut)
async def put_steel_source(project_id: UUID, payload: SteelSourceIn, current_user: User = Depends(require_permission(_WRITE)), session: AsyncSession = Depends(get_db)):
  if payload.source not in BA.SOURCES:
    raise TraceException(f"source is one of {', '.join(BA.SOURCES)}.", status_code=422, code="STEEL_SOURCE_INVALID")
  return await SteelFiguresService(session).set_source(_org(current_user), project_id, current_user.id, payload.source)
