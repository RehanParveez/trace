from __future__ import annotations
from fastapi import APIRouter, Depends
from app.modules.identity.enums import PermissionKey
from app.modules.drawings_boq.takeoff.integrity.schemas import IntegrityResponse
from uuid import UUID
from app.modules.identity.models import User
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.takeoff.integrity.service import IntegrityService

router = APIRouter()
_READ = PermissionKey.DRAWING_READ

@router.get("/drawings/{drawing_id}/takeoff/integrity", response_model=IntegrityResponse)
async def drawing_integrity(drawing_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await IntegrityService(session).integrity(current_user.active_membership.organization_id, drawing_id)
