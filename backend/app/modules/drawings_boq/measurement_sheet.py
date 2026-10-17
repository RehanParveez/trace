from __future__ import annotations
from decimal import Decimal

ZERO = Decimal("0")
MM_PER_M = Decimal("1000")
Q6 = Decimal("0.000001")

def _d(v) -> Decimal | None:
  try:
    return Decimal(str(v))
  except Exception:
    return None

def _q(v: Decimal) -> Decimal:
  return v.quantize(Q6)

def _m(inputs: dict, key: str) -> Decimal | None:
  v = _d(inputs.get(key))
  return None if v is None else v / MM_PER_M

def line(nos=None, length=None, breadth=None, height=None, quantity=None, remark: str = "", kind: str = "line", **extra) -> dict:
  """kind: line | less | total. Dimensions are Decimals in metres (nos is an int or None), quantity a Decimal in the unit of the sheet."""
  return {"nos": nos, "length": length, "breadth": breadth, "height": height, "quantity": quantity, "remark": remark, "kind": kind, **extra}

def _step_value(step: dict, unit: str) -> Decimal | None:
  return _d(step.get(unit))

def _pdf_sheet(trace: dict, unit: str, quantity: Decimal) -> list:
  inp = trace.get("inputs") or {}
  steps = trace.get("steps") or []
  mode = inp.get("quantity_mode")
  repeat = int(inp.get("repeat") or 1)
  
  count = next((int(Decimal(s["nos"])) for s in steps if s.get("op") == "count"), None)
  length_m = _d(inp.get("length_m"))
  thickness = _m(inp, "thickness_mm")
  height = _m(inp, "height_mm")
  width = _m(inp, "width_mm")
  depth = _m(inp, "depth_mm")
  mark_len = _m(inp, "length_mm")
  gross_area = next((_d(s.get("m2")) for s in steps if s.get("op") == "gross_area"), None)
  
  rows: list = []
  nos = (count or 1) * repeat if inp.get("kind") == "COUNT" else repeat
  scale = thickness if mode in ("LENGTH_X_HEIGHT_X_THICKNESS", "AREA_X_THICKNESS") and thickness is not None else Decimal("1")
  
  if mode == "DIRECT" and inp.get("kind") == "COUNT":
    rows.append(line(nos=nos, quantity=Decimal(nos), remark="counted on the drawing"))
  elif mode == "DIRECT" and inp.get("kind") == "LENGTH":
    rows.append(line(nos=nos, length=length_m, quantity=_q(length_m * nos) if length_m is not None else None, remark="traced on the drawing"))
  elif mode == "DIRECT":
    rows.append(line(nos=nos, quantity=_q((gross_area or ZERO) * nos), remark="area traced on the drawing"))
  elif mode == "LENGTH_X_HEIGHT":
    rows.append(line(nos=nos, length=length_m, height=height, quantity=_q((length_m or ZERO) * (height or ZERO) * nos)))
  elif mode == "LENGTH_X_HEIGHT_X_THICKNESS":
    first = next((_d(s.get("m2")) for s in steps if s.get("op") == "multiply" and s.get("by") == "height_mm"), None)
    rows.append(line(nos=nos, length=length_m, breadth=thickness, height=height, quantity=_q((first or ZERO) * (thickness or ZERO) * nos)))
  elif mode == "LENGTH_X_SECTION":
    rows.append(line(nos=nos, length=length_m, breadth=width, height=depth, quantity=_q((length_m or ZERO) * (width or ZERO) * (depth or ZERO) * nos)))
  elif mode == "AREA_X_THICKNESS":
    rows.append(line(nos=nos, height=thickness, quantity=_q((gross_area or ZERO) * (thickness or ZERO) * nos),
      remark=f"plan area {_q(gross_area or ZERO)} m2 traced on the drawing"))
  elif mode == "COUNT_X_LENGTH":
    rows.append(line(nos=nos, length=mark_len, quantity=_q(Decimal(nos) * (mark_len or ZERO))))
  elif mode == "COUNT_X_AREA":
    rows.append(line(nos=nos, length=mark_len, breadth=_m(inp, "width_mm"), quantity=_q(Decimal(nos) * (mark_len or ZERO) * (width or ZERO))))
  elif mode == "COUNT_X_VOLUME":
    rows.append(line(nos=nos, length=mark_len, breadth=width, height=depth, quantity=_q(Decimal(nos) * (mark_len or ZERO) * (width or ZERO) * (depth or ZERO))))
  else:
    rows.append(line(nos=nos, quantity=quantity, remark="see the working"))

  for s in steps:
    op = s.get("op")
    if op == "deduction":
      cut = _d(s.get("m2")) or ZERO
      rows.append(line(nos=repeat if repeat > 1 else None, quantity=-_q(cut * scale * repeat), kind="less", remark=str(s.get("note") or s.get("type") or "deduction")))
    elif op == "adjustment":
      v = _step_value(s, unit) or ZERO
      sign = Decimal(1) if s.get("type") == "ADD" else Decimal(-1)
      rows.append(line(nos=repeat if repeat > 1 else None, quantity=sign * _q(v * repeat), kind="line" if sign > 0 else "less",
        remark=str(s.get("note") or ("added" if sign > 0 else "deducted"))))
  return rows

def _formwork_sheet(trace: dict, unit: str, quantity: Decimal) -> list:
  src = ((trace.get("inputs") or {}).get("formwork_source")) or {}
  size = src.get("size_mm") or []
  rows: list = []
  
  if len(size) == 3:
    rows.append(line(nos=1, length=_d(size[0]) / MM_PER_M, breadth=_d(size[1]) / MM_PER_M, height=_d(size[2]) / MM_PER_M, kind="line",
      remark=f"{src.get('category', '')} {src.get('tag') or ''} size".strip() + (f", mark {src.get('instance')} of {src.get('instances')}" if src.get("instances") else "")))
  shared = {(f.get("face"), f.get("by")): f for f in src.get("shared_faces") or []}
  for s in trace.get("steps") or []:
    if s.get("op") == "face":
      rows.append(line(nos=1, quantity=_d(s.get("m2")), remark=f"{s.get('name')} face"))
  for f in shared.values():
    rows.append(line(quantity=None, kind="line", remark=f"{f.get('face')} shared with {f.get('by')}: {f.get('m2')} m2 counted once"))
  return rows

def _steel_sheet(trace: dict, unit: str, quantity: Decimal) -> list:
  src = ((trace.get("inputs") or {}).get("steel_source")) or {}
  rows: list = []
  
  for ln in src.get("lines") or []:
    bar = f"dia {ln.get('dia_mm')} mm {ln.get('role') or ln.get('kind') or ''}".strip()
    rows.append(line(nos=int(ln["count"]) if ln.get("count") is not None else None, length=_d(ln.get("cut_length_m")), quantity=_d(ln.get("kg")),
      remark=f"{bar} x {ln.get('kg_per_m')} kg per m", dia_mm=str(ln.get("dia_mm")), run_m=_d(ln.get("length_m"))))
  pct = _d(src.get("wastage_pct")) or ZERO
  bare = _d(src.get("bare_kg")) or ZERO
  if pct:
    rows.append(line(quantity=_q(bare * pct / Decimal(100)), remark=f"wastage {pct}% on {bare} kg", wastage=True))
  return rows

def _model_sheet(trace: dict, unit: str, quantity: Decimal) -> list:
  rows: list = []
  
  for s in trace.get("steps") or []:
    op = s.get("op") or ""
    v = _d(s.get("m3") or s.get("m2") or s.get("m") or s.get("kg") or s.get("nos"))
    if op.startswith("gross"):
      rows.append(line(quantity=v, remark=op.replace("_", " ")))
    elif op == "deduction":
      rows.append(line(quantity=-abs(v) if v is not None else None, kind="less", remark=" ".join(x for x in (str(s.get("type") or ""), str(s.get("note") or s.get("rule") or "")) if x)))
    elif op == "count":
      rows.append(line(nos=int(Decimal(s["nos"])), remark="count"))
    elif op == "bar_mark":
      rows.append(line(nos=int(s["count"]) if s.get("count") is not None else None, quantity=_d(s.get("kg")), remark=f"bar {s.get('mark')} dia {s.get('dia_mm')} mm"))
    elif op == "schedule_quantity":
      rows.append(line(quantity=v, remark="from the schedule"))
  return rows

def sheet_for(trace: dict | None, unit: str, quantity, label: str = "") -> dict:
  """The measurement sheet of one ledger row: {"layout", "label", "unit", "lines", "net"}. The last line is the total, taken from the row's own quantity."""
  trace = trace or {}
  q = _d(quantity) or ZERO
  inputs = trace.get("inputs") or {}
  
  code = str(trace.get("formula_code") or "")
  if code.startswith("PDF_TAKEOFF") and inputs.get("quantity_mode"):
    layout, lines = "pdf", _pdf_sheet(trace, unit, q)
  elif "formwork_source" in inputs:
    layout, lines = "formwork", _formwork_sheet(trace, unit, q)
  elif "steel_source" in inputs:
    layout, lines = "steel", _steel_sheet(trace, unit, q)
  else:
    layout, lines = "model", _model_sheet(trace, unit, q)
  lines.append(line(quantity=q, kind="total", remark=f"net, {unit}"))
  return {"layout": layout, "label": label or str(trace.get("label") or ""), "unit": unit, "lines": lines, "net": q}

def lines_sum(sheet: dict) -> Decimal:
  return sum((l["quantity"] for l in sheet["lines"] if l["kind"] != "total" and l["quantity"] is not None), ZERO)

def fmt_dim(v) -> str:
  return "" if v is None else f"{Decimal(v):.3f}"

def fmt_qty(v) -> str:
  return "" if v is None else f"{Decimal(v):,.3f}"

def steel_by_diameter(sheets: list) -> dict:
  by: dict = {}
  wastage = ZERO
  for sh in sheets:
    if sh.get("layout") != "steel":
      continue
  
    for l in sh["lines"]:
      if l.get("wastage"):
        wastage += l["quantity"] or ZERO
      elif l.get("dia_mm") and l["quantity"] is not None:
        slot = by.setdefault(l["dia_mm"], {"length_m": ZERO, "kg": ZERO})
        slot["length_m"] += l.get("run_m") or ZERO
        slot["kg"] += l["quantity"]
  rows = [{"dia_mm": d, "length_m": _q(v["length_m"]), "kg": _q(v["kg"])} for d, v in sorted(by.items(), key=lambda kv: (_d(kv[0]) or ZERO))]
  return {"rows": rows, "wastage_kg": _q(wastage), "total_kg": _q(sum((r["kg"] for r in rows), ZERO) + wastage)}
