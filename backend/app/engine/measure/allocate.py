from __future__ import annotations
from dataclasses import dataclass
from app.engine.measure.models import Overlap, SpatialIndex, CalculationContext, AllocationResult, Deduction, Solid
from shapely.ops import unary_union
from app.engine.measure.units import Unit, mm3_to_m3

EPS_Z = 0.05

def _components(ids: list, overlaps: list[Overlap]) -> list[list]:
  parent = {i: i for i in ids}

  def find(x):
    while parent[x] != x:
      parent[x] = parent[parent[x]]
      x = parent[x]
    return x

  for o in overlaps:
    ra, rb = find(o.a), find(o.b)
    if ra != rb:
      parent[max(ra, rb)] = min(ra, rb)
  groups: dict = {}
  for i in ids:
    groups.setdefault(find(i), []).append(i)
  return [g for g in groups.values() if len(g) > 1]

def _union_mm3(group: list, index: SpatialIndex, min_z: float) -> float:
  zs = sorted({z for i in group for z in (index.prisms[i].z0, index.prisms[i].z1)})
  total = 0.0
  for za, zb in zip(zs, zs[1:]):
    h = zb - za
    if h < min_z:
      continue
    active = [index.polys[i] for i in group
      if index.prisms[i].z0 <= za + EPS_Z and index.prisms[i].z1 >= zb - EPS_Z]
    if active:
      total += unary_union(active).area * h
  return total

@dataclass(frozen=True)
class CachedAllocation:
  """Result of allocating one solid in an earlier run, re-expressed with this run's solid ids."""
  deductions: tuple
  approximate: bool
  warnings: tuple
  owned_mm3: float

@dataclass(frozen=True)
class Reuse:
  """Incremental recalculation plan (Phase 9). `recompute` are allocated afresh, every other participating solid takes its
  `cached` result; only overlap components containing a `recompute` solid are conservation-checked again."""
  recompute: frozenset
  cached: dict

def _allocate_solid(sid, prism, poly, owners, index, by_id, convention, min_z):
  """Allocation of one solid against the owners that outrank it. Depends on nothing but the solid and its owners, which is
  what makes a one-hop neighbourhood the exact set to recompute when an element changes."""
  total_mm3 = poly.area * (prism.z1 - prism.z0)
  if not owners:
    return [], False, set(), total_mm3

  zs = {prism.z0, prism.z1}
  for n in owners:
    op = index.prisms[n]
    for z in (op.z0, op.z1):
      if prism.z0 + min_z < z < prism.z1 - min_z:
        zs.add(z)
  bands = sorted(zs)

  taken = {n: 0.0 for n in owners}
  for za, zb in zip(bands, bands[1:]):
    h = zb - za
    if h < min_z:
      continue
    remaining = poly
    for n in owners:
      op = index.prisms[n]
      if op.z0 <= za + EPS_Z and op.z1 >= zb - EPS_Z:
        piece = remaining.intersection(index.polys[n])
        if piece.is_empty or piece.area <= 0:
          continue
        taken[n] += piece.area * h
        remaining = remaining.difference(piece)
        if remaining.is_empty:
          break

  deductions: list[Deduction] = []
  approximate = False
  warnings: set = set()
  for n in owners:
    quantity = mm3_to_m3(taken[n]) if taken[n] > 0 else None
    if not quantity or quantity <= 0:
      continue
    loser, owner = by_id[sid], by_id[n]
    dtype, rule = convention.classify(loser.role, owner.role)
    exact = prism.exact and index.prisms[n].exact
    if not exact:
      approximate = True
    if convention.rank(loser.role) == convention.rank(owner.role):
      warnings.add("SAME_ROLE_OVERLAP")
    deductions.append(Deduction(
      from_solid_id=sid, to_solid_id=n, deduction_type=dtype, quantity=quantity,
      unit=Unit.M3.value, rule_code=rule,
      geometry={"method": "polygon_z_band" if exact else "aabb", "owner_element_id": str(owner.element_id)},
      explanation=f"{loser.role} volume shared with {owner.role}; owned by {owner.role} under {convention.code}.",
    ))
  return deductions, approximate, warnings, max(0.0, total_mm3 - sum(taken.values()))

def allocate(ctx: CalculationContext, convention, solids: list[Solid], index: SpatialIndex,
  overlaps: list[Overlap], reuse: Reuse | None = None) -> AllocationResult:
  params = ctx.convention_params or {}
  min_z = float(params.get("min_z_overlap_mm", 0.1))
  tol_rel = float(params.get("conservation_tolerance_rel", 1e-4))
  tol_abs = float(params.get("conservation_tolerance_abs_mm3", 5000.0))

  by_id = {s.id: s for s in solids}
  key = {sid: (convention.rank(by_id[sid].role), str(by_id[sid].element_id)) for sid in index.prisms}
  neighbours: dict = {}
  for o in overlaps:
    neighbours.setdefault(o.a, set()).add(o.b)
    neighbours.setdefault(o.b, set()).add(o.a)

  deductions: list[Deduction] = []
  approximate: set = set()
  warnings: dict = {}
  owned_mm3: dict = {}
  recomputed = 0

  for sid in sorted(index.prisms, key=lambda i: key[i]):
    cached = reuse.cached.get(sid) if reuse is not None and sid not in reuse.recompute else None
    if cached is not None:
      got_deductions, got_approx, got_warnings, got_owned = list(cached.deductions), cached.approximate, set(cached.warnings), cached.owned_mm3
      
    else:
      owners = sorted((n for n in neighbours.get(sid, ()) if key[n] < key[sid]), key=lambda n: key[n])
      got_deductions, got_approx, got_warnings, got_owned = _allocate_solid(
        sid, index.prisms[sid], index.polys[sid], owners, index, by_id, convention, min_z)
      recomputed += 1
    deductions.extend(got_deductions)
    if got_approx:
      approximate.add(sid)
    if got_warnings:
      warnings[sid] = got_warnings
    owned_mm3[sid] = got_owned

  failures: list[str] = []
  checked = 0
  if convention.conserves_volume:
    if reuse is None:
      scope = sorted(index.prisms, key=str)
      scope_overlaps = overlaps
    else:
      closure: set = set()
      stack = [sid for sid in reuse.recompute if sid in index.prisms]
      while stack:
        sid = stack.pop()
        if sid in closure:
          continue
        closure.add(sid)
        stack.extend(n for n in neighbours.get(sid, ()) if key[n] < key[sid] and n not in closure)
      scope = sorted(closure, key=str)
      scope_overlaps = [o for o in overlaps if o.a in closure and o.b in closure]
      
    for group in _components(scope, scope_overlaps):
      checked += 1
      owned = sum(owned_mm3.get(i, 0.0) for i in group)
      union = _union_mm3(group, index, min_z)
      if abs(owned - union) > max(tol_rel * union, tol_abs):
        failures.append(f"component of {len(group)} solids: owned {owned:.0f} mm3 != union {union:.0f} mm3")

  deductions.sort(key=lambda d: (str(d.from_solid_id), str(d.to_solid_id), d.deduction_type))
  return AllocationResult(
    deductions=deductions,
    approximate_solids=frozenset(approximate),
    unallocated_solids=index.unallocated,
    solid_warnings={k: tuple(sorted(v)) for k, v in warnings.items()},
    conservation_failures=tuple(failures),
    applied=True,
    owned_mm3=owned_mm3,
    stats={
      "convention": convention.code, "participating": len(index.prisms), "overlaps": len(overlaps),
      "approximate_solids": len(approximate), "components_checked": checked,
      "conservation_failures": len(failures),
      "conservation_scope": "model" if reuse is None else "owner_closure", "solids_recomputed": recomputed,
      "solids_reused": len(index.prisms) - recomputed,
    },
  )