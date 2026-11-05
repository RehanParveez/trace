from __future__ import annotations
import re
import numpy as np
from shapely.geometry import LineString, Polygon, Point
from shapely.ops import polygonize, unary_union
from app.modules.drawings_boq.takeoff.extract import slab_panels as SPL
from app.modules.drawings_boq.takeoff.prep import views as VW

INCH_MM = 25.4
FT_MM = 304.8
SNAP_IN = 36.0
MIN_PANEL_M2 = 1.0
RECT_FILL = 0.97
AXIS_TOL = 0.05
EDGE_MIN_MM = 600.0
EDGE_MIN_COUNT = 15
EDGE_WEIGHT_SHARE = 0.9
SQUARE_SHARE = 0.05
MIN_BANDS = 3
VOID_RE = re.compile(r"\b(STAIR\s*VOID|VOID|OPENING|OPEN\s+TO\s+(?:BELOW|SKY))\b", re.I)
STAIR_RE = re.compile(r"STAIR", re.I)
CANTILEVER_RE = re.compile(r"\b(CANTILEVER|CANTI|SUNSHADE|CHAJJA|PROJECTION)\b", re.I)

def _pt(inches: float, mm_per_pt: float) -> float:
  return inches * INCH_MM / mm_per_pt

def _lines(bands: list, mm_per_pt: float) -> list:
  out = []
  for b in bands:
    (x0, y0), (x1, y1) = b["polyline"]
    out.append({"axis": b["axis"], "p0": (x0, y0), "p1": (x1, y1), "half": _pt(float(b["width_in"]), mm_per_pt) / 2.0, "mark": b.get("mark")})
  return out

def edge_lines(index, bbox: tuple, mm_per_pt: float, unit: float = 1.0) -> list:
  segs = np.asarray(index.segs, dtype=float).reshape(-1, 5)
  kinds = np.asarray(index.kinds, dtype=int)
  ln = np.hypot(segs[:, 2] - segs[:, 0], segs[:, 3] - segs[:, 1])
  inside = (segs[:, 0] >= bbox[0]) & (segs[:, 0] <= bbox[2]) & (segs[:, 1] >= bbox[1]) & (segs[:, 1] <= bbox[3])
  axis = (np.abs(segs[:, 0] - segs[:, 2]) < AXIS_TOL * unit) | (np.abs(segs[:, 1] - segs[:, 3]) < AXIS_TOL * unit)
  long_ = segs[(ln >= EDGE_MIN_MM / mm_per_pt) & axis & (kinds == 0) & inside]
  
  if len(long_) == 0:
    return []
  widths, counts = np.unique(np.round(long_[:, 4], 2), return_counts=True)
  heavy = [w for w, c in zip(widths, counts) if c >= EDGE_MIN_COUNT and w > 0]
  if not heavy:
    return []
  keep = long_[long_[:, 4] >= EDGE_WEIGHT_SHARE * max(heavy)]
  return [((float(x0), float(y0)), (float(x1), float(y1))) for x0, y0, x1, y1, _w in keep]

def band_edges(bands: list, mm_per_pt: float) -> list:
  out = []
  for b in bands:
    (x0, y0), (x1, y1) = b["polyline"]
    h = _pt(float(b["width_in"]), mm_per_pt) / 2.0
    if b["axis"] == "H":
      out += [((x0, y0 - h), (x1, y0 - h)), ((x0, y0 + h), (x1, y0 + h))]
    else:
      out += [((x0 - h, y0), (x0 - h, y1)), ((x0 + h, y0), (x0 + h, y1))]
  return out

def _carry(seg: tuple, reach: float) -> tuple:
  (x0, y0), (x1, y1) = seg
  if abs(y1 - y0) <= abs(x1 - x0):
    a, b = sorted((x0, x1))
    return (a - reach, y0), (b + reach, y0)
  a, b = sorted((y0, y1))
  return (x0, a - reach), (x0, b + reach)

def faces_of(edges: list, mm_per_pt: float, extra: list | None = None) -> list:
  reach = _pt(SNAP_IN, mm_per_pt)
  geoms = [LineString(_carry(e, reach)) for e in edges] + [LineString(w) for w in extra or []]
  if not geoms:
    return []
  floor = MIN_PANEL_M2 * 1e6 / (mm_per_pt * mm_per_pt)
  return [f for f in polygonize(unary_union(geoms)) if f.area >= floor]

def spans(face: Polygon, mm_per_pt: float) -> dict:
  x0, y0, x1, y1 = face.bounds
  fill = face.area / max((x1 - x0) * (y1 - y0), 1e-9)
  if fill < RECT_FILL:
    return {"x_ft": None, "y_ft": None, "status": "UNSURE", "why": "NOT_RECTANGULAR", "fill": round(fill, 3)}
  return {"x_ft": round((x1 - x0) * mm_per_pt / FT_MM, 2), "y_ft": round((y1 - y0) * mm_per_pt / FT_MM, 2), "status": "SURE", "why": None, "fill": round(fill, 3)}

def _callouts(index, bbox, faces: list, lines: list, mm_per_pt: float) -> tuple:
  strings = SPL.tagged_strings(index, bbox)
  bars = SPL.bar_lines(index, bbox)
  pairs, _unbound = SPL._bind([s for s in strings if s.get("tag") != "TOP"], bars)
  axis_of = {id(s): ln for s, ln in pairs}
  per_face: list = [[] for _ in faces]
  
  tops, orphans = [], []
  for s in strings:
    where = Point(s["x"], s["y"])
    if s.get("tag") == "TOP":
      near = min(lines, key=lambda ln: LineString([ln["p0"], ln["p1"]]).distance(where), default=None)
      tops.append({"text": s["text"], "support": (near or {}).get("mark"), "at": [round(s["x"], 2), round(s["y"], 2)]})
      continue
    ln = axis_of.get(id(s))
    rec = {"text": s["text"], "bar": s["bar"], "spacing_in": s["spacing_in"], "axis": ln["axis"] if ln else s["axis"], "direction_from": "DIMENSION_LINE" if ln else "TEXT", "tag": s.get("tag"), "at": [round(s["x"], 2), round(s["y"], 2)]}
    for i, f in enumerate(faces):
      if f.contains(where):
        per_face[i].append(rec)
        break
    else:
      orphans.append(rec)
  return per_face, tops, orphans

def _roles(callouts: list, sp: dict) -> None:
  x, y = sp.get("x_ft"), sp.get("y_ft")
  if not x or not y or abs(x - y) <= SQUARE_SHARE * max(x, y):
    for c in callouts:
      c["role"] = "UNSURE"
    return
  short = "X" if x < y else "Y"
  for c in callouts:
    c["role"] = "MAIN" if c["axis"] == short else "DISTRIBUTION"

def _poly(f: Polygon) -> list:
  return [[round(x, 3), round(y, 3)] for x, y in list(f.exterior.coords)[:-1]]

def build(bands: list, index, bbox: tuple, mm_per_pt: float, words: list, unit: float = 1.0, *, walls: list | None = None, edge: Polygon | None = None, rooms: list | None = None) -> dict:
  lines = _lines(bands, mm_per_pt)
  edges = edge_lines(index, bbox, mm_per_pt, unit) + band_edges(bands, mm_per_pt)
  faces = faces_of(edges, mm_per_pt, ([edge.exterior.coords[:]] if edge is not None else []) + list(walls or []))
  per_face, tops, orphans = _callouts(index, bbox, faces, lines, mm_per_pt)
  order = sorted(range(len(faces)), key=lambda i: (round(faces[i].centroid.y, 0), round(faces[i].centroid.x, 0)))
  
  panels = []
  for i in order:
    f, calls = faces[i], per_face[i]
    sp = spans(f, mm_per_pt)
    _roles(calls, sp)
    inside = [w for w in words if f.contains(Point(w[1], w[2]))]
    text = " ".join(w[0] for w in inside)
    marks = sorted({w[0].strip().upper() for w in inside if VW._SLAB_PANEL.match(w[0].strip().upper())})
    void = bool(VOID_RE.search(text))
    
    flags = []
    if void:
      flags.append("STAIR_VOID" if STAIR_RE.search(text) else "VOID")
    if CANTILEVER_RE.search(text):
      flags.append("CANTILEVER")
    if any(len({(c["bar"], c["spacing_in"]) for c in calls if c["axis"] == ax}) > 1 for ax in ("X", "Y")):
      flags.append("TWO_PANELS_ONE_FACE")
    named = [r["name"] for r in rooms or [] if f.contains(Point(r["at"][0], r["at"][1]))]
    panels.append({"polygon": _poly(f), "area_m2": round(f.area * mm_per_pt * mm_per_pt / 1e6, 3), "clear_span_x_ft": sp["x_ft"], "clear_span_y_ft": sp["y_ft"], "spans": sp["status"], "spans_why": sp["why"],
      "mark": marks[0] if len(marks) == 1 else None, "marks_inside": marks, "void": void, "room": named[0] if len(named) == 1 else None, "callouts": calls, "flags": flags,
      "reasons": (["SPANS_UNSURE"] if sp["status"] != "SURE" and not void else []) + (["CALLOUT_ROLE_UNSURE"] if any(c["role"] == "UNSURE" for c in calls) else [])})
  return {"panels": panels, "top_extra": tops, "callouts_outside_panels": orphans, "stats": {"bands": len(bands), "faces": len(faces), "voids": sum(p["void"] for p in panels), "rectangular_sure": sum(p["spans"] == "SURE" for p in panels),
    "callouts": sum(len(p["callouts"]) for p in panels), "callouts_outside": len(orphans), "top_extra": len(tops)}}

def of_page(index, bands: dict | None, views: list, mm_per_pt: float, unit: float = 1.0) -> dict | None:
  if not bands or not mm_per_pt:
    return None
  by_key = {v["key"]: v for v in views}
  
  out = []
  for vb in bands.get("views") or []:
    v = by_key.get(vb.get("key"))
    if v is None or len(vb.get("bands") or []) < MIN_BANDS:
      continue
    bbox = tuple(float(x) for x in v["bbox"])
    words = [(w.text, w.cx, w.cy) for w in index.words if VW.contains(v, w.cx, w.cy)]
    res = build(vb["bands"], index, bbox, mm_per_pt, words, unit)
    out.append({"key": vb.get("key"), "level_hint": vb.get("level_hint"), **res})
  return {"views": out, "mm_per_pt": round(float(mm_per_pt), 5)} if out else None
