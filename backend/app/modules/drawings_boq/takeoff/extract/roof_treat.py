from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import foundation as FD
from app.modules.drawings_boq.takeoff.extract import floor_sources as FS
from app.modules.drawings_boq.takeoff.levels import level_spec
from app.modules.drawings_boq.takeoff.extract import config as C

ITEM = FD.ROOF_TREATMENT
MIN_PROJECTION_M2 = 0.05
BELOW = ("FOUNDATION", "BASEMENT")

def _rank(floor) -> int:
  return FS.ORDER.index(floor) if floor in FS.ORDER else -1

def _live(slabs: list) -> list:
  return [c for c in slabs if c.category == "SLAB" and c.status != "INVALID" and (c.facts or {}).get("floor")]

def roof_slab(slabs: list) -> tuple:
  live = _live(slabs)
  roofs = [c for c in live if c.facts["floor"] == "ROOF"]
  
  if roofs:
    return roofs[0], "ROOF_PLAN"
  floors = {c.facts["floor"] for c in live}
  if len(floors) >= 2:
    top = max(live, key=lambda c: (_rank(c.facts["floor"]), str(c.key)))
    if _rank(top.facts["floor"]) >= 0:
      return top, "TOP_OF_SHEET"
  return None, None

def main_roof_slab(slabs: list, upper) -> object | None:
  live = [c for c in _live(slabs) if c is not upper and c.facts["floor"] not in ("ROOF", *BELOW) and _rank(c.facts["floor"]) >= 0 and float(c.facts.get("area_m2") or 0.0) > 0]
  if not live:
    return None
  return max(live, key=lambda c: (_rank(c.facts["floor"]), str(c.key)))

def _name(hint):
  spec = level_spec(hint)
  return (spec[0] if spec else hint), bool(spec)

def _common(slab, how: str, role: str) -> dict:
  f = slab.facts or {}
  covered, gross = float(f.get("area_m2") or 0.0), float(f.get("gross_area_m2") or 0.0)
  out = {"derived_from": "SLAB", "slab_key": slab.key, "roof_floor": f["floor"], "roof_found_by": how, "roof_role": role,
    "covered_area_m2": round(covered, 3) if covered > 0 else None, "gross_area_m2": round(gross, 3) if gross > 0 else None, "layers": None, "slope": None, "layers_defined": False}
  if f.get("view"):
    out["view"] = f["view"]
  return out

def _deck(slab, how: str, role: str, ctx: dict, cls, finish, standing=None) -> list:
  f = slab.facts or {}
  
  covered, gross = float(f.get("area_m2") or 0.0), float(f.get("gross_area_m2") or 0.0)
  hint = f["floor"]
  name, named = _name(hint)
  area = covered if covered > 0 else gross
  if area <= 0:
    return []

  projection = round(gross - covered, 3) if (gross > 0 and covered > 0) else 0.0
  basis = "COVERED" if covered > 0 and projection >= MIN_PROJECTION_M2 else ("TABLE" if gross <= 0 else "OUTLINE")
  facts = _common(slab, how, role)
  notes = [C.note("ROOF_TREATMENT_AREA_ONLY")]
  
  if how == "TOP_OF_SHEET":
    notes.append(C.note("ROOF_TOP_FLOOR_ASSUMED", floor=name))
  if standing is not None:
    footprint = float((standing.facts or {}).get("area_m2") or 0.0)
    if 0 < footprint < area:
      area = round(area - footprint, 3)
      facts["upper_roof_footprint_m2"] = round(footprint, 3)
      notes.append(C.note("ROOF_MAIN_UNDER_UPPER_ROOF", floor=name, footprint=round(footprint, 2)))
      
  facts.update({"area_m2": round(area, 3), "area_basis": basis, "roof_part": "DECK", "projection_area_m2": projection if projection >= MIN_PROJECTION_M2 else None})
  pts = list((slab.geometry or {}).get("points") or [[0.0, 0.0]])
  suffix = "" if role == "ROOF_SLAB" else "-" + hint
  return [FD._make(cls, ctx, finish, (ITEM, hint), ITEM, f"Roof treatment · {area:.2f} m²" + (f" · {name}" if named else ""), "ROOF-TREATMENT" + suffix, pts[:1],
    {"length_mm": round(area * 1000.0, 1), "width_mm": 1000.0}, [], notes, facts, 0.6 if how in ("TOP_OF_SHEET", "BELOW_ROOF_PLAN") else 0.7)]

def _projection(slab, how: str, ctx: dict, cls, finish) -> list:
  f = slab.facts or {}
  
  covered, gross = float(f.get("area_m2") or 0.0), float(f.get("gross_area_m2") or 0.0)
  area = round(gross - covered, 3) if (gross > 0 and covered > 0) else 0.0
  if area < MIN_PROJECTION_M2:
    return []
  hint = f["floor"]
  name, named = _name(hint)
  facts = {**_common(slab, how, "PROJECTION"), "area_m2": area, "area_basis": "PROJECTION", "roof_part": "PROJECTION", "projection_area_m2": area}
  pts = list((slab.geometry or {}).get("points") or [[0.0, 0.0]])
  return [FD._make(cls, ctx, finish, (ITEM, hint, "PROJECTION"), ITEM, f"Roof treatment · projections {area:.2f} m²" + (f" · {name}" if named else ""),
    "ROOF-TREATMENT-PROJ-" + hint, pts[:1], {"length_mm": round(area * 1000.0, 1), "width_mm": 1000.0}, [],
    [C.note("ROOF_TREATMENT_AREA_ONLY"), C.note("ROOF_PROJECTION_OPTIONAL", floor=name)], facts, 0.6 if how != "ROOF_PLAN" else 0.7)]

def roof_candidates(slabs: list, ctx: dict, cls, finish) -> list:
  slab, how = roof_slab(slabs)
  if slab is None:
    return []

  out = _deck(slab, how, "ROOF_SLAB", ctx, cls, finish)
  if how == "ROOF_PLAN":
    main = main_roof_slab(slabs, slab)
    if main is not None:
      out += _deck(main, "BELOW_ROOF_PLAN", "MAIN_ROOF", ctx, cls, finish, standing=slab)
  seen: set = set()
  for c in sorted(_live(slabs), key=lambda c: (_rank(c.facts["floor"]), str(c.key))):
    if c.facts["floor"] in seen:
      continue
    seen.add(c.facts["floor"])
    out += _projection(c, how, ctx, cls, finish)
  return out
