from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import foundation as FD
from app.modules.drawings_boq.takeoff.extract import finishes as FN
from app.modules.drawings_boq.takeoff.extract import floor_sources as FS
from app.modules.drawings_boq.takeoff.extract import config as C
from app.engine.measure import rule_formulas as RF
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

MIN_PROJECTION_M2 = 0.05
BELOW = ("FOUNDATION", "BASEMENT")
PROJECTION_MARKER_OFFSET = 3.0

def _live(slabs: list) -> list:
  return [c for c in slabs if c.category == "SLAB" and c.status != "INVALID" and (c.facts or {}).get("floor")]

def main_roof_slab(slabs: list, upper) -> object | None:
  """The slab over the highest full floor (not the roof plan's own slab, not a basement): the roof the head room stands on."""
  live = [c for c in _live(slabs) if c is not upper and c.facts["floor"] not in ("ROOF", *BELOW) and _rank(c.facts["floor"]) >= 0 and float(c.facts.get("area_m2") or 0.0) > 0]
  return max(live, key=lambda c: (_rank(c.facts["floor"]), str(c.key))) if live else None

def terrace_pairs(slabs: list, main) -> list:
  """[(slab of floor n, slab of floor n+1)] for the floors below the main roof whose slab reaches past the floor above it by at least TERRACE_MIN_M2 and TERRACE_MIN_SHARE of itself:
  a terrace. One slab per floor (the larger). The roof of floor n is its slab less the footprint of floor n+1."""
  by_floor: dict = {}
  for c in _live(slabs):
    if _rank(c.facts["floor"]) >= 0 and float(c.facts.get("area_m2") or 0.0) > 0 and (c.facts["floor"] not in by_floor or float(c.facts["area_m2"]) > float(by_floor[c.facts["floor"]].facts["area_m2"])):
      by_floor[c.facts["floor"]] = c
  order = sorted(by_floor, key=_rank)
  out = []
  if main is None:
    return out
  top = _rank(main.facts["floor"])
  for lower, upper in zip(order, order[1:]):
    if _rank(lower) >= top:
      continue
    a, b = float(by_floor[lower].facts["area_m2"]), float(by_floor[upper].facts["area_m2"])
    if a - b >= max(C.TERRACE_MIN_M2, C.TERRACE_MIN_SHARE * a):
      out.append((by_floor[lower], by_floor[upper]))
  return out

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

ROOF_AREA_DEFAULTS = {"include_projection": False}   

def _deck(slab, how: str, role: str, ctx: dict, cls, finish, spec_facts: dict | None, standing_m2: float | None = None, many: bool = False) -> list:
  """The roof over a slab: its covered area, less the footprint of what stands on it (the head room on the main roof, the floor above on a terrace). The part of the slab that reaches past the walls is a
  line of its own (_projection). many: the roof plan has several roof slabs (a split-level roof), each its own roof."""
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
  footprint = 0.0
  if standing_m2 is not None:
    footprint = float(standing_m2)
    if 0 < footprint < area:
      facts["upper_roof_footprint_m2"] = round(footprint, 3)
      notes.append(C.note("ROOF_TERRACE_BELOW_UPPER" if role == "TERRACE_ROOF" else "ROOF_MAIN_UNDER_UPPER_ROOF", floor=name, footprint=round(footprint, 2)))
    else:
      footprint = 0.0
  got, applied = RF.run("roof_area", ROOF_AREA_DEFAULTS, {"covered_m2": area, "projection_m2": projection, "standing_m2": footprint})
  area = got["area_m2"]
  facts["formula"] = {k: applied[k] for k in ("formula", "source", "rule_id", "version")}
  facts.update({"area_m2": round(area, 3), "area_basis": basis, "roof_part": "DECK", "projection_area_m2": projection if projection >= MIN_PROJECTION_M2 else None})
  
  notes.extend(_printed_layers(facts, spec_facts))
  notes.extend(_edge(f, facts))
  pts = list((slab.geometry or {}).get("points") or [[0.0, 0.0]])
  suffix = "" if role == "ROOF_SLAB" and not many else "-" + (str(slab.key) if many else hint)
  return [FD._make(cls, ctx, finish, (ITEM, hint, slab.key) if many else (ITEM, hint), ITEM, f"Roof treatment · {area:.2f} m²" + (f" · {name}" if named else ""), "ROOF-TREATMENT" + suffix, pts[:1],
    {"length_mm": round(area * 1000.0, 1), "width_mm": 1000.0}, [], notes, facts, 0.6 if how in ("TOP_OF_SHEET", "BELOW_ROOF_PLAN") or role == "TERRACE_ROOF" else 0.7)]

def _projection_area(slab) -> float:
  f = slab.facts or {}
  covered, gross = float(f.get("area_m2") or 0.0), float(f.get("gross_area_m2") or 0.0)
  area = round(gross - covered, 3) if (gross > 0 and covered > 0) else 0.0
  return area if area >= MIN_PROJECTION_M2 else 0.0

def _projection(slab, how: str, ctx: dict, cls, finish) -> list:
  """The part of the slab that reaches past the walls (chajja, sunshade, projection strip): the top of it is roof treatment. Its marker is the slab's marker moved PROJECTION_MARKER_OFFSET along the
  sheet, because confirming refuses two measurements of one work item at the same place (DUPLICATE_MEASUREMENT) and the deck of the same slab stands at the slab's marker."""
  area = _projection_area(slab)
  if not area:
    return []
  hint = slab.facts["floor"]
  name, named = _name(hint)
  
  facts = {**_common(slab, how, "PROJECTION"), "area_m2": area, "area_basis": "PROJECTION", "roof_part": "PROJECTION", "projection_area_m2": area}
  pts = [[p[0] + PROJECTION_MARKER_OFFSET, p[1]] for p in list((slab.geometry or {}).get("points") or [[0.0, 0.0]])[:1]]
  return [FD._make(cls, ctx, finish, (ITEM, hint, "PROJECTION"), ITEM, f"Roof treatment · projections {area:.2f} m²" + (f" · {name}" if named else ""),
    "ROOF-TREATMENT-PROJ-" + hint, pts[:1], {"length_mm": round(area * 1000.0, 1), "width_mm": 1000.0}, [],
    [C.note("ROOF_TREATMENT_AREA_ONLY"), C.note("ROOF_PROJECTION_OPTIONAL", floor=name)], facts, 0.6 if how != "ROOF_PLAN" else 0.7)]

def _soffit(slab, how: str, ctx: dict, cls, finish) -> list:
  """The underside of the same projection: plastered and painted with the ceiling of that floor."""
  area = _projection_area(slab)
  if not area:
    return []
  hint = slab.facts["floor"]
  name, named = _name(hint)
  pts = list((slab.geometry or {}).get("points") or [[0.0, 0.0]])
  out = []
  for item, text, tag in ((FN.CEILING_PLASTER, "Ceiling plaster", "CEILING-PLASTER-PROJ-"), (FN.CEILING_PAINT, "Ceiling paint", "CEILING-PAINT-PROJ-")):
    facts = {**_common(slab, how, "PROJECTION"), "area_m2": area, "area_basis": "PROJECTION", "roof_part": "SOFFIT", "projection_area_m2": area}
    out.append(FN._make(cls, ctx, finish, (item, hint, "SOFFIT"), item, f"{text} · soffit of projections {area:.2f} m²" + (f" · {name}" if named else ""), tag + hint, pts[:1],
      {"length_mm": round(area * 1000.0, 1), "width_mm": 1000.0}, [], [C.note("CEILING_PROJECTION_SOFFIT", floor=name)], facts, 0.6))
  return out

def roof_candidates(slabs: list, ctx: dict, cls, finish, spec_facts: dict | None = None) -> list:
  slab, how = roof_slab(slabs)
  if slab is None:
    return []
  roofs = [slab] + [c for c in _live(slabs) if c is not slab and c.facts["floor"] == "ROOF"] if how == "ROOF_PLAN" else [slab]
  out = []
  
  for r in roofs:
    out += _deck(r, how, "ROOF_SLAB", ctx, cls, finish, spec_facts, many=len(roofs) > 1)
  main = None
  if how == "ROOF_PLAN":
    main = main_roof_slab(slabs, slab)
    if main is not None:
      out += _deck(main, "BELOW_ROOF_PLAN", "MAIN_ROOF", ctx, cls, finish, spec_facts, standing_m2=sum(float(r.facts.get("area_m2") or 0.0) for r in roofs))
    for lower, upper in terrace_pairs(slabs, main):
      out += _deck(lower, "BELOW_ROOF_PLAN", "TERRACE_ROOF", ctx, cls, finish, spec_facts, standing_m2=float(upper.facts.get("area_m2") or 0.0))
  seen: set = set()
  
  for c in sorted(_live(slabs), key=lambda c: (_rank(c.facts["floor"]), str(c.key))):
    if c.facts["floor"] in seen:
      continue
    seen.add(c.facts["floor"])
    out += _projection(c, how, ctx, cls, finish)
    out += _soffit(c, how, ctx, cls, finish)
  return out

def from_outline(level_hint: str | None, outline: dict | None, walls: list, ctx: dict, cls, finish) -> list:
  area = float((outline or {}).get("area_m2") or 0.0)
  if str(level_hint or "").upper() != "ROOF" or area <= 0.0:
    return []
  
  pts = [p for w in walls if (w.geometry or {}).get("points") for p in w.geometry["points"][:1]]
  facts = {"derived_from": "OUTLINE", "roof_floor": "ROOF", "roof_found_by": "OUTLINE", "roof_role": "ROOF_SLAB", "covered_area_m2": None, "gross_area_m2": None, "layers": None, "slope": None,
    "layers_defined": False, "area_m2": round(area, 3), "area_basis": "OUTLINE_ASSUMED", "roof_part": "DECK", "projection_area_m2": None, "outline_perimeter_m": (outline or {}).get("perimeter_m"), "edge_m": None, "edge_basis": None}
  notes = [C.note("ROOF_TREATMENT_AREA_ONLY"), C.note("ROOF_FROM_OUTLINE", area_m2=round(area, 2), perimeter_m=(outline or {}).get("perimeter_m"))]
  cand = FD._make(cls, ctx, finish, (ITEM, "ROOF"), ITEM, f"Roof treatment · {area:.2f} m² · from the outline of the walls", "ROOF-TREATMENT", [FD._centre(pts)] if pts else [[0.0, 0.0]],
    {"length_mm": round(area * 1000.0, 1), "width_mm": 1000.0}, [], notes, facts, 0.5)
  cand.facts = {**(cand.facts or {}), FS.SET_ASIDE: {"by": FS.ASSUMED_BY, "page_no": None}}
  return [cand]

