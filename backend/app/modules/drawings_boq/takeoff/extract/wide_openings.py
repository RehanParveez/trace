from __future__ import annotations
import hashlib
from app.modules.drawings_boq.takeoff.extract import config as C
import math
from app.modules.drawings_boq.takeoff.prep import lintels as LT

WIDE_MIN_MM = C.WALL_GAP_MAX_MM
MATCH_TOL = 0.12
SPAN_ROUND_MM = 50.0
MARK_REACH_MM = 600.0
SAME_OPENING_MM = 400.0

def _key(*parts) -> str:
  return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:16]

def unmarked_gaps(walls: list) -> list:
  """[{"span_mm", "wall", "points"}]: the gaps of the brick walls of a plan that are wider than WIDE_MIN_MM and that no marked opening of the same wall
  accounts for (an opening accounts for a gap when its width is within MATCH_TOL of the gap, or the gap is an opening plus its frame)."""
  out = []
  for w in walls:
    f = w.facts or {}
    if w.category != "WALL" or f.get("construction") == "RCC" or f.get("enclosure") == "TANK" or w.status == "INVALID":
      continue
  
    gaps, pts = f.get("gaps_mm") or [], f.get("gap_pts") or []
    ops = [o for o in ((w.params or {}).get("openings") or []) for _ in range(int(o.get("nos") or 1))]
    left = list(ops)
    for i, g in enumerate(gaps):
      if g < WIDE_MIN_MM:
        continue
      hit = next((o for o in left if abs(float(o["width_mm"]) - g) <= MATCH_TOL * g), None)
      
      if hit is not None:
        left.remove(hit)
        continue
      mid = None
      if i < len(pts):
        a, b = pts[i]
        mid = [round((a[0] + b[0]) / 2.0, 4), round((a[1] + b[1]) / 2.0, 4)]
      out.append({"span_mm": float(g), "wall": w, "point": mid})
  return out

def _near_mark(point, span_mm: float, marks: list, mm_per_pt: float) -> bool:
  """True when a door or window mark of the plan sits in the opening (then the lintel comes from that mark)."""
  reach = (span_mm / 2.0 + MARK_REACH_MM) / mm_per_pt
  return any(math.hypot(point[0] - q[0], point[1] - q[1]) <= reach for q in marks)

def _dashed(dashed: list, found: list, marks: list, mm_per_pt: float) -> list:
  """The dashed openings that no marked opening sits in and that are not the same opening as a gap already found in a wall."""
  out = []
  for d in dashed:
    mid = ((d["p0"][0] + d["p1"][0]) / 2.0, (d["p0"][1] + d["p1"][1]) / 2.0)
    if _near_mark(mid, d["span_mm"], marks, mm_per_pt):
      continue
    if any(g["point"] and math.hypot(mid[0] - g["point"][0], mid[1] - g["point"][1]) * mm_per_pt <= SAME_OPENING_MM for g in found):
      continue
    out.append({"span_mm": float(d["span_mm"]), "wall": None, "point": [round(mid[0], 4), round(mid[1], 4)], "t_mm": d["t_mm"], "dashed": True})
  return out

THIN_WALL_MM = 160.0

def _thickness(g) -> float:
  if g["wall"] is not None:
    return float((g["wall"].params or {}).get("thickness_mm") or 0.0)
  return float(g.get("t_mm") or 0.0)

def candidates(walls: list, table: list, ctx: dict, Candidate, finish, inch_text, fmt_mm, dashed: list | None = None, marks: list | None = None,
  mm_per_pt: float = 1.0) -> list:
  gaps = unmarked_gaps(walls)
  gaps += _dashed(dashed or [], gaps, marks or [], mm_per_pt)
  groups: dict = {}
  
  for g in gaps:
    groups.setdefault(round(g["span_mm"] / SPAN_ROUND_MM) * SPAN_ROUND_MM, []).append(g)
    
  out = []
  bearing = C.LINTEL_BEARING_MM
  for span, gs in sorted(groups.items(), reverse=True):
    sec = LT.section_for(table, span) if table else None
    thin = sum(1 for g in gs if (float((g["wall"].params or {}).get("thickness_mm") or 0) if g["wall"] is not None else float(g.get("t_mm") or 999.0)) < THIN_WALL_MM)
    thin_ids = {id(g) for g in gs if 0.0 < _thickness(g) < THIN_WALL_MM} if sec else set()
    for part, members in (("WALL", [g for g in gs if id(g) not in thin_ids]), ("THIN", [g for g in gs if id(g) in thin_ids])):
      if not members:
        continue
      thin_part = part == "THIN"
      notes = [C.note("LINTEL_OVER_UNMARKED_OPENING", span_mm=round(span), count=len(members)), C.note("LINTEL_BEARING_ASSUMED", bearing_mm=bearing)]
      params: dict = {"dims_basis": "SPECIFIED"}
      missing: list = []
      facts = {"opening_tag": None, "opening_kind": "UNMARKED", "span_mm": round(span, 1), "bearing_mm": bearing, "wall_keys": [g["wall"].key for g in members if g["wall"] is not None],
        "dashed": sum(1 for g in members if g.get("dashed")), "split": {"part": part, "in_thin_wall": len(thin_ids), "other": len(gs) - len(thin_ids)}}
      base = 0.6
      
      if sec:
        width, depth = LT.section_in(sec, max(_thickness(g) for g in members) if thin_part else None)
        params["length_mm"], params["width_mm"], params["depth_mm"] = round(span + 2.0 * bearing, 1), width, depth
        facts["section_mm"] = [width, depth]
        facts["table_section_mm"] = [sec["width_mm"], sec["depth_mm"]]
        facts["table_span_max_mm"] = sec["span_max_mm"]
        notes.append(C.note("LINTEL_SECTION_FROM_TABLE"))
        if thin_part:
          notes.append(C.note("LINTEL_WIDTH_FROM_WALL", wall_mm=width, table_mm=sec["width_mm"], count=len(members)))
        if sec.get("steel"):
          params["steel"] = dict(sec["steel"])
          facts["steel_text"] = LT.steel_text(sec["steel"])
          notes.append(C.note("LINTEL_STEEL_FROM_TABLE"))
        label = f"Lintel over unmarked opening ×{len(members)} · {inch_text(width)}×{inch_text(depth)} · {fmt_mm(params['length_mm'])} mm long" + (f" · in {inch_text(width)} wall" if thin_part else "")
      else:
        missing.append("size")
        notes.append(C.note("LINTEL_SPAN_ABOVE_TABLE"))
        base *= 0.7
        label = f"Lintel over unmarked opening ×{len(members)} · span {fmt_mm(span)} mm"
        if thin:
          notes.append(C.note("LINTEL_IN_THIN_WALL", count=thin))
      pts = [g["point"] for g in members if g["point"]]
      work_item, mode, kind = C.SUGGESTIONS["LINTEL"]
      tag = f"L-OPEN ({inch_text(params['width_mm'])} wall)" if thin_part else "L-OPEN"
      cand = Candidate(key=_key("LINTEL", "WIDE", *(["THIN"] if thin_part else []), round(span), *sorted(g["wall"].key if g["wall"] is not None else str(g["point"]) for g in members)), category="LINTEL", kind=kind, quantity_mode=mode, label=label,
        tag=tag, geometry={"points": pts}, params=params, missing=missing, work_item=work_item, status="VALID", confidence=0.0, facts=facts, notes=notes,
        source="VECTOR_SNAP", count=len(members))
      out.append(finish(cand, ctx, base))
  return out
