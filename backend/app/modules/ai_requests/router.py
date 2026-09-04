from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies.permissions import require_permission
from app.modules.ai_requests.models import AIEntityType, AIRequestPurpose
from app.modules.ai_requests.schemas import AIRequestResponse, AIUsageSummaryResponse
from app.modules.ai_requests.service import AIOrchestratorService
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User

router = APIRouter(
  prefix="/ai-requests",
  tags=["AI Requests"],
)

def _service(session: AsyncSession) -> AIOrchestratorService:
  return AIOrchestratorService(session)

@router.get("", response_model=list[AIRequestResponse])
async def list_ai_requests(
  purpose: AIRequestPurpose | None = Query(default=None),
  entity_type: AIEntityType | None = Query(default=None),
  entity_id: UUID | None = Query(default=None),
  skip: int = Query(default=0, ge=0),
  limit: int = Query(default=100, ge=1, le=100),
  current_user: User = Depends(
    require_permission(PermissionKey.AI_REQUEST_READ)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.list_requests(
    current_user.active_membership.organization_id,
    purpose=purpose,
    entity_type=entity_type,
    entity_id=entity_id,
    skip=skip,
    limit=limit,
  )

@router.get("/usage-summary", response_model=AIUsageSummaryResponse)
async def get_ai_usage_summary(
  current_user: User = Depends(
    require_permission(PermissionKey.AI_REQUEST_READ)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  summary = await service.get_usage_summary(current_user.active_membership.organization_id)
  return AIUsageSummaryResponse(**summary)