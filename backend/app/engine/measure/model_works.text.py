from __future__ import annotations

WALL_FOUNDATION = "WALL_FOUNDATION_WORKS"
WALL_FINISHES = "WALL_FINISHES_FROM_WALLS"
RECIPES = (WALL_FOUNDATION, WALL_FINISHES)

def describe(spec: dict | None) -> str | None:
  if not spec or spec.get("kind") != "DERIVED":
    return None

  recipe, item = spec.get("recipe"), spec.get("item")
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
