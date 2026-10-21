from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.modules.drawings_boq.takeoff.reading_score.models import ReadingLabel, ReadingScore
from sqlalchemy import delete, select

class ReadingScoreRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def labels(self, org: UUID, drawing_id: UUID, source: str | None = None) -> list[ReadingLabel]:
    stmt = select(ReadingLabel).where(ReadingLabel.organization_id == org, ReadingLabel.drawing_id == drawing_id)
    if source:
      stmt = stmt.where(ReadingLabel.source == source)
    return list((await self.session.execute(stmt.order_by(ReadingLabel.sheet_id, ReadingLabel.source, ReadingLabel.source_ref))).scalars().all())

  def add_labels(self, rows: list[ReadingLabel]) -> None:
    self.session.add_all(rows)

  async def delete_labels(self, org: UUID, drawing_id: UUID, source: str | None = None, ids: list[UUID] | None = None) -> int:
    stmt = delete(ReadingLabel).where(ReadingLabel.organization_id == org, ReadingLabel.drawing_id == drawing_id)
    
    if source:
      stmt = stmt.where(ReadingLabel.source == source)
    if ids is not None:
      if not ids:
        return 0
      stmt = stmt.where(ReadingLabel.id.in_(ids))
    return (await self.session.execute(stmt)).rowcount or 0

  def add_score(self, row: ReadingScore) -> None:
    self.session.add(row)

  async def scores(self, org: UUID, drawing_id: UUID, limit: int = 50) -> list[ReadingScore]:
    return list((await self.session.execute(
      select(ReadingScore).where(ReadingScore.organization_id == org, ReadingScore.drawing_id == drawing_id)
      .order_by(ReadingScore.created_at.desc(), ReadingScore.id).limit(limit))).scalars().all())

  async def score(self, org: UUID, score_id: UUID) -> ReadingScore | None:
    return (await self.session.execute(select(ReadingScore).where(ReadingScore.organization_id == org, ReadingScore.id == score_id))).scalar_one_or_none()

  async def comparable(self, org: UUID, drawing_id: UUID, rule_hash: str, labels_stamp: str, mode: str, label_drawing_id: UUID | None) -> list[ReadingScore]:
    stmt = select(ReadingScore).where(ReadingScore.organization_id == org, ReadingScore.drawing_id == drawing_id, ReadingScore.rule_hash == rule_hash,
      ReadingScore.labels_stamp == labels_stamp, ReadingScore.mode == mode, ReadingScore.status != "PARTIAL")
    stmt = stmt.where(ReadingScore.label_drawing_id.is_(None) if label_drawing_id is None else ReadingScore.label_drawing_id == label_drawing_id)
    return list((await self.session.execute(stmt.order_by(ReadingScore.created_at))).scalars().all())
