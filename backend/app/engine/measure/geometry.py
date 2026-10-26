from __future__ import annotations
import math

def _f(value) -> float | None:
  try:
    number = float(value)
  except (TypeError, ValueError):
    return None
  return number if math.isfinite(number) else None

def snap_mm(value: float) -> float:
  return round(value * 10.0) / 10.0

def _polygon_area(points: list[tuple[float, float]]) -> float | None:
  if len(points) < 3:
    return None
  acc = 0.0
  for i in range(len(points)):
    x1, y1 = points[i]
    x2, y2 = points[(i + 1) % len(points)]
    acc += x1 * y2 - x2 * y1
  return abs(acc) / 2.0

def profile_area_mm2(profile: dict | None) -> float | None:
  if not profile:
    return None
  kind = profile.get("kind")
  if kind == "RECT":
    x, y = _f(profile.get("x_dim")), _f(profile.get("y_dim"))
    return snap_mm(x) * snap_mm(y) if x and y else None
  if kind == "CIRCLE":
    r = _f(profile.get("radius"))
    return math.pi * snap_mm(r) ** 2 if r else None
  if kind == "POLYGON":
    try:
      pts = [(snap_mm(float(p[0])), snap_mm(float(p[1]))) for p in (profile.get("points_mm") or [])]
    except (TypeError, ValueError, IndexError):
      return None
    return _polygon_area(pts)
  return None

def extrusion_volume_mm3(profile: dict | None, placement: dict | None) -> float | None:
  area = profile_area_mm2(profile)
  depth = _f((placement or {}).get("depth_mm"))
  if not area or not depth or area <= 0 or depth <= 0:
    return None
  return area * snap_mm(depth)

VOTE_TEXT = {
  "NO_MESH": "Geometry volume differs from the model's Qto volume by more than 2%.",
  "PRISM_MESH": "The profile and the 3D mesh agree; the model's Qto volume differs by more than 2%. The profile volume is billed.",
  "MESH_QTO": "The profile differs (it is cut); the 3D mesh and the model's Qto agree, so that volume is billed.",
  "PRISM_QTO": "The profile and the model's Qto agree; the 3D mesh differs by more than 2%. The profile volume is billed.",
  "MESH_ALONE": "The profile, the 3D mesh and the model's Qto volume all differ by more than 2%; the 3D mesh volume is billed.",
}
VOTE_RESOLVED = frozenset({"PRISM_MESH", "MESH_QTO", "PRISM_QTO"})

def _m3(value: float | None) -> float | None:
  return round(value / 1e9, 4) if value is not None else None

def volume_by_agreement(prism: float, mesh: float | None, qto: float, tolerance: float) -> tuple:
  """(billed mm3, basis, sources). Two of profile, 3D mesh and Qto that agree within tolerance win. With no mesh the profile is kept, as before.
  With a mesh and no agreement the mesh is billed: it is the actual body."""
  def agree(a, b) -> bool:
    return a is not None and b is not None and abs(a - b) <= tolerance * max(a, b)

  if mesh is None:
    basis, volume = "NO_MESH", prism
  elif agree(prism, mesh):
    basis, volume = "PRISM_MESH", prism
  elif agree(mesh, qto):
    basis, volume = "MESH_QTO", mesh
  elif agree(prism, qto):
    basis, volume = "PRISM_QTO", prism
  else:
    basis, volume = "MESH_ALONE", mesh
  return volume, basis, {"profile_m3": _m3(prism), "mesh_m3": _m3(mesh), "qto_m3": _m3(qto), "billed_m3": _m3(volume)}

def bbox_volume_mm3(lo, hi) -> float | None:
  if not lo or not hi or any(v is None for v in (*lo, *hi)):
    return None
  dx, dy, dz = (float(h) - float(l) for l, h in zip(lo, hi))
  volume = dx * dy * dz
  return volume if volume > 0 else None