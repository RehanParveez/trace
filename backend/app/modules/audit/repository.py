from __future__ import annotations
from datetime import datetime
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.audit.models import AuditAction, AuditEntityType, AuditLog

class AuditLogRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create(self, entry: AuditLog) -> AuditLog:
    self.session.add(entry)
    await self.session.flush()
    return entry

  async def list_by_org(
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
    query = select(AuditLog).where(
      AuditLog.organization_id == organization_id
    )

    if entity_type is not None:
      query = query.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
      query = query.where(AuditLog.entity_id == entity_id)
    if actor_user_id is not None:
      query = query.where(AuditLog.actor_user_id == actor_user_id)
    if action is not None:
      query = query.where(AuditLog.action == action)
    if created_from is not None:
      query = query.where(AuditLog.created_at >= created_from)
    if created_to is not None:
      query = query.where(AuditLog.created_at <= created_to)

    query = (
      query
      .order_by(AuditLog.created_at.desc())
      .offset(skip)
      .limit(limit)
    )
    result = await self.session.execute(query)
    return list(result.scalars().unique())

  async def list_for_entity(
    self,
    organization_id: UUID,
    entity_type: AuditEntityType,
    entity_id: UUID,
  ) -> list[AuditLog]:
    result = await self.session.execute(
      select(AuditLog)
      .where(
        AuditLog.organization_id == organization_id,
        AuditLog.entity_type == entity_type,
        AuditLog.entity_id == entity_id,
      )
      .order_by(AuditLog.created_at.desc())
    )
    return list(result.scalars().unique())