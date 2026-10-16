from __future__ import annotations
from app.engine.measure import frame as FR
from app.modules.drawings_boq.takeoff import frame_columns as FC
from app.engine.measure import frame_reconcile as RC

PLACE_TOL_MM = FR.MAX_RESIDUAL_MM
COLUMN_ROLE = "COLUMN"

def _size_of(items: list) -> tuple | None:
  for it in items:
    s = FR.size_class(it.get("length_mm"), it.get("width_mm"))
    if s is not None:
      return s
  return None

def pdf_places(members_by_view: dict, tol: float = PLACE_TOL_MM) -> list:
  """(FramePoints, info): one point per place a PDF column stands on the frame, its ref the index into info, which carries the mark(s) and the views."""
  out, info = [], []
  for g in FC.stacks(members_by_view, tol):
    cx = sum(m["x_mm"] for _, m in g) / len(g)
    cy = sum(m["y_mm"] for _, m in g) / len(g)
    tags = sorted({m["tag"] for _, m in g if m.get("tag")})
    out.append(FR.FramePoint(round(cx, 2), round(cy, 2), _size_of([m for _, m in g]), len(info)))
    info.append({"marks": tags, "views": sorted(v for v, _ in g)})
  return out, info

def _centre_and_size(el) -> tuple | None:
  plan = (el.placement or {}).get("plan_mm") if getattr(el, "placement", None) else None
  try:
    if plan and len(plan) >= 3:
      xs, ys = [float(p[0]) for p in plan], [float(p[1]) for p in plan]
    else:
      xs = [float(el.bbox_min_x_mm), float(el.bbox_max_x_mm)]
      ys = [float(el.bbox_min_y_mm), float(el.bbox_max_y_mm)]
  except (TypeError, ValueError, IndexError):
    return None
  w, h = max(xs) - min(xs), max(ys) - min(ys)
  if w <= 0 or h <= 0:
    return None
  return ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0, FR.size_class(w, h))

def model_places(elements: list, tol: float = PLACE_TOL_MM) -> list:
  """(FramePoints, info): one point per place a model column stands, from IFC elements whose role is COLUMN; columns of different storeys at one place join into
  one. The ref of a point is the index into info."""
  rows = []
  for el in sorted(elements, key=lambda e: (str(getattr(e, "level_id", "") or ""), str(e.id))):
    if getattr(el, "structural_role", None) != COLUMN_ROLE:
      continue
  
    found = _centre_and_size(el)
    if found is not None:
      rows.append((found[0], found[1], found[2], el))
  groups: list = []
  for x, y, size, el in sorted(rows, key=lambda r: (r[0], r[1])):
    best, best_d = None, None
    for g in groups:
      if any(e.level_id is not None and e.level_id == el.level_id for *_, e in g):
        continue
      gx, gy = sum(r[0] for r in g) / len(g), sum(r[1] for r in g) / len(g)
      d = ((x - gx) ** 2 + (y - gy) ** 2) ** 0.5
      if d <= tol and (best_d is None or d < best_d):
        best, best_d = g, d
    if best is None:
      groups.append([(x, y, size, el)])
    else:
      best.append((x, y, size, el))
      
  out, info = [], []
  for g in groups:
    cx, cy = sum(r[0] for r in g) / len(g), sum(r[1] for r in g) / len(g)
    marks = sorted({e.type_mark or e.name for *_, e in g if (e.type_mark or e.name)})
    out.append(FR.FramePoint(round(cx, 2), round(cy, 2), g[0][2], len(info)))
    info.append({"names": marks, "element_ids": [str(e.id) for *_, e in g]})
  return out, info

def build(members_by_view: dict, model_elements: list, *, offset: tuple | None = None) -> dict:
  """The reconciliation of the PDF columns with the model columns, as plain data for the API."""
  pdf, pdf_info = pdf_places(members_by_view)
  model, model_info = model_places(model_elements)
  r = RC.reconcile(pdf, model, offset=offset)
  
  def p(ref):
    return pdf_info[ref]
  def m(ref):
    return model_info[ref]
  return {
    "status": r.status, "grade": r.grade, "method": r.method, "dx_mm": r.dx_mm, "dy_mm": r.dy_mm, "supporters": r.supporters, "compared": r.compared,
    "pdf_places": len(pdf), "model_places": len(model), "agrees": r.agrees,
    "pairs": [{"pdf": p(a.pdf), "model": m(a.model), "distance_mm": a.distance_mm} for a in r.pairs],
    "pdf_only": [p(x) for x in r.pdf_only], "model_only": [m(x) for x in r.model_only],
    "size_differs": [{"pdf": p(a), "model": m(b), "pdf_size": list(sa) if sa else None, "model_size": list(sb) if sb else None} for a, b, sa, sb in r.size_differs]}
