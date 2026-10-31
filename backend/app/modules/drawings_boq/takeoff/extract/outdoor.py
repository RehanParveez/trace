from __future__ import annotations
import math
import re
from shapely.geometry import Point, Polygon, box
from app.modules.drawings_boq.takeoff.extract import roof_walls as RW
from shapely.ops import unary_union
from app.modules.drawings_boq.takeoff.prep import schedules as S
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.extract import finish_rules as FR
from app.modules.drawings_boq.takeoff.prep.texts import build_lines

PASSAGE, DRIVE, PORCH, RAMP, COURTYARD, LAWN, OPEN_SITE = "PASSAGE", "DRIVE", "PORCH", "RAMP", "COURTYARD", "LAWN", "OPEN_SITE"
VOCAB = (
  (LAWN, re.compile(r"\b(?:LAWN|GARDEN)\b")),
  (COURTYARD, re.compile(r"\bCOURT[\s-]?YARD\b")),
  (RAMP, re.compile(r"\bRAMP\b")),
  (DRIVE, re.compile(r"\b(?:DRIVE(?:WAY)?|PARKING|CAR\s+PORCH)\b")),
  (PORCH, re.compile(r"\bPORCH\b")),
  (PASSAGE, re.compile(r"\b(?:PASSAGE|WALKWAY)\b")),
)
TEXT = {PASSAGE: "Paving of the passages", DRIVE: "Paving of the drive and parking", PORCH: "Paving of the open porch", RAMP: "Paving of the ramp", COURTYARD: "Paving of the courtyard",
  LAWN: "Lawn", OPEN_SITE: "Open site"}
ITEMS = ("SITE_REGION", "SITE_LAYER")
WORK_ITEM: dict = {}
PRINTED_WIDTH = re.compile(r"(?P<dim>\d+\s*'\s*-?\s*\d*(?:\s*\d+/\d+)?\s*\"?)\s*WIDE\b")

MIN_SIDE_SHARE = 0.2
GAP_SHARE = 0.06
COVER_MIN = 0.85
RUNS_MAX = 80
SAME_LINE_MM = 15.0
RATIO_MIN = 1.05
HOLD_SLACK_MM = 500.0
PAGE_SHARE_MAX = 0.8
EDGE_SHARE = 0.02
ON_FRAME_MM = 450.0
ON_FRAME_SHARE = 0.8
MIN_WIDTH_MM = 600.0
MIN_AREA_M2 = 1.0
WIDTH_AGREE = 0.08
LABEL_REACH = 0.8

def _runs(index, horizontal: bool, min_run: float, gap: float, tol: float) -> list:
  import numpy as np
  a = np.frombuffer(index.segs, dtype=np.float32).reshape(-1, 5)
  if not len(a):
    return []
  x1, y1, x2, y2 = a[:, 0], a[:, 1], a[:, 2], a[:, 3]
  if horizontal:
    keep = (np.abs(y1 - y2) <= tol) & (np.abs(x2 - x1) >= tol)
    c, lo, hi = (y1 + y2) / 2.0, np.minimum(x1, x2), np.maximum(x1, x2)
  else:
    keep = (np.abs(x1 - x2) <= tol) & (np.abs(y2 - y1) >= tol)
    c, lo, hi = (x1 + x2) / 2.0, np.minimum(y1, y2), np.maximum(y1, y2)
  rows = sorted(zip(c[keep].tolist(), lo[keep].tolist(), hi[keep].tolist()))
  groups: list = []
  for coord, l, h in rows:
    if groups and coord - groups[-1][0] <= tol:
      groups[-1][1].append((l, h))
    else:
      groups.append((coord, [(l, h)]))
      
  out = []
  for coord, spans in groups:
    spans.sort()
    merged = [list(spans[0])]
    for l, h in spans[1:]:
      if l <= merged[-1][1] + gap:
        merged[-1][1] = max(merged[-1][1], h)
      else:
        merged.append([l, h])
    if max(h - l for l, h in merged) >= min_run:
      out.append((coord, [(l, h) for l, h in merged]))
  out.sort(key=lambda r: -sum(h - l for l, h in r[1]))
  return out[:RUNS_MAX]

def _cover(spans: list, a: float, b: float) -> float:
  got = sum(max(0.0, min(h, b) - max(l, a)) for l, h in spans)
  return got / max(b - a, 1e-9)

def rectangles(index, page: tuple, within: tuple, f: float, slack: float = 0.0) -> list:
  pw, ph = page[2] - page[0], page[3] - page[1]
  min_run, gap = MIN_SIDE_SHARE * min(pw, ph), GAP_SHARE * max(pw, ph)
  tol = SAME_LINE_MM / f
  vs, hs = _runs(index, False, min_run, gap, tol), _runs(index, True, min_run, gap, tol)
  wx0, wy0, wx1, wy1 = within
  found = []
  
  for xl, sl in vs:
    if xl > wx0 + slack:
      continue
    for xr, sr in vs:
      if xr < wx1 - slack or xr - xl < min_run:
        continue
      across = [(y, s) for y, s in hs if _cover(s, xl, xr) >= COVER_MIN]
      for yb, sb in across:
        if yb > wy0 + slack:
          continue
        for yt, st in across:
          if yt < wy1 - slack or yt - yb < min_run:
            continue
          if _cover(sl, yb, yt) >= COVER_MIN and _cover(sr, yb, yt) >= COVER_MIN:
            found.append((xl, yb, xr, yt))
            
  page_area = pw * ph
  out = []
  for r in sorted(set(found), key=lambda r: (r[2] - r[0]) * (r[3] - r[1])):
    area = (r[2] - r[0]) * (r[3] - r[1])
    near_edge = r[0] - page[0] < EDGE_SHARE * pw or page[2] - r[2] < EDGE_SHARE * pw or r[1] - page[1] < EDGE_SHARE * ph or page[3] - r[3] < EDGE_SHARE * ph
    if area <= PAGE_SHARE_MAX * page_area and not near_edge:
      out.append(r)
  return out

def _extent(rooms: list) -> tuple | None:
  shapes = RW._room_shapes(rooms)
  if not shapes:
    return None
  g = unary_union(shapes)
  return g.bounds

def plot_frame(index, rooms: list, page: tuple, labels: list, f: float) -> dict | None:
  extent = _extent(rooms)
  if extent is None:
    return None
  spanned = (extent[2] - extent[0]) * (extent[3] - extent[1])
  for r in rectangles(index, page, extent, f, HOLD_SLACK_MM / f):
    area = (r[2] - r[0]) * (r[3] - r[1])
    if spanned > 0.0 and area >= RATIO_MIN * spanned and all(r[0] <= x <= r[2] and r[1] <= y <= r[3] for x, y in labels):
      return {"box": r, "ratio": round(area / spanned, 3)}
  return None

def footprint(walls: list, rooms: list, frame, f: float):
  band = frame.exterior.buffer(ON_FRAME_MM / f)
  parts = []
  for w in walls:
    if not RW._live(w):
      continue
    ln = RW._line(w)
    if ln.length > 0.0 and ln.intersection(band).length >= ON_FRAME_SHARE * ln.length:
      continue
    parts.append(ln.buffer(RW._half_pt(w, f), cap_style=3))
  parts.extend(RW._room_shapes(rooms))
  if not parts:
    return None
  reach = C.OUTLINE_CLOSE_MM / f
  joined = unary_union(parts).buffer(reach, join_style=2).buffer(-reach, join_style=2)
  rings = [Polygon(g.exterior) for g in (joined.geoms if hasattr(joined, "geoms") else [joined]) if not g.is_empty]
  return unary_union(rings).intersection(frame) if rings else None

def _lines(words: list) -> list:
  out = []
  for ln in build_lines(words):
    text = re.sub(r"\s+", " ", ln.text.upper()).strip()
    kind = next((k for k, pat in VOCAB if pat.search(text)), None)
    if kind is None:
      continue
    ws = [w for _a, _b, w in ln.spans]
    if not ws:
      continue
    m = PRINTED_WIDTH.search(text)
    width = S.feet_inches_mm(m.group("dim").strip()) if m else None
    out.append((text, sum(w.cx for w in ws) / len(ws), sum(w.cy for w in ws) / len(ws), max(w.height for w in ws), kind, width if width and width > 0 else None))
  return out

def _strip_width(area: float, perimeter: float) -> float:
  return (perimeter - math.sqrt(max(perimeter * perimeter - 16.0 * area, 0.0))) / 4.0

def regions(frame, foot, words: list, f: float) -> list:
  if foot is None:
    return []
  rest = frame.difference(foot)
  r = MIN_WIDTH_MM / 2.0 / f
  rest = rest.buffer(-r, join_style=2).buffer(r, join_style=2)
  pieces = [g for g in (rest.geoms if hasattr(rest, "geoms") else [rest]) if not g.is_empty and g.area * f * f / 1e6 >= MIN_AREA_M2]
  lines = _lines(words)
  
  out = []
  for g in pieces:
    inside = []
    for text, x, y, h, kind, width in lines:
      p = Point(x, y)
      if g.contains(p) or g.distance(p) <= LABEL_REACH * h:
        inside.append((text, kind, width))
        
    kinds = sorted({k for _t, k, _w in inside})
    kind = kinds[0] if len(kinds) == 1 else OPEN_SITE
    width = _strip_width(g.area, g.length)
    printed = sorted({w for _t, k, w in inside if k == PASSAGE and w})
    out.append({"kind": kind, "mixed": kinds if len(kinds) > 1 else None, "area_m2": round(g.area * f * f / 1e6, 3), "labels": [t for t, _k, _w in inside], "width_mm": round(width * f, 1),
      "printed_mm": printed, "polygon": [[round(x, 3), round(y, 3)] for x, y in list(g.exterior.coords)[:-1]]})
  out.sort(key=lambda r: -r["area_m2"])
  return out

def width_check(region: dict) -> dict | None:
  printed = region.get("printed_mm") or []
  if region["kind"] != PASSAGE or not printed:
    return None
  want = printed[0]
  got = region["width_mm"]
  return {"printed_mm": round(want, 1), "measured_mm": got, "agrees": abs(got - want) <= WIDTH_AGREE * want}

def _centre(polygons: list) -> list:
  pts = [p for poly in polygons for p in poly]
  return [round(sum(p[0] for p in pts) / len(pts), 4), round(sum(p[1] for p in pts) / len(pts), 4)]

def read(index, walls: list, rooms: list, f: float, ctx: dict, level_hint: str | None, spec, cls, finish, make) -> dict:
  words = index.words
  want = _lines(words)
  result: dict = {"candidates": [], "notes": [], "stats": {}}
  if not want:
    return result
  frame = plot_frame(index, rooms, index.bbox, [(x, y) for _t, x, y, _h, _k, _w in want], f)
  
  if frame is None:
    result["notes"].append(C.note("OUTDOOR_NO_PLOT_FRAME", labels=sorted({k for _t, _x, _y, _h, k, _w in want})))
    result["stats"] = {"plot_frame": None}
    return result
  x0, y0, x1, y1 = frame["box"]
  foot = footprint(walls, rooms, box(x0, y0, x1, y1), f)
  found = regions(box(x0, y0, x1, y1), foot, words, f)
  checks = [c for c in (width_check(r) for r in found) if c]
  stats = {"plot_frame": {"x0": round(x0, 2), "y0": round(y0, 2), "x1": round(x1, 2), "y1": round(y1, 2), "width_m": round((x1 - x0) * f / 1000.0, 3), "length_m": round((y1 - y0) * f / 1000.0, 3),
    "ratio": frame["ratio"]}, "regions": [{k: v for k, v in r.items() if k != "polygon"} for r in found], "width_checks": checks, "frame_checked": any(c["agrees"] for c in checks)}
  
  result["stats"] = stats
  unbilled = []
  by_kind: dict = {}
  for r in found:
    code, rule = FR.site_item(r["kind"])
    if code == FR.NONE:
      unbilled.append({"kind": r["kind"], "area_m2": r["area_m2"], "labels": r["labels"], "mixed": r["mixed"]})
    else:
      by_kind.setdefault(r["kind"], []).append(r)
  for kind, rs in sorted(by_kind.items()):
    code, rule = FR.site_item(kind)
    total = sum(r["area_m2"] for r in rs)
    checked = [c for c in (width_check(r) for r in rs) if c]
    facts = {"derived_from": "SITE_REGIONS", "region_kind": kind, "region_count": len(rs), "area_m2": round(total, 3), "item_rule": FR.evidence(FR.SITE_ITEM, rule, region=kind),
      "labels": [t for r in rs for t in r["labels"]], "plot_frame_m": [stats["plot_frame"]["width_m"], stats["plot_frame"]["length_m"]], "width_checks": checked}
    
    notes = [C.note("OUTDOOR_REGIONS_FROM_PLOT")]
    if checked:
      notes.append(C.note("OUTDOOR_WIDTH_AGREES" if all(c["agrees"] for c in checked) else "OUTDOOR_WIDTH_DIFFERS", checks=checked))
    elif not any(c["agrees"] for c in checks):
      notes.append(C.note("OUTDOOR_FRAME_UNCHECKED"))
    label = f"{TEXT[kind]} · {total:.2f} m²" + (f" · {spec[0]}" if spec else "")
    points = [_centre([r["polygon"] for r in rs])]
    result["candidates"].append(make(cls, ctx, finish, ("SITE_REGION", kind, level_hint or ""), "SITE_REGION", label, f"SITE-{kind}", points, {"length_mm": round(total * 1000.0, 1), "width_mm": 1000.0}, [],
      notes, facts, 0.65, work_item=code))
    layers, layer_rule = FR.site_layers(kind)
    
    for i, layer in enumerate(layers, 1):
      lf = {"derived_from": "SITE_REGIONS", "region_kind": kind, "area_m2": round(total, 3), "layer": i, "layer_rule": FR.evidence(FR.SITE_LAYERS, layer_rule, region=kind)}
      result["candidates"].append(make(cls, ctx, finish, ("SITE_LAYER", kind, i, level_hint or ""), "SITE_LAYER", f"{TEXT[kind]} · layer {i} · {layer['thickness_mm']:g} mm · {total:.2f} m²", f"SITE-{kind}-LAYER-{i}", points,
        {"length_mm": round(total * 1000.0, 1), "width_mm": 1000.0, "depth_mm": layer["thickness_mm"]}, [], [C.note("SITE_LAYERS_FROM_RULE")], lf, 0.6, mode="COUNT_X_VOLUME", work_item=layer["work_item"]))
  if unbilled:
    result["notes"].append(C.note("OUTDOOR_REGION_UNBILLED", regions=unbilled, area_m2=round(sum(u["area_m2"] for u in unbilled), 3)))
  if any(r["mixed"] for r in found):
    result["notes"].append(C.note("OUTDOOR_REGION_MIXED", regions=[{"labels": r["labels"], "area_m2": r["area_m2"]} for r in found if r["mixed"]]))
  stats["unbilled"] = unbilled
  return result
