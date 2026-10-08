from __future__ import annotations
from uuid import UUID
from app.modules.drawings_boq.models import RateBook, MaterialLibrary, ProjectRateOverride, RateAnalysis, RateAnalysisComponent,  RateBookEscalation, RateItem
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, func, or_, select, tuple_
from datetime import date
from sqlalchemy.orm import selectinload
from app.modules.drawings_boq.models import BOQItem

_CHUNK = 500

def _visible(org: UUID):
  return or_(RateBook.organization_id.is_(None), RateBook.organization_id == org)

class RateRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  def add(self, obj) -> None:
    self.session.add(obj)

  async def delete(self, obj) -> None:
    await self.session.delete(obj)
    await self.session.flush()

  async def get_book(self, book_id: UUID, org: UUID, *, for_update: bool = False) -> RateBook | None:
    q = select(RateBook).where(RateBook.id == book_id, _visible(org))
    if for_update:
      q = q.with_for_update()
    return (await self.session.execute(q)).scalar_one_or_none()

  async def list_books(self, org: UUID, *, status: str | None, owner: str, after: UUID | None, limit: int) -> list[RateBook]:
    q = select(RateBook).where(_visible(org))
    if status:
      q = q.where(RateBook.status == status)
    if owner == "system":
      q = q.where(RateBook.organization_id.is_(None))
    elif owner == "org":
      q = q.where(RateBook.organization_id == org)
    if after is not None:
      row = await self.get_book(after, org)
      if row is not None:
        q = q.where(tuple_(RateBook.code, RateBook.immutable_version, RateBook.id) > tuple_(row.code, row.immutable_version, row.id))
    q = q.order_by(RateBook.code.asc(), RateBook.immutable_version.asc(), RateBook.id.asc()).limit(limit + 1)
    return list((await self.session.execute(q)).scalars().all())

  async def max_version(self, org: UUID | None, code: str) -> int:
    clause = RateBook.organization_id.is_(None) if org is None else RateBook.organization_id == org
    r = await self.session.execute(select(func.max(RateBook.immutable_version)).where(RateBook.code == code, clause))
    return int(r.scalar_one_or_none() or 0)

  async def active_book(self, org: UUID | None, code: str) -> RateBook | None:
    clause = RateBook.organization_id.is_(None) if org is None else RateBook.organization_id == org
    r = await self.session.execute(select(RateBook).where(RateBook.code == code, RateBook.status == "ACTIVE", clause))
    return r.scalar_one_or_none()

  async def books_by_ids(self, ids: list[UUID], org: UUID) -> list[RateBook]:
    if not ids:
      return []
    r = await self.session.execute(select(RateBook).where(RateBook.id.in_(ids), _visible(org)))
    found = {b.id: b for b in r.scalars().all()}
    return [found[i] for i in ids if i in found]

  async def default_stack(self, org: UUID, as_of: date) -> list[RateBook]:
    q = (select(RateBook)
      .where(_visible(org), RateBook.status == "ACTIVE", RateBook.is_active.is_(True),
        or_(RateBook.effective_from.is_(None), RateBook.effective_from <= as_of),
        or_(RateBook.effective_to.is_(None), RateBook.effective_to >= as_of)))
    books = list((await self.session.execute(q)).scalars().all())
    books.sort(key=lambda b: (
      0 if b.organization_id is not None else 1,
      -(b.effective_from.toordinal() if b.effective_from else 0),
      b.code, -b.immutable_version))
    return books

  async def book_counts(self, book_ids: list[UUID]) -> dict[UUID, dict]:
    out = {i: {"item_count": 0, "analysis_count": 0, "escalation_count": 0} for i in book_ids}
    if not book_ids:
      return out
    for model, key in ((RateItem, "item_count"), (RateAnalysis, "analysis_count"), (RateBookEscalation, "escalation_count")):
      r = await self.session.execute(
        select(model.rate_book_id, func.count()).where(model.rate_book_id.in_(book_ids)).group_by(model.rate_book_id))
      for bid, n in r.all():
        out[bid][key] = n
    return out

  async def supersede(self, book_id: UUID) -> None:
    book = await self.session.get(RateBook, book_id)
    book.status = "SUPERSEDED"
    await self.session.flush()

  async def get_item(self, item_id: UUID, org: UUID, *, for_update: bool = False) -> RateItem | None:
    q = (select(RateItem).join(RateBook, RateBook.id == RateItem.rate_book_id)
      .where(RateItem.id == item_id, _visible(org)))
    if for_update:
      q = q.with_for_update(of=RateItem)
    return (await self.session.execute(q)).scalar_one_or_none()

  async def item_by_key(self, book_id: UUID, code: str, unit: str) -> RateItem | None:
    r = await self.session.execute(select(RateItem).where(
      RateItem.rate_book_id == book_id, RateItem.work_item_code == code, RateItem.unit == unit))
    return r.scalar_one_or_none()

  async def list_items(self, book_id: UUID, *, q: str | None, trade: str | None, only_active: bool,
    after: UUID | None, limit: int) -> list[RateItem]:
    stmt = select(RateItem).where(RateItem.rate_book_id == book_id)
    if q:
      like = f"%{q.strip().lower()}%"
      stmt = stmt.where(or_(func.lower(RateItem.work_item_code).like(like), func.lower(func.coalesce(RateItem.description, "")).like(like)))
    if trade:
      stmt = stmt.where(func.lower(RateItem.trade) == trade.strip().lower())
    if only_active:
      stmt = stmt.where(RateItem.is_active.is_(True))
    if after is not None:
      row = (await self.session.execute(select(RateItem).where(RateItem.id == after, RateItem.rate_book_id == book_id))).scalar_one_or_none()
      if row is not None:
        stmt = stmt.where(tuple_(RateItem.work_item_code, RateItem.unit, RateItem.id) > tuple_(row.work_item_code, row.unit, row.id))
    stmt = stmt.order_by(RateItem.work_item_code.asc(), RateItem.unit.asc(), RateItem.id.asc()).limit(limit + 1)
    return list((await self.session.execute(stmt)).scalars().all())

  async def all_items(self, book_id: UUID) -> list[RateItem]:
    r = await self.session.execute(select(RateItem).where(RateItem.rate_book_id == book_id)
      .order_by(RateItem.work_item_code.asc(), RateItem.unit.asc()))
    return list(r.scalars().all())

  async def items_for_codes(self, book_ids: list[UUID], codes: set[str]) -> dict[tuple, list[RateItem]]:
    out: dict[tuple, list[RateItem]] = {}
    if not book_ids or not codes:
      return out
    ordered = sorted(codes)
    for i in range(0, len(ordered), _CHUNK):
      r = await self.session.execute(select(RateItem).where(
        RateItem.rate_book_id.in_(book_ids), RateItem.work_item_code.in_(ordered[i:i + _CHUNK]),
        RateItem.is_active.is_(True)))
      for it in r.scalars().all():
        out.setdefault((it.rate_book_id, it.work_item_code), []).append(it)
    return out

  async def list_escalations(self, book_id: UUID) -> list[RateBookEscalation]:
    r = await self.session.execute(select(RateBookEscalation).where(RateBookEscalation.rate_book_id == book_id)
      .order_by(RateBookEscalation.effective_from.asc(), RateBookEscalation.trade_scope.asc()))
    return list(r.scalars().all())

  async def get_escalation(self, esc_id: UUID, org: UUID) -> RateBookEscalation | None:
    r = await self.session.execute(select(RateBookEscalation).join(RateBook, RateBook.id == RateBookEscalation.rate_book_id)
      .where(RateBookEscalation.id == esc_id, _visible(org)))
    return r.scalar_one_or_none()

  async def escalation_by_key(self, book_id: UUID, scope: str, effective_from: date) -> RateBookEscalation | None:
    r = await self.session.execute(select(RateBookEscalation).where(
      RateBookEscalation.rate_book_id == book_id, RateBookEscalation.trade_scope == scope,
      RateBookEscalation.effective_from == effective_from))
    return r.scalar_one_or_none()

  async def escalations_for_books(self, book_ids: list[UUID]) -> dict[UUID, list[RateBookEscalation]]:
    out: dict[UUID, list[RateBookEscalation]] = {}
    if not book_ids:
      return out
    r = await self.session.execute(select(RateBookEscalation).where(RateBookEscalation.rate_book_id.in_(book_ids)))
    for e in r.scalars().all():
      out.setdefault(e.rate_book_id, []).append(e)
    return out

  async def get_analysis(self, analysis_id: UUID, org: UUID, *, for_update: bool = False) -> RateAnalysis | None:
    q = (select(RateAnalysis).join(RateBook, RateBook.id == RateAnalysis.rate_book_id)
      .where(RateAnalysis.id == analysis_id, _visible(org)).options(selectinload(RateAnalysis.components)))
    if for_update:
      q = q.with_for_update(of=RateAnalysis)
    return (await self.session.execute(q)).scalar_one_or_none()

  async def list_analyses(self, book_id: UUID) -> list[RateAnalysis]:
    r = await self.session.execute(select(RateAnalysis).where(RateAnalysis.rate_book_id == book_id)
      .options(selectinload(RateAnalysis.components)).order_by(RateAnalysis.code.asc()))
    return list(r.scalars().all())

  async def analysis_by_code(self, book_id: UUID, code: str) -> RateAnalysis | None:
    r = await self.session.execute(select(RateAnalysis).where(RateAnalysis.rate_book_id == book_id, RateAnalysis.code == code))
    return r.scalar_one_or_none()

  async def item_by_id_in_book(self, item_id: UUID, book_id: UUID) -> RateItem | None:
    r = await self.session.execute(select(RateItem).where(RateItem.id == item_id, RateItem.rate_book_id == book_id))
    return r.scalar_one_or_none()

  async def clear_components(self, analysis_id: UUID) -> None:
    await self.session.execute(delete(RateAnalysisComponent).where(RateAnalysisComponent.analysis_id == analysis_id))
    await self.session.flush()

  async def get_override(self, override_id: UUID, org: UUID, *, for_update: bool = False) -> ProjectRateOverride | None:
    q = select(ProjectRateOverride).where(ProjectRateOverride.id == override_id, ProjectRateOverride.organization_id == org)
    if for_update:
      q = q.with_for_update()
    return (await self.session.execute(q)).scalar_one_or_none()

  async def active_override(self, org: UUID, project_id: UUID, code: str, unit: str) -> ProjectRateOverride | None:
    r = await self.session.execute(select(ProjectRateOverride).where(
      ProjectRateOverride.organization_id == org, ProjectRateOverride.project_id == project_id,
      ProjectRateOverride.work_item_code == code, ProjectRateOverride.unit == unit,
      ProjectRateOverride.revoked_at.is_(None)))
    return r.scalar_one_or_none()

  async def list_overrides(self, org: UUID, project_id: UUID, *, include_revoked: bool, after: UUID | None,
    limit: int) -> list[ProjectRateOverride]:
    q = select(ProjectRateOverride).where(
      ProjectRateOverride.organization_id == org, ProjectRateOverride.project_id == project_id)
    if not include_revoked:
      q = q.where(ProjectRateOverride.revoked_at.is_(None))
    if after is not None:
      row = await self.get_override(after, org)
      if row is not None:
        q = q.where(tuple_(ProjectRateOverride.work_item_code, ProjectRateOverride.unit, ProjectRateOverride.id)
          > tuple_(row.work_item_code, row.unit, row.id))
    q = q.order_by(ProjectRateOverride.work_item_code.asc(), ProjectRateOverride.unit.asc(),
      ProjectRateOverride.id.asc()).limit(limit + 1)
    return list((await self.session.execute(q)).scalars().all())

  async def active_overrides_for_project(self, org: UUID, project_id: UUID, codes: set[str]) -> dict[str, list[ProjectRateOverride]]:
    out: dict[str, list[ProjectRateOverride]] = {}
    if not codes:
      return out
    ordered = sorted(codes)
    for i in range(0, len(ordered), _CHUNK):
      r = await self.session.execute(select(ProjectRateOverride).where(
        ProjectRateOverride.organization_id == org, ProjectRateOverride.project_id == project_id,
        ProjectRateOverride.revoked_at.is_(None), ProjectRateOverride.work_item_code.in_(ordered[i:i + _CHUNK])))
      for o in r.scalars().all():
        out.setdefault(o.work_item_code, []).append(o)
    return out

  async def library_rows(self, org: UUID) -> list[MaterialLibrary]:
    r = await self.session.execute(select(MaterialLibrary).where(
      MaterialLibrary.organization_id == org, MaterialLibrary.default_rate.is_not(None)))
    return list(r.scalars().all())

  async def referenced_book_ids(self, org: UUID, book_id: UUID) -> int:
    r = await self.session.execute(select(func.count()).select_from(BOQItem).where(
      BOQItem.organization_id == org, BOQItem.rate_book_id == book_id))
    return int(r.scalar_one())