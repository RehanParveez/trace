from __future__ import annotations
import math
import re
from app.engine.measure import rule_registry as RR
from app.modules.drawings_boq.takeoff.extract import tank_record as TR

RULE = "TANK_CAPACITY_LABELS"
PHRASES = {"UGWT": ("UNDER", "GROUND"), "OHWT": ("OVER", "HEAD"), "SEPTIC": ("SEPTIC", "TANK")}
PHRASE_REACH = 3.5
NEAR = 6.0
GALLON = re.compile(r"gal", re.I)
NUMBER = re.compile(r"^\d[\d,]*(?:\.\d+)?$")
MIN_GALLONS = 50.0
FACTOR = re.compile(r"^\d+(?:\.\d+)?$")
GALLON_TOL = 0.02

def enabled() -> bool:
  return RR.on(RULE)

def parse_product(text: str) -> dict | None:
  parts = [p.strip() for p in re.split(r"\s*[xX×]\s*", (text or "").strip()) if p.strip()]
  factor = None
  if len(parts) == 4 and FACTOR.match(parts[3]):
    factor = float(parts[3])
    parts = parts[:3]
  if len(parts) not in (2, 3):
    return None
  
  lengths = [TR.length_in(p) for p in parts]
  if any(v is None for v in lengths):
    return None
  return {"lengths_in": lengths, "factor": factor}

def _norm(w) -> str:
  return (w.text or "").strip().upper().strip(".,:;()")

def labels(words: list) -> dict:
  out: dict = {}
  for kind, (first, second) in PHRASES.items():
    for w in words or []:
      if _norm(w) != first:
        continue
      h = max(float(w.height or 0), 1.0)
      if any(o is not w and _norm(o) == second and math.hypot(o.cx - w.cx, o.cy - w.cy) <= PHRASE_REACH * h * max(1.0, len(second) / 2.0) for o in words) and fields(words, w):
        out.setdefault(kind, []).append(w)
  return out

def fields(words: list, label, page_no: int | None = None) -> dict:
  near = TR._lines_near(words, label, NEAR)
  gallons = None
  for text, _d, _x, _y in near:
    if GALLON.search(text):
      nums = [float(t.replace(",", "")) for t in text.split() if NUMBER.match(t) and float(t.replace(",", "")) >= MIN_GALLONS]
      if nums:
        gallons = max(nums)
        break
      
  for text, _d, _x, _y in near:
    found = next(((tok, p) for tok in text.split() for p in [parse_product(tok)] if p), None)
    if found is None:
      continue
    text, got = found
    lengths = got["lengths_in"]
    a, b = lengths[0], lengths[1]
    if not (TR.MIN_SIDE_IN <= min(a, b) and max(a, b) <= TR.MAX_SIDE_IN):
      continue
    said = text
    
    if len(lengths) == 3 and got["factor"] and gallons:
      calc = lengths[0] * lengths[1] * lengths[2] / 1728.0 * got["factor"]
      said += f" ({gallons:g} gallons printed, {calc:.1f} computed, {'agree' if abs(calc - gallons) <= GALLON_TOL * calc else 'DISAGREE'})"
    out = {"plan": {"route": "LABEL", "page_no": page_no, "mm": [round(v * TR.MM_PER_IN, 1) for v in sorted((a, b), reverse=True)], "basis": "INSIDE", "text": said}}
    if len(lengths) == 3 and TR.MIN_DEPTH_IN <= lengths[2] <= TR.MAX_DEPTH_IN:
      out["depth"] = {"route": "LABEL", "page_no": page_no, "mm": round(lengths[2] * TR.MM_PER_IN, 1), "basis": "INSIDE", "text": text}
    return out
  return {}
