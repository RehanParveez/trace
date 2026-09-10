from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.budgets.service import BudgetService
from app.modules.budgets.schemas import BudgetResponse, BudgetSaveRequest
from uuid import UUID
from app.modules.identity.models import User
from fastapi import APIRouter, Depends, Query
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.modules.identity.enums import PermissionKey

router = APIRouter(prefix="/budgets", tags=["Budgets"])

def _service(session: AsyncSession) -> BudgetService:
  return BudgetService(session)

@router.get("", response_model=list[BudgetResponse])
async def list_budgets(
  project_id: UUID | None = Query(default=None),
  current_user: User = Depends(require_permission(PermissionKey.BUDGET_READ)),
  session: AsyncSession = Depends(get_db),
):
  org_id = current_user.active_membership.organization_id
  return await _service(session).list_budgets(org_id, project_id)

@router.put("/project/{project_id}", response_model=BudgetResponse)
async def save_budget(
  project_id: UUID,
  payload: BudgetSaveRequest,
  current_user: User = Depends(require_permission(PermissionKey.BUDGET_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  
  if payload.project_id != project_id:
    payload = payload.model_copy(update={"project_id": project_id})
  org_id = current_user.active_membership.organization_id
  return await _service(session).save_budget(org_id, payload)