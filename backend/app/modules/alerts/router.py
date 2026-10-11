from __future__ import annotations
from fastapi import APIRouter, Depends
from app.modules.alerts.schemas import AttentionResponse
from app.modules.identity.models import User, Organization
from app.dependencies.project_access import accessible_project_ids
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.auth import get_current_user
from app.core.database import get_db
from app.modules.alerts.service import AlertsService

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.get("/attention", response_model=AttentionResponse)
async def get_attention(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
  membership = current_user.active_membership
  permissions = {p.key for p in membership.role.permissions}
  items = await AlertsService(session).get_attention(
    membership.organization_id, permissions, await accessible_project_ids(session, current_user),
  )
  organization = await session.get(Organization, membership.organization_id)
  return AttentionResponse(currency=organization.currency if organization else "PKR", items=items)