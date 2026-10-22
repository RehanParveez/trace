from __future__ import annotations
from fastapi import APIRouter, Depends
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from uuid import UUID
from app.dependencies.permissions import require_permission
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.drawings_boq.takeoff.grades.schemas import GradesResponse, StampRequest
from app.modules.drawings_boq.takeoff.grades.service import GradesService

router = APIRouter()
_READ = PermissionKey.DRAWING_READ
_EDIT = PermissionKey.BOQ_UPDATE

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

@router.get("/drawings/{drawing_id}/takeoff/printed-grades", response_model=GradesResponse)
async def printed_grades(drawing_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await GradesService(session).report(_org(current_user), drawing_id)

@router.post("/drawings/{drawing_id}/takeoff/printed-grades/stamp", response_model=GradesResponse)
async def stamp_grades(drawing_id: UUID, payload: StampRequest, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db)):
  return await GradesService(session).stamp(_org(current_user), current_user.id, drawing_id, payload.include_confirmed)

@router.post("/drawings/{drawing_id}/takeoff/printed-grades/unstamp", response_model=GradesResponse)
async def unstamp_grades(drawing_id: UUID, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db)):
  return await GradesService(session).unstamp(_org(current_user), current_user.id, drawing_id)
