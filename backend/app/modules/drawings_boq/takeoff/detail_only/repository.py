from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from sqlalchemy import delete, select
from app.modules.drawings_boq.takeoff.detail_only.models import DetailMarkDecision

class DetailOnlyRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def decisions(self, org: UUID, drawing_id: UUID) -> list[DetailMarkDecision]:
    return list((await self.session.execute(select(DetailMarkDecision).where(DetailMarkDecision.organization_id == org, DetailMarkDecision.drawing_id == drawing_id)
      .order_by(DetailMarkDecision.created_at, DetailMarkDecision.id))).scalars().all())

  async def decision(self, org: UUID, decision_id: UUID) -> DetailMarkDecision | None:
    return (await self.session.execute(select(DetailMarkDecision).where(DetailMarkDecision.organization_id == org, DetailMarkDecision.id == decision_id))).scalar_one_or_none()

  def add(self, row: DetailMarkDecision) -> None:
    self.session.add(row)

  async def delete_for_row(self, org: UUID, drawing_id: UUID, kind: str, sheet_id: UUID | None, ckey: str | None) -> int:
    stmt = delete(DetailMarkDecision).where(DetailMarkDecision.organization_id == org, DetailMarkDecision.drawing_id == drawing_id, DetailMarkDecision.kind == kind)
    stmt = stmt.where(DetailMarkDecision.sheet_id.is_(None) if sheet_id is None else DetailMarkDecision.sheet_id == sheet_id)
    stmt = stmt.where(DetailMarkDecision.ckey.is_(None) if ckey is None else DetailMarkDecision.ckey == ckey)
    return (await self.session.execute(stmt)).rowcount or 0

  async def delete_depth(self, org: UUID, drawing_id: UUID, mark: str) -> int:
    return (await self.session.execute(delete(DetailMarkDecision).where(DetailMarkDecision.organization_id == org, DetailMarkDecision.drawing_id == drawing_id,
      DetailMarkDecision.kind == "BEAM_DEPTH", DetailMarkDecision.mark == mark))).rowcount or 0

  async def delete(self, org: UUID, decision_id: UUID) -> int:
    return (await self.session.execute(delete(DetailMarkDecision).where(DetailMarkDecision.organization_id == org, DetailMarkDecision.id == decision_id))).rowcount or 0