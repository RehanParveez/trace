from __future__ import annotations
import math
import re
from collections import Counter

MM_INCH = 25.4
MM_FOOT = 304.8
RISER_MM = (100.0, 230.0)
TREAD_MM = (200.0, 400.0)
WIDTH_MM = (600.0, 3000.0)
WAIST_MM = (75.0, 250.0)
STEPS = (3, 40)

_FRACTIONS = {"½": " 1/2", "¼": " 1/4", "¾": " 3/4"}
_IN = r"(?P<in>\d{1,3}(?:\s+\d{1,2}\s*/\s*\d{1,2}|\s*/\s*\d{1,2})?)\s*(?:\"|″|”|''|’’)"
_MM = r"(?P<mm>\d{2,4})\s*(?:MM|mm)\b"
_VAL = r"(?:" + _IN + r"|" + _MM + r")"
_RISER = re.compile(r"\bRISERS?\s*(?:HEIGHT)?\s*[:=]\s*" + _VAL, re.I)
_TREAD = re.compile(r"\bTREADS?\s*(?:WIDTH)?\s*[:=]\s*" + _VAL, re.I)
_WIDTH = re.compile(r"\bSTAIR(?:CASE)?\s+WIDTH\s*[:=]\s*(?:(?P<ft>\d{1,2})\s*['’′]\s*-?\s*(?P<in>\d{1,2}(?:\s+\d/\d)?)?\s*(?:\"|″|”|'')?|" + _MM + r")", re.I)
_STEPS = re.compile(r"\bNO\.?\s*-?\s*OF\s*(?P<what>STEPS|RISERS?|TREADS?)\s*[:=]?\s*(?P<n>\d{1,2})\b", re.I)
_STEPS_B = re.compile(r"\b(?P<n>\d{1,2})\s*(?P<what>STEPS|RISERS)\b", re.I)
_STEPS_C = re.compile(r"\b(?P<what>STEPS)\s*[:=]\s*(?P<n>\d{1,2})\b", re.I)
_WAIST_A = re.compile(r"\bWAIST(?:\s+SLAB)?\s*(?:THK\.?|THICK(?:NESS)?)?\s*[:=]?\s*" + _VAL, re.I)
_WAIST_B = re.compile(_VAL + r"\s*(?:THK\.?|THICK)\s+WAIST", re.I)
_LABEL = re.compile(r"^\W*STAIR(?:S|CASE|\s+CASE)?(?:\s+(?:UP|DN|DOWN))?\W*$", re.I)

def _fix(text: str) -> str:
  s = text
  for k, v in _FRACTIONS.items():
    s = s.replace(k, v)
  return re.sub(r"\s+", " ", s).strip()

def _inch_mm(s: str) -> float | None:
  s = (s or "").strip()
  m = re.fullmatch(r"(\d{1,3})(?:\s+(\d{1,2})\s*/\s*(\d{1,2}))?", s)
  if m:
    whole = float(m.group(1))
    if m.group(2):
      if int(m.group(3)) == 0:
        return None
      whole += int(m.group(2)) / int(m.group(3))
    return whole * MM_INCH
  m = re.fullmatch(r"(\d{1,2})\s*/\s*(\d{1,2})", s)
  if m and int(m.group(2)) != 0:
    return int(m.group(1)) / int(m.group(2)) * MM_INCH
  return None

def _mm(m) -> float | None:
  if m.groupdict().get("mm"):
    return float(m.group("mm"))
  return _inch_mm(m.group("in"))

def _within(v: float | None, bounds: tuple) -> float | None:
  if v is None or not bounds[0] <= v <= bounds[1]:
    return None
  return round(v, 1)

def read_line(text: str) -> dict:
  """What one line of drawing text states about a staircase. Most lines state nothing."""
  t = _fix(text)
  out: dict = {}
  m = _RISER.search(t)
  if m and _within(_mm(m), RISER_MM):
    out["riser_mm"] = _within(_mm(m), RISER_MM)
  m = _TREAD.search(t)
  if m and _within(_mm(m), TREAD_MM):
    out["tread_mm"] = _within(_mm(m), TREAD_MM)
  m = _WIDTH.search(t)
  
  if m:
    if m.group("mm"):
      width = float(m.group("mm"))
    else:
      inch = _inch_mm(m.group("in")) if m.group("in") else 0.0
      width = int(m.group("ft")) * MM_FOOT + (inch or 0.0)
    if _within(width, WIDTH_MM):
      out["width_mm"] = _within(width, WIDTH_MM)
  m = _STEPS.search(t) or _STEPS_B.search(t) or _STEPS_C.search(t)
  if m:
    n = int(m.group("n"))
    if m.group("what").upper().startswith("TREAD"):
      n += 1
    if STEPS[0] <= n <= STEPS[1]:
      out["steps"] = n
  m = _WAIST_A.search(t) or _WAIST_B.search(t)
  if m and _within(_mm(m), WAIST_MM):
    out["waist_mm"] = _within(_mm(m), WAIST_MM)
  return out

def read_stair_spec(lines: list) -> dict | None:
  """The staircase described on a sheet: riser, tread, width, number of steps and (when printed) the waist slab. A value printed twice is read once; when two
  different values are printed for the same item the more often printed one is used. A sheet that prints a riser and a tread is taken as describing a stair."""
  votes: dict = {}
  for ln in lines:
    found = read_line(getattr(ln, "text", ln))
    for k, v in found.items():
      votes.setdefault(k, Counter())[v] += 1
  if "riser_mm" not in votes or "tread_mm" not in votes:
    return None
  spec = {k: c.most_common(1)[0][0] for k, c in votes.items()}
  spec["text"] = stair_text(spec)
  return spec

def stair_text(spec: dict) -> str:
  parts = []
  if spec.get("steps"):
    parts.append(f"{spec['steps']} steps")
  if spec.get("riser_mm"):
    parts.append(f"riser {spec['riser_mm']:g} mm")
  if spec.get("tread_mm"):
    parts.append(f"tread {spec['tread_mm']:g} mm")
  if spec.get("width_mm"):
    parts.append(f"width {spec['width_mm']:g} mm")
  if spec.get("waist_mm"):
    parts.append(f"waist {spec['waist_mm']:g} mm")
  return ", ".join(parts)

RISE_TOL = 0.03

def rise_check(spec: dict, way: str | None, level_hint: str | None, floor_heights: dict | None) -> dict | None:
  from app.modules.drawings_boq.takeoff.prep.facts import FLOOR_ORDER
  if not (spec.get("steps") and spec.get("riser_mm")) or way not in ("UP", "DOWN") or level_hint not in FLOOR_ORDER or not floor_heights:
    return None
  key = level_hint
  if way == "DOWN":
    lower = [k for k in FLOOR_ORDER[:FLOOR_ORDER.index(level_hint)] if k in floor_heights]
    if not lower:
      return None
    key = lower[-1]
  storey = ((floor_heights.get(key) or {}).get("floor_to_floor_mm"))
  if not storey:
    return None
  rise = float(spec["steps"]) * float(spec["riser_mm"])
  gap = (rise - float(storey)) / float(storey)
  return {"rise_mm": round(rise, 1), "storey_mm": round(float(storey), 1), "storey_of": key, "gap_pct": round(gap * 100.0, 1), "differs": abs(gap) > RISE_TOL}

def find_labels(lines: list) -> list[dict]:
  """The places a plan names a staircase ("STAIR", "STAIR UP"): one point each, in page units."""
  out = []
  for ln in lines:
    if not _LABEL.match(ln.text or ""):
      continue
    ws = [w for _, _, w in ln.spans]
    if not ws:
      continue
    out.append({"text": ln.text.strip(), "x": sum(w.cx for w in ws) / len(ws), "y": sum(w.cy for w in ws) / len(ws)})
  return out

def equivalent_depth_mm(riser_mm: float, tread_mm: float, waist_mm: float) -> float:
  """The thickness that, spread over the plan run of the flight, gives the same concrete as the steps and the waist slab together: the waist measured
  vertically (its thickness over the cosine of the slope) plus half a riser for the steps."""
  slope = math.hypot(riser_mm, tread_mm) / tread_mm
  return waist_mm * slope + riser_mm / 2.0

def waist_from_depth_mm(riser_mm: float, tread_mm: float, depth_mm: float) -> float:
  """The waist slab thickness that goes with an equivalent depth: the reverse of equivalent_depth_mm."""
  slope = math.hypot(riser_mm, tread_mm) / tread_mm
  return (depth_mm - riser_mm / 2.0) / slope

def treads_of(steps) -> int:
  """The treads of a stair of this many steps (risers): the top riser meets the floor or the landing, so there is one tread fewer than risers."""
  return max(int(round(float(steps))) - 1, 1)

def flight_box(spec: dict, waist_mm: float) -> dict | None:
  """The box a flight is measured as: plan run (one tread fewer than the risers) x width x equivalent thickness."""
  for k in ("riser_mm", "tread_mm", "width_mm", "steps"):
    if not spec.get(k):
      return None
  depth = equivalent_depth_mm(float(spec["riser_mm"]), float(spec["tread_mm"]), float(waist_mm))
  return {"length_mm": round(treads_of(spec["steps"]) * float(spec["tread_mm"]), 1), "width_mm": round(float(spec["width_mm"]), 1), "depth_mm": round(depth, 1)}

def run_box(spec: dict) -> dict | None:
  for k in ("tread_mm", "width_mm", "steps"):
    if not spec.get(k):
      return None
  return {"length_mm": round(treads_of(spec["steps"]) * float(spec["tread_mm"]), 1), "width_mm": round(float(spec["width_mm"]), 1)}
