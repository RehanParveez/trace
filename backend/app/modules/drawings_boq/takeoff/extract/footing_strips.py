from __future__ import annotations
import collections
import math
import time
from app.engine.measure import rule_registry as RR
from app.modules.drawings_boq.takeoff.extract import foundation_runs as FR
from app.modules.drawings_boq.takeoff.extract import walls as W

RULE = "FOOTING_RUNS_FROM_GRID"
META_KEY = "footing_strip_runs"
CLASSES_IN = (4.5, 9.0, 13.5)
CLASS_TOL_IN = 1.0
MIN_BUBBLES = 4
ROW_TOL_PT = 3.0
MIN_RUN_MM = 600.0
LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ"

def enabled() -> bool:
  return RR.on(RULE)

def _tokens(words: list) -> list:
  out = []
  for w in words or []:
    t = (w.text or "").strip()
    if len(t) == 1 and t in LETTERS:
      out.append(("L", t, float(w.cx), float(w.cy)))
    elif t.isdigit() and 1 <= int(t) <= 60:
      out.append(("N", t, float(w.cx), float(w.cy)))
  return out

def _best_line(items: list, across: int) -> tuple | None:
  rows: dict = collections.defaultdict(list)
  for kind, text, x, y in items:
    rows[round((y if across == 1 else x) / ROW_TOL_PT)].append((text, x if across == 1 else y))
  best = None
  
  for members in rows.values():
    labels = {t for t, _ in members}
    if len(labels) < MIN_BUBBLES:
      continue
    pos = [p for _, p in members]
    cand = (max(pos) - min(pos), len(labels))
    if best is None or cand[1] > best[1]:
      best = cand
  return best

def grid_extents(words: list) -> tuple | None:
  toks = _tokens(words)
  row = _best_line([t for t in toks if t[0] == "L"], 1)
  col = _best_line([t for t in toks if t[0] == "N"], 0)
  if row is None or col is None:
    return None
  return col[0], row[0]

def scale_from_grid(words: list) -> dict | None:
  ext = grid_extents(words)
  if ext is None:
    return None
  return FR.scale_from_dims(ext, FR.printed_dims_mm(words))

def is_strip_plan(words: list) -> bool:
  texts = " ".join((w.text or "").upper() for w in words or [])
  tagged = sum(1 for w in words or [] if (w.text or "").strip().upper().startswith("F") and (w.text or "").strip()[1:].isdigit())
  return ("FOOTING" in texts or "FOUNDATION" in texts) and tagged >= 1 and grid_extents(words) is not None

def class_of(t_mm: float) -> float | None:
  inch = t_mm / FR.MM_INCH
  for c in CLASSES_IN:
    if abs(inch - c) <= CLASS_TOL_IN:
      return c
  return None

def summarize(runs: list, mm_per_pt: float) -> dict:
  by: dict = collections.defaultdict(float)
  other = 0.0
  kept = []
  
  for r in runs:
    (ax, ay), (bx, by_) = r["p0"], r["p1"]
    mm = math.hypot(bx - ax, by_ - ay) * mm_per_pt
    cls = class_of(r["t_pt"] * mm_per_pt)
    if cls is None or mm < MIN_RUN_MM:
      other += mm / FR.MM_FOOT
      continue
    by[cls] += mm / FR.MM_FOOT
    kept.append({"p0": [round(ax, 2), round(ay, 2)], "p1": [round(bx, 2), round(by_, 2)], "length_mm": round(mm, 1), "wall_in": cls})
  return {"lengths_ft": {str(k): round(v, 2) for k, v in sorted(by.items())}, "other_ft": round(other, 2), "runs": kept}

def read(index, words: list, deadline: float | None = None) -> dict | None:
  if not enabled() or FR.is_foundation_plan(words) or not is_strip_plan(words):
    return None
  scale = scale_from_grid(words)
  if scale is None:
    return {"read": "NO_SCALE", "printed_dims_mm": FR.printed_dims_mm(words)[:8], "grid_pt": list(grid_extents(words) or [])}
  f = scale["mm_per_pt"]
  stop = deadline or time.monotonic() + 120.0
  frames, found, _stats = W.detect_walls(index, f, stop, True, None)
  runs = []
  
  for r in found:
    fr = frames[r.peak]
    runs.append({"p0": fr.pt(r.s0 - r.ext0, r.dc), "p1": fr.pt(r.s1 + r.ext1, r.dc), "t_pt": float(r.t_pt)})
  doc = summarize(runs, f)
  tags = collections.Counter((w.text or "").strip().upper() for w in words if (w.text or "").strip().upper()[:1] == "F" and (w.text or "").strip()[1:].isdigit())
  return {"read": "OK", "mm_per_pt": f, "scale": scale, "tags": dict(tags), **doc}
