from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
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
from app.engine.measure import rulebook as RB
from types import SimpleNamespace
from app.modules.drawings_boq.takeoff.extract import beam_overlap_service as BOS

MATCH, NEAR, DIFF, MISSING, EXTRA, NO_TRUTH = "MATCH", "NEAR", "DIFF", "MISSING", "EXTRA", "NO_TRUTH"
STATUS_RANK = {MATCH: 0, NEAR: 1, DIFF: 2, NO_TRUTH: 3, MISSING: 4, EXTRA: 4}
CLASS_RANK = {"DRAWING": 0, "CONVENTION": 1, "NEEDS_DECISION": 2, "QS_ERROR": 3}
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
  body = {k: v for k, v in doc.items() if k not in ("hash", "timings", "stage_view")}
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

def trace_lines(rows: list, floor_of: dict, catalog: dict) -> list:
  groups: dict = {}
  for r in rows:
    family = family_of(r)
    floor = floor_of.get(str(r.get("level_id"))) if r.get("level_id") else None
    code = r.get("work_item_code") or "?"
    unit = SOFTWARE_UNIT.get(family) if family in SOFTWARE_UNIT else (r.get("unit") or "")
    k = (code, family or "-", floor or "-", unit)
    g = groups.setdefault(k, {"si": 0.0, "rows": 0})
    q = float(r.get("quantity") or 0)
    g["si"] += q
    g["rows"] += 1

  out = []
  for (code, family, floor, unit), g in sorted(groups.items()):
    wi = catalog.get(code)
    out.append({"key": f"{code}/{family}/{floor}", "code": code, "family": None if family == "-" else family, "floor": None if floor == "-" else floor, "unit": unit, "si": g["si"],
      "rows": g["rows"], "description": (getattr(wi, "description", None) or code)})
  return out

def to_unit(value_si: float, si_unit: str, unit: str):
  qty, target_si, one_si = bill_quantity("", unit, 1.0)
  if target_si != si_unit or not one_si:
    return None
  return value_si * (qty / one_si)

def resolve(entry: dict, lines: list) -> list:
  key = entry["key"]
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

def check_facts(read: list, facts: list) -> list:
  out = []
  for i, f in enumerate(facts):
    label = f"fact {i + 1} ({f.get('kind')} {f.get('mark') or f.get('label') or ''})".strip()
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
        non_plan += [tag] * sum(1 for c in live if c.category in PLAN_CATEGORIES)
      if ident.get("discipline") == "STRUCTURAL":
        structural += [tag] * sum(1 for c in live if c.category in ("DOOR", "WINDOW"))
      if _is_plan(r) and live:
        title = r.get("title") or {}
        if not title.get("composite") and not (title.get("level_hint") or ident.get("floor")):
          no_floor.append(tag)
        if r.get("ratio") is None:
          no_scale.append(tag)

  add("PLAN_ITEMS_ONLY_ON_PLAN_PAGES", non_plan, "Walls, rooms, openings or members were read on a page that is not a plan.")
  add("NO_WINDOWS_ON_STRUCTURAL_SHEETS", structural, "A door or window was read on a structural sheet.")
  add("EVERY_PLAN_PAGE_HAS_A_FLOOR_AND_A_SCALE", no_floor + no_scale, "A plan page with items has no floor, or its scale was not measured and 1:100 was used.")
  doubled, member_two, beam_two, floor_two = [], [], [], []
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

  add("EACH_STAIR_FLIGHT_ONCE_IN_THE_BUILDING", doubled, "A stair flight and its twin on the floor above are both accepted.")
  add("NO_MEMBER_ON_TWO_SHEETS", member_two, "A column or footing mark of one floor is accepted from more than one sheet.")
  add("NO_BEAM_ON_TWO_SOURCES", beam_two, "A beam mark of one floor is accepted from more than one sheet, or a floor whose framing plan draws the roof beams has them accepted from the walls as well.")
  add("ONE_ARCHITECTURE_SOURCE_PER_FLOOR", floor_two, "Walls of one floor are accepted from more than one sheet.")
  bad = [f"{r.get('work_item_code')}" for r in rows if not (float(r.get("quantity") or 0) > 0) or not math.isfinite(float(r.get("quantity") or 0)) or not r.get("unit")]
  add("LEDGER_ROWS_ARE_POSITIVE_AND_HAVE_A_UNIT", bad, "A ledger row has a zero, negative or missing quantity, or no unit.")
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

def engine_digest(ledger: list, floor_of: dict) -> str:
  """The hash of the engine's output: the ledger rows as (work item, floor, unit, quantity, label), sorted. It does not depend on how the score reads them."""
  items = sorted([r.get("work_item_code") or "?", str(floor_of.get(str(r.get("level_id"))) if r.get("level_id") else ""), r.get("unit") or "", str(round(float(r.get("quantity") or 0), 6)),
    str(((r.get("trace") or {}).get("label")) or "")] for r in ledger)
  return hashlib.sha256(json.dumps(items, sort_keys=True, default=str).encode()).hexdigest()

def run_case(case: dict, files: dict, profile, rule_set, catalog, *, ready_only: bool = False, page_budget: float = BM.PAGE_BUDGET_S, reader=None, both: bool = True, rules: dict | None = None) -> tuple:
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
      if r.get("seconds") is not None and r["seconds"] >= page_budget:
        problems.append({"pdf": name, "page": r["page_no"], "message": f"the page took {r['seconds']} s (the budget is {page_budget:g} s)"})
    reads.append((name, rows))
    timings[f"read {name}"] = round(time.monotonic() - t, 1)

  def engine(policy_ready: bool) -> tuple:
    accs, ledger, errors, tallies = [], [], [], []
    for name, rows in reads:
      acc = OA.accept_case(case["name"], [(name, rows)], profile, ready_only=policy_ready)
      accs.append(acc)
      tallies.append(acc.tally)
      problems_here = acc.problems
      inputs = OA.build_inputs(acc)
      printed = acc.printed[next(iter(acc.printed))] if acc.printed else {}
      res = OR.run_engine(inputs, profile, rule_set, printed, case=case["name"])

      for e in res.errors:
        errors.append({"pdf": name, **(e if isinstance(e, dict) else {"message": str(e)})})
      ledger += [{**{k: v for k, v in r.items() if k != "_entry"}, "quantity": float(r["quantity"])} for r in res.rows]
      if not policy_ready:
        for p in problems_here:
          problems.append({"pdf": name, "page": p.get("page"), "message": f"{p.get('code')}: {p.get('message')}"})
    floor_of = {}
    for a in accs:
      floor_of.update({str(k): v for k, v in a.floor_of.items()})
    lines = trace_lines(ledger, floor_of, catalog)
    sc, extra = score_lines(case["expected"], lines)
    return accs, ledger, errors, tallies, sc + extra_lines(extra)

  t = time.monotonic()
  main_ready = ready_only
  accs, ledger, errors, tallies, lines = engine(main_ready)
  timings["accept and run"] = round(time.monotonic() - t, 1)
  other = None
  if both:
    t = time.monotonic()
    _a, _l, _e, _t, other_lines = engine(not main_ready)
    other = summarise(other_lines)
    timings["accept and run (other policy)"] = round(time.monotonic() - t, 1)

  facts = check_facts([r for _n, rows in reads for r in rows], case["facts"])
  doc = {"case": case["name"], "tier": case["tier"], "status": "SCORED", "policy": "ready_only" if main_ready else "accept_all", "lines": lines, "facts": facts,
    "facts_tally": {s: sum(1 for f in facts if f["status"] == s) for s in sorted({f["status"] for f in facts})},
    "invariants": invariants(reads, accs, ledger), "summary": summarise(lines),
    "other_policy": {"policy": "accept_all" if main_ready else "ready_only", "summary": other} if other is not None else None,
    "accept": [{k: t.get(k) for k in ("candidates", "ready_would_accept", "all_would_accept", "accepted", "accept_refused", "confirmed", "confirm_refused")} for t in tallies],
    "engine_errors": errors, "problems": sorted(problems, key=lambda p: (str(p.get("pdf")), p.get("page") or 0, str(p.get("message")))),
    "ledger_rows": len(ledger), "files": {n: case["sha256"].get(n) for n in case["pdfs"]}}
  if rules:
    doc["rules"] = rules
  floor_all = {str(k): v for a in accs for k, v in a.floor_of.items()}
  doc["engine_digest"] = engine_digest(ledger, floor_all)
  view = stage_view(case, ledger, floor_all, catalog)
  if view:
    doc["stage_view"] = view
  doc["hash"] = digest(doc)
  doc["marks"] = _mark_lines(reads)
  timings["total"] = round(time.monotonic() - t0, 1)
  return doc, timings

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
  if doc.get("stage_view"):
    v = doc["stage_view"]
    out += [f"**Brick and plaster by stage** ({v['within_10']} of {v['of']} within 10% of the QS; not part of the hash)", "", "| Line | Floor | Stage | Unit | QS | Trace | Diff % | Stages found |", "|---|---|---|---|---|---|---|---|"]
    out += [f"| {l['key']} | {l['floor']} | {l['stage']} | {l['unit']} | {_fmt(l['qs'])} | {_fmt(l['trace'])} | {_fmt(l['diff_pct_qs'])} | {', '.join(l['stages'])} |" for l in v["lines"]]
    out += [""]
  if doc.get("other_policy") and doc["other_policy"]["summary"]:
    o = doc["other_policy"]["summary"]
    out += [f"Other policy ({doc['other_policy']['policy']}): {o['lines']} lines, {o['within_10']} within 10%, {o['within_5']} within 5% of the QS.", ""]
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
  ap.add_argument("--seed-rules", action="store_true", help="ignore the company_rules of the cases and run on the seed rules alone")
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
      doc, timings = run_case(case, files, profile, rule_set, catalog, ready_only=args.ready_only, page_budget=args.page_budget, both=not args.no_other, rules=note)
    base = load_baseline(args.baseline, name)
    folder_out = os.path.join(args.out, name)
    os.makedirs(folder_out, exist_ok=True)
    with open(os.path.join(folder_out, "score.json"), "w", encoding="utf-8") as fh:
      json.dump(r3(doc), fh, indent=1, sort_keys=True, ensure_ascii=False, default=str)
    with open(os.path.join(folder_out, "score.md"), "w", encoding="utf-8") as fh:
      fh.write(render_md(doc, base, timings))
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
