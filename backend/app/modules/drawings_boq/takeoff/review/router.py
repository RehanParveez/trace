from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from uuid import UUID
from app.modules.drawings_boq.takeoff.review.schemas import ReviewResponse, ReviewActionRequest, ReviewActionResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.modules.drawings_boq.takeoff.review.service import ReviewSersvice

router = APIRouter()
_READ = PermissionKey.DRAWING_READ
_EDIT = PermissionKey.BOQ_UPDATE

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

@router.get("/projects/{project_id}/takeoff/review", response_model=ReviewResponse)
async def project_review(project_id: UUID, item: str | None = Query(None, description="A catalogue item: only the rows that change it."), current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await ReviewService(session).review(_org(current_user), project_id, item)

@router.post("/projects/{project_id}/takeoff/review/{key:path}/action", response_model=ReviewActionResponse)
async def act_on_row(project_id: UUID, key: str, payload: ReviewActionRequest, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db)):
  return await ReviewService(session).act(_org(current_user), current_user.id, project_id, key, payload.action, payload.value)
