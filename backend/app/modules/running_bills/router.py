from __future__ import annotations
from fastapi import APIRouter, Depends, Query, Response
from uuid import UUID
from app.modules.identity.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.running_bills.service import RunningBillService
from app.modules.running_bills.schemas import RunningBillCancelRequest, RunningBillCreateRequest, RunningBillDetailResponse, RunningBillIssueRequest, RunningBillResponse
from app.core.database import get_db
from app.dependencies.permissions import require_permission
from app.modules.identity.enums import PermissionKey

router = APIRouter(prefix="/running-bills", tags=["Running Bills"])

def _service(session: AsyncSession) -> RunningBillService:
  return RunningBillService(session)

@router.get("", response_model=list[RunningBillResponse])
async def list_running_bills(
  project_id: UUID = Query(...),
  current_user: User = Depends(require_permission(PermissionKey.RUNNING_BILL_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).list_bills(current_user.active_membership.organization_id, project_id)

@router.get("/{bill_id}", response_model=RunningBillDetailResponse)
async def get_running_bill(
  bill_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.RUNNING_BILL_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).get_bill(current_user.active_membership.organization_id, bill_id)


@router.post("", response_model=RunningBillDetailResponse, status_code=201)
async def create_running_bill(
  payload: RunningBillCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.RUNNING_BILL_CREATE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).generate_draft(
    current_user.active_membership.organization_id, payload, current_user.id,
  )

@router.post("/{bill_id}/issue", response_model=RunningBillResponse)
async def issue_running_bill(
  bill_id: UUID,
  payload: RunningBillIssueRequest,
  current_user: User = Depends(require_permission(PermissionKey.RUNNING_BILL_ISSUE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).issue_bill(
    current_user.active_membership.organization_id, bill_id, payload.version, current_user.id,
  )

@router.post("/{bill_id}/cancel", response_model=RunningBillResponse)
async def cancel_running_bill(
  bill_id: UUID,
  payload: RunningBillCancelRequest,
  current_user: User = Depends(require_permission(PermissionKey.RUNNING_BILL_ISSUE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).cancel_bill(
    current_user.active_membership.organization_id, bill_id, payload.version, current_user.id,
  )

@router.get("/{bill_id}/export/pdf")
async def export_running_bill_pdf(
  bill_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.RUNNING_BILL_READ)),
  session: AsyncSession = Depends(get_db),
):
  pdf_bytes, filename = await _service(session).export_pdf(current_user.active_membership.organization_id, bill_id)
  return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/{bill_id}/export/xlsx")
async def export_running_bill_xlsx(
  bill_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.RUNNING_BILL_READ)),
  session: AsyncSession = Depends(get_db),
):
  xlsx_bytes, filename = await _service(session).export_xlsx(current_user.active_membership.organization_id, bill_id)
  return Response(
    content=xlsx_bytes, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    headers={"Content-Disposition": f'attachment; filename="{filename}"'},
  )