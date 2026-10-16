from __future__ import annotations
import re
import math
from app.modules.drawings_boq.takeoff.prep import views as VW
from app.modules.drawings_boq.takeoff.prep.spatial import VectorIndex
from app.modules.drawings_boq.takeoff.extract import walls as W
from array import array

NOT_A_FLOOR_PLAN = re.compile(r"\b(?:KEY|SITE|BLOCK|BOUNDARY|LOCATION|SEWER\w*|DRAINAGE|SEPTIC|SERVICE|LANDSCAPE|PARKING)\b", re.I)
LINK_MM = 650.0                 
LINK_MIN_PT, LINK_MAX_PT = 4.0, 24.0
SPLIT_LINK = 2.0                
MIN_WALL_M = 8.0                
ALONG_SLACK = 0.25              
REACH_SHARE, REACH_PT = 0.6, 40.0
BEHIND_PT = 6.0                 
ABSORB_MM = 3500.0              
ABSORB_MIN_PT, ABSORB_MAX_PT = 14.0, 60.0
ABSORB_MAX_SHARE = 0.7          
MARGIN_MM = 1500.0             
MARGIN_MIN_PT, MARGIN_MAX_PT = 10.0, 40.0
LEFT_OUT_MIN_M = 1.0           
FLAT_PT = 3.0                   
COVER_SHARE = 0.25              
LEFT_OUT_MAX = 14               

def is_floor_plan(cap: dict) -> bool:
  """A plan caption that names a floor, and is not the key plan, site plan, block plan or boundary wall."""
  return cap["kind"] == "PLAN" and VW.level_of(cap["text"]) is not None and not NOT_A_FLOOR_PLAN.search(cap["text"])

def floor_captions(words: list) -> list:
  return [c for c in VW.captions(words) if is_floor_plan(c)]

def _axes(angle: float) -> tuple:
  a = math.radians(angle)
  return math.cos(a), math.sin(a)

def _uv(angle: float, x: float, y: float) -> tuple:
  """A point along and across a caption (the way VW.captions measures them)."""
  ux, uy = _axes(angle)
  return x * ux + y * uy, -x * uy + y * ux

def _extent(angle: float, bbox: tuple) -> tuple:
  pts = [_uv(angle, x, y) for x in (bbox[0], bbox[2]) for y in (bbox[1], bbox[3])]
  us, vs = [p[0] for p in pts], [p[1] for p in pts]
  return min(us), max(us), min(vs), max(vs)

def _wall_lines(frames: list, runs: list, split_pt: float = 0.0) -> list:
  out = []
  
  for r in runs:
    fr = frames[r.peak]
    a0, a1 = r.s0 - r.ext0, r.s1 + r.ext1
    cuts = sorted((g0, g1) for g0, g1 in r.gaps if split_pt > 0.0 and g1 - g0 > split_pt)
    pieces, start = [], a0
    for g0, g1 in cuts:
      if g0 > start:
        pieces.append((start, g0))
      start = max(start, g1)
    if a1 > start:
      pieces.append((start, a1))
    for s0, s1 in pieces:
      p0, p1 = fr.pt(s0, r.dc), fr.pt(s1, r.dc)
      out.append((p0[0], p0[1], p1[0], p1[1], math.hypot(p1[0] - p0[0], p1[1] - p0[1])))
  return out

def _near(a: tuple, b: tuple, reach: float) -> bool:
  def dist(px, py, s):
    dx, dy = s[2] - s[0], s[3] - s[1]
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 <= 1e-12 else max(0.0, min(1.0, ((px - s[0]) * dx + (py - s[1]) * dy) / l2))
    return math.hypot(px - s[0] - t * dx, py - s[1] - t * dy)
  return min(dist(a[0], a[1], b), dist(a[2], a[3], b), dist(b[0], b[1], a), dist(b[2], b[3], a)) <= reach

def group_walls(lines: list, reach: float) -> list:
  """The walls that touch (or nearly touch) one another, as groups: [{"idx": [...], "bbox": (x0, y0, x1, y1), "length_pt": ...}]."""
  n = len(lines)
  parent = list(range(n))

  def root(a: int) -> int:
    while parent[a] != a:
      parent[a] = parent[parent[a]]
      a = parent[a]
    return a
  cell = max(reach * 2.0, 1.0)
  grid: dict = {}
  
  for i, s in enumerate(lines):
    cx0, cx1 = sorted((int(math.floor(s[0] / cell)), int(math.floor(s[2] / cell))))
    cy0, cy1 = sorted((int(math.floor(s[1] / cell)), int(math.floor(s[3] / cell))))
    for gx in range(cx0 - 1, cx1 + 2):
      for gy in range(cy0 - 1, cy1 + 2):
        grid.setdefault((gx, gy), []).append(i)
  for members in grid.values():
    for a in range(len(members)):
      for b in range(a + 1, len(members)):
        i, j = members[a], members[b]
        if root(i) != root(j) and _near(lines[i], lines[j], reach):
          parent[root(i)] = root(j)
          
  groups: dict = {}
  for i in range(n):
    groups.setdefault(root(i), []).append(i)
  out = []
  for idx in groups.values():
    xs = [c for i in idx for c in (lines[i][0], lines[i][2])]
    ys = [c for i in idx for c in (lines[i][1], lines[i][3])]
    out.append({"idx": idx, "bbox": (min(xs), min(ys), max(xs), max(ys)), "length_pt": sum(lines[i][4] for i in idx)})
  return out

def _score(cap: dict, g: dict) -> tuple | None:
  """How well a caption names a drawing: it stands under (or over) the drawing's width, and close to it. A caption under the drawing beats one over it; then the nearer one. None is not at all."""
  lo, hi = cap["along"]
  centre, line = (lo + hi) / 2.0, cap["across"]
  u0, u1, v0, v1 = _extent(cap["angle"], g["bbox"])
  width, depth = u1 - u0, v1 - v0
  if not (u0 - ALONG_SLACK * width <= centre <= u1 + ALONG_SLACK * width):
    return None
  best = None
  for side, gap in ((0, v0 - line), (1, line - v1)):
    if gap < -BEHIND_PT or gap > REACH_SHARE * depth + REACH_PT:
      continue
    if best is None or (side, gap) < best:
      best = (side, max(gap, 0.0))
  return best

def _owners(groups: list, caps: list) -> list:
  """For each group of walls the caption (an index into caps) that names it: the nearest one, or None."""
  out = []
  for g in groups:
    best = None
    for ci, cap in enumerate(caps):
      sc = _score(cap, g)
      if sc is not None and (best is None or sc < best[0]):
        best = (sc, ci)
    out.append(None if best is None else best[1])
  return out

def _gap(a: tuple, b: tuple) -> float:
  return math.hypot(max(a[0] - b[2], b[0] - a[2], 0.0), max(a[1] - b[3], b[1] - a[3], 0.0))

def _union(a: tuple, b: tuple) -> tuple:
  return min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])

def _fit(regions: list) -> list:
  """Two plans never share ground: where the margins of two overlap, each keeps its own side of the middle of the gap between their walls."""
  out = [list(r["bbox"]) for r in regions]
  for i in range(len(out)):
    for j in range(i + 1, len(out)):
      a, b = out[i], out[j]
      ox, oy = min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])
      
      if ox <= 0 or oy <= 0:
        continue
      ci, cj = regions[i]["core_bbox"], regions[j]["core_bbox"]
      if ox <= oy:
        lo, hi = (i, j) if (ci[0] + ci[2]) <= (cj[0] + cj[2]) else (j, i)
        lc, hc = regions[lo]["core_bbox"], regions[hi]["core_bbox"]
        mid = (lc[2] + hc[0]) / 2.0
        out[lo][2], out[hi][0] = min(out[lo][2], max(mid, lc[2])), max(out[hi][0], min(mid, hc[0]))
      else:
        lo, hi = (i, j) if (ci[1] + ci[3]) <= (cj[1] + cj[3]) else (j, i)
        lc, hc = regions[lo]["core_bbox"], regions[hi]["core_bbox"]
        mid = (lc[3] + hc[1]) / 2.0
        out[lo][3], out[hi][1] = min(out[lo][3], max(mid, lc[3])), max(out[hi][1], min(mid, hc[1]))
  return out

def find(index, mm_per_pt: float, deadline: float | None = None, composite: bool = False) -> tuple:
  """The floor plans of a sheet that holds several drawings: ([{key, kind, caption, level_hint, bbox, core_bbox, caption_bbox, wall_m, ...}], stats).

  Nothing is returned for an ordinary one-plan sheet (the whole sheet is read as before): this is for a sheet with two or more floor plan
  captions, or a sheet already known to hold many drawings."""
  every = VW.captions(index.words)
  floor = [i for i, c in enumerate(every) if is_floor_plan(c)]
  if len(floor) < (1 if composite else 2):
    return [], {}
  frames, runs, _ = W.detect_walls(index, mm_per_pt, deadline, False)
  if not runs:
    return [], {}

  link = min(max(LINK_MM / mm_per_pt, LINK_MIN_PT), LINK_MAX_PT)
  groups = group_walls(_wall_lines(frames, runs, SPLIT_LINK * link), link)
  min_pt = MIN_WALL_M * 1000.0 / mm_per_pt
  owner = _owners(groups, every)
  cores: dict = {}
  for ci in floor:
    mine = [gi for gi, o in enumerate(owner) if o == ci and groups[gi]["length_pt"] >= min_pt]
    if mine:
      cores[ci] = max(mine, key=lambda gi: groups[gi]["length_pt"])
  if not cores:
    return [], {}

  members = {ci: [gi] for ci, gi in cores.items()}
  boxes = {ci: groups[gi]["bbox"] for ci, gi in cores.items()}
  reach = min(max(ABSORB_MM / mm_per_pt, ABSORB_MIN_PT), ABSORB_MAX_PT)
  taken = set(cores.values())
  loose = [gi for gi in range(len(groups)) if gi not in taken and (owner[gi] is None or owner[gi] in cores)]
  for gi in loose:
    g = groups[gi]
    best = None
    for ci, core in cores.items():
      if owner[gi] is not None and owner[gi] != ci:
        continue
      if g["length_pt"] > ABSORB_MAX_SHARE * groups[core]["length_pt"]:
        continue
      d = _gap(g["bbox"], groups[core]["bbox"])
      if d <= reach and (best is None or d < best[0]):
        best = (d, ci)
    if best is not None:
      members[best[1]].append(gi)
      boxes[best[1]] = _union(boxes[best[1]], g["bbox"])
  margin = min(max(MARGIN_MM / mm_per_pt, MARGIN_MIN_PT), MARGIN_MAX_PT)
  regions = []
  
  for ci in cores:
    cap = every[ci]
    x0, y0, x1, y1 = boxes[ci]
    regions.append({"kind": "PLAN", "caption": cap["text"], "level_hint": VW.level_of(cap["text"]),
      "core_bbox": [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)],
      "bbox": [round(x0 - margin, 2), round(y0 - margin, 2), round(x1 + margin, 2), round(y1 + margin, 2)],
      "caption_bbox": [round(v, 2) for v in cap["bbox"]], "declared_ratio": cap.get("declared_ratio"), "scale_text": cap.get("scale_text"),
      "plan": True, "structural": False, "foundation": False,
      "wall_m": round(sum(groups[i]["length_pt"] for i in members[ci]) * mm_per_pt / 1000.0, 1), "walls": sum(len(groups[i]["idx"]) for i in members[ci])})
    
  for r, box in zip(regions, _fit(regions)):
    r["bbox"] = [round(v, 2) for v in box]
  regions.sort(key=lambda r: (VW.level_of(r["caption"]) or "", r["core_bbox"][0], r["core_bbox"][1]))
  count: dict = {}
  for r in regions:
    base = f"PLAN:{r['level_hint'] or '-'}:{VW._slug(r['caption'])}"
    count[base] = count.get(base, 0) + 1
    r["key"] = base if count[base] == 1 else f"{base}#{count[base]}"
  total = sum(g["length_pt"] for g in groups) * mm_per_pt / 1000.0
  inside = sum(r["wall_m"] for r in regions)
  used = {gi for gis in members.values() for gi in gis}
  return regions, {"floor_captions": len(floor), "plans": len(regions), "wall_m_on_sheet": round(total, 1), "wall_m_in_plans": round(inside, 1),
    "wall_m_left_out": round(max(total - inside, 0.0), 1), "left_out": _left_out(groups, owner, every, used, mm_per_pt, [r["core_bbox"] for r in regions])}

def _flat(b: tuple) -> bool:
  """A line, not a drawing: a box with no width or no height."""
  return min(b[2] - b[0], b[3] - b[1]) < FLAT_PT

def _covers(box: tuple, plan: list) -> bool:
  """The box lies over a plan that is read (the border of the sheet and the lines that join drawings are one group with everything between them)."""
  w, h = min(box[2], plan[2]) - max(box[0], plan[0]), min(box[3], plan[3]) - max(box[1], plan[1])
  if w <= 0 or h <= 0:
    return False
  area = w * h
  return area >= COVER_SHARE * (plan[2] - plan[0]) * (plan[3] - plan[1]) or area >= 0.5 * (box[2] - box[0]) * (box[3] - box[1])

def _left_out(groups: list, owner: list, caps: list, used: set, mm_per_pt: float, plans: list) -> list:
  """The drawings of the sheet that are not read: [{caption, kind, bbox, wall_m}], the biggest first. Groups named by one caption (an elevation, the
  key plan, the boundary wall) are shown as one box; a big group no caption names is shown on its own; small scraps (symbols) are not listed."""
  by_cap: dict = {}
  loose = []
  
  for gi, g in enumerate(groups):
    if gi in used:
      continue
    if owner[gi] is None:
      if g["length_pt"] * mm_per_pt / 1000.0 >= MIN_WALL_M:
        loose.append({"caption": None, "kind": None, "bbox": g["bbox"], "length_pt": g["length_pt"]})
      continue
  
    cur = by_cap.get(owner[gi])
    by_cap[owner[gi]] = {"caption": caps[owner[gi]]["text"], "kind": caps[owner[gi]]["kind"], "length_pt": g["length_pt"], "bbox": g["bbox"]} if cur is None else {
      **cur, "length_pt": cur["length_pt"] + g["length_pt"], "bbox": _union(cur["bbox"], g["bbox"])}
  out = []
  for e in [*by_cap.values(), *loose]:
    m = e["length_pt"] * mm_per_pt / 1000.0
    if m >= LEFT_OUT_MIN_M and not _flat(e["bbox"]) and not any(_covers(e["bbox"], p) for p in plans):
      out.append({"caption": e["caption"], "kind": e["kind"], "bbox": [round(v, 2) for v in e["bbox"]], "wall_m": round(m, 1)})
  out.sort(key=lambda e: -e["wall_m"])
  return out[:LEFT_OUT_MAX]

def sub_index(index, region: dict) -> VectorIndex:
  """The part of the sheet inside one plan, in the same coordinates as the sheet (so every point found can be drawn on the sheet)."""
  x0, y0, x1, y1 = region["bbox"]
  segs, kinds = array("f"), array("B")
  s = index.segs
  for i in range(len(index.kinds)):
    k = i * 5
    mx, my = (s[k] + s[k + 2]) / 2.0, (s[k + 1] + s[k + 3]) / 2.0
    if x0 <= mx <= x1 and y0 <= my <= y1:
      segs.extend(s[k:k + 5])
      kinds.append(index.kinds[i])
  rings = [r for r in index.rings if x0 <= (r.bbox[0] + r.bbox[2]) / 2.0 <= x1 and y0 <= (r.bbox[1] + r.bbox[3]) / 2.0 <= y1]
  words = [w for w in index.words if x0 <= w.cx <= x1 and y0 <= w.cy <= y1]
  return VectorIndex(segs, kinds, rings, words, (x0, y0, x1, y1))

def view_fact(region: dict) -> dict:
  return {"key": region["key"], "caption": region["caption"], "kind": region["kind"], "level_hint": region.get("level_hint")}
