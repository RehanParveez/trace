from __future__ import annotations
from fastapi import APIRouter, Depends, Header, Query, Response
from app.modules.identity.enums import PermissionKey
from uuid import UUID
from app.modules.identity.models import User
from app.dependencies.permissions import require_permission
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.drawings_boq.takeoff.crops.service import DEFAULT_PX, CropService

router = APIRouter()
_READ = PermissionKey.DRAWING_READ

@router.get("/takeoff/candidates/{candidate_id}/crop", response_class=Response, responses={200: {"content": {"image/png": {}}}, 304: {"description": "Unchanged"}})
async def candidate_crop(
  candidate_id: UUID, size: int = Query(DEFAULT_PX, ge=160, le=1000), if_none_match: str | None = Header(None),
  current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  png, etag = await CropService(session).crop(current_user.active_membership.organization_id, candidate_id, size, if_none_match)
  headers = {"ETag": etag, "Cache-Control": "private, max-age=300"}
  if png is None:
    return Response(status_code=304, headers=headers)
  return Response(content=png, media_type="image/png", headers=headers)