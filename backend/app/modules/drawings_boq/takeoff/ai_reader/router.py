from __future__ import annotations
from fastapi import APIRouter, Depends, Response
from app.modules.identity.enums import PermissionKey
from uuid import UUID
from app.modules.identity.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.modules.drawings_boq.takeoff.ai_reader.schemas import ShadowSummaryResponse, ShadowRunRequest, ShadowRunResponse
from app.modules.drawings_boq.takeoff.ai_reader.service import AiShadowService

router = APIRouter()
_READ = PermissionKey.DRAWING_READ
_EDIT = PermissionKey.BOQ_UPDATE

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

@router.get("/drawings/{drawing_id}/takeoff/ai-shadow", response_model=ShadowSummaryResponse)
async def shadow_summary(drawing_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await AiShadowService(session).summary(_org(current_user), drawing_id)

@router.post("/drawings/{drawing_id}/takeoff/ai-shadow", response_model=ShadowRunResponse)
async def shadow_run(drawing_id: UUID, payload: ShadowRunRequest, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db)):
  return await AiShadowService(session).run(_org(current_user), current_user.id, drawing_id, payload.mode, payload.limit, payload.force)

@router.get("/takeoff/ai-shadow/{read_id}/crop", response_class=Response, responses={200: {"content": {"image/png": {}}}})
async def shadow_crop(read_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  png = await AiShadowService(session).crop(_org(current_user), read_id)
  return Response(content=png, media_type="image/png", headers={"Cache-Control": "private, max-age=300"})
