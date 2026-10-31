from __future__ import annotations
import math
import re
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.extract import beam_sections as BS

INCH_MM = 25.4
REACH_MM = 1500.0
FRACTION = {"½": 0.5, "¼": 0.25, "¾": 0.75}
NUM = r"(\d{1,2}(?:\.\d+)?)\s*([½¼¾])?"
INCH = r"(\"|”|″|'')"
SIZE = re.compile(r"^" + NUM + r"\s*" + INCH + r"?\s*[xX×]\s*" + NUM + r"\s*" + INCH + r"?$")
DROP = ("BEAM_MARK_NO_SECTION", "BEAM_SECTIONS_LISTED")

def size_of(text: str) -> tuple | None:
  m = SIZE.match(text.strip())
  if not m or not (m.group(3) or m.group(6)):
    return None
  w = (float(m.group(1)) + FRACTION.get(m.group(2) or "", 0.0)) * INCH_MM
  d = (float(m.group(4)) + FRACTION.get(m.group(5) or "", 0.0)) * INCH_MM
  return round(w, 1), round(d, 1)

def sizes(words: list, marks: list, mm_per_pt: float) -> dict:
  out: dict = {}
  
  reach = REACH_MM / mm_per_pt
  for w in words:
    size = size_of(w.text)
    if size is None or not marks:
      continue
    tag, x, y, _ = min(marks, key=lambda m: math.hypot(m[1] - w.cx, m[2] - w.cy))
    if math.hypot(x - w.cx, y - w.cy) > reach:
      continue
    if size not in out.setdefault(tag, []):
      out[tag].append(size)
  return out

def apply(c, found: list, width_mm: float) -> bool:
  if not found:
    return False
  if len(found) > 1:
    c.notes.append(C.note("BEAM_LABEL_SIZES_DIFFER", sizes_mm=[list(s) for s in found]))
    return False
  w, d = found[0]
  if abs(w - width_mm) > C.BEAM_WIDTH_SNAP_TOL * w:
    c.notes.append(C.note("BEAM_LABEL_WIDTH_DIFFERS", label_mm=w, strip_mm=round(width_mm, 1)))
    return False

  before = (c.params or {}).get("depth_mm")
  c.params["width_mm"], c.params["depth_mm"] = w, d
  c.missing = [m for m in (c.missing or []) if m != "depth_mm"]
  c.notes = [n for n in c.notes if n.get("code") not in DROP]
  c.facts["label_size_mm"] = [w, d]
  c.notes.append(C.note("BEAM_SIZE_FROM_LABEL", width_mm=w, depth_mm=d))
  
  if before and abs(float(before) - d) > 1.0:
    c.facts["section_depth_mm"] = before
    c.notes.append(C.note("BEAM_LABEL_DEPTH_DIFFERS_SECTION", label_mm=d, section_mm=before))
  BS.basis_note(c)
  return True
