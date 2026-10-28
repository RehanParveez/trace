from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import hosts as H
import math

LABEL_HOST_REACH_MM = 1500.0    
GAP_WIDTH_TOL = 0.15             
SAME_LABEL_MM = 300.0            
SYMBOL_NEAR_REL, SYMBOL_NEAR_MM = 0.75, 150.0   

def _rows(walls: list) -> list:
  out = []
  for w in walls or []:
    f = w.facts or {}
    pts = (w.geometry or {}).get("points") or []
    if w.category != "WALL" or f.get("enclosure") == "TANK" or w.status == "INVALID" or len(pts) < 2:
      continue
    out.append((w, pts[0], pts[1], [((a, b), float(g)) for (a, b), g in zip(f.get("gap_pts") or [], f.get("gaps_mm") or [])]))
  return out

def _project(p0, p1, q) -> tuple:
  vx, vy = p1[0] - p0[0], p1[1] - p0[1]
  l2 = vx * vx + vy * vy
  s = 0.0 if l2 <= 0.0 else max(0.0, min(1.0, ((q[0] - p0[0]) * vx + (q[1] - p0[1]) * vy) / l2))
  return p0[0] + s * vx, p0[1] + s * vy

def _place(lab: dict, rows: list, mm_per_pt: float) -> dict | None:
  q = (float(lab["x"]), float(lab["y"]))
  near = []
  for row in rows:
    w, p0, p1, gaps = row
    sc = H.score([p0, p1], [g for g, _ in gaps], q, mm_per_pt, reach_mm=LABEL_HOST_REACH_MM)
    if sc is not None:
      near.append((sc, row))
      
  if not near:
    return None
  want = float(lab["w_mm"])
  best = None
  for _sc, (w, p0, p1, gaps) in near:
    for gi, ((a, b), g) in enumerate(gaps):
      if abs(g - want) > GAP_WIDTH_TOL * want:
        continue
      d = H._seg_distance(a, b, q) * mm_per_pt
      if d <= LABEL_HOST_REACH_MM and (best is None or d < best[0]):
        best = (d, w, gi, ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0), g)
  if best is not None:
    return {"wall": best[1], "gap": best[2], "gap_mm": best[4], "point": best[3]}
  sc, (w, p0, p1, _g) = min(near, key=lambda t: t[0])
  return {"wall": w, "gap": None, "gap_mm": None, "point": _project(p0, p1, q)}

def make(labels: list, walls: list, symbols: dict, mm_per_pt: float) -> dict:
  rows = _rows(walls)
  out: dict = {"DOOR": [], "WINDOW": []}
  stats = {"made": {"DOOR": 0, "WINDOW": 0}, "in_gap": 0, "no_gap": 0, "no_wall": 0, "joined_symbol": 0, "duplicates": 0}
  taken: set = set()
  placed: list = []
  
  for lab in labels or []:
    if lab.get("paired") or lab.get("opened"):
      continue
    kind = lab["kind"]
    spot = _place(lab, rows, mm_per_pt) if rows else None
    if spot is None:
      stats["no_wall"] += 1
      continue
    w = spot["wall"]
    if spot["gap"] is not None:
      slot = (kind, w.key, spot["gap"])
      if slot in taken:
        stats["duplicates"] += 1
        lab["opened"] = True
        continue
    
      mate = None
      reach = (SYMBOL_NEAR_REL * spot["gap_mm"] + SYMBOL_NEAR_MM) / mm_per_pt
      for s in symbols.get(kind) or []:
        if math.hypot(s["x"] - spot["point"][0], s["y"] - spot["point"][1]) <= reach:
          mate = s
          break
      if mate is not None:
        if not mate.get("label"):
          mate["label"] = lab
          lab["paired"] = True
          stats["joined_symbol"] += 1
        else:
          stats["duplicates"] += 1
          lab["opened"] = True
        taken.add(slot)
        continue
      taken.add(slot)
    else:
      if any(p[0] == kind and p[1] == w.key and p[2] == lab["text"] and math.hypot(p[3] - lab["x"], p[4] - lab["y"]) * mm_per_pt <= SAME_LABEL_MM for p in placed):
        stats["duplicates"] += 1
        lab["opened"] = True
        continue
    
      placed.append((kind, w.key, lab["text"], float(lab["x"]), float(lab["y"])))
    lab["opened"] = True
    out[kind].append({"x": float(spot["point"][0]), "y": float(spot["point"][1]), "width_mm": float(lab["w_mm"]), "leaves": 1, "by": "LABEL", "label": lab,
      "gap": spot["gap"] is not None, "wall_key": w.key, "ventilator": bool(lab.get("ventilator"))})
    stats["made"][kind] += 1
    stats["in_gap" if spot["gap"] is not None else "no_gap"] += 1
  out["stats"] = stats
  return out
