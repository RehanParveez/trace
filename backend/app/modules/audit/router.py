from __future__ import annotations
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies.permissions import require_permission
from app.modules.audit.models import AuditAction, AuditEntityType
from app.modules.audit.schemas import AuditLogResponse
from app.modules.audit.service import AuditLogService
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User

router = APIRouter(
  prefix="/audit-log",
  tags=["Audit Log"],
)

def _service(session: AsyncSession) -> AuditLogService:
  return AuditLogService(session)

@router.get("", response_model=list[AuditLogResponse])
async def list_audit_log(
  entity_type: AuditEntityType | None = Query(default=None),
  entity_id: UUID | None = Query(default=None),
  actor_user_id: UUID | None = Query(default=None),
  action: AuditAction | None = Query(default=None),
  created_from: datetime | None = Query(default=None),
  created_to: datetime | None = Query(default=None),
  skip: int = Query(default=0, ge=0),
  limit: int = Query(default=100, ge=1, le=100),
  current_user: User = Depends(
    require_permission(PermissionKey.AUDIT_LOG_READ)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.list_logs(
    current_user.active_membership.organization_id,
    entity_type=entity_type,
    entity_id=entity_id,
    actor_user_id=actor_user_id,
    action=action,
    created_from=created_from,
    created_to=created_to,
    skip=skip,
    limit=limit,
  )

@router.get(
  "/entity/{entity_type}/{entity_id}",
  response_model=list[AuditLogResponse],
)
async def list_audit_log_for_entity(
  entity_type: AuditEntityType,
  entity_id: UUID,
  current_user: User = Depends(
    require_permission(PermissionKey.AUDIT_LOG_READ)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.list_for_entity(
    current_user.active_membership.organization_id, entity_type, entity_id
  )