from __future__ import annotations

WALL_FOUNDATION = "WALL_FOUNDATION_WORKS"
WALL_FINISHES = "WALL_FINISHES_FROM_WALLS"
RECIPES = (WALL_FOUNDATION, WALL_FINISHES)

def describe(spec: dict | None) -> str | None:
  if spec and spec.get("kind") == "DERIVED" and spec.get("recipe") in ("OPENING_AREA_FROM_MODEL", "ROOF_TREATMENT_FROM_SLABS"):
    return {"DOOR_AREA": "area of the doors: width of the footprint box times the height, from the model", "WINDOW_AREA": "area of the windows: width of the footprint box times the height, from the model",
      "ROOF_TREATMENT": "plan area of the roof slab, flat roof assumed"}.get(str(spec.get("item")), "worked out from the model")
  if not spec or spec.get("kind") != "DERIVED":
    return None
  
  recipe, item = spec.get("recipe"), spec.get("item")
  if recipe == "STEEL_ALLOWANCE":
    p = spec.get("params") or {}
    if item == "WIRE":
      pct = p.get("steel_binding_wire_pct")
      return f"binding wire at {pct:g} % of the weight of the bars of the storey, not drawn" if isinstance(pct, (int, float)) else "binding wire for the bars, not drawn"
    rate = p.get("steel_chairs_kg_per_m2")
    return f"chairs under the slab steel at {rate:g} kg per m2 of slab, not drawn" if isinstance(rate, (int, float)) else "chairs under the slab steel, not drawn"
  if recipe == "ROOF_DECK_FROM_TREATMENT":
    prm = spec.get("params") or {}
    thick, turn = prm.get("roof_coba_thickness_mm"), prm.get("roof_turnup_mm")
    printed = (spec.get("basis") or {}).get("roof_coba_thickness_mm") == "drawing"
    up = f", turned up {turn:g} mm along the roof edge" if isinstance(turn, (int, float)) else ""
    return {"MEMBRANE": f"waterproofing over the whole roof area{up}, layers not drawn",
      "COBA": (f"coba over the roof area at an average of {thick:g} mm, the fall printed on the drawing" if printed else f"coba over the roof area at an average of {thick:g} mm, layers not drawn") if isinstance(thick, (int, float)) else "coba over the roof area, layers not drawn",
      "SCREED": f"cement screed over the coba{up}, layers not drawn"}.get(str(item), "worked out from the roof treatment")
    
  if recipe == WALL_FOUNDATION:
    cls = str(spec.get("strip_class") or "").lower()
    if item == "BRICK_STEP":
      return f"steps of the brick foundation under {cls} walls, heights and offset from the QS's workbook"
    if item == "TERMITE_TRENCH":
      return "bottom of the trench under the walls, as wide as the concrete bed"
    if item == "MEMBRANE":
      return "along the top of the plinth under the walls"
    return "worked out from the walls"
  
  if recipe == WALL_FINISHES:
    return {
      "PLASTER_INSIDE": "inside faces of the walls from the plinth up, openings taken off",
      "PAINT_INSIDE": "inside faces of the walls from the plinth up, openings taken off",
      "PLASTER_OUTSIDE": "outside faces of the outer walls from the plinth up, openings taken off",
      "PAINT_OUTSIDE": "outside faces of the outer walls from the plinth up, openings taken off",
    }.get(str(item), "worked out from the walls")
  return None