from __future__ import annotations
from dataclasses import replace
from math import sqrt

PICTURE_PCT = 3.0
MEASURED_PCT = 3.0
ASSUMED_PCT = 10.0

MODEL = "MODEL"
CONFIRMED = "CONFIRMED"
MEASURED = "MEASURED"
ASSUMED = "ASSUMED"
PRINTED = "PRINTED"
STAMPED = "ENGINE"

SWITCH_BASES = frozenset({
  "wall_bed", "shoring", "footing_formwork", "slab_edge_formwork", "formwork_shared_faces", "tank_base_formwork", "fill_from_excavation",
  "floor_works_from_spaces", "beam_depth_includes_slab", "tie_band_replaces_lintel", "dpc_door_deduction", "stair_formwork_soffit_only",
  "beam_lintel_qs_rate", "formwork_shared_walls", "formwork_shared_beams", "formwork_joints", "rcc_wall_reveals", "wall_foundation_works", "wall_membrane",
  "wall_finishes_from_walls",
})

LEVEL_BASES = frozenset({"ngl", "dpc_level", "level"})
LEVEL_EXACT = frozenset({"user", "param", "typed", "model", "convention", "claim", "ONLY_LEVEL", "drawing", "qs", "element"})
WARNING_DRIVERS = {
  "FORMWORK_FRAME_ASSUMED": "frame faces",
  "FORMWORK_ITEM_ASSUMED": "roof item",
  "FORMWORK_BEAM_SLAB_ASSUMED": "beam against slab",
  "FORMWORK_JOINT_ASSUMED": "joints of lintel, chajja and balcony",
  "DERIVED_BOX_FOOTPRINT": "footprint taken from a box",
  "WALL_WORKS_STEPS_PROPOSED": "steps of the brick foundation",
  "WALL_FINISH_SIDES_ASSUMED": "which face of the wall is outside",
  "OPENING_SIZE_FROM_BOX": "size of the opening taken from its box",
  "ROOF_AREA_FROM_PLAN": "flat roof assumed",
  "ROOF_DECK_LAYERS_ASSUMED": "roof layers not drawn",
  "SOIL_STAB_AREA_ASSUMED": "loose soil taken under the whole filled floor",
  "STEEL_ALLOWANCE_ASSUMED": "binding wire and chairs not drawn",
  "STEEL_RING_ZONE_ASSUMED": "ring zone at the joints not printed",
}

EXACT_SOURCES = {"SCHEDULE_IMPORT": PRINTED, "MANUAL": CONFIRMED}
NOT_A_DRIVER = {"DPC_AREA": frozenset({"dpc_thickness_mm"})}

def _driver(name: str, basis: str, low: float, high: float) -> dict:
  return {"name": name, "basis": basis, "low_pct": low, "high_pct": high}

def _band(basis: str) -> float:
  return ASSUMED_PCT if basis == ASSUMED else MEASURED_PCT

def _model_drivers(entry) -> list:
  inputs = (entry.trace or {}).get("inputs") or {}
  warnings = set(entry.warnings or ())
  out: list = []
  
  kind = str(inputs.get("geometry_kind") or "")
  if kind == "BOX_ONLY":
    agrees = str(inputs.get("volume_check") or "") in ("VERIFIED", "FROM_MESH")
    out.append(_driver("geometry: bounding box", MEASURED if agrees else ASSUMED, -(MEASURED_PCT if agrees else ASSUMED_PCT), MEASURED_PCT if agrees else ASSUMED_PCT))
  elif kind == "QTO_ONLY":
    out.append(_driver("geometry: the model's own quantity", MEASURED, -MEASURED_PCT, MEASURED_PCT))
  if "QTO_GEOMETRY_MISMATCH" in warnings:
    out.append(_driver("model quantity differs from the geometry", MEASURED, -MEASURED_PCT, MEASURED_PCT))
  if "OPENINGS_NOT_DEDUCTED" in warnings:
    out.append(_driver("openings not deducted", ASSUMED, -ASSUMED_PCT, 0.0))
  return out

def _derived_drivers(entry) -> list:
  spec = entry.spec or (entry.trace or {}).get("inputs", {}).get("spec") or {}
  basis = spec.get("basis") or {}
  out: list = []
  skip = NOT_A_DRIVER.get(entry.formula_code, frozenset())
  
  for name, source in basis.items():
    if name in SWITCH_BASES or name in skip:
      continue
    if name in LEVEL_BASES:
      if str(source) not in LEVEL_EXACT:
        out.append(_driver(f"{name} taken by default" if name != "level" else "storey taken by default", ASSUMED, -ASSUMED_PCT, ASSUMED_PCT))
      continue
  
    if str(source) == "default":
      out.append(_driver(name, ASSUMED, -ASSUMED_PCT, ASSUMED_PCT))
  seen = {d["name"] for d in out}
  for code, label in WARNING_DRIVERS.items():
    if code in (entry.warnings or ()) and label not in seen:
      out.append(_driver(label, ASSUMED, -ASSUMED_PCT, ASSUMED_PCT))
  return out

def drivers_of(entry) -> tuple[str, list]:
  kind = getattr(entry, "source_kind", "MODEL") or "MODEL"
  if kind == "PDF_TAKEOFF":
    return MEASURED, [_driver("hand measurement on the drawing", MEASURED, -MEASURED_PCT, MEASURED_PCT)]
  if kind in EXACT_SOURCES:
    return EXACT_SOURCES[kind], []
  if kind == "ESTIMATE":
    return ASSUMED, [_driver("estimate", ASSUMED, -ASSUMED_PCT, ASSUMED_PCT)]
  if kind == "DERIVED":
    return CONFIRMED, _derived_drivers(entry)
  return MODEL, _model_drivers(entry)

def range_for_entry(entry) -> dict:
  grade, drivers = drivers_of(entry)
  lows = [d["low_pct"] for d in drivers]
  highs = [d["high_pct"] for d in drivers]
  if drivers:
    grade = ASSUMED if any(d["basis"] == ASSUMED for d in drivers) else MEASURED
  return {
    "grade": grade, "bounded": True,
    "low_pct": round(-sqrt(sum(x * x for x in lows)), 2) if lows else 0.0,
    "high_pct": round(sqrt(sum(x * x for x in highs)), 2) if highs else 0.0,
    "leaves_out": False, "drivers": drivers, "by": STAMPED,
  }

def has_range(entry) -> bool:
  return isinstance((entry.trace or {}).get("range"), dict)

def with_range(entry) -> dict:
  trace = entry.trace or {}
  if isinstance(trace.get("range"), dict):
    return trace
  return {**trace, "range": range_for_entry(entry)}

def stamp(entry):
  if has_range(entry):
    return entry
  return replace(entry, trace=with_range(entry))

def stamp_all(rows) -> list:
  return [stamp(r) for r in rows]

def summary(rows) -> dict:
  grades: dict = {}
  stamped = unbounded = 0
  for r in rows:
    rg = (r.trace or {}).get("range")
    if not isinstance(rg, dict):
      continue
  
    grades[str(rg.get("grade"))] = grades.get(str(rg.get("grade")), 0) + 1
    if rg.get("by") == STAMPED:
      stamped += 1
    if not rg.get("bounded"):
      unbounded += 1
  return {"rows": len(rows), "grades": dict(sorted(grades.items())), "stamped": stamped, "unbounded": unbounded}
