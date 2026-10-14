from __future__ import annotations
from dataclasses import dataclass, field
import hashlib
import re
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.extract import members as M
from app.modules.drawings_boq.takeoff.extract import rooms as R
from app.modules.drawings_boq.takeoff.extract.sheetkind import sheet_kind
from app.modules.drawings_boq.takeoff.extract import walls as W
from app.modules.drawings_boq.takeoff.extract import rcc as RC
from app.modules.drawings_boq.takeoff.extract import hosts as H
from app.modules.drawings_boq.takeoff.prep import census
from app.modules.drawings_boq.takeoff.prep import schedules as S
from app.modules.drawings_boq.takeoff.prep.texts import build_lines, find_units_hint
import time

@dataclass
class Candidate:
  key: str
  category: str
  kind: str
  quantity_mode: str
  label: str
  tag: str | None
  geometry: dict
  params: dict
  missing: list
  work_item: str | None
  status: str
  confidence: float
  facts: dict
  notes: list
  source: str
  count: int

@dataclass
class Extraction:
  candidates: list = field(default_factory=list)
  unmapped_tags: list = field(default_factory=list)
  stats: dict = field(default_factory=dict)
  notes: list = field(default_factory=list)

_FEET_INCH = re.compile(r"\d+\s*['’′]\s*-\s*\d+")

def _key(*parts) -> str:
  return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:24]

def _status(notes: list) -> str:
  sev = {n["severity"] for n in notes}
  return "INVALID" if "error" in sev else "WARNING" if "warning" in sev else "VALID"

def _fmt_mm(v: float) -> str:
  return str(int(round(v))) if abs(v - round(v)) < 0.05 else f"{v:.1f}"

def _finish(c: Candidate, ctx: dict, base: float) -> Candidate:
  if ctx.get("scale_unverified"):
    c.notes.append(C.note("SCALE_UNVERIFIED"))
  c.status = _status(c.notes)
  c.confidence = round(max(0.0, min(1.0, base * ctx["cal_factor"] * ctx["content_factor"])), 4)
  return c

def _tag_candidates(index, words, shapes, f, hint, heights, ctx, openings=None) -> list:
  groups = M.tag_members(words, shapes, f, hint, openings)
  out = []
  clusters: dict = {}
  for g in groups:
    if g["category"] in ("COLUMN", "FOOTING") and "drawn_mm" in g:
      a, b = g["drawn_mm"]
      clusters.setdefault((g["category"], round(a / 10), round(b / 10)), []).append(g)
  tags_in = {}
  for (cat, ra, rb), gs in clusters.items():
    a, b = ra * 10.0, rb * 10.0
    drawn = [s for s in shapes if s["fill"] and abs(s["a"] - a) <= 0.05 * a + 5 and abs(s["b"] - b) <= 0.05 * b + 5]
    for g in gs:
      tags_in[g["tag"]] = (sum(x["count"] for x in gs), len(drawn))
  for g in groups:
    cat, tag = g["category"], g["tag"]
    work_item, mode, kind = C.SUGGESTIONS[cat]
    notes: list = []
    facts: dict = {"tag": tag, "count": g["count"], "schedule_rows": g["schedule_rows"]}
    params: dict = {}
    missing: list = []
    base = 0.9
    used = None
    
    if cat in ("COLUMN", "FOOTING"):
      drawn, sched = g.get("drawn_mm"), g.get("schedule_mm")
      facts["matched_shapes"] = g["matched"]
      if drawn:
        facts["size_drawn_mm"] = list(drawn)
      if sched:
        facts["size_schedule_mm"] = list(sched)
      if sched:
        used = sched
        notes.append(C.note("SIZE_FROM_SCHEDULE"))
        if drawn and (abs(sched[0] - drawn[0]) > C.SIZE_TOL * drawn[0] or abs(sched[1] - drawn[1]) > C.SIZE_TOL * drawn[1]):
          notes.append(C.note("SIZE_DIFFERS_FROM_SCHEDULE", drawn_mm=list(drawn), schedule_mm=list(sched)))
          base *= 0.9
      elif drawn:
        used = drawn
      else:
        notes.append(C.note("SIZE_NOT_FOUND"))
        base *= 0.8
      if drawn and g.get("spread", 0) > C.SIZE_TOL:
        notes.append(C.note("SIZE_VARIES"))
        base *= 0.9
        
      if used:
        facts["size_used_mm"] = [used[0], used[1]]
        params["length_mm"], params["width_mm"] = used[0], used[1]
      if tag in tags_in:
        n_tags, n_drawn = tags_in[tag]
        facts["same_size_marks"], facts["same_size_drawn"] = n_tags, n_drawn
        if n_drawn > n_tags:
          notes.append(C.note("UNTAGGED_SAME_SIZE", marks=n_tags, drawn=n_drawn))
          base *= 0.9
        elif n_drawn and n_drawn < n_tags:
          notes.append(C.note("COUNT_DIFFERS_FROM_DRAWN", marks=n_tags, drawn=n_drawn))
          base *= 0.9
      dim = "depth_mm"
      h = heights.get("COLUMN") if cat == "COLUMN" else None
      
      if h:
        params[dim] = h["mm"]
        notes.append(C.note("HEIGHT_FROM_NOTE", text=h["text"]))
      else:
        missing.append("height_mm" if cat == "COLUMN" else "depth_mm")
      params["dims_basis"] = "SPECIFIED" if (sched or h) else "DRAWN"
      if not used:
        missing.insert(0, "size")
      label = f"{tag} ×{g['count']}" + (f" · {_fmt_mm(used[0])}×{_fmt_mm(used[1])} mm" if used else "")
    elif cat == "BEAM":
      notes.append(C.note("BEAM_LENGTH_NOT_READ"))
      work_item = None
      sched = g.get("schedule_mm")
      if sched:
        facts["size_schedule_mm"] = list(sched)
        notes.append(C.note("SIZE_FROM_SCHEDULE"))
      label = f"{tag} ×{g['count']}" + (f" · {_fmt_mm(sched[0])}×{_fmt_mm(sched[1])} mm" if sched else "")
    else:
      sched = g.get("schedule_mm")
      kind_of = g.get("opening_kind") or cat
      facts["opening_kind"] = kind_of
      if sched:
        facts["size_schedule_mm"] = list(sched)
        facts["area_each_m2"] = round(sched[0] * sched[1] / 1e6, 3)
        notes.append(C.note("SIZE_FROM_SCHEDULE"))
        
      elif g.get("schedule_missing"):
        notes.append(C.note("SCHEDULE_MARK_NOT_FOUND"))
        base *= 0.9
      label = f"{tag}{' ventilator' if kind_of == 'VENTILATOR' else ''} ×{g['count']}" + (f" · {_fmt_mm(sched[0])}×{_fmt_mm(sched[1])} mm" if sched else "")
    cand = Candidate(key=_key(cat, tag), category=cat, kind=kind, quantity_mode=mode, label=label, tag=tag,
      geometry={"points": g["points"]}, params=params, missing=missing, work_item=work_item, status="VALID", confidence=0.0,
      facts=facts, notes=notes, source="TAG_SCAN", count=g["count"])
    out.append(_finish(cand, ctx, base))
  return out

def _is_imperial(words) -> bool:
  """A drawing dimensioned in feet and inches: several words such as 30'-0" or 13'-6"."""
  n = 0
  for w in words:
    if _FEET_INCH.search(w.text or ""):
      n += 1
      if n >= 4:
        return True
  return False

def _mark_tanks(words, walls: list, f: float) -> int:
  """Walls that close in a labelled tank (O.H.W.T, U.G.W.Tank, septic tank) get facts["enclosure"] = "TANK"."""
  marked = 0
  for w in words:
    if not C.TANK_LABEL.search(w.text or ""):
      continue
    near = []
    for c in walls:
      if c.facts.get("enclosure"):
        continue
      pts = (c.geometry or {}).get("points") or []
      if len(pts) < 2:
        continue
      if H._seg_distance(pts[0], pts[1], (w.cx, w.cy)) * f <= C.TANK_REACH_MM:
        near.append(c)
    if len(near) < 3:
      continue
    xs = [p[0] for c in near for p in c.geometry["points"]]
    ys = [p[1] for c in near for p in c.geometry["points"]]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    if not (x0 <= w.cx <= x1 and y0 <= w.cy <= y1) or max(x1 - x0, y1 - y0) * f > C.TANK_MAX_MM:
      continue
    for c in near:
      c.facts["enclosure"] = "TANK"
      c.notes.append(C.note("TANK_WALL"))
      c.status = _status(c.notes)
      marked += 1
  return marked

def _wall_candidates(index, f, heights, ctx, deadline, imperial: bool = False) -> tuple:
  frames, runs, stats = W.detect_walls(index, f, deadline)
  rcc = RC.rcc_runs(index.rings, f)
  stats["rcc_runs"] = len(rcc)
  stats["dropped_stubs"] = 0
  stats["dropped_on_rcc"] = 0
  extra = W.bridge_ends(runs, frames, f)
  stats["bridged_ends"] = sum(1 for v in extra.values() for x in v if x > 0.0)
  out = []
  for r in runs:
    fr = frames[r.peak]
    add0, add1 = extra.get(id(r), (0.0, 0.0))
    p0, p1 = fr.pt(r.s0 - r.ext0 - add0, r.dc), fr.pt(r.s1 + r.ext1 + add1, r.dc)
    t_mm = r.t_pt * f
    std, use_t = W.snap_thickness(t_mm, imperial)
    cc_m = ((r.s1 + r.ext1 + add1) - (r.s0 - r.ext0 - add0)) * f / 1000.0
    clear_m = r.clear_pt * f / 1000.0
    if std is None and cc_m * 1000.0 < C.WALL_STUB_MAX_MM:
      stats["dropped_stubs"] += 1
      continue
  
    if rcc and RC.covered_by(rcc, p0, p1, f):
      stats["dropped_on_rcc"] += 1
      continue
    spans = list(r.gaps)
    if add0 > 0.0:
      spans.append((r.s0 - r.ext0 - add0, r.s0 - r.ext0))
    if add1 > 0.0:
      spans.append((r.s1 + r.ext1, r.s1 + r.ext1 + add1))
    gaps = [round((b - a) * f) for a, b in spans]
    notes: list = []
    base = 0.8
    if std is None:
      notes.append(C.note("THICKNESS_OFF_STANDARD", drawn_mm=round(t_mm, 1)))
      base *= 0.85
      
    if gaps:
      notes.append(C.note("WALL_OPENINGS_INCLUDED", gaps_mm=gaps, total_mm=sum(gaps)))
      base *= 0.95
    if r.end0 == "FREE" and r.end1 == "FREE":
      base *= 0.9
    params = {"thickness_mm": use_t}
    missing = []
    h = heights.get("WALL")
    if h:
      params["height_mm"] = h["mm"]
      notes.append(C.note("HEIGHT_FROM_NOTE", text=h["text"]))
      
    else:
      missing.append("height_mm")
    params["dims_basis"] = "SPECIFIED" if h else "DRAWN"
    if cc_m * 1000.0 <= 0:
      continue
    facts = {"thickness_mm": round(t_mm, 1), "thickness_standard_mm": std, "thickness_used_mm": use_t, "length_cc_m": round(cc_m, 3),
      "length_clear_m": round(clear_m, 3), "gaps_mm": gaps, "ends": [r.end0, r.end1], "method": "CENTRE_LINE",
      "gap_pts": [[[round(x, 3) for x in fr.pt(a, r.dc)], [round(x, 3) for x in fr.pt(b, r.dc)]] for a, b in spans]}
    
    if add0 > 0.0 or add1 > 0.0:
      facts["bridged_mm"] = [round(add0 * f), round(add1 * f)]
      notes.append(C.note("WALL_BRIDGED"))
    key = _key("WALL", round(p0[0] / 2), round(p0[1] / 2), round(p1[0] / 2), round(p1[1] / 2))
    work_item, mode, kind = C.SUGGESTIONS["WALL"]
    
    cand = Candidate(key=key, category="WALL", kind=kind, quantity_mode=mode, label=f"Wall {_fmt_mm(use_t)} mm · {cc_m:.2f} m", tag=None,
      geometry={"points": [[round(p0[0], 4), round(p0[1], 4)], [round(p1[0], 4), round(p1[1], 4)]], "closed": False}, params=params,
      missing=missing, work_item=work_item, status="VALID", confidence=0.0, facts=facts, notes=notes, source="VECTOR_SNAP", count=1)
    out.append(_finish(cand, ctx, base))
  for rc in rcc:
    t_mm = rc["t_mm"]
    std, use_t = W.snap_thickness(t_mm, imperial)
    cc_m = rc["length_mm"] / 1000.0
    notes = [C.note("RCC_WALL_FROM_FILL")]
    if rc["gaps_mm"]:
      notes.append(C.note("WALL_OPENINGS_INCLUDED", gaps_mm=rc["gaps_mm"], total_mm=sum(rc["gaps_mm"])))
    h = heights.get("WALL")
    params = {"thickness_mm": use_t, "dims_basis": "SPECIFIED" if h else "DRAWN"}
    missing = []
    
    if h:
      params["height_mm"] = h["mm"]
      notes.append(C.note("HEIGHT_FROM_NOTE", text=h["text"]))
    else:
      missing.append("height_mm")
    facts = {"thickness_mm": round(t_mm, 1), "thickness_standard_mm": std, "thickness_used_mm": use_t, "length_cc_m": round(cc_m, 3),
      "length_clear_m": round(rc["clear_mm"] / 1000.0, 3), "gaps_mm": rc["gaps_mm"], "ends": ["FREE", "FREE"], "method": "CENTRE_LINE",
      "construction": "RCC", "gap_pts": [[[round(x, 3) for x in a], [round(x, 3) for x in b]] for a, b in rc["gap_pts"]]}
    key = _key("WALL", round(rc["p0"][0] / 2), round(rc["p0"][1] / 2), round(rc["p1"][0] / 2), round(rc["p1"][1] / 2))
    _, mode, kind = C.SUGGESTIONS["WALL"]
    cand = Candidate(key=key, category="WALL", kind=kind, quantity_mode=mode, label=f"RCC wall {_fmt_mm(use_t)} mm · {cc_m:.2f} m", tag=None,
      geometry={"points": [[round(rc["p0"][0], 4), round(rc["p0"][1], 4)], [round(rc["p1"][0], 4), round(rc["p1"][1], 4)]], "closed": False},
      params=params, missing=missing, work_item="CON-RCC", status="VALID", confidence=0.0, facts=facts, notes=notes, source="VECTOR_SNAP", count=1)
    out.append(_finish(cand, ctx, 0.75))
  stats["rcc_walls"] = len(rcc)
  out.sort(key=lambda c: (c.facts.get("construction") == "RCC", -c.facts["thickness_used_mm"], -c.facts["length_cc_m"]))
  return frames, runs, out, stats

def _room_candidates(index, frames, runs, lines, f, hint, ctx) -> list:
  faces = R.wall_faces(runs, frames)
  k = f * f / 1e6
  faces = [p for p in faces if C.ROOM_MIN_M2 <= p.area * k <= C.ROOM_MAX_M2]
  names, sizes = R.labels(lines, hint)
  pairs = [p for p in R.pair_labels(names, sizes, f) if R.plausible_room(p)]
  items = [(p, "WALLS") for p in faces] + [(p, "OUTLINE") for p in R.outline_rooms(index, names, faces, f)]
  out = []
  used: set = set()
  replaced: dict = {}
  for poly, how in items:
    poly = R._clean(poly)
    d = R.describe(poly, names, sizes, f)
    inside = R.pairs_inside(poly, pairs)
    if len(inside) >= 2:
     
      continue
    if len(inside) == 1:
      p = pairs[inside[0]]
      label_area = p["a_mm"] * p["b_mm"] / 1e6
      if abs(d["area_m2"] / label_area - 1.0) > C.ROOM_SIZE_TOL:
        replaced[inside[0]] = d["area_m2"]
        continue
      used.add(inside[0])
    notes: list = []
    base = 0.85 if how == "WALLS" else 0.65
    if how == "OUTLINE":
      notes.append(C.note("ROOM_FROM_OUTLINE"))
    room_names = d["names"]
    if not room_names:
      notes.append(C.note("ROOM_NO_LABEL"))
      base *= 0.8
      
    elif len(room_names) > 1:
      notes.append(C.note("ROOM_MULTIPLE_LABELS", names=room_names))
      base *= 0.85
    if d["deviation_pct"] is not None and abs(d["deviation_pct"]) > C.ROOM_SIZE_TOL * 100:
      notes.append(C.note("ROOM_SIZE_MISMATCH", label_area_m2=round(d["label_area_m2"], 3), measured_area_m2=round(d["area_m2"], 3)))
      base *= 0.9
    cx, cy = poly.centroid.x, poly.centroid.y
    name = " / ".join(room_names) if room_names else None
    minx, miny, maxx, maxy = poly.bounds
    facts = {"name": name, "area_m2": round(d["area_m2"], 3), "perimeter_m": round(d["perimeter_m"], 3), "holes": d["holes"],
      "bbox_mm": [round((maxx - minx) * f), round((maxy - miny) * f)], "size_text": d["size_text"], "outline_from": how}
    
    if d["label_area_m2"] is not None:
      facts["label_area_m2"] = round(d["label_area_m2"], 3)
      facts["deviation_pct"] = round(d["deviation_pct"], 2)
    work_item, mode, kind = C.SUGGESTIONS["ROOM"]
    cand = Candidate(key=_key("ROOM", round(cx / 3), round(cy / 3)), category="ROOM", kind=kind, quantity_mode=mode,
      label=(name or "Room") + f" · {d['area_m2']:.2f} m²", tag=None, geometry=R.polygon_geometry(poly), params={"dims_basis": "DRAWN"},
      missing=[], work_item=work_item, status="VALID", confidence=0.0, facts=facts, notes=notes, source="VECTOR_SNAP", count=1)
    out.append(_finish(cand, ctx, base))
  for i, p in enumerate(pairs):
    if i in used:
      continue
    poly = R.label_polygon(p, f)
    area = p["a_mm"] * p["b_mm"] / 1e6
    
    notes = [C.note("ROOM_OUTLINE_REPLACED", measured_area_m2=round(replaced[i], 3), label_area_m2=round(area, 3))] if i in replaced else []
    notes.append(C.note("ROOM_FROM_LABEL", size_text=p["size_text"]))
    facts = {"name": p["name"], "area_m2": round(area, 3), "perimeter_m": round(2.0 * (p["a_mm"] + p["b_mm"]) / 1000.0, 3), "holes": 0,
      "bbox_mm": [round(p["a_mm"]), round(p["b_mm"])], "size_text": p["size_text"], "label_area_m2": round(area, 3), "outline_from": "LABEL"}
    work_item, mode, kind = C.SUGGESTIONS["ROOM"]
    cand = Candidate(key=_key("ROOM", round(p["x"] / 3), round(p["y"] / 3)), category="ROOM", kind=kind, quantity_mode=mode,
      label=f"{p['name']} · {area:.2f} m²", tag=None, geometry=R.polygon_geometry(poly), params={"dims_basis": "SPECIFIED"},
      missing=[], work_item=work_item, status="VALID", confidence=0.0, facts=facts, notes=notes, source="VECTOR_SNAP", count=1)
    out.append(_finish(cand, ctx, 0.7))
  out.sort(key=lambda c: (c.facts["name"] or "~", -c.facts["area_m2"]))
  return out

def run_extraction(index, mm_per_pt: float, *, cal_factor: float = 1.0, scale_unverified: bool = False, content_kind: str = "VECTOR",
  budget_s: float = 25.0, schedule: dict | None = None) -> Extraction:
  started = time.monotonic()
  deadline = started + budget_s
  ctx = {"cal_factor": cal_factor, "scale_unverified": scale_unverified,
    "content_factor": {"VECTOR": 1.0, "UNKNOWN": 0.95, "RASTER": 0.85}.get(content_kind, 0.95)}
  
  res = Extraction()
  words = index.words
  lines = build_lines(words)
  hint = find_units_hint(lines)
  heights = M.height_hints(lines, hint)
  shapes = M.member_shapes(index.rings, mm_per_pt)
  openings = S.opening_lookup(schedule)
  res.candidates.extend(_tag_candidates(index, words, shapes, mm_per_pt, hint, heights, ctx, openings))
  res.stats["schedule_marks"] = len(openings)
  kind = sheet_kind(words)
  res.stats["sheet_kind"] = kind
  frames, runs = [], []
  if kind["kind"] == "STRUCTURAL":
    res.notes.append(C.note("STRUCTURAL_SHEET", title=kind["title"]))
  else:
    try:
      frames, runs, walls, wstats = _wall_candidates(index, mm_per_pt, heights, ctx, deadline, _is_imperial(words))
      res.candidates.extend(walls)
      wstats["tank_walls"] = _mark_tanks(words, walls, mm_per_pt)
      hosted = H.assign(walls, [c for c in res.candidates if c.category in ("DOOR", "WINDOW")], mm_per_pt)
      wstats["openings_assigned"], wstats["openings_unassigned"] = hosted["assigned"], hosted["unassigned"]
      for c in walls:
        if c.params.get("openings"):
          c.notes.append(C.note("OPENINGS_ASSIGNED", count=c.facts["openings"]["count"], marks=c.facts["openings"]["marks"]))
          c.status = _status(c.notes)
      res.stats["walls"] = wstats
      if wstats.get("wall_pen_pt"):
        res.notes.append(C.note("WALL_PEN_SELECTED", pen_pt=wstats["wall_pen_pt"], runs_all_pens=wstats.get("runs_all_pens"),
          wall_m_all_pens=wstats.get("wall_m_all_pens")))
      res.candidates.extend(_room_candidates(index, frames, runs, lines, mm_per_pt, hint, ctx))
    except W.TimeLimit:
      res.notes.append(C.note("TIME_LIMIT"))
  mapped = {c.tag for c in res.candidates if c.tag}
  unmapped: dict = {}
  for g in census.tag_census(words):
      
    if g["tag"] not in mapped and M.category_of(g["tag"]) is None and g["in_drawing"] >= 2:
      unmapped[g["tag"]] = g["in_drawing"]
  res.unmapped_tags = [{"tag": t, "count": n} for t, n in sorted(unmapped.items(), key=lambda kv: (-kv[1], kv[0]))][:30]
  res.stats["seconds"] = round(time.monotonic() - started, 3)
  res.stats["units_hint"] = hint
  res.stats["height_notes"] = heights
  return res