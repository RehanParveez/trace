from __future__ import annotations
from app.modules.drawings_boq.takeoff.orientation.frame import Frame

POINT_LISTS = frozenset({"points", "outer", "corners", "flight_corners"})
RING_LISTS = frozenset({"holes"})
PAIR_LISTS = frozenset({"gap_pts"})
ANGLES = frozenset({"plan_angle_deg"})
POINTS = frozenset({"p0", "p1", "p2", "centre", "center"})
BOXES = frozenset({"bbox", "core_bbox", "caption_bbox", "box", "flight_box"})
XY = (("x", "y"), ("cx", "cy"))
ROUND = 4

def _num(v) -> bool:
  return isinstance(v, (int, float)) and not isinstance(v, bool)

def _pair(v) -> bool:
  return isinstance(v, (list, tuple)) and len(v) == 2 and _num(v[0]) and _num(v[1])

def _box(v) -> bool:
  return isinstance(v, (list, tuple)) and len(v) == 4 and all(_num(x) for x in v)

def _move(frame_fn, p) -> list:
  x, y = frame_fn(float(p[0]), float(p[1]))
  return [round(x, ROUND), round(y, ROUND)]

def _box_move(box_fn, b) -> list:
  return [round(v, ROUND) for v in box_fn(b)]

def _pairs(v) -> bool:
  return isinstance(v, (list, tuple)) and all(isinstance(q, (list, tuple)) and len(q) == 2 and _pair(q[0]) and _pair(q[1]) for q in v)

def _wrap(deg: float) -> float:
  d = (deg + 180.0) % 360.0 - 180.0
  return 180.0 if d == -180.0 else d

def carry(obj, fn, box_fn, turn: float = 0.0):
  if isinstance(obj, dict):
    out = {}
    
    for k, v in obj.items():
      if k in POINT_LISTS and isinstance(v, (list, tuple)) and v and all(_pair(p) for p in v):
        out[k] = [_move(fn, p) for p in v]
      elif k in PAIR_LISTS and v and _pairs(v):
        out[k] = [[_move(fn, q[0]), _move(fn, q[1])] for q in v]
      elif k in ANGLES and _num(v):
        out[k] = round(_wrap(float(v) + turn), 2)
      elif k in RING_LISTS and isinstance(v, (list, tuple)):
        out[k] = [[_move(fn, p) for p in ring] if isinstance(ring, (list, tuple)) and all(_pair(p) for p in ring) else carry(ring, fn, box_fn, turn) for ring in v]
      elif k in POINTS and _pair(v):
        out[k] = _move(fn, v)
      elif k in BOXES and _box(v):
        out[k] = _box_move(box_fn, v)
      else:
        out[k] = carry(v, fn, box_fn, turn)
        
    for kx, ky in XY:
      if _num(out.get(kx)) and _num(out.get(ky)) and kx in obj and ky in obj:
        out[kx], out[ky] = _move(fn, (obj[kx], obj[ky]))
    return out

  if isinstance(obj, list):
    return [carry(v, fn, box_fn, turn) for v in obj]
  if isinstance(obj, tuple):
    return tuple(carry(v, fn, box_fn, turn) for v in obj)
  return obj

def to_page(obj, frame: Frame):
  return obj if frame.identity else carry(obj, frame.back, frame.back_box, -frame.psi)

def to_upright(obj, frame: Frame):
  return obj if frame.identity else carry(obj, frame.forward, frame.forward_box, frame.psi)

def extraction_to_page(res, frame: Frame):
  if frame.identity:
    return res
  for c in res.candidates:
    c.geometry = to_page(c.geometry, frame)
    c.params = to_page(c.params, frame)
    c.facts = to_page(c.facts, frame)
    c.notes = to_page(c.notes, frame)
  res.stats = to_page(res.stats, frame)
  res.notes = to_page(res.notes, frame)
  res.unmapped_tags = to_page(res.unmapped_tags, frame)
  return res

def analysis_to_page(a, frame: Frame):
  if frame.identity:
    return a

  det = a.detected_scale
  declared = det.get("declared") or {}
  declared["candidates"] = [_xy(c, frame) for c in declared.get("candidates") or []]
  if declared.get("primary"):
    declared["primary"] = _xy(declared["primary"], frame)
  measured = det.get("measured")
  
  if measured:
    for c in measured.get("clusters") or []:
      if _box(c.get("bbox")):
        c["bbox"] = _box_move(frame.back_box, c["bbox"])
    for p in (measured.get("pairs") or []) + (measured.get("mismatches") or []):
      _ends(p, frame)
      
  check = (det.get("recommended") or {}).get("check")
  if check:
    _ends(check, frame)
  for v in a.meta.get("views") or []:
    if _box(v.get("bbox")):
      v["bbox_upright"] = list(v["bbox"])
      v["bbox"] = _box_move(frame.back_box, v["bbox"])
  return a

def _xy(c: dict, frame: Frame) -> dict:
  if _num(c.get("x")) and _num(c.get("y")):
    c = dict(c)
    c["x"], c["y"] = _move(frame.back, (c["x"], c["y"]))
  return c

def _ends(p: dict, frame: Frame) -> None:
  for k in ("p1", "p2"):
    if _pair(p.get(k)):
      p[k] = _move(frame.back, p[k])

def views_to_upright(views: list | None, frame: Frame) -> list | None:
  if not views or frame.identity:
    return views

  out = []
  for v in views:
    v = dict(v)
    if _box(v.get("bbox_upright")):
      v["bbox"] = list(v["bbox_upright"])
    elif _box(v.get("bbox")):
      v["bbox"] = _box_move(frame.forward_box, v["bbox"])
    out.append(v)
  return out
