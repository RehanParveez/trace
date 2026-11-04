from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from app.modules.drawings_boq.rebar.bbs_schemas import AuditRunOut
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.modules.drawings_boq.rebar.bbs_crosscheck_service import BbsCrossCheckService

router = APIRouter(tags=["Bar bending schedule cross-check"])
_WRITE = PermissionKey.SCHEDULE_IMPORT

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

@router.post("/bbs/{document_id}/crosscheck", response_model=AuditRunOut, status_code=201)
async def run_bbs_crosscheck(document_id: UUID, current_user: User = Depends(require_permission(_WRITE)), session: AsyncSession = Depends(get_db)):
  return await BbsCrossCheckService(session).run(_org(current_user), document_id, current_user.id)
