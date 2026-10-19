from __future__ import annotations
from app.modules.identity.models import User
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.modules.identity.enums import PermissionKey
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.modules.drawings_boq.takeoff.summary import project_takeoff_summary
from app.modules.drawings_boq.takeoff.source_totals import project_source_totals

router = APIRouter()

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

class ProjectTakeoffDrawing(BaseModel):
  drawing_id: UUID
  original_filename: str
  revision_label: str | None
  is_current_revision: bool
  sheets: int
  prepared_sheets: int
  calibrated_sheets: int
  draft: int
  confirmed: int

class ProjectTakeoffResponse(BaseModel):
  drawings: list[ProjectTakeoffDrawing]

@router.get("/projects/{project_id}/takeoff/drawings", response_model=ProjectTakeoffResponse)
async def project_takeoff_drawings(
  project_id: UUID, current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)), session: AsyncSession = Depends(get_db),
):
  return await project_takeoff_summary(session, _org(current_user), project_id)

class SourceQuantity(BaseModel):
  source: str
  quantity: str

class SourceTotalItem(BaseModel):
  work_item_code: str
  name: str | None = None
  unit: str
  total: str
  rows: int
  sources: list[SourceQuantity]
  mixed: bool

class SourceTotalsRun(BaseModel):
  id: UUID
  completed_at: datetime | None = None

class SourceTotalsReconciliation(BaseModel):
  replaced: int = 0
  variances: int = 0
  not_counted: int = 0
  verified: int = 0
  tolerance_pct: str | None = None
  replaced_rows: list[dict] = []
  variance_rows: list[dict] = []
  not_counted_rows: list[dict] = []

class SourceTotalsResponse(BaseModel):
  run: SourceTotalsRun | None = None
  items: list[SourceTotalItem] = []
  reconciliation: SourceTotalsReconciliation
  mixed_items: int = 0

@router.get("/projects/{project_id}/takeoff/source-totals", response_model=SourceTotalsResponse)
async def project_totals_by_source(
  project_id: UUID, current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)), session: AsyncSession = Depends(get_db),
):
  return await project_source_totals(session, _org(current_user), project_id)
