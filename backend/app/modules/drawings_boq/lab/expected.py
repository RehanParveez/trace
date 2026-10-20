from __future__ import annotations
from app.modules.drawings_boq.lab import tolerances as T
from app.modules.drawings_boq.lab.aliases import bill_quantity, KEY_LABEL, bill_key
from app.modules.drawings_boq.lab.bill import BillLine
from app.modules.drawings_boq.lab.compare import compare, software_totals

FORMAT = "trace-expected-boq/1"
UNITS = ("cft", "cuft", "sft", "sqft", "kg", "kgs", "rft", "nos", "no", "job", "cum", "sqm", "m3", "m2", "m")
MAX_LINES = 400
LEFT_OUT = ("QS_ERROR", "CONVENTION")

def from_bill(bill_lines, overrides: dict | None = None) -> tuple:
  lines, unmapped = [], []
  for bl in bill_lines:
    key = bill_key(bl.item, overrides)
    if key is None:
      unmapped.append({"item": bl.item, "unit": bl.unit, "quantity": bl.quantity, "section": bl.section})
      continue
    lines.append({"key": key, "item": bl.item, "section": bl.section, "unit": bl.unit, "quantity": round(float(bl.quantity), 6)})
  return lines, unmapped

def families(lines) -> list:
  by: dict = {}
  for ln in lines:
    _, _, si = bill_quantity(ln["key"], ln["unit"], float(ln["quantity"]))
    slot = by.setdefault(ln["key"], {"key": ln["key"], "label": KEY_LABEL.get(ln["key"], ln["key"]), "unit": ln["unit"], "si": 0.0, "rows": 0})
    slot["si"] += si
    slot["rows"] += 1
  out = []
  for s in by.values():
    in_unit, _, one_si = bill_quantity(s["key"], s["unit"], 1.0)
    out.append({"key": s["key"], "label": s["label"], "unit": s["unit"], "quantity": round(s["si"] * (in_unit / one_si if one_si else 1.0), 4), "rows": s["rows"]})
  return sorted(out, key=lambda s: s["label"])

def validate(doc) -> dict:
  if not isinstance(doc, dict):
    raise ValueError("EXPECTED_NOT_AN_OBJECT")
  if doc.get("format") != FORMAT:
    raise ValueError("EXPECTED_BAD_FORMAT")
  raw = doc.get("lines")
  if not isinstance(raw, list) or not raw:
    raise ValueError("EXPECTED_NO_LINES")
  if len(raw) > MAX_LINES:
    raise ValueError("EXPECTED_TOO_MANY_LINES")
  lines = []
  
  for ln in raw:
    if not isinstance(ln, dict) or ln.get("key") not in KEY_LABEL:
      raise ValueError("EXPECTED_BAD_FAMILY")
    q = ln.get("quantity")
    if isinstance(q, bool) or not isinstance(q, (int, float)) or q != q or q < 0:
      raise ValueError("EXPECTED_BAD_QUANTITY")
    unit = str(ln.get("unit") or "").strip()
    if unit.lower() not in UNITS:
      raise ValueError("EXPECTED_BAD_UNIT")
    lines.append({"key": ln["key"], "item": str(ln.get("item") or KEY_LABEL[ln["key"]])[:200], "section": str(ln.get("section") or "")[:200], "unit": unit, "quantity": float(q)})
  return {"format": FORMAT, "name": str(doc.get("name") or "")[:160], "source": str(doc.get("source") or "")[:255], "lines": lines,
    "tolerances": T.clean(doc.get("tolerances")), "default_tolerance_pct": T.clamp(doc.get("default_tolerance_pct"))}

def document(name: str, source: str, lines, tolerances: dict | None = None, default_tolerance_pct: float | None = None) -> dict:
  return {"format": FORMAT, "name": name, "source": source, "lines": list(lines), "tolerances": T.clean(tolerances or {}), "default_tolerance_pct": T.clamp(default_tolerance_pct)}

def to_bill_lines(lines) -> tuple:
  out, overrides = [], {}
  for i, ln in enumerate(lines):
    item = ln.get("item") or KEY_LABEL.get(ln["key"], ln["key"])
    if overrides.get(item, ln["key"]) != ln["key"]:
      item = f"{item} ({KEY_LABEL.get(ln['key'], ln['key'])})"
    overrides[item] = ln["key"]
    out.append(BillLine(row=i + 1, section=ln.get("section") or "", item=item, unit=ln["unit"], quantity=float(ln["quantity"])))
  return out, overrides

def tolerance_table(lines, tolerances: dict | None, all_families: float | None) -> dict:
  return {k: T.resolve(k, tolerances, all_families) for k in dict.fromkeys(ln["key"] for ln in lines)}

def gate(result: dict) -> dict:
  failing = [l for l in result.get("lines", []) if l["status"] in ("DIFF", "MISSING") and l.get("class") not in LEFT_OUT]
  scoped = [l for l in result.get("lines", []) if l["status"] in ("MATCH", "DIFF", "MISSING")]
  return {"passed": not failing, "failures": [l["key"] for l in failing], "families": len(scoped),
    "within": sum(1 for l in scoped if l["status"] == "MATCH"), "failed": len(failing)}

def check(lines, software_rows, tolerances: dict | None = None, all_families: float | None = None, overrides: dict | None = None, classes: dict | None = None) -> dict:
  table = tolerance_table(lines, tolerances, all_families)
  base = T.clamp(all_families) if T.clamp(all_families) is not None else T.DEFAULT_TOLERANCE_PCT
  bill, own = to_bill_lines(lines)
  out = compare(bill, software_rows, base, {**own, **(overrides or {})}, classes, {k: v[0] for k, v in table.items()})
  for ln in out["lines"]:
    pct, origin = table.get(ln["key"], (base, "default"))
    ln["tolerance_pct"], ln["tolerance_from"] = pct, origin
  out["gate"] = gate(out)
  return out

def snapshot(software_rows) -> dict:
  """The totals of a run by family, to be stored and compared with a later run."""
  totals, _ = software_totals(software_rows)
  return {k: {"quantity": round(float(v["quantity"]), 6), "unit": v["unit"], "rows": v["rows"]} for k, v in sorted(totals.items())}

def drift(before: dict, now: dict, limit_pct: float = 0.5) -> list:
  out = []
  for k in sorted(set(before) | set(now)):
    a, b = before.get(k), now.get(k)
    if a is None or b is None:
      out.append({"key": k, "before": a and a["quantity"], "now": b and b["quantity"], "change_pct": None, "why": "ADDED" if a is None else "GONE"})
      continue
    qa, qb = float(a["quantity"]), float(b["quantity"])
    pct = (qb - qa) / qa * 100.0 if qa else (0.0 if qb == 0 else None)
    if pct is None or abs(pct) > limit_pct:
      out.append({"key": k, "before": qa, "now": qb, "change_pct": None if pct is None else round(pct, 3), "why": "MOVED"})
  return out
