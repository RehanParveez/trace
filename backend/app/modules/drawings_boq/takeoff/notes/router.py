from __future__ import annotations
from app.modules.identity.enums import PermissionKey
from fastapi import APIRouter, Depends
from app.modules.drawings_boq.takeoff.notes.schemas import NotesResponse
from uuid import UUID
from app.modules.identity.models import User
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.takeoff.notes.service import NotesService

router = APIRouter()
_READ = PermissionKey.DRAWING_READ

@router.get("/drawings/{drawing_id}/takeoff/notes", response_model=NotesResponse)
async def printed_notes(drawing_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await NotesService(session).report(current_user.active_membership.organization_id, drawing_id)