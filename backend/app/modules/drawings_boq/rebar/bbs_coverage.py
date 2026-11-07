from __future__ import annotations
from decimal import Decimal as D
from app.engine.measure import rebar_expect as RX

INDEPENDENT, BY_ANSWER, ASSUMED, UNVERIFIABLE = "INDEPENDENT", "BY_ANSWER", "ASSUMED", "UNVERIFIABLE"
KINDS = (INDEPENDENT, BY_ANSWER, ASSUMED, UNVERIFIABLE)
KIND_OF_BASIS = {RX.BASIS_DRAWING: INDEPENDENT, RX.BASIS_ANSWER: BY_ANSWER, RX.BASIS_ASSUMED: ASSUMED}
NO_MEMBER, NO_EXPECTATION, INPUT_MISSING, NO_LINE, SEVERAL_SHAPES, EXTRA_MEMBER, FROM_SCHEDULE, NOT_COMPARED = (
  "NO_MEMBER_READ", "NO_EXPECTATION", "INPUT_MISSING", "NO_LINE_FOR_ROW", "SEVERAL_SHAPES", "EXTRA_MEMBER", "INPUT_FROM_SCHEDULE", "NOT_COMPARED")
NEEDS = {"SLAB": "slab panels with their sizes and bars", "TANK": "the tank's inside size and the bars of each face", "LINTEL": "the lintel table and the opening count",
  "STAIR": "a stair member with flight, waist and landing", "PLINTH": "plinth beam runs", "FOOTING": "footing sections and strip lengths", "BEAM": "a span for every beam mark",
  "COLUMN": "the floor heights and the schedule cell", "PARAPET": "a parapet member", "WALL": "a wall member"}
TWO = D("0.01")

def _q(x: D) -> D:
  return x.quantize(TWO)

def _share(part: D, whole: D):
  return None if not whole else round(float(part / whole * 100), 2)

def _slot() -> dict:
  return {k: D(0) for k in KINDS}

def _out(slot: dict) -> dict:
  total = sum(slot.values(), D(0))
  return {"billed_kg": str(_q(total)), **{f"{k.lower()}_kg": str(_q(v)) for k, v in slot.items()}, "independent_share_pct": _share(slot[INDEPENDENT], total),
    "independent_or_answer_share_pct": _share(slot[INDEPENDENT] + slot[BY_ANSWER], total)}

def build(rows: list, sheet_names: dict, match, row_basis: dict, row_why: dict) -> dict:
  item_of = {it.row_index: it for it in match.items}
  total, per_sheet, per_class, causes = _slot(), {}, {}, {}
  
  for i, row in enumerate(rows):
    kg = row.total_kg or D(0)
    it = item_of.get(i)
    family = getattr(it, "family", None)
    if i in row_basis:
      basis, family = row_basis[i][0], row_basis[i][1] or family
      kind, cause, missing = KIND_OF_BASIS.get(basis, UNVERIFIABLE), None, []
      if kind == UNVERIFIABLE:
        cause = FROM_SCHEDULE
    else:
      cause, why_family, missing = row_why.get(i) or ((NO_MEMBER if it is not None and it.kind == "ASK" else EXTRA_MEMBER if it is not None and it.kind == "EXTRA" else NOT_COMPARED), family, [])
      family = why_family or family
      kind = UNVERIFIABLE
    total[kind] += kg
    per_sheet.setdefault(row.sheet, _slot())[kind] += kg
    per_class.setdefault(family or "OTHER", _slot())[kind] += kg
    if kind == UNVERIFIABLE:
      slot = causes.setdefault((cause, family or "OTHER"), {"kg": D(0), "rows": 0, "missing": {}})
      slot["kg"] += kg
      slot["rows"] += 1
      for name in missing:
        slot["missing"][name] = slot["missing"].get(name, 0) + 1
        
  by_sheet = [{"sheet": idx, "name": sheet_names.get(idx), **_out(slot)} for idx, slot in sorted(per_sheet.items())]
  by_cause = [{"cause": c, "family": f, "kg": str(_q(v["kg"])), "rows": v["rows"], "missing_inputs": sorted(v["missing"], key=lambda n: (-v["missing"][n], n)), "needs": NEEDS.get(f)}
    for (c, f), v in sorted(causes.items(), key=lambda kv: (-kv[1]["kg"], kv[0]))]
  return {"total": _out(total), "by_sheet": by_sheet, "by_class": {k: _out(v) for k, v in sorted(per_class.items())}, "unverifiable_by_cause": by_cause,
    "note": "Tonnage with an independent expectation counts only rows compared with an expected bar made from the drawings; the bar schedule is never a source."}

def reconciles(cov: dict, tol: D = D("0.05")) -> list:
  bad = []
  for label, rec in [("total", cov["total"])] + [(s["name"] or str(s["sheet"]), s) for s in cov["by_sheet"]]:
    parts = sum((D(rec[f"{k.lower()}_kg"]) for k in KINDS), D(0))
    if abs(parts - D(rec["billed_kg"])) > tol:
      bad.append(f"coverage of {label}: the parts add to {parts}, billed {rec['billed_kg']}")
  if abs(sum((D(s["billed_kg"]) for s in cov["by_sheet"]), D(0)) - D(cov["total"]["billed_kg"])) > tol:
    bad.append("coverage: the sheets do not add to the total")
  return bad
