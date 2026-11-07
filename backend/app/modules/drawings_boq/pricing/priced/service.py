from __future__ import annotations
from decimal import Decimal
from app.modules.drawings_boq.pricing.priced import export as X, materials as MT, price as PR
from app.modules.drawings_boq.pricing.billing import group as G, profiles as P, service as SV
from datetime import date, datetime, timezone
from app.modules.drawings_boq.pricing.rate_repository import RateRepository
from app.core.exceptions import TraceException
from uuid import UUID
from app.modules.drawings_boq.pricing.spec_match import split_code

ZERO = Decimal(0)
MIX_SPECS = ("concrete_mix", "brick_mortar", "plaster_ratio")

def _mix(text: str | None) -> str:
  return "".join(str(text or "").split()).replace("-", ":").replace("/", ":")

def wanted_spec(spec: tuple | None) -> dict | None:
  if not spec or not spec[1]:
    return None
  
  name, value = spec[0], str(spec[1])
  if name in MIX_SPECS:
    return {"mix": _mix(value)}
  if name == "steel_grade":
    digits = "".join(c for c in value if c.isdigit())
    return {"grade": digits[:2]} if len(digits) >= 2 else None
  return None

def held_flags(item) -> tuple:
  kind = str((getattr(item, "extra", None) or {}).get("rate_kind") or "").upper()
  flags = []
  if kind == "LABOUR":
    flags.append("RATE_LABOUR_ONLY")
  if item.rate is None or Decimal(str(item.rate)) == 0:
    flags.append("RATE_ZERO")
  return tuple(flags)

def _rate_of(code: str, item) -> PR.Rate:
  return PR.Rate(code, item.description or "", item.unit, Decimal(str(item.rate)), Decimal(1), held_flags(item))

def pick(line: G.BillLine, books: list) -> tuple:
  want = wanted_spec(line.spec)
  for items in books:
    exact = [i for i in items if i.work_item_code == line.code and getattr(i, "is_active", True)]
    if not exact:
      with_spec = []
      
      for i in items:
        if not getattr(i, "is_active", True):
          continue
        base, spec = split_code(i.work_item_code)
        base = (getattr(i, "extra", None) or {}).get("base_code") or base
        if base != line.code:
          continue
        if want is None or (spec and all(spec.get(k) == v for k, v in want.items())):
          with_spec.append(i)
      exact = with_spec
      
    ok = [i for i in exact if G.convert(line.qty, line.unit, i.unit) is not None] or exact
    same = [i for i in ok if i.unit == line.unit]
    ok = same or ok
    if len(ok) == 1:
      return _rate_of(line.code, ok[0]), None
    if len(ok) > 1:
      return None, f"{line.code}: {len(ok)} rate items fit ({', '.join(sorted(i.work_item_code for i in ok))[:120]}); none was chosen"
  return None, None

def rates_for(billed: G.Billed, books: list) -> tuple:
  rates: dict = {}
  notes: list = []
  clash: set = set()
  
  for line in billed.lines:
    rate, note = pick(line, books)
    if note:
      notes.append(note)
    if rate is None or line.code in clash:
      continue
    
    seen = rates.get(line.code)
    if seen is not None and (seen.unit, seen.rate, seen.flags) != (rate.unit, rate.rate, rate.flags):
      clash.add(line.code)
      del rates[line.code]
      notes.append(f"{line.code}: its lines (floors or specifications) fit different rate items; none was priced")
      continue
    
    rates[line.code] = rate
  return rates, list(dict.fromkeys(notes))

def _f(x, places: int = 2):
  return None if x is None else float(round(x, places))

def priced_view(billed: G.Billed, parts: dict, measured: list, profile: P.Profile, books: list, book_rows: list) -> tuple:
  rates, notes = rates_for(billed, books)
  lines = PR.price(billed, rates, SV.range_factors(billed, parts["ranges"]), parts["assumed"])
  totals = PR.totals(lines)
  mats = MT.from_lines(billed, None, None)
  body = SV.view(billed, parts, measured, profile)
  out_lines = []
  
  for l in lines:
    spec = None if not l.spec else {"name": l.spec[0], "value": l.spec[1], "basis": l.spec[2]}
    out_lines.append({"code": l.code, "description": l.description, "unit": l.unit, "qty": _f(l.qty, 3), "spec": spec, "floor": l.floor, "rate": _f(None if l.rate is None else l.rate / (l.basis or 1), 4),
      "rate_unit": l.rate_unit, "amount": _f(l.amount), "low": _f(l.low), "high": _f(l.high), "unpriced_why": l.unpriced_why, "assumed_share": _f(l.assumed_share, 4),
      "by_floor": {(k or "NO FLOOR"): _f(v) for k, v in l.by_floor.items()}})
    
  body["lines"] = out_lines
  body["totals"] = {"grand": _f(totals["grand"]), "measured": _f(totals["measured"]), "assumed": _f(totals["assumed"]), "priced": totals["priced"], "unpriced": totals["unpriced"],
    "by_section": {k: _f(v) for k, v in totals["by_section"].items()}, "by_floor": {k: _f(v) for k, v in totals["by_floor"].items()},
    "range": None if not totals["range"] else {k: _f(v) for k, v in totals["range"].items()}}
  
  body["rate_books"] = book_rows
  body["rate_notes"] = notes
  body["materials"] = {"totals": {k: _f(v, 3) for k, v in sorted(mats.totals.items())}, "rows": [{"code": c, "material": m, "qty": _f(q, 3), "how": h} for c, m, q, h in mats.rows],
    "missing": [{"code": c, "why": w} for c, w in mats.missing], "coefficient_table": False}
  return body, lines, totals, mats

class PricedService(SV.BillingService):
  async def _books(self, org: UUID, book_id: UUID | None) -> list:
    repo = RateRepository(self.session)
    if book_id is not None:
      found = await repo.books_by_ids([book_id], org)
      if not found:
        raise TraceException("Rate book not found.", status_code=404, code="RATE_BOOK_NOT_FOUND")
      return found
    return await repo.default_stack(org, date.today())

  async def _compute(self, org: UUID, project_id: UUID, profile_id: str | None, book_id: UUID | None):
    try:
      profile = P.get(profile_id) if profile_id else P.get(P.DEFAULT_PROFILE)
    except ValueError:
      raise TraceException(f"'{profile_id}' is not a billing profile.", status_code=422, code="PROFILE_UNKNOWN")
    entries, source = await self.entries(org, project_id)
    head = {"project_id": project_id, "profiles": [{"id": p.id, "label": p.label} for p in P.all_profiles().values()], "source": source}
    
    if entries is None:
      return None, head, profile
    parts = SV.measured_from_entries(entries)
    billed = G.group(parts["measured"], profile, None)
    books = await self._books(org, book_id)
    repo = RateRepository(self.session)
    
    items = [await repo.all_items(b.id) for b in books]
    rows = [{"id": b.id, "code": b.code, "version": b.immutable_version, "edition": b.edition, "scope": "SYSTEM" if b.organization_id is None else "ORGANISATION", "items": len(i), "content_hash": b.content_hash}
      for b, i in zip(books, items)]
    return priced_view(billed, parts, parts["measured"], profile, items, rows), head, profile

  async def priced(self, org: UUID, project_id: UUID, profile_id: str | None = None, book_id: UUID | None = None) -> dict:
    got, head, profile = await self._compute(org, project_id, profile_id, book_id)
    
    if got is None:
      return {**head, "has_ledger": False, "profile": profile.id, "lines": [], "included": [], "rate_needed": [], "questions": [], "not_measured": [], "unavailable": [],
        "counts": {"measured_entries": 0, "assumed_entries": 0, "not_measured": 0}, "reconciled": True, "lost": {}, "totals": {"grand": 0.0, "measured": 0.0, "assumed": 0.0, "priced": 0,
        "unpriced": 0, "by_section": {}, "by_floor": {}, "range": None}, "rate_books": [], "rate_notes": [], "materials": {"totals": {}, "rows": [], "missing": [], "coefficient_table": False}}
    return {**head, "has_ledger": True, **got[0]}

  async def workbook(self, org: UUID, project_id: UUID, profile_id: str | None = None, book_id: UUID | None = None) -> bytes:
    got, _head, profile = await self._compute(org, project_id, profile_id, book_id)
    if got is None:
      raise TraceException("This project has no ledger yet. Run the first-upload job.", status_code=409, code="NO_LEDGER")
    _body, lines, totals, mats = got
    return X.build_xlsx(str(project_id), profile.id, lines, totals, mats, None, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
