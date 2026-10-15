from __future__ import annotations
from decimal import Decimal
from dataclasses import dataclass, field
from app.engine.measure.rebar import KG_M_DIVISOR, REBAR_WORK_ITEM
from app.engine.measure.models import CalculationContext, LedgerEntry, Solid
import math
from uuid import uuid5
from app.engine.measure.derived import DERIVED, FACTOR_ASSUMED, FACTOR_CONFIRMED, counted_measurement_ids, resolve_params
from app.engine.measure.units import q4, q6
from app.engine.measure.takeoff import SOURCE_KIND as PDF_SOURCE

FORMULA = "PDF_MEMBER_STEEL_WEIGHT"
RECIPE_CODE = "PDF_LINTEL_STEEL"
COVER_PARAM, HOOK_PARAM = "steel_cover_mm", "ring_hook_dia"
STEEL_PARAMS = (COVER_PARAM, HOOK_PARAM)
PARAMS_USED = {"LINTEL": STEEL_PARAMS}
IFC_OF = {"LINTEL": "IfcBeam"}
MAX_MARKS = 5000
CODE_ASSUMED = "STEEL_ASSUMED"
STEEL_CODES = (CODE_ASSUMED,)
BAR_ROLES = ("bottom", "top", "bars")
EIGHTH_IN_MM = Decimal("3.175")
MM = Decimal("1000")

@dataclass(frozen=True)
class SteelResult:
  solids: list = field(default_factory=list)
  ledger: list = field(default_factory=list)
  stats: dict = field(default_factory=dict)

def bar_dia_mm(bar: int) -> Decimal:
  """A bar number is the diameter in eighths of an inch: #3 is 3/8 in (9.525 mm), #4 is 1/2 in (12.7 mm)."""
  return Decimal(int(bar)) * EIGHTH_IN_MM

def kg_per_m(bar: int) -> Decimal:
  d = bar_dia_mm(bar)
  return (d * d / KG_M_DIVISOR).quantize(Decimal("0.0001"))

def _num(v) -> Decimal | None:
  try:
    d = Decimal(str(v))
  except Exception:
    return None
  return d if d > 0 else None

def clean_steel(raw) -> dict | None:
  """The bars and rings of a member as plain numbers; anything that does not read is dropped. None when nothing is left."""
  if not isinstance(raw, dict):
    return None
  out: dict = {}
  for role in BAR_ROLES:
    g = raw.get(role)
    if isinstance(g, dict):
      n, bar = _num(g.get("n")), _num(g.get("bar"))
      if n is not None and bar is not None and n == n.to_integral_value() and bar == bar.to_integral_value() and 2 <= bar <= 12 and n <= 30:
        out[role] = {"n": int(n), "bar": int(bar)}
  ring = raw.get("ring")
  if isinstance(ring, dict):
    bar, spacing = _num(ring.get("bar")), _num(ring.get("spacing_mm"))
    if bar is not None and spacing is not None and bar == bar.to_integral_value() and 2 <= bar <= 12 and spacing <= 1000:
      out["ring"] = {"bar": int(bar), "spacing_mm": float(spacing)}
  return out or None

def steel_for(category: str, length: Decimal, width: Decimal, depth: Decimal, steel: dict, cover: Decimal, hook_dia: Decimal) -> tuple:
  """Weight of the bars and rings of one member, as (bar lines, ring line or None, kg). Bars run the member length less the cover at each end. Rings
  are spaced from the first to the last, so there is one more than the number of spaces; a ring is the perimeter of the cage inside the cover plus the
  hook allowance, given as a number of bar diameters. Lap and wastage are not added."""
  run = length - 2 * cover
  if run <= 0:
    return [], None, Decimal("0")
  lines = []
  total = Decimal("0")
  for role in BAR_ROLES:
    g = steel.get(role)
    if not g:
      continue
  
    w = kg_per_m(g["bar"])
    kg = q6(Decimal(g["n"]) * w * run / MM)
    lines.append({"role": role, "n": g["n"], "bar": g["bar"], "dia_mm": str(bar_dia_mm(g["bar"])), "kg_per_m": str(w), "length_m": str(q6(run / MM)), "kg": str(kg)})
    total += kg
  ring_line = None
  r = steel.get("ring")
  if r:
    inner_w, inner_d = width - 2 * cover, depth - 2 * cover
    if inner_w > 0 and inner_d > 0:
      spacing = Decimal(str(r["spacing_mm"]))
      count = int(run // spacing) + 1
      cut = 2 * (inner_w + inner_d) + hook_dia * bar_dia_mm(r["bar"])
      w = kg_per_m(r["bar"])
      kg = q6(Decimal(count) * cut * w / MM)
      ring_line = {"bar": r["bar"], "dia_mm": str(bar_dia_mm(r["bar"])), "spacing_mm": str(spacing), "count": count, "cut_length_m": str(q6(cut / MM)),
        "kg_per_m": str(w), "kg": str(kg)}
      total += kg
  return lines, ring_line, q6(total)

def measure_pdf_steel(ctx: CalculationContext, ledger: list, extra_ledger=()) -> SteelResult:
  """Reinforcement weight (kg) for the members read from a PDF whose bars are printed with them: today the lintels, from the row of the lintel table.
  One row per mark, so a row opens the mark it came from. It stands aside when the model or the PDF already carries a row on the steel item. The cover and
  the hook allowance are site assumptions; a lintel whose row printed no bars is skipped and counted."""
  stats: dict = {"enabled": True, "ran": False}
  inputs = tuple(m for m in (getattr(ctx.takeoff, "formwork", ()) or ()) if m.category in PARAMS_USED and m.steel)
  if not inputs:
    stats["reason"] = "NO_MEMBERS"
    return SteelResult(stats=stats)

  taken = {r.work_item_code for r in ledger if r.source_kind == "MODEL" and r.quantity > 0}
  taken |= {r.work_item_code for r in (extra_ledger or ()) if getattr(r, "source_kind", None) == PDF_SOURCE and r.quantity > 0}
  if REBAR_WORK_ITEM in taken:
    stats["reason"] = "ALL_ITEMS_IN_MODEL"
    return SteelResult(stats=stats)
  if sum(m.count for m in inputs) > MAX_MARKS:
    stats["reason"] = "TOO_MANY_MARKS"
    return SteelResult(stats=stats)
  params = resolve_params(ctx)
  cover = Decimal(str(params[COVER_PARAM]["value"]))
  hook = Decimal(str(params[HOOK_PARAM]["value"]))
  counted = counted_measurement_ids(extra_ledger)
  skipped: dict = {}
  by_category: dict = {}
  solids: list = []
  rows: list = []
  
  for m in sorted(inputs, key=lambda b: str(b.measurement_id)):
    cat = m.category
    if str(m.measurement_id) not in counted:
      skipped["NOT_COUNTED"] = skipped.get("NOT_COUNTED", 0) + m.count
      continue
    steel = clean_steel(m.steel)
    if not steel:
      skipped["NO_BARS"] = skipped.get("NO_BARS", 0) + m.count
      continue
    lines, ring, kg = steel_for(cat, m.length_mm, m.width_mm, m.depth_mm, steel, cover, hook)
    if kg <= 0:
      skipped["NO_SIZE"] = skipped.get("NO_SIZE", 0) + m.count
      continue
  
    used = PARAMS_USED[cat]
    assumed = [n for n in used if params[n]["source"] == "default"]
    factor = FACTOR_ASSUMED if assumed else FACTOR_CONFIRMED
    confidence = max(Decimal("0"), min(Decimal("1"), q4(m.confidence * factor)))
    warnings = [CODE_ASSUMED] if assumed else []
    spec = {"kind": DERIVED, "recipe": RECIPE_CODE, "item": "STEEL", "category": cat,
      "params": {n: params[n]["value"] for n in used}, "basis": {n: params[n]["source"] for n in used}}
    step_lines = [{"op": "bars", **ln} for ln in lines] + ([{"op": "rings", **ring}] if ring else [])
    for i in range(m.count):
      eid = m.element_ids[i] if i < len(m.element_ids) else None
      solid_id = uuid5(ctx.run_id, f"solid|steel|{m.measurement_id}|{i}")
      solids.append(Solid(
        id=solid_id, element_id=eid, ifc_type=IFC_OF[cat], role=cat, level_id=m.level_id, geometry_kind="QTO_ONLY",
        classification_confidence=m.confidence, confidence_factor=factor, component_type="DERIVED_STEEL",
        gross_length_m=q6(m.length_mm / MM), status="REVIEW_REQUIRED" if warnings else "OK"))
      source = {"measurement_id": str(m.measurement_id), "candidate_id": str(m.candidate_id), "sheet_id": str(m.sheet_id), "page_no": m.page_no,
        "category": cat, "tag": m.tag, "instance": i + 1, "instances": m.count, "size_mm": [float(m.length_mm), float(m.width_mm), float(m.depth_mm)],
        "bars": lines, "rings": ring}
      
      rows.append(LedgerEntry(
        solid_id=solid_id, element_id=eid, level_id=m.level_id, work_item_code=REBAR_WORK_ITEM, quantity=kg, unit="kg", material_grade=None,
        confidence=confidence, formula_code=FORMULA,
        trace={"formula_code": FORMULA, "engine_version": ctx.engine_version, "convention": ctx.convention_code,
          "rule_set": {"code": ctx.rule_set_code, "version": ctx.rule_set_version},
          "inputs": {"recipe": RECIPE_CODE, "spec": spec, "steel_source": source},
          "steps": [*step_lines, {"op": "total_kg", "kg": str(kg)}], "net": {"kg": str(kg)}, "rounding": "half_up,6dp"},
        warnings=tuple(warnings), source_kind=DERIVED, spec=spec, spec_key="derived"))
      slot = by_category.setdefault(cat, {"marks": 0, "kg": Decimal("0")})
      slot["marks"] += 1
      slot["kg"] += kg
      
  rows.sort(key=lambda r: (str(r.level_id), r.trace["inputs"]["steel_source"]["category"], str(r.solid_id)))
  total = sum((r.quantity for r in rows), Decimal("0"))
  stats.update({
    "ran": bool(rows), "rows": len(rows), "kg": str(q6(total)), "code": REBAR_WORK_ITEM,
    "by_category": {k: {"marks": v["marks"], "kg": str(q6(v["kg"]))} for k, v in sorted(by_category.items())},
    "skipped": dict(sorted(skipped.items())),
    "params": {n: dict(params[n]) for n in STEEL_PARAMS},
    "assumed": sorted({n for r in rows for n, b in ((r.spec or {}).get("basis") or {}).items() if b == "default"}),
    "lap_and_wastage_not_added": bool(rows),
  })
  if not rows:
    stats["reason"] = "NOTHING_TO_REINFORCE"
  return SteelResult(solids=solids, ledger=rows, stats=stats)

def steel_check(solids: list, ledger: list) -> list:
  failures: list = []
  by_id = {s.id for s in solids}
  
  for r in ledger:
    if r.source_kind != DERIVED or r.formula_code != FORMULA:
      continue
    if r.solid_id not in by_id:
      failures.append(f"steel row references unknown solid {r.solid_id}")
    if r.unit != "kg":
      failures.append(f"steel row {r.solid_id} is not in kg")
    if r.work_stage is not None:
      failures.append(f"steel row {r.solid_id} carries a work stage")
    src = (((r.trace or {}).get("inputs") or {}).get("steel_source") or {})
    try:
      total = sum((Decimal(b["kg"]) for b in src.get("bars") or []), Decimal("0"))
      if src.get("rings"):
        total += Decimal(src["rings"]["kg"])
    except Exception:
      failures.append(f"steel row {r.solid_id} has no bar lines in its trace")
      continue
    if abs(total - r.quantity) > Decimal("0.000004"):
      failures.append(f"steel weight != sum of its bars and rings on solid {r.solid_id}")
  return failures
