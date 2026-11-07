"""Grouping: measured quantities become billed lines through the catalogue's billing map.

Quantities are summed by item code and spec, units are converted (kg to cwt), and lines are split by floor when the profile says so. Nothing here
changes a measured quantity: `billed_in_measured_units` turns the lines back into the measured units so a caller can check that the totals are identical
under every profile. A quantity the profile has no item for is listed as "rate needed", never dropped.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from collections import defaultdict
from app.engine.catalogue import loader
from app.modules.drawings_boq import boq_logic as logic
from app.modules.drawings_boq.pricing.billing import profiles as P, specs as S

ZERO = Decimal(0)

@dataclass(frozen=True)
class Measured:
  item_id: str
  qty_key: str
  value: Decimal
  unit: str
  floor: str | None = None

@dataclass
class BillLine:
  code: str
  unit: str
  qty: Decimal
  spec: tuple | None = None          # (name, value, basis)
  floor: str | None = None
  sources: list = field(default_factory=list)       # (item_id, qty_key, floor, value, unit)

@dataclass
class Billed:
  profile: str
  lines: list
  included: list         # (qty_key, where, total in the measured unit, unit)
  rate_needed: list      # (item_id, qty_key, value, unit, why)
  questions: list        # {"spec", "floor", "default", "question"}
  included_sources: list = field(default_factory=list)      # (item_id, qty_key, floor, value, unit) of what is included in another item's rate

def convert(value: Decimal, from_unit: str, to_unit: str) -> Decimal | None:
  """value in from_unit as to_unit, or None when they are not the same kind of unit."""
  a, b = logic.UNIT_TABLE.get(logic.normalise_unit(from_unit)), logic.UNIT_TABLE.get(logic.normalise_unit(to_unit))
  if a is None or b is None or a[0] != b[0]:
    return None
  return value / a[1] * b[1]

def _entries(item, block: str, qty_key: str) -> list:
  if block == "PRIVATE_QS":
    return [(b.line, None, None) for b in item.billing.PRIVATE_QS if b.qty == qty_key]
  return [(b.item, b.spec, b.convert) for b in item.billing.MRS_PB if b.qty == qty_key]

def _chosen(entries: list, item_id: str, floor: str | None, decisions: dict | None):
  """One entry of the billing map, or None. An item mapped to several rate-book items (flashing priced under four items, a beam billed as beams, roof beams
  or beams and slabs) is billed to the one a decision names: decisions["billing_item"][item id] is a code, or a dict by floor with an optional "default"."""
  if len(entries) == 1:
    return entries[0]
  named = ((decisions or {}).get("billing_item") or {}).get(item_id)
  if isinstance(named, dict):
    named = named.get(floor) if floor is not None and floor in named else named.get("default")
  return next((e for e in entries if e[0] == named), None) if named else None

def group(measured: list, profile: P.Profile, decisions: dict | None = None) -> Billed:
  lines: dict = {}
  included: dict = defaultdict(lambda: ZERO)
  inc_unit: dict = {}
  needed, questions, asked, inc_src = [], [], set(), []
  for m in measured:
    item = loader.get(m.item_id)
    if item is None:
      needed.append((m.item_id, m.qty_key, m.value, m.unit, "the item is not in the catalogue"))
      continue
    if m.qty_key in profile.included_in:
      included[m.qty_key] += m.value
      inc_unit[m.qty_key] = m.unit
      inc_src.append((m.item_id, m.qty_key, m.floor, m.value, m.unit))
      continue
    entries = _entries(item, profile.block, m.qty_key)
    if not entries:
      needed.append((m.item_id, m.qty_key, m.value, m.unit, f"the {profile.id} billing map of {m.item_id} has no item for {m.qty_key}"))
      continue
    pick = _chosen(entries, m.item_id, m.floor, decisions)
    if pick is None:
      needed.append((m.item_id, m.qty_key, m.value, m.unit, f"{m.item_id} is billed under {', '.join(e[0] for e in entries)} in {profile.id}; a decision must name one"))
      continue
    for code, spec_name, convert_to in [pick]:
      unit = logic.normalise_unit(convert_to) if convert_to else logic.normalise_unit(m.unit)
      qty = convert(m.value, m.unit, unit) if convert_to else m.value
      if qty is None:
        needed.append((m.item_id, m.qty_key, m.value, m.unit, f"{m.unit} cannot be converted to {unit}"))
        continue
      spec = None
      if spec_name:
        sp = S.resolve(spec_name, m.floor, decisions)
        spec = (sp.name, sp.value, sp.basis)
        if sp.question and (sp.name, m.floor) not in asked:
          asked.add((sp.name, m.floor))
          questions.append({"spec": sp.name, "floor": m.floor, "default": sp.value, "question": sp.question})
      floor = m.floor if (profile.split_by_floor or code in profile.split_by_floor_codes) else None
      key = (code, spec, floor, unit)
      line = lines.setdefault(key, BillLine(code, unit, ZERO, spec, floor))
      line.qty += qty
      line.sources.append((m.item_id, m.qty_key, m.floor, m.value, m.unit))
  inc = [(k, profile.included_in[k], v, inc_unit[k]) for k, v in sorted(included.items())]
  return Billed(profile.id, sorted(lines.values(), key=lambda l: (l.code, str(l.spec), str(l.floor))), inc, needed, questions, inc_src)

def accounted_for(billed: Billed) -> dict:
  """Every measured quantity the result accounts for, by (item id, quantity name, measured unit): in a line, included in another item's rate, or rate needed.
  It is the same under every profile and equals `measured_totals`; a profile that lost a quantity would show here. Each measured entry is billed under one code."""
  out: dict = defaultdict(lambda: ZERO)
  for line in billed.lines:
    for src in line.sources:
      out[(src[0], src[1], logic.normalise_unit(src[4]))] += src[3]
  for item_id, qty_key, _floor, value, unit in billed.included_sources:
    out[(item_id, qty_key, logic.normalise_unit(unit))] += value
  for item_id, qty_key, value, unit, _why in billed.rate_needed:
    out[(item_id, qty_key, logic.normalise_unit(unit))] += value
  return dict(out)

def measured_totals(measured: list) -> dict:
  out: dict = defaultdict(lambda: ZERO)
  for m in measured:
    out[(m.item_id, m.qty_key, logic.normalise_unit(m.unit))] += m.value
  return dict(out)
