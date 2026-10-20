from __future__ import annotations
import math
import re
from decimal import Decimal
from app.engine.measure import formwork_model as FM
from dataclasses import dataclass, field, replace
from app.engine.measure import frame as FR
from app.engine.measure import model_range as MR
from app.engine.measure.units import q4, q6

ZERO, HUNDRED = Decimal("0"), Decimal("100")
SOURCE_PDF = "PDF_TAKEOFF"
VOLUME_FORMULA = "SOLID_NET_VOLUME"

SWITCH_PARAM, PREFER_PARAM, POSITION_PARAM, TRUST_PARAM = "one_total", "one_total_prefer", "one_total_position_tol_mm", "one_total_trust_pct"
ONE_TOTAL_PARAMS = {
  SWITCH_PARAM: (0.0, 0.0, 1.0),
  PREFER_PARAM: (0.0, 0.0, 2.0),
  POSITION_PARAM: (100.0, 10.0, 1000.0),
  TRUST_PARAM: (50.0, 0.0, 100.0),
}
PREFER_NAMES = {0: "EXACT", 1: "DRAWING", 2: "MODEL"}

PDF_CLASS = {"COLUMN": "COLUMN", "FOOTING": "FOOTING", "BEAM": "BEAM", "LINTEL": "BEAM", "SLAB": "SLAB", "STAIR": "STAIR"}
POINT_CLASSES = ("COLUMN", "FOOTING")
SIZED_CLASSES = ("COLUMN", "FOOTING")
STAIR_ROLES = ("STAIR", "STAIR_FLIGHT", "LANDING")
MAX_LIST = 300
MAX_VOTE_PAIRS = 4_000_000
MARK_WEIGHT, POSITION_WEIGHT, SIZE_WEIGHT = 3.0, 2.0, 1.0
MEASURED_BAND = 3.0
WORST_BAND = 100.0

CODE_DIFFERS, CODE_DRAWING_USED = "ONE_TOTAL_DIFFERS", "ONE_TOTAL_DRAWING_USED"
ONE_TOTAL_CODES = (CODE_DIFFERS, CODE_DRAWING_USED)

_TOKEN = re.compile(r"(?<![0-9A-Za-z])[A-Za-z]{1,4}\s*[-_./]?\s*\d{1,4}[A-Za-z]?(?![0-9A-Za-z])")

def norm(text) -> str:
  return re.sub(r"[^0-9A-Za-z]", "", str(text or "")).upper()

def keys_of(*texts) -> frozenset:
  out: set = set()
  for t in texts:
    if not t:
      continue
  
    n = norm(t)
    if n:
      out.add(n)
    for m in _TOKEN.finditer(str(t)):
      k = norm(m.group(0))
      if k:
        out.add(k)
  return frozenset(out)

def params_of(ctx) -> dict:
  from app.engine.measure.derived import resolve_params
  resolved = resolve_params(ctx)
  return {name: float(resolved[name]["value"]) for name in ONE_TOTAL_PARAMS}

def is_on(ctx) -> bool:
  if getattr(ctx, "takeoff", None) is None:
    return False
  return params_of(ctx)[SWITCH_PARAM] >= 0.5

def adjudicable_ids(ctx) -> frozenset:
  return frozenset(str(f.measurement_id) for f in tuple(getattr(ctx.takeoff, "formwork", ()) or ()) if PDF_CLASS.get(f.category) and int(f.count or 0) > 0)

@dataclass
class Member:
  element: object
  cls: str
  keys: frozenset
  pos: tuple | None
  size: tuple | None
  rows: list
  qty: Decimal
  level: object = None

@dataclass
class Instance:
  mid: str
  idx: int
  cls: str
  keys: frozenset
  pos: tuple | None
  size: tuple | None
  level: object
  group: str | None = None

@dataclass
class Mark:
  mid: str
  tag: str | None
  category: str
  cls: str
  level: object
  count: int
  rows: list
  qty: Decimal
  size: tuple | None
  instances: list = field(default_factory=list)

@dataclass
class Outcome:
  drop_model: set = field(default_factory=set)
  drop_pdf: set = field(default_factory=set)
  annotate: dict = field(default_factory=dict)
  stats: dict = field(default_factory=dict)

def model_class(el) -> str | None:
  cat = FM.category_of(el)
  if cat in ("COLUMN", "FOOTING", "SLAB"):
    return cat
  if cat in ("BEAM", "LINTEL"):
    return "BEAM"
  if (el.role or "").upper() in STAIR_ROLES:
    return "STAIR"
  return None

def _centre(el) -> tuple | None:
  lo, hi = el.bbox_min_mm, el.bbox_max_mm
  if not lo or not hi:
    return None
  try:
    return ((float(lo[0]) + float(hi[0])) / 2.0, (float(lo[1]) + float(hi[1])) / 2.0)
  except (TypeError, ValueError):
    return None

def _plan_size(el) -> tuple | None:
  lo, hi = el.bbox_min_mm, el.bbox_max_mm
  if not lo or not hi:
    return None
  try:
    return FR.size_class(abs(float(hi[0]) - float(lo[0])), abs(float(hi[1]) - float(lo[1])))
  except (TypeError, ValueError):
    return None

def _inputs(row) -> dict:
  return ((row.trace or {}).get("inputs")) or {}

def model_members(elements, model_rows, dropped) -> list:
  by_el: dict = {}
  for r in model_rows:
    if r.element_id is None or r.unit != "m3" or r.formula_code != VOLUME_FORMULA or r.quantity <= 0:
      continue
    if (r.solid_id, r.work_item_code) in dropped:
      continue
    by_el.setdefault(r.element_id, []).append(r)
  out = []
  
  for el in sorted(elements, key=lambda e: str(e.id)):
    rows = by_el.get(el.id)
    cls = model_class(el)
    if not rows or cls is None:
      continue
    keys = keys_of(getattr(el, "type_mark", None), getattr(el, "name", None), getattr(el, "ifc_global_id", None))
    out.append(Member(el, cls, keys, _centre(el), _plan_size(el) if cls in SIZED_CLASSES else None, rows, sum((r.quantity for r in rows), ZERO), el.level_id))
  return out

def _placed(takeoff) -> tuple:
  frames = FR.frames_of(takeoff)
  group_of = {a.view: a.group for a in tuple(getattr(takeoff, "alignments", ()) or ())}
  return frames, group_of

def marks_of(ctx, pdf_rows, only) -> list:
  rows_by: dict = {}
  for r in pdf_rows:
    mid = _inputs(r).get("measurement_id")
    if mid and r.unit == "m3" and r.quantity > 0:
      rows_by.setdefault(str(mid), []).append(r)
  frames, group_of = _placed(ctx.takeoff)
  out = []
  
  for f in sorted(tuple(getattr(ctx.takeoff, "formwork", ()) or ()), key=lambda b: str(b.measurement_id)):
    mid = str(f.measurement_id)
    cls = PDF_CLASS.get(f.category)
    if cls is None or mid not in only or mid not in rows_by:
      continue
    rows = rows_by[mid]
    n = int(f.count or 0)
    if n <= 0:
      continue
  
    size = FR.size_class(float(f.length_mm), float(f.width_mm)) if cls in SIZED_CLASSES else None
    mk = Mark(mid, f.tag, f.category, cls, f.level_id, n, rows, sum((r.quantity for r in rows), ZERO), size)
    keys = keys_of(f.tag)
    group = group_of.get(f.frame) if f.frame else None
    frame = frames.get(group) if group is not None else None
    points = tuple(f.points_mm or ())
    for i in range(n):
      pos = None
      if frame is not None and len(points) == n:
        try:
          pos = FR.frame_xy(frame, f.frame, float(points[i][0]), float(points[i][1]))
        except (TypeError, ValueError, IndexError):
          pos = None
      mk.instances.append(Instance(mid, i, cls, keys, pos, size, f.level_id, group))
    out.append(mk)
  return out

def _vote(marks, members) -> dict:
  model_pts, seen = [], set()
  for m in members:
    if m.cls in POINT_CLASSES and m.pos is not None:
      cell = (round(m.pos[0] / FR.GRID_MM), round(m.pos[1] / FR.GRID_MM), m.size)
      if cell not in seen:
        seen.add(cell)
        model_pts.append(FR.FramePoint(m.pos[0], m.pos[1], m.size, None))
  by_group: dict = {}
  
  for mk in marks:
    if mk.cls in POINT_CLASSES:
      for ins in mk.instances:
        if ins.pos is not None and ins.group is not None:
          by_group.setdefault(ins.group, []).append(FR.FramePoint(ins.pos[0], ins.pos[1], ins.size, None))
          
  out: dict = {}
  for group in sorted(by_group):
    pts = by_group[group]
    if not model_pts or len(pts) * len(model_pts) > MAX_VOTE_PAIRS:
      out[group] = None
      continue
    v = FR.vote_offset(model_pts, pts)
    out[group] = None if v is None else {"dx": round(v["dx"], 2), "dy": round(v["dy"], 2), "supporters": v["supporters"], "compared": v["compared"]}
  return out

def _level_ok(a, b) -> bool:
  return a is None or b is None or a == b

def _cell(pos, size) -> tuple:
  return (math.floor(pos[0] / size), math.floor(pos[1] / size))

def _pair(marks, members, offsets, tol_mm) -> tuple:
  by_cls: dict = {}
  for m in members:
    by_cls.setdefault(m.cls, []).append(m)
  cell_size = max(tol_mm, 1.0)
  grids: dict = {}
  names: dict = {}
  for cls, ms in by_cls.items():
    g: dict = {}
    nm: dict = {}
    
    for i, m in enumerate(ms):
      if m.pos is not None:
        g.setdefault(_cell(m.pos, cell_size), []).append(i)
      for k in m.keys:
        nm.setdefault(k, []).append(i)
    grids[cls], names[cls] = g, nm
  cands = []
  
  for mk in marks:
    ms = by_cls.get(mk.cls) or []
    if not ms:
      continue
    for ins in mk.instances:
      near: set = set()
      for k in ins.keys:
        near.update(names[mk.cls].get(k, ()))
      pos = None
      off = offsets.get(ins.group)
      
      if ins.pos is not None and off is not None:
        pos = (ins.pos[0] + off["dx"], ins.pos[1] + off["dy"])
        cx, cy = _cell(pos, cell_size)
        for dx in (-1, 0, 1):
          for dy in (-1, 0, 1):
            near.update(grids[mk.cls].get((cx + dx, cy + dy), ()))
            
      for j in near:
        m = ms[j]
        if not _level_ok(ins.level, m.level):
          continue
        mark_ok = bool(ins.keys & m.keys)
        dist = math.hypot(pos[0] - m.pos[0], pos[1] - m.pos[1]) if (pos is not None and m.pos is not None) else None
        pos_ok = dist is not None and dist <= tol_mm
        if not (mark_ok or pos_ok):
          continue
        size_ok = FR._same_size(ins.size, m.size)
        if pos_ok and not mark_ok and not size_ok:
          continue
        score = (MARK_WEIGHT if mark_ok else 0.0) + (POSITION_WEIGHT if pos_ok else 0.0) + (SIZE_WEIGHT if size_ok else 0.0) - (dist or 0.0) / 1.0e4
        by = "MARK+POSITION" if (mark_ok and pos_ok) else "MARK" if mark_ok else "POSITION"
        cands.append((-score, ins.mid, ins.idx, str(m.element.id), id(ins), id(m), ins, m, by, size_ok))
        
  cands.sort(key=lambda c: c[:4])
  used_i, used_m, pairs = set(), set(), []
  for *_, ins, m, by, size_ok in cands:
    if id(ins) in used_i or id(m) in used_m:
      continue
    used_i.add(id(ins))
    used_m.add(id(m))
    pairs.append((ins, m, by, size_ok))
  return pairs

def _band_model(rows, qty) -> float:
  if qty <= 0:
    return WORST_BAND
  total = 0.0
  for r in rows:
    rg = MR.range_for_entry(r) if not isinstance((r.trace or {}).get("range"), dict) else r.trace["range"]
    total += float(r.quantity) * max(abs(float(rg.get("low_pct") or 0.0)), abs(float(rg.get("high_pct") or 0.0)))
  return total / float(qty)

def _band_pdf(rows) -> float:
  qty = sum((r.quantity for r in rows), ZERO)
  if qty <= 0:
    return WORST_BAND
  total = 0.0
  
  for r in rows:
    rg = (r.trace or {}).get("range")
    if isinstance(rg, dict):
      if not rg.get("bounded", True) or rg.get("leaves_out"):
        band = WORST_BAND
      else:
        band = max(abs(float(rg.get("low_pct") or 0.0)), abs(float(rg.get("high_pct") or 0.0)))
    else:
      band = MEASURED_BAND
    total += float(r.quantity) * band
  return total / float(qty)

def _winner(prefer: int, model_band: float, pdf_band: float) -> tuple:
  if prefer == 1:
    return "DRAWING", "CHOICE_DRAWING"
  if prefer == 2:
    return "MODEL", "CHOICE_MODEL"
  if model_band < pdf_band - 1e-9:
    return "MODEL", "MODEL_MORE_EXACT"
  if pdf_band < model_band - 1e-9:
    return "DRAWING", "DRAWING_MORE_EXACT"
  return "DRAWING", "TIE_DRAWING"

def _pct(a: Decimal, b: Decimal) -> Decimal | None:
  if b <= 0:
    return None
  return q4((a - b) / b * HUNDRED)

def _row_band(row, source: str) -> tuple:
  """(low_pct, high_pct, bounded) of a kept row."""
  if source == "PDF":
    rg = (row.trace or {}).get("range")
    if isinstance(rg, dict):
      if not rg.get("bounded", True) or rg.get("leaves_out"):
        return 0.0, 0.0, False
      return float(rg.get("low_pct") or 0.0), float(rg.get("high_pct") or 0.0), True
    return -MEASURED_BAND, MEASURED_BAND, True
  rg = (row.trace or {}).get("range")
  rg = rg if isinstance(rg, dict) else MR.range_for_entry(row)
  return float(rg.get("low_pct") or 0.0), float(rg.get("high_pct") or 0.0), bool(rg.get("bounded", True))

def _cap(items: list) -> list:
  return items[:MAX_LIST]

def adjudicate(ctx, profile, elements, model_rows, pdf_rows, dropped=frozenset(), tolerance_pct=Decimal("5"), only=frozenset()) -> Outcome:
  p = params_of(ctx)
  prefer = int(round(p[PREFER_PARAM]))
  tol_mm = p[POSITION_PARAM]
  trust = p[TRUST_PARAM]
  out = Outcome()
  stats: dict = {"enabled": True, "ran": False, "prefer": PREFER_NAMES.get(prefer, "EXACT"), "tolerance_pct": str(tolerance_pct),
    "position_tolerance_mm": tol_mm, "trusted_share_pct": trust}
  
  members = model_members(elements, model_rows, dropped)
  marks = marks_of(ctx, pdf_rows, only)
  if not marks:
    stats["reason"] = "NO_DRAWING_MEMBERS"
    out.stats = stats
    return out
  if not elements:
    stats["reason"] = "NO_MODEL_ELEMENTS"
    out.stats = stats
    return out

  offsets = _vote(marks, members)
  pairs = _pair(marks, members, offsets, tol_mm)
  stats["ran"] = True
  stats["alignment"] = [{"group": g, "method": "VOTE" if o else "NONE", **(o or {})} for g, o in sorted(offsets.items(), key=lambda kv: str(kv[0]))]
  paired_by_mark: dict = {}
  paired_members: set = set()
  for ins, m, by, size_ok in pairs:
    paired_by_mark.setdefault(ins.mid, []).append((ins, m, by, size_ok))
    paired_members.add(id(m))

  groups: dict = {}
  for mk in marks:
    g = groups.setdefault((mk.cls, mk.level), {"drawing": 0, "matched": 0, "marks": []})
    g["drawing"] += mk.count
    g["matched"] += len(paired_by_mark.get(mk.mid, ()))
    g["marks"].append(mk)
  model_count: dict = {}
  for key in groups:
    model_count[key] = sum(1 for m in members if m.cls == key[0] and _level_ok(key[1], m.level))

  decisions: list = []
  drawing_only: list = []
  not_trusted: list = []
  distrusted: set = set()
  
  for key, g in sorted(groups.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))):
    n_model = model_count[key]
    if n_model <= 0:
      continue
    share = 100.0 * g["matched"] / max(1, min(g["drawing"], n_model))
    if share + 1e-9 < trust:
      distrusted.add(key)
      not_trusted.append({"category": key[0], "level_id": str(key[1]) if key[1] else None, "drawing_members": g["drawing"], "model_members": n_model,
        "matched": g["matched"], "share_pct": round(share, 1)})
      
  for mk in sorted(marks, key=lambda x: x.mid):
    key = (mk.cls, mk.level)
    got = paired_by_mark.get(mk.mid, [])
    k = len(got)
    base = {"measurement_id": mk.mid, "tag": mk.tag, "category": mk.category, "level_id": str(mk.level) if mk.level else None, "members": mk.count,
      "matched": k, "drawing_m3": str(q6(mk.qty))}
    if key in distrusted:
      out.drop_pdf.add(mk.mid)
      decisions.append({**base, "state": "NOT_MATCHED", "used": "MODEL", "reason": "MATCHING_NOT_TRUSTED", "conflict": True, "element_ids": [], "by": None,
        "model_m3": None, "difference_pct": None, "size_differs": False})
      continue
  
    if k == 0:
      drawing_only.append({**base, "why": "NO_MODEL_MEMBER" if model_count[key] <= 0 else "NO_PARTNER_IN_MODEL"})
      continue
    model_qty = sum((m.qty for _, m, _, _ in got), ZERO)
    share_qty = mk.qty * Decimal(k) / Decimal(mk.count)
    diff = _pct(share_qty, model_qty)
    size_differs = any(not size_ok for _, _, _, size_ok in got)
    complete = k == mk.count
    rows_model = [r for _, m, _, _ in got for r in m.rows]
    
    if complete:
      used, why = _winner(prefer, _band_model(rows_model, model_qty), _band_pdf(mk.rows))
      state = "COMPLETE"
    else:
      used, why, state = "DRAWING", "PARTIAL_DRAWING_COVERS_ALL", "PARTIAL"
    conflict = (not complete) or size_differs or (diff is not None and abs(diff) > tolerance_pct)
    bys = sorted({by for _, _, by, _ in got})
    rec = {**base, "state": state, "used": used, "reason": why, "conflict": bool(conflict), "size_differs": bool(size_differs),
      "model_m3": str(q6(model_qty)), "drawing_matched_m3": str(q6(share_qty)), "difference_pct": str(diff) if diff is not None else None,
      "by": bys[0] if len(bys) == 1 else "MIXED", "element_ids": [str(m.element.id) for _, m, _, _ in got]}
    
    if used == "DRAWING":
      for r in rows_model:
        out.drop_model.add((r.solid_id, r.work_item_code))
      other = _pct(model_qty, share_qty)
      out.annotate[mk.mid] = {"state": state, "model_m3": str(q6(model_qty)), "difference_pct": rec["difference_pct"], "conflict": bool(conflict), "reason": why,
        "elements": len(got), "other_pct": str(other) if other is not None else None}
    else:
      out.drop_pdf.add(mk.mid)
    decisions.append(rec)

  member_only: list = []
  covered_classes = {(mk.cls, mk.level) for mk in marks}
  for m in members:
    if id(m) in paired_members:
      continue
    if not any(c == m.cls and _level_ok(lv, m.level) for c, lv in covered_classes):
      continue
    if any((c == m.cls and _level_ok(lv, m.level)) and (c, lv) in distrusted for c, lv in covered_classes):
      continue
    member_only.append({"element_id": str(m.element.id), "mark": getattr(m.element, "type_mark", None) or getattr(m.element, "name", None),
      "category": m.cls, "level_id": str(m.level) if m.level else None, "model_m3": str(q6(m.qty))})

  kept: dict = {}
  def put(cls, source, row):
    k = kept.setdefault(cls, {"model": ZERO, "drawing": ZERO, "low": 0.0, "high": 0.0, "unbounded": 0})
    k["model" if source == "MODEL" else "drawing"] += row.quantity
    lo, hi, bounded = _row_band(row, "PDF" if source == "DRAWING" else "MODEL")
    if not bounded:
      k["unbounded"] += 1
      return
    k["low"] += float(row.quantity) * lo / 100.0
    k["high"] += float(row.quantity) * hi / 100.0
    
  for m in members:
    if id(m) not in paired_members and not any(c == m.cls and _level_ok(lv, m.level) for c, lv in covered_classes):
      continue
    for r in m.rows:
      if (r.solid_id, r.work_item_code) not in out.drop_model:
        put(m.cls, "MODEL", r)
  for mk in marks:
    if mk.mid in out.drop_pdf:
      continue
    for r in mk.rows:
      put(mk.cls, "DRAWING", r)
      
  for d in decisions:
    if not d["conflict"] or d["state"] == "NOT_MATCHED" or d["model_m3"] is None:
      continue
    cls = PDF_CLASS.get(d["category"])
    k = kept.get(cls)
    if k is None:
      continue
    model_q, draw_q = float(d["model_m3"]), float(d["drawing_matched_m3"])
    used_q, other_q = (model_q, draw_q) if d["used"] == "MODEL" else (draw_q, model_q)
    k["low"] -= max(0.0, used_q - other_q)
    k["high"] += max(0.0, other_q - used_q)
    
  totals = {}
  for cls, k in sorted(kept.items()):
    total = k["model"] + k["drawing"]
    totals[cls] = {"model_m3": str(q6(k["model"])), "drawing_m3": str(q6(k["drawing"])), "total_m3": str(q6(total)),
      "low_m3": str(q6(total + Decimal(str(round(k["low"], 6))))), "high_m3": str(q6(total + Decimal(str(round(k["high"], 6))))),
      "bounded": k["unbounded"] == 0, "unbounded_rows": k["unbounded"]}
    
  conflicts = [d for d in decisions if d["conflict"]]
  stats.update({
    "pairs_found": len(pairs), "marks": len(marks), "model_members": len(members),
    "complete": sum(1 for d in decisions if d["state"] == "COMPLETE"), "partial": sum(1 for d in decisions if d["state"] == "PARTIAL"),
    "set_aside_not_matched": sum(1 for d in decisions if d["state"] == "NOT_MATCHED"), "drawing_only_marks": len(drawing_only),
    "model_only_members": len(member_only), "conflicts_total": len(conflicts),
    "decisions": _cap(decisions), "conflicts": _cap(conflicts), "drawing_only": _cap(drawing_only), "model_only": _cap(member_only),
    "not_trusted": _cap(not_trusted), "totals": totals,
    "used_model": sum(1 for d in decisions if d["used"] == "MODEL" and d["state"] != "NOT_MATCHED"),
    "used_drawing": sum(1 for d in decisions if d["used"] == "DRAWING"),
    "truncated": any(len(x) > MAX_LIST for x in (decisions, conflicts, drawing_only, member_only, not_trusted)),
  })
  out.stats = stats
  return out

def annotate_row(row, note: dict):
  trace = dict(row.trace or {})
  inputs = dict(trace.get("inputs") or {})
  inputs["one_total"] = note
  trace["inputs"] = inputs
  other = note.get("other_pct")
  
  if note.get("conflict") and other is not None:
    d = float(other)
    rg = trace.get("range")
    base = dict(rg) if isinstance(rg, dict) else {"grade": MR.MEASURED, "bounded": True, "low_pct": -MEASURED_BAND, "high_pct": MEASURED_BAND, "leaves_out": False,
      "drivers": [{"name": "hand measurement on the drawing", "basis": MR.MEASURED, "low_pct": -MEASURED_BAND, "high_pct": MEASURED_BAND}], "by": MR.STAMPED}
    if base.get("bounded", True) and not base.get("leaves_out"):
      base["low_pct"] = round(min(float(base.get("low_pct") or 0.0), d), 2)
      base["high_pct"] = round(max(float(base.get("high_pct") or 0.0), d), 2)
      base["drivers"] = [*list(base.get("drivers") or ()), {"name": "the model gives another quantity", "basis": MR.MEASURED, "low_pct": round(min(0.0, d), 2), "high_pct": round(max(0.0, d), 2)}]
      
      if base.get("grade") not in (MR.ASSUMED, MR.MEASURED):
        base["grade"] = MR.MEASURED
      trace["range"] = base
  codes = [CODE_DRAWING_USED] + ([CODE_DIFFERS] if note.get("conflict") else [])
  return replace(row, trace=trace, warnings=tuple(dict.fromkeys((*row.warnings, *codes))))

def one_total_check(solids: list, ledger: list) -> list:
  failures: list = []
  
  for r in ledger:
    note = _inputs(r).get("one_total")
    if note is None:
      continue
    if getattr(r, "source_kind", None) != SOURCE_PDF:
      failures.append(f"one-total note on a row that is not from a drawing on solid {r.solid_id}")
    if not _inputs(r).get("measurement_id"):
      failures.append(f"one-total note without a measurement on solid {r.solid_id}")
  return failures
