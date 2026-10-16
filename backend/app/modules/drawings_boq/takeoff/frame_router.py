from __future__ import annotations
from fastapi import APIRouter, Depends
from uuid import UUID
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.modules.drawings_boq.takeoff.frame_schemas import FloorDatumsResponse, FramePlaceRequest, FrameReferenceRequest, FrameResponse
from app.modules.drawings_boq.takeoff.frame_service import FrameService
from app.modules.drawings_boq.takeoff.reconcile_schemas import ReconcileResponse
from app.modules.drawings_boq.takeoff.reconcile_service import ReconcileService
from app.modules.drawings_boq.takeoff.register_service import RegisterService

router = APIRouter()

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

_READ = PermissionKey.DRAWING_READ
_EDIT = PermissionKey.BOQ_UPDATE

@router.get("/drawings/{drawing_id}/takeoff/frame", response_model=FrameResponse)
async def get_frame(drawing_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await FrameService(session).frame(_org(current_user), drawing_id)

@router.put("/drawings/{drawing_id}/takeoff/frame/placement", response_model=FrameResponse)
async def place_view(drawing_id: UUID, payload: FramePlaceRequest, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db)):
  return await FrameService(session).place(_org(current_user), drawing_id, current_user.id, payload.view, payload.action, payload.dx_mm, payload.dy_mm)

@router.put("/drawings/{drawing_id}/takeoff/frame/reference", response_model=FrameResponse)
async def set_reference(drawing_id: UUID, payload: FrameReferenceRequest, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db)):
  return await FrameService(session).set_reference(_org(current_user), drawing_id, current_user.id, payload.view)

@router.get("/drawings/{drawing_id}/takeoff/floors", response_model=FloorDatumsResponse)
async def get_floors(drawing_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await RegisterService(session).floor_datums(_org(current_user), drawing_id)

@router.get("/drawings/{drawing_id}/takeoff/reconcile", response_model=ReconcileResponse)
async def get_reconcile(drawing_id: UUID, model_drawing_id: UUID | None = None, dx_mm: float | None = None, dy_mm: float | None = None,
    current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await ReconcileService(session).reconcile(_org(current_user), drawing_id, model_drawing_id, dx_mm, dy_mm)
