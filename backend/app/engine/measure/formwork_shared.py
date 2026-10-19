from __future__ import annotations
from decimal import Decimal
from app.engine.measure import frame as FR
from app.engine.measure.units import q6

SHARING = ("COLUMN",)
SLAB_BY = ("SLAB",)
MM2_PER_M2 = Decimal("1000000")
ORTHO_TOL = 0.03
BEAM_ROLES = (None, "ROOF", "PLINTH", "BAND")
MIN_TOL_MM, REL_TOL = 150.0, 0.06

def _label(kind: str, m) -> str:
  return f"{kind} {m.tag or ''}".strip()

def _walls(inputs: tuple, place, stats: dict) -> list:
  out = []
  for m in inputs:
    if m.category != "RCC_WALL":
      continue
    if not (m.frame and len(m.points_mm) >= 2):
      stats["unplaced_walls"] += 1
      continue
    a, b = place(m.frame, *map(float, m.points_mm[0])), place(m.frame, *map(float, m.points_mm[-1]))
    if a is None or b is None:
      stats["unplaced_walls"] += 1
      continue
    dx, dy = b[0] - a[0], b[1] - a[1]
    run, thick, height = max(abs(dx), abs(dy)), float(m.width_mm), float(m.depth_mm)
    if run <= 0 or thick <= 0 or height <= 0 or min(abs(dx), abs(dy)) > ORTHO_TOL * run:
      stats["walls_not_square"] += 1
      continue
    cx, cy = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
    box = FR.box_around(cx, cy, run, thick, 0.0, height) if abs(dx) >= abs(dy) else FR.box_around(cx, cy, thick, run, 0.0, height)
    out.append((m, box))
    stats["placed_walls"] += 1
  return out

def _column_points(inputs: tuple, place, group_of) -> list:
  pts = []
  for m in inputs:
    if m.category not in SHARING or not (m.frame and m.points_mm):
      continue
    for i, pt in enumerate(m.points_mm[:m.count]):
      p = place(m.frame, float(pt[0]), float(pt[1]))
      if p is not None:
        pts.append((m, i, p))
  return pts

def _beam_boxes(inputs: tuple, place, columns: list, group_of, stats: dict) -> list:
  """[(beam input, Box)]: each beam position matched to two columns of its floor that it runs between."""
  out = []
  for b in inputs:
    if b.category != "BEAM" or b.role not in BEAM_ROLES or not (b.frame and b.points_mm):
      continue
    length, width, depth = float(b.length_mm), float(b.width_mm), float(b.depth_mm)
    if min(length, width, depth) <= 0:
      continue
    tol = max(MIN_TOL_MM, REL_TOL * length)
    for pt in b.points_mm[:b.count]:
      c = place(b.frame, float(pt[0]), float(pt[1]))
      if c is None:
        stats["unplaced_beams"] += 1
        continue
      near = [(m, p) for m, _, p in columns if group_of.get(m.frame) == group_of.get(b.frame)
        and not (m.level_id is not None and b.level_id is not None and m.level_id != b.level_id)]
      best = None
      for i, (m1, p1) in enumerate(near):
        for m2, p2 in near[i + 1:]:
          dx, dy = p2[0] - p1[0], p2[1] - p1[1]
          horizontal = abs(dy) <= ORTHO_TOL * max(abs(dx), 1.0) and abs(dx) > 0
          vertical = abs(dx) <= ORTHO_TOL * max(abs(dy), 1.0) and abs(dy) > 0
          if not (horizontal or vertical):
            continue
          mid = ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)
          if abs(mid[0] - c[0]) > tol or abs(mid[1] - c[1]) > tol:
            continue
          centre = abs(dx) if horizontal else abs(dy)
          ext1, ext2 = (float(m1.length_mm), float(m2.length_mm)) if horizontal else (float(m1.width_mm), float(m2.width_mm))
          clear = centre - (ext1 + ext2) / 2.0
          fit = min(abs(length - clear), abs(length - centre))
          if clear > 0 and fit <= tol and (best is None or fit < best[0]):
            best = (fit, mid, clear, horizontal)
      if best is None:
        stats["unmatched_beams"] += 1
        continue
      _, mid, clear, horizontal = best
      out.append((b, FR.box_around(mid[0], mid[1], clear, width, 0.0, 0.0) if horizontal else FR.box_around(mid[0], mid[1], width, clear, 0.0, 0.0), depth))
      stats["matched_beams"] += 1
  return out

def shared_faces(inputs: tuple, takeoff, enabled: bool, walls_on: bool = True, beams_on: bool = True) -> tuple:
  """({(measurement id, instance): {"faces": [...], "uncertain": bool}}, stats) for the columns of inputs."""
  stats: dict = {"enabled": enabled, "placed_columns": 0, "unplaced_columns": 0, "removed_m2": "0", "members_with_removal": 0, "uncertain_members": 0,
    "placed_walls": 0, "unplaced_walls": 0, "walls_not_square": 0, "matched_beams": 0, "unmatched_beams": 0, "unplaced_beams": 0, "removed_by": {}}
  frames = FR.frames_of(takeoff)
  if not enabled or not frames:
    stats["enabled"] = bool(enabled) and bool(frames)
    return {}, stats
  group_of = {a.view: a.group for a in tuple(getattr(takeoff, "alignments", ()) or ())}

  def place(view, x, y):
    f = frames.get(group_of.get(view))
    return FR.frame_xy(f, view, x, y) if f is not None else None

  slabs = []
  for m in inputs:
    if m.category in SLAB_BY and m.frame and m.points_mm:
      p = place(m.frame, float(m.points_mm[0][0]), float(m.points_mm[0][1]))
      if p is not None:
        slabs.append((m, p))
  walls = _walls(inputs, place, stats) if walls_on else []
  columns = _column_points(inputs, place, group_of)
  beams = _beam_boxes(inputs, place, columns, group_of, stats) if beams_on else []

  out: dict = {}
  removed = Decimal("0")
  by_kind: dict = {}
  for m in inputs:
    if m.category not in SHARING:
      continue
    if not (m.frame and m.points_mm):
      stats["unplaced_columns"] += m.count
      continue
    height, length, width = float(m.depth_mm), float(m.length_mm), float(m.width_mm)
    for i, pt in enumerate(m.points_mm[:m.count]):
      p = place(m.frame, float(pt[0]), float(pt[1]))
      if p is None:
        stats["unplaced_columns"] += 1
        continue
      stats["placed_columns"] += 1
      col = FR.box_around(p[0], p[1], length, width, 0.0, height)
      near = []
      
      for w, box in walls:
        if w.level_id is not None and m.level_id is not None and w.level_id != m.level_id:
          continue
        if group_of.get(w.frame) != group_of.get(m.frame):
          continue
        near.append((_label("wall", w), FR.Box(box.x0, box.y0, box.x1, box.y1, 0.0, min(box.z1, height)), w, "wall"))
      for bm, box, depth in beams:
        if bm.level_id is not None and m.level_id is not None and bm.level_id != m.level_id:
          continue
        if group_of.get(bm.frame) != group_of.get(m.frame):
          continue
        near.append((_label("beam", bm), FR.Box(box.x0, box.y0, box.x1, box.y1, max(0.0, height - depth), height), bm, "beam"))
      for s, (sx, sy) in slabs:
        if s.level_id is not None and m.level_id is not None and s.level_id != m.level_id:
          continue
        if group_of.get(s.frame) != group_of.get(m.frame):
          continue
      
        t = min(float(s.depth_mm), height)
        near.append((_label("slab", s), FR.box_around(sx, sy, float(s.length_mm), float(s.width_mm), height - t, height), s, "slab"))
      faces = FR.shared_side_faces(col, [(label, box) for label, box, _, _ in near])
      if not faces:
        continue
      kind_of = {label: kind for label, _, _, kind in near}
      uncertain = False
      
      for label, _, n, _ in near:
        if any(f["by"] == label for f in faces) and (n.level_id is None) != (m.level_id is None):
          uncertain = True
        if any(f["by"] == label for f in faces) and n.frame != m.frame:
          fr = frames[group_of[m.frame]]
          a, b = fr.alignments.get(m.frame), fr.alignments.get(n.frame)
          if any(x is None or x.grade != FR.CONFIRMED for x in (a, b)):
            uncertain = True
            
      out[(str(m.measurement_id), i)] = {"faces": faces, "uncertain": uncertain}
      stats["members_with_removal"] += 1
      stats["uncertain_members"] += 1 if uncertain else 0
      for f in faces:
        area = Decimal(str(f["area_mm2"])) / MM2_PER_M2
        removed += area
        k = kind_of.get(f["by"], "slab")
        by_kind[k] = by_kind.get(k, Decimal("0")) + area
  stats["removed_m2"] = str(q6(removed))
  stats["removed_by"] = {k: str(q6(v)) for k, v in sorted(by_kind.items())}
  stats["alignments"] = {k: {"method": a.method, "grade": a.grade, "dx_mm": a.dx_mm, "dy_mm": a.dy_mm}
    for f in frames.values() for k, a in sorted(f.alignments.items())}
  return out, stats

def reveal_faces(m) -> list:
  thick = Decimal(str(m.width_mm))
  out = []
  
  for kind, label in (("DOOR", "door"), ("WINDOW", "window"), ("OPENING", "opening")):
    area = Decimal("0")
    for o in getattr(m, "openings", ()) or ():
      if str(o.get("role") or "OPENING").upper() != kind:
        continue
      w, h, n = Decimal(str(o.get("width_mm") or 0)), Decimal(str(o.get("height_mm") or 0)), Decimal(str(o.get("nos") or 1))
      if w <= 0 or h <= 0:
        continue
      area += n * ((2 * h + w) if kind == "DOOR" else (2 * h + 2 * w)) * thick
    if area > 0:
      out.append((f"{label} reveals", area))
  return out
