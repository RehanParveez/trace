from __future__ import annotations
import hashlib
from app.engine.measure.models import ModelElement, SpatialIndex, CalculationContext, Deduction, Overlap, Solid
from app.engine.measure.fingerprint import _element_key
import json
from dataclasses import dataclass, field
from decimal import Decimal
from app.engine.measure.intersect import find_overlaps
from app.engine.measure.allocate import CachedAllocation, Reuse
from app.engine.measure.spatial import build_spatial_index, build_spatial_index_incremental

ALLOCATION_VERSION = 1

def element_hash(el: ModelElement) -> str:
  key = _element_key(el)
  key.pop("id", None)
  key.pop("l", None)
  return hashlib.sha256(json.dumps(key, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()

def stable_keys(elements: list[ModelElement]) -> dict:
  seen: dict = {}
  for e in elements:
    if e.ifc_global_id:
      seen[e.ifc_global_id] = seen.get(e.ifc_global_id, 0) + 1
  out = {}
  for e in elements:
    out[e.id] = f"g:{e.ifc_global_id}" if e.ifc_global_id and seen[e.ifc_global_id] == 1 else f"i:{e.id}"
  return out

def alloc_signature(engine_version: str, convention_code: str | None, convention_params: dict | None) -> str:
  blob = json.dumps({"engine": engine_version, "convention": convention_code, "params": convention_params or {},
    "allocation": ALLOCATION_VERSION}, sort_keys=True, separators=(",", ":"), default=str)
  return hashlib.sha256(blob.encode()).hexdigest()

@dataclass(frozen=True)
class StoredElement:
  key: str
  element_id: object
  solid_id: object
  alloc_hash: str
  participating: bool
  approximate: bool
  warnings: tuple
  owned_mm3: float
  bounds: tuple | None = None  

@dataclass(frozen=True)
class StoredDeduction:
  to_key: str | None
  deduction_type: str
  quantity: Decimal
  unit: str
  rule_code: str
  geometry: dict
  explanation: str

@dataclass
class Baseline:
  run_id: object
  signature: str
  elements: dict = field(default_factory=dict)     
  edges: dict = field(default_factory=dict)         
  deductions: dict = field(default_factory=dict)    

@dataclass(frozen=True)
class ChangeSet:
  changed: frozenset      
  gone: frozenset         
  added: int
  modified: int
  removed: int
  eligible: int

def diff_elements(eligible: dict, baseline: Baseline) -> ChangeSet:
  changed = set()
  added = modified = 0
  for k, h in eligible.items():
    stored = baseline.elements.get(k)
    if stored is None:
      changed.add(k)
      added += 1
    elif stored.alloc_hash != h:
      changed.add(k)
      modified += 1
  gone = {k for k in baseline.elements if k not in eligible}
  return ChangeSet(frozenset(changed), frozenset(gone), added, modified, len(gone), len(eligible))

def change_ratio(change: ChangeSet) -> float:
  return (len(change.changed) + len(change.gone)) / max(change.eligible, 1)

def relations_incremental(ctx: CalculationContext, index: SpatialIndex, solid_of_key: dict, dirty: frozenset,
  baseline: Baseline) -> list[Overlap]:
  known = {}
  for pair, volume in baseline.edges.items():
    ka, kb = tuple(pair)
    sa, sb = solid_of_key.get(ka), solid_of_key.get(kb)
    if sa is not None and sb is not None and sa not in dirty and sb not in dirty:
      known[frozenset((sa, sb))] = volume
  return find_overlaps(ctx, index, known=known, dirty=dirty)

def _remap_deduction(d: StoredDeduction, sid_from, solid_of_key: dict, element_of_solid: dict):
  if d.to_key is None:
    to_sid = None
  else:
    to_sid = solid_of_key.get(d.to_key)
    if to_sid is None:
      return None
  geometry = dict(d.geometry)
  if to_sid is not None and "owner_element_id" in geometry:
    geometry["owner_element_id"] = str(element_of_solid[to_sid])
  return Deduction(from_solid_id=sid_from, to_solid_id=to_sid, deduction_type=d.deduction_type, quantity=d.quantity,
    unit=d.unit, rule_code=d.rule_code, geometry=geometry, explanation=d.explanation)

def build_reuse(index: SpatialIndex, overlaps: list[Overlap], change: ChangeSet, baseline: Baseline,
  key_of_solid: dict, solid_of_key: dict, element_of_solid: dict, rank_of_solid: dict) -> tuple[Reuse, dict]:
  new_nb: dict = {}
  for o in overlaps:
    ka, kb = key_of_solid[o.a], key_of_solid[o.b]
    new_nb.setdefault(ka, set()).add(kb)
    new_nb.setdefault(kb, set()).add(ka)
  base_nb: dict = {}
  for pair in baseline.edges:
    ka, kb = tuple(pair)
    base_nb.setdefault(ka, set()).add(kb)
    base_nb.setdefault(kb, set()).add(ka)

  present = set(solid_of_key)
  affected = set(change.changed)
  for k in change.changed:
    affected |= new_nb.get(k, set())
    affected |= base_nb.get(k, set())
  for k in change.gone:
    affected |= base_nb.get(k, set())
  affected &= present
  by_neighbourhood = len(affected - change.changed)

  cached: dict = {}
  order_flips = remap_misses = 0
  for k in present - affected:
    stored = baseline.elements[k]
    sid = solid_of_key[k]
    same_id = stored.element_id == element_of_solid[sid]
    
    flipped = False
    for n in base_nb.get(k, ()):
      sn = solid_of_key.get(n)
      if sn is None:
        flipped = True
        break
      if same_id and baseline.elements[n].element_id == element_of_solid[sn]:
        continue 
      
      old_before = (rank_of_solid[sn], str(baseline.elements[n].element_id)) < (rank_of_solid[sid], str(stored.element_id))
      new_before = (rank_of_solid[sn], str(element_of_solid[sn])) < (rank_of_solid[sid], str(element_of_solid[sid]))
      if old_before != new_before:
        flipped = True
        break
    if flipped:
      affected.add(k)
      order_flips += 1
      continue
    remapped = []
    ok = True
    for d in baseline.deductions.get(k, ()):
      r = _remap_deduction(d, sid, solid_of_key, element_of_solid)
      if r is None:
        ok = False
        break
      remapped.append(r)
    if not ok:
      affected.add(k)
      remap_misses += 1
      continue
    cached[sid] = CachedAllocation(tuple(remapped), stored.approximate, stored.warnings, stored.owned_mm3)

  recompute = frozenset(solid_of_key[k] for k in affected)
  stats = {
    "changed": len(change.changed), "added": change.added, "modified": change.modified, "removed": change.removed,
    "affected_by_neighbourhood": by_neighbourhood, "order_flips": order_flips, "remap_misses": remap_misses,
    "recompute": len(recompute), "reused": len(cached), "participating": len(present),
  }
  return Reuse(recompute=recompute, cached=cached), stats

def equivalent(full, incr) -> list[str]:
  problems = []
  def sig(d):
    return (str(d.from_solid_id), str(d.to_solid_id), d.deduction_type, str(d.quantity), d.rule_code,
      json.dumps(d.geometry, sort_keys=True), d.explanation)
  if [sig(d) for d in full.deductions] != [sig(d) for d in incr.deductions]:
    problems.append("deductions differ")
  if full.approximate_solids != incr.approximate_solids:
    problems.append("approximate_solids differ")
  if full.solid_warnings != incr.solid_warnings:
    problems.append("solid_warnings differ")
  if full.unallocated_solids != incr.unallocated_solids:
    problems.append("unallocated_solids differ")
  if full.owned_mm3 != incr.owned_mm3:
    problems.append("owned volumes differ")
  if bool(full.conservation_failures) != bool(incr.conservation_failures):
    problems.append("conservation outcome differs")
  return problems

class AllocationPlanner:

  def __init__(self, ctx: CalculationContext, convention, solids: list[Solid], accepted: list[ModelElement],
    baseline: Baseline | None = None, max_change_ratio: float = 0.5, hashes: dict | None = None):
    self.ctx, self.convention, self.solids, self.accepted = ctx, convention, solids, accepted
    self.baseline, self.max_change_ratio = baseline, max_change_ratio
    self.keys = stable_keys(accepted)
    self.hashes = hashes if hashes is not None else {e.id: element_hash(e) for e in accepted}
    self.signature = alloc_signature(ctx.engine_version, ctx.convention_code, ctx.convention_params)
    self.mode = "FULL"
    self.fallback_reason: str | None = None
    self.change: ChangeSet | None = None
    self.reuse: Reuse | None = None
    self.reuse_stats: dict = {}
    self.index = self.overlaps = self.alloc = None
    self.dirty: frozenset = frozenset()
    self._bounds: dict | None = None
    self._geo = None

  def spatial(self) -> SpatialIndex:
    by_solid = {s.id: s for s in self.solids}
    eligible_solids = [s for s in self.solids if s.gross_volume_m3 is not None and self.convention.rank(s.role) is not None]
    eligible = {self.keys[s.element_id]: self.hashes[s.element_id] for s in eligible_solids}
    self.eligible_solid_of_key = {self.keys[s.element_id]: s.id for s in eligible_solids}
    if self.baseline is None:
      self.fallback_reason = "NO_BASELINE"
    elif self.baseline.signature != self.signature:
      self.fallback_reason = "ALLOCATION_INPUTS_CHANGED"
    else:
      self.change = diff_elements(eligible, self.baseline)
      if change_ratio(self.change) > self.max_change_ratio:
        self.fallback_reason = "TOO_MANY_CHANGES"
      else:
        self.mode = "INCREMENTAL"

    if self.mode == "INCREMENTAL":
      key_of_element = self.keys
      self.index, self._bounds, self.dirty, self._geo = build_spatial_index_incremental(
        self.ctx, self.convention, self.solids, self.accepted, key_of_element, self.hashes, self.baseline.elements)
    else:
      self.index = build_spatial_index(self.ctx, self.convention, self.solids, self.accepted)
    self.element_of_solid = {sid: by_solid[sid].element_id for sid in self.index.prisms}
    self.key_of_solid = {sid: self.keys[eid] for sid, eid in self.element_of_solid.items()}
    self.solid_of_key = {k: sid for sid, k in self.key_of_solid.items()}
    self.hashes_by_key = {self.keys[eid]: self.hashes[eid] for eid in self.element_of_solid.values()}
    self.rank_of_solid = {sid: self.convention.rank(by_solid[sid].role) for sid in self.index.prisms}
    return self.index

  def relations(self) -> list[Overlap]:
    if self.mode == "INCREMENTAL":
      self.overlaps = relations_incremental(self.ctx, self.index, self.solid_of_key, self.dirty, self.baseline)
    else:
      self.overlaps = find_overlaps(self.ctx, self.index)
    return self.overlaps

  def allocate(self):
    from app.engine.measure.allocate import allocate as _allocate
    if self.mode == "INCREMENTAL":
      self.reuse, self.reuse_stats = build_reuse(self.index, self.overlaps, self.change, self.baseline,
        self.key_of_solid, self.solid_of_key, self.element_of_solid, self.rank_of_solid)
    self.alloc = _allocate(self.ctx, self.convention, self.solids, self.index, self.overlaps, self.reuse)
    return self.alloc

  def state(self):
    elements = []
    index = self.index
    for k in sorted(self.eligible_solid_of_key):
      sid = self.eligible_solid_of_key[k]
      eid = self._element_by_solid(sid)
      if sid in index.prisms:
        if self._bounds is not None:
          bounds = tuple(self._bounds[sid])
        else:
          bounds = (*index.polys[sid].bounds, index.prisms[sid].z0, index.prisms[sid].z1)
        elements.append(StoredElement(
          key=k, element_id=eid, solid_id=sid, alloc_hash=self.hashes[eid], participating=True,
          approximate=sid in self.alloc.approximate_solids, warnings=tuple(self.alloc.solid_warnings.get(sid, ())),
          owned_mm3=self.alloc.owned_mm3.get(sid, 0.0), bounds=bounds))
      else:
        elements.append(StoredElement(
          key=k, element_id=eid, solid_id=sid, alloc_hash=self.hashes[eid], participating=False,
          approximate=False, warnings=(), owned_mm3=0.0, bounds=None))
        
    edges = []
    for o in self.overlaps:
      ka, kb = self.key_of_solid[o.a], self.key_of_solid[o.b]
      ea, eb = self.element_of_solid[o.a], self.element_of_solid[o.b]
      if ka > kb:
        ka, kb, ea, eb = kb, ka, eb, ea
      edges.append((ka, kb, ea, eb, o.volume_mm3))
    return elements, edges

  def _element_by_solid(self, sid):
    if not hasattr(self, "_elem_of_all"):
      self._elem_of_all = {s.id: s.element_id for s in self.solids}
    return self._elem_of_all[sid]

  def summary(self) -> dict:
    out = {"mode": self.mode, **({"fallback_reason": self.fallback_reason} if self.fallback_reason else {})}
    if self.mode == "INCREMENTAL":
      out.update(self.reuse_stats)
      out["geometry_built"] = self._geo.built() if self._geo is not None else 0
    return out

def baseline_from_run(run_id, signature: str, stored: list, edges: list, deductions: list) -> Baseline:
  base = Baseline(run_id=run_id, signature=signature)
  key_of_solid = {}
  for s in stored:
    base.elements[s.key] = s
    key_of_solid[s.solid_id] = s.key
  for ka, kb, _ea, _eb, volume in edges:
    base.edges[frozenset((ka, kb))] = volume
  for d in deductions:
    from_key = key_of_solid.get(d.from_solid_id)
    if from_key is None:
      continue
    to_key = key_of_solid.get(d.to_solid_id) if d.to_solid_id is not None else None
    base.deductions.setdefault(from_key, []).append(StoredDeduction(
      to_key=to_key, deduction_type=d.deduction_type, quantity=d.quantity, unit=d.unit, rule_code=d.rule_code,
      geometry=dict(d.geometry or {}), explanation=d.explanation))
  return base
