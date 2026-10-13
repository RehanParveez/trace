from __future__ import annotations
from app.modules.identity.models import User
from uuid import UUID
from app.modules.identity.enums import PermissionKey
from app.modules.drawings_boq.takeoff.extract.extract_schemas import (ExtractResponse, ExtractRequest, AcceptRequest, AcceptResponse, CandidateListResponse, DecideRequest, DecideResponse, 
  DrawingCandidatesResponse, DrawingExtractResponse, RegisterSyncResponse
)
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.modules.drawings_boq.takeoff.extract.extract_service import ExtractService
from app.modules.drawings_boq.takeoff.register_service import RegisterService

router = APIRouter()

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

_READ = PermissionKey.DRAWING_READ
_EDIT = PermissionKey.BOQ_UPDATE

@router.post("/takeoff/sheets/{sheet_id}/extract", response_model=ExtractResponse)
async def extract_sheet(
  sheet_id: UUID, payload: ExtractRequest | None = None,
  current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await ExtractService(session).extract_sheet(_org(current_user), sheet_id, current_user.id, payload or ExtractRequest())

@router.get("/takeoff/sheets/{sheet_id}/candidates", response_model=CandidateListResponse)
async def sheet_candidates(
  sheet_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  return await ExtractService(session).candidates(_org(current_user), sheet_id)

@router.post("/drawings/{drawing_id}/takeoff/extract", response_model=DrawingExtractResponse)
async def extract_drawing(
  drawing_id: UUID, payload: ExtractRequest | None = None,
  current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await ExtractService(session).extract_drawing(_org(current_user), drawing_id, current_user.id, payload or ExtractRequest())

@router.get("/drawings/{drawing_id}/takeoff/candidates", response_model=DrawingCandidatesResponse)
async def drawing_candidates(
  drawing_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  return await ExtractService(session).drawing_candidates(_org(current_user), drawing_id)

@router.post("/takeoff/candidates/accept", response_model=AcceptResponse)
async def accept_candidates(
  payload: AcceptRequest, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await ExtractService(session).accept(_org(current_user), current_user.id, payload)

@router.post("/takeoff/candidates/reject", response_model=DecideResponse)
async def reject_candidates(
  payload: DecideRequest, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await ExtractService(session).reject(_org(current_user), current_user.id, payload.ids)

@router.post("/takeoff/candidates/restore", response_model=DecideResponse)
async def restore_candidates(
  payload: DecideRequest, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
    return await ExtractService(session).restore(_org(current_user), current_user.id, payload.ids)

@router.post("/drawings/{drawing_id}/takeoff/register", response_model=RegisterSyncResponse)
async def sync_register(
  drawing_id: UUID, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await RegisterService(session).sync_and_commit(_org(current_user), drawing_id)
