from __future__ import annotations
from decimal import Decimal
from dataclasses import dataclass, field
from collections import defaultdict
from app.modules.drawings_boq.pricing.billing import group as G
from app.modules.drawings_boq.pricing.priced import coefficients as C

ZERO = Decimal(0)
CONCRETE_SPEC, MORTAR_SPECS = "concrete_mix", ("brick_mortar", "plaster_ratio")

@dataclass
class Materials:
  totals: dict = field(default_factory=lambda: defaultdict(lambda: ZERO))     
  rows: list = field(default_factory=list)          
  missing: list = field(default_factory=list)       

def from_lines(billed: G.Billed, table: C.Table | None, bricks_per_cft: Decimal | None = None, brick_item_prefix: str = "7-") -> Materials:
  m = Materials()
  
  for line in billed.lines:
    if not line.spec:
      pass
    else:
      name, mix = line.spec[0], line.spec[1]
      kind = "CONCRETE" if name == CONCRETE_SPEC else "MORTAR" if name in MORTAR_SPECS else None
      if kind:
        row = C.find(table, kind, mix)
        qty = G.convert(line.qty, line.unit, row.unit) if row else None
        if row is None:
          m.missing.append((line.code, f"no {kind.lower()} row for mix {mix} in the coefficient table" + ("" if table else " (no table is loaded for this edition)")))
        elif qty is None:
          m.missing.append((line.code, f"the line is in {line.unit} and the coefficient row is per {row.unit}"))
        else:
          for mat in C.MATERIALS:
            per = getattr(row, mat)
            if per is not None:
              amount = qty / row.per_qty * per
              m.totals[mat] += amount
              m.rows.append((line.code, mat, amount, f"{qty.quantize(Decimal('0.001'))} {row.unit} of {kind.lower()} {mix} at {per} per {row.per_qty} {row.unit}" + (f" (page {row.page})" if row.page else "")))
              
    if line.code.startswith(brick_item_prefix) and line.unit == "cft" and bricks_per_cft is not None:
      m.totals["bricks"] += line.qty * bricks_per_cft
      m.rows.append((line.code, "bricks", line.qty * bricks_per_cft, f"{line.qty.quantize(Decimal('0.001'))} cft at {bricks_per_cft} bricks per cft (a convention)"))
    if line.code.startswith("6-12") or line.code == "STEEL":
      kg = G.convert(line.qty, line.unit, "kg")
      if kg is not None:
        m.totals["steel_kg"] += kg
        m.rows.append((line.code, "steel_kg", kg, f"{line.qty.quantize(Decimal('0.001'))} {line.unit} of steel"))
        
  if bricks_per_cft is None and any(l.code.startswith(brick_item_prefix) and l.unit == "cft" for l in billed.lines):
    m.missing.append(("bricks", "no bricks-per-cft convention was given, so the bricks are not counted"))
  return m
