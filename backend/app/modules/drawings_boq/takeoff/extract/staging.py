from __future__ import annotations
import math
from app.modules.drawings_boq.takeoff.extract import foundation as FD
from app.modules.drawings_boq.takeoff.extract import finishes as FN
from app.modules.drawings_boq.takeoff.extract import config as C
from app.engine.measure import proposed as QP

SCAFFOLD_OUTSIDE = "SCAFFOLD_OUTSIDE"
PROPS_SLAB = "PROPS_SLAB"
ITEMS = (SCAFFOLD_OUTSIDE, PROPS_SLAB)
WORK_ITEM = {SCAFFOLD_OUTSIDE: "SCF-EXTERNAL", PROPS_SLAB: "FRM-PROPS"}
MODE = {SCAFFOLD_OUTSIDE: "COUNT_X_AREA", PROPS_SLAB: "COUNT_X_AREA"}
STAGING_ABOVE_MM = 3600.0
BELOW_GROUND = ("BASEMENT", "FOUNDATION")

def _ft(mm: float) -> str:
  return f"{round(mm / 304.8, 2):g}"

def _make(cls, ctx: dict, finish, key_parts: tuple, item: str, label: str, tag: str, points: list, area_m2: float, facts: dict, notes: list, base: float):
  cand = cls(key=FD._key_of(key_parts), category="WALL", kind="COUNT", quantity_mode=MODE[item], label=label, tag=tag, geometry={"points": points},
    params={"length_mm": round(area_m2 * 1000.0, 1), "width_mm": 1000.0, "dims_basis": "SPECIFIED"}, missing=[], work_item=WORK_ITEM[item], status="VALID", confidence=0.0,
    facts={**facts, "foundation_item": item}, notes=notes, source="VECTOR_SNAP", count=1)
  return finish(cand, ctx, base)

def scaffold_candidates(finishes: list, floor_heights: dict | None, level_hint: str | None, ctx: dict, cls, finish) -> tuple:
  out: list = []
  notes: list = []

  hint = str(level_hint or "").upper()
  if not hint or hint in BELOW_GROUND:
    return out, notes
  fh = (floor_heights or {}).get(level_hint or "") or {}
  level, ftf = fh.get("level_mm"), fh.get("floor_to_floor_mm")
  for c in finishes:
    f = c.facts or {}
    face = float(f.get("face_length_m") or 0.0)
    if f.get("foundation_item") != FN.PLASTER_OUTSIDE or face <= 0.0:
      continue

    if level is None or not ftf:
      notes.append(C.note("SCAFFOLD_NEEDS_LEVELS", floor=hint))
      continue
    top = float(level) + float(ftf)
    above = top - max(float(level), STAGING_ABOVE_MM)
    if above <= 0.0:
      continue

    area = face * above / 1000.0
    tail = c.label.rsplit(" · ", 1)[-1] if " · " in c.label and not c.label.endswith("of face") else None
    label = f"Scaffolding on the outside walls above {STAGING_ABOVE_MM / 1000.0:g} m · {area:.2f} m²" + (f" · {tail}" if tail else "")
    facts = {"derived_from": "WALLS", "staging": "SCAFFOLD", "plaster_key": c.key, "face_length_m": round(face, 3), "floor_level_mm": float(level), "floor_to_floor_mm": float(ftf),
      "top_mm": round(top, 1), "threshold_mm": STAGING_ABOVE_MM, "above_mm": round(above, 1), "area_m2": round(area, 3),
      "whole_storey_m2": round(face * float(ftf) / 1000.0, 3)}
    out.append(_make(cls, ctx, finish, (SCAFFOLD_OUTSIDE, "STAGING", level_hint or ""), SCAFFOLD_OUTSIDE, label, "SCAFFOLD-OUTSIDE", list((c.geometry or {}).get("points") or [[0.0, 0.0]])[:1],
      area, facts, [C.note("SCAFFOLD_ABOVE_THRESHOLD", threshold_mm=STAGING_ABOVE_MM)], 0.6))
  return out, notes

def props_candidates(slabs: list, floor_heights: dict | None, ctx: dict, cls, finish) -> list:
  out: list = []

  for s in slabs:
    f = s.facts or {}
    area = float(f.get("area_m2") or 0.0)
    clear = ((floor_heights or {}).get(f.get("floor") or "") or {}).get("clear_mm")
    if s.status == "INVALID" or area <= 0.0 or not clear or float(clear) <= STAGING_ABOVE_MM:
      continue

    steps = max(1, int(math.ceil(round((float(clear) - STAGING_ABOVE_MM) / QP.PROPS_STEP_MM, 6))))
    quantity = area * steps
    label = f"Props under the slab · {area:.2f} m² · {_ft(float(clear))} ft clear · {steps} extra metre{'' if steps == 1 else 's'} · {quantity:.2f} m²"
    facts = {"derived_from": "SLAB", "staging": "PROPS", "slab_key": s.key, "floor": f.get("floor"), "clear_mm": float(clear), "threshold_mm": STAGING_ABOVE_MM, "slab_area_m2": round(area, 3),
      "step_mm": QP.PROPS_STEP_MM, "steps": steps, "area_m2": round(quantity, 3)}
    out.append(_make(cls, ctx, finish, (PROPS_SLAB, "STAGING", s.key), PROPS_SLAB, label, "PROPS-SLAB", list((s.geometry or {}).get("points") or [[0.0, 0.0]])[:1], quantity, facts,
      [C.note("PROPS_ABOVE_THRESHOLD", threshold_mm=STAGING_ABOVE_MM, step_mm=QP.PROPS_STEP_MM, steps=steps)], 0.6))
  return out
