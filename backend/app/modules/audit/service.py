from __future__ import annotations
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.audit.models import AuditAction, AuditEntityType, AuditLog
from app.modules.audit.repository import AuditLogRepository

class AuditLogService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repository = AuditLogRepository(session)

  async def log(
    self,
    organization_id: UUID,
    actor_user_id: UUID | None,
    entity_type: AuditEntityType,
    entity_id: UUID | None,
    action: AuditAction,
    summary: str,
    changes: dict | None = None,
    ip_address: str | None = None,
    *,
    commit: bool = True,
  ) -> AuditLog:
    entry = AuditLog(
      id=uuid4(),
      organization_id=organization_id,
      actor_user_id=actor_user_id,
      entity_type=entity_type,
      entity_id=entity_id,
      action=action,
      summary=summary,
      changes=changes or {},
      ip_address=ip_address,
    )
    entry = await self.repository.create(entry)
    if commit:
      await self.session.commit()
    return entry

  async def list_logs(
    self,
    organization_id: UUID,
    *,
    entity_type: AuditEntityType | None = None,
    entity_id: UUID | None = None,
    actor_user_id: UUID | None = None,
    action: AuditAction | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    skip: int = 0,
    limit: int = 100,
  ) -> list[AuditLog]:
    return await self.repository.list_by_org(
      organization_id,
      entity_type=entity_type,
      entity_id=entity_id,
      actor_user_id=actor_user_id,
      action=action,
      created_from=created_from,
      created_to=created_to,
      skip=skip,
      limit=limit,
    )

  async def list_for_entity(
    self,
    organization_id: UUID,
    entity_type: AuditEntityType,
    entity_id: UUID,
  ) -> list[AuditLog]:
    return await self.repository.list_for_entity(
      organization_id, entity_type, entity_id
    )