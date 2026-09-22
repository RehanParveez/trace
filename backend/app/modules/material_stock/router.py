from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.modules.material_stock.schemas import MaterialIssueCreateRequest, MaterialIssueResponse, MaterialStockReconciliationResponse
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from app.modules.material_stock.service import MaterialStockService

router = APIRouter(prefix="/material-stock", tags=["Material Stock"])

def _service(session: AsyncSession) -> MaterialStockService:
  return MaterialStockService(session)

@router.post("/projects/{project_id}/issues", response_model=MaterialIssueResponse, status_code=201)
async def record_issue(
  project_id: UUID,
  payload: MaterialIssueCreateRequest,
  current_user: User = Depends(require_permission(PermissionKey.MATERIAL_STOCK_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).record_issue(
    current_user.active_membership.organization_id, project_id, payload, current_user.id,
  )

@router.get("/projects/{project_id}/issues", response_model=list[MaterialIssueResponse])
async def list_issues(
  project_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.MATERIAL_STOCK_READ)),
  session: AsyncSession = Depends(get_db),
):
  return await _service(session).list_issues(current_user.active_membership.organization_id, project_id)

@router.get("/projects/{project_id}/reconciliation", response_model=MaterialStockReconciliationResponse)
async def get_reconciliation(
  project_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.MATERIAL_STOCK_READ)),
  session: AsyncSession = Depends(get_db),
):
  data = await _service(session).get_reconciliation(current_user.active_membership.organization_id, project_id)
  return MaterialStockReconciliationResponse(**data)