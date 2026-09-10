from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.modules.expenses.models import ExpenseStatus
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.modules.identity.models import User
from app.modules.identity.enums import PermissionKey
from app.modules.expenses.schemas import ExpenseCreateRequest, ExpenseResponse, ExpenseReviewRequest
from app.modules.expenses.service import ExpenseService

router = APIRouter(prefix="/expenses", tags=["Expenses"])

def _service(session: AsyncSession) -> ExpenseService:
  return ExpenseService(session)

@router.get("", response_model=list[ExpenseResponse])
async def list_expenses(
  project_id: UUID | None = Query(default=None),
  status: ExpenseStatus | None = Query(default=None),
  skip: int = Query(default=0, ge=0),
  limit: int = Query(default=100, ge=1, le=200),
  current_user: User = Depends(require_permission(PermissionKey.EXPENSE_READ)),
  session: AsyncSession = Depends(get_db),
):
  org_id = current_user.active_membership.organization_id
  return await _service(session).list_expenses(
    org_id, project_id, status, skip, limit,
  )

@router.post("", response_model=ExpenseResponse, status_code=201)
async def create_expense(
  payload: ExpenseCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.EXPENSE_CREATE)),
  session: AsyncSession = Depends(get_db),
):
  org_id = current_user.active_membership.organization_id
  return await _service(session).create_expense(org_id, current_user.id, payload)

@router.post("/{expense_id}/approve", response_model=ExpenseResponse)
async def approve_expense(
  expense_id: UUID,
  payload: ExpenseReviewRequest,
  current_user: User = Depends(require_permission(PermissionKey.EXPENSE_APPROVE)),
  session: AsyncSession = Depends(get_db),
):
  org_id = current_user.active_membership.organization_id
  return await _service(session).approve_expense(
    org_id, expense_id, current_user.id, payload,
  )

@router.post("/{expense_id}/reject", response_model=ExpenseResponse)
async def reject_expense(
  expense_id: UUID,
  payload: ExpenseReviewRequest,
  current_user: User = Depends(require_permission(PermissionKey.EXPENSE_APPROVE)),
  session: AsyncSession = Depends(get_db),
):
  org_id = current_user.active_membership.organization_id
  return await _service(session).reject_expense(
    org_id, expense_id, current_user.id, payload,
  )