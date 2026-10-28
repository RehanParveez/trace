from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.prep.texts import parse_dimension, is_tag
from app.modules.drawings_boq.takeoff.prep import schedules as S
from app.modules.drawings_boq.takeoff.prep import mark_vocab as MV
from app.modules.drawings_boq.takeoff.prep.census import _is_rectangle, dense_flags
import math
from bisect import bisect_left, bisect_right
from statistics import median

_SIZE = re.compile(r"(?P<a>\d[\d.,'\"′″½¼¾\-\s]*?)\s*[xX×]\s*(?P<b>\d[\d.,'\"′″½¼¾\-\s]*)")

def category_of(tag: str, vocab: dict | None = None, discipline: str | None = None, plan_kind: str | None = None) -> str | None:
  return MV.category_of(tag, vocab, discipline, plan_kind)

def _round5(v: float) -> float:
  return float(round(v / 5.0) * 5)

def _pick_reading(text: str, hint: str | None) -> float | None:
  rs = parse_dimension(text.strip(), hint)
  if not rs:
    return None
  return max(rs, key=lambda r: r.prior).value_mm

def _reading(text: str, hint: str | None, from_end: bool) -> float | None:
  tokens = text.split()
  pieces = [" ".join(tokens[i:]) for i in range(len(tokens))] if from_end else [" ".join(tokens[:i]) for i in range(len(tokens), 0, -1)]
  for piece in pieces:
    v = _pick_reading(piece, hint)
    if v is not None:
      return v
  return None

def parse_size(text: str, hint: str | None) -> tuple | None:
  
  for m in _SIZE.finditer(text or ""):
    a = _reading(m.group("a"), hint, True)
    b = _reading(m.group("b"), hint, False)
    if a is not None and b is not None:
      return (_round5(a), _round5(b))
  return None

def member_shapes(rings: list, mm_per_pt: float) -> list[dict]:

  lo, hi = C.MEMBER_MIN_MM / mm_per_pt, C.MEMBER_MAX_MM / mm_per_pt
  out = []
  for r in rings:
    w, h = r.bbox[2] - r.bbox[0], r.bbox[3] - r.bbox[1]
    if min(w, h) < lo or max(w, h) > hi:
      continue
    rect = _is_rectangle(r.pts) if not r.curved else None
    if rect is not None:
      a, b = sorted(rect)
      kind = "RECT"
    elif r.curved and len(r.pts) >= 8 and abs(w - h) <= 0.04 * max(w, h):
      a = b = (w + h) / 2.0
      kind = "CIRCLE"
    else:
      continue
    out.append({"cx": (r.bbox[0] + r.bbox[2]) / 2.0, "cy": (r.bbox[1] + r.bbox[3]) / 2.0, "a": a * mm_per_pt, "b": b * mm_per_pt,
      "kind": kind, "fill": bool(r.fill)})
  return out

def match_shapes(points: list, shapes: list, radius_pt: float) -> list:
  
  pairs = []
  for i, (x, y) in enumerate(points):
    for j, s in enumerate(shapes):
      d = math.hypot(s["cx"] - x, s["cy"] - y)
      if d <= radius_pt:
        pairs.append((d, i, j))
        
  pairs.sort()
  used_i, used_j = set(), set()
  out = [None] * len(points)
  for d, i, j in pairs:
    if i in used_i or j in used_j:
      continue
    used_i.add(i)
    used_j.add(j)
    out[i] = shapes[j]
  return out

_PLAUSIBLE = {  
  "COLUMN": ((100.0, 1500.0), (100.0, 1500.0)), "FOOTING": ((300.0, 6000.0), (300.0, 6000.0)),
  "BEAM": ((100.0, 1500.0), (100.0, 1500.0)), "DOOR": ((500.0, 3600.0), (1500.0, 3300.0)),
  "WINDOW": ((300.0, 4000.0), (300.0, 3300.0)),
}

def _plausible(cat: str, size: tuple) -> bool:
  (a0, a1), (b0, b1) = _PLAUSIBLE.get(cat, ((0.0, 1e9), (0.0, 1e9)))
  a, b = size
  return (a0 <= a <= a1 and b0 <= b <= b1) or (a0 <= b <= a1 and b0 <= a <= b1)

HEADERS = {"MARK", "MARKS", "MK", "TAG", "ID", "NO", "REF", "TYPE", "SYMBOL", "SR", "S.NO"}

def schedule_rows(words: list, hint: str | None, vocab: dict | None = None, discipline: str | None = None, plan_kind: str | None = None) -> tuple:

  tag_of = {id(w): is_tag(w.text) for w in words}
  cat_of = {id(w): category_of(w.text, vocab, discipline, plan_kind) for w in words if tag_of[id(w)]}
  marks = [w for w in words if tag_of[id(w)] and MV.counted(cat_of[id(w)])]
  if not marks:
    return {}, set()
  
  by_y = sorted(words, key=lambda o: o.cy)
  ys = [o.cy for o in by_y]
  tags_y = [o for o in by_y if tag_of[id(o)]]
  tag_ys = [o.cy for o in tags_y]
  max_size = max((o.size for o in words), default=1.0)
  rows: dict = {}
  row_ids: set = set()
  
  for w in marks:
    size_w = max(w.size, 1.0)
    lo, hi = bisect_left(tag_ys, w.cy - 18 * size_w), bisect_right(tag_ys, w.cy + 18 * size_w)
    stacked = any(o is not w and abs(o.x0 - w.x0) <= 2.5 for o in tags_y[lo:hi])
    if not stacked:  
      stacked = any(o.text.strip().upper().rstrip(".:") in HEADERS and abs(o.x0 - w.x0) <= 2.5 and abs(o.cy - w.cy) <= 4 * size_w
        for o in by_y[bisect_left(ys, w.cy - 4 * size_w):bisect_right(ys, w.cy + 4 * size_w)])
    if not stacked:
      continue
    reach = 0.6 * max(size_w, max_size)
    near = by_y[bisect_left(ys, w.cy - reach):bisect_right(ys, w.cy + reach)]
    line = [o for o in near if o is not w and abs(o.cy - w.cy) <= 0.6 * max(size_w, o.size) and o.x0 > w.x1 - 0.5
      and (o.x0 - w.x1) <= 40 * size_w]
    line.sort(key=lambda o: o.cx)
    chain, last = [], w
    
    for o in line:
      if o.x0 - last.x1 > (40 if last is w else 8) * size_w:
        break
      chain.append(o)
      last = o
    if not chain:
      continue
    size = parse_size(" ".join(o.text for o in chain), hint)
    if size is None or not _plausible(cat_of[id(w)], size):
      continue
    rows.setdefault(w.text.strip().upper(), []).append(size)
    row_ids.add(id(w))
  return {k: max(set(v), key=v.count) for k, v in rows.items()}, row_ids

def height_hints(lines: list, hint: str | None) -> dict:
  out: dict = {}
  for ln in lines:
    for cat, pat in C.HEIGHT_NOTES:
      m = pat.search(ln.text)
      if not m or cat in out:
        continue
      rs = parse_dimension(m.group("v").strip().rstrip(".,;"), hint) or parse_dimension(re.split(r"\s", m.group("v").strip())[0], hint)
      if not rs:
        continue
      mm = max(rs, key=lambda r: r.prior).value_mm
      if 1500.0 <= mm <= 6500.0:
        out[cat] = {"mm": _round5(mm), "text": ln.text[:80]}
  return out

def tag_members(words: list, shapes: list, mm_per_pt: float, hint: str | None, openings: dict | None = None, plan_view: bool = False,
  vocab: dict | None = None, discipline: str | None = None, plan_kind: str | None = None, skipped: dict | None = None) -> list[dict]:
  openings = openings or {}
  kind = {"vocab": vocab, "discipline": discipline, "plan_kind": plan_kind}

  flags = dense_flags(words) if words and not plan_view else [False] * len(words)
  sched, row_ids = schedule_rows(words, hint, **kind)
  table_ids = S.table_marks(words) if words else set()
  if openings:
    row_ids = row_ids - {id(w) for w in words if category_of(w.text, **kind) in ("DOOR", "WINDOW")}
  groups: dict = {}
  for w, dense in zip(words, flags):
    if not is_tag(w.text):
      continue
    cat = category_of(w.text, **kind)
    if cat is None:
      continue
    if not MV.counted(cat):
      if skipped is not None:
        row = skipped.setdefault(w.text.strip().upper(), {"tag": w.text.strip().upper(), "category": cat, "count": 0, "points": []})
        row["count"] += 1
        if len(row["points"]) < 60:
          row["points"].append([round(w.cx, 4), round(w.cy, 4)])
      continue
    mk = S.norm_mark(w.text)
    if mk and S.mark_type(mk) == "VENTILATOR" and mk not in openings:
      continue  
    key = w.text.strip().upper()
    g = groups.setdefault(key, {"tag": key, "category": cat, "points": [], "dense": 0})
    if dense or id(w) in row_ids or id(w) in table_ids:
      g["dense"] += 1
      
    else:
      g["points"].append([round(w.cx, 4), round(w.cy, 4)])
  radius = C.MEMBER_SEARCH_MM / mm_per_pt
  out = []
  for key, g in groups.items():
    pts = g["points"]
    if not pts:
      continue
    drawn = []
    if g["category"] in ("COLUMN", "FOOTING"):
      pool = [s for s in shapes if _plausible(g["category"], (s["a"], s["b"]))]
      want = sched.get(key)
      if want:
        close = [s for s in pool if abs(s["a"] - min(want)) <= C.SIZE_TOL * min(want) + 5 and abs(s["b"] - max(want)) <= C.SIZE_TOL * max(want) + 5]
        pool = close or pool
      found = [s for s in match_shapes(pts, pool, radius) if s is not None]
      drawn = [(s["a"], s["b"]) for s in found]
    entry = {"tag": key, "category": g["category"], "points": pts, "count": len(pts), "schedule_rows": g["dense"], "matched": len(drawn)}
    
    if drawn:
      a = _round5(median(d[0] for d in drawn))
      b = _round5(median(d[1] for d in drawn))
      spread = max(max(abs(d[0] - a) / a, abs(d[1] - b) / b) for d in drawn)
      entry["drawn_mm"] = (a, b)
      entry["spread"] = spread
    if key in sched:
      entry["schedule_mm"] = sched[key]
    if g["category"] in ("DOOR", "WINDOW") and openings:
      row = openings.get(S.norm_mark(key) or key)
      if row:
        entry["schedule_mm"] = (row[0], row[1])
        entry["opening_kind"] = row[2]
      else:
        entry["schedule_missing"] = True
    out.append(entry)
  out.sort(key=lambda e: (e["category"], e["tag"]))
  return out
