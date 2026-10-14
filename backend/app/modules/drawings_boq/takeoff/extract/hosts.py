from __future__ import annotations
import math

HOST_MAX_MM = 1400.0
GAP_BONUS_MM = 450.0
GAP_NEAR_MM = 700.0
ROLE_OF = {"DOOR": "DOOR", "WINDOW": "WINDOW", "VENTILATOR": "WINDOW"}

def _seg_distance(p0, p1, q) -> float:
  vx, vy = p1[0] - p0[0], p1[1] - p0[1]
  ln2 = vx * vx + vy * vy
  if ln2 <= 0:
    return math.hypot(q[0] - p0[0], q[1] - p0[1])
  s = max(0.0, min(1.0, ((q[0] - p0[0]) * vx + (q[1] - p0[1]) * vy) / ln2))
  return math.hypot(q[0] - (p0[0] + s * vx), q[1] - (p0[1] + s * vy))

def score(wall_pts: list, gap_pts: list, q, mm_per_pt: float) -> float | None:
  """Distance in mm from a mark to a wall (smaller is a better host), or None when the wall is too far to hold the opening."""
  d = _seg_distance(wall_pts[0], wall_pts[1], q) * mm_per_pt
  
  if d > HOST_MAX_MM:
    return None
  best = d
  for a, b in gap_pts or []:
    if _seg_distance(a, b, q) * mm_per_pt <= GAP_NEAR_MM:
      best = d - GAP_BONUS_MM
      break
  return best

def assign(walls: list, openings: list, mm_per_pt: float) -> dict:
  """walls: wall candidates. openings: door / window / ventilator candidates.
  Returns {"assigned": n, "unassigned": n, "by_wall": {wall key: [opening dicts]}} and fills each wall's params["openings"] and facts["openings"]."""
  hosts = {}
  for w in walls:
    pts = (w.geometry or {}).get("points") or []
    if len(pts) >= 2 and w.category == "WALL":
      hosts[w.key] = (w, pts[0], pts[1], (w.facts or {}).get("gap_pts") or [])
  found: dict = {k: {} for k in hosts}
  n_ok = n_lost = 0
  
  for o in openings:
    size = (o.facts or {}).get("size_schedule_mm")
    kind = (o.facts or {}).get("opening_kind") or o.category
    role = ROLE_OF.get(kind)
    if not size or role is None:
      continue
    for q in (o.geometry or {}).get("points") or []:
      best, best_key = None, None
      for key, (w, p0, p1, gaps) in hosts.items():
        sc = score([p0, p1], gaps, q, mm_per_pt)
        if sc is not None and (best is None or sc < best):
          best, best_key = sc, key
      if best_key is None:
        n_lost += 1
        continue
      n_ok += 1
      slot = found[best_key].setdefault((role, round(size[0], 1), round(size[1], 1), o.tag or ""), 0)
      found[best_key][(role, round(size[0], 1), round(size[1], 1), o.tag or "")] = slot + 1
  by_wall: dict = {}
  
  for key, groups in found.items():
    if not groups:
      continue
    w = hosts[key][0]
    ops = [{"role": r, "width_mm": wd, "height_mm": ht, "nos": n, "label": tag or None} for (r, wd, ht, tag), n in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][3]))]
    w.params["openings"] = ops
    area = sum(o["width_mm"] * o["height_mm"] * o["nos"] for o in ops) / 1e6
    w.facts["openings"] = {"count": sum(o["nos"] for o in ops), "area_m2": round(area, 3), "marks": sorted({o["label"] for o in ops if o["label"]})}
    by_wall[key] = ops
  return {"assigned": n_ok, "unassigned": n_lost, "by_wall": by_wall}
