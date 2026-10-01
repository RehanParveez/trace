from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
import re
import math
import ifcopenshell
import numpy as np
import ifcopenshell.util.element
import ifcopenshell.util.placement
import ifcopenshell.util.unit
from functools import lru_cache
from app.modules.drawings_boq.ifc_types import (COUNT_ROLES, DEFAULT_DISCIPLINE, DEFAULT_MESH_FALLBACK_LIMIT, DEFAULT_QUANTITY_KIND_ORDER, DISCIPLINE_BY_ROLE, EXCLUDED_IFC_TYPES, LINEAR_ROLES,
  LOW_CLASSIFICATION_CONFIDENCE, MESH_FALLBACK_ROLES, NAME_KEYWORD_ROLES, NO_LEGACY_BOQ_ROLES, PREDEFINED_TYPE_ROLE_OVERRIDES, QUANTITY_KIND_ORDER_BY_ROLE, QUANTITY_PROPS_BY_KIND,
  REQUIRED_DIMENSIONS_BY_ROLE, ROLE_BY_IFC_TYPE, SLAB_ROLES, SUPERTYPE_FALLBACK_TYPES, WALL_ROLES,
)

MATERIAL_TEXT_MAX = 300
_KEYWORD_PATTERNS = [
  (re.compile(rf"(?<![a-z]){re.escape(keyword)}(?:s|es)?(?![a-z])"), role)
  for keyword, role in NAME_KEYWORD_ROLES
]
_MM3_PER_M3 = 1_000_000_000.0
_MM2_PER_M2 = 1_000_000.0
 
@dataclass
class ReadLevel:
  global_id: str
  name: str
  elevation_mm: Decimal | None
  sequence: int
 
@dataclass
class ReadElement:
  step_id: int
  global_id: str | None
  ifc_type: str
  name: str | None
  raw_material_text: str
  is_generic_fallback: bool
  discipline: str
  structural_role: str
  classification_source: str
  classification_confidence: Decimal
  level_global_id: str | None = None
  unit: str | None = None
  quantity: Decimal = Decimal("0")
  quantity_source: str = "NONE"
  length_mm: Decimal | None = None
  width_mm: Decimal | None = None
  height_mm: Decimal | None = None
  thickness_mm: Decimal | None = None
  area_mm2: Decimal | None = None
  volume_mm3: Decimal | None = None
  elevation_base_mm: Decimal | None = None
  elevation_top_mm: Decimal | None = None
  bbox_min_mm: tuple[Decimal, Decimal, Decimal] | None = None
  bbox_max_mm: tuple[Decimal, Decimal, Decimal] | None = None
  geometry_kind: str = "UNSUPPORTED"
  profile: dict | None = None
  placement: dict | None = None
  properties: dict = field(default_factory=dict)
  status: str = "VALID"
  issues: list[dict] = field(default_factory=list)
 
@dataclass
class IfcReadResult:
  schema: str
  length_unit_scale: float  
  levels: list[ReadLevel]
  elements: list[ReadElement]
  model_issues: list[dict]
  stats: dict
 
@dataclass
class _Scales:
  length_m: float
  area_m2: float
  volume_m3: float
  ambiguous: bool
 
  @property
  def mm_per_unit(self) -> float:
    return self.length_m * 1000.0
 
@dataclass
class _Geometry:
  kind: str = "UNSUPPORTED"
  profile: dict | None = None
  placement: dict | None = None
  bbox_min: np.ndarray | None = None 
  bbox_max: np.ndarray | None = None  
  dims: dict = field(default_factory=dict)  
  profile_area_mm2: float | None = None
  depth_mm: float | None = None
  issues: list[dict] = field(default_factory=list)
 
def humanize_ifc_type(ifc_type: str) -> str:
  """'IfcWallStandardCase' -> 'Wall Standard Case'."""
  stripped = ifc_type[3:] if ifc_type.startswith("Ifc") else ifc_type
  return re.sub(r"(?<!^)(?=[A-Z])", " ", stripped).strip()
 
def _issue(code: str, severity: str, message: str) -> dict:
  return {"code": code, "severity": severity, "message": message}
 
def _num(value) -> float | None:
  if value is None or isinstance(value, bool):
    return None
  try:
    number = float(value)
  except (TypeError, ValueError):
    return None
  return number if math.isfinite(number) else None
 
def _dec(value: float | None, places: int = 3) -> Decimal | None:
  if value is None or not math.isfinite(value):
    return None
  return Decimal(str(round(value, places)))
 
def _json_safe(value):
  if isinstance(value, dict):
    return {str(k): _json_safe(v) for k, v in value.items()}
  if isinstance(value, (list, tuple)):
    return [_json_safe(v) for v in value]
  if isinstance(value, str):
    return value.replace("\x00", "")
  if isinstance(value, (bool, int)) or value is None:
    return value
  if isinstance(value, float):
    return value if math.isfinite(value) else None
  if isinstance(value, ifcopenshell.entity_instance):
    return {"ifc_entity": value.is_a(), "step_id": value.id()}
  return str(value)
 
def _clean(text) -> str | None:
  if text is None:
    return None
  cleaned = str(text).strip()
  return cleaned or None
 
def _resolve_scales(model) -> _Scales:
  projects = model.by_type("IfcProject")
  units_ctx = projects[0].UnitsInContext if projects else None
  assigned = {
    u.UnitType for u in (units_ctx.Units if units_ctx else []) if hasattr(u, "UnitType")
  }
 
  def _scale(unit_type: str) -> float | None:
    if unit_type not in assigned:
      return None
    try:
      value = float(ifcopenshell.util.unit.calculate_unit_scale(model, unit_type))
    except Exception:
      return None
    return value if value > 0 else None
 
  length = _scale("LENGTHUNIT")
  ambiguous = length is None
  length = length or 1.0
  area = _scale("AREAUNIT") or length**2
  volume = _scale("VOLUMEUNIT") or length**3
  return _Scales(length_m=length, area_m2=area, volume_m3=volume, ambiguous=ambiguous)
 
def _read_levels(model, scales: _Scales) -> list[ReadLevel]:
  raw: list[tuple[float | None, str, str]] = []
  for storey in model.by_type("IfcBuildingStorey"):
    elevation = _num(getattr(storey, "Elevation", None))
    if elevation is None and storey.ObjectPlacement is not None:
      try:
        matrix = ifcopenshell.util.placement.get_local_placement(storey.ObjectPlacement)
        elevation = float(matrix[2][3])
      except Exception:
        elevation = None
    elevation_mm = elevation * scales.mm_per_unit if elevation is not None else None
    raw.append((elevation_mm, _clean(storey.Name) or "Level", storey.GlobalId))
  raw.sort(key=lambda r: (r[0] if r[0] is not None else math.inf, r[1], r[2]))
  return [
    ReadLevel(global_id=gid, name=name, elevation_mm=_dec(elev), sequence=idx)
    for idx, (elev, name, gid) in enumerate(raw)
  ]
 
def _storey_of(element) -> str | None:
  try:
    container = ifcopenshell.util.element.get_container(element)
    hops = 0
    while container is not None and not container.is_a("IfcBuildingStorey") and hops < 5:
      parent = ifcopenshell.util.element.get_aggregate(container)
      container = parent or ifcopenshell.util.element.get_container(container)
      hops += 1
  except Exception:
    return None
  if container is not None and container.is_a("IfcBuildingStorey"):
    return container.GlobalId
  return None
 
def _level_by_elevation(levels: list[ReadLevel], base_mm: float | None) -> str | None:
  if base_mm is None:
    return None
  chosen = None
  for level in levels:
    if level.elevation_mm is None:
      continue
    if float(level.elevation_mm) <= base_mm + 500.0:
      chosen = level.global_id
  return chosen
 
def _material_names(material) -> list[str]:
  names: list[str] = []
  if material is None:
    return names
  if material.is_a("IfcMaterial"):
    name = _clean(material.Name)
    return [name] if name else []
  if material.is_a("IfcMaterialLayerSetUsage"):
    return _material_names(material.ForLayerSet)
  if material.is_a("IfcMaterialProfileSetUsage"):
    return _material_names(material.ForProfileSet)
  if material.is_a("IfcMaterialLayerSet"):
    for layer in material.MaterialLayers or []:
      names += _material_names(layer.Material)
    return names
  if material.is_a("IfcMaterialProfileSet"):
    for profile in material.MaterialProfiles or []:
      names += _material_names(profile.Material)
    return names
  if material.is_a("IfcMaterialConstituentSet"):
    for constituent in material.MaterialConstituents or []:
      names += _material_names(constituent.Material)
    return names
  if material.is_a("IfcMaterialList"):
    for item in material.Materials or []:
      names += _material_names(item)
    return names
  name = _clean(getattr(material, "Name", None))
  return [name] if name else []
 
def _material_text(element) -> str | None:
  try:
    material = ifcopenshell.util.element.get_material(element)
    names = _material_names(material)
    set_name = None
    if material is not None and material.is_a("IfcMaterialLayerSetUsage"):
      set_name = _clean(getattr(material.ForLayerSet, "LayerSetName", None))
    elif material is not None and material.is_a("IfcMaterialLayerSet"):
      set_name = _clean(material.LayerSetName)
  except Exception:
    return None
  if set_name:
    return set_name[:MATERIAL_TEXT_MAX]
  if not names:
    return None
  unique = list(dict.fromkeys(names))
  return " / ".join(unique)[:MATERIAL_TEXT_MAX]
 
@lru_cache(maxsize=None)
def _type_chain(schema_id: str, ifc_type: str) -> tuple[str, ...]:
  """('IfcWallStandardCase', 'IfcWall', 'IfcBuildingElement', 'IfcElement', ...)."""
  try:
    entity = ifcopenshell.ifcopenshell_wrapper.schema_by_name(schema_id).declaration_by_name(ifc_type).as_entity()
  except Exception:
    return (ifc_type,)
  chain: list[str] = []
  while entity is not None:
    chain.append(entity.name())
    entity = entity.supertype()
  return tuple(chain)
 
def _classify(element, psets: dict, schema_id: str) -> tuple[str, str, float]:
  """Returns (role, source, confidence). Never fails: every IfcElement ends at IfcElement."""
  chain = _type_chain(schema_id, element.is_a())
  matched = next((name for name in chain if name in ROLE_BY_IFC_TYPE), None)
  role = ROLE_BY_IFC_TYPE[matched] if matched else "UNKNOWN"
 
  if role != "UNKNOWN":
    predefined = _clean(getattr(element, "PredefinedType", None))
    if predefined:
      for name in chain:
        override = PREDEFINED_TYPE_ROLE_OVERRIDES.get((name, predefined))
        if override:
          return override, "PREDEFINED_TYPE", 0.98
    if role == "WALL":
      is_external = (psets.get("Pset_WallCommon") or {}).get("IsExternal")
      if is_external is True:
        return "WALL_EXTERNAL", "PSET", 0.95
      if is_external is False:
        return "WALL_INTERNAL", "PSET", 0.95
    if matched in SUPERTYPE_FALLBACK_TYPES:
      return role, "IFC_SUPERTYPE", 0.7
    return role, "IFC_TYPE", 0.95
 
  raw = " ".join(
    str(v) for v in (getattr(element, "Name", None), getattr(element, "ObjectType", None)) if v
  ).lower()
  haystack = " " + re.sub(r"[\s_\-:.,/]+", " ", raw) + " "
  for pattern, keyword_role in _KEYWORD_PATTERNS:
    if pattern.search(haystack):
      return keyword_role, "NAME_HEURISTIC", 0.4
  return "UNKNOWN", "NONE", 0.0
 
def _axis2d(placement) -> tuple[float, float, float, float]:
  if placement is None:
    return 0.0, 0.0, 1.0, 0.0
  loc = placement.Location.Coordinates if placement.Location else (0.0, 0.0)
  x0, y0 = float(loc[0]), float(loc[1])
  ref = placement.RefDirection.DirectionRatios if getattr(placement, "RefDirection", None) else (1.0, 0.0)
  rx, ry = float(ref[0]), float(ref[1])
  norm = math.hypot(rx, ry) or 1.0
  return x0, y0, rx / norm, ry / norm
 
def _apply2d(points, x0, y0, rx, ry):
  return [(x0 + x * rx - y * ry, y0 + x * ry + y * rx) for x, y in points]
 
def _shoelace(points) -> float:
  area = 0.0
  for i in range(len(points)):
    x1, y1 = points[i]
    x2, y2 = points[(i + 1) % len(points)]
    area += x1 * y2 - x2 * y1
  return abs(area) / 2.0
 
def _curve_points(curve) -> list[tuple[float, float]] | None:
  if curve is None:
    return None
  if curve.is_a("IfcPolyline"):
    pts = [(float(p.Coordinates[0]), float(p.Coordinates[1])) for p in curve.Points]
  elif curve.is_a("IfcIndexedPolyCurve"):
    coords = curve.Points.CoordList
    segments = curve.Segments
    if segments:
      if any(seg.is_a("IfcArcIndex") for seg in segments):
        return None
      order: list[int] = []
      for seg in segments:
        for idx in seg.wrappedValue:
          if not order or order[-1] != idx:
            order.append(idx)
      pts = [(float(coords[i - 1][0]), float(coords[i - 1][1])) for i in order]
    else:
      pts = [(float(c[0]), float(c[1])) for c in coords]
  else:
    return None
  if len(pts) > 1 and pts[0] == pts[-1]:
    pts = pts[:-1]
  return pts if len(pts) >= 3 else None
 
def _profile_points(profile):
  """Returns (points_in_file_units, meta_in_file_units, area_file_units2) or None."""
  kind = profile.is_a()
  if kind == "IfcRectangleProfileDef":
    dx, dy = float(profile.XDim), float(profile.YDim)
    pts = [(-dx / 2, -dy / 2), (dx / 2, -dy / 2), (dx / 2, dy / 2), (-dx / 2, dy / 2)]
    pts = _apply2d(pts, *_axis2d(profile.Position))
    return pts, {"kind": "RECT", "x_dim": dx, "y_dim": dy}, dx * dy
  if kind == "IfcCircleProfileDef":
    r = float(profile.Radius)
    pts = [(r * math.cos(a * math.pi / 8), r * math.sin(a * math.pi / 8)) for a in range(16)]
    pts = _apply2d(pts, *_axis2d(profile.Position))
    return pts, {"kind": "CIRCLE", "radius": r}, math.pi * r * r
  if kind == "IfcArbitraryClosedProfileDef":
    pts = _curve_points(profile.OuterCurve)
    if pts is None:
      return None
    return pts, {"kind": "POLYGON", "points": [[round(x, 6), round(y, 6)] for x, y in pts[:500]]}, _shoelace(pts)
  return None
 
def _body_items(element):
  representation = getattr(element, "Representation", None)
  if representation is None:
    return None
  for rep in representation.Representations or []:
    if rep.RepresentationIdentifier == "Body":
      return list(rep.Items or [])
  return None
 
def _unwrap_boolean(item):
  clipped = False
  while item is not None and item.is_a("IfcBooleanResult"):
    item = item.FirstOperand
    clipped = True
  return item, clipped
 
def _closest_dim(px: float, py: float, target: float) -> tuple[float, float]:
  """Returns (dimension closest to target, the other dimension)."""
  if abs(px - target) <= abs(py - target):
    return px, py
  return py, px
 
def _dims_from_extrusion(role: str, px: float, py: float, depth: float, vertical: bool, zext: float) -> dict:
  long_, short = max(px, py), min(px, py)
  if role in WALL_ROLES:
    if vertical:
      return {"length": long_, "thickness": short, "height": depth}
    height, length = _closest_dim(px, py, zext)
    return {"length": length, "thickness": depth, "height": height}
  if role in SLAB_ROLES:
    return {"length": long_, "width": short, "thickness": depth}
  if role in LINEAR_ROLES:
    if vertical:
      return {"length": depth, "width": short, "height": long_}
    height, width = _closest_dim(px, py, zext)
    return {"length": depth, "width": width, "height": height}
  if vertical:
    return {"length": long_, "width": short, "height": depth}
  height, width = _closest_dim(px, py, zext)
  return {"length": depth, "width": width, "height": height}
 
def _extruded_geometry(element, role: str, scales: _Scales) -> _Geometry | None:
  items = _body_items(element)
  if not items or len(items) != 1:
    return None
  solid, clipped = _unwrap_boolean(items[0])
  if solid is None or solid.is_a() != "IfcExtrudedAreaSolid":
    return None
  parsed = _profile_points(solid.SweptArea)
  if parsed is None:
    return None
  points, meta, area_file = parsed
 
  mm = scales.mm_per_unit
  if element.ObjectPlacement is not None:
    placement_matrix = ifcopenshell.util.placement.get_local_placement(element.ObjectPlacement)
  else:
    placement_matrix = np.eye(4)
  solid_matrix = (
    ifcopenshell.util.placement.get_axis2placement(solid.Position) if solid.Position is not None else np.eye(4)
  )
  matrix = placement_matrix @ solid_matrix
 
  ratios = np.array(solid.ExtrudedDirection.DirectionRatios[:3] + (0.0,) * (3 - len(solid.ExtrudedDirection.DirectionRatios)), dtype=float)
  norm = np.linalg.norm(ratios)
  if norm == 0:
    return None
  direction_local = ratios / norm
  depth_file = float(solid.Depth)
 
  base_local = np.array([[x, y, 0.0, 1.0] for x, y in points]).T
  top_local = base_local.copy()
  top_local[:3, :] += (direction_local * depth_file).reshape(3, 1)
  base_world = (matrix @ base_local)[:3, :].T * mm
  top_world = (matrix @ top_local)[:3, :].T * mm
  all_world = np.vstack([base_world, top_world])
 
  direction_world = matrix[:3, :3] @ direction_local
  direction_world = direction_world / (np.linalg.norm(direction_world) or 1.0)
  vertical = abs(float(direction_world[2])) > 0.9
 
  xs = [p[0] for p in points]
  ys = [p[1] for p in points]
  px, py = (max(xs) - min(xs)) * mm, (max(ys) - min(ys)) * mm
  depth_mm = depth_file * mm
  zext = float(base_world[:, 2].max() - base_world[:, 2].min())
 
  geometry = _Geometry()
  linear_horizontal = role in LINEAR_ROLES and not vertical
  geometry.kind = "AXIS_SWEPT" if linear_horizontal else "EXTRUDED_PROFILE"
  geometry.bbox_min = all_world.min(axis=0)
  geometry.bbox_max = all_world.max(axis=0)
  geometry.dims = _dims_from_extrusion(role, px, py, depth_mm, vertical, zext)
  geometry.profile_area_mm2 = area_file * mm * mm
  geometry.depth_mm = depth_mm
  geometry.profile = {
    **{k: (round(v * mm, 3) if isinstance(v, float) else v) for k, v in meta.items() if k != "points"},
    **(
      {"points_mm": [[round(x * mm, 3), round(y * mm, 3)] for x, y in points[:500]]}
      if meta["kind"] == "POLYGON"
      else {}
    ),
  }
  origin = (matrix @ np.array([0.0, 0.0, 0.0, 1.0]))[:3] * mm
  geometry.placement = {
    "origin_mm": [round(float(v), 3) for v in origin],
    "extrusion_dir": [round(float(v), 6) for v in direction_world],
    "depth_mm": round(depth_mm, 3),
    "vertical": vertical,
  }
  if clipped:
    geometry.issues.append(_issue("GEOMETRY_CLIPPED", "info", "Solid has a boolean clipping; dimensions are those of the unclipped solid."))
  return geometry
 
_MESH_SETTINGS = None
 
def _mesh_settings():
  global _MESH_SETTINGS
  if _MESH_SETTINGS is None:
    import ifcopenshell.geom
 
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    _MESH_SETTINGS = settings
  return _MESH_SETTINGS
 
 
def _mesh_bbox_geometry(element, role: str) -> _Geometry | None:
  try:
    import ifcopenshell.geom
 
    shape = ifcopenshell.geom.create_shape(_mesh_settings(), element)
    verts = np.asarray(shape.geometry.verts, dtype=float).reshape(-1, 3)
  except Exception:
    return None
  if verts.size == 0:
    return None
  verts_mm = verts * 1000.0 
  geometry = _Geometry(kind="BOX_ONLY")
  geometry.bbox_min = verts_mm.min(axis=0)
  geometry.bbox_max = verts_mm.max(axis=0)
  dx, dy, dz = (geometry.bbox_max - geometry.bbox_min).tolist()
  long_, short = max(dx, dy), min(dx, dy)
  if role in WALL_ROLES:
    geometry.dims = {"length": long_, "thickness": short, "height": dz}
  elif role in SLAB_ROLES:
    geometry.dims = {"length": long_, "width": short, "thickness": dz}
  else:
    geometry.dims = {"length": long_, "width": short, "height": dz}
  geometry.issues.append(_issue("BOX_ONLY_GEOMETRY", "info", "Dimensions come from the axis-aligned bounding box of the mesh; treat as approximate."))
  return geometry
 
def _flatten_qtos(qtos: dict) -> dict:
  flat: dict = {}
  for values in qtos.values():
    for key, value in values.items():
      if key != "id" and value is not None:
        flat.setdefault(key, value)
  return flat
 
def _qto_quantity(kind: str, flat: dict, scales: _Scales) -> tuple[Decimal, str] | None:
  scale, unit = {
    "volume": (scales.volume_m3, "m3"),
    "area": (scales.area_m2, "m2"),
    "length": (scales.length_m, "m"),
  }[kind]
  for prop in QUANTITY_PROPS_BY_KIND[kind]:
    value = _num(flat.get(prop))
    if value is not None and value > 0:
      return Decimal(str(round(value * scale, 4))), unit
  return None
 
def _dims_from_qto(role: str, element, flat: dict, scales: _Scales) -> dict:
  mm = scales.mm_per_unit
  dims: dict = {}
 
  def _length(name: str) -> float | None:
    value = _num(flat.get(name))
    return value * mm if value is not None and value > 0 else None
 
  if role in WALL_ROLES:
    dims = {"length": _length("Length"), "height": _length("Height"), "thickness": _length("Width")}
  elif role in SLAB_ROLES:
    thickness = _length("Depth")
    if thickness is None:
      volume = _num(flat.get("NetVolume")) or _num(flat.get("GrossVolume"))
      area = _num(flat.get("GrossArea")) or _num(flat.get("NetArea")) or _num(flat.get("GrossFootprintArea"))
      if volume and area:
        thickness = (volume * scales.volume_m3) / (area * scales.area_m2) * 1000.0
    dims = {"length": _length("Length"), "width": _length("Width"), "thickness": thickness}
  elif role == "COLUMN":
    dims = {"height": _length("Length")}
  elif role in LINEAR_ROLES:
    dims = {"length": _length("Length")}
  elif role in ("DOOR", "WINDOW"):
    width = _num(getattr(element, "OverallWidth", None))
    height = _num(getattr(element, "OverallHeight", None))
    dims = {"width": width * mm if width else None, "height": height * mm if height else None}
  return {k: v for k, v in dims.items() if v is not None}
 
def _normalise_element(
  element,
  scales: _Scales,
  levels: list[ReadLevel],
  mesh_budget: list[int],
  schema_id: str,
) -> ReadElement:
  psets = ifcopenshell.util.element.get_psets(element, psets_only=True) or {}
  qtos = ifcopenshell.util.element.get_psets(element, qtos_only=True) or {}
  flat_qto = _flatten_qtos(qtos)
 
  role, class_source, class_conf = _classify(element, psets, schema_id)
  material = _material_text(element)
  ifc_type = element.is_a()
  issues: list[dict] = []
 
  geometry: _Geometry | None = None
  if role not in COUNT_ROLES and getattr(element, "Representation", None) is not None:
    try:
      geometry = _extruded_geometry(element, role, scales)
    except Exception:
      geometry = None
    if geometry is None and role in MESH_FALLBACK_ROLES and mesh_budget[0] > 0:
      mesh_budget[0] -= 1
      geometry = _mesh_bbox_geometry(element, role)
  if geometry is None:
    geometry = _Geometry(kind="UNSUPPORTED")
 
  dims = {k: v for k, v in geometry.dims.items() if v is not None and v > 0}
  qto_dims = _dims_from_qto(role, element, flat_qto, scales)
  for key, value in qto_dims.items():
    dims.setdefault(key, value)
  if geometry.kind == "UNSUPPORTED" and dims:
    geometry.kind = "QTO_ONLY"
  issues += geometry.issues
 
  order = QUANTITY_KIND_ORDER_BY_ROLE.get(role, DEFAULT_QUANTITY_KIND_ORDER)
  quantity, unit, source = Decimal("0"), None, "NONE"
  for kind in order:
    if kind == "count":
      quantity, unit, source = Decimal("1"), "nos", "COUNT"
      break
    found = _qto_quantity(kind, flat_qto, scales)
    if found:
      quantity, unit = found
      source = "QTO"
      break
  if source == "NONE":
    for kind in order:
      if kind == "volume" and geometry.profile_area_mm2 and geometry.depth_mm:
        cubic_mm = geometry.profile_area_mm2 * geometry.depth_mm
        quantity, unit, source = Decimal(str(round(cubic_mm / _MM3_PER_M3, 4))), "m3", "GEOMETRY"
        break
      if kind == "length" and dims.get("length"):
        quantity, unit, source = Decimal(str(round(dims["length"] / 1000.0, 4))), "m", "GEOMETRY"
        break
    if source == "GEOMETRY":
      issues.append(_issue("QUANTITY_FROM_GEOMETRY", "info", "No usable Qto quantity; quantity derived from extruded geometry."))
 
  volume_m3 = _qto_quantity("volume", flat_qto, scales)
  area_m2 = _qto_quantity("area", flat_qto, scales)
  volume_mm3 = float(volume_m3[0]) * _MM3_PER_M3 if volume_m3 else (
    geometry.profile_area_mm2 * geometry.depth_mm if geometry.profile_area_mm2 and geometry.depth_mm else None
  )
  area_mm2 = float(area_m2[0]) * _MM2_PER_M2 if area_m2 else geometry.profile_area_mm2
 
  base_mm = float(geometry.bbox_min[2]) if geometry.bbox_min is not None else None
  top_mm = float(geometry.bbox_max[2]) if geometry.bbox_max is not None else None
  level_gid = _storey_of(element)
  if level_gid is None and levels:
    level_gid = _level_by_elevation(levels, base_mm)
    if level_gid:
      issues.append(_issue("LEVEL_INFERRED", "info", "No storey container; level inferred from element elevation."))
  if level_gid is None and levels:
    issues.append(_issue("NO_LEVEL", "info", "Element could not be assigned to a level."))
 
  if source == "NONE" and role in NO_LEGACY_BOQ_ROLES:
    issues.append(_issue("STORED_ONLY", "info", f"Role {role} is stored for later phases; no BOQ quantity is taken from it here."))
  elif source == "NONE":
    issues.append(_issue("NO_QUANTITY", "error", "No usable quantity from Qto sets or geometry."))
  for required in REQUIRED_DIMENSIONS_BY_ROLE.get(role, ()):
    if required not in dims:
      issues.append(_issue("MISSING_DIMENSION", "error", f"Missing required dimension '{required}' for role {role}."))
  if geometry.kind == "UNSUPPORTED" and role in MESH_FALLBACK_ROLES:
    issues.append(_issue("UNSUPPORTED_GEOMETRY", "warning", "No extrudable or meshable body geometry found."))
  if class_source == "IFC_SUPERTYPE":
    issues.append(_issue("ROLE_FALLBACK", "info", f"Only the broad family is known ({role}); no specific class mapping."))
  if role == "UNKNOWN":
    issues.append(_issue("UNCLASSIFIED_ELEMENT", "warning", "Element role could not be determined."))
  elif class_conf < LOW_CLASSIFICATION_CONFIDENCE:
    issues.append(_issue("LOW_CONFIDENCE_CLASSIFICATION", "warning", f"Role {role} inferred from {class_source} with low confidence."))
  is_generic = material is None
  if is_generic and role not in COUNT_ROLES and role not in NO_LEGACY_BOQ_ROLES:
    issues.append(_issue("MISSING_MATERIAL", "warning", "No material assigned; generic type name used."))
 
  severities = {i["severity"] for i in issues}
  status = "INVALID" if "error" in severities else "WARNING" if "warning" in severities else "VALID"
 
  properties = _json_safe({**psets, **qtos})
  properties["is_generic_fallback"] = is_generic
  properties["_ifc"] = {
    "predefined_type": _clean(getattr(element, "PredefinedType", None)),
    "object_type": _clean(getattr(element, "ObjectType", None)),
  }
 
  bbox_min = bbox_max = None
  if geometry.bbox_min is not None and geometry.bbox_max is not None:
    bbox_min = tuple(_dec(float(v)) for v in geometry.bbox_min)
    bbox_max = tuple(_dec(float(v)) for v in geometry.bbox_max)
 
  return ReadElement(
    step_id=element.id(),
    global_id=_clean(getattr(element, "GlobalId", None)),
    ifc_type=ifc_type,
    name=_clean(getattr(element, "Name", None)),
    raw_material_text=material or humanize_ifc_type(ifc_type),
    is_generic_fallback=is_generic,
    discipline=DISCIPLINE_BY_ROLE.get(role, DEFAULT_DISCIPLINE),
    structural_role=role,
    classification_source=class_source,
    classification_confidence=Decimal(str(class_conf)),
    level_global_id=level_gid,
    unit=unit,
    quantity=quantity,
    quantity_source=source,
    length_mm=_dec(dims.get("length")),
    width_mm=_dec(dims.get("width")),
    height_mm=_dec(dims.get("height")),
    thickness_mm=_dec(dims.get("thickness")),
    area_mm2=_dec(area_mm2),
    volume_mm3=_dec(volume_mm3),
    elevation_base_mm=_dec(base_mm),
    elevation_top_mm=_dec(top_mm),
    bbox_min_mm=bbox_min,
    bbox_max_mm=bbox_max,
    geometry_kind=geometry.kind,
    profile=geometry.profile,
    placement=geometry.placement,
    properties=properties,
    status=status,
    issues=issues,
  )
 
def read_ifc(path: str, *, mesh_fallback_limit: int = DEFAULT_MESH_FALLBACK_LIMIT) -> IfcReadResult:
  model = ifcopenshell.open(path)
  scales = _resolve_scales(model)
  levels = _read_levels(model, scales)
 
  model_issues: list[dict] = []
  if scales.ambiguous:
    model_issues.append(_issue("UNIT_SCALE_AMBIGUOUS", "error", "IFC file has no length unit; metres assumed. Verify dimensions."))
  if not levels:
    model_issues.append(_issue("NO_STOREYS", "warning", "Model has no IfcBuildingStorey; elements have no level."))
 
  schema_id = model.schema_identifier
  raw_elements = []
  excluded_counts: dict[str, int] = {}
  for element in model.by_type("IfcElement"):
    chain = _type_chain(schema_id, element.is_a())
    hit = next((name for name in chain if name in EXCLUDED_IFC_TYPES), None)
    if hit:
      excluded_counts[hit] = excluded_counts.get(hit, 0) + 1
      continue
    raw_elements.append(element)
  raw_elements.sort(key=lambda e: e.id())
 
  mesh_budget = [mesh_fallback_limit]
  elements: list[ReadElement] = []
  for element in raw_elements:
    try:
      elements.append(_normalise_element(element, scales, levels, mesh_budget, schema_id))
    except Exception as exc:
      elements.append(
        ReadElement(
          step_id=element.id(),
          global_id=_clean(getattr(element, "GlobalId", None)),
          ifc_type=element.is_a(),
          name=_clean(getattr(element, "Name", None)),
          raw_material_text=humanize_ifc_type(element.is_a()),
          is_generic_fallback=True,
          discipline=DEFAULT_DISCIPLINE,
          structural_role="UNKNOWN",
          classification_source="NONE",
          classification_confidence=Decimal("0"),
          status="INVALID",
          issues=[_issue("READ_ERROR", "error", f"Element could not be read: {str(exc)[:200]}")],
        )
      )
 
  if not elements:
    model_issues.append(_issue("NO_ELEMENTS", "error", "No supported building elements were found in the model."))
  if mesh_budget[0] <= 0:
    model_issues.append(_issue("MESH_FALLBACK_LIMIT_REACHED", "info", f"Mesh bounding-box fallback limit ({mesh_fallback_limit}) reached; later elements may lack geometry."))
 
  stats = {
    "element_count": len(elements),
    "by_status": {s: sum(1 for e in elements if e.status == s) for s in ("VALID", "WARNING", "INVALID")},
    "by_geometry_kind": {},
    "by_role": {},
    "by_discipline": {},
    "excluded": excluded_counts,
  }
  for e in elements:
    stats["by_geometry_kind"][e.geometry_kind] = stats["by_geometry_kind"].get(e.geometry_kind, 0) + 1
    stats["by_role"][e.structural_role] = stats["by_role"].get(e.structural_role, 0) + 1
    stats["by_discipline"][e.discipline] = stats["by_discipline"].get(e.discipline, 0) + 1
 
  return IfcReadResult(
    schema=str(model.schema),
    length_unit_scale=scales.length_m,
    levels=levels,
    elements=elements,
    model_issues=model_issues,
    stats=stats,
  )
 