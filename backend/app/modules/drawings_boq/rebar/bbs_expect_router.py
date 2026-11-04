from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.modules.drawings_boq.rebar.bbs_expect_schemas import DecisionValue, ExpectationList, ExpectRunOut
from app.modules.drawings_boq.rebar.bbs_expect_service import BbsExpectService
from app.modules.drawings_boq.rebar.bbs_match_schemas import DecisionsOut

router = APIRouter(tags=["Bar bending schedule expected quantities"])
_READ = PermissionKey.DRAWING_READ
_WRITE = PermissionKey.SCHEDULE_IMPORT

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

@router.post("/bbs/{document_id}/expect", response_model=ExpectRunOut, status_code=201)
async def run_bbs_expect(document_id: UUID, current_user: User = Depends(require_permission(_WRITE)), session: AsyncSession = Depends(get_db)):
  return await BbsExpectService(session).run(_org(current_user), document_id, current_user.id)

@router.get("/bbs/{document_id}/expect", response_model=ExpectRunOut | None)
async def latest_bbs_expect(document_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await BbsExpectService(session).latest_out(_org(current_user), document_id)

@router.get("/bbs/{document_id}/expect/items", response_model=ExpectationList)
async def list_bbs_expect_items(document_id: UUID, member_class: str | None = Query(default=None, pattern="^(COLUMN|BEAM|FOOTING|PLINTH|SLAB|LINTEL|TANK)$"),
  complete: bool | None = Query(default=None), page: int = Query(default=1, ge=1), page_size: int = Query(default=100, ge=1, le=500),
  current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await BbsExpectService(session).items(_org(current_user), document_id, member_class, complete, page, page_size)

@router.put("/projects/{project_id}/bbs-decisions/{key}", response_model=DecisionsOut)
async def put_bbs_decision(project_id: UUID, key: str, payload: DecisionValue, current_user: User = Depends(require_permission(_WRITE)), session: AsyncSession = Depends(get_db)):
  return await BbsExpectService(session).set_decision(_org(current_user), project_id, current_user.id, key, payload.value)

@router.delete("/projects/{project_id}/bbs-decisions/{key}", response_model=DecisionsOut)
async def clear_bbs_decision(project_id: UUID, key: str, current_user: User = Depends(require_permission(_WRITE)), session: AsyncSession = Depends(get_db)):
  return await BbsExpectService(session).set_decision(_org(current_user), project_id, current_user.id, key, None)
