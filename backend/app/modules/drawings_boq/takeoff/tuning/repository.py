from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.modules.drawings_boq.takeoff.tuning.models import ReadingSweep
from sqlalchemy import delete, select

class SweepRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  def add(self, row: ReadingSweep) -> None:
    self.session.add(row)

  async def list(self, org: UUID, drawing_id: UUID, limit: int = 50) -> list[ReadingSweep]:
    return list((await self.session.execute(select(ReadingSweep).where(ReadingSweep.organization_id == org, ReadingSweep.drawing_id == drawing_id)
      .order_by(ReadingSweep.created_at.desc(), ReadingSweep.id).limit(limit))).scalars().all())

  async def get(self, org: UUID, sweep_id: UUID) -> ReadingSweep | None:
    return (await self.session.execute(select(ReadingSweep).where(ReadingSweep.organization_id == org, ReadingSweep.id == sweep_id))).scalar_one_or_none()

  async def delete(self, org: UUID, sweep_id: UUID) -> int:
    return (await self.session.execute(delete(ReadingSweep).where(ReadingSweep.organization_id == org, ReadingSweep.id == sweep_id))).rowcount or 0
