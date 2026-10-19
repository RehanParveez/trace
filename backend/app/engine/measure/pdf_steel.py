from __future__ import annotations
from decimal import Decimal
from dataclasses import dataclass, field
from app.engine.measure.rebar import REBAR_WORK_ITEM, ESTIMATE_BANDS
from app.engine.measure.models import CalculationContext, LedgerEntry, Solid
from uuid import uuid5
from app.engine.measure.derived import DERIVED, FACTOR_ASSUMED, FACTOR_CONFIRMED, counted_measurement_ids, resolve_params
from app.engine.measure.member_steel import FAMILY_OF, STEEL_FAMILIES, bar_dia_mm_of, clean_steel, member_lines, kg_per_m  # noqa: F401
from app.engine.measure.units import q4, q6
from app.engine.measure import steel_review as SRV
from app.engine.measure.takeoff import SOURCE_KIND as PDF_SOURCE, range_trace

"""Reinforcement weight (kg) for the concrete members read from a PDF whose bars are printed with them: lintels from the lintel table, and columns,
beams, footings, slabs and RCC walls from the notes printed for their marks or typed at accept. One row per mark."""

FORMULA = "PDF_MEMBER_STEEL_WEIGHT"
RECIPE_CODE = "PDF_MEMBER_STEEL"
LEGACY_RECIPE = "PDF_LINTEL_STEEL"
COVER_PARAM, HOOK_PARAM, LAP_PARAM, ANCHOR_PARAM, WASTAGE_PARAM = "steel_cover_mm", "ring_hook_dia", "bar_lap_dia", "bar_anchor_dia", "steel_wastage_pct"
COVER_OF = {"LINTEL": "steel_cover_beam_mm", "BEAM": "steel_cover_beam_mm", "COLUMN": "steel_cover_column_mm", "FOOTING": "steel_cover_footing_mm",
  "SLAB": "steel_cover_slab_mm", "RCC_WALL": "steel_cover_wall_mm",
  "STAIR": "steel_cover_slab_mm", "CHAJJA": "steel_cover_slab_mm", "BALCONY_SLAB": "steel_cover_slab_mm", "PARAPET": "steel_cover_wall_mm"}
STEEL_PARAMS = (COVER_PARAM, HOOK_PARAM, LAP_PARAM, ANCHOR_PARAM, WASTAGE_PARAM, *dict.fromkeys(COVER_OF.values()))

def extra_of(m) -> dict | None:
  """The stair or tank detail a member's lines need beyond its box (the slope of a flight; the height and walls of a tank)."""
  return {k: v for k, v in (("stair", getattr(m, "stair", None)), ("site", getattr(m, "site", None))) if v} or None

def cover_name(category: str, params: dict) -> str:
  """The cover parameter a member uses: the one for its kind when it was given (typed, convention, drawing, QS), else the general cover."""
  name = COVER_OF.get(category, COVER_PARAM)
  return name if params[name]["source"] != "default" else COVER_PARAM
CONVENTION_PARAMS = {
  "LINTEL": (COVER_PARAM, HOOK_PARAM, ANCHOR_PARAM), "BEAM": (COVER_PARAM, HOOK_PARAM, ANCHOR_PARAM),
  "COLUMN": (COVER_PARAM, HOOK_PARAM, LAP_PARAM, ANCHOR_PARAM), "FOOTING": (COVER_PARAM,), "SLAB": (COVER_PARAM,), "RCC_WALL": (COVER_PARAM,),
  "STAIR": (COVER_PARAM,), "TANK": (COVER_PARAM,), "PARAPET": (COVER_PARAM,), "CHAJJA": (COVER_PARAM,), "BALCONY_SLAB": (COVER_PARAM,)}
PARAMS_USED = CONVENTION_PARAMS
IFC_OF = {"LINTEL": "IfcBeam", "BEAM": "IfcBeam", "COLUMN": "IfcColumn", "FOOTING": "IfcFooting", "SLAB": "IfcSlab", "RCC_WALL": "IfcWall", "STAIR": "IfcStair", "TANK": "IfcTank", "PARAPET": "IfcWall", "CHAJJA": "IfcSlab", "BALCONY_SLAB": "IfcSlab"}
ROLE_OF = {"RCC_WALL": "WALL"}
MAX_MARKS = 5000
CODE_ASSUMED = "STEEL_ASSUMED"
CODE_INTENSITY = "STEEL_INTENSITY_OUT_OF_RANGE"
STEEL_CODES = (CODE_ASSUMED, CODE_INTENSITY)
MM = Decimal("1000")
MM3_PER_M3 = Decimal("1000000000")
INTENSITY_FAMILY = {"LINTEL": "BEAM", "BEAM": "BEAM", "COLUMN": "COLUMN", "FOOTING": "FOOTING", "SLAB": "SLAB", "CHAJJA": "SLAB", "BALCONY_SLAB": "SLAB"}

@dataclass(frozen=True)
class SteelResult:
  solids: list = field(default_factory=list)
  ledger: list = field(default_factory=list)
  stats: dict = field(default_factory=dict)

def _plate(category: str, length: Decimal, width: Decimal, depth: Decimal) -> tuple:
  """The size a member's steel is worked out from. A wall's mesh covers its run and height; its thickness is not a mesh side."""
  if category in ("RCC_WALL", "PARAPET"):
    return length, depth, width
  return length, width, depth

def intensity_range(category: str) -> tuple | None:
  family = INTENSITY_FAMILY.get(category)
  band = ESTIMATE_BANDS.get(family or "")
  return (band[0], band[2]) if band else None

def measure_pdf_steel(ctx: CalculationContext, ledger: list, extra_ledger=()) -> SteelResult:
  """Reinforcement weight (kg) for the members read from a PDF whose bars are printed or typed with them. One row per mark, so a row opens the mark it
  came from. It stands aside when the model or the PDF already carries a row on the steel item. Cover, hook, lap and anchorage are site conventions that
  fall back to flagged defaults; a member with no bars is skipped and counted. Wastage is a project parameter, 0 unless set. The intensity (kg per m3)
  of each family is compared with the working range and flagged, never changed."""
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
  value = {n: Decimal(str(params[n]["value"])) for n in STEEL_PARAMS}
  wastage = value[WASTAGE_PARAM]
  lap_table = ((getattr(ctx, "drawing_params", None) or {}).get("lap_table_mm") or None) if params[LAP_PARAM]["source"] == "drawing" else None
  counted = counted_measurement_ids(extra_ledger)
  skipped: dict = {}
  by_category: dict = {}
  by_dia: dict = {}
  family_volume: dict = {}
  family_kg: dict = {}
  reviewable: list = []
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
    length, width, depth = _plate(cat, m.length_mm, m.width_mm, m.depth_mm)
    cover_n = cover_name(cat, params)
    lines, bare = member_lines(cat, length, width, depth, steel, value[cover_n], value[HOOK_PARAM], value[LAP_PARAM], value[ANCHOR_PARAM], lap_table, extra_of(m))
    reviewable.append({"cat": cat, "length": length, "width": width, "depth": depth, "steel": steel, "count": m.count, "cover": value[cover_n], "hook": value[HOOK_PARAM]})
    if bare <= 0:
      skipped["NO_SIZE"] = skipped.get("NO_SIZE", 0) + m.count
      continue
  
    kg = q6(bare * (1 + wastage / 100))
    used = tuple(cover_n if n == COVER_PARAM else n for n in PARAMS_USED[cat])
    assumed = [n for n in used if params[n]["source"] == "default"]
    factor = FACTOR_ASSUMED if assumed else FACTOR_CONFIRMED
    confidence = max(Decimal("0"), min(Decimal("1"), q4(m.confidence * factor)))
    warnings = [CODE_ASSUMED] if assumed else []
    spec = {"kind": DERIVED, "recipe": RECIPE_CODE, "item": "STEEL", "category": cat,
      "params": {n: params[n]["value"] for n in (*used, WASTAGE_PARAM)}, "basis": {n: params[n]["source"] for n in used}}
    step_lines = [{"op": ln["kind"], **ln} for ln in lines]
    volume = q6(m.length_mm * m.width_mm * m.depth_mm / MM3_PER_M3)
    for i in range(m.count):
      eid = m.element_ids[i] if i < len(m.element_ids) else None
      solid_id = uuid5(ctx.run_id, f"solid|steel|{m.measurement_id}|{i}")
      
      solids.append(Solid(
        id=solid_id, element_id=eid, ifc_type=IFC_OF[cat], role=ROLE_OF.get(cat, cat), level_id=m.level_id, geometry_kind="QTO_ONLY",
        classification_confidence=m.confidence, confidence_factor=factor, component_type="DERIVED_STEEL",
        gross_length_m=q6(m.length_mm / MM), status="REVIEW_REQUIRED" if warnings else "OK"))
      source = {"measurement_id": str(m.measurement_id), "candidate_id": str(m.candidate_id), "sheet_id": str(m.sheet_id), "page_no": m.page_no,
        "category": cat, "tag": m.tag, "instance": i + 1, "instances": m.count, "size_mm": [float(m.length_mm), float(m.width_mm), float(m.depth_mm)],
        "steel": steel, "lines": lines, "bare_kg": str(bare), "wastage_pct": str(wastage), "concrete_m3": str(volume)}
      rows.append(LedgerEntry(
        solid_id=solid_id, element_id=eid, level_id=m.level_id, work_item_code=REBAR_WORK_ITEM, quantity=kg, unit="kg", material_grade=None,
        confidence=confidence, formula_code=FORMULA,
        trace={"formula_code": FORMULA, "engine_version": ctx.engine_version, "convention": ctx.convention_code,
          "rule_set": {"code": ctx.rule_set_code, "version": ctx.rule_set_version},
          "inputs": {"recipe": RECIPE_CODE, "spec": spec, "steel_source": source},
          "steps": [*step_lines, {"op": "total_kg", "bare_kg": str(bare), "wastage_pct": str(wastage), "kg": str(kg)}], "net": {"kg": str(kg)},
          "rounding": "half_up,6dp", **({"range": rg} if (rg := range_trace(ctx.takeoff, m.measurement_id)) else {})},
        warnings=tuple(warnings), source_kind=DERIVED, spec=spec, spec_key="derived"))
      slot = by_category.setdefault(cat, {"marks": 0, "kg": Decimal("0"), "bare_kg": Decimal("0")})
      
      slot["marks"] += 1
      slot["kg"] += kg
      slot["bare_kg"] += bare
      for ln in lines:
        d = by_dia.setdefault(ln["dia_mm"], {"kg": Decimal("0"), "length_m": Decimal("0")})
        d["kg"] += Decimal(ln["kg"])
        d["length_m"] += Decimal(ln["length_m"])
      fam = INTENSITY_FAMILY.get(cat)
      if fam:
        family_volume[fam] = family_volume.get(fam, Decimal("0")) + volume
        family_kg[fam] = family_kg.get(fam, Decimal("0")) + bare

  rows.sort(key=lambda r: (str(r.level_id), r.trace["inputs"]["steel_source"]["category"], str(r.solid_id)))
  total = sum((r.quantity for r in rows), Decimal("0"))
  bare_total = sum((v["bare_kg"] for v in by_category.values()), Decimal("0"))
  intensity: dict = {}
  
  for fam, vol in sorted(family_volume.items()):
    if vol <= 0:
      continue
    value_kgm3 = family_kg[fam] / vol
    low, high = ESTIMATE_BANDS[fam][0], ESTIMATE_BANDS[fam][2]
    status = "BELOW_RANGE" if value_kgm3 < low else "ABOVE_RANGE" if value_kgm3 > high else "IN_RANGE"
    intensity[fam] = {"kg": str(q6(family_kg[fam])), "concrete_m3": str(q6(vol)), "kg_per_m3": str(q4(value_kgm3)), "range": [str(low), str(high)], "status": status}
  stats.update({
    "ran": bool(rows), "rows": len(rows), "kg": str(q6(total)), "bare_kg": str(q6(bare_total)), "code": REBAR_WORK_ITEM,
    "wastage_pct": str(wastage), "with_5pct_kg": str(q6(bare_total * Decimal("1.05"))),
    "by_category": {k: {"marks": v["marks"], "kg": str(q6(v["kg"])), "bare_kg": str(q6(v["bare_kg"]))} for k, v in sorted(by_category.items())},
    "by_diameter": {k: {"kg": str(q6(v["kg"])), "length_m": str(q6(v["length_m"]))} for k, v in sorted(by_dia.items(), key=lambda kv: Decimal(kv[0]))},
    "intensity": intensity,
    "skipped": dict(sorted(skipped.items())),
    "params": {n: dict(params[n]) for n in STEEL_PARAMS},
    "assumed": sorted({n for r in rows for n, b in ((r.spec or {}).get("basis") or {}).items() if b == "default"}),
    "lap_and_wastage_not_added": bool(rows) and wastage == 0,
    "review": SRV.review(reviewable, value[ANCHOR_PARAM], value[LAP_PARAM], params[LAP_PARAM]["source"] == "default", lap_table) if reviewable else {},
  })
  if not rows:
    stats["reason"] = "NOTHING_TO_REINFORCE"
  return SteelResult(solids=solids, ledger=rows, stats=stats)

def pdf_steel_check(solids: list, ledger: list) -> list:
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
      bare = sum((Decimal(b["kg"]) for b in src.get("lines") or []), Decimal("0"))
      pct = Decimal(src["wastage_pct"])
    except Exception:
      failures.append(f"steel row {r.solid_id} has no bar lines in its trace")
      continue
    if abs(q6(bare * (1 + pct / 100)) - r.quantity) > Decimal("0.000004"):
      failures.append(f"steel weight != sum of its bars, rings and mesh on solid {r.solid_id}")
  return failures
