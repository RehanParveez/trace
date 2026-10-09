from __future__ import annotations
from app.engine.measure.models import ModelElement, Prism, CalculationContext, Solid, SpatialIndex
from collections.abc import Mapping
import numpy as np
import shapely
from shapely.geometry import Polygon
from shapely import STRtree, make_valid
from app.engine.measure.geometry import snap_mm, extrusion_volume_mm3

PRISM_VOLUME_TOLERANCE = 0.005
BROAD_PHASE_CHUNK = 4096

def _prism_from_element(el: ModelElement) -> Prism | None:
  found = prism_and_polygon(el)
  return found[0] if found else None

def prism_and_polygon(el: ModelElement):
  pl = el.placement or {}
  plan, zmin, zmax = pl.get("plan_mm"), pl.get("z_min_mm"), pl.get("z_max_mm")
  if plan and len(plan) >= 3 and zmin is not None and zmax is not None:
    try:
      pts = tuple((snap_mm(float(p[0])), snap_mm(float(p[1]))) for p in plan)
      lo, hi = snap_mm(float(zmin)), snap_mm(float(zmax))
    except (TypeError, ValueError, IndexError):
      pts, lo, hi = None, 0.0, 0.0
    if pts and hi > lo:
      prism = Prism(plan=pts, z0=lo, z1=hi, exact=True)
      poly = _polygon(prism)
      ref = extrusion_volume_mm3(el.profile, pl)
      if ref is None and el.volume_mm3 is not None:
        ref = float(el.volume_mm3)
      if ref is None or abs(poly.area * (hi - lo) - ref) > max(PRISM_VOLUME_TOLERANCE * ref, 5000.0):
        return None
      return prism, poly
    
  bmin, bmax = el.bbox_min_mm, el.bbox_max_mm
  if bmin and bmax:
    x0, y0, za = (snap_mm(float(v)) for v in bmin)
    x1, y1, zb = (snap_mm(float(v)) for v in bmax)
    if x1 > x0 and y1 > y0 and zb > za:
      prism = Prism(plan=((x0, y0), (x1, y0), (x1, y1), (x0, y1)), z0=za, z1=zb, exact=False)
      return prism, _polygon(prism)
  return None

def _polygon(prism: Prism):
  poly = Polygon(prism.plan)
  return poly if poly.is_valid else make_valid(poly)

def broad_phase(ids: list, prisms: dict, polys: dict, min_z: float, chunk: int = BROAD_PHASE_CHUNK) -> list:
  """STR-tree over plan bounding boxes, queried in chunks; pairs that cannot share `min_z` of height are dropped
  at once (the exact test in intersect.find_overlaps applies the same rule, so the overlaps found do not change,
  only the number of pairs that are ever materialised)."""
  n = len(ids)
  if n < 2:
    return []
  bounds = np.array([polys[i].bounds for i in ids], dtype=float)
  z0 = np.array([prisms[i].z0 for i in ids], dtype=float)
  z1 = np.array([prisms[i].z1 for i in ids], dtype=float)
  boxes = shapely.box(bounds[:, 0], bounds[:, 1], bounds[:, 2], bounds[:, 3])
  tree = STRtree(boxes)
  keep: list = []
  for start in range(0, n, chunk):
    stop = min(start + chunk, n)
    left, right = tree.query(boxes[start:stop], predicate="intersects")
    left = left + start
    mask = left < right
    left, right = left[mask], right[mask]
    if left.size:
      dz = np.minimum(z1[left], z1[right]) - np.maximum(z0[left], z0[right])
      ok = dz >= min_z
      left, right = left[ok], right[ok]
    if left.size:
      keep.append(left.astype(np.int64) * n + right.astype(np.int64))
  if not keep:
    return []
  flat = np.unique(np.concatenate(keep))
  return [(ids[int(v // n)], ids[int(v % n)]) for v in flat]

class BaselineMismatch(Exception):
  """The stored baseline no longer describes the model (geometry that took part in the baseline cannot be rebuilt)."""

class _LazyView(Mapping):
  def __init__(self, owner, which: int):
    self._owner, self._which = owner, which
  def __getitem__(self, sid):
    return self._owner.get(sid)[self._which]
  def __iter__(self):
    return iter(self._owner.ids)
  def __len__(self):
    return len(self._owner.ids)
  def __contains__(self, sid):
    return sid in self._owner.idset

class LazyGeometry:
  """Prisms and plan polygons of the solids that take part in allocation, built the first time they are asked for.

  An incremental run only ever touches the changed solids, their neighbours and the owners of those, so the thousands of
  untouched solids never get a polygon at all. `prisms` and `polys` behave like the plain dicts a full run uses."""
  def __init__(self, ids, builder):
    self.ids = list(ids)
    self.idset = frozenset(self.ids)
    self._builder = builder
    self._cache: dict = {}
    self.prisms = _LazyView(self, 0)
    self.polys = _LazyView(self, 1)

  def get(self, sid):
    got = self._cache.get(sid)
    if got is None:
      got = self._builder(sid)
      if got is None:
        raise BaselineMismatch(f"geometry of solid {sid} could not be rebuilt")
      self._cache[sid] = got
    return got

  def put(self, sid, pair) -> None:
    self._cache[sid] = pair

  def built(self) -> int:
    return len(self._cache)

def build_spatial_index_incremental(ctx: CalculationContext, convention, solids: list[Solid],
  elements: list[ModelElement], key_of_element: dict, hash_of_element: dict, baseline_elements: dict):
  """Spatial index for an incremental run. Solids whose element is unchanged since the baseline are taken from it
  (participating or not, with the bounds that were stored) and get no geometry until something asks for it; changed and
  new solids are built eagerly. Returns (index, bounds) where `bounds` maps every participating solid id to
  (xmin, ymin, xmax, ymax, z0, z1) for the broad phase."""
  by_element = {e.id: e for e in elements}
  participating: list = []
  unallocated: set = set()
  bounds: dict = {}
  eager: dict = {}
  dirty: set = set()
  clean_ids: set = set()
  for s in sorted(solids, key=lambda s: str(s.element_id)):
    if s.gross_volume_m3 is None:
      continue
    if convention.rank(s.role) is None:
      unallocated.add(s.id)
      continue
    key = key_of_element[s.element_id]
    stored = baseline_elements.get(key)
    if stored is not None and stored.alloc_hash == hash_of_element[s.element_id]:
      if stored.participating:
        participating.append(s.id)
        bounds[s.id] = stored.bounds
        clean_ids.add(s.id)
      else:
        unallocated.add(s.id)
      continue
    found = prism_and_polygon(by_element[s.element_id]) if s.element_id in by_element else None
    if found is None:
      unallocated.add(s.id)
      continue
    participating.append(s.id)
    eager[s.id] = found
    dirty.add(s.id)
    bounds[s.id] = (*found[1].bounds, found[0].z0, found[0].z1)

  element_of_solid = {s.id: s.element_id for s in solids}

  def builder(sid):
    return prism_and_polygon(by_element[element_of_solid[sid]])

  geo = LazyGeometry(sorted(participating, key=str), builder)
  for sid, pair in eager.items():
    geo.put(sid, pair)
  min_z = float((ctx.convention_params or {}).get("min_z_overlap_mm", 0.1))
  candidates = broad_phase_touching(geo.ids, bounds, dirty, min_z)
  index = SpatialIndex(prisms=geo.prisms, polys=geo.polys, candidates=candidates, unallocated=frozenset(unallocated))
  return index, bounds, frozenset(dirty), geo

def broad_phase_touching(ids: list, bounds: dict, dirty: set, min_z: float, chunk: int = BROAD_PHASE_CHUNK) -> list:
  n = len(ids)
  if n < 2 or not dirty:
    return []
  arr = np.array([bounds[i] for i in ids], dtype=float)
  boxes = shapely.box(arr[:, 0], arr[:, 1], arr[:, 2], arr[:, 3])
  z0, z1 = arr[:, 4], arr[:, 5]
  tree = STRtree(boxes)
  position = {sid: i for i, sid in enumerate(ids)}
  query_idx = np.array(sorted(position[d] for d in dirty), dtype=np.int64)
  keep: list = []
  
  for start in range(0, len(query_idx), chunk):
    q = query_idx[start:start + chunk]
    left, right = tree.query(boxes[q], predicate="intersects")
    left = q[left]
    mask = left != right
    left, right = left[mask], right[mask]
    if left.size:
      dz = np.minimum(z1[left], z1[right]) - np.maximum(z0[left], z0[right])
      ok = dz >= min_z
      left, right = left[ok], right[ok]
    if left.size:
      lo, hi = np.minimum(left, right), np.maximum(left, right)
      keep.append(lo.astype(np.int64) * n + hi.astype(np.int64))
      
  if not keep:
    return []
  flat = np.unique(np.concatenate(keep))
  return [(ids[int(v // n)], ids[int(v % n)]) for v in flat]

def build_spatial_index(ctx: CalculationContext, convention, solids: list[Solid],
   elements: list[ModelElement]) -> SpatialIndex:
  by_element = {e.id: e for e in elements}
  prisms: dict = {}
  polys: dict = {}
  unallocated: set = set()
  for s in sorted(solids, key=lambda s: str(s.element_id)):
    if s.gross_volume_m3 is None:
      continue
    if convention.rank(s.role) is None:
      unallocated.add(s.id)
      continue
    el = by_element.get(s.element_id)
    found = prism_and_polygon(el) if el is not None else None
    if found is None:
      unallocated.add(s.id)
      continue
    prisms[s.id], polys[s.id] = found

  ids = sorted(prisms, key=str)
  min_z = float((ctx.convention_params or {}).get("min_z_overlap_mm", 0.1))
  candidates = broad_phase(ids, prisms, polys, min_z)
  return SpatialIndex(prisms=prisms, polys=polys, candidates=candidates, unallocated=frozenset(unallocated))
