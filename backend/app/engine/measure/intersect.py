from __future__ import annotations
from app.engine.measure.models import CalculationContext, SpatialIndex, Overlap

def find_overlaps(ctx: CalculationContext, index: SpatialIndex) -> list[Overlap]:
  params = ctx.convention_params or {}
  sliver = float(params.get("sliver_area_mm2", 1.0))
  min_z = float(params.get("min_z_overlap_mm", 0.1))
  overlaps: list[Overlap] = []
  for a, b in index.candidates:
    pa, pb = index.prisms[a], index.prisms[b]
    dz = min(pa.z1, pb.z1) - max(pa.z0, pb.z0)
    if dz < min_z:
      continue
    inter = index.polys[a].intersection(index.polys[b])
    if inter.is_empty or inter.area <= sliver:
      continue
    overlaps.append(Overlap(a=a, b=b, volume_mm3=inter.area * dz))
  return overlaps