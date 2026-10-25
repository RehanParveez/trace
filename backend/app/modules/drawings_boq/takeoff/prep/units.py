from __future__ import annotations
import re

FEET_INCH = re.compile(r"\d+\s*['’′]\s*-\s*\d+")
INCH = re.compile(r"\d+(?:\.\d+)?\s*[\"”]")
METRIC = re.compile(r"\b\d{2,5}\s*mm\b", re.I)
MIN_FEET_INCH = 4
VOCAB_TOL = 0.15
GRID_TOL = 0.06
GRID_IN = 0.5
IMPERIAL_HINTS = ("ft", "ft-in")
METRIC_HINTS = ("mm", "cm", "m")
MIN_VOCAB_WALLS = 2
MM = 25.4

def count_words(words: list) -> dict:
  """What one sheet's text says about units: {"feet_inch", "inch", "metric"} counts of words such as 13'-6", 9" and 230 mm."""
  fi = inch = metric = 0
  for w in words or []:
    t = getattr(w, "text", None) or ""
    if FEET_INCH.search(t):
      fi += 1
    elif INCH.search(t):
      inch += 1
    if METRIC.search(t):
      metric += 1
  return {"feet_inch": fi, "inch": inch, "metric": metric}

def drawing_imperial(sheets: list) -> dict:
  hints = {s.get("hint") for s in sheets if s.get("hint")}
  imp_hint = any(h in IMPERIAL_HINTS for h in hints)
  met_hint = any(h in METRIC_HINTS for h in hints)
  if imp_hint and not met_hint:
    return {"imperial": True, "basis": "NOTE", "pages": [s["page_no"] for s in sheets if s.get("hint") in IMPERIAL_HINTS]}
  if met_hint and not imp_hint:
    return {"imperial": False, "basis": "NOTE", "pages": [s["page_no"] for s in sheets if s.get("hint") in METRIC_HINTS]}
  counted = [s for s in sheets if s.get("units")]
  
  fi = sum(int(s["units"].get("feet_inch") or 0) for s in counted)
  inch = sum(int(s["units"].get("inch") or 0) for s in counted)
  metric = sum(int(s["units"].get("metric") or 0) for s in counted)
  if imp_hint and met_hint:
    return {"imperial": None, "basis": "NOTES_DISAGREE", "pages": []}
  if fi >= MIN_FEET_INCH and (fi + inch) > metric:
    return {"imperial": True, "basis": "DIMENSIONS", "pages": [s["page_no"] for s in counted if (s["units"].get("feet_inch") or 0) > 0]}
  if metric >= MIN_FEET_INCH and metric > fi + inch:
    return {"imperial": False, "basis": "DIMENSIONS", "pages": [s["page_no"] for s in counted if (s["units"].get("metric") or 0) > 0]}
  return {"imperial": None, "basis": "TOO_FEW", "pages": []}

def sheet_imperial(counts: dict | None, hint: str | None, drawing: dict) -> dict:
  """Whether this one sheet is dimensioned in feet and inches, from its own text: {"imperial", "basis", "differs"}. A note on the sheet decides first, then the
  count of its labels, as for the drawing. When the sheet's text does not decide, the answer of the drawing stands. A sheet that differs from its drawing is
  allowed and flagged ("differs")."""
  c = counts or {}
  fi, inch, metric = int(c.get("feet_inch") or 0), int(c.get("inch") or 0), int(c.get("metric") or 0)
  own, basis = None, None
  if hint in IMPERIAL_HINTS:
    own, basis = True, "NOTE"
  elif hint in METRIC_HINTS:
    own, basis = False, "NOTE"
  elif fi >= MIN_FEET_INCH and (fi + inch) > metric:
    own, basis = True, "DIMENSIONS"
  elif metric >= MIN_FEET_INCH and metric > fi + inch:
    own, basis = False, "DIMENSIONS"
  if own is None:
    return {"imperial": drawing.get("imperial"), "basis": drawing.get("basis"), "differs": False}
  return {"imperial": own, "basis": basis, "differs": drawing.get("imperial") is not None and own != drawing.get("imperial")}

def wall_vocabulary(rows: list, imperial: bool | None) -> list:
  count: dict = {}
  for used, std, composite in rows:
    if composite or not std or not used:
      continue
    count[round(float(used), 1)] = count.get(round(float(used), 1), 0) + 1
  return sorted(t for t, n in count.items() if n >= MIN_VOCAB_WALLS)

def grid_mm(t_mm: float) -> float | None:
  """The nearest half inch, when the measurement is within a few per cent of it."""
  inches = t_mm / MM
  g = round(inches / GRID_IN) * GRID_IN
  if g <= 0:
    return None
  return round(g * MM, 1) if abs(inches - g) / g <= GRID_TOL else None

def snap_wall(t_mm: float, imperial: bool, vocab: list | None, standard_imperial: tuple, standard_metric_fn) -> tuple:
  if not imperial:
    std = standard_metric_fn(t_mm)
    return (std, float(std)) if std is not None else (None, float(round(t_mm / 5.0) * 5))
  if vocab:
    near = min(vocab, key=lambda s: abs(t_mm / s - 1.0))
    if abs(t_mm / near - 1.0) <= VOCAB_TOL:
      return near, near
  
  best = min(standard_imperial, key=lambda s: abs(t_mm / s - 1.0))
  if abs(t_mm / best - 1.0) <= 0.06:
    return best, best
  g = grid_mm(t_mm)
  if g is not None:
    return g, g
  return None, float(round(t_mm / 5.0) * 5)
