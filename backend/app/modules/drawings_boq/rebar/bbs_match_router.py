from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.rebar.bbs_match_service import BbsMatchService
from app.modules.drawings_boq.rebar.bbs_match_schemas import ConfirmRequest, DecisionsOut, FloorMapRequest, MatchItemList, MatchRunOut

router = APIRouter(tags=["Bar bending schedule match"])
_READ = PermissionKey.DRAWING_READ
_WRITE = PermissionKey.SCHEDULE_IMPORT

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

@router.post("/bbs/{document_id}/match", response_model=MatchRunOut, status_code=201)
async def run_bbs_match(document_id: UUID, current_user: User = Depends(require_permission(_WRITE)), session: AsyncSession = Depends(get_db)):
  return await BbsMatchService(session).run(_org(current_user), document_id, current_user.id)

@router.get("/bbs/{document_id}/match", response_model=MatchRunOut | None)
async def latest_bbs_match(document_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await BbsMatchService(session).latest_out(_org(current_user), document_id)

@router.get("/bbs/{document_id}/match/items", response_model=MatchItemList)
async def list_bbs_match_items(document_id: UUID, kind: str | None = Query(default=None, pattern="^(MATCH|ASK|EXTRA|MISSING)$"), family: str | None = Query(default=None, max_length=12),
  page: int = Query(default=1, ge=1), page_size: int = Query(default=100, ge=1, le=500), current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await BbsMatchService(session).items(_org(current_user), document_id, kind, family, page, page_size)

@router.post("/bbs/{document_id}/match/confirm", response_model=MatchRunOut, status_code=201)
async def confirm_bbs_match(document_id: UUID, payload: ConfirmRequest, current_user: User = Depends(require_permission(_WRITE)), session: AsyncSession = Depends(get_db)):
  elements = [e.model_dump(by_alias=True) for e in payload.elements]
  return await BbsMatchService(session).confirm(_org(current_user), document_id, current_user.id, payload.group, elements, payload.note)

@router.delete("/bbs/{document_id}/match/confirm", response_model=MatchRunOut)
async def forget_bbs_match(document_id: UUID, group: str = Query(min_length=1, max_length=620), current_user: User = Depends(require_permission(_WRITE)),
  session: AsyncSession = Depends(get_db)):
  return await BbsMatchService(session).forget(_org(current_user), document_id, current_user.id, group)

@router.get("/projects/{project_id}/bbs-decisions", response_model=DecisionsOut)
async def get_bbs_decisions(project_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await BbsMatchService(session).project_decisions(_org(current_user), project_id)

@router.put("/projects/{project_id}/bbs-decisions/bbs_floor_map", response_model=DecisionsOut)
async def put_bbs_floor_map(project_id: UUID, payload: FloorMapRequest, current_user: User = Depends(require_permission(_WRITE)), session: AsyncSession = Depends(get_db)):
  return await BbsMatchService(session).set_floor_map(_org(current_user), project_id, current_user.id, payload.value)
