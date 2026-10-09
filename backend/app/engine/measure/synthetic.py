from __future__ import annotations
from uuid import NAMESPACE_URL, UUID, uuid5
from decimal import Decimal
from app.engine.measure.models import ModelElement
from dataclasses import replace

BAY_MM = 5000.0
STOREY_MM = 3000.0
COL = 300.0
BEAM_W, BEAM_D = 230.0, 450.0
SLAB_T = 125.0
WALL_T = 230.0

def element_count(nx: int, ny: int, nz: int) -> int:
  columns = nx * ny
  beams = (nx - 1) * ny + nx * (ny - 1)
  slabs = (nx - 1) * (ny - 1)
  walls = (nx - 1) * (2 if ny > 1 else 1)
  return (columns + beams + slabs + walls) * nz

def grid_for(target: int) -> tuple[int, int, int]:
  nz = 12
  n = 2
  while element_count(n, n, nz) < target:
    n += 1
  return n, n, nz

def _id(namespace: UUID, tag: str) -> UUID:
  return uuid5(namespace, f"synthetic|{tag}")

def rect(x0, y0, x1, y1):
  return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

def make_element(namespace: UUID, tag: str, ifc_type: str, role: str, level, plan, z0: float, z1: float,
  kind: str = "EXTRUDED_PROFILE") -> ModelElement:
  xs = [p[0] for p in plan]
  ys = [p[1] for p in plan]
  depth = z1 - z0
  w, l = max(xs) - min(xs), max(ys) - min(ys)
  
  return ModelElement(
    id=_id(namespace, tag), ifc_type=ifc_type, role=role, level_id=level, geometry_kind=kind,
    profile={"kind": "POLYGON", "points_mm": [[float(x - min(xs)), float(y - min(ys))] for x, y in plan]},
    placement={"plan_mm": [[float(x), float(y)] for x, y in plan], "depth_mm": depth, "vertical": True,
      "z_max_mm": z1, "z_min_mm": z0, "origin_mm": [min(xs), min(ys), z0], "extrusion_dir": [0.0, 0.0, 1.0]},
    volume_mm3=Decimal(str(w * l * depth)),
    bbox_min_mm=(min(xs), min(ys), z0), bbox_max_mm=(max(xs), max(ys), z1),
    classification_confidence=Decimal("0.95"), normalization_status="VALID", ifc_global_id=tag)

def level_ids(namespace: UUID, nz: int, prefix: str = "b") -> list[UUID]:
  return [_id(namespace, f"{prefix}|level|{k}") for k in range(nz)]

def frame(nx: int, ny: int, nz: int, offset=(0.0, 0.0), prefix: str = "b",
  namespace: UUID = NAMESPACE_URL) -> list[ModelElement]:
  out: list[ModelElement] = []
  ox, oy = offset
  levels = level_ids(namespace, nz, prefix)
  for k in range(nz):
    z0 = k * STOREY_MM
    z1 = z0 + STOREY_MM
    lv = levels[k]
    
    for i in range(nx):
      for j in range(ny):
        cx, cy = ox + i * BAY_MM, oy + j * BAY_MM
        out.append(make_element(namespace, f"{prefix}|col|{k}|{i}|{j}", "IfcColumn", "COLUMN", lv,
          rect(cx, cy, cx + COL, cy + COL), z0, z1))
        
    for i in range(nx - 1):
      for j in range(ny):
        cx, cy = ox + i * BAY_MM + COL, oy + j * BAY_MM
        out.append(make_element(namespace, f"{prefix}|bx|{k}|{i}|{j}", "IfcBeam", "BEAM", lv,
          rect(cx, cy + (COL - BEAM_W) / 2, cx + BAY_MM - COL, cy + (COL + BEAM_W) / 2), z1 - BEAM_D, z1, "AXIS_SWEPT"))
        
    for i in range(nx):
      for j in range(ny - 1):
        cx, cy = ox + i * BAY_MM, oy + j * BAY_MM + COL
        out.append(make_element(namespace, f"{prefix}|by|{k}|{i}|{j}", "IfcBeam", "BEAM", lv,
          rect(cx + (COL - BEAM_W) / 2, cy, cx + (COL + BEAM_W) / 2, cy + BAY_MM - COL), z1 - BEAM_D, z1, "AXIS_SWEPT"))
        
    for i in range(nx - 1):
      for j in range(ny - 1):
        cx, cy = ox + i * BAY_MM, oy + j * BAY_MM
        out.append(make_element(namespace, f"{prefix}|slab|{k}|{i}|{j}", "IfcSlab", "SLAB", lv,
          rect(cx, cy, cx + BAY_MM, cy + BAY_MM), z1 - SLAB_T, z1))
        
    for i in range(nx - 1):
      for j in ((0, ny - 1) if ny > 1 else (0,)):
        cx, cy = ox + i * BAY_MM + COL, oy + j * BAY_MM
        out.append(make_element(namespace, f"{prefix}|wall|{k}|{i}|{j}", "IfcWall", "WALL_EXTERNAL", lv,
          rect(cx, cy, cx + BAY_MM - COL, cy + WALL_T), z0, z1 - BEAM_D))
  return out

def shifted(el: ModelElement, dx: float = 0.0, dy: float = 0.0) -> ModelElement:
  pl = el.placement
  plan = [[p[0] + dx, p[1] + dy] for p in pl["plan_mm"]]
  origin = [pl["origin_mm"][0] + dx, pl["origin_mm"][1] + dy, pl["origin_mm"][2]]
  return replace(el, placement={**pl, "plan_mm": plan, "origin_mm": origin},
    bbox_min_mm=(el.bbox_min_mm[0] + dx, el.bbox_min_mm[1] + dy, el.bbox_min_mm[2]),
    bbox_max_mm=(el.bbox_max_mm[0] + dx, el.bbox_max_mm[1] + dy, el.bbox_max_mm[2]))

def reissued(elements: list[ModelElement], namespace: UUID) -> list[ModelElement]:
  return [replace(e, id=uuid5(namespace, f"reissue|{e.ifc_global_id}")) for e in elements]
