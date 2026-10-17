from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.modules.drawings_boq.models import TakeoffExtraction, TakeoffCandidate, TakeoffMeasurement
from sqlalchemy import delete, select

class ExtractRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def extraction(self, org: UUID, sheet_id: UUID) -> TakeoffExtraction | None:
    return (await self.session.execute(
      select(TakeoffExtraction).where(TakeoffExtraction.sheet_id == sheet_id, TakeoffExtraction.organization_id == org))).scalar_one_or_none()

  async def extractions(self, org: UUID, sheet_ids: list[UUID]) -> list[TakeoffExtraction]:
    if not sheet_ids:
      return []
    return list((await self.session.execute(
      select(TakeoffExtraction).where(TakeoffExtraction.organization_id == org, TakeoffExtraction.sheet_id.in_(sheet_ids)))).scalars().all())

  async def candidates(self, org: UUID, sheet_ids: list[UUID]) -> list[TakeoffCandidate]:
    if not sheet_ids:
      return []
    return list((await self.session.execute(
      select(TakeoffCandidate).where(TakeoffCandidate.organization_id == org, TakeoffCandidate.sheet_id.in_(sheet_ids))
      .order_by(TakeoffCandidate.category, TakeoffCandidate.label, TakeoffCandidate.id))).scalars().all())

  async def accepted_with_typed(self, org: UUID, project_id: UUID, limit: int = 600) -> list[TakeoffCandidate]:
    """The newest accepted items of a project. The ones that took a typed size say so in their facts."""
    return list((await self.session.execute(
      select(TakeoffCandidate).where(TakeoffCandidate.organization_id == org, TakeoffCandidate.project_id == project_id, TakeoffCandidate.decision == "ACCEPTED",
        TakeoffCandidate.decided_at.is_not(None)).order_by(TakeoffCandidate.decided_at.desc()).limit(limit))).scalars().all())

  async def candidates_by_ids(self, org: UUID, ids: list[UUID], lock: bool = False) -> list[TakeoffCandidate]:
    if not ids:
      return []
    stmt = select(TakeoffCandidate).where(TakeoffCandidate.organization_id == org, TakeoffCandidate.id.in_(ids))
    if lock:
      stmt = stmt.with_for_update()
    return list((await self.session.execute(stmt)).scalars().all())

  async def existing_measurement_ids(self, org: UUID, ids: list[UUID]) -> set[UUID]:
    if not ids:
      return set()
    rows = await self.session.execute(
      select(TakeoffMeasurement.id).where(TakeoffMeasurement.organization_id == org, TakeoffMeasurement.id.in_(ids)))
    return {r[0] for r in rows.all()}

  async def delete_candidates(self, org: UUID, ids: list[UUID]) -> None:
    if ids:
      await self.session.execute(delete(TakeoffCandidate).where(TakeoffCandidate.organization_id == org, TakeoffCandidate.id.in_(ids)))
