from __future__ import annotations
import io
import re
from statistics import median
import openpyxl

FLOORS = ("BASEMENT", "GROUND", "FIRST", "SECOND", "ROOF", "OTHERS")
FLOOR_LABEL = {"BASEMENT": "Basement", "GROUND": "Ground floor", "FIRST": "First floor", "SECOND": "Second floor", "ROOF": "Mumty / roof", "OTHERS": "Others"}
_FLOOR_WORDS = (
  (re.compile(r"basement|\bb\.?\s?f\b|cellar", re.I), "BASEMENT"),
  (re.compile(r"ground|\bg\.?\s?f\b", re.I), "GROUND"),
  (re.compile(r"first|\bf\.?\s?f\b|1st", re.I), "FIRST"),
  (re.compile(r"second|\bs\.?\s?f\b|2nd", re.I), "SECOND"),
  (re.compile(r"mumty|roof|terrace|\bm\.?\s?f\b|\br\.?\s?f\b", re.I), "ROOF"),
  (re.compile(r"other", re.I), "OTHERS"),
)

GROUPS = (
  ("FOUNDATION", "RCC foundation", re.compile(r"foundation|footing", re.I)),
  ("PLINTH_BEAMS", "Plinth beams", re.compile(r"plinth\s*beam", re.I)),
  ("COLUMNS", "RCC columns", re.compile(r"columns?", re.I)),
  ("RCC_WALL", "RCC wall", re.compile(r"rcc\s*wall", re.I)),
  ("LINTELS", "Lintels", re.compile(r"lintel", re.I)),
  ("ROOF_BEAMS", "Roof beams", re.compile(r"roof\s*beam|\bbeams?\b", re.I)),
  ("SLAB", "Slab", re.compile(r"\bslab", re.I)),
  ("OHWT", "Overhead water tank", re.compile(r"ohwt|over\s*head", re.I)),
  ("UHWT", "Underground water tank", re.compile(r"uhwt|ugwt|under\s*ground", re.I)),
  ("SEPTIC", "Septic tank", re.compile(r"septic", re.I)),
  ("STAIRCASE", "Staircase", re.compile(r"stair", re.I)),
  ("PARAPET", "Parapet", re.compile(r"parapet", re.I)),
)
LABEL = {k: label for k, label, _ in GROUPS}

NOT_BUILT = ("OHWT", "UHWT", "SEPTIC", "STAIRCASE", "PARAPET")
SOFTWARE_GROUP = {"FOOTING": "FOUNDATION", "COLUMN": "COLUMNS", "RCC_WALL": "RCC_WALL", "LINTEL": "LINTELS", "SLAB": "SLAB"}

def floor_of(text: str | None) -> str | None:
  """The floor a column heading or a level name means, or None."""
  t = str(text or "")
  for rx, key in _FLOOR_WORDS:
    if rx.search(t):
      return key
  return None

def group_of_qs(description: str) -> str | None:
  d = str(description or "")
  for key, _, rx in GROUPS:
    if rx.search(d):
      return key
  return None

def group_of_software(category: str, tag: str | None) -> str | None:
  cat = str(category or "").upper()
  if cat == "BEAM":
    return "PLINTH_BEAMS" if str(tag or "").upper().startswith("PLINTH") else "ROOF_BEAMS"
  return SOFTWARE_GROUP.get(cat)

def _text(v) -> str:
  return re.sub(r"\s+", " ", str(v)).strip() if v is not None else ""

def _number(v) -> float | None:
  return None if isinstance(v, bool) or not isinstance(v, (int, float)) else float(v)

def parse_steel_summary(data: bytes) -> dict:
  wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
  ws = next((w for w in wb.worksheets if "steel" in w.title.lower() and "summary" in w.title.lower()), None) or next((w for w in wb.worksheets if "steel" in w.title.lower()), None)
  if ws is None:
    raise ValueError("STEEL_NO_SHEET")
  head_row, cols = None, {}
  
  for r in range(1, 20):
    found = {c: floor_of(ws.cell(r, c).value) for c in range(1, min(ws.max_column, 12) + 1) if ws.cell(r, c).value is not None}
    mapped = {c: f for c, f in found.items() if f}
    if len(mapped) >= 2 and any(_text(ws.cell(r, c).value).lower().startswith("desc") for c in range(1, 6)):
      head_row, cols = r, mapped
      break
  
  if head_row is None:
    raise ValueError("STEEL_NO_HEADER")
  col_desc = next(c for c in range(1, 6) if _text(ws.cell(head_row, c).value).lower().startswith("desc"))
  lines: list = []
  current = None
  total = None
  
  for r in range(head_row + 1, ws.max_row + 1):
    item = _text(ws.cell(r, col_desc).value)
    label_a = _text(ws.cell(r, 1).value)
    if not item and not label_a:
      continue
    up = (item or label_a).upper()
    if "TOTAL STEEL IN KG" in up:
      total = next((v for v in (_number(ws.cell(r, c).value) for c in range(max(cols) + 1, min(ws.max_column, 12) + 1)) if v is not None), None)
      continue
    if up.startswith(("TOTAL", "STEEL WA", "GRAND")):
      continue
  
    vals = {}
    for c, f in cols.items():
      v = _number(ws.cell(r, c).value)
      if v is not None:
        vals[f] = vals.get(f, 0.0) + v
    if item.lower().startswith("upto") or (not label_a and item.lower().startswith(("up to", "below", "above"))):
      key = current
    else:
      key = group_of_qs(item)
      current = key
    if key is None or not vals:
      continue
  
    lines.append({"row": r, "group": key, "item": item, "floors": vals})
  if not lines:
    raise ValueError("STEEL_EMPTY")
  waste = None
  for r in range(head_row + 1, ws.max_row + 1):
    m = re.search(r"waist?age\s*(\d+(?:\.\d+)?)\s*%", _text(ws.cell(r, 1).value) + " " + _text(ws.cell(r, col_desc).value), re.I)
    if m:
      waste = float(m.group(1))
  return {"sheet": ws.title, "floors": [f for f in FLOORS if f in set(cols.values())], "lines": lines, "printed_total_kg": total, "waste_pct": waste}

def software_by_group(rows: list) -> tuple:
  """rows: [{"category", "tag", "kg", "floor", "assumed"}] -> ({group: {"floors": {floor: kg}, "rows": n, "assumed": n}}, [rows with no group])."""
  out: dict = {}
  rest: dict = {}
  
  for r in rows:
    g = group_of_software(r.get("category"), r.get("tag"))
    kg = float(r.get("kg") or 0.0)
    if g is None:
      name = str(r.get("category") or r.get("tag") or "?")
      d = rest.setdefault(name, {"name": name, "rows": 0, "quantity": 0.0, "unit": "kg"})
      d["rows"] += 1
      d["quantity"] += kg
      continue
  
    slot = out.setdefault(g, {"floors": {}, "rows": 0, "assumed": 0, "tags": {}})
    fl = r.get("floor") or "OTHERS"
    slot["floors"][fl] = slot["floors"].get(fl, 0.0) + kg
    slot["rows"] += 1
    slot["assumed"] += 1 if r.get("assumed") else 0
    if r.get("tag"):
      slot["tags"][str(r["tag"])] = slot["tags"].get(str(r["tag"]), 0.0) + kg
  return out, sorted(rest.values(), key=lambda x: -x["quantity"])

def _pct(sw: float, qs: float) -> float | None:
  return round((sw - qs) / qs * 100.0, 2) if qs else None

def compare_steel(summary: dict, rows: list, tolerance_pct: float = 5.0, classes: dict | None = None) -> dict:
  """The Steel Summary against the software's steel rows. The answer has the shape of the bill comparison (lines, measures...), with the floors of each line added."""
  sw, rest = software_by_group(rows)
  
  qs: dict = {}
  for ln in summary["lines"]:
    slot = qs.setdefault(ln["group"], {"floors": {}, "rows": []})
    for f, v in ln["floors"].items():
      slot["floors"][f] = slot["floors"].get(f, 0.0) + v
    slot["rows"].append({"row": ln["row"], "section": "Steel Summary", "item": ln["item"], "unit": "kg", "quantity": round(sum(ln["floors"].values()), 3)})
  classes = classes or {}
  lines = []
  
  for key in [k for k, _, _ in GROUPS if k in qs or k in sw]:
    q, s = qs.get(key), sw.get(key)
    qs_total = sum(q["floors"].values()) if q else None
    sw_total = sum(s["floors"].values()) if s else None
    err = _pct(sw_total, qs_total) if (q and s and qs_total) else None
    floors = []
    
    for fl in FLOORS:
      a, b = (q["floors"].get(fl) if q else None), (s["floors"].get(fl) if s else None)
      if (a or 0) == 0 and (b or 0) == 0:
        continue
      floors.append({"floor": fl, "label": FLOOR_LABEL[fl], "qs": round(a, 3) if a is not None else None, "software": round(b, 3) if b is not None else None,
        "error_pct": _pct(b or 0.0, a) if a else None})
    if q is None:
      status, suggested = "EXTRA", "NEEDS_DECISION"
    elif s is None:
      status, suggested = "MISSING", ("MISSING_FEATURE" if key in NOT_BUILT else "NEEDS_DECISION")
    elif err is not None and abs(err) <= tolerance_pct:
      status, suggested = "MATCH", None
    else:
      status, suggested = "DIFF", ("CONVENTION" if s["assumed"] else "NEEDS_DECISION")
      
    user = classes.get(key) or {}
    cls = user.get("class") if user.get("class") in ("READING", "CONVENTION", "QS_ERROR", "MISSING_FEATURE", "NEEDS_DECISION") else None
    lines.append({"key": key, "label": LABEL[key], "status": status, "unit": "kg", "qs": round(qs_total, 3) if qs_total is not None else None,
      "software": round(sw_total, 3) if sw_total is not None else None, "difference": round(sw_total - qs_total, 3) if (sw_total is not None and qs_total is not None) else None,
      "error_pct": err, "suggested_class": suggested, "class": cls, "note": user.get("note") or "", "bill_rows": q["rows"] if q else [],
      "software_rows": s["rows"] if s else 0, "software_tags": [{"tag": t, "quantity": round(v, 3)} for t, v in sorted((s or {"tags": {}})["tags"].items(), key=lambda x: -x[1])[:12]],
      "floors": floors, "assumed_rows": s["assumed"] if s else 0})
    
  order = {"DIFF": 0, "MISSING": 1, "EXTRA": 2, "MATCH": 3}
  lines.sort(key=lambda x: (order[x["status"]], -abs(x["error_pct"] or 0), x["label"]))
  both = [x for x in lines if x["error_pct"] is not None]
  scoped = [x for x in lines if x["qs"] is not None]
  covered = [x for x in scoped if x["software"] is not None]
  open_diffs = [x for x in lines if x["status"] in ("DIFF", "MISSING", "EXTRA") and not x["class"]]
  qs_sum = sum(x["qs"] for x in scoped)
  sw_sum = sum(x["software"] for x in lines if x["software"] is not None)
  
  measures = {"bill_lines": len(scoped), "compared": len(both), "within_tolerance": sum(1 for x in both if abs(x["error_pct"]) <= tolerance_pct),
    "line_error_median_pct": round(median(abs(x["error_pct"]) for x in both), 2) if both else None,
    "coverage_pct": round(100.0 * len(covered) / len(scoped), 1) if scoped else None, "extra_lines": sum(1 for x in lines if x["status"] == "EXTRA"),
    "unclassified_differences": len(open_diffs)}
  return {"tolerance_pct": tolerance_pct, "lines": lines, "unmapped": [], "unclassified_software": rest[:30], "measures": measures, "bill_sheet": summary["sheet"], "bill_sheets": [summary["sheet"]],
    "software_rows": len(rows), "totals": {"qs_kg": round(qs_sum, 3), "software_kg": round(sw_sum, 3), "qs_printed_kg": summary.get("printed_total_kg"), "waste_pct": summary.get("waste_pct"),
      "qs_with_waste_kg": round(qs_sum * (1 + (summary.get("waste_pct") or 5.0) / 100.0), 3)}}
