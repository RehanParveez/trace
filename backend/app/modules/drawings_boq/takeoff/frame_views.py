from __future__ import annotations
from decimal import Decimal
from app.engine.measure import frame as FR
from app.engine.measure import takeoff as tk
from app.modules.drawings_boq.takeoff import frame_columns as FC

ANCHORS = ("COLUMN", "FOOTING")
MARKS = ("COLUMN", "FOOTING", "SLAB", "BEAM", "LINTEL")

def view_points(formwork, group_of_sheet: dict) -> dict:
  """{group: {view key: [FramePoint]}}. Only columns and footings are used to find the match between views (they sit on the grid and repeat from one view to the next);
  a view that has other placed members but no column still appears, with no points, so it can be placed by hand."""
  out: dict = {}
  
  for f in formwork:
    if not (f.frame and f.points_mm):
      continue
    group = group_of_sheet.get(f.sheet_id)
    if group is None:
      continue
    pts = out.setdefault(group, {}).setdefault(f.frame, [])
    if f.category in ANCHORS:
      size = FR.size_class(float(f.length_mm), float(f.width_mm))
      pts.extend(FR.FramePoint(float(x), float(y), size, (str(f.measurement_id), i)) for i, (x, y) in enumerate(f.points_mm[:f.count]))
  return out

def solve_frames(views_by_group: dict, stored: dict | None = None) -> dict:
  """{group: Frame}. stored maps a group to {"reference": view key or None, "placements": {view key: (dx, dy)}} as people left it."""
  stored = stored or {}
  out = {}
  for group in sorted(views_by_group):
    s = stored.get(group) or {}
    placements = {k: v for k, v in (s.get("placements") or {}).items() if k in views_by_group[group]}
    ref = s.get("reference")
    ref = ref if ref in views_by_group[group] else None
    frame = FR.align_views(views_by_group[group], reference=ref, confirmed=placements)
    if ref is not None and frame.reference == ref and ref not in placements:
    
      frame.alignments[ref] = FR.confirm(frame.alignments[ref])
    out[group] = frame
  return out

def alignment_inputs(frames: dict) -> tuple:
  items = []
  for group in sorted(frames):
    f = frames[group]
    for view in sorted(f.alignments):
      a = f.alignments[view]
      items.append(tk.AlignmentInput(
        view=view, dx_mm=Decimal(str(a.dx_mm)), dy_mm=Decimal(str(a.dy_mm)), method=a.method, grade=a.grade, supporters=a.supporters, compared=a.compared,
        residual_mm=Decimal(str(a.residual_mm)), reference=(view == f.reference), group=group,
        origin_x_mm=Decimal(str(f.origin_mm[0])), origin_y_mm=Decimal(str(f.origin_mm[1]))))
  return tuple(items)

def build_alignments(formwork, group_of_sheet: dict, stored: dict | None = None) -> tuple:
  return alignment_inputs(solve_frames(view_points(formwork, group_of_sheet), stored))

def placed_members(formwork, group_of_sheet: dict, frames: dict) -> dict:
  """{group: {view: [member dicts in frame coordinates]}} for the overlay: every counted mark with its centre, size and level, or None as the centre when its view is not placed."""
  out: dict = {}
  for f in formwork:
    if not (f.frame and f.points_mm) or f.category not in MARKS:
      continue
    group = group_of_sheet.get(f.sheet_id)
    frame = frames.get(group)
    if frame is None:
      continue
    rows = out.setdefault(group, {}).setdefault(f.frame, [])
    for i, (x, y) in enumerate(f.points_mm[:f.count]):
      p = FR.frame_xy(frame, f.frame, float(x), float(y))
      rows.append({"measurement_id": str(f.measurement_id), "instance": i, "category": f.category, "tag": f.tag, "length_mm": float(f.length_mm), "width_mm": float(f.width_mm),
        "sheet_x_mm": float(x), "sheet_y_mm": float(y), "x_mm": p[0] if p else None, "y_mm": p[1] if p else None})
  return out

def describe(frame, members: dict, anchors: dict, stored: dict | None) -> dict:
  """The frame of one drawing as the screen shows it. members is {view: [placed member dicts]}, anchors {view: number of column and footing points}, stored what
  people decided. A frame is CONFIRMED only when every view in it carries a person's decision; until then it stays ASSUMED."""
  stored = stored or {}
  placements = stored.get("placements") or {}
  
  views = []
  for view in sorted(frame.alignments):
    a = frame.alignments[view]
    views.append({
      "key": view, "reference": view == frame.reference, "method": a.method, "grade": a.grade, "dx_mm": a.dx_mm, "dy_mm": a.dy_mm,
      "supporters": a.supporters, "compared": a.compared, "residual_mm": a.residual_mm, "confidence": a.confidence,
      "anchors": anchors.get(view, 0), "decided": view in placements or view == stored.get("reference"),
      "members": members.get(view, [])})
  unconfirmed = [v["key"] for v in views if v["grade"] != FR.CONFIRMED and not (v["reference"] and v["decided"])]
 
  open_views = [v["key"] for v in views if not v["decided"]]
  columns = FC.check(members, {v["key"]: (FR.CONFIRMED if v["grade"] == FR.CONFIRMED or v["decided"] else v["grade"]) for v in views})
  return {"reference": frame.reference, "origin_mm": list(frame.origin_mm), "views": views, "columns": columns,
    "status": "CONFIRMED" if views and not open_views else "ASSUMED", "open_views": open_views, "unplaced": [v["key"] for v in views if v["method"] == FR.UNALIGNED and not v["decided"]],
    "unconfirmed": unconfirmed}

def register_positions(formwork, group_of_sheet: dict, stored: dict | None = None) -> dict:
  """{(measurement id, instance): {"view", "position_mm", "grade", "method"}} for every placed mark; marks of a view that is not placed are left out."""
  frames = solve_frames(view_points(formwork, group_of_sheet), stored)
  out: dict = {}
  for group, views in placed_members(formwork, group_of_sheet, frames).items():
    for view, rows in views.items():
      a = frames[group].alignments[view]
      for r in rows:
        if r["x_mm"] is None:
          continue
        out[(r["measurement_id"], r["instance"])] = {"view": view, "position_mm": [r["x_mm"], r["y_mm"]], "grade": a.grade, "method": a.method}
  return out
