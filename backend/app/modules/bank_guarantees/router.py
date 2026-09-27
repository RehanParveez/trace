from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.bank_guarantees.service import BankGuaranteeService
from app.modules.bank_guarantees.schemas import BankGuaranteeResponse, BankGuaranteeCreateRequest, BankGuaranteeRenewRequest, ProjectBankGuaranteeSummaryResponse
from app.modules.identity.models import User
from fastapi import APIRouter, Depends, Query
from app.dependencies.permissions import require_permission
from app.modules.identity.enums import PermissionKey
from app.core.database import get_db
from uuid import UUID

router = APIRouter(prefix="/bank-guarantees", tags=["Bank Guarantees"])

def _service(session: AsyncSession) -> BankGuaranteeService:
  return BankGuaranteeService(session)

@router.post("", response_model=BankGuaranteeResponse, status_code=201)
async def create_guarantee(
  payload: BankGuaranteeCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.BANK_GUARANTEE_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).create_guarantee(current_user.active_membership.organization_id, payload, current_user.id)

@router.get("", response_model=list[BankGuaranteeResponse])
async def list_guarantees(
  project_id: UUID = Query(...),
  current_user: User = Depends(require_permission(PermissionKey.BANK_GUARANTEE_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).list_guarantees(current_user.active_membership.organization_id, project_id)

@router.get("/{guarantee_id}", response_model=BankGuaranteeResponse)
async def get_guarantee(
  guarantee_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.BANK_GUARANTEE_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).get_guarantee(current_user.active_membership.organization_id, guarantee_id)

@router.get("/projects/{project_id}/summary", response_model=ProjectBankGuaranteeSummaryResponse)
async def get_project_summary(
  project_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.BANK_GUARANTEE_READ)),
  session: AsyncSession = Depends(get_db),
):
  data = await _service(session).get_project_summary(current_user.active_membership.organization_id, project_id)
  return ProjectBankGuaranteeSummaryResponse(**data)

@router.post("/{guarantee_id}/renew", response_model=BankGuaranteeResponse)
async def renew_guarantee(
  guarantee_id: UUID,
  payload: BankGuaranteeRenewRequest,
  current_user: User = Depends(require_permission(PermissionKey.BANK_GUARANTEE_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).renew_guarantee(current_user.active_membership.organization_id, guarantee_id, payload, current_user.id)

@router.post("/{guarantee_id}/release", response_model=BankGuaranteeResponse)
async def release_guarantee(
  guarantee_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.BANK_GUARANTEE_RELEASE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).release_guarantee(current_user.active_membership.organization_id, guarantee_id, current_user.id)

@router.post("/{guarantee_id}/mark-called", response_model=BankGuaranteeResponse)
async def mark_called(
  guarantee_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.BANK_GUARANTEE_RELEASE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).mark_called(current_user.active_membership.organization_id, guarantee_id, current_user.id)