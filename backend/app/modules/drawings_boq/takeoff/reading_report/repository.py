from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from sqlalchemy import func, select
from app.modules.drawings_boq.takeoff.reading_report.models import ReadingMisreadReport, ReadingOverride

class ReadingReportRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def override_counts(self, org: UUID, drawing_id: UUID) -> dict:
    rows = await self.session.execute(select(ReadingOverride.sheet_id, func.count()).where(ReadingOverride.organization_id == org, ReadingOverride.drawing_id == drawing_id,
      ReadingOverride.status == "ACTIVE").group_by(ReadingOverride.sheet_id))
    return {r[0]: int(r[1]) for r in rows.all()}

  async def misread_counts(self, org: UUID, drawing_id: UUID) -> dict:
    rows = await self.session.execute(select(ReadingMisreadReport.sheet_id, func.count()).where(ReadingMisreadReport.organization_id == org, ReadingMisreadReport.drawing_id == drawing_id,
      ReadingMisreadReport.status.in_(("OPEN", "QUEUED"))).group_by(ReadingMisreadReport.sheet_id))
    return {r[0]: int(r[1]) for r in rows.all()}

  async def overrides(self, org: UUID, drawing_id: UUID, sheet_id: UUID | None = None) -> list[ReadingOverride]:
    stmt = select(ReadingOverride).where(ReadingOverride.organization_id == org, ReadingOverride.drawing_id == drawing_id, ReadingOverride.status == "ACTIVE")
    if sheet_id is not None:
      stmt = stmt.where(ReadingOverride.sheet_id == sheet_id)
    return list((await self.session.execute(stmt.order_by(ReadingOverride.created_at, ReadingOverride.id))).scalars().all())

  async def override(self, org: UUID, drawing_id: UUID, override_id: UUID) -> ReadingOverride | None:
    return (await self.session.execute(select(ReadingOverride).where(ReadingOverride.organization_id == org, ReadingOverride.drawing_id == drawing_id,
      ReadingOverride.id == override_id))).scalar_one_or_none()

  async def misreads(self, org: UUID, drawing_id: UUID, limit: int = 200) -> list[ReadingMisreadReport]:
    return list((await self.session.execute(select(ReadingMisreadReport).where(ReadingMisreadReport.organization_id == org, ReadingMisreadReport.drawing_id == drawing_id)
      .order_by(ReadingMisreadReport.created_at.desc(), ReadingMisreadReport.id).limit(limit))).scalars().all())

  def add(self, row) -> None:
    self.session.add(row)
