from __future__ import annotations
import heapq
import math
import os
import yaml

PT_MM = 25.4 / 72.0            
MAX_SEGMENTS = 30000
SNAP_PT = 2.0                  
REACH_PT = 12.0                
SCALE_TOL = 0.05              
HERE = os.path.dirname(os.path.abspath(__file__))
TABLES = os.path.join(HERE, "..", "catalogue", "mep_tables.yaml")

UNMEASURED = None              

def tables(path: str = TABLES) -> dict:
  with open(path, encoding="utf-8") as fh:
    return yaml.safe_load(fh) or {}

def paper_to_mm(length_pt: float, ratio: float) -> float:
  return float(length_pt) * PT_MM * float(ratio)

def scale_check(ratio: float | None, drawn_pt: float | None = None, printed_mm: float | None = None, tol: float = SCALE_TOL) -> tuple:
  if ratio is None or ratio <= 0:
    return False, None
  if drawn_pt is None or printed_mm is None or drawn_pt <= 0 or printed_mm <= 0:
    return True, None
  implied = printed_mm / (drawn_pt * PT_MM)
  return abs(implied - ratio) <= tol * ratio, round(implied, 3)

def _dist(a, b) -> float:
  return math.hypot(a[0] - b[0], a[1] - b[1])

def _project(p, s) -> tuple:
  dx, dy = s[2] - s[0], s[3] - s[1]
  n = dx * dx + dy * dy
  t = 0.0 if n <= 0 else max(0.0, min(1.0, ((p[0] - s[0]) * dx + (p[1] - s[1]) * dy) / n))
  foot = (s[0] + t * dx, s[1] + t * dy)
  return t, _dist(p, foot), foot

class _Grid:
  def __init__(self, cell: float):
    self.cell, self.cells = cell, {}

  def add(self, key, box):
    c = self.cell
    for i in range(int(box[0] // c), int(box[2] // c) + 1):
      for j in range(int(box[1] // c), int(box[3] // c) + 1):
        self.cells.setdefault((i, j), []).append(key)

  def near(self, p, r):
    c = self.cell
    out = set()
    for i in range(int((p[0] - r) // c), int((p[0] + r) // c) + 1):
      for j in range(int((p[1] - r) // c), int((p[1] + r) // c) + 1):
        out.update(self.cells.get((i, j), ()))
    return out

class _Find:
  def __init__(self):
    self.up = {}

  def find(self, x):
    self.up.setdefault(x, x)
    while self.up[x] != x:
      self.up[x] = self.up[self.up[x]]
      x = self.up[x]
    return x

  def union(self, a, b):
    ra, rb = self.find(a), self.find(b)
    if ra != rb:
      self.up[rb] = ra

def route_pt(segments: list, a: tuple, b: tuple, snap: float = SNAP_PT, reach: float = REACH_PT) -> dict:
  segs = [tuple(float(v) for v in s) for s in segments if _dist((s[0], s[1]), (s[2], s[3])) > 1e-6]
  if len(segs) > MAX_SEGMENTS:
    return {"length_pt": UNMEASURED, "reason": "TOO_MANY_SEGMENTS", "segments": len(segs)}
  if not segs:
    return {"length_pt": UNMEASURED, "reason": "NO_LINE_NEAR_START", "segments": 0}
  grid = _Grid(max(snap, reach, 8.0))
  for i, s in enumerate(segs):
    grid.add(i, (min(s[0], s[2]) - snap, min(s[1], s[3]) - snap, max(s[0], s[2]) + snap, max(s[1], s[3]) + snap))
  cuts = {i: [(0.0, (s[0], s[1])), (1.0, (s[2], s[3]))] for i, s in enumerate(segs)}
  ends = [(i, p) for i, s in enumerate(segs) for p in ((s[0], s[1]), (s[2], s[3]))]
  for i, p in ends:
    for j in grid.near(p, snap):
      if j == i:
        continue
      t, d, foot = _project(p, segs[j])
      if d <= snap and 0.0 < t < 1.0:
        cuts[j].append((t, foot))
        
  anchors = []
  for name, p in (("START", a), ("END", b)):
    best = None
    for j in grid.near(p, reach + snap):
      t, d, foot = _project(p, segs[j])
      if d <= reach and (best is None or d < best[0]):
        best = (d, j, t, foot)
    if best is None:
      return {"length_pt": UNMEASURED, "reason": "NO_LINE_NEAR_" + name, "segments": len(segs)}
    cuts[best[1]].append((best[2], best[3]))
    anchors.append(best[3])
  nodes, uf, ng = [], _Find(), _Grid(max(snap, 1.0))

  def node(p):
    for k in ng.near(p, snap):
      if _dist(nodes[k], p) <= snap:
        return k
    nodes.append(p)
    k = len(nodes) - 1
    ng.add(k, (p[0], p[1], p[0], p[1]))
    return k
  edges: dict = {}
  for i, pieces in cuts.items():
    pieces.sort(key=lambda x: x[0])
    for (t0, p0), (t1, p1) in zip(pieces, pieces[1:]):
      u, v = node(p0), node(p1)
      if u != v:
        w = _dist(p0, p1)
        edges.setdefault(u, []).append((v, w))
        edges.setdefault(v, []).append((u, w))
        
  src, dst = node(anchors[0]), node(anchors[1])
  dist, heap = {src: 0.0}, [(0.0, src)]
  while heap:
    d, u = heapq.heappop(heap)
    if u == dst:
      return {"length_pt": round(d, 3), "reason": None, "segments": len(segs)}
    if d > dist.get(u, 1e18):
      continue
    for v, w in edges.get(u, ()):
      nd = d + w
      if nd < dist.get(v, 1e18):
        dist[v] = nd
        heapq.heappush(heap, (nd, v))
  return {"length_pt": UNMEASURED, "reason": "NOT_CONNECTED", "segments": len(segs)}

def route_mm(segments: list, a: tuple, b: tuple, ratio: float | None, scale_ok: bool = True, **kw) -> dict:
  if not scale_ok or ratio is None:
    return {"length_mm": UNMEASURED, "length_pt": UNMEASURED, "reason": "SCALE", "segments": len(segments)}
  r = route_pt(segments, a, b, **kw)
  return {**r, "length_mm": None if r["length_pt"] is None else round(paper_to_mm(r["length_pt"], ratio), 1)}

def vertical_mm(level_from_mm: float | None, level_to_mm: float | None) -> float | None:
  if level_from_mm is None or level_to_mm is None:
    return UNMEASURED
  return abs(float(level_to_mm) - float(level_from_mm))

def drop_mm(ceiling_mm: float | None, mounting_mm: float | None) -> float | None:
  if ceiling_mm is None or mounting_mm is None:
    return UNMEASURED
  return max(0.0, float(ceiling_mm) - float(mounting_mm))

def _fill(conduit_mm: int, mm2: str, t: dict) -> int | None:
  return ((t["conduit"]["fill"].get(conduit_mm) or {}).get(mm2))

def conduit_size(wires: dict, t: dict | None = None) -> dict:
  t = t or tables()
  sizes = t["wires"]["sizes_mm2"]
  need = {}
  for w, n in (wires or {}).items():
    if int(n) <= 0:
      continue
    if w not in sizes:
      return {"size_mm": None, "fill": None, "reason": "UNKNOWN_WIRE", "wire": w}
    need[str(sizes[w])] = need.get(str(sizes[w]), 0) + int(n)
  if not need:
    return {"size_mm": None, "fill": None, "reason": "NO_WIRES"}
  for c in sorted(int(k) for k in t["conduit"]["fill"]):
    fits = [_fill(c, mm2, t) for mm2 in need]
    if any(not f for f in fits):
      continue
    share = sum(n / _fill(c, mm2, t) for mm2, n in need.items())
    if share <= 1.0 + 1e-9:
      return {"size_mm": c, "fill": round(share, 3), "reason": None}
  return {"size_mm": None, "fill": None, "reason": "OVER_TABLE"}

def circuit_totals(runs: list, t: dict | None = None) -> dict:
  t = t or tables()
  wire, conduit, unmeasured, no_size = {}, {}, 0, 0
  for r in runs:
    L = r.get("length_mm")
    if L is None:
      unmeasured += 1
      continue
    for w, n in (r.get("wires") or {}).items():
      wire[w] = wire.get(w, 0.0) + float(L) * int(n)
    c = conduit_size(r.get("wires") or {}, t)
    if c["size_mm"] is None:
      no_size += 1
    else:
      conduit[c["size_mm"]] = conduit.get(c["size_mm"], 0.0) + float(L)
  return {"wire_mm": {k: round(v, 1) for k, v in sorted(wire.items())}, "conduit_mm": {k: round(v, 1) for k, v in sorted(conduit.items())}, "unmeasured": unmeasured, "no_size": no_size}

def pipe_totals(runs: list) -> dict:
  out: dict = {}
  for r in runs:
    k = (str(r.get("service") or "?"), str(r.get("size") or "?"))
    e = out.setdefault(k, {"mm": 0.0, "runs": 0, "unmeasured": 0})
    e["runs"] += 1
    if r.get("length_mm") is None:
      e["unmeasured"] += 1
    else:
      e["mm"] = round(e["mm"] + float(r["length_mm"]), 1)
  return {f"{s}|{z}": v for (s, z), v in sorted(out.items())}

def fallback(rooms: int | None, points: int | None, wire_per_point_m: float | None, points_per_room: float | None) -> dict:
  open_cards = []
  if points is None:
    if points_per_room is None:
      open_cards.append("POINTS_PER_ROOM")
    elif rooms is None:
      open_cards.append("ROOMS")
    else:
      points = round(float(rooms) * float(points_per_room))
  if wire_per_point_m is None:
    open_cards.append("WIRE_PER_POINT")
  if open_cards:
    return {"status": "OPEN", "open": open_cards, "points": points, "wire_mm": None}
  return {"status": "ASSUMED", "open": [], "points": points, "wire_mm": round(points * float(wire_per_point_m) * 1000.0, 1)}

def card_values() -> dict:
  from app.engine.catalogue import standards as ST
  out = {}
  for key, entry_id in (("WIRE_PER_POINT", "STD_WIRE_PER_POINT"), ("POINTS_PER_ROOM", "STD_POINTS_PER_ROOM")):
    try:
      v = ST.value(entry_id)
    except ST.StandardsError:
      v = None
    out[key] = v if isinstance(v, (int, float)) else None
  return out
