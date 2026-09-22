from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.subcontractors.service import SubcontractorService
from app.modules.identity.models import User
from app.core.database import get_db
from app.dependencies.permissions import require_permission
from app.modules.identity.enums import PermissionKey
from app.modules.subcontractors.schemas import (ProjectSubcontractCostResponse, SubcontractAgreementCreateRequest, SubcontractAgreementDetailResponse, SubcontractAgreementResponse, SubcontractAgreementUpdateRequest, SubcontractorAdvanceCreateRequest,
  SubcontractorAdvanceResponse, SubcontractorBillCancelRequest, SubcontractorBillCreateRequest, SubcontractorBillDetailResponse, SubcontractorBillIssueRequest, SubcontractorBillResponse,
  SubcontractorCreateRequest, SubcontractorLedgerResponse, SubcontractorPaymentCreateRequest, SubcontractorPaymentResponse, SubcontractorResponse, SubcontractorUpdateRequest,
)

router = APIRouter(prefix="/subcontractors", tags=["Subcontractors"])

def _service(session: AsyncSession) -> SubcontractorService:
  return SubcontractorService(session)

@router.post("", response_model=SubcontractorResponse, status_code=201)
async def create_subcontractor(
  payload: SubcontractorCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.SUBCONTRACTOR_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).create_subcontractor(current_user.active_membership.organization_id, payload)

@router.get("", response_model=list[SubcontractorResponse])
async def list_subcontractors(
  current_user: User = Depends(require_permission(PermissionKey.SUBCONTRACTOR_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).list_subcontractors(current_user.active_membership.organization_id)

@router.patch("/{subcontractor_id}", response_model=SubcontractorResponse)
async def update_subcontractor(
  subcontractor_id: UUID,
  payload: SubcontractorUpdateRequest,
  current_user: User = Depends(require_permission(PermissionKey.SUBCONTRACTOR_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).update_subcontractor(current_user.active_membership.organization_id, subcontractor_id, payload)

@router.post("/agreements", response_model=SubcontractAgreementDetailResponse, status_code=201)
async def create_agreement(
  payload: SubcontractAgreementCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.SUBCONTRACTOR_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).create_agreement(current_user.active_membership.organization_id, payload)

@router.get("/agreements/{agreement_id}", response_model=SubcontractAgreementDetailResponse)
async def get_agreement(
  agreement_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.SUBCONTRACTOR_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).get_agreement(current_user.active_membership.organization_id, agreement_id)

@router.patch("/agreements/{agreement_id}", response_model=SubcontractAgreementResponse)
async def update_agreement(
  agreement_id: UUID,
  payload: SubcontractAgreementUpdateRequest,
  current_user: User = Depends(require_permission(PermissionKey.SUBCONTRACTOR_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).update_agreement(current_user.active_membership.organization_id, agreement_id, payload)

@router.get("/projects/{project_id}/agreements", response_model=list[SubcontractAgreementDetailResponse])
async def list_agreements(
  project_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.SUBCONTRACTOR_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).list_agreements(current_user.active_membership.organization_id, project_id)

@router.get("/projects/{project_id}/cost-summary", response_model=ProjectSubcontractCostResponse)
async def get_project_cost_summary(
  project_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.SUBCONTRACTOR_READ)),
  session: AsyncSession = Depends(get_db),
):
  data = await _service(session).get_project_cost_summary(current_user.active_membership.organization_id, project_id)
  return ProjectSubcontractCostResponse(**data)

@router.post("/agreements/{agreement_id}/bills", response_model=SubcontractorBillDetailResponse, status_code=201)
async def create_bill(
  agreement_id: UUID,
  payload: SubcontractorBillCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.SUBCONTRACTOR_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  payload.agreement_id = agreement_id
  return await _service(session).generate_draft_bill(current_user.active_membership.organization_id, payload, current_user.id)

@router.get("/agreements/{agreement_id}/bills", response_model=list[SubcontractorBillResponse])
async def list_bills(
  agreement_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.SUBCONTRACTOR_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).list_bills(current_user.active_membership.organization_id, agreement_id)

@router.get("/bills/{bill_id}", response_model=SubcontractorBillDetailResponse)
async def get_bill(
  bill_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.SUBCONTRACTOR_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).get_bill(current_user.active_membership.organization_id, bill_id)

@router.post("/bills/{bill_id}/issue", response_model=SubcontractorBillResponse)
async def issue_bill(
  bill_id: UUID,
  payload: SubcontractorBillIssueRequest,
  current_user: User = Depends(require_permission(PermissionKey.SUBCONTRACTOR_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).issue_bill(current_user.active_membership.organization_id, bill_id, payload.version, current_user.id)

@router.post("/bills/{bill_id}/cancel", response_model=SubcontractorBillResponse)
async def cancel_bill(
  bill_id: UUID,
  payload: SubcontractorBillCancelRequest,
  current_user: User = Depends(require_permission(PermissionKey.SUBCONTRACTOR_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).cancel_bill(current_user.active_membership.organization_id, bill_id, payload.version, current_user.id)

@router.get("/bills/{bill_id}/export/pdf")
async def export_bill_pdf(
  bill_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.SUBCONTRACTOR_READ)),
  session: AsyncSession = Depends(get_db),
):
  content, filename = await _service(session).export_pdf(current_user.active_membership.organization_id, bill_id)
  return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})

@router.get("/bills/{bill_id}/export/xlsx")
async def export_bill_xlsx(
  bill_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.SUBCONTRACTOR_READ)),
  session: AsyncSession = Depends(get_db),
):
  content, filename = await _service(session).export_xlsx(current_user.active_membership.organization_id, bill_id)
  return Response(content=content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{filename}"'})

@router.post("/agreements/{agreement_id}/advances", response_model=SubcontractorAdvanceResponse, status_code=201)
async def record_advance(
  agreement_id: UUID,
  payload: SubcontractorAdvanceCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.SUBCONTRACTOR_PAYMENT_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).record_advance(current_user.active_membership.organization_id, agreement_id, payload, current_user.id)

@router.get("/agreements/{agreement_id}/advances", response_model=list[SubcontractorAdvanceResponse])
async def list_advances(
  agreement_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.SUBCONTRACTOR_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).list_advances(current_user.active_membership.organization_id, agreement_id)

@router.post("/agreements/{agreement_id}/payments", response_model=SubcontractorPaymentResponse, status_code=201)
async def record_payment(
  agreement_id: UUID,
  payload: SubcontractorPaymentCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.SUBCONTRACTOR_PAYMENT_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).record_payment(current_user.active_membership.organization_id, agreement_id, payload, current_user.id)

@router.get("/agreements/{agreement_id}/payments", response_model=list[SubcontractorPaymentResponse])
async def list_payments(
  agreement_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.SUBCONTRACTOR_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).list_payments(current_user.active_membership.organization_id, agreement_id)

@router.get("/agreements/{agreement_id}/ledger", response_model=SubcontractorLedgerResponse)
async def get_ledger(
  agreement_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.SUBCONTRACTOR_READ)),
  session: AsyncSession = Depends(get_db),
):
  data = await _service(session).get_ledger(current_user.active_membership.organization_id, agreement_id)
  return SubcontractorLedgerResponse(**data)