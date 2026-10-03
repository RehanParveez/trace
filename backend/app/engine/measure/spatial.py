from __future__ import annotations
from app.engine.measure.models import ModelElement, Prism, CalculationContext, Solid, SpatialIndex
from shapely.geometry import Polygon
from shapely import STRtree, box, make_valid
from app.engine.measure.geometry import snap_mm

def _prism_from_element(el: ModelElement) -> Prism | None:
  pl = el.placement or {}
  plan, zmin, zmax = pl.get("plan_mm"), pl.get("z_min_mm"), pl.get("z_max_mm")
  if plan and len(plan) >= 3 and zmin is not None and zmax is not None:
    try:
      pts = tuple((snap_mm(float(p[0])), snap_mm(float(p[1]))) for p in plan)
      lo, hi = snap_mm(float(zmin)), snap_mm(float(zmax))
    except (TypeError, ValueError, IndexError):
      pts, lo, hi = None, 0.0, 0.0
    if pts and hi > lo:
      return Prism(plan=pts, z0=lo, z1=hi, exact=True)
  bmin, bmax = el.bbox_min_mm, el.bbox_max_mm
  if bmin and bmax:
    x0, y0, za = (snap_mm(float(v)) for v in bmin)
    x1, y1, zb = (snap_mm(float(v)) for v in bmax)
    if x1 > x0 and y1 > y0 and zb > za:
      return Prism(plan=((x0, y0), (x1, y0), (x1, y1), (x0, y1)), z0=za, z1=zb, exact=False)
  return None

def _polygon(prism: Prism):
  poly = Polygon(prism.plan)
  return poly if poly.is_valid else make_valid(poly)

def build_spatial_index(ctx: CalculationContext, convention, solids: list[Solid],
   elements: list[ModelElement]) -> SpatialIndex:
  by_element = {e.id: e for e in elements}
  prisms: dict = {}
  polys: dict = {}
  unallocated: set = set()
  for s in sorted(solids, key=lambda s: str(s.element_id)):
    if convention.rank(s.role) is None or s.gross_volume_m3 is None:
      continue
    el = by_element.get(s.element_id)
    prism = _prism_from_element(el) if el is not None else None
    if prism is None:
      unallocated.add(s.id)
      continue
    prisms[s.id] = prism
    polys[s.id] = _polygon(prism)

  ids = sorted(prisms, key=str)
  candidates: list = []
  if len(ids) > 1:
    boxes = [box(*polys[i].bounds) for i in ids]
    tree = STRtree(boxes)
    left, right = tree.query(boxes, predicate="intersects")
    pairs = sorted({(int(a), int(b)) for a, b in zip(left, right) if a < b})
    candidates = [(ids[a], ids[b]) for a, b in pairs]
  return SpatialIndex(prisms=prisms, polys=polys, candidates=candidates, unallocated=frozenset(unallocated))