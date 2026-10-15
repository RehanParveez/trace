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
from app.modules.drawings_boq.takeoff.extract import structure as ST
from app.modules.drawings_boq.takeoff.levels import level_spec
from app.modules.drawings_boq.takeoff.prep import census
from app.modules.drawings_boq.takeoff.prep import lintels as LT
from app.modules.drawings_boq.takeoff.prep import schedules as S
from app.modules.drawings_boq.takeoff.prep import stairs as STR
from app.modules.drawings_boq.takeoff.prep import views as VW
from app.modules.drawings_boq.takeoff.prep.details import norm_mark as ST_norm
from app.modules.drawings_boq.takeoff.prep.texts import build_lines, find_units_hint
import time

SCAN_TEXT_FACTOR = 0.8

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

VIEW_SCALE_TOL = 0.03
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

_snap_inch = ST.snap_inch

def _tag_candidates(index, words, shapes, f, hint, heights, ctx, openings=None, view=None, groups=None, imperial: bool = False, footing: dict | None = None, col_details: dict | None = None) -> list:
  """view: one drawing of a composite sheet (its marks are counted inside it only). groups: the marks already found in that view.
  footing: {"assigned": {mark: (a, b)}, "assumed": bool, "options": [...]} the footing sizes read from the footing section details."""
  if groups is None:
    groups = M.tag_members(words, shapes, f, hint, openings)
  out = []
  
  clusters: dict = {}
  for g in groups:
    if g["category"] in ("COLUMN", "FOOTING") and "drawn_mm" in g:
      a, b = g["drawn_mm"]
      ids = tuple(i for i, s in enumerate(shapes) if s["fill"] and abs(s["a"] - a) <= 0.05 * a + 5 and abs(s["b"] - b) <= 0.05 * b + 5)
      clusters.setdefault((g["category"], ids), []).append(g)
  tags_in = {}
  for (cat, ids), gs in clusters.items():
    for g in gs:
      tags_in[g["tag"]] = (sum(x["count"] for x in gs), len(ids))
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
      if drawn and imperial and cat == "COLUMN":
        snapped = (_snap_inch(drawn[0]), _snap_inch(drawn[1]))
        if snapped != tuple(drawn):
          facts["size_measured_mm"] = list(drawn)
          drawn = snapped
      detail = (footing or {}).get("assigned", {}).get(tag) if cat == "FOOTING" else None
      cdet = (col_details or {}).get(ST_norm(tag)) if cat == "COLUMN" else None
      cdet_mm = cdet.get("size_mm") if cdet and not cdet.get("disagree") else None
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
          
      elif cdet_mm:
        used = cdet_mm
        facts["size_detail_mm"] = list(cdet_mm)
        notes.append(C.note("SIZE_FROM_COLUMN_DETAIL"))
        if drawn and (abs(cdet_mm[0] - drawn[0]) > C.SIZE_TOL * cdet_mm[0] or abs(cdet_mm[1] - drawn[1]) > C.SIZE_TOL * cdet_mm[1]):
          notes.append(C.note("COLUMN_PLAN_VS_DETAIL", drawn_mm=list(drawn), detail_mm=list(cdet_mm)))
          base *= 0.9
      elif drawn:
        used = drawn
        if view and cat == "COLUMN":
          notes.append(C.note("COLUMN_SIZE_FROM_PLAN"))
      elif detail:
        used = detail
        facts["size_detail_mm"] = list(detail)
        notes.append(C.note("SIZE_FROM_DETAIL"))
        
        if footing.get("assumed"):
          notes.append(C.note("FOOTING_SIZE_ORDER_ASSUMED", options_mm=footing["options"]))
          base *= 0.8
      else:
        notes.append(C.note("SIZE_NOT_FOUND"))
        if cat == "FOOTING" and footing and footing.get("options") and not g.get("stair"):
          notes.append(C.note("FOOTING_SIZES_LISTED", options_mm=footing["options"]))
        base *= 0.8
      if cdet and cdet.get("disagree"):
        notes.append(C.note("COLUMN_DETAILS_DISAGREE", sizes_in=cdet["sizes_in"]))
        base *= 0.9
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
        notes.append(_height_note(h))
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
    if view:
      facts["view"] = {"key": view["key"], "caption": view["caption"], "kind": view["kind"], "level_hint": view.get("level_hint")}
      spec = level_spec(view.get("level_hint"))
      
      if spec:
        label += f" · {spec[0]}"
    cand = Candidate(key=_key(cat, tag, view["key"]) if view else _key(cat, tag), category=cat, kind=kind, quantity_mode=mode, label=label, tag=tag,
      geometry={"points": g["points"]}, params=params, missing=missing, work_item=work_item, status="VALID", confidence=0.0,
      facts=facts, notes=notes, source="TAG_SCAN", count=g["count"])
    out.append(_finish(cand, ctx, base))
  return out

def _ft_in(mm: float) -> str:
  inches = int(round(mm / 25.4))
  return f"{inches // 12}'-{inches % 12}\""

def _with_floor_height(heights: dict, floor_heights: dict | None, level_hint: str | None) -> dict:
  """The height notes of the sheet, with the clear storey height printed on the building sections added for the floor this plan shows. A height
  written as a note on the plan itself is kept; the section height only fills a gap."""
  fh = (floor_heights or {}).get(level_hint or "")
  
  if not fh or not fh.get("clear_mm"):
    return heights
  entry = {"mm": float(fh["clear_mm"]), "text": f"clear storey height {_ft_in(float(fh['clear_mm']))} printed on the building section", "basis": "SECTION"}
  out = dict(heights)
  for cat in ("WALL", "COLUMN"):
    out.setdefault(cat, entry)
  return out

def _height_note(h: dict) -> dict:
  return C.note("HEIGHT_FROM_SECTION" if h.get("basis") == "SECTION" else "HEIGHT_FROM_NOTE", text=h["text"])

def _unmarked_columns(v: dict, squares: list, f: float, ctx: dict, imperial: bool, heights: dict | None = None) -> Candidate | None:
  """A framing view with no column marks at all (a mumty or a stair head) still shows its columns as black squares."""
  sized = [s for s in squares if 150.0 <= s["a"] <= 600.0 and s["b"] <= 900.0]
  if not sized:
    return None
  a = sorted(s["a"] for s in sized)[len(sized) // 2]
  b = sorted(s["b"] for s in sized)[len(sized) // 2]
  a, b = (_snap_inch(a), _snap_inch(b)) if imperial else (M._round5(a), M._round5(b))
  work_item, mode, kind = C.SUGGESTIONS["COLUMN"]
  notes = [C.note("UNMARKED_COLUMNS"), C.note("COLUMN_SIZE_FROM_PLAN")]
  h = (heights or {}).get("COLUMN")
  
  if h:
    notes.append(_height_note(h))
  spec = level_spec(v.get("level_hint"))
  label = f"Columns (no mark) ×{len(sized)} · {_fmt_mm(a)}×{_fmt_mm(b)} mm" + (f" · {spec[0]}" if spec else "")
  facts = {"tag": None, "count": len(sized), "size_drawn_mm": [a, b], "size_used_mm": [a, b], "matched_shapes": len(sized),
    "view": {"key": v["key"], "caption": v["caption"], "kind": v["kind"], "level_hint": v.get("level_hint")}}
  cand = Candidate(key=_key("COLUMN", "UNMARKED", v["key"]), category="COLUMN", kind=kind, quantity_mode=mode, label=label, tag=None,
    geometry={"points": [[round(s["cx"], 4), round(s["cy"], 4)] for s in sized]},
    params={"length_mm": a, "width_mm": b, "dims_basis": "DRAWN", **({"depth_mm": h["mm"]} if h else {})},
    missing=[] if h else ["height_mm"], work_item=work_item, status="VALID", confidence=0.0, facts=facts, notes=notes, source="TAG_SCAN", count=len(sized))
  return _finish(cand, ctx, 0.6)

def _settle_hidden_columns(cands: list) -> int:
  """Fewer columns of a mark's size are drawn than there are marks (some are hidden inside a wall, as on a basement), but the same mark with the same
  number of columns is on another floor where every one is drawn: the marks are the count, and the shortfall is explained."""
  full: dict = {}
  for c in cands:
    f = c.facts or {}
    codes = {n.get("code") for n in c.notes}
    if c.category == "COLUMN" and c.tag and f.get("same_size_marks") and f.get("same_size_drawn") == f.get("same_size_marks") and not codes & {"COUNT_DIFFERS_FROM_DRAWN", "UNTAGGED_SAME_SIZE"}:
      full.setdefault((c.tag, int(c.count or 0), f["same_size_marks"]), set()).add((f.get("view") or {}).get("key"))
  settled = 0
  
  for c in cands:
    f = c.facts or {}
    if c.category != "COLUMN" or not c.tag or not any(n.get("code") == "COUNT_DIFFERS_FROM_DRAWN" for n in c.notes):
      continue
    peers = full.get((c.tag, int(c.count or 0), f.get("same_size_marks")), set()) - {(f.get("view") or {}).get("key")}
    if not peers:
      continue
    c.notes = [C.note("COUNT_MATCHES_OTHER_FLOOR", marks=c.count, drawn=f.get("same_size_drawn")) if n.get("code") == "COUNT_DIFFERS_FROM_DRAWN" else n for n in c.notes]
    c.status = _status(c.notes)
    settled += 1
  return settled

def _structure_candidates(index, views: list, f: float, hint, heights, ctx, imperial: bool, view_scales: dict | None = None, col_details: dict | None = None,
  floor_heights: dict | None = None) -> tuple:
  """A sheet that shows several structural plans (foundation, basement / ground / first framing plans, mumty framing plan): each plan is read on
  its own, so the C1 marks of the ground floor are not added to the C1 marks of the first floor. Footings are read from the foundation plan only

  (the framing plans repeat the footing marks beside the columns)."""
  plans = [v for v in views if v["structural"]]
  squares = ST.dedupe_solid(ST.square_shapes(index.rings, f), f)
  pool = ST.dedupe_solid(M.member_shapes(index.rings, f) + squares, f)
  shapes_by = VW.split(pool, views, lambda s: (s["cx"], s["cy"]))
  squares_by = VW.split(squares, views, lambda s: (s["cx"], s["cy"]))
  words_by = VW.split(index.words, views, lambda w: (w.cx, w.cy))
  sizes = ST.footing_sizes(index.words, hint, imperial)
  out: list = []
  stats: list = []
  found: dict = {}
  
  for v in plans:
    ws, sh = words_by.get(v["key"], []), shapes_by.get(v["key"], [])
   
    keep = ("FOOTING",) if v.get("foundation") else ("COLUMN", "BEAM")
    found[v["key"]] = [g for g in M.tag_members(ws, sh, f, hint, None, plan_view=True) if g["category"] in keep]
  
  seen: dict = {}
  for gs in found.values():
    for g in gs:
      if g["category"] == "COLUMN" and g.get("drawn_mm"):
        seen.setdefault(g["tag"], []).append(g["drawn_mm"])
  for v in plans:
    groups = found[v["key"]]
    ws, sh = words_by.get(v["key"], []), shapes_by.get(v["key"], [])
    borrowed = set()
    for g in groups:
      if g["category"] == "COLUMN" and not g.get("drawn_mm") and seen.get(g["tag"]):
        g["drawn_mm"] = max(set(seen[g["tag"]]), key=seen[g["tag"]].count)
        g["spread"] = 0.0
        borrowed.add(g["tag"])
    footing = None
    if v.get("foundation"):
      footing = ST.assign_footing_sizes(groups, sizes)
      for w in ST.stair_footings(ws):
        groups.append({"tag": "STAIR-F", "category": "FOOTING", "points": [[round(w.cx, 4), round(w.cy, 4)]], "count": 1, "schedule_rows": 0,
          "matched": 0, "stair": True})
    view_heights = _with_floor_height(heights, floor_heights, v.get("level_hint")) if not v.get("foundation") else heights
    cands = _tag_candidates(index, ws, sh, f, hint, view_heights, ctx, view=v, groups=groups, imperial=imperial, footing=footing, col_details=col_details)
    for c in cands:
      if c.tag in borrowed and c.category == "COLUMN":

        c.notes.append(C.note("SIZE_FROM_OTHER_VIEW"))
        c.status = _status(c.notes)
    has_columns = any(g["category"] == "COLUMN" for g in groups)
    if not has_columns and not v.get("foundation"):
      extra = _unmarked_columns(v, squares_by.get(v["key"], []), f, ctx, imperial, view_heights)
      if extra is not None:
        cands.append(extra)
    own = (view_scales or {}).get(v["key"]) or {}
    if own.get("mm_per_pt") and abs(own["mm_per_pt"] / f - 1.0) > VIEW_SCALE_TOL:
      for c in cands:
        c.notes.append(C.note("VIEW_SCALE_DIFFERS", view_mm_per_pt=own["mm_per_pt"], sheet_mm_per_pt=round(f, 5)))
        c.status = _status(c.notes)
    out.extend(cands)
    by = {}
    
    for c in cands:
      by[c.category] = by.get(c.category, 0) + int(c.count or 0)
    stats.append({"key": v["key"], "caption": v["caption"], "level_hint": v.get("level_hint"), "foundation": bool(v.get("foundation")),
      "columns": by.get("COLUMN", 0), "footings": by.get("FOOTING", 0), "beams": by.get("BEAM", 0), "squares": len(squares_by.get(v["key"], [])),
      "slab_panels": v.get("slab_panels", 0), "slab_note_mm": v.get("slab_note_mm")})
  _settle_hidden_columns(out)
  return out, stats

def _is_imperial(words) -> bool:
  """A drawing dimensioned in feet and inches: several words such as 30'-0" or 13'-6"."""
  n = 0
  for w in words:
    if _FEET_INCH.search(w.text or ""):
      n += 1
      if n >= 4:
        return True
  return False

def _drop_tank_heights(walls: list) -> None:
  """A tank wall is not a storey wall: the storey height read from the sections does not apply to it."""
  for c in walls:
    if c.facts.get("enclosure") != "TANK" or not any(n.get("code") == "HEIGHT_FROM_SECTION" for n in c.notes):
      continue
  
    c.params.pop("height_mm", None)
    c.params["dims_basis"] = "DRAWN"
    c.notes = [n for n in c.notes if n.get("code") != "HEIGHT_FROM_SECTION"]
    if "height_mm" not in c.missing:
      c.missing.append("height_mm")
    c.status = _status(c.notes)
    
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
  stats["dropped_outside_rcc"] = 0
  box = RC.envelope(rcc, f) if rcc else None
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
    
    if box is not None and RC.outside(box, p0, p1):
      stats["dropped_outside_rcc"] += 1
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
      notes.append(_height_note(h))
      
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
      notes.append(_height_note(h))
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
  _flag_nested_rooms(out)
  out.sort(key=lambda c: (c.facts["name"] or "~", -c.facts["area_m2"]))
  return out

def _flag_nested_rooms(rooms: list) -> None:
  """A room whose centre is inside a larger room's outline (a W/C drawn inside a stair hall) is counted twice in the room total. It is kept and
  flagged, not removed: only the engineer can say which outline is the room."""
  from shapely.geometry import Polygon
  polys = []
  for c in rooms:
    g = c.geometry or {}
    try:
      polys.append(Polygon(g["outer"], g.get("holes") or []) if g.get("outer") else None)
    except Exception:
      polys.append(None)
      
  for i, a in enumerate(rooms):
    pa = polys[i]
    if pa is None or pa.is_empty:
      continue
    inside = [j for j, b in enumerate(rooms) if j != i and polys[j] is not None and b.facts["area_m2"] > a.facts["area_m2"] * 1.2
              and polys[j].contains(pa.representative_point())]
    if inside:
      big = max(inside, key=lambda j: rooms[j].facts["area_m2"])
      a.notes.append(C.note("ROOM_INSIDE_ROOM", enclosing=rooms[big].facts.get("name"), enclosing_m2=rooms[big].facts["area_m2"]))
      a.facts["inside_room"] = rooms[big].facts.get("name")
      a.status = _status(a.notes)

def _inch_text(mm: float) -> str:
  return f"{mm / 25.4:g}\""

def _slab_thickness(note_mm, slab_values: list) -> tuple:
  """(thickness mm or None, source, notes) for one slab: the note on its own framing plan first; another thickness printed elsewhere on the drawing
  is a dispute; with no plan note the one thickness the drawing prints is used, and several are listed without choosing."""
  values = [v for v in (slab_values or []) if v.get("mm")]
  if note_mm:
    others = [v for v in values if abs(v["mm"] - note_mm) > 1.0]
    notes = [C.note("SLAB_THICKNESS_DISAGREES", plan_mm=note_mm, others=[{"mm": v["mm"], "pages": v.get("pages", [])} for v in others])] if others else []
    return float(note_mm), "PLAN_NOTE", notes
  if len(values) == 1:
    return float(values[0]["mm"]), "OTHER_SHEET", [C.note("SLAB_THICKNESS_FROM_OTHER_SHEET", pages=values[0].get("pages", []))]
  if len(values) > 1:
    return None, None, [C.note("SLAB_THICKNESSES_LISTED", options_mm=[v["mm"] for v in values])]
  return None, None, []

def _slab_candidate(plan: dict, areas: dict, slab_values: list, ctx: dict) -> tuple:
  """One slab per floor from a structural framing plan: the covered area printed for that floor in the area table, as the rectangle (length x width)
  printed beside it, with the thickness of the plan's slab note. Nothing is measured from the drawn lines, so the scale of the sheet does not enter.
  Returns (candidate or None, notes for the sheet)."""
  hint = plan.get("level_hint")
  area = areas.get(hint) if hint else None
  spec = level_spec(hint)
  if area is None:
    return None, [C.note("SLAB_AREA_NOT_FOUND", floor=spec[0] if spec else hint, caption=plan.get("caption"))]
  t, source, notes = _slab_thickness(plan.get("note_mm"), slab_values)
  params: dict = {"dims_basis": "SPECIFIED"}
  missing: list = []
  dims = area.get("dims_mm")
  base = 0.9
  
  if dims and len(dims) == 2:
    params["length_mm"], params["width_mm"] = float(dims[0]), float(dims[1])
    notes.append(C.note("SLAB_AREA_FROM_TABLE"))
  else:
    missing.append("size")
    notes.append(C.note("SLAB_SIZE_NOT_PRINTED"))
    base *= 0.7
  if t:
    params["depth_mm"] = t
  else:
    missing.append("thickness_mm")
    base *= 0.8
  if any(n["code"] == "SLAB_THICKNESS_DISAGREES" for n in notes):
    base *= 0.9
  m2 = float(area["m2"])
  label = "Slab" + (f" {_inch_text(t)}" if t else "") + f" · {m2:.2f} m²" + (f" · {spec[0]}" if spec else "")
  facts = {"floor": hint, "area_m2": m2, "area_text": f"{area['value']:g} {area['unit']}", "area_name": area.get("name"), "area_pages": area.get("pages", []),
    "thickness_mm": t, "thickness_source": source, "panels": plan.get("panels", 0), "panel_marks": plan.get("marks", [])}
  if dims:
    facts["dims_mm"] = [float(dims[0]), float(dims[1])]
    facts["dims_text"] = area.get("dims_text")
  if t and dims:
    facts["volume_m3"] = round(float(dims[0]) * float(dims[1]) * t / 1e9, 4)
  if plan.get("view"):
    facts["view"] = plan["view"]
  work_item, mode, kind = C.SUGGESTIONS["SLAB"]
  cand = Candidate(key=_key("SLAB", hint, plan.get("key") or ""), category="SLAB", kind=kind, quantity_mode=mode, label=label, tag="SLAB",
    geometry={"points": [[round(plan["centre"][0], 4), round(plan["centre"][1], 4)]]}, params=params, missing=missing, work_item=work_item,
    status="VALID", confidence=0.0, facts=facts, notes=notes, source="PRINTED", count=1)
  cand.status = _status(cand.notes)
  cand.confidence = round(max(0.0, min(1.0, base * ctx["content_factor"])), 4)
  return cand, []

def _hosted_by_tag(by_wall: dict, walls: list) -> dict:
  """tag -> {"thin": n, "rcc": n, "hosted": n}: how many of each opening mark sit in 4.5 inch walls and in RCC walls, from the openings already assigned to walls."""
  wall_of = {w.key: w for w in walls}
  out: dict = {}
  for key, ops in (by_wall or {}).items():
    w = wall_of.get(key)
    if w is None:
      continue
    thin = float((w.params or {}).get("thickness_mm") or 0) < 160.0
    rcc = (w.facts or {}).get("construction") == "RCC"
    for o in ops:
      if not o.get("label"):
        continue
      rec = out.setdefault(o["label"], {"thin": 0, "rcc": 0, "hosted": 0})
      rec["hosted"] += int(o["nos"])
      rec["thin"] += int(o["nos"]) if (thin and not rcc) else 0
      rec["rcc"] += int(o["nos"]) if rcc else 0
  return out

def _lintel_candidates(openings: list, table: list, hosted: dict, ctx: dict) -> list:
  """One lintel candidate per door / window / ventilator mark of a plan: the opening width from the schedule picks the row of the lintel table printed on
  the drawing, the length is the width plus the bearing at each end, and the count is the number of marks counted. Nothing is read from drawn lines."""
  out = []
  if not table:
    return out
  bearing = C.LINTEL_BEARING_MM
  for o in openings:
    size = (o.facts or {}).get("size_schedule_mm")
    pts = (o.geometry or {}).get("points") or []
    if o.category not in ("DOOR", "WINDOW") or not size or not o.tag or not pts:
      continue
    span = float(size[0])
    sec = LT.section_for(table, span)
    notes = [C.note("LINTEL_BEARING_ASSUMED", bearing_mm=bearing)]
    params: dict = {"dims_basis": "SPECIFIED"}
    
    missing: list = []
    base = 0.85
    facts = {"opening_tag": o.tag, "opening_kind": (o.facts or {}).get("opening_kind") or o.category, "span_mm": round(span, 1), "bearing_mm": bearing,
      "opening_size_mm": [round(float(size[0]), 1), round(float(size[1]), 1)]}
    if sec:
      params["length_mm"], params["width_mm"], params["depth_mm"] = round(span + 2.0 * bearing, 1), sec["width_mm"], sec["depth_mm"]
      facts["section_mm"] = [sec["width_mm"], sec["depth_mm"]]
      facts["table_span_max_mm"] = sec["span_max_mm"]
      facts["table_pages"] = list(sec.get("pages") or [])
      notes.append(C.note("LINTEL_SECTION_FROM_TABLE"))
      if sec.get("steel"):
        params["steel"] = dict(sec["steel"])
        facts["steel_text"] = LT.steel_text(sec["steel"])
        notes.append(C.note("LINTEL_STEEL_FROM_TABLE"))
      label = f"Lintel {o.tag} ×{o.count} · {_inch_text(sec['width_mm'])}×{_inch_text(sec['depth_mm'])} · {_fmt_mm(params['length_mm'])} mm long"
    else:
      missing.append("size")
      notes.append(C.note("LINTEL_SPAN_ABOVE_TABLE"))
      base *= 0.7
      label = f"Lintel {o.tag} ×{o.count} · span {_fmt_mm(span)} mm"
    h = hosted.get(o.tag)
    if h:
      facts["hosted"] = dict(h)
      if h["thin"]:
        notes.append(C.note("LINTEL_IN_THIN_WALL", count=h["thin"]))
        base *= 0.9
      if h["rcc"]:
        notes.append(C.note("LINTEL_IN_RCC_WALL", count=h["rcc"]))
    work_item, mode, kind = C.SUGGESTIONS["LINTEL"]
    
    cand = Candidate(key=_key("LINTEL", o.key), category="LINTEL", kind=kind, quantity_mode=mode, label=label, tag=f"L-{o.tag}",
      geometry={"points": [list(p) for p in pts]}, params=params, missing=missing, work_item=work_item, status="VALID", confidence=0.0,
      facts=facts, notes=notes, source="TAG_SCAN", count=int(o.count or len(pts)))
    cand.status = _status(cand.notes)
    cand.confidence = round(max(0.0, min(1.0, base * ctx["content_factor"])), 4)
    out.append(cand)
  return out

def _stair_candidates(lines: list, spec: dict | None, ctx: dict) -> tuple[list, list]:
  """One stair candidate per plan that names a staircase, sized from the riser, tread, width and number of steps printed elsewhere on the drawing. The
  concrete is the plan run of the steps x the width x an equivalent thickness (waist slab along the slope plus half a riser). The waist slab is rarely
  printed, so 6 inches is assumed and said so. Landings are not included."""
  labels = STR.find_labels(lines)
  if not labels:
    return [], []
  if not spec:
    return [], [C.note("STAIR_DETAILS_NOT_FOUND")]
  waist = spec.get("waist_mm")
  assumed = not waist
  waist_used = float(waist or C.STAIR_WAIST_DEFAULT_MM)
  box = STR.flight_box(spec, waist_used)
  notes = [C.note("STAIR_FROM_DETAILS"), C.note("STAIR_LANDINGS_NOT_INCLUDED"), C.note("STAIR_COUNT_FROM_LABELS", count=len(labels))]
  facts = {"stair_text": spec.get("text"), "riser_mm": spec.get("riser_mm"), "tread_mm": spec.get("tread_mm"), "stair_width_mm": spec.get("width_mm"),
    "steps": spec.get("steps"), "waist_mm": round(waist_used, 1), "waist_source": "ASSUMED" if assumed else "PRINTED", "stair_pages": list(spec.get("pages") or [])}
  params: dict = {"dims_basis": "SPECIFIED"}
  missing: list = []
  base = 0.8
  
  if box:
    params.update(box)
    facts["equivalent_depth_mm"] = box["depth_mm"]
    if assumed:
      notes.append(C.note("STAIR_WAIST_ASSUMED"))
      base *= 0.85
    label = f"Stair ×{len(labels)} · {spec['steps']} steps · {_fmt_mm(spec['riser_mm'])}/{_fmt_mm(spec['tread_mm'])} mm · {_fmt_mm(spec['width_mm'])} mm wide"
  else:
    missing = ["size"]
    notes.append(C.note("STAIR_DETAILS_INCOMPLETE"))
    base *= 0.6
    label = f"Stair ×{len(labels)}"
  work_item, mode, kind = C.SUGGESTIONS["STAIR"]
  cand = Candidate(key=_key("STAIR", round(labels[0]["x"], 1), round(labels[0]["y"], 1), len(labels)), category="STAIR", kind=kind, quantity_mode=mode, label=label,
    tag="STAIR", geometry={"points": [[round(l["x"], 3), round(l["y"], 3)] for l in labels]}, params=params, missing=missing, work_item=work_item, status="VALID",
    confidence=0.0, facts=facts, notes=notes, source="TAG_SCAN", count=len(labels))
  cand.status = _status(cand.notes)
  cand.confidence = round(max(0.0, min(1.0, base * ctx["content_factor"])), 4)
  return [cand], []

def _view_plans(views: list) -> list:
  """The framing plans of a composite structural sheet (not the foundation plan) as slab plans."""
  out = []
  for v in views:
    if not v.get("structural") or v.get("foundation") or not v.get("level_hint"):
      continue
    b = v["bbox"]
    out.append({"key": v["key"], "caption": v.get("caption"), "level_hint": v["level_hint"], "centre": ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0),
      "note_mm": v.get("slab_note_mm"), "panels": int(v.get("slab_panels") or 0), "marks": list(v.get("slab_marks") or []),
      "view": {"key": v["key"], "caption": v["caption"], "kind": v["kind"], "level_hint": v.get("level_hint")}})
  return out

def _sheet_plan(words: list, lines: list, level_hint: str | None, title: str | None) -> dict | None:
  """A structural sheet that shows one framing plan (no separate drawings on it): its slab note and panel marks come from the whole sheet."""
  if not level_hint or not words or VW._FOUNDATION.search(title or ""):
    return None
  note = None
  for ln in lines:
    m = VW._SLAB_NOTE.search(ln.text)
    if m:
      note = round(float(m.group(1)) * 25.4, 1)
      break
  marks = sorted({w.text.strip().upper() for w in words if VW._SLAB_PANEL.match(w.text.strip().upper())})
  xs, ys = [w.cx for w in words], [w.cy for w in words]
  return {"key": "", "caption": title, "level_hint": level_hint, "centre": ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0), "note_mm": note,
    "panels": len(marks), "marks": marks, "view": None}

def run_extraction(index, mm_per_pt: float, *, cal_factor: float = 1.0, scale_unverified: bool = False, content_kind: str = "VECTOR",
  budget_s: float = 25.0, schedule: dict | None = None, views_meta: list | None = None, col_details: dict | None = None,
  floor_heights: dict | None = None, level_hint: str | None = None, slab_values: list | None = None, text_source: str = "TEXT") -> Extraction:
  started = time.monotonic()
  deadline = started + budget_s
  ctx = {"cal_factor": cal_factor, "scale_unverified": scale_unverified,
    "content_factor": {"VECTOR": 1.0, "UNKNOWN": 0.95, "RASTER": 0.85}.get(content_kind, 0.95) * (SCAN_TEXT_FACTOR if text_source == "OCR" else 1.0)}
  
  res = Extraction()
  if text_source == "OCR":
    res.notes.append(C.note("SCAN_TEXT_READ"))
  words = index.words
  lines = build_lines(words)
  hint = find_units_hint(lines)
  heights = M.height_hints(lines, hint)
  sheet_heights = _with_floor_height(heights, floor_heights, level_hint)
  shapes = M.member_shapes(index.rings, mm_per_pt)
  openings = S.opening_lookup(schedule)
  views = VW.find_views(index)
  
  composite_structural = sum(1 for v in views if v["structural"]) >= 2
  if composite_structural:
    found, vstats = _structure_candidates(index, views, mm_per_pt, hint, heights, ctx, _is_imperial(words), {v["key"]: v.get("scale") for v in (views_meta or []) if v.get("scale")}, col_details, floor_heights)
    res.candidates.extend(found)
    res.stats["views"] = vstats
    plans = _view_plans(views)
  else:
    res.candidates.extend(_tag_candidates(index, words, shapes, mm_per_pt, hint, sheet_heights, ctx, openings, col_details=col_details))
    plans = []
    
  res.stats["schedule_marks"] = len(openings)
  kind = sheet_kind(words)
  if not composite_structural and kind["kind"] == "STRUCTURAL":
    one = _sheet_plan(words, lines, level_hint, kind.get("title"))
    plans = [one] if one else []
  areas = {a["key"]: a for a in ((schedule or {}).get("areas") or []) if a.get("kind") == "FLOOR"}
  seen_floor: set = set()
  for plan in plans:
    cand, notes = _slab_candidate(plan, areas, slab_values or [], ctx)
    if cand is not None and plan["level_hint"] not in seen_floor:
      seen_floor.add(plan["level_hint"])
      res.candidates.append(cand)
    res.notes.extend(notes)
  res.stats["slabs"] = sum(1 for c in res.candidates if c.category == "SLAB")
  
  res.stats["sheet_kind"] = kind
  frames, runs = [], []
  if kind["kind"] == "STRUCTURAL" or composite_structural:
    res.notes.append(C.note("STRUCTURAL_SHEET", title=kind["title"] or (views[0]["caption"] if views else None)))
  else:
    try:
      frames, runs, walls, wstats = _wall_candidates(index, mm_per_pt, sheet_heights, ctx, deadline, _is_imperial(words))
      res.candidates.extend(walls)
      wstats["tank_walls"] = _mark_tanks(words, walls, mm_per_pt)
      _drop_tank_heights(walls)
      hosted = H.assign(walls, [c for c in res.candidates if c.category in ("DOOR", "WINDOW")], mm_per_pt)
      wstats["openings_assigned"], wstats["openings_unassigned"] = hosted["assigned"], hosted["unassigned"]
      for c in walls:
        if c.params.get("openings"):
          c.notes.append(C.note("OPENINGS_ASSIGNED", count=c.facts["openings"]["count"], marks=c.facts["openings"]["marks"]))
          c.status = _status(c.notes)
      res.stats["walls"] = wstats
      lintels = _lintel_candidates([c for c in res.candidates if c.category in ("DOOR", "WINDOW")], (schedule or {}).get("lintels") or [],
        _hosted_by_tag(hosted.get("by_wall"), walls), ctx)
      res.candidates.extend(lintels)
      res.stats["lintels"] = len(lintels)
      stairs, stair_notes = _stair_candidates(lines, (schedule or {}).get("stair"), ctx)
      res.candidates.extend(stairs)
      res.notes.extend(stair_notes)
      res.stats["stairs"] = len(stairs)
      if wstats.get("dropped_outside_rcc"):
        res.notes.append(C.note("RUNS_OUTSIDE_CONCRETE_WALLS", count=wstats["dropped_outside_rcc"]))
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