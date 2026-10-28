from __future__ import annotations
from dataclasses import dataclass, field
import hashlib
import math
import re
from app.engine.measure import opening_rules as OPR
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.orientation import carry as OC, frame as OF, turn as OT
from app.modules.drawings_boq.takeoff.extract import members as M
from app.modules.drawings_boq.takeoff.extract import rooms as R
from app.modules.drawings_boq.takeoff.extract import pageroles as PRL
from app.modules.drawings_boq.takeoff.extract import geo_safe as GS
from app.modules.drawings_boq.takeoff.extract import scaleplausible as SP
from app.modules.drawings_boq.takeoff.extract import spec_facts as SPF
from app.modules.drawings_boq.takeoff.extract import floor_layers as FLL
from app.modules.drawings_boq.takeoff.extract.sheetkind import sheet_kind
from app.modules.drawings_boq.takeoff.extract import walls as W
from app.modules.drawings_boq.takeoff.extract import rcc as RC
from app.modules.drawings_boq.takeoff.extract import rcc_ring as RR
from app.modules.drawings_boq.takeoff.extract import completion as CP
from app.modules.drawings_boq.takeoff.extract import rules as QR
from app.modules.drawings_boq.takeoff.extract import neck as NK
from app.modules.drawings_boq.takeoff.extract import footing_pairs as FP
from app.modules.drawings_boq.takeoff.extract import column_marks as CM
from app.modules.drawings_boq.takeoff.extract import wide_openings as WO
from app.modules.drawings_boq.takeoff.extract import lintel_heads as LH
from app.modules.drawings_boq.takeoff.extract import beam_sections as BS
from app.modules.drawings_boq.takeoff.extract import tank_sections as TS
from app.modules.drawings_boq.takeoff.extract import tank_steel as TSTEEL
from app.modules.drawings_boq.takeoff.extract import site_items as SI
from app.modules.drawings_boq.takeoff.extract import boundary as BDY
from app.modules.drawings_boq.takeoff.extract import staging as STG
from app.modules.drawings_boq.takeoff.extract import drainage as DR
from app.modules.drawings_boq.takeoff.extract import piles_rafts as PRF
from app.modules.drawings_boq.takeoff.extract import electrical as EL
from app.modules.drawings_boq.takeoff.extract import sheet_identity as SID
from app.modules.drawings_boq.takeoff.extract import opening_check as OK
from app.modules.drawings_boq.takeoff.extract import opening_symbols as OS
from app.modules.drawings_boq.takeoff.prep import tank_details as TD
from app.modules.drawings_boq.takeoff.extract import dashed_openings as DO
from app.modules.drawings_boq.takeoff.extract import hosts as H
from app.modules.drawings_boq.takeoff.extract import wall_net as WN
from app.modules.drawings_boq.takeoff.extract import band_count as BC
from app.modules.drawings_boq.takeoff.extract import slab_projection as SPJ
from app.modules.drawings_boq.takeoff.extract import slab_panels as SPN
from app.modules.drawings_boq.takeoff.extract import slab_plan as SPL
from app.modules.drawings_boq.takeoff.extract import beam_marks as BM
from app.modules.drawings_boq.takeoff.extract import plan_regions as PR
from app.modules.drawings_boq.takeoff.extract import foundation as FD
from app.modules.drawings_boq.takeoff.extract import finishes as FN
from app.modules.drawings_boq.takeoff.extract import openings_area as OA
from app.modules.drawings_boq.takeoff.extract import earth_fill as EF
from app.modules.drawings_boq.takeoff.extract import roof_treatment as RF
from app.modules.drawings_boq.takeoff.extract import flights as FL
from app.modules.drawings_boq.takeoff.extract import slab_openings as SO
from app.modules.drawings_boq.takeoff.extract import stair_external as SX
from app.modules.drawings_boq.takeoff.extract import structure as ST
from app.modules.drawings_boq.takeoff.extract import column_census as CS
from app.modules.drawings_boq.takeoff.extract import beam_strips as BSP
from app.modules.drawings_boq.takeoff.extract import beam_net as BN
from app.modules.drawings_boq.takeoff.levels import level_spec
from app.modules.drawings_boq.takeoff.prep import census
from app.modules.drawings_boq.takeoff.prep import lintels as LT
from app.modules.drawings_boq.takeoff.prep import steel_notes as SN
from app.modules.drawings_boq.takeoff.prep import schedules as S
from app.modules.drawings_boq.takeoff.prep import stairs as STR
from app.modules.drawings_boq.takeoff.prep import views as VW
from app.modules.drawings_boq.takeoff.extract import round_columns as RND
from app.modules.drawings_boq.takeoff.prep.details import norm_mark as ST_norm
from app.modules.drawings_boq.takeoff.prep.texts import build_lines, find_units_hint, is_tag
from app.modules.drawings_boq.takeoff.prep import mark_vocab as MV
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

def _tag_candidates(index, words, shapes, f, hint, heights, ctx, openings=None, view=None, groups=None, imperial: bool = False, footing: dict | None = None, col_details: dict | None = None, marks: dict | None = None) -> list:
  """view: one drawing of a composite sheet (its marks are counted inside it only). groups: the marks already found in that view.
  footing: {"assigned": {mark: (a, b)}, "assumed": bool, "options": [...]} the footing sizes read from the footing section details."""
  if groups is None:
    groups = M.tag_members(words, shapes, f, hint, openings, **(marks or {}))
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
      detail = ((footing or {}).get("stair") if g.get("stair") else (footing or {}).get("assigned", {}).get(tag)) if cat == "FOOTING" else None
      if cat == "FOOTING" and not g.get("stair") and ((footing or {}).get("pair_of") or {}).get(tag):
        facts["paired_column"] = list(footing["pair_of"][tag])
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
        
        if g.get("stair"):
          sn = C.note("FOOTING_SIZE_BY_ELIMINATION")
          sn["message"] = FP.stair_message(detail)
          notes.append(sn)
          base *= 0.8
        elif footing.get("assumed") and footing.get("basis") == "PAIRS":
          pn = C.note("FOOTING_SIZE_PAIRED", options_mm=footing["options"])
          pn["message"] = FP.paired_message(footing, tag)
          notes.append(pn)
          facts["footing_pairing"] = {"basis": "PAIRS", "evidence": [dict(e) for e in footing["evidence"]]}
          base *= 0.85
        elif footing.get("assumed"):
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
  """A wall and a column take the floor-to-floor height of the floor (the QS, S5); the clear height is the fallback."""
  return QR.floor_heights(heights, floor_heights, level_hint, _ft_in, _with_clear_height)

def _with_clear_height(heights: dict, floor_heights: dict | None, level_hint: str | None) -> dict:
  """The height notes of the sheet, with the clear storey height printed on the building sections added for the floor this plan shows. A height
  written as a note on the plan itself is kept; the section height only fills a gap."""
  fh = (floor_heights or {}).get(level_hint or "")
  
  if not fh or not fh.get("clear_mm"):
    return heights
  how = "given by the room notes of the plans (ceiling height)" if fh.get("basis") == "PLAN_NOTES" else "printed on the building section"
  entry = {"mm": float(fh["clear_mm"]), "text": f"clear storey height {_ft_in(float(fh['clear_mm']))} {how}", "basis": "SECTION"}
  out = dict(heights)
  for cat in ("WALL", "COLUMN"):
    out.setdefault(cat, entry)
  return out

def _height_note(h: dict) -> dict:
   return C.note("HEIGHT_FROM_SECTION" if h.get("basis") == "SECTION" else "HEIGHT_FROM_QS" if h.get("basis") == "QS" else "HEIGHT_FROM_NOTE", text=h["text"], **({"origin": h["origin"]} if h.get("origin") else {}))

def _mark_by_size(a: float, b: float, col_details: dict | None) -> tuple:
  """(mark, how): the mark of the one column detail that has this size within MARK_BY_SIZE_TOL_MM, else (UNMARKED-<size>, "NAMED")."""
  want = sorted((float(a), float(b)))
  hits = sorted(m for m, rec in (col_details or {}).items() if any(len(s) == 2 and all(abs(x * 25.4 - y) <= C.MARK_BY_SIZE_TOL_MM for x, y in zip(sorted(s), want)) for s in (rec.get("sizes_in") or [])))
  if len(hits) == 1:
    return hits[0], "DETAIL"
  return f"UNMARKED-{round(want[0] / 25.4):g}x{round(want[1] / 25.4):g}" if want[0] else "UNMARKED", "NAMED"

def _unmarked_columns(v: dict, squares: list, f: float, ctx: dict, imperial: bool, heights: dict | None = None, col_details: dict | None = None) -> Candidate | None:
  """A framing view with no column marks at all (a mumty or a stair head) still shows its columns as black squares."""
  sized = [s for s in squares if 150.0 <= s["a"] <= 600.0 and s["b"] <= 900.0]
  if not sized:
    return None
  a = sorted(s["a"] for s in sized)[len(sized) // 2]
  b = sorted(s["b"] for s in sized)[len(sized) // 2]
  a, b = (_snap_inch(a), _snap_inch(b)) if imperial else (M._round5(a), M._round5(b))
  work_item, mode, kind = C.SUGGESTIONS["COLUMN"]
  mark, how = _mark_by_size(a, b, col_details)
  notes = [C.note("UNMARKED_COLUMNS"), C.note("COLUMN_SIZE_FROM_PLAN"), C.note("COLUMN_MARK_FROM_SIZE", mark=mark, how=how)]
  h = (heights or {}).get("COLUMN")
  
  if h:
    notes.append(_height_note(h))
  spec = level_spec(v.get("level_hint"))
  label = f"Columns (no mark) ×{len(sized)}· {_fmt_mm(a)}×{_fmt_mm(b)} mm" + (f" · {spec[0]}" if spec else "")
  facts = {"tag": mark, "mark_from_size": how, "count": len(sized), "size_drawn_mm": [a, b], "size_used_mm": [a, b], "matched_shapes": len(sized),
    "view": {"key": v["key"], "caption": v["caption"], "kind": v["kind"], "level_hint": v.get("level_hint")}}
  cand = Candidate(key=_key("COLUMN", "UNMARKED", v["key"]), category="COLUMN", kind=kind, quantity_mode=mode, label=label, tag=mark,
    geometry={"points": [[round(s["cx"], 4), round(s["cy"], 4)] for s in sized]},
    params={"length_mm": a, "width_mm": b, "dims_basis": "DRAWN", **({"depth_mm": h["mm"]} if h else {})},
    missing=[] if h else ["height_mm"], work_item=work_item, status="VALID", confidence=0.0, facts=facts, notes=notes, source="TAG_SCAN", count=len(sized))
  return _finish(cand, ctx, 0.6)

def _unmarked_round_columns(v: dict, rounds: list, f: float, ctx: dict, imperial: bool, heights: dict | None = None) -> list:
  """A framing view with no column marks also shows round columns as circles. One item for each size of circle (diameters within the same tolerance as the squares', named to the half inch, or to 5 mm), counted as the square of the
  same area, the way piles are (side = diameter x root pi / 2)."""
  by: list = []
  for r in sorted(rounds, key=lambda r: r["d"]):
    if by and CS.same_size((r["d"],), (by[-1][0]["d"],)):
      by[-1].append(r)
    else:
      by.append([r])
  work_item, mode, kind = C.SUGGESTIONS["COLUMN"]
  h = (heights or {}).get("COLUMN")
  spec = level_spec(v.get("level_hint"))
  out: list = []
  for rs in by:
    mid = sum(r["d"] for r in rs) / len(rs)
    d = round(_snap_inch(2.0 * mid) / 2.0, 1) if imperial else M._round5(mid)
    side = round(d * math.sqrt(math.pi) / 2.0, 1)
    notes = [C.note("UNMARKED_COLUMNS"), C.note("COLUMN_SIZE_FROM_PLAN")]
    if h:
      notes.append(_height_note(h))
    label = f"Round columns (no mark) ×{len(rs)} · {_fmt_mm(d)} mm dia" + (f" · {spec[0]}" if spec else "")
    facts = {"tag": None, "count": len(rs), "size_drawn_mm": [d, d], "size_used_mm": [side, side], "section": "CIRCULAR", "diameter_mm": d, "equivalent_square_mm": side,
      "matched_shapes": len(rs), "view": {"key": v["key"], "caption": v["caption"], "kind": v["kind"], "level_hint": v.get("level_hint")}}
    cand = Candidate(key=_key("COLUMN", "UNMARKED", "ROUND", v["key"], round(d)), category="COLUMN", kind=kind, quantity_mode=mode, label=label, tag=None,
      geometry={"points": [[round(r["cx"], 4), round(r["cy"], 4)] for r in rs]},
      params={"length_mm": side, "width_mm": side, "dims_basis": "DRAWN", **({"depth_mm": h["mm"]} if h else {})},
      missing=[] if h else ["height_mm"], work_item=work_item, status="VALID", confidence=0.0, facts=facts, notes=notes, source="TAG_SCAN", count=len(rs))
    out.append(_finish(cand, ctx, 0.55))
  return out

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

def _column_marks(cands: list) -> list:
  """The columns a framing plan lists, for the shape count: [{"tag", "count", "sizes_mm"}], the plan size first and then the detail size."""
  out = []
  for c in cands:
    f = c.facts or {}
    if c.category != "COLUMN" or f.get("neck_of") or f.get("from_shapes"):
      continue
  
    sizes: list = []
    for k in ("size_drawn_mm", "size_detail_mm", "size_used_mm"):
      v = f.get(k)
      if v and not any(CS.same_size(v, x) for x in sizes):
        sizes.append((float(v[0]), float(v[1])))
    out.append({"tag": c.tag, "count": int(c.count or 0), "sizes_mm": [list(x) for x in sizes]})
  return out

def _beam_width_mm(widths: list, imperial: bool) -> float:
  """The width of a strip beam: the middle of the widths measured on its legs, taken to a whole number of inches on a drawing in inches."""
  mid = sorted(widths)[len(widths) // 2]
  n = round(mid / 25.4)
  return round(n * 25.4, 1) if imperial and n >= 1 and abs(mid - n * 25.4) <= C.BEAM_WIDTH_SNAP_TOL * mid else round(mid, 1)

def _apply_strips(index, view: dict, words: list, cands: list, f: float, ctx: dict, imperial: bool, sections: list | None, level_hint: str | None, squares: list | None = None) -> dict | None:
  beams = [c for c in cands if c.category == "BEAM" and c.tag and not (c.facts or {}).get("derived_from")]
  tags = {str(c.tag).strip().upper() for c in beams}
  marks = [(w.text.strip().upper(), w.cx, w.cy, w.angle) for w in words if w.text.strip().upper() in tags]
  segments, _, truncated = index.window(*view["bbox"], max_segments=C.STRIP_MAX_SEGMENTS)
  
  if truncated:
    return None
  res = BSP.read(segments, marks, f)
  if not res["legs"] and not marks:
    return None

  by = BSP.by_tag(res)
  spec = level_spec(level_hint)
  where = f" · {spec[0]}" if spec else ""
  for c in beams:
    tag = str(c.tag).strip().upper()
    legs = by.get(tag)
    missed = res["unplaced"].get(tag, 0)
    if not legs:
      if missed:
        c.notes.append(C.note("BEAM_MARK_WITHOUT_STRIP", marks=missed, strips=0))
        c.status = _status(c.notes)
      continue
  
    net = BN.net_legs(legs, squares or [], f)
    total = net["net_mm"]
    width = _beam_width_mm([l["width_mm"] for l in legs], imperial)
    longest = max(legs, key=lambda l: l["length_mm"])
    marks_printed = int(c.count or 0)
    c.work_item, c.quantity_mode, c.kind = "CON-RCC", "COUNT_X_VOLUME", "COUNT"
    c.count = 1
    
    c.geometry = {"points": [[round((longest["p0"][0] + longest["p1"][0]) / 2.0, 4), round((longest["p0"][1] + longest["p1"][1]) / 2.0, 4)]]}
    c.params = {"length_mm": round(total, 1), "width_mm": width, "dims_basis": "DRAWN"}
    c.missing = ["depth_mm"]
    c.notes = [n for n in c.notes if n.get("code") != "BEAM_LENGTH_NOT_READ"]
    c.notes.append(C.note("BEAM_LENGTH_FROM_STRIPS", strips=len(legs), length_m=round(total / 1000.0, 3)))
    joined = [l for l in legs if l.get("joined")]
    if joined:
      c.notes.append(C.note("BEAM_STRIPS_JOINED", runs=len(joined), joins=sum(l["joined"] for l in joined), length_change_m=round(sum(l["join_delta_mm"] for l in joined) / 1000.0, 3)))
    
    if net["columns"]:
      nn = C.note("BEAM_NET_OF_COLUMNS", gross_m=round(net["gross_mm"] / 1000.0, 3), taken_m=round(net["taken_mm"] / 1000.0, 3), columns=net["columns"])
      nn["message"] = (f"The strips are {net['gross_mm'] / 1000.0:.2f} m from column centre to column centre. The width of the {net['columns']} column{'s' if net['columns'] != 1 else ''} they run into "
        f"({net['taken_mm'] / 1000.0:.2f} m) is taken off, so the beam is {total / 1000.0:.2f} m between column faces: the column concrete is counted in the column.")
      c.notes.append(nn)
    inferred = [l for l in legs if l["via"] != "LABEL"]
    if inferred:
      c.notes.append(C.note("BEAM_STRIP_MARK_FROM_NEIGHBOUR", strips=len(inferred), length_m=round(sum(l["length_mm"] for l in inferred) / 1000.0, 3)))
      
    if missed:
      c.notes.append(C.note("BEAM_MARK_WITHOUT_STRIP", marks=missed, strips=len(legs)))
    if not BS.apply_marked(c, sections or []):
      BS.list_for_strips(c, sections or [])
    c.facts.update({"from_strips": True, "count": 1, "marks_printed": marks_printed, "strip_count": len(legs), "length_m": round(total / 1000.0, 3), "beam_width_mm": width,
      "length_gross_m": round(net["gross_mm"] / 1000.0, 3), "columns_taken": net["columns"], "strip_joins": sum(l.get("joined") or 0 for l in legs),
      "level_hint": level_hint, "strips": [{"p0": l["p0"], "p1": l["p1"], "length_mm": l["length_mm"], "net_mm": n, "via": l["via"]} for l, n in zip(legs, net["legs"])]})
    c.label = f"{c.tag} · {total / 1000.0:.2f} m × {_inch_label(width)} in · {len(legs)} strip{'s' if len(legs) != 1 else ''}{where}"
    c.status = _status(c.notes)
  orphans = by.get(None)
  
  if orphans:
    net = BN.net_legs(orphans, squares or [], f)
    total = net["net_mm"]
    width = _beam_width_mm([l["width_mm"] for l in orphans], imperial)
    longest = max(orphans, key=lambda l: l["length_mm"])
    notes = [C.note("BEAM_STRIP_NO_MARK", strips=len(orphans)), C.note("BEAM_LENGTH_FROM_STRIPS", strips=len(orphans), length_m=round(total / 1000.0, 3))]
    joined = [l for l in orphans if l.get("joined")]
    if joined:
      notes.append(C.note("BEAM_STRIPS_JOINED", runs=len(joined), joins=sum(l["joined"] for l in joined), length_change_m=round(sum(l["join_delta_mm"] for l in joined) / 1000.0, 3)))
    facts = {"from_strips": True, "count": 1, "tag": None, "strip_count": len(orphans), "length_m": round(total / 1000.0, 3), "beam_width_mm": width, "level_hint": level_hint,
      "length_gross_m": round(net["gross_mm"] / 1000.0, 3), "columns_taken": net["columns"],
      "strips": [{"p0": l["p0"], "p1": l["p1"], "length_mm": l["length_mm"], "net_mm": n, "via": None} for l, n in zip(orphans, net["legs"])]}
    
    if view.get("key"):
      facts["view"] = {"key": view["key"], "caption": view["caption"], "kind": view["kind"], "level_hint": view.get("level_hint")}
    cand = Candidate(key=_key("BEAM", "STRIPS", view.get("key") or level_hint or ""), category="BEAM", kind="COUNT", quantity_mode="COUNT_X_VOLUME",
      label=f"Beam strips (no mark) · {total / 1000.0:.2f} m × {_inch_label(width)} in · {len(orphans)} strip{'s' if len(orphans) != 1 else ''}{where}", tag=None,
      geometry={"points": [[round((longest["p0"][0] + longest["p1"][0]) / 2.0, 4), round((longest["p0"][1] + longest["p1"][1]) / 2.0, 4)]]},
      params={"length_mm": round(total, 1), "width_mm": width, "dims_basis": "DRAWN"}, missing=["depth_mm"], work_item="CON-RCC", status="VALID", confidence=0.0, facts=facts,
      notes=notes, source="VECTOR_SNAP", count=1)
    cands.append(_finish(cand, ctx, 0.5))
    
  by_tag_m = {str(t): round(sum(l["length_mm"] for l in ls) / 1000.0, 3) for t, ls in by.items() if t is not None}
  return {"legs": len(res["legs"]), "length_m": round(sum(l["length_mm"] for l in res["legs"]) / 1000.0, 3), "by_tag": by_tag_m,
    "unmarked_m": round(sum(l["length_mm"] for l in orphans or []) / 1000.0, 3), "unplaced_marks": res["unplaced"], "level_hint": level_hint}

def _structure_candidates(index, views: list, f: float, hint, heights, ctx, imperial: bool, view_scales: dict | None = None, col_details: dict | None = None,
  floor_heights: dict | None = None, beam_sections: list | None = None, marks: dict | None = None) -> tuple:
  """A sheet that shows several structural plans (foundation, basement / ground / first framing plans, mumty framing plan): each plan is read on
  its own, so the C1 marks of the ground floor are not added to the C1 marks of the first floor. Footings are read from the foundation plan only

  (the framing plans repeat the footing marks beside the columns)."""
  plans = [v for v in views if v["structural"]]
  squares = ST.dedupe_solid(ST.square_shapes(index.rings, f), f)
  pool = ST.dedupe_solid(M.member_shapes(index.rings, f) + squares, f)
  shapes_by = VW.split(pool, views, lambda s: (s["cx"], s["cy"]))
  squares_by = VW.split(squares, views, lambda s: (s["cx"], s["cy"]))
  rounds_by: dict | None = None
  words_by = VW.split(index.words, views, lambda w: (w.cx, w.cy))
  sizes = ST.footing_sizes(index.words, hint, imperial)
  out: list = []
  stats: list = []
  found: dict = {}
  
  for v in plans:
    ws, sh = words_by.get(v["key"], []), shapes_by.get(v["key"], [])
   
    keep = ("FOOTING",) if v.get("foundation") else ("COLUMN", "BEAM")
    found[v["key"]] = [g for g in M.tag_members(ws, sh, f, hint, None, plan_view=True, **{**(marks or {}), "plan_kind": "FOUNDATION" if v.get("foundation") else (marks or {}).get("plan_kind")})
      if g["category"] in keep]
  
  seen: dict = {}
  for gs in found.values():
    for g in gs:
      if g["category"] == "COLUMN" and g.get("drawn_mm"):
        seen.setdefault(g["tag"], []).append(g["drawn_mm"])
        
  column_mm: dict = {}
  for tag, ds in seen.items():
    column_mm[ST_norm(tag)] = max(set(ds), key=ds.count)
  for tag, rec in (col_details or {}).items():
    if rec.get("size_mm") and not rec.get("disagree"):
      column_mm[tag] = rec["size_mm"]
      
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
      stair_words = ST.stair_footings(ws)
      footing = FP.assign(groups, sizes, FP.summary(FP.label_pairs(ws)), column_mm, len(stair_words))
      for w in stair_words:
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
      if rounds_by is None:
        rounds_by = VW.split(RND.circles(index, f, index.words), views, lambda r: (r["cx"], r["cy"]))
      cands.extend(_unmarked_round_columns(v, rounds_by.get(v["key"], []), f, ctx, imperial, view_heights))
    strip_stats = None if v.get("foundation") else _apply_strips(index, v, ws, cands, f, ctx, imperial, beam_sections, v.get("level_hint"), squares_by.get(v["key"], []))
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
      "slab_panels": v.get("slab_panels", 0), "slab_note_mm": v.get("slab_note_mm"),
      "column_marks": [] if v.get("foundation") else _column_marks(cands), "beam_strips": strip_stats})
  _settle_hidden_columns(out)
  CM.apply(out, CM.findings(out, col_details), _status)
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
      c.facts["tank_kind"] = TD.kind_of(w.text)
      c.notes.append(C.note("TANK_WALL"))
      c.status = _status(c.notes)
      marked += 1
  return marked

def _outer_box(frames: list, runs: list, f: float) -> tuple | None:
  """The ground the walls of a plan stand on: the box round the runs that are 9 inch or thicker and meet another wall at both ends."""
  pts = []
  for r in runs:
    if r.t_pt * f >= C.OUTER_CORE_MIN_MM and r.end0 != "FREE" and r.end1 != "FREE":
      fr = frames[r.peak]
      pts += [fr.pt(r.s0 - r.ext0, r.dc), fr.pt(r.s1 + r.ext1, r.dc)]
  if len(pts) < 6:
    return None
  tol = max(1.5, C.OUTER_TOL_MM / f)
  return min(p[0] for p in pts) - tol, min(p[1] for p in pts) - tol, max(p[0] for p in pts) + tol, max(p[1] for p in pts) + tol

def _tread_ladders(walls: list, f: float) -> set:
  """The wall candidates (by id) that are really the treads of a stair: at least LADDER_MIN_RUNGS lines of one length and one direction, stacked
  one step apart (a step is at most LADDER_MAX_STEP_MM) at an even spacing. On a plan drawn small, a tread pair looks like a thin wall."""
  items = []
  for c in walls:
    (x0, y0), (x1, y1) = c.geometry["points"]
    length = math.hypot(x1 - x0, y1 - y0)
    if length <= 0.0:
      continue
    ang = math.degrees(math.atan2(y1 - y0, x1 - x0)) % 180.0
    items.append((c, ang, length, (x0 + x1) / 2.0, (y0 + y1) / 2.0))
  gone: set = set()
  step_max = C.LADDER_MAX_STEP_MM / f
  for i, (_, a0, l0, _, _) in enumerate(items):
    group = [it for it in items if min(abs(it[1] - a0), 180.0 - abs(it[1] - a0)) <= 3.0 and abs(it[2] / l0 - 1.0) <= C.LADDER_LENGTH_TOL]
    if len(group) < C.LADDER_MIN_RUNGS:
      continue
  
    rad = math.radians(a0)
    ux, uy = math.cos(rad), math.sin(rad)
    stacked = sorted(((-it[3] * uy + it[4] * ux, it[3] * ux + it[4] * uy, it) for it in group), key=lambda t: t[0])
    chain: list = []
    for t in stacked + [None]:
      if t is not None and chain and 0.0 <= t[0] - chain[-1][0] <= step_max and abs(t[1] - chain[-1][1]) <= 0.6 * l0:
        chain.append(t)
        continue
    
      if len(chain) >= C.LADDER_MIN_RUNGS:
        steps = sorted(b[0] - a[0] for a, b in zip(chain, chain[1:]) if b[0] - a[0] > 0.5)
        mid = steps[len(steps) // 2] if steps else 0.0
        if len(steps) + 1 >= C.LADDER_MIN_RUNGS and all(abs(s - mid) <= C.LADDER_STEP_TOL * mid for s in steps):
          gone.update(id(x[2][0]) for x in chain)
      chain = [t] if t is not None else []
  return gone

def _wall_candidates(index, f, heights, ctx, deadline, imperial: bool = False, at_grade: bool = False, outer_only: bool = False, wall_vocab: list | None = None) -> tuple:
  frames, runs, stats = W.detect_walls(index, f, deadline, at_grade)
  rcc = RC.rcc_runs(index.rings, f)
  stats["rcc_runs"] = len(rcc)
  stats["dropped_stubs"] = 0
  stats["dropped_on_rcc"] = 0
  stats["dropped_outside_rcc"] = 0
  stats["dropped_outside_plan"] = 0
  stats["outside_plan_m"] = 0.0
  outer = _outer_box(frames, runs, f) if outer_only else None
  box = RC.envelope(rcc, f) if rcc else None
  extra = W.bridge_ends(runs, frames, f)
  stats["bridged_ends"] = sum(1 for v in extra.values() for x in v if x > 0.0)
  
  out = []
  for r in runs:
    fr = frames[r.peak]
    add0, add1 = extra.get(id(r), (0.0, 0.0))
    p0, p1 = fr.pt(r.s0 - r.ext0 - add0, r.dc), fr.pt(r.s1 + r.ext1 + add1, r.dc)
    t_mm = r.t_pt * f
    std, use_t = W.snap_thickness(t_mm, imperial, wall_vocab)
    cc_m = ((r.s1 + r.ext1 + add1) - (r.s0 - r.ext0 - add0)) * f / 1000.0
    clear_m = r.clear_pt * f / 1000.0
    if std is None and cc_m * 1000.0 < C.WALL_STUB_MAX_MM:
      stats["dropped_stubs"] += 1
      continue
  
    if outer is not None and not (outer[0] <= (p0[0] + p1[0]) / 2.0 <= outer[2] and outer[1] <= (p0[1] + p1[1]) / 2.0 <= outer[3]):
      stats["dropped_outside_plan"] += 1
      stats["outside_plan_m"] = round(stats["outside_plan_m"] + cc_m, 2)
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
      if max(gaps) > C.WALL_GAP_MAX_MM:
        notes.append(C.note("WALL_WIDE_OPENING", widest_mm=max(gaps)))
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
    
    if r.pen_kept:
      facts["light_pen"] = True
      notes.append(C.note("LIGHT_PEN_WALL"))
    if add0 > 0.0 or add1 > 0.0:
      facts["bridged_mm"] = [round(add0 * f), round(add1 * f)]
      notes.append(C.note("WALL_BRIDGED"))
    key = _key("WALL", round(p0[0] / 2), round(p0[1] / 2), round(p1[0] / 2), round(p1[1] / 2))
    work_item, mode, kind = C.SUGGESTIONS["WALL"]
    
    cand = Candidate(key=key, category="WALL", kind=kind, quantity_mode=mode, label=f"Wall {_fmt_mm(use_t)} mm · {cc_m:.2f} m", tag=None,
      geometry={"points": [[round(p0[0], 4), round(p0[1], 4)], [round(p1[0], 4), round(p1[1], 4)]], "closed": False}, params=params,
      missing=missing, work_item=work_item, status="VALID", confidence=0.0, facts=facts, notes=notes, source="VECTOR_SNAP", count=1)
    out.append(_finish(cand, ctx, base))
  if outer_only:
    treads = _tread_ladders(out, f)
    if treads:
      stats["dropped_treads"] = len(treads)
      stats["treads_m"] = round(sum(c.facts["length_cc_m"] for c in out if id(c) in treads), 2)
      out = [c for c in out if id(c) not in treads]
  for rc in rcc:
    t_mm = rc["t_mm"]
    std, use_t = W.snap_thickness(t_mm, imperial, wall_vocab)
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
  stats["rcc_ring"] = RR.ring_gaps(rcc, f) if rcc else None
  out.sort(key=lambda c: (c.facts.get("construction") == "RCC", -c.facts["thickness_used_mm"], -c.facts["length_cc_m"]))
  return frames, runs, out, stats

def _stage(res, stage: str, fn, default):
  try:
    return fn()
  except W.TimeLimit:
    raise
  except Exception as exc:
    res.notes.append(C.note("STAGE_FAILED", stage=stage, error=type(exc).__name__, detail=str(exc)[:160]))
    res.stats.setdefault("stage_failures", []).append({"stage": stage, "error": type(exc).__name__})
    return default

def _room_candidates(index, frames, runs, lines, f, hint, ctx, res=None, walls=None) -> list:
  gstats: dict = {}
  faces = R.wall_faces(runs, frames, gstats)
  if res is not None:
    if gstats.get("repaired"):
      res.notes.append(C.note("ROOM_GEOMETRY_REPAIRED", count=gstats["repaired"]))
    if gstats.get("dropped"):
      res.notes.append(C.note("ROOM_FACE_SKIPPED", count=gstats["dropped"]))
      
  k = f * f / 1e6
  faces = [p for p in faces if C.ROOM_MIN_M2 <= p.area * k <= C.ROOM_MAX_M2]
  names, sizes = R.labels(lines, hint)
  pairs = [p for p in R.pair_labels(names, sizes, f) if R.plausible_room(p)]
  closed = []
  try:
    closed = [(p, n, w) for p, n, w in R.closed_faces(runs, frames, R.gap_bridges(walls or [], f, C.WALL_GAP_MAX_MM), faces) if C.ROOM_MIN_M2 <= p.area * k <= C.ROOM_MAX_M2]
  except W.TimeLimit:
    raise
  except Exception as exc:
    if res is not None:
      res.notes.append(C.note("ROOM_CLOSURE_SKIPPED", error=type(exc).__name__))
      
  items = [(p, "WALLS", None) for p in faces] + [(p, "CLOSED", (n, w)) for p, n, w in closed] + [(p, "OUTLINE", None) for p in R.outline_rooms(index, names, [*faces, *[c[0] for c in closed]], f)]
  out = []
  used: set = set()
  replaced: dict = {}
  
  for poly, how, via in items:
    poly = R._clean(poly)
    d = R.describe(poly, names, sizes, f)
    inside = R.pairs_inside(poly, pairs)
    if how == "CLOSED":
      if len(inside) != 1 or abs(d["area_m2"] / (pairs[inside[0]]["a_mm"] * pairs[inside[0]]["b_mm"] / 1e6) - 1.0) > C.ROOM_SIZE_TOL:
        continue
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
    base = 0.85 if how == "WALLS" else 0.8 if how == "CLOSED" else 0.65
    if how == "OUTLINE":
      notes.append(C.note("ROOM_FROM_OUTLINE"))
    if how == "CLOSED":
      notes.append(C.note("ROOM_CLOSED_ACROSS_OPENINGS", openings=via[0], width_mm=via[1]))
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
    if how == "CLOSED":
      facts["closed_across"] = {"openings": via[0], "width_mm": via[1]}
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
  if res is not None:
    res.stats["room_closure"] = {"closed_rooms": sum(1 for c in out if c.facts.get("outline_from") == "CLOSED"), "faces_closed_by_openings": len(closed),
      "rooms_from_labels": sum(1 for c in out if c.facts.get("outline_from") == "LABEL")}
  return out

def _flag_nested_rooms(rooms: list) -> None:
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
    overlap = None
    if not inside and a.facts.get("outline_from") == "LABEL":

      for j, b in enumerate(rooms):
        if j == i or polys[j] is None or b.facts.get("outline_from") == "LABEL":
          continue
        
        common, _how = GS.safe_intersection(pa, polys[j])
        if common is not None and common.area >= C.ROOM_DUPLICATE_SHARE * pa.area and (overlap is None or common.area > overlap[1]):
          overlap = (j, common.area)
      if overlap is not None:
        inside = [overlap[0]]
    if inside:
      big = max(inside, key=lambda j: rooms[j].facts["area_m2"])
      extra = {"overlap_pct": round(100.0 * overlap[1] / pa.area, 1)} if overlap is not None else {}
      a.notes.append(C.note("ROOM_INSIDE_ROOM", enclosing=rooms[big].facts.get("name"), enclosing_m2=rooms[big].facts["area_m2"], **extra))
      a.facts["inside_room"] = rooms[big].facts.get("name")
      a.status = _status(a.notes)

def _inch_text(mm: float) -> str:
  return f"{mm / 25.4:g}\""

def _section_label(values: list, note_mm: float, implied_mm) -> dict | None:
  best = None
  for v in values:
    if abs(v["mm"] - note_mm) <= 1.0 or "slab" not in (v.get("scopes") or []) or int(v.get("count") or 0) < C.SLAB_LABEL_MIN_COUNT:
      continue
    if implied_mm and abs(float(implied_mm) - v["mm"]) > C.SLAB_LABEL_SECTIONS_TOL_MM:
      continue
    if best is None or int(v["count"]) > int(best["count"]):
      best = v
  return best

def _slab_thickness(note_mm, slab_values: list, implied_mm=None) -> tuple:
  values = [v for v in (slab_values or []) if v.get("mm")]
  if note_mm:
    others = [v for v in values if abs(v["mm"] - note_mm) > 1.0]
    label = _section_label(others, float(note_mm), implied_mm) if others else None
    note = lambda used: C.note("SLAB_THICKNESS_DISAGREES", plan_mm=note_mm, used=used, others=[{"mm": v["mm"], "pages": v.get("pages", []), "count": int(v.get("count") or 0)} for v in others])
    
    if label:
      return float(label["mm"]), "SECTION_LABEL", [note("SECTION_LABEL")]
    return float(note_mm), "PLAN_NOTE", [note("PLAN_NOTE")] if others else []
  if len(values) == 1:
    return float(values[0]["mm"]), "OTHER_SHEET", [C.note("SLAB_THICKNESS_FROM_OTHER_SHEET", pages=values[0].get("pages", []))]
  if len(values) > 1:
    return None, None, [C.note("SLAB_THICKNESSES_LISTED", options_mm=[v["mm"] for v in values])]
  return None, None, []

def _slab_options(t, source, slab_values: list, implied, note_mm=None) -> list:
  """Every thickness the drawing supports for one slab, each with the places that print it: the plan note or the one used, the other sheets that print a
  slab thickness, and the thickness the building sections imply (floor-to-floor height less clear storey height)."""
  out: list = []
  def add(mm, src, pages=None):
    if not mm:
      return
    for o in out:
      if abs(o["mm"] - mm) <= 1.0:
        if src not in o["sources"]:
          o["sources"].append(src)
        o["pages"] = sorted(set(o["pages"]) | set(pages or []))
        return
    out.append({"mm": float(mm), "sources": [src], "pages": sorted(set(pages or []))})
  add(t, source or "PLAN_NOTE")
  add(note_mm, "PLAN_NOTE")
  for v in slab_values or []:
    add(v.get("mm"), "OTHER_SHEET", v.get("pages"))
  add(implied, "SECTIONS")
  return out

def _implied_slab_mm(floor_heights: dict | None, hint: str | None) -> float | None:
  """The slab thickness the building sections imply for one floor: the floor-to-floor height less the clear storey height."""
  fh = (floor_heights or {}).get(hint or "") or {}
  ftf, clear = fh.get("floor_to_floor_mm"), fh.get("clear_mm")
  if not ftf or not clear:
    return None
  mm = float(ftf) - float(clear)
  return round(mm, 1) if C.SLAB_SECTION_MIN_MM <= mm <= C.SLAB_SECTION_MAX_MM else None

def _outline_axes(dims, printed: list) -> tuple | None:
  """(horizontal mm, vertical mm) of the covered area: the overall lengths printed on the plans along each direction are matched to the two sides of the
  area table's rectangle. None when they cannot be matched."""
  a, b = float(dims[0]), float(dims[1])
  def has(axis: str, v: float) -> bool:
    return any(d.get("axis") == axis and abs(float(d["mm"]) - v) <= 0.015 * v for d in printed)
  ah, av, bh, bv = has("H", a), has("V", a), has("H", b), has("V", b)
  if ah and bv and not (av and bh):
    return a, b
  if bh and av and not (ah and bv):
    return b, a
  if ah and bv and av and bh and abs(a - b) <= 0.015 * a:
    return a, b
  return None

CFT_PER_M3 = 35.3146667

def _vol_text(area_m2: float, t_mm) -> str:
  if not t_mm:
    return f"{area_m2:.2f} m²"
  m3 = area_m2 * float(t_mm) / 1000.0
  return f"{area_m2:.2f} m², {m3:.2f} m³ ({m3 * CFT_PER_M3:,.0f} cft) at {_inch_text(float(t_mm))}"

def _strip_name(r: dict) -> str:
  return f"{r['text'] or 'roof projection'} on the {r['side'].lower()}"

def _strip_notes(recs: list, t_mm) -> list:
  notes: list = []
  
  def bound(r):
    return " / ".join(SPJ.feet_text(x) for x in r["lengths_mm"]) if r["lengths_mm"] else "no length"
  out_of = [r for r in recs if r["status"] == "NOT_BOUND"]
  if out_of:
    n = C.note("SLAB_PROJECTION_NOT_BOUND", strips=[{"side": r["side"], "width_mm": r["width_mm"]} for r in out_of])
    n["message"] = ("No overall length is printed beside " + "; ".join(_strip_name(r) for r in out_of) + ", so the length of the strip is not known and it was not added to the slab. "
      "If it is slab, add it with its length (width x length x thickness): " + "; ".join(f"{_strip_name(r)} on a side of {SPJ.feet_text(r['outline_mm'])} would add {_vol_text(SPJ.strip_m2(r), t_mm)}" for r in out_of) + ".")
    notes.append(n)
    
  out_of = [r for r in recs if r["status"] == "ADDED" and r.get("assumed")]
  if out_of:
    n = C.note("SLAB_PROJECTION_LENGTH_ASSUMED", strips=[{"side": r["side"], "width_mm": r["width_mm"], "length_mm": r["length_mm"]} for r in out_of])
    n["message"] = ("No overall length is printed beside " + "; ".join(_strip_name(r) for r in out_of) + ", so the strip is taken along the whole side of the plan it stands beside: "
      + "; ".join(f"{_strip_name(r)} x {SPJ.feet_text(r['length_mm'])} adds {_vol_text(SPJ.strip_m2(r), t_mm)}" for r in out_of)
      + ". This is assumed. If the projection is shorter than the side, type its length, or take it off.")
    notes.append(n)
  out_of = [r for r in recs if r["status"] == "NOT_VERIFIED"]
  if out_of:
    n = C.note("SLAB_PROJECTION_NOT_VERIFIED", strips=[{"side": r["side"], "width_mm": r["width_mm"], "bound_mm": r["lengths_mm"], "outline_mm": r["outline_mm"]} for r in out_of])
    n["message"] = ("; ".join(f"{_strip_name(r)} is bound to the printed length {bound(r)}, but that side of the plan outline is {SPJ.feet_text(r['outline_mm'])}"
      + (f" ({SPJ.feet_text(r['outline_widened_mm'])} with the projections of its neighbours)" if abs(r["outline_widened_mm"] - r["outline_mm"]) > 1.0 else "") for r in out_of)
      + ". A strip whose length is not the side it stands beside is not added to the slab. If it is slab: " + "; ".join(f"{_strip_name(r)} over the side would add {_vol_text(SPJ.strip_m2(r), t_mm)}" for r in out_of) + ".")
    notes.append(n)
    
  out_of = [r for r in recs if r["status"] == "CHAJJA"]
  if out_of:
    n = C.note("SLAB_PROJECTION_IS_CHAJJA", strips=[{"side": r["side"], "width_mm": r["width_mm"], "length_mm": r["length_mm"]} for r in out_of], limit_mm=SPJ.chajja_max_mm())
    n["message"] = ("; ".join(f"{_strip_name(r)} runs the {SPJ.feet_text(r['length_mm'])} of its side" for r in out_of) + f". A strip of {SPJ.feet_text(SPJ.chajja_max_mm())} or less is a chajja (sunshade or drip), "
      "not slab, so it is not in the slab concrete (QS parameter slab_projection_chajja_max_mm, assumed). It would add " + "; ".join(_vol_text(SPJ.strip_m2(r), t_mm) for r in out_of)
      + " if the QS counts it in the slab.")
    notes.append(n)
  return notes

def _slab_outline(dims, proj: dict | None, t_mm=None) -> tuple:
  if not proj or not dims or len(dims) != 2:
    return None, {}, []

  sides = dict(proj.get("sides") or {})
  unplaced, conflicts = proj.get("unplaced") or [], proj.get("conflicts") or []
  if not sides and not unplaced and not conflicts:
    return None, {}, []
  notes: list = []
  
  facts: dict = {"projections": {"sides": {k: v["width_mm"] for k, v in sides.items()}, "text": {k: v["text"] for k, v in sides.items()},
    "pages": sorted({p for v in sides.values() for p in v.get("pages", [])}), "applied": False}}
  if unplaced:
    notes.append(C.note("SLAB_PROJECTION_UNPLACED", labels=[u["text"] for u in unplaced]))
  if conflicts:
    notes.append(C.note("SLAB_PROJECTION_CONFLICT", sides=[{"side": c["side"], "widths_mm": c["widths_mm"]} for c in conflicts]))
  if not sides:
    return None, facts, notes
  axes = _outline_axes(dims, proj.get("dims") or [])
  if axes is None:
    notes.append(C.note("SLAB_PROJECTION_AXIS_UNKNOWN"))
    return None, facts, notes
  
  h, v = axes
  recs = SPJ.classify(sides, axes)
  facts["projections"]["strips"] = recs
  facts["projections"]["table_dims_mm"] = [h, v]
  added = {r["side"]: r for r in recs if r["status"] == "ADDED"}
  facts["projections"]["sides"] = {k: r["width_mm"] for k, r in added.items()}
  facts["projections"]["text"] = {k: r["text"] for k, r in added.items()}
  notes.extend(_strip_notes(recs, t_mm))
  if not added:
    return None, facts, notes
  w = {k: float(added[k]["width_mm"]) if k in added else 0.0 for k in ("TOP", "BOTTOM", "LEFT", "RIGHT")}
  outline = (h + w["LEFT"] + w["RIGHT"], v + w["TOP"] + w["BOTTOM"])
  facts["projections"]["applied"] = True
  notes.append(C.note("SLAB_PROJECTIONS_ADDED", sides={k: r["text"] for k, r in added.items()}))
  return outline, facts, notes

WITNESS_NAME = {"PLAN_NOTE": "the slab note on the structural framing plan", "SECTION_LABEL": "the thickness labelled on the sections", "SECTIONS": "the building sections (floor-to-floor less clear height)"}
WITNESS_ORDER = ("PLAN_NOTE", "SECTION_LABEL", "SECTIONS")

def _thickness_volumes(options: list, length_mm, width_mm, used_mm) -> list:
  if not (length_mm and width_mm and used_mm):
    return []
  base = float(length_mm) * float(width_mm) * float(used_mm) / 1e9
  out = []
  for o in options:
    m3 = float(length_mm) * float(width_mm) * float(o["mm"]) / 1e9
    who = [k for k in WITNESS_ORDER if k in o["sources"]] or list(o["sources"])
    out.append({"mm": o["mm"], "witnesses": who, "pages": list(o.get("pages") or []), "m3": round(m3, 3), "cft": round(m3 * CFT_PER_M3, 1),
      "delta_m3": round(m3 - base, 3), "delta_cft": round((m3 - base) * CFT_PER_M3, 1), "used": abs(float(o["mm"]) - float(used_mm)) <= 1.0})
  return out

def _thickness_text(vols: list, used_mm, source) -> str:
  def who(o):
    names = [WITNESS_NAME[k] for k in o["witnesses"] if k in WITNESS_NAME]
    pages = ", ".join(str(p) for p in o["pages"])
    return " and ".join(names) + (f" (sheet {pages})" if pages else "")
  listed = "; ".join(f"{_inch_text(o['mm'])}: {who(o)} gives {o['m3']:.2f} m³ ({o['cft']:,.0f} cft)" for o in vols)
  others = [o for o in vols if not o["used"]]
  worth = "; ".join(f"{_inch_text(o['mm'])} instead of {_inch_text(float(used_mm))} changes this slab by {o['delta_m3']:+.2f} m³ ({o['delta_cft']:+,.0f} cft)" for o in others)
  how = {"SECTION_LABEL": "the thickness labelled on the sections, printed more than once and agreeing with the building sections, over a general slab note", "PLAN_NOTE": "the slab note of the framing plan"}.get(source, "the only thickness printed")
  return f"The drawing prints more than one slab thickness for this slab. {listed}. Used: {_inch_text(float(used_mm))}, {how}. {worth}. Confirm the thickness; it is the largest single choice in the slab concrete."

def _slab_candidate(plan: dict, areas: dict, slab_values: list, ctx: dict, implied_mm: float | None = None, projections: dict | None = None) -> tuple:
  hint = plan.get("level_hint")
  area = areas.get(hint) if hint else None
  spec = level_spec(hint)
  
  if area is None:
    return None, [C.note("SLAB_AREA_NOT_FOUND", floor=spec[0] if spec else hint, caption=plan.get("caption"))]
  t, source, notes = _slab_thickness(plan.get("note_mm"), slab_values, implied_mm)
  options = _slab_options(t, source, slab_values, implied_mm, plan.get("note_mm"))
  if implied_mm:
    notes.append(C.note("SLAB_THICKNESS_SECTIONS", implied_mm=implied_mm))
    for n in notes:
      if n["code"] == "SLAB_THICKNESS_DISAGREES":
        n["sections_mm"] = implied_mm
        
  params: dict = {"dims_basis": "SPECIFIED"}
  missing: list = []
  dims = area.get("dims_mm")
  base = 0.9
  outline, outline_facts, outline_notes = _slab_outline(dims, (projections or {}).get(hint) if hint else None, t)
  if dims and len(dims) == 2:
    params["length_mm"], params["width_mm"] = (float(outline[0]), float(outline[1])) if outline else (float(dims[0]), float(dims[1]))
    notes.append(C.note("SLAB_AREA_FROM_TABLE"))
    notes.extend(outline_notes)
    if outline_notes:
      base *= 0.95
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
  gross_m2 = float(outline[0]) * float(outline[1]) / 1e6 if outline else m2
  label = "Slab" + (f" {_inch_text(t)}" if t else "") + f" · {gross_m2:.2f} m²" + (f" · {spec[0]}" if spec else "")
  facts = {"floor": hint, "area_m2": m2, "area_text": f"{area['value']:g} {area['unit']}", "area_name": area.get("name"), "area_pages": area.get("pages", []),
    "thickness_mm": t, "thickness_source": source, "thickness_options": options, "thickness_sections_mm": implied_mm, "panels": plan.get("panels", 0),
    "panel_marks": plan.get("marks", [])}
  
  if dims:
    facts["dims_mm"] = [float(dims[0]), float(dims[1])]
    facts["dims_text"] = area.get("dims_text")
  facts.update(outline_facts)
  vols = _thickness_volumes(options, params.get("length_mm"), params.get("width_mm"), t)
  
  if vols:
    facts["thickness_volumes"] = vols
    if len(vols) > 1:
      for n in notes:
        if n["code"] == "SLAB_THICKNESS_DISAGREES":
          n["message"] = _thickness_text(vols, t, source)
          
  if outline:
    facts["outline_dims_mm"] = [round(float(outline[0]), 1), round(float(outline[1]), 1)]
    facts["gross_area_m2"] = round(gross_m2, 3)
    facts["projection_area_m2"] = round(gross_m2 - m2, 3)
  if t and dims:
    facts["volume_m3"] = round(float(params["length_mm"]) * float(params["width_mm"]) * t / 1e9, 4)
  if plan.get("view"):
    facts["view"] = plan["view"]
    
  work_item, mode, kind = C.SUGGESTIONS["SLAB"]
  cand = Candidate(key=_key("SLAB", hint, plan.get("key") or ""), category="SLAB", kind=kind, quantity_mode=mode, label=label, tag="SLAB",
    geometry={"points": [[round(plan["centre"][0], 4), round(plan["centre"][1], 4)]]}, params=params, missing=missing, work_item=work_item,
    status="VALID", confidence=0.0, facts=facts, notes=notes, source="PRINTED", count=1)
  cand.status = _status(cand.notes)
  cand.confidence = round(max(0.0, min(1.0, base * ctx["content_factor"])), 4)
  return cand, []

def _slab_panel_candidates(found: dict, note_mm, level_hint: str | None, slab_values: list, ctx: dict, implied_mm: float | None) -> list:
  t, source, thickness_notes = _slab_thickness(note_mm, slab_values, implied_mm)
  options = _slab_options(t, source, slab_values, implied_mm, note_mm)
  spec = level_spec(level_hint) if level_hint else None
  work_item, mode, kind = C.SUGGESTIONS["SLAB"]
  out = []
  for g in found["panels"]:
    each = g["length_mm"] * g["width_mm"] / 1e6
    notes = [dict(n) for n in thickness_notes]

    n = C.note("SLAB_PANELS_FROM_LABELS", size=g["text"], printed=g["count"])
    n["message"] = (f"This slab is read from the panel size {g['text']} written on the slab plan, which is printed {g['count']} time{'s' if g['count'] != 1 else ''} in the view with the bar strings ({each:.2f} m\u00b2 each). "
      f"The plan prints {found['labels']} panel sizes in all, {found['area_m2']:.1f} m\u00b2. The size is the printed one, not measured. A size is often printed once for several equal panels and a panel can have no size printed; "
      "look at the plan and set the count to the number of panels of this size. Beams and the stair well are not in these panels.")
    notes.append(n)
    if not level_hint:
      notes.append(C.note("SLAB_FLOOR_NOT_NAMED"))
    params: dict = {"dims_basis": "SPECIFIED", "length_mm": g["length_mm"], "width_mm": g["width_mm"]}
    missing: list = []
    base = 0.75
    if t:
      params["depth_mm"] = t
    else:
      missing.append("thickness_mm")
      base *= 0.8
    facts = {"floor": level_hint, "panel_basis": "PRINTED_PANEL_SIZE", "panel_text": g["text"], "panels_printed": g["count"], "panel_area_m2": round(each, 3), "sheet_panel_labels": found["labels"],
      "sheet_panel_area_m2": found["area_m2"], "bar_strings": found["string_text"][:8], "thickness_mm": t, "thickness_source": source, "thickness_options": options, "thickness_sections_mm": implied_mm,
      "dims_mm": [g["length_mm"], g["width_mm"]]}
    vols = _thickness_volumes(options, g["length_mm"], g["width_mm"], t)
    if vols:
      facts["thickness_volumes"] = vols
      if len(vols) > 1:
        for x in notes:
          if x["code"] == "SLAB_THICKNESS_DISAGREES":
            x["message"] = _thickness_text(vols, t, source)

    label = "Slab panel " + g["text"] + (f" · {_inch_text(t)}" if t else "") + (f" · {spec[0]}" if spec else "")
    cand = Candidate(key=_key("SLAB", "PANEL", level_hint or "", round(g["length_mm"]), round(g["width_mm"])), category="SLAB", kind=kind, quantity_mode=mode, label=label, tag="SLAB",
      geometry={"points": [g["points"][0]]}, params=params, missing=missing, work_item=work_item, status="VALID", confidence=0.0, facts=facts, notes=notes, source="PRINTED", count=int(g["count"]))
    cand.status = _status(cand.notes)
    cand.confidence = round(max(0.0, min(1.0, base * ctx["content_factor"])), 4)
    out.append(cand)
  return out

THIN_WALL_MM = 160.0

def _hosted_by_tag(by_wall: dict, walls: list, by_point: dict | None = None) -> dict:
  wall_of = {w.key: w for w in walls}
  out: dict = {}
  kind_of: dict = {}
  for key, ops in (by_wall or {}).items():
    w = wall_of.get(key)
    if w is None:
      continue
    
    t = float((w.params or {}).get("thickness_mm") or 0.0)
    rcc = (w.facts or {}).get("construction") == "RCC"
    thin = 0.0 < t < THIN_WALL_MM and not rcc
    kind_of[key] = "RCC" if rcc else "THIN" if thin else None
    for o in ops:
      if not o.get("label"):
        continue
      
      rec = out.setdefault(o["label"], {"thin": 0, "rcc": 0, "hosted": 0, "thin_mm": 0.0, "thin_pts": [], "rcc_pts": []})
      rec["hosted"] += int(o["nos"])
      rec["thin"] += int(o["nos"]) if thin else 0
      rec["rcc"] += int(o["nos"]) if rcc else 0
      if thin:
        rec["thin_mm"] = max(rec["thin_mm"], t)
  for tag, placed in (by_point or {}).items():
    rec = out.get(tag)
    if rec is None:
      continue
    
    rec["thin_pts"] = [q for q, key in placed if kind_of.get(key) == "THIN"]
    rec["rcc_pts"] = [q for q, key in placed if kind_of.get(key) == "RCC"]
  return out

def _lintel_candidates(openings: list, table: list, hosted: dict, ctx: dict, marks: list | None = None) -> list:
  out = []
  if not table:
    return out
  bearing = C.LINTEL_BEARING_MM
  
  for o in openings:
    drawn = not (o.facts or {}).get("size_schedule_mm") and bool((o.facts or {}).get("size_drawn_mm"))
    size = (o.facts or {}).get("size_schedule_mm") or ((o.facts or {}).get("size_drawn_mm") if drawn else None)
    pts = (o.geometry or {}).get("points") or []
    if o.category not in ("DOOR", "WINDOW") or not size or not o.tag or not pts:
      continue
    span = float(size[0])
    sec = LT.section_for(table, span)
    h = hosted.get(o.tag) or {}
    total = int(o.count or len(pts))
    rcc = min(int(h.get("rcc") or 0), total)
    thin = min(int(h.get("thin") or 0), total - rcc) if sec else 0
    plain = total - rcc - thin
    if marks is not None:
      marks.append({"tag": o.tag, "marks": total, "in_rcc_left_out": rcc, "in_thin_wall": thin, "other": plain})
    if plain <= 0 and thin <= 0:
      if rcc:
        o.notes.append(C.note("LINTEL_RCC_LEFT_OUT", count=rcc, marks=total))
      continue
    
    cut = {tuple(p) for p in [*(h.get("thin_pts") or []), *(h.get("rcc_pts") or [])]}
    thin_pts = [list(p) for p in pts if tuple(p) in {tuple(q) for q in h.get("thin_pts") or []}] or [list(p) for p in pts]
    plain_pts = [list(p) for p in pts if tuple(p) not in cut] or [list(p) for p in pts]
    for part, n in (("WALL", plain), ("THIN", thin)):
      if n <= 0:
        continue
      thin_part = part == "THIN"
      notes = [C.note("LINTEL_BEARING_ASSUMED", bearing_mm=bearing)]
      params: dict = {"dims_basis": "SPECIFIED"}
      missing: list = []
      base = 0.85
      if drawn:
        notes.append(C.note("OPENING_FROM_SYMBOLS"))
        base *= 0.8
      facts = {"opening_tag": o.tag, **({"size_basis": "DRAWN_SYMBOL"} if drawn else {}), "opening_kind": (o.facts or {}).get("opening_kind") or o.category, "span_mm": round(span, 1), "bearing_mm": bearing,
        "opening_size_mm": [round(float(size[0]), 1), round(float(size[1]), 1)],
        "split": {"part": part, "marks": total, "in_rcc_left_out": rcc, "in_thin_wall": thin, "other": plain}}
      if sec:
        width, depth = LT.section_in(sec, float(h["thin_mm"]) if thin_part and h.get("thin_mm") else None)
        params["length_mm"], params["width_mm"], params["depth_mm"] = round(span + 2.0 * bearing, 1), width, depth
        facts["section_mm"] = [width, depth]
        facts["table_section_mm"] = [sec["width_mm"], sec["depth_mm"]]
        facts["table_span_max_mm"] = sec["span_max_mm"]
        facts["table_pages"] = list(sec.get("pages") or [])
        notes.append(C.note("LINTEL_SECTION_FROM_TABLE"))
        if thin_part:
          notes.append(C.note("LINTEL_WIDTH_FROM_WALL", wall_mm=width, table_mm=sec["width_mm"], count=n))
        if sec.get("steel"):
          params["steel"] = dict(sec["steel"])
          facts["steel_text"] = LT.steel_text(sec["steel"])
          notes.append(C.note("LINTEL_STEEL_FROM_TABLE"))
        label = f"Lintel {o.tag} ×{n} · {_inch_text(width)}×{_inch_text(depth)} · {_fmt_mm(params['length_mm'])} mm long" + (f" · in {_inch_text(width)} wall" if thin_part else "")
      else:
        missing.append("size")
        notes.append(C.note("LINTEL_SPAN_ABOVE_TABLE"))
        base *= 0.7
        label = f"Lintel {o.tag} ×{n} · span {_fmt_mm(span)} mm"
      if h:
        facts["hosted"] = {k: h[k] for k in ("thin", "rcc", "hosted", "thin_mm") if k in h}
        if h.get("thin") and not sec:
          notes.append(C.note("LINTEL_IN_THIN_WALL", count=h["thin"]))
          base *= 0.9
      if rcc:
        notes.append(C.note("LINTEL_RCC_LEFT_OUT", count=rcc, marks=total))
      work_item, mode, kind = C.SUGGESTIONS["LINTEL"]
      tag = f"L-{o.tag} ({_inch_text(params['width_mm'])} wall)" if thin_part and sec else f"L-{o.tag}"
      cand = Candidate(key=_key("LINTEL", "THIN", o.key) if thin_part else _key("LINTEL", o.key), category="LINTEL", kind=kind, quantity_mode=mode, label=label, tag=tag,
        geometry={"points": thin_pts if thin_part else plain_pts}, params=params, missing=missing, work_item=work_item, status="VALID", confidence=0.0,
        facts=facts, notes=notes, source="TAG_SCAN", count=n)
      cand.status = _status(cand.notes)
      cand.confidence = round(max(0.0, min(1.0, base * ctx["content_factor"])), 4)
      out.append(cand)
  return out

def _located_stairs(places: list, spec: dict, ctx: dict, level_hint: str | None = None, floor_heights: dict | None = None) -> list:
  waist = spec.get("waist_mm")
  printed = bool(waist)
  waist_used = float(waist or C.STAIR_WAIST_DEFAULT_MM)
  work_item, mode, kind = C.SUGGESTIONS["STAIR"]
  out = []
  
  for p in places:
    notes = [C.note("STAIR_FROM_DETAILS"), C.note("STAIR_LANDINGS_NOT_INCLUDED"), C.note("STAIR_LOCATED_BY_TREADS")]
    way = p.get("direction")
    if way == "DOWN":
      notes.append(C.note("STAIR_DOWN_FLIGHT"))
    elif way is None:
      notes.append(C.note("STAIR_DIRECTION_UNKNOWN"))
    if p.get("short"):
      notes.append(C.note("STAIR_SHORT_FLIGHT"))
    own = p.get("width_printed_mm")
    
    width = float(own) if own else float(spec["width_mm"])
    if own and abs(width - float(spec["width_mm"])) > C.STAIR_OWN_WIDTH_TOL * float(spec["width_mm"]):
      notes.append(C.note("STAIR_OWN_WIDTH", printed_mm=round(width, 1), detail_mm=round(float(spec["width_mm"]), 1), printed_text=p.get("width_printed_text")))
    box = STR.flight_box({**spec, "width_mm": width}, waist_used)
    facts = {"stair_text": spec.get("text"), "riser_mm": spec.get("riser_mm"), "tread_mm": spec.get("tread_mm"), "stair_width_mm": round(width, 1),
      "detail_width_mm": spec.get("width_mm"), "width_source": "PRINTED_BESIDE" if own else "STAIR_DETAIL", "steps": spec.get("steps"),
      "stair_pages": list(spec.get("pages") or []), "direction": way, "treads_drawn": p["treads_drawn"], "width_drawn_mm": p["width_drawn_mm"],
      "flight_area_m2": p.get("flight_area_m2"), "flight_box": p.get("box"), "floor_hint": level_hint, "tread_drawn_mm": p.get("tread_drawn_mm"),
      "short_flight": bool(p.get("short"))}
    if p.get("corners"):
      facts.update({"flight_corners": p["corners"], "plan_angle_deg": p["angle_deg"]})
    rise = STR.rise_check(spec, way, level_hint, floor_heights)
    if rise:
      facts["rise"] = rise
      if rise["differs"]:
        note = C.note("STAIR_RISE_DIFFERS_FROM_STOREY")
        note["message"] += f" The steps rise {rise['rise_mm']:g} mm ({spec['steps']} x {spec['riser_mm']:g} mm); the storey is {rise['storey_mm']:g} mm floor to floor ({rise['gap_pct']:+.1f}%)."
        notes.append(note)
    params: dict = {"dims_basis": "SPECIFIED"}
    missing: list = []
    
    base = 0.8 if way else 0.7
    if box:
      params.update(box)
      facts.update({"waist_mm": round(waist_used, 1), "waist_source": "PRINTED" if printed else "ASSUMED", "equivalent_depth_mm": box["depth_mm"]})
      if not printed:
        notes.append(C.note("STAIR_WAIST_ASSUMED"))
        base *= 0.9
      label = f"Stair {'up' if way == 'UP' else 'down' if way == 'DOWN' else ''}".strip() + f" · {spec['steps']} steps · {_fmt_mm(spec['riser_mm'])}/{_fmt_mm(spec['tread_mm'])} mm · {_fmt_mm(width)} mm wide"
    else:
      missing = ["size"]
      gap = C.note("STAIR_DETAILS_INCOMPLETE")
      gap["message"] += STR.read_gap_text(spec)
      notes.append(gap)
      base *= 0.6
      label = "Stair"
    cand = Candidate(key=_key("STAIR", round(p["x"], 1), round(p["y"], 1), 1), category="STAIR", kind=kind, quantity_mode=mode, label=label, tag="STAIR",
      geometry={"points": [[round(p["x"], 3), round(p["y"], 3)]]}, params=params, missing=missing, work_item=work_item, status="VALID", confidence=0.0,
      facts=facts, notes=notes, source="VECTOR_SNAP", count=1)
    cand.status = _status(cand.notes)
    cand.confidence = round(max(0.0, min(1.0, base * ctx["content_factor"])), 4)
    out.append(cand)
  return out

def _drawn_stairs(places: list, ctx: dict, level_hint: str | None = None) -> list:
  """A stair for each flight drawn with UP or DN beside it when no sheet prints the size of the stair. Only what is drawn is carried (width, tread, treads drawn);
  the size is left to be measured, so nothing is guessed."""
  work_item, mode, kind = C.SUGGESTIONS["STAIR"]
  out = []
  for p in places:
    way = p["direction"]
    notes = [C.note("STAIR_FOUND_NO_DETAILS"), C.note("STAIR_LANDINGS_NOT_INCLUDED"), C.note("STAIR_LOCATED_BY_TREADS")]
    if way == "DOWN":
      notes.append(C.note("STAIR_DOWN_FLIGHT"))
    if p.get("short"):
      notes.append(C.note("STAIR_SHORT_FLIGHT"))
    width = float(p["width_drawn_mm"])
    facts = {"details_printed": False, "stair_width_mm": round(width, 1), "width_source": "DRAWN", "direction": way, "treads_drawn": p["treads_drawn"],
      "tread_drawn_mm": p.get("tread_drawn_mm"), "width_drawn_mm": p["width_drawn_mm"], "flight_area_m2": p.get("flight_area_m2"), "flight_box": p.get("box"),
      "floor_hint": level_hint, "short_flight": bool(p.get("short"))}
    if p.get("corners"):
      facts.update({"flight_corners": p["corners"], "plan_angle_deg": p["angle_deg"]})
    label = f"Stair {'up' if way == 'UP' else 'down'} · {p['treads_drawn']} treads drawn · {_fmt_mm(width)} mm wide · size not printed"
    cand = Candidate(key=_key("STAIR", round(p["x"], 1), round(p["y"], 1), 1), category="STAIR", kind=kind, quantity_mode=mode, label=label, tag="STAIR",
      geometry={"points": [[round(p["x"], 3), round(p["y"], 3)]]}, params={"dims_basis": "DRAWN"}, missing=["size"], work_item=work_item, status="VALID", confidence=0.0,
      facts=facts, notes=notes, source="VECTOR_SNAP", count=1)
    cand.status = _status(cand.notes)
    cand.confidence = round(max(0.0, min(1.0, 0.5 * ctx["content_factor"])), 4)
    out.append(cand)
  return out

def _stair_candidates(lines: list, spec: dict | None, ctx: dict, index=None, mm_per_pt: float | None = None, level_hint: str | None = None, floor_heights: dict | None = None) -> tuple[list, list]:
  
  if spec and index is not None and mm_per_pt:
    places = FL.find_stairs(W.straight_lines(index), spec, mm_per_pt, FL.direction_labels(lines), FL.length_labels(lines, S.feet_inches_mm))
    if places:
      return _located_stairs(places, spec, ctx, level_hint, floor_heights), []
  if not (spec and spec.get("tread_mm") and spec.get("width_mm")) and index is not None and mm_per_pt:
    drawn = FL.find_drawn_flights(W.straight_lines(index), mm_per_pt, FL.direction_labels(lines), FL.length_labels(lines, S.feet_inches_mm))
    if drawn:
      return _drawn_stairs(drawn, ctx, level_hint), []
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
    gap = C.note("STAIR_DETAILS_INCOMPLETE")
    gap["message"] += STR.read_gap_text(spec)
    notes.append(gap)
    base *= 0.6
    label = f"Stair ×{len(labels)}" + (f" · read: {spec['text']}" if spec.get("text") else "")
  work_item, mode, kind = C.SUGGESTIONS["STAIR"]
  cand = Candidate(key=_key("STAIR", round(labels[0]["x"], 1), round(labels[0]["y"], 1), len(labels)), category="STAIR", kind=kind, quantity_mode=mode, label=label,
    tag="STAIR", geometry={"points": [[round(l["x"], 3), round(l["y"], 3)] for l in labels]}, params=params, missing=missing, work_item=work_item, status="VALID",
    confidence=0.0, facts=facts, notes=notes, source="TAG_SCAN", count=len(labels))
  cand.status = _status(cand.notes)
  cand.confidence = round(max(0.0, min(1.0, base * ctx["content_factor"])), 4)
  return [cand], []

def _inch_label(mm: float) -> str:
  return f"{mm / 25.4:g}"

def _wall_beams(walls: list, role: str, ctx: dict, level_hint: str | None, min_wall_mm: float = 0.0, tie_band: dict | None = None) -> list:
  """One beam candidate per wall thickness: the brick walls of this floor laid end to end, as wide as the wall. The depth is not drawn, so it is left to be
  typed when the beam is accepted."""
  groups: dict = {}
  for w in walls:
    f = w.facts or {}
    if w.category != "WALL" or f.get("construction") == "RCC" or f.get("enclosure") == "TANK" or w.status == "INVALID":
      continue
    t = float(f.get("thickness_used_mm") or 0.0)
    if t <= 0.0 or t < min_wall_mm:
      continue
  
    groups.setdefault((round(t, 1), BM.mark_of(w, BS.KIND_OF_ROLE.get(role, role)) or ""), []).append(w)
  out = []
  spec = level_spec(level_hint)
  work_item, mode, kind = ("CON-RCC", "COUNT_X_VOLUME", "COUNT")
  for (t, mark), ws in sorted(groups.items(), key=lambda kv: (-kv[0][0], kv[0][1])):
    length_m = sum(float((w.facts or {}).get("length_cc_m") or 0.0) for w in ws)
    if length_m <= 0.0:
      continue
  
    pts = [p for w in ws for p in ((w.geometry or {}).get("points") or [])]
    cx = sum(p[0] for p in pts) / len(pts) if pts else 0.0
    cy = sum(p[1] for p in pts) / len(pts) if pts else 0.0
    prefix = {"PLINTH": "PLINTH-BEAM", "BAND": "TIE-BAND"}.get(role, "ROOF-BEAM")
    tag = f"{prefix}-{_inch_label(t)}IN" + (f"-{mark}" if mark else "")
    notes = [C.note("BEAM_FROM_WALLS"), C.note("BEAM_OVER_OPENINGS")]
    if role == "PLINTH":
      notes.append(C.note("PLINTH_BEAM_UNDER_9IN"))
    if role == "BAND":
       notes.append(C.note("TIE_BAND_FROM_NOTE"))
    facts = {"derived_from": "WALLS", "beam_role": role, "wall_thickness_mm": t, "wall_count": len(ws), "length_m": round(length_m, 3),
      "wall_keys": [w.key for w in ws], "openings_m": round(sum(sum((w.facts or {}).get("gaps_mm") or []) for w in ws) / 1000.0, 3), "level_hint": level_hint}
    if role == "BAND" and tie_band:
      facts["tie_band_text"] = tie_band.get("text")
      
    if mark:
      facts["beam_mark"] = mark
    kindname = {"PLINTH": "Plinth beam", "BAND": "Tie band at lintel level"}.get(role, "Roof beam")
    label = f"{kindname} {mark} under {_inch_label(t)} in walls · {length_m:.2f} m" if mark else f"{kindname} under {_inch_label(t)} in walls · {length_m:.2f} m"
    label += f" · {spec[0]}" if spec else ""
    cand = Candidate(key=_key("BEAM", role, round(t), level_hint or "", *([mark] if mark else [])), category="BEAM", kind=kind, quantity_mode=mode, label=label, tag=tag,
      geometry={"points": [[round(cx, 4), round(cy, 4)]]}, params={"length_mm": round(length_m * 1000.0, 1), "width_mm": t, "dims_basis": "SPECIFIED"},
      missing=["depth_mm"], work_item=work_item, status="VALID", confidence=0.0, facts=facts, notes=notes, source="VECTOR_SNAP", count=1)
    out.append(_finish(cand, ctx, 0.7))
  return out

def _beam_candidates(walls: list, ctx: dict, level_hint: str | None, lowest: bool, tie_band: dict | None = None) -> list:
  out = _wall_beams(walls, "ROOF", ctx, level_hint)
  if lowest:
    out.extend(_wall_beams(walls, "PLINTH", ctx, level_hint, C.PLINTH_BEAM_MIN_WALL_MM))
  if tie_band:
    out.extend(_wall_beams(walls, "BAND", ctx, level_hint, 0.0, tie_band))
  return out

def _foundation_candidates(walls: list, rooms: list, schedule: dict | None, ctx: dict, level_hint: str | None, sections: list | None = None, mm_per_pt: float | None = None,
  spec_facts: dict | None = None, sink: dict | None = None, fill_levels: dict | None = None, words: list | None = None, is_mark=None) -> list:
  """The work under the lowest floor that is worked out from what is already read: a trench, a concrete bed and termite treatment under the walls, the
  termite treatment under the floor, and, on a basement, the dig over the whole outline of the basement."""
  spec = level_spec(level_hint)
  outer = FD.outer_flags(walls, mm_per_pt)
  marks = FD.mark_runs(walls, words, mm_per_pt, sections, is_mark) if words and is_mark else {}
  out = FD.strip_candidates(walls, ctx, level_hint, spec, Candidate, _finish, sections, outer, marks)
  out.extend(FD.brick_step_candidates(walls, ctx, level_hint, spec, Candidate, _finish, sections, outer, marks))
  membrane = FD.membrane_candidate(walls, ctx, level_hint, spec, Candidate, _finish, mm_per_pt)
  if membrane is not None:
    out.append(membrane)
  out.extend(FD.membrane_layer_candidates(walls, ctx, level_hint, spec, Candidate, _finish, mm_per_pt, SPF.waterproof_for(spec_facts, level_hint)))
  layer_items, layer_notes, layer_stats = FLL.candidates(rooms, spec_facts, ctx, level_hint, spec, Candidate, _finish)
  out.extend(layer_items)
  
  if sink is not None:
    sink["notes"] = layer_notes
    sink["stats"] = layer_stats
  fill = EF.fill_candidate(rooms, ctx, level_hint, spec, Candidate, _finish, fill_levels)
  if fill is not None:
    out.append(fill)
  floor = FD.under_floor_candidate(rooms, ctx, level_hint, spec, Candidate, _finish)
  if floor is not None:
    out.append(floor)
    
  if level_hint == "BASEMENT":
    area = next((a for a in ((schedule or {}).get("areas") or []) if a.get("kind") == "FLOOR" and a.get("key") == level_hint), None)
    dims = (area or {}).get("dims_mm")
    if dims and len(dims) == 2:
      outline, facts, _ = _slab_outline(dims, ((schedule or {}).get("projections") or {}).get(level_hint))
      pts = [p for w in walls for p in ((w.geometry or {}).get("points") or [])]
      centre = [round(sum(p[0] for p in pts) / len(pts), 4), round(sum(p[1] for p in pts) / len(pts), 4)] if pts else [0.0, 0.0]
      cand = FD.excavation_candidate(outline or dims, facts, ctx, level_hint, spec, Candidate, _finish, centre)
      if cand is not None:
        out.append(cand)
  return out

def _finish_candidates(walls: list, rooms: list, doors: list, mm_per_pt: float, ctx: dict, level_hint: str | None, windows: list | None = None, arched: set | None = None) -> list:
  """The finishes of every floor that are worked out from what is already read: the kacha bed and the ceiling plaster from the room areas, the plaster on
   the faces of the walls, and the frames of the doors."""
  spec = level_spec(level_hint)
  if level_hint == "ROOF":
    rooms = [r for r in rooms if (r.facts or {}).get("name")]
  out = []
  for build in (FN.kacha_candidate, FN.ceiling_candidate, FN.floor_candidate, FN.floor_wet_candidate, FN.ceiling_paint_candidate):
    cand = build(rooms, ctx, level_hint, spec, Candidate, _finish)
    if cand is not None:
      out.append(cand)

  skirting = FN.skirting_candidate(rooms, doors, mm_per_pt, ctx, level_hint, spec, Candidate, _finish)
  dado = FN.dado_candidate(rooms, doors, mm_per_pt, ctx, level_hint, spec, Candidate, _finish, windows)
  tile = FN.wall_tile_candidate(rooms, doors, mm_per_pt, ctx, level_hint, spec, Candidate, _finish, windows)
  proof = FN.wet_waterproof_candidate(rooms, doors, mm_per_pt, ctx, level_hint, spec, Candidate, _finish)
  out.extend(c for c in (skirting, dado, tile, proof) if c is not None)
  out.extend(FN.plaster_candidates(walls, mm_per_pt, ctx, level_hint, spec, Candidate, _finish))
  out.extend(FN.paint_candidates(walls, mm_per_pt, ctx, level_hint, spec, Candidate, _finish, float(((dado.facts if dado is not None else {}) or {}).get("area_m2") or 0.0)))
  out.extend(FN.door_frame_candidates(doors, walls, ctx, level_hint, spec, Candidate, _finish))
  out.extend(FN.arch_candidates(doors, windows or [], walls, arched or set(), ctx, level_hint, spec, Candidate, _finish))
  out.extend(OA.opening_area_candidates(doors, windows or [], ctx, level_hint, spec, Candidate, _finish))
  return out

def _settle_scale(res: Extraction) -> None:
  for c in res.candidates:
    if any(n.get("code") == "SCALE_UNVERIFIED" for n in c.notes):
      c.notes = [n for n in c.notes if n.get("code") != "SCALE_UNVERIFIED"]
      c.status = _status(c.notes)

def _opening_symbols(index, walls: list, mm_per_pt: float, ctx: dict, imperial: bool, deadline: float, res: Extraction, wall_pen: float | None = None, opening_heights: dict | None = None) -> None:
  verified = not ctx.get("scale_unverified")
  try:
    symbols = OS.read(index, walls, mm_per_pt, scale_verified=verified, deadline=deadline, wall_pen=wall_pen, imperial=imperial)
    sym = OS.reconcile(res.candidates, symbols, mm_per_pt, scale_verified=verified, imperial=imperial, ctx=ctx, cls=Candidate, finish=_finish, set_heights=opening_heights)
  except Exception as exc:
    res.notes.append(C.note("OPENING_SYMBOLS_FAILED", error=type(exc).__name__))
    res.stats["opening_symbols"] = {"error": f"{type(exc).__name__}: {exc}"}
    return
  
  res.candidates.extend(sym["new"])
  res.notes.extend(sym["notes"])
  if sym.get("settled"):
    res.stats["scale_settled_by_schedule"] = True
  if symbols["stats"]["doors"] or symbols["stats"]["windows"]:
    res.notes.append(C.note("OPENING_SYMBOLS_READ", doors=symbols["stats"]["doors"], windows=symbols["stats"]["windows"]))
  if symbols["stats"]["timed_out"]:
    res.notes.append(C.note("OPENING_SYMBOLS_TIME_LIMIT"))
  res.stats["opening_symbols"] = {**symbols["stats"], **sym["stats"]}

def _view_plans(views: list, scales: dict | None = None) -> list:
  out = []
  for v in views:
    if not v.get("structural") or v.get("foundation") or not v.get("level_hint"):
      continue
    b = v["bbox"]
    out.append({"key": v["key"], "caption": v.get("caption"), "level_hint": v["level_hint"], "centre": ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0),
      "note_mm": v.get("slab_note_mm"), "panels": int(v.get("slab_panels") or 0), "marks": list(v.get("slab_marks") or []),
      "bbox": list(b), "mm_per_pt": ((scales or {}).get(v["key"]) or {}).get("mm_per_pt"),
      "view": {"key": v["key"], "caption": v["caption"], "kind": v["kind"], "level_hint": v.get("level_hint")}})
  return out

def _sheet_plan(words: list, lines: list, level_hint: str | None, title: str | None, mm_per_pt: float | None = None) -> dict | None:
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
    "panels": len(marks), "marks": marks, "view": None, "bbox": [min(xs) - 30.0, min(ys) - 30.0, max(xs) + 30.0, max(ys) + 30.0], "mm_per_pt": mm_per_pt}

def _mark_stats(res: Extraction, words: list, marks: dict) -> None:
  vocab, disc = marks["vocab"], marks["discipline"]
  seen = {MV.norm(w.text) for w in words if is_tag(w.text)}
  for mark, kept, other in MV.conflicts(vocab, disc):
    if mark in seen:
      res.notes.append(C.note("MARK_MEANING_CONFLICT", mark=mark, kept={k: kept.get(k) for k in ("category", "basis", "text", "page_no")}, other={k: other.get(k) for k in ("category", "basis", "text", "page_no")}))
  rows = []
  for row in sorted(marks["skipped"].values(), key=lambda r: (r["category"], r["tag"])):
    e = MV.entry_of(vocab, row["tag"], disc)
    rows.append({**row, "basis": e["basis"] if e else "DEFAULT", "text": e.get("text") if e else None, "params": dict(e.get("params") or {}) if e else {}})
  res.stats["marks"] = {"discipline": disc, "plan_kind": marks["plan_kind"], "in_vocabulary": len((vocab or {}).get(disc) or {}), "not_counted": rows}

def _read_sheet(index, mm_per_pt: float, *, cal_factor: float = 1.0, scale_unverified: bool = False, content_kind: str = "VECTOR",
  budget_s: float = 25.0, schedule: dict | None = None, views_meta: list | None = None, col_details: dict | None = None,
  floor_heights: dict | None = None, level_hint: str | None = None, slab_values: list | None = None, text_source: str = "TEXT",
  lowest_level: bool = False, with_finishes: bool = False, beam_sections: list | None = None, tank_details: list | None = None,
  sheet_words: list | None = None, outer_only: bool = False, imperial: bool | None = None, wall_vocab: list | None = None,
  footing_sections: list | None = None, spec_facts: dict | None = None, read_as: str | None = None, role_info: dict | None = None,
  mark_vocab: dict | None = None, discipline: str | None = None, opening_heights: dict | None = None) -> Extraction:
  started = time.monotonic()
  deadline = started + budget_s
  ctx = {"cal_factor": cal_factor, "scale_unverified": scale_unverified,
    "content_factor": {"VECTOR": 1.0, "UNKNOWN": 0.95, "RASTER": 0.85}.get(content_kind, 0.95) * (SCAN_TEXT_FACTOR if text_source in ("OCR", "OUTLINED") else 1.0)}
  
  res = Extraction()
  role_info = role_info or {}
  if read_as:
    res.stats["read_as"] = read_as
  if read_as == "SKIP":
    res.notes.append(C.note("SHEET_NOT_READ_ROLE", role=role_info.get("role"), title=role_info.get("title")))
    return res
  partial = read_as in ("DETAILS_ONLY", "SYMBOLS_ONLY")
  if text_source == "OCR":
    res.notes.append(C.note("SCAN_TEXT_READ"))
  elif text_source == "OUTLINED":
    res.notes.append(C.note("OUTLINED_TEXT_READ"))
  words = index.words
  imp_here = imperial if imperial is not None else _is_imperial(words)
  imp_sheet = imperial if imperial is not None else _is_imperial(sheet_words if sheet_words is not None else words)
  lines = build_lines(words)
  notes_lines = build_lines(sheet_words) if sheet_words is not None else lines
  hint = find_units_hint(notes_lines)
  heights = M.height_hints(notes_lines, hint)
  sheet_heights = QR.less_beams(_with_floor_height(heights, floor_heights, level_hint), bool(lowest_level), _ft_in)
  shapes = M.member_shapes(index.rings, mm_per_pt)
  openings = S.opening_lookup(schedule)
  plan_kind = role_info.get("plan_kind")
  marks = {"vocab": mark_vocab, "discipline": discipline, "plan_kind": plan_kind, "skipped": {}}
  views = VW.find_views(index)
  
  composite_structural = sum(1 for v in views if v["structural"]) >= 2
  if composite_structural:
    found, vstats = _structure_candidates(index, views, mm_per_pt, hint, heights, ctx, imp_here, {v["key"]: v.get("scale") for v in (views_meta or []) if v.get("scale")}, col_details, floor_heights, beam_sections, marks)
    res.candidates.extend(found)
    res.stats["views"] = vstats
    res.stats["column_details"] = {t: {"sizes_in": r.get("sizes_in") or []} for t, r in (col_details or {}).items()}
    plans = _view_plans(views, {v["key"]: v.get("scale") for v in (views_meta or []) if v.get("scale")})
  else:
    found = [] if partial else _tag_candidates(index, words, shapes, mm_per_pt, hint, sheet_heights, ctx, openings, col_details=col_details, marks=marks)
    only = [] if partial else [v for v in views if v["structural"] and not v.get("foundation")]
    if len(only) == 1:
      in_view = [w for w in words if VW.contains(only[0], w.cx, w.cy)]
      strips = _apply_strips(index, only[0], in_view, found, mm_per_pt, ctx, imp_here, beam_sections, only[0].get("level_hint") or level_hint)
      if strips is not None:
        res.stats["beam_strips"] = strips
      if not any(c.category == "COLUMN" for c in found):
        mine = [r for r in RND.circles(index, mm_per_pt, words) if VW.contains(only[0], r["cx"], r["cy"])]
        found.extend(_unmarked_round_columns(only[0], mine, mm_per_pt, ctx, imp_here, sheet_heights))
    res.candidates.extend(found)
    plans = []
    
  res.stats["schedule_marks"] = len(openings)
  _mark_stats(res, words, marks)
  kind = sheet_kind(sheet_words if sheet_words is not None else words)
  slab_plan = SPL.read(words, lines, hint) if not composite_structural and not partial else None
  if slab_plan and kind["kind"] == "UNKNOWN":
    kind = {"kind": "STRUCTURAL", "title": "slab plan (read from its bar strings and panel sizes)"}
  if not composite_structural and not partial and kind["kind"] == "STRUCTURAL":
    one = _sheet_plan(words, lines, level_hint, kind.get("title"), None if scale_unverified else mm_per_pt)
    plans = [one] if one else []
  areas = {a["key"]: a for a in ((schedule or {}).get("areas") or []) if a.get("kind") == "FLOOR"}
  seen_floor: set = set()
  for plan in plans:
    cand, notes = _slab_candidate(plan, areas, slab_values or [], ctx, _implied_slab_mm(floor_heights, plan.get("level_hint")), (schedule or {}).get("projections"))
    if cand is not None and plan["level_hint"] not in seen_floor:
      seen_floor.add(plan["level_hint"])
      SPN.attach(cand, plan, index, C.note)
      cand.status = _status(cand.notes)

      res.candidates.append(cand)
    res.notes.extend(notes)
  if slab_plan and kind["kind"] == "STRUCTURAL" and not any(c.category == "SLAB" for c in res.candidates):
    note_mm = next((round(float(m.group(1)) * 25.4, 1) for m in (VW._SLAB_NOTE.search(ln.text) for ln in lines) if m), None)
    panels = _slab_panel_candidates(slab_plan, note_mm, level_hint, slab_values or [], ctx, _implied_slab_mm(floor_heights, level_hint))
    if panels:
      res.candidates.extend(panels)

      res.notes = [n for n in res.notes if n.get("code") != "SLAB_AREA_NOT_FOUND"]
      res.stats["slab_plan"] = {"panels": len(slab_plan["panels"]), "labels": slab_plan["labels"], "labels_outside": slab_plan["labels_outside"], "strings": slab_plan["strings"], "area_m2": slab_plan["area_m2"]}
  res.stats["slabs"] = sum(1 for c in res.candidates if c.category == "SLAB")
  res.candidates.extend(RF.roof_candidates([c for c in res.candidates if c.category == "SLAB"], ctx, Candidate, _finish, spec_facts))
  roof_layers, roof_notes, res.stats["roof_layers"] = FLL.roof_candidates([c for c in res.candidates if (c.facts or {}).get("foundation_item") == FD.ROOF_TREATMENT], spec_facts, ctx, Candidate, _finish)
  res.candidates.extend(roof_layers)
  res.notes.extend(roof_notes)
  props = STG.props_candidates([c for c in res.candidates if c.category == "SLAB"], floor_heights, ctx, Candidate, _finish)
  res.candidates.extend(props)
  res.stats["props_items"] = len(props)
  pads = FD.pad_candidates([c for c in res.candidates if c.category == "FOOTING"], ctx, Candidate, _finish, footing_sections)
  res.candidates.extend(pads)
  res.stats["concrete_beds"] = len(pads)
  
  res.stats["sheet_kind"] = kind
  role = PRL.page_role(sheet_words if sheet_words is not None else words, kind, drawn=len(index.kinds))
  role["advice"] = PRL.reading_advice(role)
  role.setdefault("purpose", PRL.purpose(PRL._title_lines(sheet_words if sheet_words is not None else words)))
  res.stats["sheet_role"] = role
  if kind["kind"] != "STRUCTURAL" and not composite_structural and level_hint and sheet_words is None:
    res.stats["column_shapes"] = CS.census(index.rings, mm_per_pt, imp_here, _snap_inch, level_hint)
  frames, runs = [], []
  if partial:
    res.notes.append(C.note("SHEET_READ_" + str(read_as), role=role_info.get("role"), title=role_info.get("title")))
  elif kind["kind"] == "STRUCTURAL" or composite_structural:
    res.notes.append(C.note("STRUCTURAL_SHEET", title=kind["title"] or (views[0]["caption"] if views else None)))
  else:
    try:
      frames, runs, walls, wstats = _wall_candidates(index, mm_per_pt, sheet_heights, ctx, deadline, imp_sheet, bool(lowest_level) or str(level_hint or "").upper() in ("GROUND", "BASEMENT"), outer_only, wall_vocab)
      res.candidates.extend(walls)
      wstats["tank_walls"] = _mark_tanks(words, walls, mm_per_pt)
      _drop_tank_heights(walls)
      wstats["tank_drawings_listed"] = TS.apply(walls, tank_details or [])
      res.stats["beam_marks"] = BM.assign(walls, BM.mark_words(words, beam_sections or []), mm_per_pt)
      beams = _beam_candidates(walls, ctx, level_hint, lowest_level, (schedule or {}).get("tie_band"))
      res.stats["beam_sections"] = BS.apply(beams, beam_sections or [])
      res.candidates.extend(beams)
      res.stats["wall_beams"] = len(beams)
      _stage(res, "OPENING_SYMBOLS", lambda: _opening_symbols(index, walls, mm_per_pt, ctx, imp_sheet, deadline, res, wstats.get("wall_pen_pt"), opening_heights), None)
      hosted = H.assign(walls, [c for c in res.candidates if c.category in ("DOOR", "WINDOW")], mm_per_pt)
      wstats["openings_assigned"], wstats["openings_unassigned"] = hosted["assigned"], hosted["unassigned"]
      wstats["opening_rules"] = OPR.apply(walls)
      marked = [c for c in res.candidates if c.category in ("DOOR", "WINDOW")]
      wstats["opening_marks"] = OK.check(marked, walls, (schedule or {}).get("openings") or [], mm_per_pt)
      for c in marked:
        if c.facts.get("gap_check"):
          c.status = _status(c.notes)
      
      for c in walls:
        if c.params.get("openings"):
          c.notes.append(C.note("OPENINGS_ASSIGNED", count=c.facts["openings"]["count"], marks=c.facts["openings"]["marks"]))
          c.status = _status(c.notes)
      ring = wstats.pop("rcc_ring", None)
      completion = CP.candidates(ring, CP.rcc_notes(notes_lines), sheet_heights, ctx, imp_sheet, Candidate, _finish, _height_note)
      QR.mark_clear([*walls, *completion], floor_heights, level_hint)
      wstats["qs_rcc_heights"] = QR.rcc_heights([*walls, *completion], level_hint)
      wstats["rcc_completion"] = {"pieces": len(completion), "sides_drawn": ring["sides"]} if ring else None
      res.stats["walls"] = wstats
      lintel_marks: list = []
      
      lintels = _lintel_candidates([c for c in res.candidates if c.category in ("DOOR", "WINDOW")], (schedule or {}).get("lintels") or [],
        _hosted_by_tag(hosted.get("by_wall"), walls, hosted.get("by_point")), ctx, lintel_marks)
      res.stats["lintel_marks"] = lintel_marks
      res.candidates.extend(lintels)
      wstats["brick_net_of_lintels"] = WN.attach(walls, lintels)
      dashed = DO.find(index, mm_per_pt, wstats.get("wall_pen_pt"))
      marks = [tuple(q) for c in res.candidates if c.category in ("DOOR", "WINDOW") for q in ((c.geometry or {}).get("points") or [])]
      wide = WO.candidates(walls, (schedule or {}).get("lintels") or [], ctx, Candidate, _finish, _inch_text, _fmt_mm, dashed, marks, mm_per_pt)
      wstats["dashed_openings"] = len(dashed)
      res.candidates.extend(wide)
      bands = [c for c in beams if (c.facts or {}).get("beam_role") == "BAND"]
      res.stats["lintel_heads"] = LH.apply([*lintels, *wide, *bands], [c for c in res.candidates if c.category in ("DOOR", "WINDOW")])
      kept_beams, band_rec = BC.resolve(beams, (schedule or {}).get("roof_band"), [*lintels, *wide], level_hint, "roof_band" in (schedule or {}))
      if band_rec:
        listed = {id(c) for c in kept_beams}
        gone = {id(c) for c in beams} - listed
        res.candidates[:] = [c for c in res.candidates if id(c) not in gone]
        res.stats["tie_band_count"] = band_rec
        res.stats["wall_beams"] = len(kept_beams)
        bands = [c for c in kept_beams if (c.facts or {}).get("beam_role") == "BAND"]
      if bands and not BC.lintels_counted():
        for c in [*lintels, *wide]:
          if c.facts.get("split") or not (c.facts.get("hosted") or {}).get("rcc"):
            c.facts["tie_band"] = {"text": (bands[0].facts or {}).get("tie_band_text"), "candidate_key": bands[0].key}
            c.notes.append(C.note("LINTEL_COVERED_BY_TIE_BAND"))
            
      for c in [*lintels, *wide, *bands, *(kept_beams if band_rec else [])]:
        c.status = _status(c.notes)
      res.stats["lintels"] = len(lintels) + len(wide)
      res.stats["lintels_unmarked_openings"] = len(wide)
      stairs, stair_notes = _stair_candidates(lines, (schedule or {}).get("stair"), ctx, index, mm_per_pt, level_hint, floor_heights)
      res.candidates.extend(stairs)
      res.notes.extend(stair_notes)
      res.stats["stairs"] = len(stairs)
      res.stats["stairs_external"] = SX.mark(stairs, lines, walls, mm_per_pt)
      res.stats["stairs_size_not_printed"] = sum(1 for c in stairs if (c.facts or {}).get("details_printed") is False)
      labels = SO.read_labels(lines, hint, mm_per_pt)
      attached, unplaced = SO.attach_landings(stairs, labels["landings"], mm_per_pt, FL._gap)
      for c in stairs:
        c.status = _status(c.notes)
      for lan in unplaced:
        res.notes.append(C.note("STAIR_LANDING_NOT_PLACED", size=lan["text"], area_m2=lan["area_m2"]))
      if labels["unsized"]:
        res.notes.append(C.note("SLAB_OPENING_SIZE_NOT_PRINTED", count=labels["unsized"]))
      res.stats["slab_openings"] = SO.sheet_entries(stairs, labels["voids"], level_hint, mm_per_pt)
      res.stats["stair_landings"] = {"printed": len(labels["landings"]), "attached": attached}
      if wstats.get("dropped_treads"):
        res.notes.append(C.note("STAIR_TREADS_NOT_WALLS", count=wstats["dropped_treads"], metres=wstats["treads_m"]))
      if wstats.get("dropped_outside_plan"):
        res.notes.append(C.note("RUNS_OUTSIDE_PLAN_WALLS", count=wstats["dropped_outside_plan"], metres=wstats["outside_plan_m"]))
      if wstats.get("dropped_outside_rcc"):
        res.notes.append(C.note("RUNS_OUTSIDE_CONCRETE_WALLS", count=wstats["dropped_outside_rcc"]))
        
      if wstats.get("wall_pen_pt"):
        res.notes.append(C.note("WALL_PEN_SELECTED", pen_pt=wstats["wall_pen_pt"], runs_all_pens=wstats.get("runs_all_pens"),
          wall_m_all_pens=wstats.get("wall_m_all_pens")))
      if wstats.get("light_walls_kept"):
        res.notes.append(C.note("LIGHT_PEN_WALLS_KEPT", count=wstats["light_walls_kept"], metres=wstats.get("light_walls_m")))
      rooms = _stage(res, "ROOMS", lambda: _room_candidates(index, frames, runs, lines, mm_per_pt, hint, ctx, res, walls), [])
      res.candidates.extend(rooms)
      res.candidates.extend(completion)
      
      if with_finishes:
        finishes = _stage(res, "FINISHES", lambda: _finish_candidates([*walls, *QR.counted_completion(completion)], rooms, [c for c in res.candidates if c.category == "DOOR"],
          mm_per_pt, ctx, level_hint, [c for c in res.candidates if c.category == "WINDOW"], S.arched_marks(schedule)), [])
        res.candidates.extend(finishes)
        res.stats["finish_items"] = len(finishes)
        if level_hint == "ROOF" and any(r.category == "ROOM" and not (r.facts or {}).get("name") for r in rooms):
          res.notes.append(C.note("ROOF_PLAN_ROOMS_UNNAMED", rooms=sum(1 for r in rooms if r.category == "ROOM" and not (r.facts or {}).get("name"))))
        scaffold, scaffold_notes = STG.scaffold_candidates(finishes, floor_heights, level_hint, ctx, Candidate, _finish)
        res.candidates.extend(scaffold)
        res.notes.extend(scaffold_notes[:1])
        res.stats["scaffold_items"] = len(scaffold)
      if lowest_level:
        sink: dict = {}
        
        below = _stage(res, "FOUNDATION", lambda: _foundation_candidates([*walls, *QR.counted_completion(completion)], rooms, schedule, ctx, level_hint,
          footing_sections, mm_per_pt, spec_facts, sink, EF.fill_depth(floor_heights, level_hint, EF.natural_ground_mm(index.words), spec_facts), index.words,
          lambda tag: M.category_of(tag, mark_vocab, discipline, plan_kind) == "WALL_SECTION"), [])
        res.candidates.extend(below)
        res.stats["foundation_items"] = len(below)
        res.notes.extend(sink.get("notes") or [])
        if sink.get("stats"):
          res.stats["floor_layers"] = sink["stats"]
          
    except W.TimeLimit:
      res.notes.append(C.note("TIME_LIMIT"))
  if role["role"] == "UNKNOWN" and sum(1 for c in res.candidates if c.category == "ROOM" and c.facts.get("name")) >= 3:
    role.update(role="PLAN", basis="CONTENT", advice="READ")   
  if role["advice"] == "SKIP":
    walls_read = sum(1 for c in res.candidates if c.category in ("WALL", "ROOM"))
    if walls_read:
      res.notes.append(C.note("SHEET_NOT_A_PLAN", role=role["role"], title=role.get("title"), items=walls_read))
  if scale_unverified and kind["kind"] != "STRUCTURAL" and not composite_structural and not res.stats.get("scale_settled_by_schedule"):
    widths = [float(w) for c in res.candidates if c.category == "DOOR" for w in (c.facts.get("widths_measured_mm") or [])]
    named = [(c.facts.get("name"), c.facts.get("area_m2")) for c in res.candidates if c.category == "ROOM" and c.facts.get("name")
      and c.facts.get("outline_from") != "LABEL" and not any(n.get("code") == "ROOM_INSIDE_ROOM" for n in c.notes)]
    plaus = SP.check(mm_per_pt, widths, named)
    
    res.stats["scale_plausibility"] = plaus
    if plaus and plaus["status"] == "IMPLAUSIBLE":
      res.notes.append(C.note("SCALE_LOOKS_WRONG", used_mm_per_pt=plaus["used_mm_per_pt"], suggested_mm_per_pt=plaus["suggested_mm_per_pt"],
        suggested_scale=plaus["suggested_scale"], evidence=plaus["evidence"], agree=plaus["agree"]))
  found_steel = SN.read(notes_lines)
  res.stats["steel"] = SN.attach(res.candidates, found_steel, C.note)
  res.stats["column_steel"] = ST.apply_column_steel(res.candidates, col_details, C.note)
  res.stats["steel_notes"] = found_steel["notes"]
  res.stats["spec_grades"] = SPF.annotate(res.candidates, spec_facts, C.note)
  
  if composite_structural:
    neck = NK.candidates(res.candidates, ctx, Candidate, _finish)
    res.candidates.extend(neck)
    res.stats["neck_columns"] = len(neck)
  if res.stats.get("scale_settled_by_schedule"):
    _settle_scale(res)
  for c in res.candidates:
    c.status = _status(c.notes)
  res.stats["qs"] = QR.apply(res.candidates, level_hint)
  for c in res.candidates:
    c.status = _status(c.notes)
  mapped = {c.tag for c in res.candidates if c.tag}
  unmapped: dict = {}
  for g in census.tag_census(words):
      
    if g["tag"] not in mapped and M.category_of(g["tag"], mark_vocab, discipline, plan_kind) is None and g["in_drawing"] >= 2:
      unmapped[g["tag"]] = g["in_drawing"]
  res.unmapped_tags = [{"tag": t, "count": n} for t, n in sorted(unmapped.items(), key=lambda kv: (-kv[1], kv[0]))][:30]
  res.stats["seconds"] = round(time.monotonic() - started, 3)
  res.stats["units_hint"] = hint
  res.stats["units"] = {"imperial": imp_sheet, "basis": "DRAWING" if imperial is not None else "SHEET", "wall_vocab_mm": list(wall_vocab or [])}
  res.stats["height_notes"] = heights
  return res

def _region_scale_note(region: dict, views_meta: list | None, f: float) -> dict | None:
  """The dimensions printed inside the drawing that holds this plan show another scale than the sheet."""
  cx, cy = (region["core_bbox"][0] + region["core_bbox"][2]) / 2.0, (region["core_bbox"][1] + region["core_bbox"][3]) / 2.0
  best = None
  
  for v in views_meta or []:
    b, own = v.get("bbox"), v.get("scale") or {}
    if not b or not own.get("mm_per_pt") or not (b[0] <= cx <= b[2] and b[1] <= cy <= b[3]):
      continue
    area = (b[2] - b[0]) * (b[3] - b[1])
    if best is None or area < best[0]:
      best = (area, own["mm_per_pt"])
  if best is None or abs(best[1] / f - 1.0) <= VIEW_SCALE_TOL:
    return None
  return C.note("VIEW_SCALE_DIFFERS", view_mm_per_pt=best[1], sheet_mm_per_pt=round(f, 5))

def _read_regions(index, mm_per_pt: float, regions: list, found: dict, *, started: float, budget_s: float, **kw) -> Extraction:
  """Each floor plan of a sheet that holds several drawings, read on its own: its walls, its openings, its rooms, its floor."""
  res = Extraction()
  kw.pop("level_hint", None)
  kw.pop("lowest_level", None)
  views_meta = kw.get("views_meta")
  kw["views_meta"] = None
  seen: set = set()
  merged: dict = {}
  unmapped: dict = {}
  openings: list = []
  per: list = []
  left = len(regions)
  for r in regions:
    sub = PR.sub_index(index, r)
    part = _read_sheet(sub, mm_per_pt, budget_s=max(2.0, (budget_s - (time.monotonic() - started)) / left), level_hint=r["level_hint"],
      lowest_level=False, sheet_words=index.words, outer_only=True, **kw)
    
    left -= 1
    spec = level_spec(r["level_hint"])
    scale_note = _region_scale_note(r, views_meta, mm_per_pt)
    for c in part.candidates:
      c.facts = {**(c.facts or {}), "view": PR.view_fact(r)}
      if spec and spec[0] not in c.label:
        c.label = f"{c.label} · {spec[0]}"
      if scale_note is not None:
        c.notes.append(scale_note)
        c.status = _status(c.notes)
      if c.key in seen:
        c.key = _key(c.key, r["key"])
      seen.add(c.key)
    res.candidates.extend(part.candidates)
    
    for n in part.notes:
      if n.get("code") in ("RUNS_OUTSIDE_PLAN_WALLS", "STAIR_TREADS_NOT_WALLS"):
        n["plan"] = r["caption"]
      if n not in res.notes:
        res.notes.append(n)
    for t in part.unmapped_tags:
      unmapped[t["tag"]] = unmapped.get(t["tag"], 0) + int(t["count"])
    openings.extend(part.stats.get("slab_openings") or [])
    for k, v in (part.stats.get("walls") or {}).items():
      if isinstance(v, (int, float)) and not isinstance(v, bool):
        merged[k] = round(merged.get(k, 0) + v, 3)
    by: dict = {}
    
    for c in part.candidates:
      by[c.category] = by.get(c.category, 0) + 1
    per.append({"key": r["key"], "caption": r["caption"], "level_hint": r["level_hint"], "bbox": r["bbox"], "wall_m_found": r["wall_m"],
      "items": by, "walls": (part.stats.get("walls") or {}).get("runs"), "seconds": part.stats.get("seconds")})
  res.unmapped_tags = [{"tag": t, "count": n} for t, n in sorted(unmapped.items(), key=lambda kv: (-kv[1], kv[0]))][:30]
  res.stats["walls"] = merged
  res.stats["slab_openings"] = openings
  res.stats["plan_regions"] = {**found, "count": len(regions), "plans": per}
  res.notes.insert(0, C.note("PLAN_REGIONS_READ", plans=[{"caption": r["caption"], "level_hint": r["level_hint"]} for r in regions]))
  return res

def _site_candidates(found: list, ctx: dict) -> list:
  """One candidate per site item the sheet prints (tanks, septic tank, boundary wall, gate, porch ramp). Their sizes are not drawn on a plan, so a size is
  either printed (and in params) or missing (and typed when the item is accepted)."""
  _, mode, kind = C.SUGGESTIONS["SITE"]
  out = []
  for it in found:
    notes = []
    for code, extra in it["codes"]:
      n = C.note(code, **extra)
      if extra.get("derived"):
        n["message"] += " " + extra["derived"] + "." + (f" Still to type: {extra['left']}." if extra.get("left") else "")
      if extra.get("printed"):
        n["message"] += " Printed: " + extra["printed"] + "."
    notes.append(n)
    params = {"dims_basis": "SPECIFIED", **it["params"]}
    mode_of = "COUNT_X_AREA" if it["site_kind"] == "GATE" else mode
    cand = Candidate(key=_key("SITE", it["site_kind"], round(it["x"], 1), round(it["y"], 1)), category="SITE", kind=kind, quantity_mode=mode_of, label=it["label"], tag=it["tag"],
      geometry={"points": [[round(it["x"], 3), round(it["y"], 3)]]}, params=params, missing=list(it["missing"]), work_item=SI.WORK_ITEM.get(it["site_kind"]), status="VALID",
      confidence=0.0, facts=it["facts"], notes=notes, source="TAG_SCAN", count=1)
    cand.status = _status(cand.notes)
    cand.confidence = round(max(0.0, min(1.0, it["base"] * ctx["content_factor"])), 4)
    out.append(cand)
  return out

def _tank_twin_walls(res: Extraction, sites: list) -> int:
  """The walls the plan draws round a labelled tank are the concrete of the tank item too. Each says so, and so does the tank."""
  n = 0
  walls = [c for c in res.candidates if c.category == "WALL" and (c.facts or {}).get("enclosure") == "TANK"]
  for s in sites:
    kind = (s.facts or {}).get("tank_kind")
    
    if not kind:
      continue
    mine = [w for w in walls if (w.facts or {}).get("tank_kind") in (kind, "TANK")]
    if not mine:
      continue
    s.notes.append(C.note("SITE_TANK_WALLS_ALSO_LISTED", walls=len(mine)))
    s.status = _status(s.notes)
    for w in mine:
      w.notes.append(C.note("SITE_TANK_WALLS_ALSO_LISTED", tank=s.tag))
      w.status = _status(w.notes)
      n += 1
  return n

def _finish_site(c: Candidate, ctx: dict, base: float) -> Candidate:
  c.status = _status(c.notes)
  c.confidence = round(max(0.0, min(1.0, base * ctx["content_factor"])), 4)
  return c

def _site_ctx(kw: dict) -> dict:
  return {"content_factor": {"VECTOR": 1.0, "UNKNOWN": 0.95, "RASTER": 0.85}.get(kw.get("content_kind", "VECTOR"), 0.95) * (SCAN_TEXT_FACTOR if kw.get("text_source", "TEXT") in ("OCR", "OUTLINED") else 1.0)}

def _with_site(res: Extraction, index, mm_per_pt: float, kw: dict) -> Extraction:
  ctx = _site_ctx(kw)
  sites = _site_candidates(SI.find(index.words, mm_per_pt, kw.get("tank_details")), ctx)
  res.candidates.extend(sites)
  boundary = BDY.candidates(sites, ctx, Candidate, _finish_site)
  res.candidates.extend(boundary)
  res.stats["boundary_items"] = len(boundary)
  drainage = DR.candidates(index.words, kw.get("floor_heights"), ctx, Candidate, _finish_site)
  res.candidates.extend(drainage)
  res.stats["drainage_items"] = len(drainage)
  piles_rafts, pr_notes = PRF.candidates(index.words, kw.get("schedule"), ctx, Candidate, _finish_site)
  res.candidates.extend(piles_rafts)
  res.notes.extend(pr_notes)
  res.stats["pile_raft_items"] = len(piles_rafts)
  res.stats["qs_site"] = QR.apply(sites, None)
  res.stats["site_items"] = {c.facts["site_kind"]: 1 for c in sites}
  res.stats["site_tank_walls"] = _tank_twin_walls(res, sites)
  _list_views(res, index)
  return res

COMPOSITE_CAPTIONS = 4

def _list_views(res: Extraction, index) -> None:
  kinds: dict = {}
  for cap in VW.captions(index.words):
    kinds.setdefault(cap["kind"], []).append(cap["text"])
  if sum(len(v) for v in kinds.values()) < COMPOSITE_CAPTIONS:
    return
  res.stats["sheet_captions"] = {k: v for k, v in sorted(kinds.items())}
  res.notes.append(C.note("SHEET_VIEWS_LISTED", views={k: len(v) for k, v in sorted(kinds.items())}, titles=[t for k, v in sorted(kinds.items()) for t in v][:30]))

def _run_extraction_upright(index, mm_per_pt: float, *, composite: bool = False, regions_only: bool = False, site_only: bool = False, **kw) -> Extraction:
  started = time.monotonic()
  budget_s = float(kw.get("budget_s", 25.0))
  regions, found = [], {}
  if kw.get("read_as") == "SKIP":
    return _read_sheet(index, mm_per_pt, **kw)
  if site_only:
    res = Extraction()
    res.stats["plan_regions"] = {"count": 0}
    res.stats["site_only"] = True
    res.notes.append(C.note("SHEET_SITE_ITEMS_ONLY"))
    return _with_site(res, index, mm_per_pt, kw)
  
  if kw.get("read_as") in (None, "PLAN_ITEMS") and sum(1 for c in VW.captions(index.words) if c["kind"] == "STRUCT_PLAN") < 2 and sheet_kind(index.words)["kind"] != "STRUCTURAL":
    try:
      regions, found = PR.find(index, mm_per_pt, started + 0.3 * budget_s, composite)
    except W.TimeLimit:
      regions, found = [], {}
  if not regions:
    if regions_only:
      res = Extraction()
      res.stats["plan_regions"] = {"count": 0}
      return res
    return _with_site(_read_sheet(index, mm_per_pt, **kw), index, mm_per_pt, kw)
  return _with_site(_read_regions(index, mm_per_pt, regions, found, started=started, budget_s=budget_s, **{k: v for k, v in kw.items() if k != "budget_s"}), index, mm_per_pt, kw)

def _scan_reading_notes(res: Extraction, scan: dict | None) -> None:
  if not scan:
    return
  if scan.get("ocr_split"):
    res.notes.append(C.note("SCAN_FIGURES_ASKED", count=int(scan["ocr_split"]), at=list(scan.get("ocr_split_at") or [])))
  if scan.get("ocr_repaired"):
    res.notes.append(C.note("SCAN_FIGURES_REPAIRED", count=int(scan["ocr_repaired"]), repairs=list(scan.get("ocr_repairs") or [])))

def _with_electrical(res: Extraction, electrical: dict | None, kw: dict) -> None:
  found = EL.candidates(electrical, _site_ctx(kw), Candidate, _finish_site)
  res.candidates.extend(found)
  res.notes.extend(EL.sheet_notes(electrical))
  res.stats["electrical_items"] = len(found)

def _identity_gate(res: Extraction, identity: dict | None) -> None:
  if not identity:
    return
  res.stats["sheet_identity"] = {k: identity.get(k) for k in ("discipline", "sheet_type", "floor", "basis", "confidence", "role", "plan_kind", "floor_basis", "read_as")}
  if not SID.gates_services(identity):
    return
  left: dict = {}
  for c in res.candidates:
    if c.category != "SITE":
      left[c.category] = left.get(c.category, 0) + 1
  res.candidates[:] = [c for c in res.candidates if c.category == "SITE"]
  if left:
    res.notes.append(C.note("SERVICES_SHEET_BACKDROP_LEFT_OUT", discipline=identity.get("discipline"), sheet_type=identity.get("sheet_type"), basis=identity.get("basis"),
      confidence=identity.get("confidence"), left_out=left))

def _pdf_type_notes(res: Extraction, pdf: dict | None) -> None:
  if not pdf:
    return
  res.stats["pdf_type"] = pdf
  if pdf.get("type") == "VECTOR_OUTLINED" and not pdf.get("text_recovered"):
    res.notes.append(C.note("OUTLINED_TEXT_NOT_READ", ocr_error=pdf.get("ocr_error")))
  if pdf.get("type") == "VECTOR_NOLETTER":
    res.notes.append(C.note("NO_LETTERING_PAGE", drawn_segments=pdf.get("drawn_segments")))

def run_extraction(index, mm_per_pt: float, *, frame: dict | None = None, **kw) -> Extraction:
  scan = kw.pop("scan_reading", None)
  pdf = kw.pop("pdf_type", None)
  identity = kw.pop("identity", None)
  electrical = kw.pop("electrical", None)
  if identity:
    kw["read_as"] = SID.read_as(identity)
    kw["role_info"] = {"role": identity.get("role"), "title": identity.get("role_title"), "plan_kind": identity.get("plan_kind")}
    kw["discipline"] = identity.get("discipline")
  token = OS.FROM_PICTURE.set(bool((pdf or {}).get("lines_from_picture")))
  try:
    res = _run_extraction_framed(index, mm_per_pt, frame=frame, **kw)
  finally:
    OS.FROM_PICTURE.reset(token)
  _identity_gate(res, identity)
  _identity_gate(res, identity)
  if (identity or {}).get("mixed"):
    res.notes.append(C.note("MIXED_SHEET", discipline=identity.get("discipline")))
  _pdf_type_notes(res, pdf)
  _with_electrical(res, electrical, kw)
  _scan_reading_notes(res, scan)
  return res

def _run_extraction_framed(index, mm_per_pt: float, *, frame: dict | None = None, **kw) -> Extraction:
  fr = OF.Frame.from_json(frame) if frame else OF.detect(index.words, index.bbox, index.segs, index.kinds)
  
  if fr.identity:
    return _run_extraction_upright(index, mm_per_pt, **kw)
  kw = {**kw, "views_meta": OC.views_to_upright(kw.get("views_meta"), fr)}
  res = _run_extraction_upright(OT.turn_index(index, fr), mm_per_pt, **kw)
  OC.extraction_to_page(res, fr)
  res.stats["sheet_frame"] = fr.to_json()
  res.notes.insert(0, C.note("SHEET_READ_UPRIGHT", turn_deg=fr.turn_deg, skew_deg=round(fr.skew_deg, 2)))
  return res
