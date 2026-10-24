from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import foundation as FD
from app.modules.drawings_boq.takeoff.extract import floor_sources as FS
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.extract import spec_facts as SF
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

def _printed_layers(facts: dict, spec_facts: dict | None) -> list:
  """Put the roof layers the specification block prints on the roof item: the layers of the one roof heading when there is one, every roof heading's layers when there are several."""
  sets = SF.roof_sets(spec_facts)
  if not sets:
    return []
  notes = [C.note("ROOF_LAYERS_FROM_SPEC", headings=[s["heading"] for s in sets], chosen=sets[0]["heading"] if len(sets) == 1 else None)]
  if len(sets) == 1:
    facts.update(layers=sets[0]["layers"], layers_defined=True, layers_heading=sets[0]["heading"], layers_waterproof=sets[0]["waterproof"])
    fall = sets[0].get("fall")
    if fall:
      facts["slope"] = {"min_mm": fall["min_mm"], "max_mm": fall["max_mm"], "avg_mm": fall["avg_mm"], "text": fall.get("text"), "pages": fall.get("pages"), "heading": sets[0]["heading"]}
      notes.append(C.note("ROOF_FALL_FROM_SPEC", heading=sets[0]["heading"], min_mm=fall["min_mm"], max_mm=fall["max_mm"], avg_mm=fall["avg_mm"]))
  else:
    facts["layer_sets"] = sets
  return notes

EDGE_AREA_TOL = 0.08

def _edge(slab_facts: dict, facts: dict) -> list:
  """The length of the roof edge, from the one rectangle the area table prints for the roof (its length and width), when that rectangle has the area of the slab."""
  dims = slab_facts.get("dims_mm")
  area = float(slab_facts.get("area_m2") or 0.0)
  if isinstance(dims, (list, tuple)) and len(dims) == 2 and all(isinstance(d, (int, float)) and d > 0 for d in dims) and area > 0:
    drawn = float(dims[0]) * float(dims[1]) / 1.0e6
    if abs(drawn - area) / area <= EDGE_AREA_TOL:
      edge = round(2.0 * (float(dims[0]) + float(dims[1])) / 1000.0, 3)
      facts.update(edge_m=edge, edge_basis="PRINTED_SIZE", edge_dims_mm=[float(dims[0]), float(dims[1])])
      return [C.note("ROOF_EDGE_FROM_SIZE", edge_m=edge, dims_mm=[float(dims[0]), float(dims[1])])]
  facts.update(edge_m=None, edge_basis=None)
  return [C.note("ROOF_EDGE_NOT_KNOWN")]

def roof_candidates(slabs: list, ctx: dict, cls, finish, spec_facts: dict | None = None) -> list:
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
  notes.extend(_printed_layers(facts, spec_facts))
  notes.extend(_edge(f, facts))
  label = f"Roof treatment · {area:.2f} m²" + (f" · {spec[0]}" if spec else "")
  pts = list((slab.geometry or {}).get("points") or [[0.0, 0.0]])
  return [FD._make(cls, ctx, finish, (ITEM, hint), ITEM, label, "ROOF-TREATMENT", pts[:1], {"length_mm": round(area * 1000.0, 1), "width_mm": 1000.0}, [], notes, facts,
    0.6 if how == "TOP_OF_SHEET" else 0.7)]
