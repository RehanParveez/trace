from __future__ import annotations
from app.modules.identity.models import User
from uuid import UUID
from pydantic import BaseModel
from app.modules.identity.enums import PermissionKey
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.modules.drawings_boq.takeoff.summary import project_takeoff_summary

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
