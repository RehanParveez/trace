from __future__ import annotations
from decimal import Decimal

COLUMN_MIN_ZONE_MM = Decimal("450")
COLUMN_HEIGHT_PART = Decimal("6")
BEAM_DEPTHS = Decimal("2")
FAMILIES = ("BEAM", "COLUMN")
RULE_WORDS = {"COLUMN": "largest of a sixth of the height, the larger side and 450 mm", "BEAM": "twice the depth of the beam"}

def default_dense_ring(category: str, length: Decimal, width: Decimal, depth: Decimal, steel: dict, dense_spacing_mm: Decimal) -> tuple:
  ring = steel.get("ring") if isinstance(steel, dict) else None
  if category not in FAMILIES or not ring:
    return steel, None
  if ring.get("dense_spacing_mm") is not None:
    return steel, {"applied": False, "reason": "PRINTED"}

  spacing = Decimal(str(ring["spacing_mm"]))
  dense = min(dense_spacing_mm, spacing)
  
  if dense >= spacing:
    return steel, {"applied": False, "reason": "ALREADY_CLOSE"}
  if category == "COLUMN":
    height = depth
    zone = max(height / COLUMN_HEIGHT_PART, max(length, width), COLUMN_MIN_ZONE_MM)
    run = height
  else:
    zone = BEAM_DEPTHS * depth
    run = length
  if zone <= 0 or run <= 0 or 2 * zone >= run:
    return steel, {"applied": False, "reason": "MEMBER_TOO_SHORT"}
  zone = zone.quantize(Decimal("0.1"))
  return {**steel, "ring": {**ring, "dense_spacing_mm": float(dense), "dense_zone_mm": float(zone)}}, {
    "applied": True, "spacing_mm": float(spacing), "dense_spacing_mm": float(dense), "zone_mm": float(zone), "rule": RULE_WORDS[category]}
