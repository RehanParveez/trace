from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies.permissions import require_permission
from app.modules.drawings_boq.rebar.bbs_steel_boq import SteelBoqService
from app.modules.drawings_boq.rebar.bbs_steel_boq_schemas import SteelBoqIn, SteelBoqOut
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User

router = APIRouter(tags=["Audited steel on the bill"])

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

@router.get("/boq-versions/{version_id}/audited-steel", response_model=SteelBoqOut)
async def audited_steel_preview(version_id: UUID, item_id: UUID | None = Query(default=None),
  current_user: User = Depends(require_permission(PermissionKey.DRAWING_READ)), session: AsyncSession = Depends(get_db)):
  return await SteelBoqService(session).preview(_org(current_user), version_id, item_id)

@router.post("/boq-versions/{version_id}/audited-steel", response_model=SteelBoqOut)
async def audited_steel_apply(version_id: UUID, payload: SteelBoqIn,
  current_user: User = Depends(require_permission(PermissionKey.BOQ_ADJUST)), session: AsyncSession = Depends(get_db)):
  return await SteelBoqService(session).apply(_org(current_user), version_id, current_user.id, payload.item_id)
