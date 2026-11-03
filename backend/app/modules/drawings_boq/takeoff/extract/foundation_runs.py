from __future__ import annotations
import math
import re
import time
from app.modules.drawings_boq.takeoff.extract import walls as W

MM_FOOT = 304.8
MM_INCH = 25.4
WALL_CLASSES_IN = (4.5, 9.0)
CLASS_TOL_IN = 1.0
PT_MM = 25.4 / 72.0
GUESS_RATIO = 100.0
SCALE_AGREE = 0.02
EDGE_TOL_MM = 450.0
MARKER_REACH_MM = 2400.0
MIN_MARKERS = 3
BOUNDARY, HOUSE, HOUSE_ON_EDGE = "BOUNDARY", "HOUSE", "HOUSE_ON_EDGE"
_MARK = re.compile(r"^W[1-9]$")
_FT_IN = re.compile(r"^(?P<ft>\d{1,3})\s*'\s*(?:-?\s*(?P<in>\d{1,2})(?:\s*(?P<n>\d)/(?P<d>\d))?\s*(?:\"|″|”|'')?)?$")
THICK_OF = {"W1": 4.5, "W2": 4.5, "W3": 9.0, "W4": 9.0}
EXTERIOR_OF = {"W1": False, "W2": True, "W3": False, "W4": True}

def printed_dims_mm(words: list) -> list:
  out: list = []
  for w in words or []:
    m = _FT_IN.match(w.text.strip())
    if not m:
      continue
    inch = int(m.group("in") or 0) + (int(m.group("n")) / int(m.group("d")) if m.group("n") and m.group("d") and int(m.group("d")) else 0.0)
    mm = int(m.group("ft")) * MM_FOOT + inch * MM_INCH
    if mm >= 3000.0:
      out.append(round(mm, 1))
  return sorted(set(out), reverse=True)

def markers(words: list) -> list:
  return [{"mark": w.text.strip(), "x": float(w.cx), "y": float(w.cy)} for w in words or [] if _MARK.match(w.text.strip())]

def is_foundation_plan(words: list) -> bool:
  texts = " ".join(w.text.upper() for w in words or [])
  return "FOUNDATION" in texts and len(markers(words)) >= MIN_MARKERS

def _runs_of(index, f: float, deadline: float) -> tuple:
  frames, runs, _stats = W.detect_walls(index, f, deadline, True, None)
  out: list = []
  for r in runs:
    fr = frames[r.peak]
    out.append({"p0": fr.pt(r.s0 - r.ext0, r.dc), "p1": fr.pt(r.s1 + r.ext1, r.dc), "t_pt": float(r.t_pt)})
  return out

def _extent(runs: list) -> tuple:
  xs = [p[0] for r in runs for p in (r["p0"], r["p1"])]
  ys = [p[1] for r in runs for p in (r["p0"], r["p1"])]
  return min(xs), max(xs), min(ys), max(ys)

def scale_from_dims(extent_pt: tuple, dims_mm: list) -> dict | None:
  long_pt, short_pt = max(extent_pt), min(extent_pt)
  best = None
  for a in dims_mm:
    for b in dims_mm:
      if b >= a or a < 6000.0:
        continue
      fa, fb = a / long_pt, b / short_pt
      if abs(fa - fb) / max(fa, fb) <= SCALE_AGREE and (best is None or a > best["long_mm"]):
        best = {"mm_per_pt": round((fa + fb) / 2.0, 4), "long_mm": a, "short_mm": b, "agree": round(abs(fa - fb) / max(fa, fb), 4)}
        
  return best

def _class_in(t_mm: float) -> float | None:
  inch = t_mm / MM_INCH
  for c in WALL_CLASSES_IN:
    if abs(inch - c) <= CLASS_TOL_IN:
      return c
  return None

def _near(run: dict, m: dict) -> float:
  (x0, y0), (x1, y1) = run["p0"], run["p1"]
  dx, dy = x1 - x0, y1 - y0
  n = dx * dx + dy * dy
  t = 0.0 if n == 0 else max(0.0, min(1.0, ((m["x"] - x0) * dx + (m["y"] - y0) * dy) / n))
  return math.hypot(m["x"] - (x0 + t * dx), m["y"] - (y0 + t * dy))

def _on_edge(run: dict, box: tuple, tol_pt: float) -> bool:
  x0, x1, y0, y1 = box
  (ax, ay), (bx, by) = run["p0"], run["p1"]
  return any(all(abs(v - edge) <= tol_pt for v in vs) for edge, vs in ((x0, (ax, bx)), (x1, (ax, bx)), (y0, (ay, by)), (y1, (ay, by))))

def read(index, words: list, deadline: float | None = None) -> dict | None:
  if not is_foundation_plan(words):
    return None
  stop = deadline or time.monotonic() + 120.0
  first = _runs_of(index, PT_MM * GUESS_RATIO, stop)
  if not first:
    return None

  box = _extent(first)
  dims = printed_dims_mm(words)
  scale = scale_from_dims((box[1] - box[0], box[3] - box[2]), dims)
  if scale is None:
    return {"read": "NO_SCALE", "printed_dims_mm": dims[:8]}
  f = scale["mm_per_pt"]
  runs = _runs_of(index, f, stop)
  box = _extent(runs)
  tol = EDGE_TOL_MM / f
  marks = markers(words)
  
  out: list = []
  for r in runs:
    (ax, ay), (bx, by) = r["p0"], r["p1"]
    length = math.hypot(bx - ax, by - ay) * f
    cls = _class_in(r["t_pt"] * f)
    if cls is None or length < 600.0:
      continue
    edge = _on_edge(r, box, tol)
    
    kind = (BOUNDARY if cls == 4.5 else HOUSE_ON_EDGE) if edge else HOUSE
    fit = [(_near(r, m) * f, m) for m in marks if THICK_OF.get(m["mark"]) == cls and EXTERIOR_OF[m["mark"]] == edge]
    fit = [x for x in fit if x[0] <= MARKER_REACH_MM]
    tag = min(fit, key=lambda x: x[0])[1]["mark"] if fit else None
    assumed = tag is None
    if assumed:
      tag = ("W2" if cls == 4.5 else "W4") if edge else ("W1" if cls == 4.5 else "W3")
    out.append({"p0": [round(ax, 2), round(ay, 2)], "p1": [round(bx, 2), round(by, 2)], "length_mm": round(length, 1), "wall_in": cls, "kind": kind, "mark": tag, "exterior": EXTERIOR_OF[tag], "type_assumed": assumed})
  perimeter = 2.0 * ((box[1] - box[0]) + (box[3] - box[2])) * f
  return {"read": "OK", "mm_per_pt": f, "scale": scale, "box_pt": [round(v, 2) for v in box], "outline_mm": [round((box[1] - box[0]) * f, 1), round((box[3] - box[2]) * f, 1)], "perimeter_mm": round(perimeter, 1),
    "runs": out, "markers": len(marks), "printed_dims_mm": dims[:8]}

def lengths_ft(doc: dict, kinds: tuple | None = None) -> dict:
  out: dict = {}
  for r in doc.get("runs") or []:
    if kinds is None or r["kind"] in kinds:
      out[r["mark"]] = round(out.get(r["mark"], 0.0) + r["length_mm"] / MM_FOOT, 2)
  return out
