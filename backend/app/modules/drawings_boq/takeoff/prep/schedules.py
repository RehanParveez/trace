from __future__ import annotations
import re
import math
from collections import Counter
from app.modules.drawings_boq.takeoff.prep import marks as M
from app.modules.drawings_boq.takeoff.prep import lintels as lintel_reader
from app.modules.drawings_boq.takeoff.prep import lintel_matrix
from app.modules.drawings_boq.takeoff.prep import stairs as stair_reader
from app.modules.drawings_boq.takeoff.prep.texts import build_lines

MM_INCH = 25.4
MM_FOOT = 304.8
SFT_M2 = 0.09290304
_FRACTIONS = {"½": " 1/2", "¼": " 1/4", "¾": " 3/4", "⅛": " 1/8", "⅜": " 3/8", "⅝": " 5/8", "⅞": " 7/8"}

NAME_HEADERS = {"NAME", "MARK", "MARKS", "MK", "TAG", "TYPE", "ID", "REF", "SYMBOL", "DESIGNATION"}
SIZE_HEADERS = {"SIZE", "SIZES", "DIMENSION", "DIMENSIONS", "OPENING", "WIDTH", "HEIGHT"}
MARK_RE = re.compile(r"^(?P<p>DR|D|WIN|WN|W|VENT|V)[-.]?(?P<n>\d{1,3})(?P<s>[A-Z])?$")
TYPE_OF = {"D": "DOOR", "DR": "DOOR", "W": "WINDOW", "WN": "WINDOW", "WIN": "WINDOW", "V": "VENTILATOR", "VENT": "VENTILATOR"}

PLAUSIBLE = {  
  "DOOR": ((450.0, 3600.0), (1500.0, 3300.0)),
  "WINDOW": ((300.0, 6000.0), (300.0, 3600.0)),
  "VENTILATOR": ((200.0, 3000.0), (200.0, 1800.0)),
}

MAX_SIZE_REACH_PT = 160.0   
MAX_ROW_OFFSET_PT = 5.0     
NAME_COLUMN_TOL_PT = 6.0
MAX_OPENINGS = 80
MAX_AREAS = 24

_UNIT = r"(?:SFT|S\.?\s?F\.?\s?T\.?|SQ\.?\s?FT\.?|SQFT|SQ\.?\s?M\.?|SQM|M2|M²|SQ\.?\s?YD|SQYD)"
_TOTAL = re.compile(r"TOTAL\s+AREA\s+OF\s+(?P<name>[A-Z0-9/.&' -]+?)\s*=\s*(?:[^=]*?=\s*)?(?P<v>\d[\d,]*(?:\.\d+)?)\s*(?P<u>" + _UNIT + r")", re.I)
_GRAND = re.compile(r"GRAND\s+TOTAL\s*(?:AREA)?\s*=\s*(?:[^=]*?=\s*)?(?P<v>\d[\d,]*(?:\.\d+)?)\s*(?P<u>" + _UNIT + r")", re.I)
_FLOOR_AREA = re.compile(r"^(?P<name>[A-Z/ ]*?FLOOR|BASEMENT|MUMTY)\s+AREA\s*=\s*(?P<v>\d[\d,]*(?:\.\d+)?)\s*(?P<u>" + _UNIT + r")", re.I)
_DIMS = re.compile(r"=\s*(?P<a>\d[^=xX×]*?)\s*[xX×]\s*(?P<b>\d[^=]*?)\s*=\s*(?P<v>\d[\d,]*(?:\.\d+)?)\s*(?P<u>" + _UNIT + r")", re.I)
DIMS_AGREE_TOL = 0.015
DIMS_REACH = 40.0
_FEET_INCH = re.compile(r"(?P<ft>\d{1,3})\s*'\s*-?\s*(?P<in>\d{1,2}(?:\s+\d{1,2}/\d{1,2})?)?\s*(?:\"|″|”|'')?")
_INCH_ONLY = re.compile(r"^(?P<in>\d{1,3})\s*(?:\"|″|”|'')$")
_LENGTH = re.compile(r"\d{1,3}\s*'\s*-?\s*(?:\d{1,2}(?:\s+\d{1,2}/\d{1,2})?)?\s*(?:\"|''|″)?")
_SPLIT_X = re.compile(r"\s*[xX×]\s*")

def _fix(text: str) -> str:
  s = M.tidy(text)
  for k, v in _FRACTIONS.items():
    s = s.replace(k, v)
  return re.sub(r"\s+", " ", s).strip()

def norm_mark(text: str) -> str | None:
  """'D-1', 'd1' and 'D1' are the same mark. Returns the compact upper-case form, or None when the text is not a door, window or ventilator mark."""
  t = re.sub(r"\s+", "", (text or "")).upper()
  m = MARK_RE.match(t)
  if not m:
    return None
  return f"{m.group('p')}{m.group('n')}{m.group('s') or ''}"

def mark_type(mark: str) -> str | None:
  m = MARK_RE.match(mark or "")
  return TYPE_OF.get(m.group("p")) if m else None

def _frame(w) -> tuple:
  a = round(w.angle / 90.0) % 4
  rad = math.radians(a * 90)
  ux, uy = math.cos(rad), math.sin(rad)
  return a * 90, w.cx * ux + w.cy * uy, -w.cx * uy + w.cy * ux

def feet_inches_mm(text: str) -> float | None:
  """3'-6" -> 1066.8, 7'-0" -> 2133.6, 4'- -> 1219.2, 36" -> 914.4. None when the text is not one length."""
  s = _fix(text)
  m = _INCH_ONLY.match(s)
  
  if m:
    return round(int(m.group("in")) * MM_INCH, 1)
  m = _FEET_INCH.fullmatch(s)
  if not m:
    return None
  inch = 0.0
  if m.group("in"):
    parts = m.group("in").split()
    inch = float(parts[0])
    if len(parts) == 2:
      a, b = parts[1].split("/")
      if int(b) == 0:
        return None
      inch += int(a) / int(b)
  if inch >= 12:
    return None
  return round(int(m.group("ft")) * MM_FOOT + inch * MM_INCH, 1)

def _metric_mm(s: str) -> float | None:
  s = s.strip()
  if re.fullmatch(r"\d{3,4}", s):
    return float(s)
  if re.fullmatch(r"\d\.\d{1,3}", s):
    return round(float(s) * 1000.0, 1)
  return None

def parse_size_text(text: str) -> tuple | None:
  """'3'-0" x 5'-0"' -> (914.4, 1524.0). Width first, then height. Imperial feet-inch, inches only, or plain millimetres / metres."""
  s = _fix(text)
  s = re.sub(r"'\s*-\s+(\d)", r"'-\1", s)
  s = re.sub(r"'-\s*(\d{1,2})\s+\"", r"'-\1\"", s)
  parts = [p for p in _SPLIT_X.split(s) if p]
  if len(parts) == 1:  
    parts = [m.group(0).strip() for m in _LENGTH.finditer(s)]
  if len(parts) != 2:
    return None
  a, b = (feet_inches_mm(parts[0]), feet_inches_mm(parts[1]))
  if a is None or b is None:
    a, b = _metric_mm(parts[0]), _metric_mm(parts[1])
  if a is None or b is None:
    return None
  return a, b

def _plausible(kind: str, w: float, h: float) -> bool:
  (w0, w1), (h0, h1) = PLAUSIBLE[kind]
  return w0 <= w <= w1 and h0 <= h <= h1

_UNIT_WORD = re.compile(r"^" + _UNIT + r"$", re.I)

def _rows_by_anchor(items: list, tol: float) -> list:
  """Rows of the area table. Each row is the words level with one unit word ("SFT"); a word level with two rows goes to the nearer one."""
  anchors = [(ac, al) for ac, al, w in items if _UNIT_WORD.match(w.text.strip())]
  if not anchors:
    return []
  rows: dict = {i: [] for i in range(len(anchors))}
  for ac, al, w in items:
    best, best_d = None, tol + 1e-6
    for i, (aac, _) in enumerate(anchors):
      d = abs(ac - aac)
      if d < best_d:
        best, best_d = i, d
    if best is not None:
      rows[best].append((ac, al, w))
  return [r for r in rows.values() if r]

def _row_text(row: list) -> str:
  return _fix(" ".join(w.text for _, _, w in sorted(row, key=lambda t: t[1])))

def _tidy(text: str) -> str:
  return re.sub(r"\s+", " ", text).strip()

def table_marks(words: list) -> set:
  """The mark words that sit in the name column of a door / window schedule table. They are table rows, not marks on the plan."""
  return _scan(words)[1]

def read_openings(words: list) -> list[dict]:
  """The door, window and ventilator marks with their sizes, from a table that has a name column and a size column."""
  return _scan(words)[0]

def _scan(words: list) -> tuple:
  out: dict = {}
  ids: set = set()
  by_angle: dict = {}
  for w in words:
    ang_off = abs(((w.angle + 45) % 90) - 45)
    if ang_off > 6:
      continue
    ang, along, across = _frame(w)
    by_angle.setdefault(ang, []).append((across, along, w))
    
  for ang, items in by_angle.items():
    heads = [(al, w) for ac, al, w in items if w.text.strip().upper().rstrip(".:") in NAME_HEADERS]
    sizes_h = [(al, w) for ac, al, w in items if w.text.strip().upper().rstrip(".:") in SIZE_HEADERS]
    if not heads or not sizes_h:
      continue
    name_cols = sorted({round(al) for al, _ in heads})
    marks = []
    for ac, al, w in items:
      mk = norm_mark(w.text)
      if mk is None:
        continue
      if any(abs(al - c) <= NAME_COLUMN_TOL_PT for c in name_cols):
        marks.append((ac, al, w, mk))
    if len(marks) < 2:
      continue
    ids.update(id(w) for _, _, w, _ in marks)
    dims = [(ac, al, w) for ac, al, w in items if not norm_mark(w.text) and w.text.strip().upper() not in NAME_HEADERS | SIZE_HEADERS]
    rows: dict = {i: [] for i in range(len(marks))}
    
    for ac, al, w in dims:
      best, best_d = None, MAX_ROW_OFFSET_PT + 1e-6
      for i, (mac, mal, _, _) in enumerate(marks):
        d = abs(ac - mac)
        if d < best_d and 2.0 < al - mal <= MAX_SIZE_REACH_PT:
          best, best_d = i, d
      if best is not None:
        rows[best].append((ac, al, w))
    for i, (mac, mal, mw, mk) in enumerate(marks):
      cells = sorted(rows[i], key=lambda t: t[1])
      if not cells:
        continue
      arched = any(re.search(r"\bARCH(?:ED)?\b", cw.text, re.I) for _, _, cw in cells)
      kind = mark_type(mk)
      if kind is None:
        continue
    
      text = ""
      for _, _, cw in cells:
        piece = cw.text.strip()
        if not re.fullmatch(r"[0-9'\"′″”’½¼¾\-/ xX×.]+", piece):
          break
        text += " " + piece
      size = parse_size_text(text)
      
      if size is None:
        continue
      w_mm, h_mm = size
      swapped = False
      if not _plausible(kind, w_mm, h_mm) and _plausible(kind, h_mm, w_mm):
        w_mm, h_mm, swapped = h_mm, w_mm, True
      if not _plausible(kind, w_mm, h_mm):
        continue
      rec = {"mark": mk, "type": kind, "width_mm": round(w_mm, 1), "height_mm": round(h_mm, 1), "text": _tidy(text)[:40]}
      if swapped:
        rec["swapped"] = True
      if arched:
        rec["arched"] = True
      out.setdefault(mk, []).append(rec)
      
  flat = []
  for mk, recs in out.items():
    flat.append(max(recs, key=lambda r: sum(1 for x in recs if (x["width_mm"], x["height_mm"]) == (r["width_mm"], r["height_mm"]))))
  flat.sort(key=lambda r: (r["type"], int(re.sub(r"\D", "", r["mark"]) or 0), r["mark"]))
  return flat[:MAX_OPENINGS], ids

def level_key(name: str) -> str | None:
  t = (name or "").upper()
  for key, pat in (("BASEMENT", r"BASEMENT|CELLAR"), ("GROUND", r"GROUND|\bG\.?\s?F\b"), ("FIRST", r"\bFIRST\b|\b1ST\b"), ("SECOND", r"\bSECOND\b|\b2ND\b"),
    ("THIRD", r"\bTHIRD\b|\b3RD\b"), ("FOURTH", r"\bFOURTH\b|\b4TH\b"), ("ROOF", r"MUMTY|ROOF|TERRACE|PENT")):
    if re.search(pat, t):
      return key
  return None

def _m2(v: float, unit: str) -> float:
  u = re.sub(r"[\s.]", "", unit.upper())
  if u in ("SQM", "M2", "M²"):
    return v
  if u in ("SQYD",):
    return v * 0.83612736
  return v * SFT_M2

def _dims_of(text: str, m2: float, unit: str) -> dict | None:
  """The length and width printed in a covered-area line ("A = 30'-0" X 48'-0" = 1440.00 SFT"), kept only when length x width gives the area printed on the same line."""
  m = _DIMS.search(_fix(text))
  if not m:
    return None
  size = parse_size_text(f"{m.group('a')} x {m.group('b')}")
  
  if size is None:
    return None
  v = float(m.group("v").replace(",", ""))
  if abs(_m2(v, m.group("u")) - m2) > 0.02 * max(m2, 1.0):
    return None
  got = size[0] * size[1] / 1e6
  if got <= 0 or abs(got - m2) > DIMS_AGREE_TOL * m2:
    return None
  return {"dims_mm": [round(size[0], 1), round(size[1], 1)], "dims_text": _tidy(f"{m.group('a')} x {m.group('b')}")}

def _anchor_across(row: list) -> float:
  for ac, _, w in row:
    if _UNIT_WORD.match(w.text.strip()):
      return ac
  return sum(ac for ac, _, _ in row) / len(row)

def read_areas(words: list) -> list[dict]:
  """The area table: one row per floor ("TOTAL AREA OF GROUND FLOOR = 1440.00 SFT"), the grand total and the plot. A floor also carries the length and
  width printed in its covered-area line ("B = 30'-0" X 48'-0" = 1440.00 SFT") when that line is beside the floor's total and its product agrees with the area."""
  rows_out: dict = {}
  by_angle: dict = {}
  
  for w in words:
    if abs(((w.angle + 45) % 90) - 45) > 6:
      continue
    ang, along, across = _frame(w)
    by_angle.setdefault(ang, []).append((across, along, w))
  for items in by_angle.values():
    size = sorted(w.size for _, _, w in items)[len(items) // 2] if items else 4.0
    recs_here: list = []
    dim_rows: list = []
    for row in _rows_by_anchor(items, max(2.0, 0.7 * size)):
      if len(row) < 3:
        continue
      text = _row_text(row)
      if len(text) > 200:
        continue
      across = _anchor_across(row)
      m = _GRAND.search(text)
      
      if m:
        key, name, kind = "GRAND", "Grand total", "GRAND"
      else:
        m = _TOTAL.search(text) or _FLOOR_AREA.search(text)
        if not m:
          dm = _DIMS.search(_fix(text))
          if dm:
            v = float(dm.group("v").replace(",", ""))
            if 1.0 <= v <= 5e7:
              dim_rows.append({"across": across, "text": text, "v": v, "u": dm.group("u"), "m2": round(_m2(v, dm.group("u")), 2)})
          continue
        name = _tidy(m.group("name")).upper()
        lk = level_key(name)
        
        if "PLOT" in name:
          key, kind = "PLOT", "PLOT"
        elif lk:
          key, kind = lk, "FLOOR"
        else:
          continue
        name = name.title()
      v = float(m.group("v").replace(",", ""))
      if not (1.0 <= v <= 5e7):
        continue
    
      rec = {"key": key, "kind": kind, "name": name, "value": v, "unit": re.sub(r"[\s.]", "", m.group("u").upper()), "m2": round(_m2(v, m.group("u")), 2)}
      own = _dims_of(text, rec["m2"], m.group("u"))
      if own:
        rec.update(own)
      recs_here.append((rec, across))
      rows_out.setdefault(key, []).append(rec)
    pairs = []
    for i, (rec, across) in enumerate(recs_here):
      if rec["kind"] != "FLOOR" or rec.get("dims_mm"):
        continue
      for j, d in enumerate(dim_rows):
        gap = abs(d["across"] - across)
        if gap <= DIMS_REACH and abs(d["m2"] - rec["m2"]) <= 0.02 * max(rec["m2"], 1.0):
          pairs.append((gap, i, j))
          
    used_i: set = set()
    used_j: set = set()
    for gap, i, j in sorted(pairs):
      if i in used_i or j in used_j:
        continue
      rec = recs_here[i][0]
      got = _dims_of(dim_rows[j]["text"], rec["m2"], dim_rows[j]["u"])
      if got:
        rec.update(got)
        used_i.add(i)
        used_j.add(j)
      
  flat = []
  for key, recs in rows_out.items():
    flat.append(max(recs, key=lambda r: (1 if r.get("dims_mm") else 0, sum(1 for x in recs if x["m2"] == r["m2"]))))
  order = {"BASEMENT": 0, "GROUND": 1, "FIRST": 2, "SECOND": 3, "THIRD": 4, "FOURTH": 5, "ROOF": 6, "PLOT": 8, "GRAND": 9}
  flat.sort(key=lambda r: order.get(r["key"], 7))
  return flat[:MAX_AREAS]

def read_schedules(words: list) -> dict:
  """Everything the sheet's tables say about openings and floor areas. Empty lists when the sheet has no such table."""
  try:
    openings = read_openings(words)
  except Exception:
    openings = []
  try:
    areas = read_areas(words)
  except Exception:
    areas = []
  try:
    lintels = lintel_reader.read_lintel_table(words) or lintel_matrix.read(words)
    tie_band = lintel_reader.read_tie_band(words)
  except Exception:
    lintels, tie_band = [], None
  try:
    roof_band = lintel_reader.read_roof_band(words)
  except Exception:
    roof_band = None
  try:
    stair = stair_reader.read_stair_spec(build_lines(words))
  except Exception:
    stair = None
  out = {"openings": openings, "areas": areas, "lintels": lintels, "tie_band": tie_band, "roof_band": roof_band}
  if stair:
    out["stair"] = stair
  return out

def gather(sheets: list[dict]) -> dict:
  """All sheets' schedules together. Each sheet is {"page_no", "schedule"}. A mark or a floor printed with two different sizes is a conflict."""
  from app.modules.drawings_boq.takeoff.prep import projections as projection_reader
  ops: dict = {}
  areas: dict = {}
  spans: dict = {}
  tie_band = None
  tie_pages: list = []
  roof_band = None
  roof_pages: list = []
  stairs: list = []
  
  for sh in sheets:
    sc = sh.get("schedule") or {}
    if sc.get("stair"):
      stairs.append((sh["page_no"], sc["stair"]))
    for r in sc.get("lintels") or []:
      spans.setdefault(r["span_max_ft"], []).append((sh["page_no"], r))
    if sc.get("tie_band"):
      tie_band = tie_band or sc["tie_band"]
      tie_pages.append(sh["page_no"])
    if sc.get("roof_band"):
      roof_band = roof_band or dict(sc["roof_band"])
      roof_pages.append(sh["page_no"])
    for o in sc.get("openings") or []:
      ops.setdefault(o["mark"], []).append((sh["page_no"], o))
    for a in sc.get("areas") or []:
      areas.setdefault(a["key"], []).append((sh["page_no"], a))
  openings, conflicts = [], []
  
  for mark, recs in ops.items():
    sizes = Counter((o["width_mm"], o["height_mm"]) for _, o in recs)
    (w, h), _ = sizes.most_common(1)[0]
    base = next(o for _, o in recs if (o["width_mm"], o["height_mm"]) == (w, h))
    openings.append({**base, "area_m2": round(w * h / 1e6, 3), "pages": sorted({p for p, _ in recs}), **({"arched": True} if any(o.get("arched") for _, o in recs) else {})})
    if len(sizes) > 1:
      conflicts.append({"kind": "OPENING_SIZE", "name": mark, "values": [{"width_mm": a, "height_mm": b, "pages": sorted({p for p, o in recs if (o["width_mm"], o["height_mm"]) == (a, b)})} for (a, b) in sizes]})
  openings.sort(key=lambda r: (r["type"], int(re.sub(r"\D", "", r["mark"]) or 0), r["mark"]))
  
  area_rows = []
  for key, recs in areas.items():
    vals = Counter(a["m2"] for _, a in recs)
    m2, _ = vals.most_common(1)[0]
    base = next((a for _, a in recs if a["m2"] == m2 and a.get("dims_mm")), None) or next(a for _, a in recs if a["m2"] == m2)
    area_rows.append({**base, "pages": sorted({p for p, _ in recs})})
    if len(vals) > 1:
      conflicts.append({"kind": "FLOOR_AREA", "name": base["name"], "values": [{"m2": v, "pages": sorted({p for p, a in recs if a["m2"] == v})} for v in vals]})
  order = {"BASEMENT": 0, "GROUND": 1, "FIRST": 2, "SECOND": 3, "THIRD": 4, "FOURTH": 5, "ROOF": 6, "PLOT": 8, "GRAND": 9}
  area_rows.sort(key=lambda r: order.get(r["key"], 7))
  lintel_rows = []
  
  for span in sorted(spans):
    recs = spans[span]
    sizes = Counter((r["width_mm"], r["depth_mm"]) for _, r in recs)
    (w, d), _ = sizes.most_common(1)[0]
    base = next(r for _, r in recs if (r["width_mm"], r["depth_mm"]) == (w, d))
    lintel_rows.append({**base, "pages": sorted({p for p, _ in recs})})
    if len(sizes) > 1:
      conflicts.append({"kind": "LINTEL_SIZE", "name": f"up to {span:g} ft", "values": [{"width_mm": a, "depth_mm": b, "pages": sorted({p for p, r in recs if (r["width_mm"], r["depth_mm"]) == (a, b)})} for (a, b) in sizes]})
  stair = None
  if stairs:
    stair = {}
    for key in ("riser_mm", "tread_mm", "width_mm", "steps", "waist_mm"):
      votes = Counter(s[key] for _, s in stairs if s.get(key))
      if votes:
        stair[key] = votes.most_common(1)[0][0]
        if len(votes) > 1:
          conflicts.append({"kind": "STAIR_" + key.upper(), "name": key.replace("_mm", "").replace("_", " "), "values": [{"value": v, "pages": sorted({p for p, s in stairs if s.get(key) == v})} for v in votes]})
          
    stair["text"] = stair_reader.stair_text(stair)
    stair["pages"] = sorted({p for p, _ in stairs})
  out = {"openings": openings, "areas": area_rows, "lintels": lintel_rows, "tie_band": ({"text": tie_band, "pages": sorted(set(tie_pages))} if tie_band else None), "conflicts": conflicts}
  if roof_band:
    out["roof_band"] = {**roof_band, "pages": sorted(set(roof_pages))}
  elif any("roof_band" in (sh.get("schedule") or {}) for sh in sheets):
    out["roof_band"] = None                      
  if stair:
    out["stair"] = stair
  projections = projection_reader.gather(sheets)
  if projections:
    out["projections"] = projections
  return out

def arched_marks(schedule: dict | None) -> set:
  """The marks of the openings whose schedule row says they are arched."""
  return {str(o["mark"]).upper() for o in (schedule or {}).get("openings") or [] if o.get("arched")}

def opening_lookup(schedule: dict | None) -> dict:
  """mark -> (width_mm, height_mm, type) for the extraction step."""
  out = {}
  for o in (schedule or {}).get("openings") or []:
    out[o["mark"]] = (o["width_mm"], o["height_mm"], o["type"])
  return out