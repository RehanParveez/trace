from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from uuid import UUID
from app.modules.drawings_boq.pricing.billing.schemas import BillingResponse
from app.dependencies.permissions import require_permission
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.pricing.billing.service import BillingService

router = APIRouter(tags=["Billing"])
_READ = PermissionKey.DRAWING_READ

def _org(user: User) -> UUID:
  return user.active_membership.organization_id

@router.get("/projects/{project_id}/billing", response_model=BillingResponse)
async def project_billing(project_id: UUID, profile: str | None = Query(None, description="PRIVATE_QS (default) or MRS_PB."),
    current_user: User = Depends(require_permission(_READ)), session: AsyncSession = Depends(get_db)):
  return await BillingService(session).billed(_org(current_user), project_id, profile)
