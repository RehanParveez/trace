from __future__ import annotations
from decimal import Decimal
from app.modules.drawings_boq import boq_logic as logic
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable
import hashlib
import json

ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")

AUTO_SOURCES = frozenset({"PROJECT_OVERRIDE", "RATE_BOOK", "LIBRARY"})

def same_unit(a: str | None, b: str | None) -> bool:
  return logic.normalise_unit(a) == logic.normalise_unit(b)

def convert(rate: Decimal, from_unit: str, to_unit: str) -> Decimal | None:
  if same_unit(from_unit, to_unit):
    return logic.q2(rate)
  return logic.convert_rate(rate, from_unit, to_unit)

@dataclass(frozen=True)
class UnitMatch:
  entry: object
  rate: Decimal
  converted: bool

def match_unit(entries: Iterable, target_unit: str) -> tuple[UnitMatch | None, bool]:
  entries = list(entries)
  for e in entries:
    if same_unit(e.unit, target_unit):
      return UnitMatch(e, logic.q2(e.rate), False), False
  for e in sorted(entries, key=lambda x: (logic.normalise_unit(x.unit), str(getattr(x, "id", "")))):
    rate = logic.convert_rate(e.rate, e.unit, target_unit)
    if rate is not None:
      return UnitMatch(e, rate, True), False
  return None, bool(entries)

def in_window(on: date, start: date | None, end: date | None) -> bool:
  return (start is None or start <= on) and (end is None or on <= end)

def escalation_for(escalations: Iterable, trade: str | None, as_of: date) -> tuple[Decimal, object | None]:
  wanted = (trade or "").strip().lower()
  best = None
  for e in escalations:
    if e.effective_from > as_of:
      continue
    scope = (e.trade_scope or "ALL").strip().lower()
    if scope != "all" and scope != wanted:
      continue
    rank = (0 if scope == "all" else 1, e.effective_from)
    if best is None or rank > best[0]:
      best = (rank, e)
  if best is None:
    return ONE, None
  return Decimal(best[1].factor), best[1]

def escalate(base: Decimal, factor: Decimal) -> Decimal:
  return logic.q2(Decimal(base) * Decimal(factor))

@dataclass
class Resolution:
  source: str | None = None
  unit_rate: Decimal | None = None
  base_rate: Decimal | None = None
  escalation_factor: Decimal | None = None
  rate_book_id: object | None = None
  trace: dict = field(default_factory=dict)
  unit_mismatch: bool = False
  attempts: list[dict] = field(default_factory=list)

  @property
  def found(self) -> bool:
    return self.unit_rate is not None

  def stored(self) -> dict | None:
    return self.trace or None

@dataclass(frozen=True)
class AnalysisLine:
  sequence: int
  component_type: str
  description: str
  unit: str
  coefficient: Decimal
  unit_rate: Decimal

def analysis_totals(lines: list[AnalysisLine], basis_quantity: Decimal, overhead_pct: Decimal, profit_pct: Decimal) -> dict:
  if Decimal(basis_quantity) <= 0:
    raise ValueError("basis_quantity must be positive")
  by_type: dict[str, Decimal] = {}
  
  rows = []
  for l in lines:
    amount = logic.q2(Decimal(l.coefficient) * Decimal(l.unit_rate))
    by_type[l.component_type] = by_type.get(l.component_type, ZERO) + amount
    rows.append({"sequence": l.sequence, "component_type": l.component_type, "description": l.description,
      "unit": l.unit, "coefficient": logic.fmt(l.coefficient, 6), "unit_rate": logic.fmt(l.unit_rate, 2),
      "amount": logic.fmt(amount, 2)})
  cost = sum(by_type.values(), ZERO)
  overhead = logic.q2(cost * Decimal(overhead_pct) / HUNDRED)
  profit = logic.q2((cost + overhead) * Decimal(profit_pct) / HUNDRED)
  total = cost + overhead + profit
  rate = logic.q2(total / Decimal(basis_quantity))
  return {
    "lines": rows,
    "cost_by_type": {k: logic.fmt(v, 2) for k, v in sorted(by_type.items())},
    "cost": logic.fmt(cost, 2), "overhead": logic.fmt(overhead, 2), "profit": logic.fmt(profit, 2),
    "total": logic.fmt(total, 2), "basis_quantity": logic.fmt(basis_quantity, 4), "rate": logic.fmt(rate, 2),
    "rate_value": rate,
  }

def rate_book_hash(header: dict, items: Iterable, analyses: Iterable) -> str:
  rows = sorted(
    ({"code": i.work_item_code, "unit": logic.normalise_unit(i.unit), "rate": logic.fmt(i.rate, 2),
      "trade": i.trade, "csr_ref": i.csr_ref} for i in items if i.is_active),
    key=lambda r: (r["code"], r["unit"]))
  arows = sorted(
    ({"code": a.code, "work_item_code": a.work_item_code, "unit": logic.normalise_unit(a.unit),
      "computed_rate": logic.fmt(a.computed_rate, 2) if a.computed_rate is not None else None}
     for a in analyses if a.is_active),
    key=lambda r: r["code"])
  blob = json.dumps({"header": header, "items": rows, "analyses": arows}, sort_keys=True,
    separators=(",", ":"), default=str)
  return hashlib.sha256(blob.encode("utf-8")).hexdigest()

def line_keys(rows: list[dict]) -> dict[str, dict]:
  seen: dict[str, int] = {}
  out: dict[str, dict] = {}
  for r in rows:
    key = r.get("item_key")
    if not key:
      base = f"manual:{(r.get('work_item_code') or '').strip().upper()}:{(r.get('material_name') or '').strip().lower()}:{logic.normalise_unit(r.get('unit'))}"
      n = seen.get(base, 0)
      seen[base] = n + 1
      key = base if n == 0 else f"{base}#{n + 1}"
    out[key] = r
  return out

def _amount(r: dict) -> Decimal | None:
  if r.get("amount") is not None:
    return Decimal(r["amount"])
  if r.get("unit_rate") is not None and r.get("quantity") is not None:
    return logic.q2(Decimal(r["quantity"]) * Decimal(r["unit_rate"]))
  return None

def _qty_in(row: dict, unit: str) -> Decimal | None:
  q = row.get("quantity")
  if q is None:
    return None
  if logic.normalise_unit(row.get("unit")) == logic.normalise_unit(unit):
    return Decimal(q)
  a = logic.UNIT_TABLE.get(logic.normalise_unit(row.get("unit")))
  b = logic.UNIT_TABLE.get(logic.normalise_unit(unit))
  if a is None or b is None or a[0] != b[0]:
    return None
  return logic.q4(Decimal(q) * b[1] / a[1])

def _pct(delta: Decimal, base: Decimal | None) -> Decimal | None:
  if base is None or base == 0:
    return None
  return logic.q2(delta / base * HUNDRED)

def diff_lines(rows_a: list[dict], rows_b: list[dict]) -> dict:
  ka, kb = line_keys(rows_a), line_keys(rows_b)
  lines: list[dict] = []
  for key in sorted(set(ka) | set(kb), key=lambda k: (
      (kb.get(k) or ka.get(k)).get("work_item_code") or "~", (kb.get(k) or ka.get(k)).get("material_name") or "", k)):
    a, b = ka.get(key), kb.get(key)
    ref = b or a
    
    entry = {
      "item_key": key, "work_item_code": ref.get("work_item_code"), "material_name": ref.get("material_name"),
      "unit_a": a.get("unit") if a else None, "unit_b": b.get("unit") if b else None,
      "net_a": a.get("net_quantity") if a else None, "net_b": b.get("net_quantity") if b else None,
      "quantity_a": a.get("quantity") if a else None, "quantity_b": b.get("quantity") if b else None,
      "rate_a": a.get("unit_rate") if a else None, "rate_b": b.get("unit_rate") if b else None,
      "amount_a": _amount(a) if a else None, "amount_b": _amount(b) if b else None,
      "net_delta": None, "quantity_delta": None, "quantity_delta_pct": None, "rate_delta": None, "amount_delta": None,
      "unit_changed": False,
    }
    if a is None:
      entry["status"] = "ADDED"
      entry["quantity_delta"] = logic.q4(Decimal(b["quantity"]))
      entry["net_delta"] = logic.q4(Decimal(b["net_quantity"])) if b.get("net_quantity") is not None else None
      entry["amount_delta"] = entry["amount_b"]
    elif b is None:
      entry["status"] = "REMOVED"
      entry["quantity_delta"] = -logic.q4(Decimal(a["quantity"]))
      entry["net_delta"] = -logic.q4(Decimal(a["net_quantity"])) if a.get("net_quantity") is not None else None
      entry["amount_delta"] = -entry["amount_a"] if entry["amount_a"] is not None else None
      
    else:
      entry["unit_changed"] = logic.normalise_unit(a.get("unit")) != logic.normalise_unit(b.get("unit"))
      qa = _qty_in(a, b.get("unit")) if entry["unit_changed"] else Decimal(a["quantity"])
      if qa is not None:
        entry["quantity_delta"] = logic.q4(Decimal(b["quantity"]) - qa)
        entry["quantity_delta_pct"] = _pct(entry["quantity_delta"], qa)
      if a.get("net_quantity") is not None and b.get("net_quantity") is not None and not entry["unit_changed"]:
        entry["net_delta"] = logic.q4(Decimal(b["net_quantity"]) - Decimal(a["net_quantity"]))
      if a.get("unit_rate") is not None and b.get("unit_rate") is not None and not entry["unit_changed"]:
        entry["rate_delta"] = logic.q2(Decimal(b["unit_rate"]) - Decimal(a["unit_rate"]))
      aa, ab = entry["amount_a"], entry["amount_b"]
      if aa is not None and ab is not None:
        entry["amount_delta"] = logic.q2(ab - aa)
        
      elif ab is not None or aa is not None:
        entry["amount_delta"] = logic.q2((ab or ZERO) - (aa or ZERO))
      changed = (entry["unit_changed"] or (entry["quantity_delta"] not in (None, ZERO))
        or (entry["rate_delta"] not in (None, ZERO)) or (entry["net_delta"] not in (None, ZERO))
        or (a.get("unit_rate") is None) != (b.get("unit_rate") is None))
      entry["status"] = "CHANGED" if changed else "UNCHANGED"
    lines.append(entry)

  def total(rows):
    return sum((_amount(r) or ZERO for r in rows), ZERO)
  ta, tb = total(rows_a), total(rows_b)
  counts = {s: sum(1 for l in lines if l["status"] == s) for s in ("ADDED", "REMOVED", "CHANGED", "UNCHANGED")}
  summary = {**counts, "total_a": logic.q2(ta), "total_b": logic.q2(tb), "total_delta": logic.q2(tb - ta),
    "total_delta_pct": _pct(logic.q2(tb - ta), logic.q2(ta)) if ta else None,
    "unpriced_a": sum(1 for r in rows_a if r.get("unit_rate") is None),
    "unpriced_b": sum(1 for r in rows_b if r.get("unit_rate") is None)}
  return {"summary": summary, "lines": lines}