"""Price: amount = quantity x rate, in the book's unit and basis. Billed lines (PX-1) in, priced lines out; the measured quantity is never changed.

A line with no rate, or a rate that is held (a labour-only rate no profile calls a full price), is shown unpriced with its reason and adds nothing to a total.
Totals are by section (the rate book's chapter) and by floor, split into measured and assumed quantities.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
from app.modules.drawings_boq.pricing.billing import group as G

ZERO = Decimal(0)
CENT = Decimal("0.01")
HELD_FLAGS = frozenset({"RATE_LABOUR_ONLY", "RATE_MISSING", "RATE_ZERO", "UNIT_UNKNOWN", "UNIT_AMBIGUOUS", "RATE_TEXT", "ALT_RATE_MISMATCH"})

@dataclass(frozen=True)
class Rate:
  code: str
  description: str
  unit: str                  
  rate: Decimal              
  basis: Decimal = Decimal(1)        
  flags: tuple = ()

  @property
  def per_unit(self) -> Decimal:
    return self.rate / self.basis

@dataclass
class PricedLine:
  code: str
  description: str | None
  unit: str
  qty: Decimal
  spec: tuple | None
  floor: str | None
  rate: Decimal | None = None
  basis: Decimal | None = None
  rate_unit: str | None = None
  amount: Decimal | None = None
  low: Decimal | None = None
  high: Decimal | None = None
  unpriced_why: str | None = None
  assumed_share: Decimal = ZERO          
  by_floor: dict = field(default_factory=dict)       

def _q(x: Decimal) -> Decimal:
  return x.quantize(CENT, rounding=ROUND_HALF_UP)

def _assumed_share(line: G.BillLine, assumed: frozenset) -> Decimal:
  total = sum((s[3] for s in line.sources), ZERO)
  if not total:
    return ZERO
  return sum((s[3] for s in line.sources if (s[0], s[1]) in assumed), ZERO) / total

def price(billed: G.Billed, rates: dict, ranges: dict | None = None, assumed: frozenset = frozenset()) -> list:
  out = []
  
  for line in billed.lines:
    rate = rates.get(line.code)
    p = PricedLine(line.code, rate.description if rate else None, line.unit, line.qty, line.spec, line.floor, assumed_share=_assumed_share(line, assumed))
    if rate is None:
      p.unpriced_why = "no rate for this item in the rate book: rate needed"
    elif any(f in HELD_FLAGS for f in rate.flags):
      p.rate, p.basis, p.rate_unit = rate.rate, rate.basis, rate.unit
      p.unpriced_why = "the rate is held: " + ", ".join(f for f in rate.flags if f in HELD_FLAGS)
    else:
      qty = G.convert(line.qty, line.unit, rate.unit)
      p.rate, p.basis, p.rate_unit = rate.rate, rate.basis, rate.unit
      if qty is None:
        p.unpriced_why = f"the line is in {line.unit} and the rate is per {rate.unit}"
      else:
        p.amount = _q(qty * rate.per_unit)
        lo, hi = (ranges or {}).get(line.code, (None, None))
        p.low = _q(qty * Decimal(str(lo)) * rate.per_unit) if lo is not None else None
        p.high = _q(qty * Decimal(str(hi)) * rate.per_unit) if hi is not None else None
        by_floor: dict = defaultdict(lambda: ZERO)
        total = sum((s[3] for s in line.sources), ZERO)
        for s in line.sources:
          by_floor[s[2]] += (p.amount * s[3] / total) if total else ZERO
        p.by_floor = {k: _q(v) for k, v in by_floor.items()}
    out.append(p)
    
  return out

def section_of(code: str) -> str:
  head = code.split("-", 1)[0]
  return head if head.isdigit() else code

def totals(lines: list) -> dict:
  grand, sections, floors = ZERO, defaultdict(lambda: ZERO), defaultdict(lambda: ZERO)
  measured, assumed = ZERO, ZERO
  low, high, ranged = ZERO, ZERO, ZERO
  for l in lines:
    if l.amount is None:
      continue
    grand += l.amount
    
    sections[section_of(l.code)] += l.amount
    for f, a in l.by_floor.items():
      floors[f or "NO FLOOR"] += a
    a = l.amount * l.assumed_share
    assumed += a
    measured += l.amount - a
    
    if l.low is not None and l.high is not None:
      low, high, ranged = low + l.low, high + l.high, ranged + l.amount
  unpriced = [l for l in lines if l.amount is None]
  return {"grand": _q(grand), "measured": _q(measured), "assumed": _q(assumed), "by_section": {k: _q(v) for k, v in sorted(sections.items())},
    "by_floor": {k: _q(v) for k, v in sorted(floors.items())}, "unpriced": len(unpriced), "priced": len(lines) - len(unpriced),
    "range": {"low": _q(low), "high": _q(high), "of_amount": _q(ranged)} if ranged else None}
