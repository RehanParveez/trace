from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import hosts as H
from app.modules.drawings_boq.takeoff.extract import config as C

GAP_REACH_MM = H.GAP_NEAR_MM
OTHER_MARK_TOL = 0.025     
OWN_MARK_TOL = 0.12       
MIN_GAP_MM = 500.0

def _gaps(walls: list) -> list:
  """[(point a, point b, width mm)] of the gaps of the brick walls of a plan."""
  out = []
  for w in walls:
    f = w.facts or {}
    if w.category != "WALL" or f.get("enclosure") == "TANK" or w.status == "INVALID":
      continue
    for (a, b), g in zip(f.get("gap_pts") or [], f.get("gaps_mm") or []):
      if g >= MIN_GAP_MM:
        out.append((a, b, float(g)))
  return out

def _role(kind: str | None) -> str | None:
  return H.ROLE_OF.get(kind)

def check(openings: list, walls: list, table: list, mm_per_pt: float) -> dict:
  """Flag the marks that stand beside a gap of another mark's width. table: the schedule's openings [{"mark", "type", "width_mm"}]. Returns {"checked": n, "flagged": n}."""
  gaps = _gaps(walls)
  stats = {"checked": 0, "flagged": 0}
  if not gaps or not table:
    return stats
  for o in openings:
    f = o.facts or {}
    size = f.get("size_schedule_mm")
    role = _role(f.get("opening_kind") or o.category)
    if not size or role is None:
      continue
  
    own = float(size[0])
    cands = [t for t in table if _role(t.get("type")) == role and t.get("mark") != o.tag and t.get("width_mm")]
    hits = []
    for q in (o.geometry or {}).get("points") or []:
      near = [(H._seg_distance(a, b, q) * mm_per_pt, w) for a, b, w in gaps]
      near = [(d, w) for d, w in near if d <= GAP_REACH_MM]
      if not near:
        continue
      stats["checked"] += 1
      d, width = min(near)
      if abs(width - own) <= OWN_MARK_TOL * own:
        continue
    
      like = [t for t in cands if abs(float(t["width_mm"]) - width) <= OTHER_MARK_TOL * width]
      if like:
        best = min(like, key=lambda t: abs(float(t["width_mm"]) - width))
        hits.append({"gap_mm": round(width), "mark": best["mark"], "mark_width_mm": round(float(best["width_mm"]))})
    if hits:
      f["gap_check"] = {"own_width_mm": round(own), "other_mark": hits}
      note = C.note("OPENING_GAP_IS_ANOTHER_MARK", count=len(hits), marks=sorted({h["mark"] for h in hits}))
      note["message"] += " " + "; ".join(f"{o.tag} ({round(own)} mm) stands beside a {h['gap_mm']} mm gap, the width of {h['mark']} ({h['mark_width_mm']} mm)" for h in hits) + "."
      o.notes.append(note)
      stats["flagged"] += 1
  return stats
