from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.modules.site_progress.models import SiteLogEntry
from sqlalchemy import select

class SiteProgressRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def list_logs(
    self,
    organization_id: UUID,
    project_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
  ) -> list[SiteLogEntry]:
    q = select(SiteLogEntry).where(
      SiteLogEntry.organization_id == organization_id,
    )
    if project_id is not None:
      q = q.where(SiteLogEntry.project_id == project_id)
    q = q.order_by(SiteLogEntry.log_date.desc(), SiteLogEntry.created_at.desc())
    q = q.offset(skip).limit(limit)
    result = await self.session.execute(q)
    return list(result.scalars().all())

  async def get_by_id(
    self, log_id: UUID, organization_id: UUID,
  ) -> SiteLogEntry | None:
    result = await self.session.execute(
      select(SiteLogEntry).where(
        SiteLogEntry.id == log_id,
        SiteLogEntry.organization_id == organization_id,
      )
    )
    return result.scalar_one_or_none()

  async def create(self, entry: SiteLogEntry) -> SiteLogEntry:
    self.session.add(entry)
    await self.session.flush()
    return entry

  async def delete(self, entry: SiteLogEntry) -> None:
    await self.session.delete(entry)
    await self.session.flush()