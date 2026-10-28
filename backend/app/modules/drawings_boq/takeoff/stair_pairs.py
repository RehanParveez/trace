from __future__ import annotations
import math
from types import SimpleNamespace
from app.modules.drawings_boq.takeoff.prep.facts import FLOOR_ORDER
from app.modules.drawings_boq.takeoff.extract import floor_union as FU
from app.modules.drawings_boq.takeoff.extract import config as C

def level_key(sheet) -> str | None:
  title = ((getattr(sheet, "prep_meta", None) or {}).get("title")) or {}
  return None if title.get("composite") else title.get("level_hint")

def _facts(c) -> dict:
  return getattr(c, "facts", None) or {}

def _view_floor(c) -> str | None:
  return (_facts(c).get("view") or {}).get("level_hint")

def way_of(c) -> str | None:
  w = _facts(c).get("direction")
  return w if w in ("UP", "DOWN") else None

def _width(c) -> float | None:
  w = _facts(c).get("stair_width_mm")
  return float(w) if isinstance(w, (int, float)) else None

def _unlike(a, b) -> float:
  wa, wb = _width(a), _width(b)
  return 0.0 if wa is None or wb is None else abs(wa - wb)

def _widths_agree(a, b) -> bool:
  wa, wb = _width(a), _width(b)
  return wa is None or wb is None or abs(wa - wb) <= C.STAIR_TWIN_WIDTH_TOL * max(wa, wb)

def _mm_per_pt(c) -> float | None:
  v = _facts(c).get("mm_per_pt")
  if v is None:
    v = getattr(c, "mm_per_pt", None)
  try:
    v = float(v)
  except (TypeError, ValueError):
    return None
  return v if v > 0 else None

def _point(c):
  pts = (getattr(c, "geometry", None) or {}).get("points") or []
  return (float(pts[0][0]), float(pts[0][1])) if pts else None

def _box(c):
  b = _facts(c).get("flight_box")
  try:
    x0, y0, x1, y1 = (float(v) for v in b)
  except (TypeError, ValueError):
    p = _point(c)
    return None if p is None else (p[0], p[1], p[0], p[1])
  return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))

def _in_frame(box: tuple, reg) -> tuple:
  if reg is None:
    return box
  x0, y0, x1, y1 = box
  pts = [reg.apply(p) for p in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
  return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))

def _box_gap(a: tuple, b: tuple) -> float:
  dx = max(a[0] - b[2], b[0] - a[2], 0.0)
  dy = max(a[1] - b[3], b[1] - a[3], 0.0)
  return math.hypot(dx, dy)

class _Frames:
  def __init__(self, candidates: list):
    self.rows: dict = {}
    for c in candidates:
      if c.category != "STAIR" and c.decision != "REJECTED":
        self.rows.setdefault(c.sheet_id, []).append(c)
    self.cache: dict = {}

  def between(self, lo_sheet, hi_sheet, mm_lo: float, mm_hi: float) -> tuple:
    key = (lo_sheet, hi_sheet)
    if key in self.cache:
      return self.cache[key]
    out: tuple = (None, None)
    if lo_sheet != hi_sheet:
      reg = None
      try:
        reg = FU.register(self.rows.get(lo_sheet) or [], self.rows.get(hi_sheet) or [])
      except Exception:
        reg = None
      if reg is not None:
        out = ("REGISTERED", reg)
      elif abs(mm_lo - mm_hi) <= C.STAIR_TWIN_SAME_SCALE_TOL * max(mm_lo, mm_hi):
        out = ("SAME_FRAME", None)
    self.cache[key] = out
    return out

def _evidence(lo, hi, frames: _Frames) -> tuple | None:
  mlo, mhi = _mm_per_pt(lo), _mm_per_pt(hi)
  blo, bhi = _box(lo), _box(hi)
  if mlo is None or mhi is None or blo is None or bhi is None:
    return None
  how, reg = frames.between(lo.sheet_id, hi.sheet_id, mlo, mhi)
  if how is None:
    return None
  return _box_gap(blo, _in_frame(bhi, reg)) * mlo, how

def _flights(candidates: list, sheets: dict) -> dict:
  out: dict = {}
  for c in candidates:
    if c.category != "STAIR" or c.decision == "REJECTED" or c.sheet_id not in sheets or (_facts(c).get("external") and not C.STAIR_EXTERNAL_PAIRED):
      continue
    key = level_key(sheets[c.sheet_id]) or _view_floor(c)
    if key in FLOOR_ORDER:
      out.setdefault(key, []).append(c)
  return out

def solve(candidates: list, sheets: dict) -> SimpleNamespace:
  flights = _flights(candidates, sheets)
  frames = _Frames(candidates)
  up = {k: [c for c in v if way_of(c) == "UP"] for k, v in flights.items()}
  down = {k: [c for c in v if way_of(c) == "DOWN"] for k, v in flights.items()}
  up, down = {k: v for k, v in up.items() if v}, {k: v for k, v in down.items() if v}
  pairs: list = []
  hidden: set = set()
  as_upper: set = set()
  as_lower: set = set()
  
  for key in FLOOR_ORDER:
    here = flights.get(key) or []
    if not here:
      continue
    low = [k for k in FLOOR_ORDER[:FLOOR_ORDER.index(key)] if any(way_of(c) in ("UP", None) for c in flights.get(k, []))]
    if not low:
      continue
    lower_key = low[-1]
    lows = [c for c in flights[lower_key] if way_of(c) in ("UP", None) and c.id not in as_lower]
    highs = [c for c in here if way_of(c) in ("DOWN", None) and c.id not in as_upper]
    
    found = []
    for hi in highs:
      for lo in lows:
        if not _widths_agree(lo, hi):
          continue
        ev = _evidence(lo, hi, frames)
        if ev is not None and ev[0] <= C.STAIR_TWIN_REACH_MM:
          found.append((ev[0], str(lo.id), str(hi.id), lo, hi, ev[1]))
          
    found.sort(key=lambda t: t[:3])
    used_lo: set = set()
    used_hi: set = set()
    for gap, _a, _b, lo, hi, how in found:
      if lo.id in used_lo or hi.id in used_hi:
        continue
      used_lo.add(lo.id)
      used_hi.add(hi.id)
      pairs.append(SimpleNamespace(lo=lo, hi=hi, how=how, gap_mm=gap, unknown_way=way_of(hi) is None or way_of(lo) is None))

    pool = [c for c in lows if c.id not in used_lo and way_of(c) == "UP"]
    pool.sort(key=lambda c: (c.decision != "ACCEPTED", sheets[c.sheet_id].page_no, str(c.id)))
    for hi in sorted((c for c in highs if c.id not in used_hi and way_of(c) == "DOWN"), key=lambda c: (c.decision != "ACCEPTED", str(c.id))):
      if any(_evidence(lo, hi, frames) is not None for lo in pool):
        continue
      need = max(1, int(hi.count or 1))
      if len(pool) < need:
        continue
      pool.sort(key=lambda c: _unlike(c, hi))
      owners, pool = pool[:need], pool[need:]
      for lo in owners:
        used_lo.add(lo.id)
        pairs.append(SimpleNamespace(lo=lo, hi=hi, how="ORDER", gap_mm=None, unknown_way=False))
      used_hi.add(hi.id)
    as_lower.update(used_lo)
    as_upper.update(used_hi)
    
  also: dict = {}
  owners_of: dict = {}
  info: dict = {}
  for p in pairs:
    hidden.add(p.hi.id)
    also.setdefault(p.lo.id, []).append(sheets[p.hi.sheet_id].page_no)
    owners_of.setdefault(p.hi.id, []).append(sheets[p.lo.sheet_id].page_no)
    info.setdefault(p.hi.id, {"twin_of_page": sheets[p.lo.sheet_id].page_no, "twin_of": str(p.lo.id), "how": p.how,
      "gap_m": None if p.gap_mm is None else round(p.gap_mm / 1000.0, 2), "unknown_way": p.unknown_way})
    
  also = {k: sorted(set(v)) for k, v in also.items()}
  owners_of = {k: sorted(set(v)) for k, v in owners_of.items()}
  lone: list = []
  have_up = {k for k, v in up.items() if v}
  have_down = {k for k, v in down.items() if v}
  
  for key, fl in down.items():
    if any(k in have_up for k in FLOOR_ORDER[:FLOOR_ORDER.index(key)]):
      lone.extend(d.id for d in fl if d.id not in owners_of)
  for key, fl in up.items():
    if any(k in have_down for k in FLOOR_ORDER[FLOOR_ORDER.index(key) + 1:]):
      lone.extend(u.id for u in fl if u.id not in also)
  return SimpleNamespace(pairs=pairs, hidden=hidden, also=also, owners=owners_of, up=up, down=down, lone=lone, info=info)

def sightings(candidates: list, sheets: dict) -> dict:
  return {k: v["twin_of_page"] for k, v in solve(candidates, sheets).info.items()}

def sheets_of(read: list) -> dict:
  return {s["sheet_id"]: SimpleNamespace(id=s["sheet_id"], page_no=s["page_no"], prep_meta={"title": s.get("title") or {}}) for s in read if s.get("sheet_id") is not None}
