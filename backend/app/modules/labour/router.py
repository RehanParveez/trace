from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.labour.service import LabourService
from app.modules.labour.schemas import ( LabourSourceResponse, AttendanceBulkCreateRequest, AttendanceBulkResultResponse, DayAttendanceSummaryResponse, LabourAdvanceCreateRequest, LabourAdvanceResponse, LabourBalanceResponse, LabourCostResponse,
  LabourDeploymentCreateRequest, LabourDeploymentResponse, LabourDeploymentUpdateRequest, LabourPaymentCreateRequest, LabourPaymentResponse, LabourSourceCreateRequest,
  LabourSourceUpdateRequest, LabourSummaryResponse, LabourTradeCostResponse, LabourWorkerCreateRequest, LabourWorkerResponse, LabourWorkerUpdateRequest,
)
from app.modules.identity.models import User
from app.modules.identity.enums import PermissionKey
from fastapi import APIRouter, Depends, Query
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from datetime import date
from uuid import UUID

router = APIRouter(prefix="/labour", tags=["Labour"])

def _service(session: AsyncSession) -> LabourService:
  return LabourService(session)

@router.post("/sources", response_model=LabourSourceResponse, status_code=201)
async def create_source(
  payload: LabourSourceCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.LABOUR_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).create_source(current_user.active_membership.organization_id, payload)

@router.get("/sources", response_model=list[LabourSourceResponse])
async def list_sources(
  current_user: User = Depends(require_permission(PermissionKey.LABOUR_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).list_sources(current_user.active_membership.organization_id)

@router.patch("/sources/{source_id}", response_model=LabourSourceResponse)
async def update_source(
  source_id: UUID,
  payload: LabourSourceUpdateRequest,
  current_user: User = Depends(require_permission(PermissionKey.LABOUR_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).update_source(current_user.active_membership.organization_id, source_id, payload)

@router.post("/workers", response_model=LabourWorkerResponse, status_code=201)
async def create_worker(
  payload: LabourWorkerCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.LABOUR_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).create_worker(current_user.active_membership.organization_id, payload)

@router.get("/workers", response_model=list[LabourWorkerResponse])
async def list_workers(
  source_id: UUID | None = Query(default=None),
  current_user: User = Depends(require_permission(PermissionKey.LABOUR_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).list_workers(current_user.active_membership.organization_id, source_id)

@router.patch("/workers/{worker_id}", response_model=LabourWorkerResponse)
async def update_worker(
  worker_id: UUID,
  payload: LabourWorkerUpdateRequest,
  current_user: User = Depends(require_permission(PermissionKey.LABOUR_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).update_worker(current_user.active_membership.organization_id, worker_id, payload)

@router.post("/projects/{project_id}/deployments", response_model=LabourDeploymentResponse, status_code=201)
async def create_deployment(
  project_id: UUID,
  payload: LabourDeploymentCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.LABOUR_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).create_deployment(current_user.active_membership.organization_id, project_id, payload)

@router.get("/projects/{project_id}/deployments", response_model=list[LabourDeploymentResponse])
async def list_deployments(
  project_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.LABOUR_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).list_deployments(current_user.active_membership.organization_id, project_id)

@router.patch("/projects/{project_id}/deployments/{deployment_id}", response_model=LabourDeploymentResponse)
async def update_deployment(
  project_id: UUID,
  deployment_id: UUID,
  payload: LabourDeploymentUpdateRequest,
  current_user: User = Depends(require_permission(PermissionKey.LABOUR_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).update_deployment(current_user.active_membership.organization_id, deployment_id, payload)

@router.post("/projects/{project_id}/attendance/bulk", response_model=AttendanceBulkResultResponse)
async def bulk_record_attendance(
  project_id: UUID,
  payload: AttendanceBulkCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.LABOUR_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  created, updated, items = await _service(session).bulk_record_attendance(
    current_user.active_membership.organization_id, project_id, payload, current_user.id,
  )
  return AttendanceBulkResultResponse(created=created, updated=updated, items=items)

@router.get("/projects/{project_id}/attendance", response_model=list[dict])
async def list_attendance(
  project_id: UUID,
  period_start: date | None = Query(default=None),
  period_end: date | None = Query(default=None),
  current_user: User = Depends(require_permission(PermissionKey.LABOUR_READ)),
  session: AsyncSession = Depends(get_db),
):
  records = await _service(session).list_attendance(
    current_user.active_membership.organization_id, project_id, period_start, period_end,
  )
  return [
    {"id": r.id, "deployment_id": r.deployment_id, "attendance_date": r.attendance_date,
     "units_present": r.units_present, "notes": r.notes}
    for r in records
  ]

@router.get("/projects/{project_id}/attendance/day-summary", response_model=DayAttendanceSummaryResponse)
async def get_day_attendance_summary(
  project_id: UUID,
  attendance_date: date = Query(...),
  current_user: User = Depends(require_permission(PermissionKey.LABOUR_READ)),
  session: AsyncSession = Depends(get_db),
):
  total, by_trade = await _service(session).get_day_attendance_total(
    current_user.active_membership.organization_id, project_id, attendance_date,
  )
  return DayAttendanceSummaryResponse(
    attendance_date=attendance_date, total_present=total,
    by_trade=[LabourTradeCostResponse(trade=trade, cost=count) for trade, count in by_trade],
  )

@router.get("/projects/{project_id}/cost", response_model=LabourCostResponse)
async def get_labour_cost(
  project_id: UUID,
  period_start: date = Query(...),
  period_end: date = Query(...),
  source_id: UUID | None = Query(default=None),
  worker_id: UUID | None = Query(default=None),
  current_user: User = Depends(require_permission(PermissionKey.LABOUR_READ)),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  total = await service.get_cost(
    current_user.active_membership.organization_id, project_id, period_start, period_end, source_id, worker_id,
  )
  org = current_user.active_membership.organization_id
  return LabourCostResponse(period_start=period_start, period_end=period_end, total_cost=total, currency="PKR")

@router.get("/projects/{project_id}/balance", response_model=LabourBalanceResponse)
async def get_labour_balance(
  project_id: UUID,
  source_id: UUID = Query(...),
  worker_id: UUID | None = Query(default=None),
  current_user: User = Depends(require_permission(PermissionKey.LABOUR_READ)),
  session: AsyncSession = Depends(get_db),
):
  balance = await _service(session).get_balance(
    current_user.active_membership.organization_id, project_id, source_id, worker_id,
  )
  return LabourBalanceResponse(outstanding_advance_balance=balance, currency="PKR")

@router.post("/projects/{project_id}/advances", response_model=LabourAdvanceResponse, status_code=201)
async def record_advance(
  project_id: UUID,
  payload: LabourAdvanceCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.LABOUR_PAYMENT_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).record_advance(
    current_user.active_membership.organization_id, project_id, payload, current_user.id,
  )

@router.get("/projects/{project_id}/advances", response_model=list[LabourAdvanceResponse])
async def list_advances(
  project_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.LABOUR_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).list_advances(current_user.active_membership.organization_id, project_id)

@router.post("/projects/{project_id}/payments", response_model=LabourPaymentResponse, status_code=201)
async def record_payment(
  project_id: UUID,
  payload: LabourPaymentCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.LABOUR_PAYMENT_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).record_payment(
    current_user.active_membership.organization_id, project_id, payload, current_user.id,
  )

@router.get("/projects/{project_id}/payments", response_model=list[LabourPaymentResponse])
async def list_payments(
  project_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.LABOUR_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).list_payments(current_user.active_membership.organization_id, project_id)

@router.get("/projects/{project_id}/summary", response_model=LabourSummaryResponse)
async def get_labour_summary(
  project_id: UUID,
  period_start: date = Query(...),
  period_end: date = Query(...),
  current_user: User = Depends(require_permission(PermissionKey.LABOUR_READ)),
  session: AsyncSession = Depends(get_db),
):
  data = await _service(session).get_project_summary(
    current_user.active_membership.organization_id, project_id, period_start, period_end,
  )
  return LabourSummaryResponse(
    project_id=project_id, period_start=period_start, period_end=period_end,
    total_accrued_cost=data["total_accrued_cost"],
    cost_by_trade=[LabourTradeCostResponse(**row) for row in data["cost_by_trade"]],
    total_advances_given=data["total_advances_given"], total_payments_made=data["total_payments_made"],
    outstanding_advance_balance=data["outstanding_advance_balance"], currency=data["currency"],
  )