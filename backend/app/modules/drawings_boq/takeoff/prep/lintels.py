from __future__ import annotations
import re
import math
from app.modules.drawings_boq.takeoff.prep.texts import build_lines
from app.modules.drawings_boq.takeoff.prep import marks as M
from app.modules.drawings_boq.takeoff.prep.texts import build_lines

MM_INCH = 25.4
MM_FOOT = 304.8
MIN_ROWS = 2
MAX_ROWS = 12
WIDTH_IN = (4.0, 24.0)
DEPTH_IN = (4.0, 36.0)
SPAN_FT = (1.0, 40.0)

_MARKS = r"[\"”″'’′]"
_ROW = re.compile(
   r"UP\s*TO\s*(?P<span>\d{1,2}(?:\.\d)?)\s*" + _MARKS + r"{0,2}\s+.*?(?P<w>\d{1,2}(?:\.\d)?)\s*" + _MARKS + r"{1,2}\s*[xX×]\s*(?P<d>\d{1,2}(?:\.\d)?)\s*" + _MARKS + r"{1,2}", re.I)
_HEADER = re.compile(r"LINTELS?", re.I)
_RING = re.compile(r"#\s*(?P<bar>\d{1,2})\s*[-–@]\s*(?P<s>\d{1,2}(?:\.\d)?)\s*" + _MARKS + r"?\s*C\s*/?\s*C", re.I)
_BARS = re.compile(r"(?<![#\d.])(?P<n>\d{1,2})\s*#\s*(?P<bar>\d{1,2})(?![\d-])")
BAR_NUMBERS = (2, 12)
BAR_COUNT = (1, 30)
RING_SPACING_IN = (2.0, 24.0)
_TIE = re.compile(r"TIE\s*(?:BAND|BEAM)", re.I)

def _across_rows(items: list, tol: float) -> list:
  rows: list = []
  for it in sorted(items, key=lambda t: t[0]):
    if rows and it[0] - rows[-1][-1][0] <= tol:
      rows[-1].append(it)
    else:
      rows.append([it])
  return rows

_FRACTIONS = {"½": " 1/2", "¼": " 1/4", "¾": " 3/4", "⅛": " 1/8", "⅜": " 3/8", "⅝": " 5/8", "⅞": " 7/8"}

def _fix(text: str) -> str:
  """Same clean-up as the opening schedule reader. Kept here so this module imports nothing from schedules.py (schedules.py imports this one)."""
  s = M.tidy(text)
  for k, v in _FRACTIONS.items():
    s = s.replace(k, v)
  return re.sub(r"\s+", " ", s).strip()

def _frame(w) -> tuple:
  """Same as the opening schedule reader: (angle, position along the text line, position across it) for a word on a rotated page."""
  a = round(w.angle / 90.0) % 4
  rad = math.radians(a * 90)
  ux, uy = math.cos(rad), math.sin(rad)
  return a * 90, w.cx * ux + w.cy * uy, -w.cx * uy + w.cy * ux

def _text(row: list) -> str:
  return _fix(" ".join(w.text for _, _, w in sorted(row, key=lambda t: t[1])))

def _header_order(items: list) -> str:
  """"BT" when the BOTTOM column of the table comes before the TOP column along the line, "TB" when it is the other way round. The common print is BOTTOM, TOP."""
  pos: dict = {}
  for _, along, w in items:
    token = w.text.strip().upper().strip(".:,")
    if token in ("BOTTOM", "TOP") and token not in pos:
      pos[token] = along
  if "BOTTOM" in pos and "TOP" in pos and pos["TOP"] < pos["BOTTOM"]:
    return "TB"
  return "BT"

def read_steel(text: str, order: str = "BT") -> dict | None:
  """The reinforcement printed on a lintel table row: bars at the bottom and the top ("2 # 3", two bars of #3) and the rings ("# 3-8" C/C", #3 at 8 inch
  centres). A bar number is the diameter in eighths of an inch. Returns {"bottom": {"n", "bar"}, "top": {...}, "ring": {"bar", "spacing_mm"}} with only the
  parts that read, or None when nothing reads."""
  s = _fix(text)
  out: dict = {}
  ring = _RING.search(s)
  if ring:
    bar, spacing = int(ring.group("bar")), float(ring.group("s"))
    if BAR_NUMBERS[0] <= bar <= BAR_NUMBERS[1] and RING_SPACING_IN[0] <= spacing <= RING_SPACING_IN[1]:
      out["ring"] = {"bar": bar, "spacing_mm": round(spacing * MM_INCH, 1)}
    s = s[:ring.start()] + " " + s[ring.end():]
    
  groups = []
  for m in _BARS.finditer(s):
    n, bar = int(m.group("n")), int(m.group("bar"))
    if BAR_COUNT[0] <= n <= BAR_COUNT[1] and BAR_NUMBERS[0] <= bar <= BAR_NUMBERS[1]:
      groups.append({"n": n, "bar": bar})
  if len(groups) == 2:
    first, second = ("bottom", "top") if order == "BT" else ("top", "bottom")
    out[first], out[second] = groups[0], groups[1]
  elif len(groups) == 1:
    out["bars"] = groups[0]
  return out or None

def steel_text(steel: dict | None) -> str:
  if not steel:
    return ""
  parts = []
  for key, name in (("bottom", "bottom"), ("top", "top"), ("bars", "bars")):
    g = steel.get(key)
    if g:
      parts.append(f"{g['n']} #{g['bar']} {name}")
  r = steel.get("ring")
  if r:
    parts.append(f"rings #{r['bar']} at {r['spacing_mm'] / MM_INCH:g} in")
  return ", ".join(parts)

def read_lintel_table(words: list) -> list[dict]:
  """The lintel table printed on a structural sheet ("UP TO 4" 9'X6" 2#3 2#3 ..."): one row per span with the section of the lintel.
  The span is a length in feet and the section is width x depth in inches, whatever marks are printed after the numbers: a drawing prints a lintel
  span as 4" and a 9 inch wide lintel as 9', and neither can be taken literally. Rows are kept only when two or more rows read, so a stray "UP TO" is not a table."""
  by_angle: dict = {}
  for w in words:
    if abs(((w.angle + 45) % 90) - 45) > 6:
      continue
    ang, along, across = _frame(w)
    by_angle.setdefault(ang, []).append((across, along, w))
  found: list = []
  for items in by_angle.values():
    if not items:
      continue
    size = sorted(w.size for _, _, w in items)[len(items) // 2]
    order = _header_order(items)
    for row in _across_rows(items, max(1.5, 0.45 * size)):
      text = _text(row)
      m = _ROW.search(text)
      
      if not m:
        continue
      span, w_in, d_in = float(m.group("span")), float(m.group("w")), float(m.group("d"))
      if not (SPAN_FT[0] <= span <= SPAN_FT[1] and WIDTH_IN[0] <= w_in <= WIDTH_IN[1] and DEPTH_IN[0] <= d_in <= DEPTH_IN[1]):
        continue
      entry = {"span_max_ft": span, "span_max_mm": round(span * MM_FOOT, 1), "width_mm": round(w_in * MM_INCH, 1), "depth_mm": round(d_in * MM_INCH, 1),
        "text": f"up to {span:g} x {w_in:g} x {d_in:g}"}
      steel = read_steel(text[m.end():], order)
      if steel:
        entry["steel"] = steel
      found.append(entry)
  by_span: dict = {}
  for r in found:
    by_span.setdefault(r["span_max_ft"], r)
  rows = [by_span[k] for k in sorted(by_span)][:MAX_ROWS]
  return rows if len(rows) >= MIN_ROWS else []

def read_tie_band(words: list) -> str | None:
  """The note that a continuous tie band runs over the walls at lintel level ("TIE BEAM / LINTEL", "LEVEL TIE BAND"), or None."""
  hits = []
  for ln in build_lines(words):
    t = ln.text.strip()
    if _TIE.search(t) and len(t) <= 80:
      hits.append(t)
  if not hits:
    return None
  joined = " ".join(hits)
  if re.search(r"LINTEL|BAND", joined, re.I):
    return " / ".join(dict.fromkeys(h.upper() for h in hits))[:120]
  return None

_ROOF_BAND = re.compile(r"^\W*ROOF\s*BAND\W*$", re.I)
_BINDING = re.compile(r"BINDING\s*BARS?", re.I)
_BAR_AT = re.compile(r"#\s*(?P<bar>\d{1,2})\s*@\s*(?P<s>\d{1,2}(?:\.\d)?)")
BINDING_REACH = 60.0

def read_roof_band(words: list) -> dict | None:
  lines = build_lines(words)
  cap = next((ln for ln in lines if _ROOF_BAND.match(ln.text.strip()) and ln.spans), None)
  if cap is None:
    return None
  out: dict = {"text": "ROOF BAND", "binding": None}
  tag = next((ln for ln in lines if _BINDING.search(ln.text) and ln.spans), None)
  if tag is not None:
    ws = [w for _, _, w in tag.spans]
    
    cx, cy = sum(w.cx for w in ws) / len(ws), sum(w.cy for w in ws) / len(ws)
    best = None
    for w in words:
      m = _BAR_AT.search(w.text or "")
      if m is None:
        continue
      
      d = math.hypot(w.cx - cx, w.cy - cy)
      if d <= BINDING_REACH and (best is None or d < best[0]):
        best = (d, m)
    if best is not None:
      bar, spacing = int(best[1].group("bar")), float(best[1].group("s"))
      if BAR_NUMBERS[0] <= bar <= BAR_NUMBERS[1] and RING_SPACING_IN[0] <= spacing <= RING_SPACING_IN[1]:
        out["binding"] = {"bar": bar, "spacing_mm": round(spacing * MM_INCH, 1)}
  return out

def section_for(rows: list, span_mm: float) -> dict | None:
  """The first table row whose span limit holds the opening; None when the opening is wider than every row."""
  for r in sorted(rows or [], key=lambda r: r["span_max_mm"]):
    if span_mm <= r["span_max_mm"] + 1.0:
      return r
  return None

def section_in(sec: dict, wall_mm: float | None = None) -> tuple:
  width, depth = float(sec["width_mm"]), float(sec["depth_mm"])
  if wall_mm:
    thin = sec.get("thin")
    if thin:
      width, depth = float(thin["width_mm"]), float(thin["depth_mm"])
    width = min(width, float(wall_mm))
  return width, depth
