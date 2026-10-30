from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.prep import footing_sections as FS

PLAN_CAPTION = re.compile(r"^(?:FOUNDATION|FOOTING)\s+PLAN\s+(?P<mark>[A-Z]{1,2}\s*-?\s*\d{1,2})\s*$", re.I)
ANY_CAPTION = re.compile(r"^(?:SECTION|SEC\.?|FOUNDATION\s+PLAN|FOOTING\s+PLAN|COLUMN\s+SEC|DETAIL|PLAN)\b", re.I)
FEET = re.compile(r"^(?P<ft>\d+)\s*['’]\s*(?:-?\s*(?P<in>\d+(?:\.\d+)?)\s*[\"”]?)?$")
FT_MM = 304.8
IN_MM = 25.4
MIN_FT = 1.0
MAX_FT = 40.0
REACH_PT = 330.0
COLUMN_HALF_PT = 150.0
ORIENT_TOL = 30.0

def feet_mm(text: str) -> float | None:
  m = FEET.match((text or "").strip())
  if not m:
    return None
  mm = int(m.group("ft")) * FT_MM + float(m.group("in") or 0.0) * IN_MM
  return mm if MIN_FT * FT_MM <= mm <= MAX_FT * FT_MM else None

def _orient(w) -> int:
  return int(round((w.angle % 180.0) / 90.0)) % 2

def read(words: list) -> list:
  if not words:
    return []
  u, w = FS._frame(words)
  lines = FS._lines(words, u, w)
  caps = [l for l in lines if ANY_CAPTION.match(l["text"].strip())]
  plans = [l for l in caps if PLAN_CAPTION.match(l["text"].strip())]
  if not plans:
    return []
  placed = []
  for wd in words:
    mm = feet_mm(wd.text)
    if mm is not None:
      placed.append((wd.cx * u[0] + wd.cy * u[1], wd.cx * w[0] + wd.cy * w[1], mm, wd))
      
  out = []
  for cap in plans:
    mark = PLAN_CAPTION.match(cap["text"].strip()).group("mark")
    above = [c["Z"] for c in caps if c is not cap and c["Z"] > cap["Z"] and abs(c["X"] - cap["X"]) <= COLUMN_HALF_PT]
    top = min(above + [cap["Z"] + REACH_PT])
    mine = []
    for X, Z, mm, wd in placed:
      if not cap["Z"] < Z < top:
        continue
    
      near = min(plans, key=lambda c: abs(c["X"] - X))
      if near is cap and abs(X - cap["X"]) <= COLUMN_HALF_PT:
        mine.append((mm, _orient(wd), wd.text.strip()))
    rec = {"mark": re.sub(r"[\s\-]", "", mark).upper(), "caption": cap["text"].strip(), "read": "UNCLEAR", "size_mm": None, "dims": [t for _m, _o, t in mine], "issues": []}
    by: dict = {}
    for mm, o, _t in mine:
      by.setdefault(o, []).append(mm)
    if len(by) != 2:
      rec["issues"].append("FOOTING_VIEW_DIMS_NOT_TWO_DIRECTIONS")
    elif any(max(v) - min(v) > 1.0 for v in by.values()):
      rec["issues"].append("FOOTING_VIEW_DIMS_DISAGREE")
    else:
      a, b = (v[0] for v in by.values())
      rec["size_mm"] = [round(min(a, b), 1), round(max(a, b), 1)]
      rec["read"] = "OK"
    out.append(rec)
  return out
