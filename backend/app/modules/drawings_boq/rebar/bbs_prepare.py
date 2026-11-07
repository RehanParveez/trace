from __future__ import annotations
from decimal import Decimal as D
from app.engine.measure import rebar_expect as RX
from app.modules.drawings_boq.rebar import bbs_report as BR
from app.modules.drawings_boq.takeoff.prep.facts import FLOOR_ORDER

LAYOUT = "PK_BBS_FEET"
COLUMNS = (("Sr", "sr"), ("Description", "description"), ("Dia (#)", "dia"), ("C/C (in)", "spacing_in"), ("Members", "members"), ("Each", "each"), ("Total bars", "total"),
  ("Cut (ft)", "cut_ft"), ("Total length (ft)", "total_ft"), ("Unit kg/ft", "unit_kg_ft"), ("kg", "kg"))
ORDER = ("FOOTING", "PLINTH", "COLUMN", "BEAM", "SLAB", "STAIR", "LINTEL", "TANK")
CLASS_WORDS = {"FOOTING": "FOOTINGS", "PLINTH": "PLINTH BEAMS", "COLUMN": "COLUMNS", "BEAM": "BEAMS", "SLAB": "SLABS", "STAIR": "STAIRCASE", "LINTEL": "LINTELS", "TANK": "TANKS"}
FLOORED = ("COLUMN", "BEAM", "SLAB", "LINTEL")
FLOOR_WORDS = {"BASEMENT": "BASEMENT", "GROUND": "GROUND FLOOR", "FIRST": "FIRST FLOOR", "SECOND": "SECOND FLOOR", "THIRD": "THIRD FLOOR", "FOURTH": "FOURTH FLOOR", "ROOF": "ROOF"}
STRAIGHT, STIRRUP, U_BAR, SPECIAL = "STRAIGHT", "STIRRUP_RECT", "U_BAR", "SPECIAL"
TWO = D("0.01")
THREE = D("0.001")
SECTION_KEYS = {"COLUMN": ("size_w_in", "size_d_in", "COVER_COLUMN_BEAM")}

def f2(x):
  return None if x is None else float(D(str(x)).quantize(TWO))

def f3(x):
  return None if x is None else float(D(str(x)).quantize(THREE))

def _inp(e, name):
  return next((i.value for i in e.inputs if i.name == name and i.value is not None), None)

def _dec(x):
  return None if x is None else D(str(x))

def shape_of(e, line) -> tuple:
  """(shape, parts in ft): a ring is a rectangle of its section less cover, a footing bar a U with its two legs; the rest straight. A class with no rule for its bars is special."""
  role = (line.role or "").lower()
  cut = _dec(line.cut_ft)
  if cut is None:
    return SPECIAL, []
  if "ring" in role:
    w_name, d_name, c_name = SECTION_KEYS.get(e.cls, ("width_in", "depth_in", "COVER_COLUMN_BEAM"))
    w, d, c = _dec(_inp(e, w_name)), _dec(_inp(e, d_name)), _dec(_inp(e, c_name))
    if None not in (w, d, c):
      return STIRRUP, [f2((w - 2 * c) / 12), f2((d - 2 * c) / 12)]
    return SPECIAL, [f2(cut)]
  if e.cls == "FOOTING" and (role.startswith("main") or role.startswith("bars along")):
    depth, c = _dec(_inp(e, "depth_in")), _dec(_inp(e, "COVER_FOOTING"))
    if None not in (depth, c):
      leg = (depth - 2 * c) / 12
      return U_BAR, [f2(leg), f2(cut - 2 * leg), f2(leg)]
    return SPECIAL, [f2(cut)]
  if e.cls in ("TANK", "STAIR"):
    return SPECIAL, [f2(cut)]
  return STRAIGHT, [f2(cut)]

def _source(job: dict, e) -> str:
  for i in e.inputs:
    if i.value is not None and i.name not in RX.CONVENTION_KEYS and RX.basis_of(i) == RX.BASIS_DRAWING and " p." in str(i.source):
      return str(i.source)
  return f"p.{job['page']}" if job.get("page") else "no page"

def _floor_rank(floor) -> int:
  return -1 if floor is None else (FLOOR_ORDER.index(floor) if floor in FLOOR_ORDER else len(FLOOR_ORDER))

def title_of(cls: str, floor) -> str:
  base = CLASS_WORDS.get(cls, cls)
  return f"{base} ({FLOOR_WORDS.get(floor, floor)})" if cls in FLOORED and floor else base

def _group_key(cls: str, floor) -> tuple:
  return (ORDER.index(cls) if cls in ORDER else len(ORDER), _floor_rank(floor), cls, floor or "")

def prepare(results: list, project: dict | None = None) -> dict:
  """results: [(job, Expected)] as expect_source.run_jobs gives them."""
  groups: dict = {}
  answers: list = []
  conventions: dict = {}
  for job, e in results:
    slot = groups.setdefault(_group_key(e.cls, e.floor), {"title": title_of(e.cls, e.floor), "class": e.cls, "floor": e.floor, "rows": [], "unverifiable": []})
    members = job.get("plan_count")
    source = _source(job, e)
    sr = 0
    for line in e.lines:
      if line.kg is None:
        continue
      sr += 1
      shape, parts = shape_of(e, line)
      each = _dec(line.count)
      bars = None if members is None else each * D(int(members))
      total_ft = line.total_ft * (D(int(members)) if members else D(1))
      kg = line.kg * (D(int(members)) if members else D(1))
      slot["rows"].append({"member": e.mark, "floor": e.floor, "sr": sr, "description": line.role, "dia": line.dia, "spacing_in": f2(line.spacing_in), "members": members, "each": f2(each),
        "total": f2(bars), "cut_ft": f2(line.cut_ft), "laps": line.laps, "lap_ft": f2(line.lap_ft), "total_ft": f2(total_ft), "unit_kg_ft": f3(RX.kg_per_ft(line.dia)) if line.dia else None,
        "kg": f2(kg), "kg_each_member": f2(line.kg), "members_assumed": members is None, "shape": shape, "parts": parts, "note": line.note, "source": source, "basis": RX.job_basis(e)})
    missing = [l for l in e.lines if l.kg is None]
    if missing or not e.lines:
      slot["unverifiable"].append({"member": e.mark, "floor": e.floor, "class": e.cls, "lines_without_figure": len(missing), "lines": len(e.lines), "blocked": list(e.blocked), "source": source,
        "reason": ("no bars can be worked out; missing: " + ", ".join(e.blocked)) if e.blocked else "no bars can be worked out"})
    for i in e.inputs:
      if i.value is None:
        continue
      row = {"input": i.name, "value": i.value if not isinstance(i.value, D) else str(i.value), "basis": RX.basis_of(i), "source": i.source}
      if i.name in RX.CONVENTION_KEYS:
        conventions.setdefault((i.name, str(i.value), i.source), {**row, "kind": "convention"})
      elif row["basis"] != RX.BASIS_DRAWING:
        answers.append({**row, "member": e.mark, "class": e.cls, "floor": e.floor})
  sheets = []
  grand_kg, grand_dia, grand_rows = D(0), {}, 0
  for key in sorted(groups):
    g = groups[key]
    by_dia: dict = {}
    kg = D(0)
    for r in g["rows"]:
      slot = by_dia.setdefault(str(r["dia"]), {"length_ft": D(0), "kg": D(0)})
      slot["length_ft"] += D(str(r["total_ft"]))
      slot["kg"] += D(str(r["kg"]))
      kg += D(str(r["kg"]))
      grand_dia.setdefault(str(r["dia"]), D(0))
      grand_dia[str(r["dia"])] += D(str(r["kg"]))
    grand_kg += kg
    grand_rows += len(g["rows"])
    g["totals"] = {"rows": len(g["rows"]), "kg": f2(kg), "by_dia": {k: {"length_ft": f2(v["length_ft"]), "kg": f2(v["kg"])} for k, v in sorted(by_dia.items(), key=lambda t: (t[0] == "None", t[0]))},
      "rows_with_members_unknown": sum(1 for r in g["rows"] if r["members_assumed"])}
    g["state"] = "ROWS" if g["rows"] and not g["unverifiable"] else "PARTLY_UNVERIFIABLE" if g["rows"] else "ALL_UNVERIFIABLE"
    sheets.append(g)
  return {"layout": LAYOUT, "columns": [{"title": t, "key": k} for t, k in COLUMNS], "project": project or {}, "sheets": sheets,
    "totals": {"sheets": len(sheets), "rows": grand_rows, "kg": f2(grand_kg), "by_dia_kg": {k: f2(v) for k, v in sorted(grand_dia.items(), key=lambda t: (t[0] == "None", t[0]))}},
    "answers": answers, "conventions": sorted(conventions.values(), key=lambda c: c["input"]),
    "unverifiable": [u for g in sheets for u in g["unverifiable"]],
    "sources": sorted({r["source"] for g in sheets for r in g["rows"]}),
    "notes": ["Each row is one expected bar line of one member, worked out from the drawings and the answers listed; it is not a copy of any supplied schedule.",
      "Rows whose member count is not known (members_assumed) show the weight of one member; the sheet total counts them once.",
      "A member whose bars cannot be worked out has no row; it is listed with the inputs it lacks."]}

def compare(prepared: dict, rows: list, sheets: list, findings: list, row_expect: dict, coverage: dict | None = None) -> dict:
  """Trace's expected bars against the rows of a supplied schedule that were audited, each difference with the finding that explains it."""
  hits = BR.findings_by_row(rows, findings)
  names = {s["idx"]: s["name"] for s in sheets}
  out, per = [], {}
  for r in rows:
    ex = row_expect.get(str(r["row_no"] - 1))
    if not ex:
      continue
    verdict = BR.row_verdict(hits.get(r["row_no"], []))
    bbs_kg, trace_kg = BR.d(r.get("total_kg")), BR.d(ex.get("kg"))
    diff = None if bbs_kg is None or trace_kg is None else trace_kg - bbs_kg
    out.append({"row_no": r["row_no"], "sheet": r["sheet"], "sheet_name": names.get(r["sheet"]), "page": r.get("page"), "member": r.get("member"), "sr": r.get("sr"), "description": r.get("description"),
      "bbs": {"each": BR.num(r.get("each")), "cut_ft": BR.num(r.get("cut_ft")), "kg": BR.num(bbs_kg)}, "trace": {"each": BR.num(ex.get("each")), "cut_ft": BR.num(ex.get("cut")), "kg": BR.num(trace_kg)},
      "diff_kg": BR.num(diff), "class": verdict["class"], "rule": verdict["rule"], "status": verdict["status"], "codes": sorted({f["code"] for f in hits.get(r["row_no"], [])})})
    slot = per.setdefault(r["sheet"], {"sheet": r["sheet"], "name": names.get(r["sheet"]), "rows_compared": 0, "bbs_kg": D(0), "trace_kg": D(0), "differences": 0})
    slot["rows_compared"] += 1
    slot["bbs_kg"] += bbs_kg or D(0)
    slot["trace_kg"] += trace_kg or D(0)
    slot["differences"] += 1 if verdict["class"] else 0
  sheet_totals = [{**s, "bbs_kg": f2(s["bbs_kg"]), "trace_kg": f2(s["trace_kg"]), "diff_kg": f2(s["trace_kg"] - s["bbs_kg"])} for s in sorted(per.values(), key=lambda s: s["sheet"])]
  supplied = sum((BR.d(r.get("total_kg")) or D(0) for r in rows), D(0))
  return {"rows": out, "sheets": sheet_totals, "coverage": coverage,
    "totals": {"supplied_kg": f2(supplied), "supplied_kg_compared": f2(sum((s["bbs_kg"] for s in per.values()), D(0))), "trace_kg_for_those_rows": f2(sum((s["trace_kg"] for s in per.values()), D(0))),
      "trace_prepared_kg": prepared["totals"]["kg"], "rows_compared": len(out), "supplied_rows": len(rows)},
    "note": "Trace kg here is the expected weight of the supplied row's own members count; a difference is explained by the finding named on the row, or is a method difference of laps and hooks."}
