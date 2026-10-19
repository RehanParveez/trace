from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import foundation as FD
from app.modules.drawings_boq.takeoff.extract import floor_sources as FS
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.levels import level_spec

ITEM = FD.ROOF_TREATMENT

def _rank(floor) -> int:
  return FS.ORDER.index(floor) if floor in FS.ORDER else -1

def roof_slab(slabs: list) -> tuple:
  """(slab, how): the slab taken as the roof, and "ROOF_PLAN" or "TOP_OF_SHEET"; (None, None) when the sheet does not show a roof."""
  live = [c for c in slabs if c.category == "SLAB" and c.status != "INVALID" and (c.facts or {}).get("floor")]
  roofs = [c for c in live if c.facts["floor"] == "ROOF"]
  if roofs:
    return roofs[0], "ROOF_PLAN"
  floors = {c.facts["floor"] for c in live}
  if len(floors) >= 2:
    top = max(live, key=lambda c: (_rank(c.facts["floor"]), str(c.key)))
    if _rank(top.facts["floor"]) >= 0:
      return top, "TOP_OF_SHEET"
  return None, None

def roof_candidates(slabs: list, ctx: dict, cls, finish) -> list:
  slab, how = roof_slab(slabs)
  if slab is None:
    return []

  f = slab.facts or {}
  covered = float(f.get("area_m2") or 0.0)
  gross = float(f.get("gross_area_m2") or 0.0)
  area = gross if gross > 0 else covered
  if area <= 0:
    return []

  basis = "OUTLINE" if gross > 0 else "TABLE"
  hint = f["floor"]
  spec = level_spec(hint)
  facts = {"derived_from": "SLAB", "slab_key": slab.key, "roof_floor": hint, "roof_found_by": how, "area_m2": round(area, 3), "area_basis": basis,
    "covered_area_m2": round(covered, 3) if covered > 0 else None, "gross_area_m2": round(gross, 3) if gross > 0 else None, "layers": None, "slope": None,
    "layers_defined": False}
  if f.get("view"):
    facts["view"] = f["view"]
  notes = [C.note("ROOF_TREATMENT_AREA_ONLY")] + ([C.note("ROOF_TOP_FLOOR_ASSUMED", floor=spec[0] if spec else hint)] if how == "TOP_OF_SHEET" else [])
  label = f"Roof treatment · {area:.2f} m²" + (f" · {spec[0]}" if spec else "")
  pts = list((slab.geometry or {}).get("points") or [[0.0, 0.0]])
  return [FD._make(cls, ctx, finish, (ITEM, hint), ITEM, label, "ROOF-TREATMENT", pts[:1], {"length_mm": round(area * 1000.0, 1), "width_mm": 1000.0}, [], notes, facts,
    0.6 if how == "TOP_OF_SHEET" else 0.7)]
