from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
from app.modules.drawings_boq.takeoff.proof import known_facts as KF
from app.modules.drawings_boq.lab import tolerances as T
from app.modules.drawings_boq.takeoff.proof import offline_accept as OA
from app.modules.drawings_boq.takeoff.proof import offline_run as OR
from app.modules.drawings_boq.lab.aliases import KEY_LABEL, SOFTWARE_UNIT, bill_quantity, software_key
from app.modules.drawings_boq.takeoff import stair_twins as ST
from app.modules.drawings_boq.takeoff.proof import benchmark as BM
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.takeoff.proof import levels as LV
from app.engine.measure import rulebook as RB
from app.modules.drawings_boq.takeoff.prep import page_role as PRL
from types import SimpleNamespace
from app.modules.drawings_boq.takeoff.extract import beam_overlap_service as BOS
from app.modules.drawings_boq.takeoff.extract import slab_label as SL
from app.modules.drawings_boq.takeoff.extract import safe as SF
from app.modules.drawings_boq.takeoff.extract import note_scope as NS
from app.modules.drawings_boq.takeoff import register as RGS

SIZE_TOL_PCT = 2.0
MATCH, NEAR, DIFF, MISSING, EXTRA, NO_TRUTH = "MATCH", "NEAR", "DIFF", "MISSING", "EXTRA", "NO_TRUTH"
STATUS_RANK = {MATCH: 0, NEAR: 1, DIFF: 2, NO_TRUTH: 3, MISSING: 4, EXTRA: 4}
CLASS_RANK = {"DRAWING": 0, "CONVENTION": 1, "NEEDS_DECISION": 2, "QS_ERROR": 3}
DETAIL_SHEET_CATEGORIES = ("WALL", "ROOM", "DOOR", "WINDOW")      
PLAN_CATEGORIES = ("WALL", "ROOM", "DOOR", "WINDOW", "LINTEL", "STAIR", "COLUMN", "BEAM", "SLAB", "FOOTING")
NOT_PLAN_TYPES = ("SECTION", "DETAIL", "SCHEDULE", "NOTES", "COVER", "LEGEND", "ELEVATION")

def r3(v):
  if isinstance(v, bool) or v is None:
    return v
  if isinstance(v, float):
    return round(v, 3) if math.isfinite(v) else None
  if isinstance(v, dict):
    return {str(k): r3(x) for k, x in v.items()}
  if isinstance(v, (list, tuple)):
    return [r3(x) for x in v]
  return v

CASE_RULES_NOTE = "These rules were read from the totals of one workbook, not stated by the QS, and could fit one building. Until the QS answers, a number that depends on them is that workbook's, not a convention."

def digest(doc: dict) -> str:
  body = {k: v for k, v in doc.items() if k not in ("hash", "timings", "stage_view", "members", "wall_faces", "warnings", "fact_decisions", "options", "quantities", "robust", "steel", "reading_work", "levels", "mark_join")}
  return hashlib.sha256(json.dumps(r3(body), sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")).hexdigest()

WALL_FORMULA = "PDF_TAKEOFF_LENGTH_X_HEIGHT_X_THICKNESS"
WALL_FAMILY_OF_CODE = {"MAS-BRICK": "BRICK_WALLS", "CON-RCC": "RCC_WALLS"}

def family_of(r: dict) -> str | None:
  trace = r.get("trace") or {}
  inputs = trace.get("inputs") or {}
  src = inputs.get("formwork_source") or inputs.get("steel_source") or {}
  family = software_key(r.get("formula_code") or "", inputs.get("tag") or src.get("tag"), trace.get("label"))
  if family is None and r.get("formula_code") == WALL_FORMULA:
    family = WALL_FAMILY_OF_CODE.get(r.get("work_item_code"))
  return family

GRADE_SPLIT = ("PCC",)       

def _nos(r: dict) -> float:
  for step in ((r.get("trace") or {}).get("steps") or []):
    if step.get("op") == "count" and step.get("nos") is not None:
      try:
        return float(step["nos"])
      except (TypeError, ValueError):
        return 1.0
  return 1.0

def frame_length_m(r: dict) -> float:
  """The running length of the door frames of a ledger row: the length each frame is measured round (two jambs and the head) times how many there are."""
  try:
    return float(((r.get("trace") or {}).get("inputs") or {}).get("length_mm") or 0.0) / 1000.0 * _nos(r)
  except (TypeError, ValueError):
    return 0.0

def trace_lines(rows: list, floor_of: dict, catalog: dict, derive=()) -> list:
  groups: dict = {}
  for r in rows:
    family = family_of(r)
    floor = floor_of.get(str(r.get("level_id"))) if r.get("level_id") else None
    code = r.get("work_item_code") or "?"
    unit = SOFTWARE_UNIT.get(family) if family in SOFTWARE_UNIT else (r.get("unit") or "")
    grade = str(r.get("material_grade") or "-") if family in GRADE_SPLIT else ""
    k = (code, family or "-", floor or "-", unit, grade)
    g = groups.setdefault(k, {"si": 0.0, "rows": 0})
    q = float(r.get("quantity") or 0)
    g["si"] += q
    g["rows"] += 1
    if "DOOR_FRAMES_RFT" in derive and family == "DOOR_FRAMES":
      d = groups.setdefault((code, "DOOR_FRAMES_RFT", floor or "-", "m", ""), {"si": 0.0, "rows": 0})
      d["si"] += frame_length_m(r)
      d["rows"] += 1

  out = []
  for (code, family, floor, unit, grade), g in sorted(groups.items()):
    wi = catalog.get(code)
    out.append({"key": f"{code}/{family}/{floor}" + (f"@{grade}" if grade else ""), "code": code, "family": None if family == "-" else family, "floor": None if floor == "-" else floor, "unit": unit,
      "grade": grade or None, "si": g["si"], "rows": g["rows"], "description": (getattr(wi, "description", None) or code)})
  return out

def to_unit(value_si: float, si_unit: str, unit: str):
  qty, target_si, one_si = bill_quantity("", unit, 1.0)
  if target_si != si_unit or not one_si:
    return None
  return value_si * (qty / one_si)

def resolve(entry: dict, lines: list) -> list:
  key = entry["key"]
  if entry.get("grade"):
    lines = [l for l in lines if l.get("grade") == entry["grade"]]
  exact = [l for l in lines if l["key"] == key]

  if exact:
    return exact
  parts = key.split("/")
  if len(parts) >= 2 and parts[1] in ("ALL", "*"):
    every = [l for l in lines if l["code"] == parts[0]]
    if every:
      return every
  if len(parts) == 2 and parts[0] and any(l["code"] == parts[0] for l in lines):
    got = [l for l in lines if l["code"] == parts[0] and (l["floor"] or "-") == parts[1]]
    if got:
      return got
  fams = entry.get("families")
  if fams:
    got = [l for l in lines if l["family"] in fams]
    if got:
      return got
  fam = entry.get("family")
  if fam:
    got = [l for l in lines if l["family"] == fam and (not entry.get("floor") or l["floor"] == entry["floor"])]
    if got:
      return got
  words = entry.get("match") or []
  if words:
    return [l for l in lines if all(w in l["description"].lower() for w in words)]
  return []

def _pct(a, b):
  return None if a is None or b in (None, 0) else (a - b) / b * 100.0

def _status(trace, drawing, tol):
  if drawing is None:
    return NO_TRUTH
  e = _pct(trace, drawing)
  if e is None:
    return DIFF
  return MATCH if abs(e) <= tol else NEAR if abs(e) <= 2 * tol else DIFF

def score_lines(expected: list, lines: list) -> tuple:
  taken: set = set()
  groups: dict = {}
  order: list = []

  for e in expected:
    got = resolve(e, lines)
    sig = tuple(sorted(l["key"] for l in got)) or ("~" + str(e.get("family") or e["key"]),)
    if sig not in groups:
      groups[sig] = {"entries": [], "lines": got}
      order.append(sig)
    groups[sig]["entries"].append(e)
    taken.update(l["key"] for l in got)
  out = []
  
  for sig in order:
    g = groups[sig]
    es, got = g["entries"], g["lines"]
    unit = next((e["unit"] for e in es if e["unit"]), "")
    qs = sum(e["qs"] for e in es if e["qs"] is not None) if any(e["qs"] is not None for e in es) else None
    drawing = None if any(e["drawing"] is None for e in es) else sum(e["drawing"] for e in es)
    cls = max((e["class"] for e in es), key=lambda c: CLASS_RANK[c])
    fam = es[0].get("family") if len({e.get("family") for e in es}) == 1 else None
    tol = next((e["tolerance_pct"] for e in es if e["tolerance_pct"] is not None), None)
    tol = T.default_for(fam) if tol is None and fam else (T.DEFAULT_TOLERANCE_PCT if tol is None else tol)
    trace, why = None, ""

    if got:
      conv = [to_unit(l["si"], l["unit"], unit) for l in got]
      if all(c is not None for c in conv):
        trace = sum(conv)
      else:
        why = f"unit: the bill says {unit or '?'}, Trace measured {', '.join(sorted({l['unit'] for l in got}))}"
    notes = "; ".join(e["note"] for e in es if e["note"])
    key = es[0]["key"] if len(es) == 1 else (fam or es[0]["key"])
    if trace is None:
      status = NO_TRUTH if drawing is None and not why else MISSING
    else:
      status = _status(trace, drawing, tol)
    out.append({"key": key, "item": es[0]["item"] if len(es) == 1 else KEY_LABEL.get(fam, es[0]["item"]), "unit": unit, "trace": trace, "qs": qs, "drawing": drawing,
      "diff_pct_qs": _pct(trace, qs), "diff_pct_drawing": _pct(trace, drawing), "status": status, "class": cls, "tolerance_pct": tol, "entries": len(es),
      "why": "; ".join(x for x in (why, notes if status not in (MATCH,) else "") if x)[:300]})

  extra = []
  for l in lines:
    if l["key"] in taken:
      continue
    extra.append(l)
  return out, extra

def extra_lines(extra: list) -> list:
  by: dict = {}
  for l in extra:
    k = l["family"] or l["code"]
    g = by.setdefault(k, {"key": k, "item": KEY_LABEL.get(l["family"], l["description"]), "unit": "", "trace": 0.0, "rows": 0, "floors": set()})
    unit = {"m3": "cft", "m2": "sft", "m": "rft"}.get(l["unit"], l["unit"])
    v = to_unit(l["si"], l["unit"], unit) if unit in ("cft", "sft", "rft") else l["si"]
    if g["unit"] and g["unit"] != unit:
      continue
    
    g["unit"] = unit
    g["trace"] += v if v is not None else 0.0
    g["rows"] += l["rows"]
    g["floors"].add(l["floor"] or "-")
  return [{"key": g["key"], "item": g["item"], "unit": g["unit"], "trace": g["trace"], "qs": None, "drawing": None, "diff_pct_qs": None, "diff_pct_drawing": None, "status": EXTRA, "class": "",
    "tolerance_pct": None, "entries": 0, "why": f"{g['rows']} ledger rows on {', '.join(sorted(g['floors']))}; no expected line"} for g in sorted(by.values(), key=lambda x: x["key"])]

def summarise(lines: list) -> dict:
  both = [l for l in lines if l["trace"] is not None and l["qs"] is not None]
  dr = [l for l in lines if l["trace"] is not None and l["drawing"] is not None]

  counts: dict = {}
  for l in lines:
    counts[l["status"]] = counts.get(l["status"], 0) + 1
  return {"lines": len(both), "within_10": sum(1 for l in both if abs(l["diff_pct_qs"]) <= 10.0), "within_5": sum(1 for l in both if abs(l["diff_pct_qs"]) <= 5.0),
    "expected_lines": sum(1 for l in lines if l["status"] != EXTRA), "with_a_number": sum(1 for l in lines if l["trace"] is not None and l["status"] != EXTRA),
    "against_drawing": len(dr), "within_10_drawing": sum(1 for l in dr if abs(l["diff_pct_drawing"]) <= 10.0), "within_5_drawing": sum(1 for l in dr if abs(l["diff_pct_drawing"]) <= 5.0),
    "status": dict(sorted(counts.items()))}

CATEGORY_OF_MARK = (("D", "DOOR"), ("W", "WINDOW"), ("V", "WINDOW"), ("C", "COLUMN"), ("F", "FOOTING"), ("B", "BEAM"), ("RB", "BEAM"), ("L", "LINTEL"))
SFT_PER_M2 = 10.7639104

def known_fact(f: dict) -> tuple:
  """A fact of facts.yaml (kinds of Data contracts item 5) -> (a fact known_facts.check can test, None), or (None, why it cannot be tested yet). The older known_facts kinds pass as they are."""
  kind = str(f.get("kind") or "").upper()

  if kind in KF.KINDS:
    return KF.normalise(f), None
  if kind == "COUNT_BY_MARK":
    mark = str(f.get("mark") or "").upper()
    cat = (f.get("category") or next((c for p, c in sorted(CATEGORY_OF_MARK, key=lambda x: -len(x[0])) if mark.startswith(p)), "")).upper()
    return KF.normalise({"kind": "COUNT", "category": cat, "tag": mark, "floor": f.get("floor"), "count": f.get("value"), "tolerance_pct": f.get("tolerance_pct")}), None
  if kind == "COUNT_BY_LABEL" and f.get("category"):
    return KF.normalise({"kind": "TOTAL", "category": f["category"], "floor": f.get("floor"), "count": f.get("value")}), None

  if kind in ("ROOM_SIZE", "AREA") and f.get("label"):
    v = float(f.get("value") or 0)
    m2 = v / SFT_PER_M2 if str(f.get("unit") or "m2").lower() in ("sft", "sqft") else v
    if str(f["label"]).upper() == "SLAB":
      return KF.normalise({"kind": "SLAB_AREA", "floor": f.get("floor"), "area_m2": m2, "tolerance_pct": f.get("tolerance_pct")}), None
    return KF.normalise({"kind": "ROOM_AREA", "name": f["label"], "floor": f.get("floor"), "area_m2": m2, "tolerance_pct": f.get("tolerance_pct")}), None
  return None, f"No check for {kind or 'this kind of'} facts exists yet."

def _mark(text) -> str:
  return re.sub(r"[^A-Z0-9]", "", str(text or "").upper())

def size_fact(read: list, f: dict) -> dict:
  """FOOTING_SIZE (mark, L and W in feet) and COLUMN_SIZE (mark, b and d in inches): the plan size the reader gave the items of that mark, against the size stated. The two sides may be turned
  (a footing read 5 by 4 is a footing stated 4 by 5). MISSING when no item carries the mark, or none carries a size."""
  kind = str(f.get("kind")).upper()
  category = "FOOTING" if kind == "FOOTING_SIZE" else "COLUMN"
  mark = _mark(f.get("mark"))
  to_mm = 304.8 if category == "FOOTING" else 25.4
  names = ("L", "W") if category == "FOOTING" else ("b", "d")
  want = sorted(float(f[n]) * to_mm for n in names)
  tol = float(f["tolerance_pct"] if f.get("tolerance_pct") is not None else SIZE_TOL_PCT) / 100.0
  unit = "ft" if category == "FOOTING" else "in"
  stated = " x ".join(f"{float(f[n]):g}" for n in names) + f" {unit}"
  sized, marked = [], []
  for sh in read:
    for c in sh["candidates"]:
      if c.category == category and _mark(c.tag) == mark:
        marked.append(sh["page_no"])
        p = c.params or {}
        if p.get("length_mm") and p.get("width_mm"):
          sized.append((sh["page_no"], sorted([float(p["length_mm"]), float(p["width_mm"])])))
          
  text = f"{category.lower()} {f.get('mark')} {stated}"
  if not marked:
    return {"text": text, "status": "MISSING", "expected": stated, "found": None, "message": f"No {category.lower()} marked {f.get('mark')} was read.", "pages": []}
  if not sized:
    return {"text": text, "status": "MISSING", "expected": stated, "found": None, "message": f"{f.get('mark')} was read on page(s) {sorted(set(marked))} with no size.", "pages": sorted(set(marked))}
  def close(a, b):
    return all(abs(x - y) <= tol * y for x, y in zip(a, b))
  shown = sorted({" x ".join(f"{v / to_mm:g}" for v in dims) + f" {unit}" for _p, dims in sized})
  if any(close(dims, want) for _p, dims in sized):
    return {"text": text, "status": "PASS", "expected": stated, "found": shown, "message": f"{f.get('mark')} read as {', '.join(shown)}: as stated.", "pages": sorted({p for p, _d in sized})}
  return {"text": text, "status": "FAIL", "expected": stated, "found": shown, "message": f"{f.get('mark')} was read as {', '.join(shown)}; {stated} is stated.", "pages": sorted({p for p, _d in sized})}

STEP_TOL_IN = 0.5

def _steps_of(rec: dict) -> list:
  return sorted((float(s["width_in"]), float(s["height_in"])) for s in rec.get("steps") or [])

def _step_text(steps: list) -> str:
  return ", ".join(f"{w:g} x {h:g}" for w, h in steps) + " in" if steps else "none"

def step_fact(read: list, f: dict) -> dict:
  mark = str(f.get("section") or "").strip().upper().replace(" ", "")
  by_mark = bool(re.fullmatch(r"[A-Z]{1,2}\d{1,2}", mark))
  want = sorted((float(s["width_in"]), float(s["height_in"])) for s in f["steps"])
  text = f"step table {f.get('section')} ({len(want)} steps)"
  stated = _step_text(want)
  
  recs = []
  for sh in read:
    for rec in ((sh.get("meta") or {}).get("footing_sections") or []):
      if rec.get("read") != "OK" or not rec.get("steps"):
        continue
      if by_mark and str(rec.get("mark") or "").upper() == mark or not by_mark and rec.get("wall_in") is not None and abs(float(rec["wall_in"]) - float(f["thickness_in"])) < 0.01:
        recs.append((sh["page_no"], rec))
        
  if not recs:
    return {"text": text, "status": "MISSING", "expected": stated, "found": None, "message": "No section of that " + ("mark" if by_mark else "wall") + " was read with steps.", "pages": []}
  def same(a, b):
    return len(a) == len(b) and all(abs(x[0] - y[0]) <= STEP_TOL_IN and abs(x[1] - y[1]) <= STEP_TOL_IN for x, y in zip(a, b))
  pages = sorted({p for p, _r in recs})
  shown = sorted({_step_text(_steps_of(r)) for _p, r in recs})
  ok = [r for _p, r in recs if same(_steps_of(r), want)]
  if ok and f.get("base_width_in") is not None:
    base = [round(float(r["base_width_mm"]) / 25.4, 1) for r in ok if r.get("base_width_mm")]
    if base and not any(abs(b - float(f["base_width_in"])) <= STEP_TOL_IN for b in base):
      return {"text": text, "status": "FAIL", "expected": stated, "found": shown, "message": f"The steps are as stated; the base is read {base[0]:g} in wide and {float(f['base_width_in']):g} in is stated.", "pages": pages}
  if ok:
    return {"text": text, "status": "PASS", "expected": stated, "found": shown, "message": f"{len(want)} steps read: as stated.", "pages": pages}
  return {"text": text, "status": "FAIL", "expected": stated, "found": shown, "message": f"The section was read with {'; '.join(shown)}; {stated} is stated.", "pages": pages}

def check_facts(read: list, facts: list) -> list:
  out = []
  for i, f in enumerate(facts):
    if str(f.get("kind") or "").upper() == "STEP_TABLE":
      try:
        out.append(step_fact(read, f))
      except (KeyError, TypeError, ValueError) as e:
        out.append({"text": f"fact {i + 1} (STEP_TABLE {f.get('section') or ''})".strip(), "status": "INVALID", "expected": None, "found": None, "message": f"missing or bad value: {e}", "pages": []})
      continue
    if str(f.get("kind") or "").upper() in ("FOOTING_SIZE", "COLUMN_SIZE"):
      try:
        out.append(size_fact(read, f))
      except (KeyError, TypeError, ValueError) as e:
        out.append({"text": f"fact {i + 1} ({f.get('kind')} {f.get('mark') or ''})".strip(), "status": "INVALID", "expected": None, "found": None, "message": f"missing or bad value: {e}", "pages": []})
      continue
    label = f"fact {i + 1} ({f.get('kind')} {f.get('mark') or f.get('label') or f.get('name') or f.get('section') or ''})".strip()
    try:
      known, why = known_fact(f)
    except (ValueError, TypeError) as e:
      out.append({"text": label, "status": "INVALID", "expected": f.get("value"), "found": None, "message": str(e), "pages": []})
      continue
    if known is None:
      out.append({"text": label, "status": "UNCHECKED", "expected": f.get("value"), "found": None, "message": why, "pages": []})
      continue
    r = KF.check(read, [known])[0]
    out.append({"text": r["text"], "status": r["status"], "expected": r["expected"], "found": r["found"], "message": r["message"], "pages": r["pages"]})
  return out

def _is_plan(r: dict) -> bool:
  ident = (r.get("meta") or {}).get("identity") or {}
  vote = ident.get("role_vote") or {}
  if vote.get("role") and not vote.get("held"):
    return vote["role"] in PRL.PLAN_ROLES
  if ident.get("sheet_type") == "PLAN":
    return True
  return any(v.get("sheet_type") == "PLAN" for v in (ident.get("views") or []))

def _live(c) -> bool:
  return c.decision != "REJECTED" and not (c.facts or {}).get("set_aside")

def _cand_floor(acc, c) -> str | None:
  view = ((c.facts or {}).get("view") or {})
  if view.get("level_id"):
    return acc.floor_of.get(__import__("uuid").UUID(str(view["level_id"])))
  s = acc.sheets.get(c.sheet_id)
  return acc.floor_of.get(s.level_id) if s is not None and s.level_id else None

def _floor_finish_sources(acc) -> list:
  """The pages of the storeys whose floor finish has two sources: rooms accepted for a floor finish and a floor total accepted too, or finish areas that add up to more than the gross floor area of the
  storey (the area table of the set, when it has one). Rooms are billed only when the storey has no total (Pack 158)."""
  from app.modules.drawings_boq.takeoff.extract import finishes as FN
  code_of = {m.id: m.work_item_code for m in acc.measurements}
  gross: dict = {}
  for read in acc.read.values():
    for r in read:
      for a in ((r.get("schedule") or {}).get("areas") or []):
        if a.get("kind") == "FLOOR" and a.get("m2"):
          gross[a.get("key")] = float(a["m2"])
          
  floors: dict = {}
  for c in acc.candidates:
    if c.decision != "ACCEPTED":
      continue
    f = c.facts or {}
    code = code_of.get(c.measurement_id) or ""
    if c.category == "ROOM" and code.startswith("FIN-FLOOR"):
      src = "ROOMS"
    elif f.get("foundation_item") in FN.FLOOR_ITEMS:
      src = "TOTAL"
    else:
      continue
    d = floors.setdefault(_cand_floor(acc, c) or "-", {"src": set(), "area": 0.0, "pages": set()})
    d["src"].add(src)
    d["area"] += float(f.get("area_m2") or 0.0)
    d["pages"].add(acc.sheets[c.sheet_id].page_no)
  where = next(iter(acc.drawings.values()))
  return [f"{where} p.{p}" for k, d in floors.items() if len(d["src"]) > 1 or (k in gross and d["area"] > gross[k]) for p in sorted(d["pages"])]

def page_votes(reads: list) -> list:
  out, plans = [], 0
  for pdf, read in reads:
    for r in read:
      ident = (r.get("meta") or {}).get("identity") or {}
      vote = ident.get("role_vote") or {}
      plans += 1 if _is_plan(r) else 0
      if vote.get("read_as") or (vote.get("held") and str(vote.get("why") or "").startswith("two strong")):
        out.append({"pdf": pdf, "page": r["page_no"], "role": vote.get("role"), "held": bool(vote.get("held")), "votes": vote.get("votes"), "why": vote.get("why"), "read_as": vote.get("read_as"),
          "signals": [f"{s['signal']} {s['certainty']}: {s['why']}" for s in vote.get("signals") or []]})
  return {"pages": out, "plan_pages": plans, "held": sum(1 for p in out if p["held"])}

def height_sources(reads: list) -> list:
  seen: dict = {}
  for _pdf, read in reads:
    for r in read:
      for c in r["candidates"]:
        if not _live(c):
          continue
        for n in c.notes or []:
          src = n.get("ladder") if (str(n.get("code") or "").startswith("HEIGHT_FROM") or n.get("code") == "NECK_HEIGHT_ASSUMED") else None
          if src:
            mm = (c.params or {}).get("height_mm") or (c.params or {}).get("depth_mm") or n.get("height_mm")
            key = (src.get("kind"), src.get("what"), src.get("floor"), src.get("basis"), round(float(mm), 1) if mm else None)
            seen[key] = seen.get(key, 0) + 1
  return [{"kind": k[0], "what": k[1], "floor": k[2], "basis": k[3], "mm": k[4], "rows": n} for k, n in sorted(seen.items(), key=lambda kv: str(kv[0]))]

def _held_for_scale(r: dict, live: list) -> bool:
  return _is_plan(r) and bool(live) and r.get("ratio") is None and all(any(n.get("code") == "SCALE_UNVERIFIED" for n in c.notes or []) for c in live)

def scale_held(reads: list) -> list:
  return [f"{pdf} p.{r['page_no']}" for pdf, read in reads for r in read if _held_for_scale(r, [c for c in r["candidates"] if _live(c)])]

def invariants(reads: list, accs: list, rows: list) -> list:
  res = []
  def add(name, bad, why):
    pages = sorted(set(bad))
    res.append({"name": name, "status": "FAIL" if bad else "PASS", "count": len(bad), "pages": pages[:40], "why": why})
  pdf_of = {}

  non_plan, structural, no_floor, no_scale = [], [], [], []
  for pdf, read in reads:
    for r in read:
      tag = f"{pdf} p.{r['page_no']}"
      live = [c for c in r["candidates"] if _live(c)]
      ident = (r.get("meta") or {}).get("identity") or {}
      if not _is_plan(r):
        wanted = DETAIL_SHEET_CATEGORIES if (ident.get("role_vote") or {}).get("role") == PRL.DETAIL else PLAN_CATEGORIES
        non_plan += [tag] * sum(1 for c in live if c.category in wanted)
      if ident.get("discipline") == "STRUCTURAL":
        structural += [tag] * sum(1 for c in live if c.category in ("DOOR", "WINDOW"))
      if _is_plan(r) and live:
        title = r.get("title") or {}
        if not title.get("composite") and not (title.get("level_hint") or ident.get("floor")):
          no_floor.append(tag)
        if r.get("ratio") is None:
          if not _held_for_scale(r, live):
            no_scale.append(tag)      

  add("PLAN_ITEMS_ONLY_ON_PLAN_PAGES", non_plan, "Walls, rooms, openings or members were read on a page that is not a plan.")
  add("NO_WINDOWS_ON_STRUCTURAL_SHEETS", structural, "A door or window was read on a structural sheet.")
  uncited = []
  for pdf, read in reads:
    for r in read:
      for c in r["candidates"]:
        if not _live(c):
          continue
        f = c.facts or {}
        
        for n in c.notes or []:
          if str(n.get("code") or "").startswith("HEIGHT_FROM") or n.get("code") == "NECK_HEIGHT_ASSUMED":
            if (n.get("ladder") or {}).get("kind") in (None, "NONE"):
              uncited.append(f"{pdf} p.{r['page_no']}")
        if f.get("foundation_item") in ("PLASTER_INSIDE", "PLASTER_OUTSIDE", "PAINT_INSIDE", "PAINT_OUTSIDE") and f.get("area_m2") is not None and not f.get("heights_from"):
          uncited.append(f"{pdf} p.{r['page_no']}")
  add("EVERY_HEIGHT_CITES_A_LEVEL", uncited, "A row that uses a storey height does not say which entry of the table of floor heights, which note of the plan or which rule it took it from.")
  add("EVERY_PLAN_PAGE_HAS_A_FLOOR_AND_A_SCALE", no_floor + no_scale, "A plan page with items has no floor, or its scale was not measured and 1:100 was used.")
  doubled, member_two, beam_two, floor_two, finish_two, silent = [], [], [], [], [], []
  for acc in accs:
    live = [c for c in acc.candidates if c.decision == "ACCEPTED"]
    _also, hidden = ST.twins(acc.candidates, acc.sheets)
    doubled += [f"{acc.drawings and next(iter(acc.drawings.values()))} p.{acc.sheets[c.sheet_id].page_no}" for c in live if c.category == "STAIR" and c.id in hidden]
    seen: dict = {}

    for c in live:
      if c.category in ("COLUMN", "FOOTING") and c.tag:
        seen.setdefault((c.category, c.tag, _cand_floor(acc, c)), set()).add(acc.sheets[c.sheet_id].page_no)
    member_two += [f"{next(iter(acc.drawings.values()))} p.{p}" for k, ps in seen.items() if len(ps) > 1 for p in ps]
    seen = {}
    for c in live:
      if c.category == "BEAM" and c.tag:
        seen.setdefault((c.tag, _cand_floor(acc, c)), set()).add(acc.sheets[c.sheet_id].page_no)
    beam_two += [f"{next(iter(acc.drawings.values()))} p.{p}" for k, ps in seen.items() if len(ps) > 1 for p in ps]
    exts = {s["sheet_id"]: SimpleNamespace(stats=s.get("stats") or {}) for rd in acc.read.values() for s in rd}
    owned = BOS.framing_floors(BOS.strips_by_level(list(acc.sheets.values()), exts), BOS.walls_by_level(list(acc.candidates), {k: v.page_no for k, v in acc.sheets.items()}))
    for level in owned:
      by_source: dict = {}
      for c in live:
        f = c.facts or {}
        if c.category == "BEAM" and f.get("level_hint") == level:
          kind = "WALLS" if f.get("derived_from") == "WALLS" and f.get("beam_role") == "ROOF" else "STRIPS" if f.get("from_strips") and BOS.roof_mark(c.tag) else None
          if kind:
            by_source.setdefault(kind, set()).add(acc.sheets[c.sheet_id].page_no)
      if len(by_source) == 2:
        beam_two += [f"{next(iter(acc.drawings.values()))} p.{p}" for ps in by_source.values() for p in ps]
    seen = {}
    for c in live:
      if c.category == "WALL" and not (c.facts or {}).get("foundation_item"):
        seen.setdefault(_cand_floor(acc, c) or "-", set()).add(acc.sheets[c.sheet_id].page_no)
    floor_two += [f"{next(iter(acc.drawings.values()))} p.{p}" for k, ps in seen.items() if len(ps) > 1 for p in ps]
    finish_two += _floor_finish_sources(acc)
    silent += _silent_decisions(acc)

  add("EACH_STAIR_FLIGHT_ONCE_IN_THE_BUILDING", doubled, "A stair flight and its twin on the floor above are both accepted.")
  add("NO_MEMBER_ON_TWO_SHEETS", member_two, "A column or footing mark of one floor is accepted from more than one sheet.")
  add("NO_BEAM_ON_TWO_SOURCES", beam_two, "A beam mark of one floor is accepted from more than one sheet, or a floor whose framing plan draws the roof beams has them accepted from the walls as well.")
  add("ONE_ARCHITECTURE_SOURCE_PER_FLOOR", floor_two, "Walls of one floor are accepted from more than one sheet.")
  add("NO_SILENT_DECISION", silent, "A billed row depends on a decision with no governing option, or a beam with several printed sections has no depth and does not list them.")
  add("ONE_FLOOR_FINISH_SOURCE", finish_two, "The floor finish of a storey is accepted from its rooms and from a total made of the rooms, or the finish area accepted for the storey is more than its gross area.")
  bad = [f"{r.get('work_item_code')}" for r in rows if not (float(r.get("quantity") or 0) > 0) or not math.isfinite(float(r.get("quantity") or 0)) or not r.get("unit")]
  add("LEDGER_ROWS_ARE_POSITIVE_AND_HAVE_A_UNIT", bad, "A ledger row has a zero, negative or missing quantity, or no unit.")
  stale, disagree = [], []
  for acc in accs:
    where = next(iter(acc.drawings.values()))
    reg_rows = []
    for c in acc.candidates:
      if c.decision == "REJECTED":
        continue
      tag = f"{where} p.{acc.sheets[c.sheet_id].page_no}"
      if c.category == "SLAB" and (c.facts or {}).get("label_parts") and c.label != SL.current(c):
        stale.append(tag)
      if RGS._spec(c) is None or (c.facts or {}).get("foundation_item"):
        continue
      issues, status = RGS._issues(c)
      if c.status != NS.status_of(c.notes) and c.status != "INVALID":
        disagree.append(tag)
      if status != ("INVALID" if c.status == "INVALID" else NS.status_of(issues)):
        disagree.append(tag)
      reg_rows += [{"ifc_type": RGS._spec(c)["ifc_type"], "normalization_status": status}] * RGS.rows_of(c)
    head = RGS.header_totals(reg_rows)
    if head["total"] != len(reg_rows) or sum(head["by_type"].values()) != len(reg_rows) or sum(head["by_status"].values()) != len(reg_rows) \
       or head["needs_review"] != sum(1 for r in reg_rows if r["normalization_status"] != "VALID"):
      disagree.append(where)
  add("SLAB_LABEL_PRINTS_THE_THICKNESS_MEASURED_WITH", stale, "A slab row's label prints a thickness other than the one it is measured with.")
  add("STATUS_AND_HEADER_TOTALS_AGREE_WITH_THEIR_ROWS", disagree, "A candidate's status is not what its notes give (a warning of ROW scope makes it a WARNING, an error INVALID, otherwise VALID), a register row's status is not what its issues give, or a header total is not the count of its rows.")
  return res

STAGE_NOTES = (("plinth level to lintel level", "PLINTH_TO_LINTEL"), ("lintel level to", "LINTEL_TO_SLAB"))
STAGE_FAMILIES = ("BRICK_WALLS", "WALL_PLASTER")

def stage_view(case: dict, ledger: list, floor_of: dict, catalog: dict) -> dict | None:
  rows: dict = {}
  for r in ledger:
    fam = family_of(r)
    if fam not in STAGE_FAMILIES:
      continue
    floor = floor_of.get(str(r.get("level_id"))) if r.get("level_id") else None
    rows.setdefault((fam, floor), []).append((r.get("work_stage"), float(r.get("quantity") or 0.0), r.get("unit") or ""))
    
  out = []
  for e in case.get("expected") or []:
    fam = e.get("family")
    parts = str(e["key"]).split("/")
    if fam not in STAGE_FAMILIES or len(parts) < 2 or e.get("qs") in (None, 0):
      continue
    
    note = str(e.get("note") or "").lower()
    stage = next((s for text, s in STAGE_NOTES if text in note), None)
    got = [x for x in rows.get((fam, parts[1]), []) if stage is None or x[0] == stage]
    unit = e.get("unit") or ""
    si = sum(q for _s, q, _u in got)
    si_unit = got[0][2] if got else ""
    ours = to_unit(si, si_unit, unit) if got else None
    diff = _pct(ours, e["qs"])
    out.append({"key": e["key"], "family": fam, "floor": parts[1], "stage": stage or "ALL", "unit": unit, "qs": e["qs"], "trace": None if ours is None else round(ours, 3),
      "diff_pct_qs": None if diff is None else round(diff, 3), "within_10": diff is not None and abs(diff) <= 10.0, "stages": sorted({str(x[0]) for x in got})})
  if not out:
    return None
  return {"lines": out, "within_10": sum(1 for l in out if l["within_10"]), "of": len(out)}

def mark_join_view(reads: list) -> dict | None:
  from app.modules.drawings_boq.takeoff.extract import mark_join as MJ
  rows = [r for _pdf, read in reads for r in read]
  layout: dict = {"FOOTING": {}, "COLUMN": {}}
  for r in rows:
    if (r.get("stats") or {}).get("read_as") == "DETAILS_ONLY":
      continue
    for c in r["candidates"]:
      f = c.facts or {}
      if c.category in layout and c.tag and _live(c) and not f.get("stair") and not f.get("neck_of") and not f.get("from_shapes") and not f.get("mark_from_size"):
        k = MJ.norm(c.tag)
        layout[c.category][k] = max(layout[c.category].get(k, 0), int(c.count or 0))
        
  views = {"FOOTING": [{**v, "page_no": r["page_no"]} for r in rows for v in ((r.get("meta") or {}).get("footing_views") or [])], "COLUMN": []}
  for r in rows:
    for d in ((r.get("meta") or {}).get("details") or []):
      if d.get("mark") and d.get("w_in") and d.get("h_in") and d.get("read") in ("TEXT", "TEXT_SQUARE", "OCR", "OCR_SQUARE"):
        views["COLUMN"].append({"mark": d["mark"], "size_mm": sorted([round(d["w_in"] * 25.4, 1), round(d["h_in"] * 25.4, 1)]), "page_no": r["page_no"]})
  out: dict = {}
  for kind in ("FOOTING", "COLUMN"):
    if not views[kind]:
      continue
    j = MJ.join(layout[kind], views[kind], kind)
    out[kind] = {"views": len(views[kind]), "marks_on_plans": len(layout[kind]), "sized": sorted(m for m, v in j["joined"].items() if v["size_mm"]), "issues": j["issues"]}
  return out or None

def members_view(accs: list) -> dict | None:
  from app.modules.drawings_boq.takeoff.model import members as MB
  from app.modules.drawings_boq.takeoff.extract import layout_groups as LG
  from app.modules.drawings_boq.takeoff.extract.ready import mark_skip
  plans = [{**r, "drawing_id": str(did)} for a in accs for did, rd in a.read.items() for r in rd if "title" in r and "stats" in r]
  found = MB.build(plans, None, mark_skip(LG.undecided_sheets(plans)))
  return found.summary() if found.members else None

def wall_faces_view(accs: list) -> dict | None:
  
  from app.modules.drawings_boq.takeoff.extract import finishes as FN, config as XC
  from app.modules.drawings_boq.takeoff.model import walls as MW
  rows = []
  for a in accs:
    for did, rd in a.read.items():
      for r in rd:
        cands = r.get("candidates") or []
        walls = FN.plaster_walls([c for c in cands if c.category == "WALL" and c.decision == "ACCEPTED"])
        rooms = FN.usable_rooms([c for c in cands if c.category == "ROOM" and c.decision == "ACCEPTED"])
        mm = r.get("mm_per_pt")
        if not walls or not rooms or not mm:
          continue
        g = MW.build(walls, rooms, mm, None, XC.WALL_GAP_CLEAR_MAX_MM)
        faces = FN.plaster_faces(walls, mm)
        sides = g.sides()
        rows.append({"page_no": r["page_no"], "floor": (r.get("title") or {}).get("level_hint"), "walls": len(walls), "rooms": len(rooms), "closed": g.closed, "open_rooms": sorted(g.open_rooms),
          "outline_in_m": round(sum(f["in"] * f["l"] for f in faces), 1), "outline_out_m": round(sum(f["out"] * f["l"] for f in faces), 1),
          "graph_in_m": round(sum(s[0] * f["l"] for s, f in zip(sides, faces)), 1), "graph_out_m": round(sum(s[1] * f["l"] for s, f in zip(sides, faces)), 1)})
  rows.sort(key=lambda x: (str(x["floor"]), x["page_no"]))
  return {"floors": rows, "closed": sum(1 for x in rows if x["closed"]), "of": len(rows)} if rows else None

def options_view(accs: list) -> dict:
  from app.modules.drawings_boq.takeoff.extract import revisions as RV
  sheets: list = []
  for a in accs:
    for did, rd in a.read.items():
      for r in rd:
        sheets.append({"sheet_id": (str(did), r["page_no"]), "page_no": r["page_no"], "title": r.get("title"), "stats": r.get("stats"), "identity": ((getattr(a.sheets.get(r.get("sheet_id")), "prep_meta", None) or {}).get("identity")),
          "candidates": r.get("candidates") or [], "drawing_id": str(did)})
  view = RV.build(sheets)
  ident = [s["identity"] or {} for s in sheets]
  return {"sheets": len(sheets), "print_an_option": sum(1 for i in ident if i.get("option")), "print_a_stamp": sum(1 for i in ident if i.get("stamps")), "to_decide": view["to_decide"], "tolerance": view["tolerance"],
    "groups": [{"kind": g["kind"], "caption": g["caption"], "floor": g["floor"], "sheet_no": g["sheet_no"], "state": g["state"], "default": g["default"],
      "options": [{"value": o["value"], "text": o["text"], "pages": o["pages"], "items": o["items"], "live": o["live"]} for o in g["options"]]} for g in view["groups"]]}

STEEL_STAGE_OF = {"FOUNDATION": "BASEMENT", "BASEMENT": "BASEMENT", "GROUND": "GROUND", "FIRST": "FIRST", "SECOND": "SECOND", "ROOF": "ROOF"}

def steel_view(case: dict, ledger: list, floor_of: dict, steel_stats: dict | None = None) -> dict | None:
  rows = [r for r in ledger if (r.get("work_item_code") or "") == "STL-REBAR"]
  qs_rows = [e for e in case.get("expected") or [] if e.get("family") == "STEEL" and e.get("qs") not in (None, 0)]
  if not rows and not qs_rows:
    return None
  
  by: dict = {}
  for r in rows:
    floor = floor_of.get(str(r.get("level_id"))) if r.get("level_id") else None
    slot = by.setdefault(floor or "NO_FLOOR", {"measured": 0.0, "estimated": 0.0, "members": 0})
    kg = float(r.get("quantity") or 0.0)
    slot["estimated" if "STEEL_ESTIMATED" in (r.get("warnings") or ()) else "measured"] += kg
    slot["members"] += 1
    
  qs: dict = {}
  for e in qs_rows:
    parts = str(e["key"]).split("/")
    stage = "ALL" if len(parts) < 2 or parts[1] == "ALL" else "OTHERS" if parts[1] == "OTHERS" else STEEL_STAGE_OF.get(parts[1], parts[1])
    qs[stage] = qs.get(stage, 0.0) + float(e["qs"])
    
  out = []
  for stage in [s for s in ("BASEMENT", "GROUND", "FIRST", "SECOND", "ROOF") if s in qs or s in by] + [s for s in ("OTHERS", "ALL") if s in qs]:
    mine = by.get(stage) or {"measured": 0.0, "estimated": 0.0, "members": 0}
    ours = mine["measured"] + mine["estimated"] if stage not in ("OTHERS", "ALL") else None
    diff = _pct(ours, qs.get(stage)) if (ours is not None and qs.get(stage)) else None
    out.append({"stage": stage, "qs": qs.get(stage), "trace": None if ours is None else round(ours, 1), "measured_kg": round(mine["measured"], 1), "estimated_kg": round(mine["estimated"], 1),
      "members": mine["members"], "diff_pct_qs": None if diff is None else round(diff, 1), "within_10": diff is not None and abs(diff) <= 10.0})
  total = sum(s["measured"] + s["estimated"] for s in by.values())
  total_qs = sum(qs.values())
  stats = steel_stats or {}
  return {"stages": out, "total_trace": round(total, 1), "total_qs": round(total_qs, 1) if qs else None, "total_diff_pct": None if not (qs and total) else round(_pct(total, total_qs), 1),
    "measured_kg": round(sum(s["measured"] for s in by.values()), 1), "estimated_kg": round(sum(s["estimated"] for s in by.values()), 1),
    "within_10": sum(1 for s in out if s["within_10"]), "of": sum(1 for s in out if s["diff_pct_qs"] is not None),
    "reason": stats.get("reason"), "outside_band": stats.get("outside_band") or {}}

def _decision_rows(accs: list) -> tuple:
  from app.modules.drawings_boq.takeoff.extract import conflicts as CF
  rows: list = []
  sheets: dict = {}
  for a in accs:
    for did, rd in a.read.items():
      for r in rd:
        sid = (str(did), r["page_no"])
        sheets[sid] = {"page_no": r["page_no"], "discipline": CF.sheet_discipline(r.get("title"))}
        for c in r.get("candidates") or []:
          rows.append(SimpleNamespace(id=str(getattr(c, "id", None) or f"{did}-{r['page_no']}-{getattr(c, 'key', None) or getattr(c, 'ckey', '')}"), decision=getattr(c, "decision", "NEW"), sheet_id=sid, category=c.category, facts=c.facts, params=c.params, tag=c.tag, count=c.count, label=c.label, notes=c.notes))
  return rows, sheets

def _silent_decisions(acc) -> list:
  from app.modules.drawings_boq.takeoff.extract import conflicts as CF
  rows, sheets = _decision_rows([acc])
  billed = {str(c.id) for c in acc.candidates if c.decision == "ACCEPTED"}
  where = next(iter(acc.drawings.values()))
  page_of = {str(c.id): f"{where} p.{acc.sheets[c.sheet_id].page_no}" for c in acc.candidates}
  bad = [page_of[i] for c in CF.build(rows, sheets, [], None)["conflicts"] if c["governing_index"] is None for i in c["item_ids"] if i in billed and i in page_of]
  for c in acc.candidates:
    if c.category != "BEAM" or c.decision == "REJECTED":
      continue
    f = c.facts or {}
    
    if len([o for o in f.get("section_options") or [] if o.get("depth_mm")]) >= 2 and not (c.params or {}).get("depth_mm") and not any(n.get("code") == "BEAM_SECTIONS_LISTED" for n in c.notes or []):
      bad.append(page_of[str(c.id)])
  return bad

def decisions_view(accs: list) -> dict:
  from app.modules.drawings_boq.takeoff.extract import conflicts as CF
  rows, sheets = _decision_rows(accs)
  view = CF.build(rows, sheets, [], None)
  return {"per_row_conflicts": len(view["conflicts"]), "facts": len(view["facts"]), "open": view["open_decisions"], "tolerances": view["tolerances"],
    "decisions": [{"kind": d["kind"], "id": d["id"], "facts": d["facts"], "rows": d["rows"], "default": d["default"], "options": [{"value": o["value"], "label": o["label"], "trust": o["trust"], "quantity": o["quantity"], "unit": o["unit"],
      "sources": [f"{s['discipline'].lower()} p{s['page_no'] if s['page_no'] is not None else '-'} {s['basis']}" for s in o["sources"]]} for o in d["options"]]} for d in view["decisions"]]}

def safe_view(expected: list, ledger: list, floor_of: dict, catalog: dict, accs: list) -> dict:
  """Safe precision and safe coverage over the ledger rows (the rows that make the bill). A row is SAFE when the candidate its measurement came from is (extract.safe). Coverage: the share of ledger rows that are SAFE.
  Precision: of the SAFE rows that can be judged, the share within tolerance of the drawing column. A row can be judged when the ledger line it belongs to (work item, family, floor) is covered by an expected line with
  a drawing figure; it takes the verdict of that line (all the expected lines covering it must be within tolerance). This is a line-level test: a wrong row inside a right line is not caught. Rows that cannot be judged are
  counted apart."""
  lines = trace_lines(ledger, floor_of, catalog)
  verdict: dict = {}
  verdict_qs: dict = {}
  for e in expected:
    got = resolve(e, lines)
    conv = [to_unit(l["si"], l["unit"], e["unit"]) for l in got]
    if not got or any(c is None for c in conv):
      continue
    fam = e.get("family")
    tol = e["tolerance_pct"] if e.get("tolerance_pct") is not None else (T.default_for(fam) if fam else T.DEFAULT_TOLERANCE_PCT)
    for column, book, name in ((e.get("drawing"), verdict, "drawing"), (e.get("qs"), verdict_qs, "qs")):
      if column is None:
        continue
      ok = _status(sum(conv), column, tol) == MATCH
      for l in got:
        book.setdefault(l["key"], []).append(ok)
        
  info: dict = {}
  cand_of: dict = {}
  for acc in accs:
    for read in acc.read.values():
      info.update(SF.assess(read, _live))
    cand_of.update({str(c.measurement_id): str(c.id) for c in acc.candidates if c.measurement_id})
  out = {"rows": 0, "safe_rows": 0, "review_rows": 0, "judged_safe": 0, "judged_safe_within": 0, "judged_review": 0, "judged_review_within": 0, "unjudged_safe": 0, "unjudged_review": 0, "qs_judged_safe": 0, "qs_judged_safe_within": 0, "by_basis": {}}
  for r in ledger:
    mid = ((r.get("trace") or {}).get("inputs") or {}).get("measurement_id")
    got = info.get(cand_of.get(str(mid)))
    if got is None:
      continue
    safe = got["status"] == SF.SAFE
    fam = family_of(r)
    floor = floor_of.get(str(r.get("level_id"))) if r.get("level_id") else None
    cell = f"{r.get('work_item_code') or '?'}/{fam or '-'}/{floor or '-'}"
    v = verdict.get(cell)
    q = verdict_qs.get(cell)
    if safe and q:
      out["qs_judged_safe"] += 1
      out["qs_judged_safe_within"] += 1 if all(q) else 0
    out["rows"] += 1
    out["safe_rows" if safe else "review_rows"] += 1
    if safe:
      out["by_basis"][got["basis"]] = out["by_basis"].get(got["basis"], 0) + 1
    if not v:
      out["unjudged_safe" if safe else "unjudged_review"] += 1
      continue
    out["judged_safe" if safe else "judged_review"] += 1
    if all(v):
      out["judged_safe_within" if safe else "judged_review_within"] += 1
      
  pct = lambda a, b: round(100.0 * a / b, 1) if b else None
  out["safe_coverage_pct"] = pct(out["safe_rows"], out["rows"])
  out["safe_precision_pct"] = pct(out["judged_safe_within"], out["judged_safe"])
  out["review_precision_pct"] = pct(out["judged_review_within"], out["judged_review"])
  out["safe_precision_vs_qs_pct"] = pct(out["qs_judged_safe_within"], out["qs_judged_safe"])
  return out

def register_view(accs: list) -> dict:
  rows = own = every = unaccepted = 0
  for acc in accs:
    for c in acc.candidates:
      if c.decision == "REJECTED" or RGS._spec(c) is None or (c.facts or {}).get("foundation_item"):
        continue
      issues, status = RGS._issues(c)
      n = RGS.rows_of(c)
      rows += n
      own += n if status == "WARNING" else 0
      every += n if status != "INVALID" and any(i["severity"] == "warning" for i in issues) else 0
      unaccepted += n if c.status != "INVALID" and (NS.status_of(c.notes) == "WARNING" or c.missing) else 0
  pct = lambda k: round(100.0 * k / rows, 1) if rows else 0.0
  return {"rows": rows, "warning_rows": own, "share_pct": pct(own), "warning_rows_if_every_note_counted": every, "share_pct_if_every_note_counted": pct(every),
    "warning_rows_before_accepting": unaccepted, "share_pct_before_accepting": pct(unaccepted)}

def warnings_view(ledger: list, accs: list | None = None) -> dict:

  carried = ("SLAB_THICKNESS_DISAGREES", "BEAM_SECTIONS_LISTED")
  by: dict = {}
  hit = own = 0
  for r in ledger:
    codes = [str(c) for c in (r.get("warnings") or [])]
    hit += 1 if codes else 0
    own += 1 if any(c not in carried for c in codes) else 0
    for c in set(codes):
      by[c] = by.get(c, 0) + 1
  n = len(ledger)
  out = {"rows": n, "with_warnings": hit,"share_pct": round(100.0 * hit / n, 1) if n else 0.0, "without_conflict_codes": own, "share_pct_without_conflict_codes": round(100.0 * own / n, 1) if n else 0.0,
    "by_code": sorted(by.items(), key=lambda kv: (-kv[1], kv[0]))[:14]}
  if accs:
    out["register"] = register_view(accs)
  return out

def engine_digest(ledger: list, floor_of: dict) -> str:
  """The hash of the engine's output: the ledger rows as (work item, floor, unit, quantity, label), sorted. It does not depend on how the score reads them."""
  items = sorted([r.get("work_item_code") or "?", str(floor_of.get(str(r.get("level_id"))) if r.get("level_id") else ""), r.get("unit") or "", str(round(float(r.get("quantity") or 0), 6)),
    str(((r.get("trace") or {}).get("label")) or "")] for r in ledger)
  return hashlib.sha256(json.dumps(items, sort_keys=True, default=str).encode()).hexdigest()

MOVE_PCT = 1.0

def quantities_view(ledger: list, floor_of: dict) -> dict:
  """What the engine measured, summed per work item, floor and unit: {"CODE|FLOOR|unit": total}. Not part of the hash; the robustness run compares it."""
  out: dict = {}
  for r in ledger:
    k = f"{r.get('work_item_code') or '?'}|{floor_of.get(str(r.get('level_id'))) if r.get('level_id') else ''}|{r.get('unit') or ''}"
    out[k] = round(out.get(k, 0.0) + float(r.get("quantity") or 0.0), 6)
  return dict(sorted(out.items()))

def _moves(clean: dict, now: dict) -> list:
  out = []
  for k in sorted(set(clean) | set(now)):
    a, b = clean.get(k), now.get(k)
    if (a or 0.0) < 1e-6 and (b or 0.0) < 1e-6:
      continue
    if a is None or a < 1e-6:
      pct = 100.0
    elif b is None:
      pct = 100.0
    else:
      pct = abs(b - a) / abs(a) * 100.0
    out.append({"key": k, "clean": a, "now": b, "pct": round(pct, 2)})
  return sorted(out, key=lambda m: (-m["pct"], m["key"]))

def robust_run(case: dict, files: dict, profile, rule_set, catalog, clean: dict, *, ready_only: bool, page_budget: float, rules, keep: dict) -> dict:
  import tempfile
  from app.modules.drawings_boq.takeoff.proof import perturb as PB, robustness as RBS
  variants = (("rescale 0.5", lambda b: PB.rescale(b, 0.5)), ("rescale 2.0", lambda b: PB.rescale(b, 2.0)), ("rotate view 90", lambda b: PB.rotate_view(b, 90)))
  base_reads = {n: rows for n, rows in keep.get("reads") or []}
  out: dict = {}
  for vname, fn in variants:
    with tempfile.TemporaryDirectory() as tmp:
      moved_files = {}
      for name in case["pdfs"]:
        with open(files[name], "rb") as fh:
          data = fh.read()
        path = os.path.join(tmp, name)
        with open(path, "wb") as fh:
          fh.write(fn(data))
        moved_files[name] = path
        
      k2: dict = {}
      try:
        doc2, _t = run_case(case, moved_files, profile, rule_set, catalog, ready_only=ready_only, page_budget=page_budget, both=False, rules=rules, keep=k2)
      except Exception as exc:
        out[vname] = {"error": f"{type(exc).__name__}: {str(exc)[:160]}"}
        continue
    moves = _moves(clean.get("quantities") or {}, doc2.get("quantities") or {})
    over = [m for m in moves if m["pct"] > MOVE_PCT]
    new_reads = {n: rows for n, rows in k2.get("reads") or []}
    
    pages = {}
    for n, rows in base_reads.items():
      s = RBS.score(rows, new_reads.get(n) or [])
      pages[n] = {"pages": s["pages"], "changed": s["pages_changed"], "unread": s["pages_unread"], "families": {f: v["recall"] for f, v in s["families"].items() if v["recall"] is not None and v["recall"] < 1.0}}
    out[vname] = {"worst_pct": moves[0]["pct"] if moves else 0.0, "worst_key": moves[0]["key"] if moves else None, "quantities": len(moves), "moved": len(over), "top": over[:20], "reads": pages,
      "lines_within_10": doc2["summary"]["within_10"], "problems": len(doc2.get("problems") or []),
      "invariants_failing": {i["name"]: i["count"] for i in doc2.get("invariants") or [] if i["status"] == "FAIL"}, "pages_held_for_scale": len(doc2.get("scale_held") or []),
      "pages_voted": len((doc2.get("page_votes") or {}).get("pages") or [])}
  worst = max((v.get("worst_pct", 0.0) for v in out.values()), default=0.0)
  return {"move_pct": MOVE_PCT, "worst_pct": worst, "variants": out}

def run_case(case: dict, files: dict, profile, rule_set, catalog, *, ready_only: bool = False, page_budget: float = BM.PAGE_BUDGET_S, reader=None, both: bool = True, rules: dict | None = None, keep: dict | None = None) -> tuple:
  t0 = time.monotonic()
  reads, problems, timings = [], [], {}
  whole = None
  if reader is None:
    t = time.monotonic()
    blobs = []
    for name in case["pdfs"]:
      with open(files[name], "rb") as fh:
        blobs.append((name, fh.read()))
    whole = {n: (r, pr) for n, r, pr in BM.read_set(blobs, budget_s=page_budget)}
    timings["read the set"] = round(time.monotonic() - t, 1)
  for name in case["pdfs"]:
    t = time.monotonic()
    if whole is not None:
      rows, probs = whole[name]
    else:
      with open(files[name], "rb") as fh:
        rows, probs = reader(fh.read(), page_budget)

    problems += [{"pdf": name, "page": p, "message": m} for p, m in probs]

    for r in rows:
      for stop in [(r.get("stats") or {}).get("wall_stop"), (r.get("stats") or {}).get("plan_regions_stop")]:
        if not stop:
          continue
        how = "the work budget" if stop.get("by") == "WORK_BUDGET" else "the safety clock, so another machine may read it differently"
        problems.append({"pdf": name, "page": r["page_no"], "message": f"the wall reading of the page was stopped by {how} after {stop.get('work')} primitives"})
    reads.append((name, rows))
    timings[f"read {name}"] = round(time.monotonic() - t, 1)

  if keep is not None:
    keep["reads"] = reads
  steel_by_policy: dict = {}

  decision_log: dict = {}

  def engine(policy_ready: bool, decisions: dict | None = None, record: bool = True) -> tuple:
    errors, tallies = [], []
    if record:
      steel_by_policy[policy_ready] = []
    names = [name for name, _rows in reads]
    acc = OA.accept_case(case["name"], reads, profile, ready_only=policy_ready, decisions=decisions)
    if decisions:
      decision_log.update(acc.decision_log)
    tallies.append(acc.tally)
    inputs = OA.build_inputs(acc)
    res = OR.run_engine(inputs, profile, rule_set, acc.printed_all, case=case["name"])
    
    if record:
      steel_by_policy[policy_ready].append(((res.stats or {}).get("derived") or {}).get("steel") or {})
    for e in res.errors:
      errors.append({"pdf": ", ".join(names), **(e if isinstance(e, dict) else {"message": str(e)})})
    ledger = [{**{k: v for k, v in r.items() if k != "_entry"}, "quantity": float(r["quantity"])} for r in res.rows]
    if not policy_ready and record:
      for p in acc.problems:
        problems.append({"pdf": p.get("pdf"), "page": p.get("page"), "message": f"{p.get('code')}: {p.get('message')}"})
    accs = OA.split_by_drawing(acc)
    return accs, ledger, errors, tallies, score_ledger(case["expected"], ledger, accs, catalog)

  t = time.monotonic()
  main_ready = ready_only
  accs, ledger, errors, tallies, lines = engine(main_ready)
  if keep is not None:
    keep["ledger"], keep["accs"] = ledger, accs
  timings["accept and run"] = round(time.monotonic() - t, 1)
  other = None
  if both:
    t = time.monotonic()
    _a, _l, _e, _t, other_lines = engine(not main_ready)
    other = summarise(other_lines)
    timings["accept and run (other policy)"] = round(time.monotonic() - t, 1)

  decisions = {d["id"]: d["value"] for d in case.get("decisions") or []}
  if decisions:
    t = time.monotonic()
    accs_d, ledger_d, errors_d, _t, lines_d = engine(main_ready, decisions, False)
    errors += [{"level": "decided", **e} for e in errors_d]
    timings["accept and run (decided)"] = round(time.monotonic() - t, 1)
  else:
    accs_d, ledger_d, lines_d = accs, ledger, lines
  expected_r, applied, pending, correction_problems = LV.corrected_expected(case["expected"], case.get("corrections") or [])
  lines_r = score_ledger(expected_r, ledger_d, accs_d, catalog) if applied else lines_d
  levels = LV.build(lines, lines_d, lines_r, decisions=case.get("decisions") or [], decision_log=decision_log, corrections=case.get("corrections") or [], applied=applied, pending=pending,
    correction_problems=correction_problems, ledger=ledger_d, residuals=case.get("residuals") or [])

  facts = check_facts([r for _n, rows in reads for r in rows], case["facts"])
  doc = {"case": case["name"], "tier": case["tier"], "status": "SCORED", "policy": "ready_only" if main_ready else "accept_all", "lines": lines, "facts": facts,
    "facts_tally": {s: sum(1 for f in facts if f["status"] == s) for s in sorted({f["status"] for f in facts})},
    "invariants": invariants(reads, accs, ledger), "page_votes": page_votes(reads), "scale_held": scale_held(reads), "height_sources": height_sources(reads), "summary": summarise(lines),
    "other_policy": {"policy": "accept_all" if main_ready else "ready_only", "summary": other} if other is not None else None,
    "accept": [{k: t.get(k) for k in ("candidates", "ready_would_accept", "all_would_accept", "accepted", "accept_refused", "confirmed", "confirm_refused")} for t in tallies],
    "engine_errors": errors, "problems": sorted(problems, key=lambda p: (str(p.get("pdf")), p.get("page") or 0, str(p.get("message")))),
    "ledger_rows": len(ledger), "files": {n: case["sha256"].get(n) for n in case["pdfs"]}}
  
  if rules:
    doc["rules"] = rules
  doc["levels"] = levels
  floor_all = {str(k): v for a in accs for k, v in a.floor_of.items()}
  doc["engine_digest"] = engine_digest(ledger, floor_all)
  doc["safe"] = safe_view(case["expected"], ledger, floor_all, catalog, accs)
  steel_runs = steel_by_policy.get(main_ready) or []
  steel_stats = {"reason": next((s.get("reason") for s in steel_runs if s.get("reason")), None) if not any(s.get("ran") for s in steel_runs) else None,
    "outside_band": {fam: {"members": sum(((s.get("outside_band") or {}).get(fam) or {}).get("members", 0) for s in steel_runs)} for fam in sorted({f for s in steel_runs for f in (s.get("outside_band") or {})})}}
  steel = steel_view(case, ledger, floor_all, steel_stats)
  
  if steel:
    doc["steel"] = steel
  view = stage_view(case, ledger, floor_all, catalog)
  if view:
    doc["stage_view"] = view
  mem = members_view(accs)
  if mem:
    doc["members"] = mem
  mj = mark_join_view(reads)
  if mj:
    doc["mark_join"] = mj
  wf = wall_faces_view(accs)
  if wf:
     doc["wall_faces"] = wf
  doc["warnings"] = warnings_view(ledger, accs)
  doc["reading_work"] = work_view(reads)
  doc["fact_decisions"] = decisions_view(accs)
  doc["options"] = options_view(accs)
  doc["quantities"] = quantities_view(ledger, floor_all)
  doc["hash"] = digest(doc)
  doc["marks"] = _mark_lines(reads)
  timings["total"] = round(time.monotonic() - t0, 1)
  return doc, timings

def score_ledger(expected: list, ledger: list, accs: list, catalog: dict) -> list:
  floor_of: dict = {}
  for a in accs:
    floor_of.update({str(k): v for k, v in a.floor_of.items()})
  lines = trace_lines(ledger, floor_of, catalog, derive={e.get("family") for e in expected if e.get("family")})
  sc, extra = score_lines(expected, lines)
  return sc + extra_lines(extra)

def work_view(reads: list) -> dict:
  from app.modules.drawings_boq.takeoff.extract import config as XC
  used = [(r.get("stats", {}).get("wall_work") or 0, name, r["page_no"]) for name, rows in reads for r in rows]
  stops = [(name, r["page_no"], st) for name, rows in reads for r in rows for st in [(r.get("stats") or {}).get("wall_stop"), (r.get("stats") or {}).get("plan_regions_stop")] if st]
  top = max(used, default=(0, None, None))
  budget = XC.PAGE_WORK_BUDGET
  return {"budget": budget, "pages": len(used), "most_used": top[0], "most_used_at": f"{top[1]} p.{top[2]}" if top[1] else None,
    "over_half": sum(1 for u in used if budget and u[0] > budget / 2),
    "stopped_by_work": [f"{n} p.{p}" for n, p, st in stops if st.get("by") == "WORK_BUDGET"], "stopped_by_clock": [f"{n} p.{p}" for n, p, st in stops if st.get("by") != "WORK_BUDGET"]}

def dump_view(keep: dict) -> tuple:
  cands = []
  for acc in keep.get("accs") or []:
    for c in acc.candidates:
      sheet = acc.sheets[c.sheet_id]
      cands.append({"pdf": acc.drawings.get(sheet.drawing_id), "page": sheet.page_no, "ckey": c.ckey, "category": c.category, "kind": c.kind, "label": c.label, "tag": c.tag,
        "quantity_mode": c.quantity_mode, "status": c.status, "decision": c.decision, "count": c.count, "missing": list(c.missing or []), "params": c.params, "facts": c.facts,
        "notes": [n.get("code") for n in (c.notes or [])], "work_item": c.suggested_work_item, "confidence": float(c.confidence) if c.confidence is not None else None})
  return list(keep.get("ledger") or []), sorted(cands, key=lambda d: (str(d["pdf"]), d["page"] or 0, str(d["category"]), str(d["ckey"])))

def _mark_lines(reads: list) -> list:
  from types import SimpleNamespace
  from app.modules.drawings_boq.takeoff.prep import mark_vocab as MV
  sheets = [(name, SimpleNamespace(page_no=r["page_no"], prep_meta=r.get("meta") or {})) for name, rows in reads for r in rows]
  return MV.lines_for(MV.build(sheets))

def _fmt(v, nd=1):
  return "" if v is None else f"{v:,.{nd}f}"

def _worse(before: dict, now: dict) -> list:
  old = {l["key"]: l for l in before.get("lines", [])}
  out = []

  for l in now["lines"]:
    o = old.get(l["key"])
    if o is None:
      continue
    def err(x):
      e = x["diff_pct_drawing"] if x["diff_pct_drawing"] is not None else x["diff_pct_qs"]
      return None if e is None else abs(e)
    a, b = err(o), err(l)
    if STATUS_RANK[l["status"]] > STATUS_RANK[o["status"]] or (a is not None and b is not None and b > a + 0.5):
      out.append((l["key"], o, l))
  return out

def render_md(doc: dict, baseline: dict | None = None, timings: dict | None = None) -> str:
  s = doc["summary"]
  out = [f"# Score: {doc['case']} (tier {doc['tier']})", "", f"Hash `{doc['hash']}`. Policy: {doc['policy']}. {s['lines']} lines with a Trace and a QS number; {s['within_10']} within 10% and {s['within_5']} within 5% of the QS; "
    f"{s['against_drawing']} with a drawing figure, {s['within_10_drawing']} within 10% and {s['within_5_drawing']} within 5% of it.", ""]
  if doc.get("rules"):
    r = doc["rules"]
    out += [f"**Run under the rules of the case:** {r['file']}, {r['count']} rules ({', '.join(r['keys'])}). {r['note']}", ""]
  if doc.get("engine_digest"):
    out += [f"Engine output `{doc['engine_digest'][:16]}`: the hash of the ledger rows themselves. A change to how the score reads the ledger changes the hash above and not this one.", ""]
  if doc.get("members"):
    mm = doc["members"]
    out += ["**Members** (not part of the hash): " + "; ".join(f"{k.lower()}s {v['members']} ({v['sightings']} sightings, {v['on_several_sheets']} seen on more than one sheet)" for k, v in mm["by_kind"].items())
      + f". Marks on several floors: {len(mm['marks_on_several_floors'])}, with different counts: {mm['marks_with_different_counts']}. Sheets not laid over their base plan: {len(mm['unregistered_sheets'])}. Decisions: {mm['decisions']}.", ""]
  if doc.get("mark_join"):
    for kind, mj in doc["mark_join"].items():
      out += [f"**Mark join, {kind.lower()}s** (not part of the hash): {mj['views']} detail views, {mj['marks_on_plans']} marks on the plans, {len(mj['sized'])} marks with a size from a view ({', '.join(mj['sized']) or 'none'}); "
        + (f"{len(mj['issues'])} issues: " + "; ".join(f"{i['code']} {i['mark']}" for i in mj["issues"]) if mj["issues"] else "no issues") + ".", ""]
  if doc.get("warnings"):
    wv = doc["warnings"]
    out += [f"**Rows with a warning** (not part of the hash): {wv['with_warnings']} of {wv['rows']} ledger rows ({wv['share_pct']}%); {wv['without_conflict_codes']} ({wv['share_pct_without_conflict_codes']}%) when the two warnings that a decision now carries are left out. Most often: " + ", ".join(f"{c} {n}" for c, n in wv["by_code"][:8]) + ".", ""]
    if wv.get("register"):
      rv = wv["register"]
      out += [f"**Register rows with a warning** (not part of the hash): {rv['warning_rows']} of {rv['rows']} ({rv['share_pct']}%) by the row-scope rule; {rv['warning_rows_if_every_note_counted']} ({rv['share_pct_if_every_note_counted']}%) if every warning note counted, as before the scopes; {rv['warning_rows_before_accepting']} ({rv['share_pct_before_accepting']}%) as the register lists them before anything is accepted (a value still missing is a row warning).", ""]
  if doc.get("reading_work") and doc["reading_work"].get("pages"):
    rw = doc["reading_work"]
    out += [f"**Reading work** (not part of the hash): the wall reading of the busiest page used {rw['most_used']:,} of the {('{:,}'.format(rw['budget']) if rw['budget'] else 'unlimited')} primitives it may ({rw['most_used_at']}); {rw['over_half']} page(s) used more than half. "
      f"Stopped by the work budget: {', '.join(rw['stopped_by_work']) or 'none'}. Stopped by the safety clock (such a page can read differently on another machine): {', '.join(rw['stopped_by_clock']) or 'none'}.", ""]
  if doc.get("safe") and doc["safe"]["rows"]:
    sf = doc["safe"]
    out += [f"**Safe to accept**: {sf['safe_rows']} of {sf['rows']} ledger rows are SAFE (coverage {sf['safe_coverage_pct']}%); of the {sf['judged_safe']} SAFE rows that a drawing figure can judge, {sf['judged_safe_within']} are within tolerance (precision {sf['safe_precision_pct']}%; against the QS column {sf['safe_precision_vs_qs_pct']}% of {sf['qs_judged_safe']}); "
      f"for REVIEW rows the figure is {sf['review_precision_pct']}% of {sf['judged_review']}. Not judged: {sf['unjudged_safe']} SAFE, {sf['unjudged_review']} REVIEW. By basis: {sf['by_basis']}.", ""]
  if doc.get("steel"):
    sv = doc["steel"]
    out += [f"**Steel by stage** (not part of the hash): {sv['total_trace']:,} kg, {sv['measured_kg']:,} from printed bars and {sv['estimated_kg']:,} from the usual band" + (f"; the QS has {sv['total_qs']:,}" + (f" ({sv['total_diff_pct']:+.1f}%)" if sv.get("total_diff_pct") is not None else "") if sv.get("total_qs") else "") + (f"; the steel stage did not run: {sv['reason']}" if sv.get("reason") else "") + ".", ""]
    out += ["| Stage | QS | Trace | Bars | Band | Difference |", "|---|---|---|---|---|---|"]
    for s in sv["stages"]:
      out += [f"| {s['stage']} | {s['qs'] if s['qs'] is not None else ''} | {s['trace'] if s['trace'] is not None else ''} | {s['measured_kg']} | {s['estimated_kg']} | {'' if s['diff_pct_qs'] is None else format(s['diff_pct_qs'], '+.1f') + '%'} |"]
    if sv.get("outside_band"):
      out += ["", "Members whose own bars give a steel intensity outside the usual band (STEEL_OUTSIDE_BAND): " + ", ".join(f"{k} {v['members']}" for k, v in sv["outside_band"].items()) + "."]
    out += [""]
  if doc.get("robust"):
    rb = doc["robust"]
    out += [f"**Robustness** (not part of the hash; more than {rb['move_pct']:g}% is a move): worst move {rb['worst_pct']:g}%."]
    for vn, v in rb["variants"].items():
      if "error" in v:
        out += [f"- {vn}: failed, {v['error']}"]
        continue
      out += [f"- {vn}: worst {v['worst_pct']:g}% ({v['worst_key']}); {v['moved']} of {v['quantities']} quantities move by more than {rb['move_pct']:g}%; {v['lines_within_10']} lines within 10% of the QS."]
    out += [""]
  if doc.get("options"):
    ov = doc["options"]
    out += [f"**Options and revisions** (not part of the hash): {len(ov['groups'])} groups, {ov['to_decide']} open; {ov['print_an_option']} of {ov['sheets']} sheets print an option label, {ov['print_a_stamp']} print a revision stamp."]
    for g in ov["groups"]:
      out += [f"- {g['kind']} · {g['caption']}{' · sheet ' + g['sheet_no'] if g['sheet_no'] else ''} · {g['state']} · default {g['default'] or 'none'}: " + " | ".join(f"{o['value']} on page {', '.join(str(x) for x in o['pages'])} ({o['live']} items measured)" for o in g["options"])]
    out += [""]
  if doc.get("fact_decisions"):
    fd = doc["fact_decisions"]
    out += [f"**Open decisions** (not part of the hash): {fd['open']} of {len(fd['decisions'])} decisions; they replace {fd['per_row_conflicts']} per-row conflicts; {fd['facts']} facts. Tolerance per kind: " + "; ".join(f"{k} {t['tolerance']:g} {t['unit']}" for k, t in fd["tolerances"].items()) + ".", ""]
    for d in fd["decisions"]:
      out += [f"- {d['kind']} ({', '.join(d['facts'][:3])}{' and %d more' % (len(d['facts']) - 3) if len(d['facts']) > 3 else ''}; {d['rows']} rows; default {d['default'] or 'none, tied'}): " + " | ".join(f"{o['label']} [{o['trust']}] {o['quantity']} {o['unit']} from {', '.join(o['sources'])}" for o in d["options"])]
    if fd["decisions"]:
      out += [""]
  if doc.get("wall_faces"):
    wf = doc["wall_faces"]
    out += [f"**Wall faces** ({wf['closed']} of {wf['of']} plan sheets have walls that close; not part of the hash)", "", "| Page | Floor | Walls | Rooms | Closed | Rooms in the open | Inside, outline (m) | Inside, graph (m) | Outside, outline (m) | Outside, graph (m) |", "|---|---|---|---|---|---|---|---|---|---|"]
    out += [f"| {x['page_no']} | {x['floor']} | {x['walls']} | {x['rooms']} | {'yes' if x['closed'] else 'no'} | {', '.join(x['open_rooms'])} | {x['outline_in_m']} | {x['graph_in_m']} | {x['outline_out_m']} | {x['graph_out_m']} |" for x in wf["floors"]]
    out += [""]
  if doc.get("stage_view"):
    v = doc["stage_view"]
    out += [f"**Brick and plaster by stage** ({v['within_10']} of {v['of']} within 10% of the QS; not part of the hash)", "", "| Line | Floor | Stage | Unit | QS | Trace | Diff % | Stages found |", "|---|---|---|---|---|---|---|---|"]
    out += [f"| {l['key']} | {l['floor']} | {l['stage']} | {l['unit']} | {_fmt(l['qs'])} | {_fmt(l['trace'])} | {_fmt(l['diff_pct_qs'])} | {', '.join(l['stages'])} |" for l in v["lines"]]
    out += [""]
  if doc.get("other_policy") and doc["other_policy"]["summary"]:
    o = doc["other_policy"]["summary"]
    out += [f"Other policy ({doc['other_policy']['policy']}): {o['lines']} lines, {o['within_10']} within 10%, {o['within_5']} within 5% of the QS.", ""]
  if doc.get("levels"):
    out += LV.render(doc["levels"])
  cols = "| Line | Unit | Trace | QS | Drawing | Diff % QS | Diff % drawing | Status | Class |" + (" Before | Before status |" if baseline else "")

  out += [cols, "|" + "---|" * (cols.count("|") - 1)]
  old = {l["key"]: l for l in (baseline or {}).get("lines", [])}
  for l in doc["lines"]:
    row = f"| {l['key']} | {l['unit']} | {_fmt(l['trace'])} | {_fmt(l['qs'])} | {_fmt(l['drawing'])} | {_fmt(l['diff_pct_qs'])} | {_fmt(l['diff_pct_drawing'])} | {l['status']} | {l['class']} |"
    if baseline:
      o = old.get(l["key"])
      row += f" {_fmt(o['trace']) if o else ''} | {o['status'] if o else ''} |"
    out.append(row)

  if baseline:
    worse = _worse(baseline, doc)
    out += ["", f"Lines that got worse than the baseline: {len(worse)}."] + [f"- {k}: {_fmt(o['trace'])} -> {_fmt(n['trace'])} ({o['status']} -> {n['status']})" for k, o, n in worse]
  if doc.get("scale_held"):
    out += ["", f"## Plan pages held for want of a scale ({len(doc['scale_held'])}; every item says SCALE_UNVERIFIED)", ""] + [f"- {t}" for t in doc["scale_held"]]
  hs = doc.get("height_sources") or []
  if hs:
    out += ["", "## Where the heights came from", ""] + [f"- {h['kind']} {h['what']} {h['floor'] or ''}{' (' + str(h['basis']) + ')' if h['basis'] else ''}: {h['mm']} mm, {h['rows']} rows" for h in hs]
  pv = doc.get("page_votes") or {}
  if pv.get("pages"):
    out += ["", f"## Page roles voted ({len(pv['pages'])} pages; {pv.get('held', 0)} held of {pv.get('plan_pages', 0)} plan pages)", ""]
    out += [f"- {p['pdf']} p.{p['page']}: {p['role'] or 'HELD'} ({p['why'] or 'read as ' + str(p['read_as'])}); " + "; ".join(p["signals"]) for p in pv["pages"]]
  out += ["", "## Invariants", ""] + [f"- {i['status']} {i['name']}" + (f": {i['count']} ({', '.join(i['pages'][:6])})" if i["status"] == "FAIL" else "") for i in doc["invariants"]]
  if doc.get("marks"):
    out += ["", "## Mark vocabulary", ""] + [f"- {m}" for m in doc["marks"]]
  if doc["facts"]:
    out += ["", "## Facts", "", f"{doc['facts_tally']}"] + [f"- {f['status']}: {f['text']}. {f['message']}" for f in doc["facts"] if f["status"] != "PASS"][:30]
  if doc["engine_errors"]:
    out += ["", "## Engine errors", ""] + [f"- {e}" for e in doc["engine_errors"]]
  if doc["problems"]:
    out += ["", "## Problems", ""] + [f"- {p['pdf']} p.{p['page']}: {p['message']}" for p in doc["problems"][:30]]
  if timings:
    out += ["", "Timings (not in the hash): " + ", ".join(f"{k} {v} s" for k, v in timings.items())]
  return "\n".join(out) + "\n"

def load_baseline(path: str | None, case: str) -> dict | None:
  if not path or not os.path.isfile(path):
    return None
  with open(path, encoding="utf-8") as fh:
    doc = json.load(fh)
  return (doc.get("cases") or {}).get(case) if "cases" in doc else (doc if doc.get("case") == case else None)

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Read, accept and run every case offline and score it against the QS and the drawing.")
  ap.add_argument("cases", nargs="*", help="case names (default: every case folder)")
  ap.add_argument("--out", default="score_out")
  ap.add_argument("--ready-only", action="store_true", help="accept only what the Approve screen accepts by default (the other policy is still reported)")
  ap.add_argument("--baseline", help="a score.json (or the all.json of an earlier run) to compare with")
  ap.add_argument("--cases-dir", help=f"the folder with the PDFs (default: {CIO.CASES_DIR_ENV})")
  ap.add_argument("--page-budget", type=float, default=BM.PAGE_BUDGET_S)
  ap.add_argument("--no-other", action="store_true", help="skip the second policy (faster)")
  ap.add_argument("--robust", action="store_true", help="read each case again with every sheet half and twice the size and turned a quarter, and record the worst move of any quantity")
  ap.add_argument("--seed-rules", action="store_true", help="ignore the company_rules of the cases and run on the seed rules alone")
  ap.add_argument("--dump", action="store_true", help="also write ledger.json and candidates.json beside score.json (every ledger row, and every candidate read with how it was decided)")
  ap.add_argument("--rules", help="run every case named under this rules file (a company_rules file), whatever its case.yaml says")

  args = ap.parse_args(argv)
  names = args.cases or CIO.list_cases()
  files_dir = CIO.cases_dir(args.cases_dir)
  profile, rule_set = OR.seed_profile()
  catalog = OR.work_item_catalog()
  os.makedirs(args.out, exist_ok=True)
  done: dict = {}
  total = time.monotonic()
  for name in names:
    folder = os.path.join(CIO.HERE, name)
    try:
      case = CIO.load_case(folder)
    except ValueError as e:
      print(f"{name}: SKIPPED. {e}")
      done[name] = {"case": name, "status": "BAD_CASE", "message": str(e)}
      continue
    files, probs = CIO.find_files(case, files_dir)
    if probs:
      print(f"{name}: NO_FILES. {' '.join(probs)}")
      done[name] = {"case": name, "tier": case["tier"], "status": "NO_FILES", "problems": probs}
      continue

    if args.seed_rules:
      rows, rule_problems, rule_file = [], [], None
    elif args.rules:
      rows, rule_problems = RB.load_rules(args.rules)
      rule_file = os.path.basename(args.rules)
    else:
      rows, rule_problems, rule_file = CIO.load_company_rules(case)
    if rule_problems:
      print(f"{name}: SKIPPED. {' '.join(rule_problems)}")
      done[name] = {"case": name, "status": "BAD_CASE", "message": " ".join(rule_problems)}
      continue
    note = {"file": rule_file, "count": len(rows), "keys": sorted({r["key"] for r in rows}), "note": CASE_RULES_NOTE} if rows else None
    with RB.using_case(rows):
      keep: dict = {}
      doc, timings = run_case(case, files, profile, rule_set, catalog, ready_only=args.ready_only, page_budget=args.page_budget, both=not args.no_other, rules=note, keep=keep)
      if args.robust:
        t = time.monotonic()
        doc["robust"] = robust_run(case, files, profile, rule_set, catalog, doc, ready_only=args.ready_only, page_budget=args.page_budget, rules=note, keep=keep)
        timings["robustness run"] = round(time.monotonic() - t, 1)
    base = load_baseline(args.baseline, name)
    folder_out = os.path.join(args.out, name)
    os.makedirs(folder_out, exist_ok=True)
    with open(os.path.join(folder_out, "score.json"), "w", encoding="utf-8") as fh:
      json.dump(r3(doc), fh, indent=1, sort_keys=True, ensure_ascii=False, default=str)
    with open(os.path.join(folder_out, "score.md"), "w", encoding="utf-8") as fh:
      fh.write(render_md(doc, base, timings))
    if args.dump:
      ledger_rows, candidate_rows = dump_view(keep)
      for fname, body in (("ledger.json", ledger_rows), ("candidates.json", candidate_rows)):
        with open(os.path.join(folder_out, fname), "w", encoding="utf-8") as fh:
          json.dump(r3(body), fh, indent=1, sort_keys=True, ensure_ascii=False, default=str)
    s = doc["summary"]
    print(f"{name}: {s['lines']} lines, {s['within_10']} within 10%, {s['within_5']} within 5% of the QS; invariants failing: {sum(1 for i in doc['invariants'] if i['status'] == 'FAIL')}; hash {doc['hash'][:16]}; {timings['total']} s")
    done[name] = doc

  combined = {"cases": {k: r3(v) for k, v in sorted(done.items())}}
  combined["hash"] = hashlib.sha256(json.dumps({k: v.get("hash") or v.get("status") for k, v in sorted(done.items())}, sort_keys=True).encode()).hexdigest()
  with open(os.path.join(args.out, "all.json"), "w", encoding="utf-8") as fh:
    json.dump(combined, fh, indent=1, sort_keys=True, ensure_ascii=False, default=str)
  print(f"all cases: {len(done)} in {time.monotonic() - total:.1f} s; combined hash {combined['hash'][:16]}")
  return 0

if __name__ == "__main__":
  sys.exit(main())
