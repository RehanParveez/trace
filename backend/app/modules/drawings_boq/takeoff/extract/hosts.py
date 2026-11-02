from __future__ import annotations
import math
from app.modules.drawings_boq.takeoff.extract import config as C

HOST_MAX_MM = 1400.0
GAP_BONUS_MM = 450.0
GAP_NEAR_MM = 700.0
SEAT_SLACK_MM = 50.0
WIDTH_TOL = 0.03
ROLE_OF = {"DOOR": "DOOR", "WINDOW": "WINDOW", "VENTILATOR": "WINDOW"}

def _seg_distance(p0, p1, q) -> float:
  vx, vy = p1[0] - p0[0], p1[1] - p0[1]
  ln2 = vx * vx + vy * vy
  if ln2 <= 0:
    return math.hypot(q[0] - p0[0], q[1] - p0[1])
  s = max(0.0, min(1.0, ((q[0] - p0[0]) * vx + (q[1] - p0[1]) * vy) / ln2))
  return math.hypot(q[0] - (p0[0] + s * vx), q[1] - (p0[1] + s * vy))


def reach(wall_pts: list, gap_pts: list, q, mm_per_pt: float, reach_mm: float = HOST_MAX_MM) -> tuple | None:
  d = _seg_distance(wall_pts[0], wall_pts[1], q) * mm_per_pt
  if d > reach_mm:
    return None
  for a, b in gap_pts or []:
    if _seg_distance(a, b, q) * mm_per_pt <= GAP_NEAR_MM:
      return d - GAP_BONUS_MM, d, True
  return d, d, False

def score(wall_pts: list, gap_pts: list, q, mm_per_pt: float, reach_mm: float = HOST_MAX_MM) -> float | None:
  r = reach(wall_pts, gap_pts, q, mm_per_pt, reach_mm)
  return None if r is None else r[0]

def _half_thickness(w) -> float:
  f, p = w.facts or {}, w.params or {}
  return float(f.get("thickness_used_mm") or p.get("thickness_mm") or f.get("thickness_mm") or 0.0) / 2.0

def _unclaimed_gaps(hosts: dict, points: list, mm_per_pt: float) -> list:
  out = []
  for key, (_w, _p0, _p1, gaps) in hosts.items():
    for a, b in gaps:
      if not any(_seg_distance(a, b, q) * mm_per_pt <= GAP_NEAR_MM for q in points):
        out.append((key, math.hypot(a[0] - b[0], a[1] - b[1]) * mm_per_pt))
  return out

def _pair_by_width(placed: list, hosts: dict, points: list, mm_per_pt: float) -> int:
  loose = [p for p in placed if not p["confirmed"] and p["key"] is not None]
  gaps = _unclaimed_gaps(hosts, points, mm_per_pt)
  paired = 0
  for p in loose:
    width = p["size"][0]
    gap_hits = [g for g in gaps if abs(g[1] - width) <= WIDTH_TOL * width]
    mark_hits = [x for x in loose if abs(x["size"][0] - width) <= WIDTH_TOL * width]
    if len(gap_hits) == 1 and len(mark_hits) == 1 and gap_hits[0][0] != p["key"]:
      p.update({"key": gap_hits[0][0], "route": "GAP_WIDTH", "confirmed": True, "gap_width_mm": round(gap_hits[0][1], 1)})
      paired += 1
  return paired

def _record(p: dict) -> dict:
  return {k: (round(v, 1) if isinstance(v, float) else v) for k, v in p.items() if k in ("route", "distance_mm", "runner_up_mm", "confirmed", "gap_width_mm", "nearest_mm") and v is not None}

def assign(walls: list, openings: list, mm_per_pt: float) -> dict:
  hosts = {}
  for w in walls:
    pts = (w.geometry or {}).get("points") or []
    if len(pts) >= 2 and w.category == "WALL":
      hosts[w.key] = (w, pts[0], pts[1], (w.facts or {}).get("gap_pts") or [])
  found: dict = {k: {} for k in hosts}
  placed: list = []
  points: list = []
  for o in openings:
    size = (o.facts or {}).get("size_schedule_mm") or (o.facts or {}).get("size_drawn_mm")
    kind = (o.facts or {}).get("opening_kind") or o.category
    role = ROLE_OF.get(kind)
    if not size or role is None:
      continue
    for q in (o.geometry or {}).get("points") or []:
      points.append(q)
      ranked = []
      for key, (w, p0, p1, gaps) in hosts.items():
        r = reach([p0, p1], gaps, q, mm_per_pt)
        if r is not None:
          ranked.append((r[0], r[1], r[2], key))
      ranked.sort(key=lambda r: r[0])
      near = min((_seg_distance(p0, p1, q) * mm_per_pt for (_w, p0, p1, _g) in hosts.values()), default=None)
      if not ranked:
        placed.append({"o": o, "q": tuple(q), "key": None, "size": size, "role": role, "confirmed": False, "route": "NONE", "nearest_mm": near})
        continue
      sc, d, gapped, key = ranked[0]
      seated = gapped or d <= _half_thickness(hosts[key][0]) + SEAT_SLACK_MM
      placed.append({"o": o, "q": tuple(q), "key": key, "size": size, "role": role, "confirmed": seated, "route": "GAP" if gapped else "NEAREST", "distance_mm": d, "runner_up_mm": ranked[1][1] if len(ranked) > 1 else None})
  paired = _pair_by_width(placed, hosts, points, mm_per_pt)
  
  where: dict = {}
  n_ok = n_lost = 0
  for p in placed:
    o = p["o"]
    if p["key"] is None:
      n_lost += 1
      o.facts["host"] = _record(p)
      o.facts["host_issue"] = "OPENING_NO_HOST"
      o.notes.append(C.note("OPENING_NO_HOST", reach_mm=HOST_MAX_MM, nearest_mm=round(p["nearest_mm"], 1) if p["nearest_mm"] is not None else None))
      continue
    n_ok += 1
    
    where.setdefault(o.tag or "", []).append((p["q"], p["key"]))
    group = (p["role"], round(p["size"][0], 1), round(p["size"][1], 1), o.tag or "")
    found[p["key"]][group] = found[p["key"]].get(group, 0) + 1
    o.facts["host"] = {"wall": p["key"], **_record(p)}
    if p["route"] == "GAP_WIDTH":
      o.facts["host_issue"] = "OPENING_HOST_BY_WIDTH"
      o.notes.append(C.note("OPENING_HOST_BY_WIDTH", gap_mm=p["gap_width_mm"], width_mm=round(p["size"][0], 1)))
    elif not p["confirmed"]:
      o.facts["host_issue"] = "OPENING_HOST_UNCONFIRMED"
      o.notes.append(C.note("OPENING_HOST_UNCONFIRMED", distance_mm=round(p["distance_mm"], 1), runner_up_mm=round(p["runner_up_mm"], 1) if p["runner_up_mm"] is not None else None))
      
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
  audit = {"seated": sum(1 for p in placed if p["key"] is not None and p["confirmed"] and p["route"] != "GAP_WIDTH"), "by_width": paired,
    "unconfirmed": [{"tag": p["o"].tag, **_record(p)} for p in placed if p["key"] is not None and not p["confirmed"]], "none": [{"tag": p["o"].tag, **_record(p)} for p in placed if p["key"] is None]}
  return {"assigned": n_ok, "unassigned": n_lost, "by_wall": by_wall, "by_point": where, "audit": audit}
