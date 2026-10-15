from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies.permissions import require_permission
from app.modules.drawings_boq.takeoff.schemas import (BulkConfirmRequest, BulkConfirmResponse, CalibrationCreateRequest, CalibrationResponse, CalibrationUpdateRequest, MeasurementCreateRequest, 
  MeasurementResponse, MeasurementUpdateRequest, ModeOption, PreviewRequest, PreviewResponse, ReconciliationResponse, SheetResponse, SheetUpdateRequest, TakeoffOverviewResponse,
)
from app.modules.drawings_boq.takeoff.service import TakeoffService
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from app.modules.drawings_boq.takeoff.extract.extract_router import router as _extract_router
from app.modules.drawings_boq.takeoff.summary_router import router as _summary_router
from app.modules.drawings_boq.takeoff.frame_router import router as _frame_router

router = APIRouter()

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

_READ = PermissionKey.DRAWING_READ
_EDIT = PermissionKey.BOQ_UPDATE

@router.get("/takeoff/modes", response_model=list[ModeOption])
async def list_modes(current_user: User = Depends(require_permission(_READ))):
  return TakeoffService.modes()

@router.post("/drawings/{drawing_id}/takeoff/sync", response_model=TakeoffOverviewResponse)
async def sync_sheets(
  drawing_id: UUID, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await TakeoffService(session).sync_sheets(_org(current_user), drawing_id, current_user.id)

@router.get("/drawings/{drawing_id}/takeoff", response_model=TakeoffOverviewResponse)
async def get_overview(
  drawing_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  return await TakeoffService(session).overview(_org(current_user), drawing_id)

@router.patch("/takeoff/sheets/{sheet_id}", response_model=SheetResponse)
async def update_sheet(
  sheet_id: UUID, payload: SheetUpdateRequest,
  current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await TakeoffService(session).update_sheet(_org(current_user), sheet_id, current_user.id, payload)

@router.post("/takeoff/sheets/{sheet_id}/calibrations", response_model=CalibrationResponse, status_code=201)
async def create_calibration(
  sheet_id: UUID, payload: CalibrationCreateRequest,
  current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await TakeoffService(session).create_calibration(_org(current_user), sheet_id, current_user.id, payload)

@router.patch("/takeoff/calibrations/{calibration_id}", response_model=CalibrationResponse)
async def update_calibration(
  calibration_id: UUID, payload: CalibrationUpdateRequest,
  current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await TakeoffService(session).update_calibration(_org(current_user), calibration_id, current_user.id, payload)

@router.post("/takeoff/calibrations/{calibration_id}/default", response_model=CalibrationResponse)
async def make_default_calibration(
  calibration_id: UUID, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await TakeoffService(session).set_default_calibration(_org(current_user), calibration_id, current_user.id)

@router.delete("/takeoff/calibrations/{calibration_id}", status_code=204)
async def delete_calibration(
  calibration_id: UUID, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  await TakeoffService(session).delete_calibration(_org(current_user), calibration_id, current_user.id)

@router.post("/takeoff/sheets/{sheet_id}/measurements", response_model=MeasurementResponse, status_code=201)
async def create_measurement(
  sheet_id: UUID, payload: MeasurementCreateRequest,
  current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await TakeoffService(session).create_measurement(_org(current_user), sheet_id, current_user.id, payload)

@router.patch("/takeoff/measurements/{measurement_id}", response_model=MeasurementResponse)
async def update_measurement(
  measurement_id: UUID, payload: MeasurementUpdateRequest,
  current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await TakeoffService(session).update_measurement(_org(current_user), measurement_id, current_user.id, payload)

@router.delete("/takeoff/measurements/{measurement_id}", status_code=204)
async def delete_measurement(
  measurement_id: UUID, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  await TakeoffService(session).delete_measurement(_org(current_user), measurement_id, current_user.id)

@router.post("/takeoff/measurements/bulk-confirm", response_model=BulkConfirmResponse)
async def bulk_confirm(
  payload: BulkConfirmRequest, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await TakeoffService(session).bulk_confirm(_org(current_user), payload.ids, current_user.id)

@router.post("/takeoff/measurements/{measurement_id}/confirm", response_model=MeasurementResponse)
async def confirm_measurement(
  measurement_id: UUID, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await TakeoffService(session).confirm(_org(current_user), measurement_id, current_user.id)

@router.post("/takeoff/measurements/{measurement_id}/unconfirm", response_model=MeasurementResponse)
async def unconfirm_measurement(
  measurement_id: UUID, current_user: User = Depends(require_permission(_EDIT)), session: AsyncSession = Depends(get_db),
):
  return await TakeoffService(session).unconfirm(_org(current_user), measurement_id, current_user.id)

@router.post("/takeoff/preview", response_model=PreviewResponse)
async def preview(
  payload: PreviewRequest, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  return await TakeoffService(session).preview(_org(current_user), payload)

@router.get("/projects/{project_id}/takeoff/reconciliation", response_model=ReconciliationResponse)
async def reconciliation(
  project_id: UUID, current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db),
):
  return await TakeoffService(session).reconciliation(_org(current_user), project_id)

from app.modules.drawings_boq.takeoff.prep_router import router as _prep_router 
router.include_router(_prep_router)

router.include_router(_extract_router)
router.include_router(_summary_router)
router.include_router(_frame_router)
