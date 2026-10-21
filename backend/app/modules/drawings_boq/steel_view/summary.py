from __future__ import annotations
from decimal import Decimal, InvalidOperation
from app.modules.drawings_boq.steel_view.allowances import allowances_of

STEEL_ITEM = "STL-REBAR"
FORMULA_PRINTED, FORMULA_BBS, FORMULA_RULE = "PDF_MEMBER_STEEL_WEIGHT", "REBAR_BBS_WEIGHT", "REBAR_RULE_ESTIMATE"
ESTIMATE_RECIPE = "PDF_MEMBER_STEEL_ESTIMATE"
STEEL_FORMULAS = (FORMULA_PRINTED, FORMULA_BBS, FORMULA_RULE)
PRINTED, SCHEDULE, ESTIMATE_PDF, ESTIMATE_MODEL = "PRINTED", "SCHEDULE", "ESTIMATE_PDF", "ESTIMATE_MODEL"
BASIS_ORDER = (PRINTED, SCHEDULE, ESTIMATE_PDF, ESTIMATE_MODEL)
INTENSITY_FAMILY = {"LINTEL": "BEAM", "BEAM": "BEAM", "COLUMN": "COLUMN", "FOOTING": "FOOTING", "SLAB": "SLAB", "CHAJJA": "SLAB", "BALCONY_SLAB": "SLAB"}
USUAL_RANGE = {"SLAB": (55.0, 78.5), "BEAM": (78.5, 157.0), "COLUMN": (78.5, 392.0), "FOOTING": (50.0, 100.0)}
FAMILY_LABEL = {"LINTEL": "Lintels", "BEAM": "Beams", "COLUMN": "Columns", "FOOTING": "Footings", "SLAB": "Slabs", "RCC_WALL": "RCC walls", "STAIR": "Stairs",
  "TANK": "Tanks", "PARAPET": "Parapets", "CHAJJA": "Chajjas", "BALCONY_SLAB": "Balcony slabs", "OTHER": "Other members"}
FAMILY_ALIAS = {"WALL": "RCC_WALL", "RCC WALL": "RCC_WALL", "STAIRCASE": "STAIR", "STAIRS": "STAIR", "SLABS": "SLAB", "BEAMS": "BEAM", "COLUMNS": "COLUMN", "FOOTINGS": "FOOTING"}
MARK_CAP = 4000
BASIS_WORDS = {PRINTED: "Bars printed on the drawing", SCHEDULE: "Bar bending schedule", ESTIMATE_PDF: "Estimated from the size (no bars printed)", ESTIMATE_MODEL: "Estimated from the model's concrete volume"}

def dec(value, default: Decimal = Decimal("0")) -> Decimal:
  try:
    return Decimal(str(value))
  except (InvalidOperation, ValueError, TypeError):
    return default

def r3(value: Decimal) -> float:
  return float(round(value, 3))

def family_of(raw) -> str:
  text = str(raw or "").strip().upper().replace("-", "_")
  text = FAMILY_ALIAS.get(text, text)
  return text if text in FAMILY_LABEL else (text or "OTHER")

def label_of(family: str) -> str:
  return FAMILY_LABEL.get(family) or family.replace("_", " ").capitalize()

def _lines(source: dict) -> list:
  out = []
  for ln in source.get("lines") or []:
    if isinstance(ln, dict) and ln.get("dia_mm") is not None:
      out.append((str(dec(ln["dia_mm"]).normalize()), dec(ln.get("kg")), dec(ln.get("length_m"))))
  return out

def member_of(row: dict, wastage_pct=None) -> dict | None:
  formula = row.get("formula")
  trace = row.get("trace") or {}
  inputs = trace.get("inputs") or {}
  net = trace.get("net") or {}
  kg_row = dec(row.get("quantity"))
  out = {"row_id": row.get("id"), "level": row.get("level") or "", "element": row.get("element") or "", "warnings": row.get("warnings") or [], "count": 1,
    "wastage_pct": None, "bare_kg": None, "concrete_m3": None, "kg_low": None, "kg_high": None, "tag": "", "page": None, "dia": []}
  
  if formula == FORMULA_PRINTED:
    src = inputs.get("steel_source") or {}
    estimate = inputs.get("recipe") == ESTIMATE_RECIPE
    bare = dec(src.get("bare_kg")) if src.get("bare_kg") is not None else None
    as_run = dec(src.get("wastage_pct"))
    applied = as_run if wastage_pct is None else dec(wastage_pct)
    kg = kg_row
    low, high = dec(net.get("kg_low"), kg_row) if net.get("kg_low") is not None else None, dec(net.get("kg_high"), kg_row) if net.get("kg_high") is not None else None
    if bare is not None and bare > 0:
      kg = bare * (1 + applied / 100)
      if estimate and low is not None and high is not None and kg_row > 0:
        scale = kg / kg_row
        low, high = low * scale, high * scale
        
    dia = []
    lines = _lines(src)
    total_lines = sum((k for _, k, _ in lines), Decimal("0"))
    if not estimate and lines and total_lines > 0:
      scale = kg / total_lines
      by: dict = {}
      
      for d, k, length in lines:
        slot = by.setdefault(d, [Decimal("0"), Decimal("0")])
        slot[0] += k * scale
        slot[1] += length
      dia = [(d, v[0], v[1]) for d, v in by.items()]
    out.update({"family": family_of(src.get("category")), "basis": ESTIMATE_PDF if estimate else PRINTED, "tag": str(src.get("tag") or ""), "page": src.get("page_no"),
      "kg": kg, "bare_kg": bare, "wastage_pct": applied, "concrete_m3": dec(src.get("concrete_m3")) if src.get("concrete_m3") is not None else None,
      "kg_low": low, "kg_high": high, "dia": dia, "as_run_wastage_pct": as_run, "keeps_bare": bare is not None and bare > 0})
    return out

  if formula in (FORMULA_BBS, FORMULA_RULE):
    label = str(trace.get("label") or "")
    fam = family_of(label.split(" ", 1)[1] if " " in label else None)
    by = {}
    marks = []
    
    for st in trace.get("steps") or []:
      if isinstance(st, dict) and st.get("op") == "bar_mark" and st.get("dia_mm") is not None:
        d = str(dec(st["dia_mm"]).normalize())
        slot = by.setdefault(d, [Decimal("0"), Decimal("0")])
        slot[0] += dec(st.get("kg"))
        marks.append(str(st.get("mark") or ""))
        
    total_marks = sum((v[0] for v in by.values()), Decimal("0"))
    scale = kg_row / total_marks if total_marks > 0 else Decimal("1")
    out.update({"family": fam, "basis": SCHEDULE if formula == FORMULA_BBS else ESTIMATE_MODEL, "tag": out["element"] or (marks[0] if marks else ""), "kg": kg_row,
      "kg_low": dec(net.get("kg_low")) if net.get("kg_low") is not None else None, "kg_high": dec(net.get("kg_high")) if net.get("kg_high") is not None else None,
      "dia": [(d, v[0] * scale, v[1]) for d, v in by.items()], "keeps_bare": False, "as_run_wastage_pct": None})
    return out
  return None

def _blank(): 
  return {"members": 0, "kg": Decimal("0"), "kg_low": Decimal("0"), "kg_high": Decimal("0")}

def summarise(rows, wastage_pct=None, allowances=()) -> dict:
  members = [m for m in (member_of(r, wastage_pct) for r in rows) if m is not None]
  by_dia: dict = {}
  by_family: dict = {}
  by_basis = {b: _blank() for b in BASIS_ORDER}
  marks: dict = {}
  spread_none = {"kg": Decimal("0"), "members": 0}
  as_run, affected, fixed = set(), 0, 0
  
  for m in members:
    kg = m["kg"]
    low, high = (m["kg_low"] if m["kg_low"] is not None else kg), (m["kg_high"] if m["kg_high"] is not None else kg)
    b = by_basis[m["basis"]]
    b["members"] += 1; b["kg"] += kg; b["kg_low"] += low; b["kg_high"] += high
    fam = by_family.setdefault(m["family"], {**_blank(), "volume_m3": Decimal("0"), "volume_kg": Decimal("0"), "volume_members": 0, "basis": {}, "bare_kg": Decimal("0")})
    fam["members"] += 1; fam["kg"] += kg; fam["kg_low"] += low; fam["kg_high"] += high
    fam["basis"][m["basis"]] = fam["basis"].get(m["basis"], Decimal("0")) + kg
    if m["bare_kg"] is not None:
      fam["bare_kg"] += m["bare_kg"]
    if m["concrete_m3"] is not None and m["concrete_m3"] > 0:
      fam["volume_m3"] += m["concrete_m3"]; fam["volume_kg"] += kg; fam["volume_members"] += 1
    if m.get("keeps_bare"):
      affected += 1
      as_run.add(m["as_run_wastage_pct"])
      
    else:
      fixed += 1
    if m["dia"]:
      for d, k, length in m["dia"]:
        slot = by_dia.setdefault(d, {"kg": Decimal("0"), "length_m": Decimal("0"), "members": 0, "by_family": {}})
        slot["kg"] += k; slot["length_m"] += length; slot["members"] += 1
        slot["by_family"][m["family"]] = slot["by_family"].get(m["family"], Decimal("0")) + k
    else:
      spread_none["kg"] += kg; spread_none["members"] += 1
    key = (m["family"], m["tag"] or m["element"] or "(no mark)", m["level"], m["basis"])
    mk = marks.setdefault(key, {"family": m["family"], "tag": key[1], "level": m["level"], "basis": m["basis"], "count": 0, "kg": Decimal("0"), "kg_low": Decimal("0"),
      "kg_high": Decimal("0"), "bare_kg": Decimal("0"), "has_bare": False, "concrete_m3": Decimal("0"), "page": m["page"], "dia": {}, "warnings": set()})
    mk["count"] += 1; mk["kg"] += kg; mk["kg_low"] += low; mk["kg_high"] += high
    if m["bare_kg"] is not None:
      mk["bare_kg"] += m["bare_kg"]; mk["has_bare"] = True
    if m["concrete_m3"] is not None:
      mk["concrete_m3"] += m["concrete_m3"]
    for d, k, _ in m["dia"]:
      mk["dia"][d] = mk["dia"].get(d, Decimal("0")) + k
    for w in m["warnings"]:
      mk["warnings"].add(w if isinstance(w, str) else str((w or {}).get("code") or ""))
      
  total = sum((b["kg"] for b in by_basis.values()), Decimal("0"))
  low_total = sum((b["kg_low"] for b in by_basis.values()), Decimal("0"))
  high_total = sum((b["kg_high"] for b in by_basis.values()), Decimal("0"))
  estimated = by_basis[ESTIMATE_PDF]["kg"] + by_basis[ESTIMATE_MODEL]["kg"]
  spread_total = sum((v["kg"] for v in by_dia.values()), Decimal("0"))
  dia_rows = []
  for d in sorted(by_dia, key=lambda x: Decimal(x)):
    v = by_dia[d]
    dia_rows.append({"dia_mm": float(Decimal(d)), "kg": r3(v["kg"]), "length_m": r3(v["length_m"]), "members": v["members"],
      "share_pct": r3(v["kg"] / spread_total * 100) if spread_total > 0 else 0.0,
      "by_family": {f: r3(k) for f, k in sorted(v["by_family"].items(), key=lambda kv: -kv[1])}})
    
  fam_rows = []
  for f, v in sorted(by_family.items(), key=lambda kv: -kv[1]["kg"]):
    band = USUAL_RANGE.get(INTENSITY_FAMILY.get(f, ""))
    per = v["volume_kg"] / v["volume_m3"] if v["volume_m3"] > 0 else None
    status = None
    
    if per is not None and band is not None:
      status = "BELOW_RANGE" if float(per) < band[0] else "ABOVE_RANGE" if float(per) > band[1] else "IN_RANGE"
    fam_rows.append({"family": f, "label": label_of(f), "members": v["members"], "kg": r3(v["kg"]), "kg_low": r3(v["kg_low"]), "kg_high": r3(v["kg_high"]),
      "bare_kg": r3(v["bare_kg"]) if v["bare_kg"] > 0 else None,
      "concrete_m3": r3(v["volume_m3"]) if v["volume_m3"] > 0 else None, "kg_per_m3": r3(per) if per is not None else None,
      "intensity_from": v["volume_members"], "range": list(band) if band else None, "status": status,
      "by_basis": {b: r3(k) for b, k in v["basis"].items()}})
    
  mark_rows = []
  for key in sorted(marks, key=lambda k: (k[0], k[2], k[1], k[3])):
    mk = marks[key]
    mark_rows.append({"family": mk["family"], "tag": mk["tag"], "level": mk["level"], "basis": mk["basis"], "count": mk["count"], "kg": r3(mk["kg"]),
      "kg_each": r3(mk["kg"] / mk["count"]), "kg_low": r3(mk["kg_low"]), "kg_high": r3(mk["kg_high"]), "bare_kg": r3(mk["bare_kg"]) if mk["has_bare"] else None,
      "concrete_m3": r3(mk["concrete_m3"]) if mk["concrete_m3"] > 0 else None,
      "kg_per_m3": r3(mk["kg"] / mk["concrete_m3"]) if mk["concrete_m3"] > 0 else None, "page": mk["page"],
      "dia": {d: r3(k) for d, k in sorted(mk["dia"].items(), key=lambda kv: Decimal(kv[0]))}, "warnings": sorted(w for w in mk["warnings"] if w)})
    
  truncated = len(mark_rows) > MARK_CAP
  runs_at = sorted(float(p) for p in as_run)
  return {"wastage": {"as_run_pct": runs_at, "applied_pct": None if wastage_pct is None else float(dec(wastage_pct)), "rows_with_bare_weight": affected, "rows_fixed": fixed},
    "totals": {"members": len(members), "kg": r3(total), "kg_low": r3(low_total), "kg_high": r3(high_total), "estimated_kg": r3(estimated),
      "estimated_share_pct": r3(estimated / total * 100) if total > 0 else 0.0,
      "by_basis": {b: {"members": by_basis[b]["members"], "kg": r3(by_basis[b]["kg"])} for b in BASIS_ORDER if by_basis[b]["members"]}},
    "by_diameter": dia_rows, "without_diameter": {"kg": r3(spread_none["kg"]), "members": spread_none["members"]},
    "by_family": fam_rows, "marks": mark_rows[:MARK_CAP], "marks_truncated": truncated, "marks_total": len(mark_rows),
    "allowances": allowances_of(allowances, total)}
