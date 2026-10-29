from __future__ import annotations
import hashlib
import math
from dataclasses import dataclass, field
from shapely.geometry import Polygon, Point
from app.modules.drawings_boq.takeoff.model.types import Level, Source, Member, Sighting, WallRun, Face
from app.modules.drawings_boq.takeoff.model import rules as MR
from app.modules.drawings_boq.takeoff.model import walls as MW
from app.modules.drawings_boq.takeoff.prep.schedules import level_key
from app.engine.measure import readings as QSR

IFC = "IFC"
KINDS = ("COLUMN", "FOOTING", "BEAM")
PROBE_POINTS = 5
PROBE_REACH_MM = 150.0
MIN_AXIS_MM = 300.0

@dataclass(frozen=True)
class IfcModel:
  levels: tuple = ()
  members: tuple = ()
  walls: tuple = ()
  beam_webs: dict = field(default_factory=dict)
  notes: tuple = ()

  def summary(self) -> dict:
    kinds: dict = {}
    for m in self.members:
      kinds[m.kind] = kinds.get(m.kind, 0) + 1
    return {"levels": len(self.levels), "members": dict(sorted(kinds.items())), "walls": len(self.walls), "walls_with_room_faces": sum(1 for w in self.walls if any(f.bounds != MW.OUTSIDE for f in w.faces)),
      "beams_with_web": len(self.beam_webs), "notes": list(self.notes)}

def _g(e, *names):
  for n in names:
    v = getattr(e, n, None)
    if v is None and isinstance(e, dict):
      v = e.get(n)
    if v is not None:
      return v
  return None

def _f(v) -> float | None:
  try:
    x = float(v)
  except (TypeError, ValueError):
    return None
  return x if x == x and x > 0 else None

def floor_key(name: str | None) -> str | None:
  if not name:
    return None
  return level_key(name) or str(name).strip().upper()

def levels_of(levels, elements=()) -> tuple:
  rows = sorted(((_g(l, "global_id", "id"), _g(l, "name"), _f_any(_g(l, "elevation_mm"))) for l in levels), key=lambda t: (t[2] is None, t[2] if t[2] is not None else 0.0))
  zr: dict = {}
  for e in elements:
    gid = _g(e, "level_global_id", "level_id")
    lo, hi = _f_any(_g(e, "elevation_base_mm")), _f_any(_g(e, "elevation_top_mm"))
    if gid is None or lo is None or hi is None:
      continue
    cur = zr.get(str(gid))
    zr[str(gid)] = (min(cur[0], lo), max(cur[1], hi)) if cur else (lo, hi)
    
  out = []
  for i, (gid, name, elev) in enumerate(rows):
    nxt = next((r[2] for r in rows[i + 1:] if r[2] is not None and elev is not None and r[2] > elev), None)
    f2f = (nxt - elev) if (nxt is not None and elev is not None) else None
    src = [Source(IFC, "level_mm", elev, "IFC_STOREY", IFC, True)] if elev is not None else []
    if f2f:
      src.append(Source(IFC, "floor_to_floor_mm", f2f, "NEXT_STOREY", IFC, True))
    if str(gid) in zr:
      lo, hi = zr[str(gid)]
      src.append(Source(IFC, "z_range_mm", hi - lo, f"ELEMENTS {lo:g} to {hi:g}", IFC, False))
    key = floor_key(name)
    out.append(Level(key or str(gid), elev, None, f2f, tuple(src), IFC, "IFC_STOREY" if elev is not None else ""))
  return tuple(out)

def _f_any(v) -> float | None:
  try:
    x = float(v)
  except (TypeError, ValueError):
    return None
  return x if x == x else None

def _size(role: str, e) -> tuple | None:
  length, width, height, thick = (_f(_g(e, k)) for k in ("length_mm", "width_mm", "height_mm", "thickness_mm"))
  prof = _g(e, "profile") or {}
  
  if role == "COLUMN":
    a, b = _f(prof.get("x_dim")) or length, _f(prof.get("y_dim")) or width
    return tuple(sorted((round(a, 1), round(b, 1)))) if a and b else None
  if role == "FOOTING":
    a, b, d = length, width, height or thick
    return (*sorted((round(a, 1), round(b, 1))), round(d, 1)) if a and b and d else None
  b, d = _f(prof.get("x_dim")) or width, _f(prof.get("y_dim")) or height
  return (round(b, 1), round(d, 1)) if b and d else None

def _kind_of(e) -> str | None:
  role = str(_g(e, "structural_role") or "").upper()
  return role if role in KINDS else None

def _outline(e) -> tuple:
  pl = _g(e, "placement") or {}
  plan = pl.get("plan_mm") if isinstance(pl, dict) else None
  if plan and len(plan) >= 3:
    return tuple((round(float(x), 1), round(float(y), 1)) for x, y in plan)
  lo, hi = _g(e, "bbox_min_mm"), _g(e, "bbox_max_mm")
  
  if not (lo and hi) and None not in (_g(e, "bbox_min_x_mm"), _g(e, "bbox_min_y_mm"), _g(e, "bbox_max_x_mm"), _g(e, "bbox_max_y_mm")):
    lo, hi = (_g(e, "bbox_min_x_mm"), _g(e, "bbox_min_y_mm")), (_g(e, "bbox_max_x_mm"), _g(e, "bbox_max_y_mm"))
  if lo and hi:
    return ((float(lo[0]), float(lo[1])), (float(hi[0]), float(lo[1])), (float(hi[0]), float(hi[1])), (float(lo[0]), float(hi[1])))
  return ()

def _id(kind, floor, mark, gid) -> str:
  return "mi_" + hashlib.sha1(f"{kind}|{floor}|{mark}|{gid}".encode()).hexdigest()[:12]

def members_of(elements, drawing_id: str, floor_of: dict) -> tuple:
  out = []
  for e in elements:
    kind = _kind_of(e)
    if kind is None or str(_g(e, "status", "normalization_status") or "VALID") == "INVALID":
      continue
  
    gid = str(_g(e, "global_id", "ifc_global_id") or _g(e, "step_id") or "")
    floor = floor_of.get(str(_g(e, "level_global_id", "level_id")))
    mark = _g(e, "type_mark") or None
    out.append(Member(_id(kind, floor, mark or _g(e, "name"), gid), kind, mark, floor, _outline(e), _size(kind, e), _f(_g(e, "height_mm")) if kind == "COLUMN" else None,
      (Sighting(str(drawing_id), 0, gid, IFC),)))
  return tuple(out)

def _axis(e) -> tuple | None:
  ring = _outline(e)
  if len(ring) < 3:
    return None
  try:
    box = Polygon(ring).minimum_rotated_rectangle
    pts = list(box.exterior.coords)[:4]
  except Exception:
    return None

  sides = [(math.hypot(pts[(i + 1) % 4][0] - pts[i][0], pts[(i + 1) % 4][1] - pts[i][1]), i) for i in range(4)]
  long_len, i = max(sides)
  short_len = min(s for s, _ in sides)
  if long_len < MIN_AXIS_MM:
    return None
  a, b, c, d = pts[i], pts[(i + 1) % 4], pts[(i + 2) % 4], pts[(i + 3) % 4]
  p0, p1 = ((a[0] + d[0]) / 2.0, (a[1] + d[1]) / 2.0), ((b[0] + c[0]) / 2.0, (b[1] + c[1]) / 2.0)
  t = _f(_g(e, "thickness_mm")) or short_len
  return p0, p1, t

def _faces(p0, p1, t: float, rooms: list) -> tuple:
  L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
  if L <= 0:
    return ()
  ux, uy = (p1[0] - p0[0]) / L, (p1[1] - p0[1]) / L
  nx, ny = -uy, ux
  out = []
  
  for side, sign in (("L", 1.0), ("R", -1.0)):
    got: dict = {}
    for k in range(PROBE_POINTS):
      f = (k + 0.5) / PROBE_POINTS
      x = p0[0] + ux * L * f + sign * nx * (t / 2.0 + PROBE_REACH_MM)
      y = p0[1] + uy * L * f + sign * ny * (t / 2.0 + PROBE_REACH_MM)
      pt = Point(x, y)
      hit = next((rid for rid, poly in rooms if poly.contains(pt)), MW.OUTSIDE)
      got[hit] = got.get(hit, 0) + 1
    out += [Face(side, b, round(n / PROBE_POINTS, 4)) for b, n in sorted(got.items(), key=lambda kv: str(kv[0]))]
  return tuple(out)

def walls_of(elements, spaces, floor_of: dict) -> tuple:
  rooms: dict = {}
  for s in spaces or []:
    fp = _g(s, "footprint") or {}
    plan = fp.get("plan_mm") if isinstance(fp, dict) else None
    if plan and len(plan) >= 3:
      try:
        poly = Polygon([(float(x), float(y)) for x, y in plan])
      except Exception:
        continue
      if poly.is_valid and not poly.is_empty:
        rooms.setdefault(floor_of.get(str(_g(s, "level_global_id"))), []).append((str(_g(s, "global_id")), poly))
        
  out = []
  for e in elements:
    if not str(_g(e, "structural_role") or "").upper().startswith("WALL") or str(_g(e, "status", "normalization_status") or "VALID") == "INVALID":
      continue
    ax = _axis(e)
    if ax is None:
      continue
    p0, p1, t = ax
    floor = floor_of.get(str(_g(e, "level_global_id", "level_id")))
    gid = str(_g(e, "global_id", "ifc_global_id") or _g(e, "step_id") or "")
    out.append(WallRun(gid, floor, (round(p0[0], 1), round(p0[1], 1)), (round(p1[0], 1), round(p1[1], 1)), round(t, 1), _faces(p0, p1, t, rooms.get(floor, []))))
  return tuple(out)

def beam_webs_of(elements, members: tuple, floor_of: dict) -> dict:
  slab = {}
  for e in elements:
    if str(_g(e, "structural_role") or "").upper().startswith("SLAB") and not str(_g(e, "structural_role")).upper().endswith("FOUNDATION"):
      t = _f(_g(e, "thickness_mm")) or _f(_g(e, "height_mm"))
      fl = floor_of.get(str(_g(e, "level_global_id", "level_id")))
      if t and (fl not in slab or t < slab[fl]):
        slab[fl] = t
  includes = bool(QSR.param("beam_depth_includes_slab"))
  by_gid = {str(_g(e, "global_id", "ifc_global_id") or _g(e, "step_id") or ""): e for e in elements}
  out = {}
  
  for m in members:
    if m.kind != "BEAM" or not m.size_mm or len(m.size_mm) < 2:
      continue
    e = by_gid.get(m.sightings[0].candidate_key)
    text = " ".join(str(x) for x in (_g(e, "name"), _g(e, "type_name"), (_g(e, "properties") or {}).get("_ifc", {}).get("predefined_type")) if x).upper()
    role = "PLINTH" if any(w in text for w in ("GRADE", "PLINTH", "TIE BEAM", "FOUNDATION")) else "BAND" if "BAND" in text else "ROOF"
    basis = MR.depth_basis(role, m.mark, includes)
    web = MR.beam_web(m.size_mm[1], slab.get(m.floor), basis)
    if web:
      out[m.id] = {**web, "depth_mm": m.size_mm[1]}
  return out

def from_read(result, drawing_id: str, floor_of: dict | None = None) -> IfcModel:
  levels = levels_of(result.levels, result.elements)
  fl = floor_of or {str(_g(l, "global_id")): floor_key(_g(l, "name")) for l in result.levels}
  members = members_of(result.elements, drawing_id, fl)
  notes = []
  
  if not any(True for _ in result.spaces or []):
    notes.append("NO_SPACES: the model has no IfcSpace, so no wall has a room on a face; both faces of every wall are OUTSIDE")
  return IfcModel(levels, members, walls_of(result.elements, result.spaces, fl), beam_webs_of(result.elements, members, fl), tuple(notes))

def from_rows(rows, drawing_id: str, level_names: dict) -> tuple:
  floor_of = {str(k): floor_key(v) for k, v in level_names.items()}
  return members_of(rows, drawing_id, floor_of)
