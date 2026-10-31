from __future__ import annotations
import math
import re
from app.modules.drawings_boq.takeoff.prep.lintels import _fix, _frame, MM_INCH, MM_FOOT, SPAN_FT, WIDTH_IN, DEPTH_IN, BAR_NUMBERS, BAR_COUNT, RING_SPACING_IN

MIN_ROWS = 2
REACH_LINES = 10.0
ROW_TOL_LINES = 0.6
_MARKS = r"[\"”″]"
_CAPTION = re.compile(r"^L\s*(?P<n>\d{1,2})\s*\(\s*UP\s*TO\s*(?P<span>\d{1,2}(?:\.\d)?)\s*['’′]?\s*(?:FT|FEET)?\s*SPAN\s*\)", re.I)
_DIM = re.compile(r"^(?P<n>\d{1,2}(?:\.\d)?)\s*" + _MARKS + r"$")
_BARS = re.compile(r"(?<![#\d.])(?P<n>\d{1,2})\s*-\s*#\s*(?P<bar>\d{1,2})(?![\d-])")
_RING = re.compile(r"^#\s*(?P<bar>\d{1,2})\s*@\s*(?P<s>\d{1,2}(?:\.\d)?)\s*" + _MARKS + r"?\s*C\s*/\s*C$", re.I)
_BENT = re.compile(r"^BENT", re.I)
_START = re.compile(r"^L\s*(?P<n>\d{1,2})\s*\(\s*UP$", re.I)
CAPTION_LINE_TOL = 0.35
BENT_REACH_LINES = 3.0

def _in_frame(w, angle: int) -> tuple:
  rad = math.radians(angle)
  ux, uy = math.cos(rad), math.sin(rad)
  return w.cx * ux + w.cy * uy, -w.cx * uy + w.cy * ux

def _captions(words: list) -> list:
  frames = [(w, *_frame(w)) for w in words]
  out = []
  for w, ang, along, across in frames:
    start = _START.match(_fix(w.text).strip())
    if not start:
      continue
    tail = sorted((f for f in frames if f[1] == ang and f[2] > along and abs(f[3] - across) <= CAPTION_LINE_TOL * w.size), key=lambda f: f[2])[:3]
    m = _CAPTION.search(_fix(" ".join([w.text, *(f[0].text for f in tail)])))
    if not m:
      continue
    span = float(m.group("span"))
    if SPAN_FT[0] <= span <= SPAN_FT[1]:
      centre = sum([along, *(f[2] for f in tail)]) / (1 + len(tail))
      out.append({"mark": "L" + start.group("n"), "span_ft": span, "angle": ang, "along": centre, "across": across, "size": w.size})
  return out

def _rows(caps: list) -> list:
  rows: list = []
  for c in sorted(caps, key=lambda c: (c["angle"], c["across"], c["along"])):
    for r in rows:
      if r[0]["angle"] == c["angle"] and abs(r[0]["across"] - c["across"]) <= ROW_TOL_LINES * c["size"]:
        r.append(c)
        break
    else:
      rows.append([c])
  return [r for r in rows if len(r) >= MIN_ROWS]

def _inches(text: str) -> float | None:
  m = _DIM.match(_fix(text).strip())
  return float(m.group("n")) if m else None

def _steel(groups: list) -> tuple:
  bent = [g for g in groups if g["bent"]]
  plain = sorted((g for g in groups if not g["bent"]), key=lambda g: -g["across"])
  middle: list = []
  
  if len(plain) >= 3:
    middle, plain = plain[1:-1], [plain[0], plain[-1]]
  extra = [*bent, *middle]
  if len(extra) > 1:
    return None, "more than one bar group that is neither top nor bottom"
  out: dict = {}
  if len(plain) == 1:
    out["bars"] = {"n": plain[0]["n"], "bar": plain[0]["bar"]}
  elif len(plain) == 2:
    out["top"] = {"n": plain[0]["n"], "bar": plain[0]["bar"]}
    out["bottom"] = {"n": plain[1]["n"], "bar": plain[1]["bar"]}
  if extra:
    out["extra"] = {"n": extra[0]["n"], "bar": extra[0]["bar"]}
  return out or None, None

def _detail(cap: dict, near: list) -> dict | None:
  width: set = set()
  depth: set = set()
  groups: list = []
  rings: list = []
  
  for w, along, across in near:
    text = _fix(w.text).strip()
    inch = _inches(text)
    if inch is not None:
      same = round(w.angle / 90.0) % 4 == round(cap["angle"] / 90.0) % 4
      lim = WIDTH_IN if same else DEPTH_IN
      if lim[0] <= inch <= lim[1]:
        (width if same else depth).add(inch)
      continue
  
    ring = _RING.match(text)
    if ring:
      rings.append({"bar": int(ring.group("bar")), "spacing_in": float(ring.group("s"))})
      continue
    m = _BARS.fullmatch(text)
    if m:
      n, bar = int(m.group("n")), int(m.group("bar"))
      if BAR_COUNT[0] <= n <= BAR_COUNT[1] and BAR_NUMBERS[0] <= bar <= BAR_NUMBERS[1]:
        bent = any(_BENT.match(_fix(o.text).strip()) and 0.0 < oa - along <= BENT_REACH_LINES * cap["size"] and abs(oc - across) <= 1.2 * cap["size"] for o, oa, oc in near)
        groups.append({"n": n, "bar": bar, "across": across, "bent": bent})
        
  uniq: dict = {}
  for g in groups:
    uniq.setdefault((g["n"], g["bar"], g["bent"], round(g["across"], 0)), g)
  groups = list(uniq.values())
  if len(width) != 1 or len(depth) != 1:
    return {"mark": cap["mark"], "span_ft": cap["span_ft"], "problem": f"width read as {sorted(width)} and depth as {sorted(depth)} inches"}
  w_in, d_in = next(iter(width)), next(iter(depth))
  entry = {"span_max_ft": cap["span_ft"], "span_max_mm": round(cap["span_ft"] * MM_FOOT, 1), "width_mm": round(w_in * MM_INCH, 1), "depth_mm": round(d_in * MM_INCH, 1),
    "text": f"{cap['mark']} up to {cap['span_ft']:g} x {w_in:g} x {d_in:g}", "mark": cap["mark"], "from_details": True}
  steel, problem = _steel(groups)
  uniq_rings = {(r["bar"], r["spacing_in"]) for r in rings}
  
  if len(uniq_rings) == 1:
    bar, spacing = next(iter(uniq_rings))
    if BAR_NUMBERS[0] <= bar <= BAR_NUMBERS[1] and RING_SPACING_IN[0] <= spacing <= RING_SPACING_IN[1]:
      steel = {**(steel or {}), "ring": {"bar": bar, "spacing_mm": round(spacing * MM_INCH, 1)}}
  elif len(uniq_rings) > 1:
    problem = problem or "two different rings printed"
  if problem:
    entry["steel_problem"] = problem
    steel = None
  if steel:
    entry["steel"] = steel
  return entry

def read(words: list) -> list[dict]:
  rows_out: list = []
  caps = _captions(words)
  if len(caps) < MIN_ROWS:
    return []
  for row in _rows(caps):
    row.sort(key=lambda c: c["along"])
    size = max(c["size"] for c in row)
    
    lo, hi = row[0]["along"] - 0.5 * (row[1]["along"] - row[0]["along"]), row[-1]["along"] + 0.5 * (row[-1]["along"] - row[-2]["along"])
    mine: dict = {id(c): [] for c in row}
    for w in words:
      along, across = _in_frame(w, row[0]["angle"])
      if not (lo <= along <= hi):
        continue
    
      rise = across - row[0]["across"]
      if not (0.0 < rise <= REACH_LINES * size):
        continue
      nearest = min(row, key=lambda c: abs(c["along"] - along))
      mine[id(nearest)].append((w, along, across))
    for c in row:
      got = _detail(c, mine[id(c)])
      if got:
        rows_out.append(got)
        
  good = {}
  for r in rows_out:
    if "problem" not in r:
      good.setdefault(r["span_max_ft"], r)
  rows = [good[k] for k in sorted(good)]
  return rows if len(rows) >= MIN_ROWS else []
