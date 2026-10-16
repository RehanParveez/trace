from __future__ import annotations
import math
import re
from app.engine.measure import frame as FR

TAG_DIFFERS, SIZE_DIFFERS = "COLUMN_TAG_DIFFERS", "COLUMN_SIZE_DIFFERS"
POSITION_TOL_MM = FR.MAX_RESIDUAL_MM

def norm_tag(tag: str | None) -> str | None:
  t = re.sub(r"[\s\-_]", "", tag or "").upper()
  return t or None

def _columns(members_by_view: dict) -> list:
  out = []
  for view in sorted(members_by_view):
    for m in members_by_view[view]:
      if m.get("category") == "COLUMN" and m.get("x_mm") is not None and m.get("y_mm") is not None:
        out.append((view, m))
  return out

def stacks(members_by_view: dict, tol: float = POSITION_TOL_MM) -> list:
  """Columns grouped by place: [[(view, member), ...]], one member per view in a group, a group for every place a column stands (a lone column is a group of one)."""
  items = sorted(_columns(members_by_view), key=lambda vm: (vm[1]["x_mm"], vm[1]["y_mm"], vm[0], vm[1].get("measurement_id", ""), vm[1].get("instance", 0)))
  groups: list = []
  
  for view, m in items:
    best, best_d = None, None
    for g in groups:
      if any(v == view for v, _ in g):
        continue
      cx = sum(x["x_mm"] for _, x in g) / len(g)
      cy = sum(x["y_mm"] for _, x in g) / len(g)
      d = math.hypot(m["x_mm"] - cx, m["y_mm"] - cy)
      if d <= tol and (best_d is None or d < best_d):
        best, best_d = g, d
    if best is None:
      groups.append([(view, m)])
    else:
      best.append((view, m))
  return groups

def _size(m: dict) -> tuple | None:
  return FR.size_class(m.get("length_mm"), m.get("width_mm"))

def check(members_by_view: dict, grade_of_view: dict | None = None, tol: float = POSITION_TOL_MM) -> dict:
  """{"places": n, "shared": n, "agree": n, "issues": [...]}. Each issue is {code, x_mm, y_mm, grade, columns: [{view, tag, length_mm, width_mm}]}. grade is CONFIRMED only when
  every view in the group has a confirmed placement."""
  grade_of_view = grade_of_view or {}
  groups = stacks(members_by_view, tol)
  shared = [g for g in groups if len(g) > 1]
  issues = []
  
  for g in shared:
    tags = {norm_tag(m.get("tag")) for _, m in g} - {None}
    sizes = [_size(m) for _, m in g if _size(m) is not None]
    differ_size = any(not FR._same_size(sizes[0], s) for s in sizes[1:])
    grade = FR.CONFIRMED if all(grade_of_view.get(v) == FR.CONFIRMED for v, _ in g) else FR.ASSUMED
    where = {"x_mm": round(sum(m["x_mm"] for _, m in g) / len(g), 1), "y_mm": round(sum(m["y_mm"] for _, m in g) / len(g), 1), "grade": grade,
      "columns": [{"view": v, "tag": m.get("tag"), "length_mm": float(m.get("length_mm") or 0.0), "width_mm": float(m.get("width_mm") or 0.0)} for v, m in g]}
    
    if len(tags) > 1:
      issues.append({"code": TAG_DIFFERS, **where})
    if differ_size:
      issues.append({"code": SIZE_DIFFERS, **where})
  issues.sort(key=lambda i: (i["code"], i["x_mm"], i["y_mm"]))
  bad = {(i["x_mm"], i["y_mm"]) for i in issues}
  return {"places": len(groups), "shared": len(shared), "agree": sum(1 for g in shared if (round(sum(m["x_mm"] for _, m in g) / len(g), 1), round(sum(m["y_mm"] for _, m in g) / len(g), 1)) not in bad),
    "issues": issues}
