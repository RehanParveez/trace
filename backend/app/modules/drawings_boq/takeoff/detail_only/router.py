from __future__ import annotations
from fastapi import APIRouter, Depends
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from uuid import UUID
from app.modules.drawings_boq.takeoff.detail_only.schemas import DetailOnlyResponse, ChooseDepthRequest, ChooseMarkRequest
from app.modules.drawings_boq.takeoff.detail_only.service import DetailOnlyService
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.permissions import require_permission
from app.core.database import get_db

router = APIRouter()
_READ = PermissionKey.DRAWING_READ
_EDIT = PermissionKey.BOQ_UPDATE

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

@router.get("/drawings/{drawing_id}/takeoff/detail-only", response_model=DetailOnlyResponse)
async def detail_only(drawing_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await DetailOnlyService(session).report(_org(current_user), drawing_id)

@router.post("/drawings/{drawing_id}/takeoff/detail-only/column-mark", response_model=DetailOnlyResponse)
async def choose_column_mark(drawing_id: UUID, payload: ChooseMarkRequest, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db)):
  return await DetailOnlyService(session).choose_mark(_org(current_user), current_user.id, drawing_id, payload)

@router.post("/drawings/{drawing_id}/takeoff/detail-only/beam-depth", response_model=DetailOnlyResponse)
async def choose_beam_depth(drawing_id: UUID, payload: ChooseDepthRequest, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db)):
  return await DetailOnlyService(session).choose_depth(_org(current_user), current_user.id, drawing_id, payload)

@router.delete("/drawings/{drawing_id}/takeoff/detail-only/decisions/{decision_id}", response_model=DetailOnlyResponse)
async def undo_decision(drawing_id: UUID, decision_id: UUID, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db)):
  return await DetailOnlyService(session).undo(_org(current_user), current_user.id, drawing_id, decision_id)