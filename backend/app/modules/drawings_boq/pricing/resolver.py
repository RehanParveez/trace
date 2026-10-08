from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.models import ProjectRateOverride, MaterialLibrary, RateBook
from app.modules.drawings_boq.pricing.rate_repository import RateRepository
from app.core.exceptions import TraceException
from decimal import Decimal
from app.modules.drawings_boq import boq_logic as logic
from app.modules.drawings_boq.pricing import pricing_logic as pl
from app.modules.drawings_boq.models import BOQItemRateSource

@dataclass
class PriceResolver:
  org: UUID
  project_id: UUID | None
  as_of: date
  books: list[RateBook]
  items: dict = field(default_factory=dict)
  escalations: dict = field(default_factory=dict)
  overrides: dict = field(default_factory=dict)
  library_by_code: dict = field(default_factory=dict)
  library_by_text: dict = field(default_factory=dict)

  @classmethod
  async def load(cls, session: AsyncSession, org: UUID, project_id: UUID | None, *, as_of: date | None = None,
    codes: set[str] | None = None, rate_book_ids: list[UUID] | None = None) -> "PriceResolver":
    repo = RateRepository(session)
    on = as_of or date.today()
    
    if rate_book_ids:
      books = await repo.books_by_ids(list(rate_book_ids), org)
      missing = set(rate_book_ids) - {b.id for b in books}
      if missing:
        raise TraceException("A rate book was not found.", status_code=404, code="RATE_BOOK_NOT_FOUND")
      bad = [b.code for b in books if b.status not in ("ACTIVE", "SUPERSEDED")]
      if bad:
        raise TraceException(f"Only ACTIVE or SUPERSEDED rate books can price a BOQ ({', '.join(bad)}).",
          status_code=422, code="RATE_BOOK_NOT_PUBLISHED")
        
    else:
      books = await repo.default_stack(org, on)
    codes = {c for c in (codes or set()) if c}
    ids = [b.id for b in books]
    r = cls(org=org, project_id=project_id, as_of=on, books=books)
    r.items = await repo.items_for_codes(ids, codes)
    r.escalations = await repo.escalations_for_books(ids)
    if project_id is not None:
      r.overrides = await repo.active_overrides_for_project(org, project_id, codes)
    for row in await repo.library_rows(org):
      if row.work_item_code:
        r.library_by_code.setdefault(row.work_item_code, []).append(row)
      r.library_by_text[(row.raw_text or "").strip().lower()] = row
    return r

  def stack_summary(self) -> list[dict]:
    return [{"id": str(b.id), "code": b.code, "edition": b.edition, "immutable_version": b.immutable_version,
      "scope": "ORGANIZATION" if b.organization_id else "SYSTEM", "content_hash": b.content_hash} for b in self.books]

  def resolve(self, work_item_code: str | None, texts: list[str | None], unit: str, *, trade_hint: str | None = None) -> pl.Resolution:
    res = pl.Resolution()
    code = (work_item_code or "").strip()
    attempts = res.attempts
    mismatch = False

    if code:
      active = [o for o in self.overrides.get(code, []) if pl.in_window(self.as_of, o.effective_from, o.effective_to)]
      if active:
        m, bad = pl.match_unit(active, unit)
        if m is not None:
          o: ProjectRateOverride = m.entry
          attempts.append({"source": "PROJECT_OVERRIDE", "result": "used", "override_id": str(o.id)})
          res.source, res.unit_rate, res.base_rate = "PROJECT_OVERRIDE", m.rate, m.rate
          res.escalation_factor = None
          res.trace = {"source": "PROJECT_OVERRIDE", "override_id": str(o.id), "override_rate": logic.fmt(o.rate, 2),
            "override_unit": o.unit, "unit_converted": m.converted, "reason": o.reason, "as_of": self.as_of.isoformat()}
          return res
      
        if bad:
          mismatch = True
          attempts.append({"source": "PROJECT_OVERRIDE", "result": "unit_mismatch", "units": sorted({o.unit for o in active})})

      for book in self.books:
        entries = self.items.get((book.id, code), [])
        if not entries:
          attempts.append({"source": "RATE_BOOK", "book": book.code, "book_id": str(book.id), "result": "no_rate"})
          continue
        m, bad = pl.match_unit(entries, unit)
        
        if m is None:
          mismatch = mismatch or bad
          attempts.append({"source": "RATE_BOOK", "book": book.code, "book_id": str(book.id), "result": "unit_mismatch",
            "units": sorted({e.unit for e in entries})})
          continue
      
        ri = m.entry
        factor, esc = pl.escalation_for(self.escalations.get(book.id, []), ri.trade, self.as_of)
        unit_rate = pl.escalate(m.rate, factor)
        attempts.append({"source": "RATE_BOOK", "book": book.code, "book_id": str(book.id), "result": "used"})
        res.source, res.unit_rate, res.base_rate, res.escalation_factor = "RATE_BOOK", unit_rate, m.rate, factor
        res.rate_book_id = book.id
        res.trace = {"source": "RATE_BOOK", "rate_book_id": str(book.id), "rate_book_code": book.code,
          "edition": book.edition, "book_version": book.immutable_version, "book_hash": book.content_hash,
          "rate_item_id": str(ri.id), "csr_ref": ri.csr_ref, "rate_unit": ri.unit, "rate": logic.fmt(ri.rate, 2),
          "unit_converted": m.converted, "escalation_factor": logic.fmt(factor, 4),
          "escalation_id": str(esc.id) if esc is not None else None, "as_of": self.as_of.isoformat()}
        return res

    lib = self._library(code, texts)
    if lib is not None:
      row, how = lib
      if row.default_unit and not pl.same_unit(row.default_unit, unit):
        converted = logic.convert_rate(row.default_rate, row.default_unit, unit)
        if converted is None:
          mismatch = True
          attempts.append({"source": "LIBRARY", "result": "unit_mismatch", "units": [row.default_unit]})
          row = None
          
        else:
          rate, was_converted = converted, True
      else:
        rate, was_converted = logic.q2(row.default_rate), False
      if row is not None:
        attempts.append({"source": "LIBRARY", "result": "used", "matched_on": how})
        res.source, res.unit_rate, res.base_rate, res.escalation_factor = "LIBRARY", rate, rate, None
        res.trace = {"source": "LIBRARY", "library_id": str(row.id), "matched_on": how, "raw_text": row.raw_text,
          "library_unit": row.default_unit, "unit_converted": was_converted, "as_of": self.as_of.isoformat()}
        return res
    else:
      attempts.append({"source": "LIBRARY", "result": "no_rate"})

    res.unit_mismatch = mismatch
    return res

  def _library(self, code: str, texts: list[str | None]) -> tuple[MaterialLibrary, str] | None:
    if code:
      rows = [r for r in self.library_by_code.get(code, []) if r.effective_from is None or r.effective_from <= self.as_of]
      if rows:
        rows.sort(key=lambda r: (r.effective_from or date.min), reverse=True)
        return rows[0], "work_item_code"
    
    for t in texts:
      key = (t or "").strip().lower()
      if key and key in self.library_by_text:
        row = self.library_by_text[key]
        if row.effective_from is None or row.effective_from <= self.as_of:
          return row, "text"
    return None

def apply_resolution(item, res: pl.Resolution) -> bool:
  new = (res.unit_rate, BOQItemRateSource(res.source), res.base_rate, res.escalation_factor, res.rate_book_id, res.trace)
  old = (item.unit_rate, item.rate_source, item.base_rate, item.escalation_factor, item.rate_book_id, item.rate_resolution)
  if old == new:
    return False
  (item.unit_rate, item.rate_source, item.base_rate, item.escalation_factor, item.rate_book_id,
    item.rate_resolution) = new
  return True

def clear_rate(item) -> bool:
  old = (item.unit_rate, item.rate_source, item.base_rate, item.escalation_factor, item.rate_book_id, item.rate_resolution)
  if old == (None, None, None, None, None, None):
    return False
  item.unit_rate = item.rate_source = item.base_rate = item.escalation_factor = item.rate_book_id = None
  item.rate_resolution = None
  return True

def to_decimal(value) -> Decimal:
  return Decimal(str(value))