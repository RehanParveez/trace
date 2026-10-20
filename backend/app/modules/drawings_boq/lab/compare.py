from __future__ import annotations
from dataclasses import dataclass, field
from statistics import median, mean
from app.modules.drawings_boq.lab.aliases import KEY_LABEL, NOT_MEASURED, SOFTWARE_UNIT, bill_key, bill_quantity, software_key, software_to_bill_unit

CLASSES = ("READING", "CONVENTION", "QS_ERROR", "MISSING_FEATURE", "NEEDS_DECISION")
DEFAULT_TOLERANCE_PCT = 5.0

def closeness_of(status: str, error_pct) -> float | None:
  """How close one bill line is, from 0 to 100. A line that is found is 100 less its error (never below 0); a line the software did not find is 0; a line with nothing to compare against is not scored."""
  if status == "MISSING":
    return 0.0
  if status in ("MATCH", "DIFF") and error_pct is not None:
    return round(max(0.0, 100.0 - abs(float(error_pct))), 1)
  return None

@dataclass
class _Agg:
  key: str
  unit: str = ""
  bill_unit: str = ""
  qs_si: float = 0.0
  qs_bill: float = 0.0
  bill_rows: list = field(default_factory=list)
  sw_si: float = 0.0
  sw_rows: int = 0
  sw_tags: dict = field(default_factory=dict)

def software_totals(rows) -> tuple:
  totals = {}
  unclassified = {}
  for r in rows:
    trace = r.get("trace") or {}
    inputs = trace.get("inputs") or {}
    src = inputs.get("formwork_source") or inputs.get("steel_source") or {}
    tag = inputs.get("tag") or src.get("tag")
    label = trace.get("label")
    key = software_key(r.get("formula_code") or "", tag, label)
    q = float(r.get("quantity") or 0)
    unit = r.get("unit") or ""
    
    if key is None:
      name = str(tag or label or r.get("formula_code") or "?")
      d = unclassified.setdefault(name, {"name": name, "rows": 0, "quantity": 0.0, "unit": unit})
      d["rows"] += 1
      d["quantity"] += q
      continue
    d = totals.setdefault(key, {"quantity": 0.0, "rows": 0, "tags": {}, "unit": SOFTWARE_UNIT.get(key, unit)})
    d["quantity"] += q
    d["rows"] += 1
    if tag:
      d["tags"][str(tag)] = d["tags"].get(str(tag), 0.0) + q
  return totals, sorted(unclassified.values(), key=lambda x: -x["quantity"])

def compare(bill_lines, software_rows, tolerance_pct: float = DEFAULT_TOLERANCE_PCT, overrides: dict | None = None, classes: dict | None = None, tolerances: dict | None = None) -> dict:
  totals, unclassified = software_totals(software_rows)
  aggs = {}
  unmapped = []
  
  for bl in bill_lines:
    key = bill_key(bl.item, overrides)
    if key is None:
      unmapped.append({"row": bl.row, "section": bl.section, "item": bl.item, "unit": bl.unit, "quantity": bl.quantity})
      continue
  
    q_bill, si_unit, q_si = bill_quantity(key, bl.unit, bl.quantity)
    a = aggs.setdefault(key, _Agg(key=key))
    a.unit = si_unit if not a.unit else a.unit
    a.bill_unit = a.bill_unit or bl.unit
    a.qs_si += q_si
    a.qs_bill += q_bill
    a.bill_rows.append({"row": bl.row, "section": bl.section, "item": bl.item, "unit": bl.unit, "quantity": bl.quantity})
  for key, d in totals.items():
    a = aggs.setdefault(key, _Agg(key=key))
    a.unit = a.unit or d["unit"]
    a.sw_si = d["quantity"]
    a.sw_rows = d["rows"]
    a.sw_tags = d["tags"]
  classes = classes or {}
  lines = []
  
  for key, a in aggs.items():
    in_bill = bool(a.bill_rows)
    scope = key != "LUMP_SUM"
    factor = (a.qs_bill / a.qs_si) if a.qs_si else None
    sw_bill = None
    if a.sw_rows:
      sw_bill = a.sw_si * factor if factor else software_to_bill_unit(SOFTWARE_UNIT.get(key, a.unit), a.sw_si)
    err = None
    if in_bill and a.sw_rows and a.qs_si:
      err = (a.sw_si - a.qs_si) / a.qs_si * 100.0
    tol = float((tolerances or {}).get(key, tolerance_pct))
    if not scope:
      status, suggested = "OUT_OF_SCOPE", None
    elif not in_bill:
      status, suggested = "EXTRA", "NEEDS_DECISION"
    elif not a.sw_rows:
      status, suggested = "MISSING", ("MISSING_FEATURE" if key in NOT_MEASURED else "NEEDS_DECISION")
    elif err is not None and abs(err) <= tol:
      status, suggested = "MATCH", None
    else:
      status, suggested = "DIFF", "NEEDS_DECISION"
    user = classes.get(key) or {}
    cls = user.get("class") if user.get("class") in CLASSES else None
    
    lines.append({
      "key": key, "label": KEY_LABEL.get(key, key), "status": status, "unit": a.bill_unit or a.unit, "tolerance_pct": tol,
      "qs": round(a.qs_bill, 3) if in_bill else None, "software": round(sw_bill, 3) if sw_bill is not None else None,
      "difference": round(sw_bill - a.qs_bill, 3) if (sw_bill is not None and in_bill) else None,
      "error_pct": round(err, 2) if err is not None else None,
      "closeness": closeness_of(status, err),
      "suggested_class": suggested, "class": cls, "note": user.get("note") or "",
      "bill_rows": a.bill_rows, "software_rows": a.sw_rows,
      "software_tags": [{"tag": t, "quantity": round(q, 4)} for t, q in sorted(a.sw_tags.items(), key=lambda x: -x[1])[:12]],
    })
    
  order = {"DIFF": 0, "MISSING": 1, "EXTRA": 2, "MATCH": 3, "OUT_OF_SCOPE": 4}
  lines.sort(key=lambda x: (order[x["status"]], -abs(x["error_pct"] or 0), x["label"]))
  scoped = [x for x in lines if x["status"] != "OUT_OF_SCOPE" and x["qs"] is not None]
  both = [x for x in scoped if x["error_pct"] is not None]
  sum_qs = sum(abs(x["qs"]) for x in both)
  covered = [x for x in scoped if x["software"] is not None]
  scores = [x["closeness"] for x in scoped if x["closeness"] is not None]
  open_diffs = [x for x in lines if x["status"] in ("DIFF", "MISSING", "EXTRA") and not x["class"]]
  
  measures = {
    "bill_lines": len(scoped), "compared": len(both),
    "within_tolerance": sum(1 for x in both if abs(x["error_pct"]) <= x["tolerance_pct"]),
    "line_error_median_pct": round(median(abs(x["error_pct"]) for x in both), 2) if both else None,
    "coverage_pct": round(100.0 * len(covered) / len(scoped), 1) if scoped else None,
    "closeness_pct": round(mean(scores), 1) if scores else None,
    "closeness_measured_pct": round(mean(x["closeness"] for x in both), 1) if both else None,
    "extra_lines": sum(1 for x in lines if x["status"] == "EXTRA"),
    "unclassified_differences": len(open_diffs),
  }
  return {"tolerance_pct": tolerance_pct, "lines": lines, "unmapped": unmapped, "unclassified_software": unclassified[:30], "measures": measures}
