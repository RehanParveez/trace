from __future__ import annotations
from decimal import Decimal
from app.engine.measure.stages import stage_label

NO_RANGE = "no range"
NOT_GRADED = "not graded"

def _num(v):
  try:
    return float(Decimal(str(v)))
  except Exception:
    return None

def stage_text(r: dict) -> str:
  return stage_label(r.get("work_stage")) or ""

def range_pair(r: dict) -> tuple:
  """(low, high) of the quantity, or (None, None) when the row carries no range."""
  qr = r.get("quantity_range")
  if not qr:
    return None, None
  return _num(qr.get("low")), _num(qr.get("high"))

def grade_text(r: dict) -> str:
  qr = r.get("quantity_range")
  return (qr.get("weakest") or "") if qr else NOT_GRADED

def range_text(r: dict, fmt=lambda v: f"{v:,.4f}") -> str:
  low, high = range_pair(r)
  if low is None or high is None:
    return NO_RANGE
  text = f"{fmt(low)} to {fmt(high)} {r.get('unit') or ''}".strip()
  qr = r.get("quantity_range") or {}
  if qr.get("unbounded_rows"):
    text += " (a minimum: some inputs have no range)"
  return text

def note_line(r: dict) -> str:
  """One small line for a printed table: Stage · Range · Grade, leaving out the stage when the row has none."""
  bits = ([f"Stage: {stage_text(r)}"] if stage_text(r) else []) + [f"Range: {range_text(r)}", f"Grade: {grade_text(r) or '-'}"]
  return " | ".join(bits)

def head_cells() -> list:
  return ["Stage", "Range low", "Range high", "Grade"]

def cells(r: dict) -> list:
  low, high = range_pair(r)
  return [stage_text(r), low, high, grade_text(r)]

def steel_table(by_dia: dict | None) -> list:
  if not by_dia or not by_dia.get("rows"):
    return []
  out = [["Diameter (mm)", "Length (m)", "Weight (kg)"]]
  out += [[r["dia_mm"], float(r["length_m"]), float(r["kg"])] for r in by_dia["rows"]]
  out += [["Wastage", None, float(by_dia["wastage_kg"])], ["Total", None, float(by_dia["total_kg"])]]
  return out

def steel_table_text(by_dia: dict | None) -> list:
  return [[("" if v is None else (f"{v:,.2f}" if isinstance(v, float) else str(v))) for v in row] for row in steel_table(by_dia)]
