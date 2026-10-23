from __future__ import annotations
from shapely.validation import make_valid
from shapely.errors import GEOSException
import shapely

PLAIN, REPAIRED, SNAPPED = "PLAIN", "REPAIRED", "SNAPPED"
GRID = 1e-3      

def _repair(g):
  return g if g.is_valid else make_valid(g)

def safe_op(op: str, a, b):
  try:
    return getattr(a, op)(b), PLAIN
  except GEOSException:
    pass
  try:
    return getattr(_repair(a), op)(_repair(b)), REPAIRED
  except GEOSException:
    pass
  try:
    return getattr(shapely, op)(_repair(a), _repair(b), grid_size=GRID), SNAPPED
  except (GEOSException, ValueError):
    return None, None

def safe_difference(a, b):
  return safe_op("difference", a, b)

def safe_intersection(a, b):
  return safe_op("intersection", a, b)
