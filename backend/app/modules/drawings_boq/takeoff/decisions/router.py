from __future__ import annotations
from fastapi import APIRouter, Depends
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from uuid import UUID
from app.dependencies.permissions import require_permission
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.drawings_boq.takeoff.decisions.schemas import DecisionsResponse, ChooseDecisionRequest
from app.modules.drawings_boq.takeoff.decisions.service import DecisionsService

router = APIRouter()
_READ = PermissionKey.DRAWING_READ
_EDIT = PermissionKey.BOQ_UPDATE

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

@router.get("/drawings/{drawing_id}/takeoff/decisions", response_model=DecisionsResponse)
async def drawing_decisions(drawing_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await DecisionsService(session).view(_org(current_user), drawing_id)

@router.put("/drawings/{drawing_id}/takeoff/decisions", response_model=DecisionsResponse)
async def choose_decision(drawing_id: UUID, payload: ChooseDecisionRequest, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db)):
  return await DecisionsService(session).choose(_org(current_user), current_user.id, drawing_id, payload)
