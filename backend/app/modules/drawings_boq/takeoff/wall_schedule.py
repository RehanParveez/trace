from __future__ import annotations
import math
from app.modules.drawings_boq.takeoff.prep.facts import FLOOR_ORDER
from app.modules.drawings_boq.takeoff import stair_pairs as SP

NAME_OUTSIDE = "Outside"
NAME_UNKNOWN = "(no room found)"
FACE_PROBE_MM = 100.0       
RUN_TOL_MM = 50.0           
REGISTER_ERROR_TIMES = 2.0   
ONLY_THIS_FLOOR = "ONLY_THIS_FLOOR"
COVERED = "COVERED"
NO_FRAME = "NO_COMMON_FRAME"
VOLUME_ITEMS = ("PCC_STRIP", "TRENCH", "RCC_STRIP")
AREA_ITEMS = ("TERMITE_STRIP",)

def _key(c) -> str:
  return getattr(c, "ckey", None) or getattr(c, "key", None)

def _facts(c) -> dict:
  return getattr(c, "facts", None) or {}

def _inside(poly: list, x: float, y: float) -> bool:
  n, hit = len(poly), False
  for i in range(n):
    x0, y0 = poly[i]
    x1, y1 = poly[(i + 1) % n]
    if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
      hit = not hit
  return hit

def _room_polys(candidates: list) -> dict:
  out: dict = {}
  for c in candidates:
    if c.category != "ROOM" or c.decision == "REJECTED":
      continue
    ring = ((getattr(c, "geometry", None) or {}).get("outer")) or []
    if len(ring) >= 3:
      name = str(_facts(c).get("name") or "").strip().title() or str(_facts(c).get("room_type") or "Room").strip().title()
      out.setdefault(c.sheet_id, []).append((name, [(float(p[0]), float(p[1])) for p in ring], [[(float(p[0]), float(p[1])) for p in h] for h in (((c.geometry or {}).get("holes")) or [])]))
  return out

def _space(rooms: list, x: float, y: float) -> str | None:
  for name, ring, holes in rooms:
    if _inside(ring, x, y) and not any(_inside(h, x, y) for h in holes):
      return name
  return None

def _faces(c, rooms: list, mm_per_pt: float) -> tuple:
  pts = ((c.geometry or {}).get("points")) or []
  if len(pts) < 2 or not mm_per_pt:
    return NAME_UNKNOWN, NAME_UNKNOWN
  (x0, y0), (x1, y1) = (float(pts[0][0]), float(pts[0][1])), (float(pts[-1][0]), float(pts[-1][1]))
  mx, my = (x0 + x1) / 2.0, (y0 + y1) / 2.0
  L = math.hypot(x1 - x0, y1 - y0)
  
  if L <= 0:
    return NAME_UNKNOWN, NAME_UNKNOWN
  nx, ny = -(y1 - y0) / L, (x1 - x0) / L
  t = float(_facts(c).get("thickness_used_mm") or 0.0)
  d = (t / 2.0 + FACE_PROBE_MM) / mm_per_pt
  names = [_space(rooms, mx + s * nx * d, my + s * ny * d) for s in (1.0, -1.0)]
  fill = NAME_OUTSIDE if any(n is not None for n in names) and (_facts(c).get("face_sides") or {}).get("out", 0) else NAME_UNKNOWN
  return tuple(sorted(n or fill for n in names))

def _share_items(candidates: list) -> dict:
  by_key: dict = {}
  for c in candidates:
    f = _facts(c)
    keys = f.get("wall_keys") or []
    if c.category == "WALL" and not f.get("foundation_item") or c.decision == "REJECTED" or not keys:
      continue
  
    item = f.get("foundation_item") or (c.category if f.get("derived_from") == "WALLS" else None) or f.get("derived_from") or c.category
    if f.get("step_no") and item == "BRICK_STEP":
      item = f"BRICK_STEP_{int(f['step_no'])}"
    p = getattr(c, "params", None) or {}
    L, W, D = (p.get("length_mm"), p.get("width_mm"), p.get("depth_mm"))
    qty, unit = None, None
    if (item in VOLUME_ITEMS or item.startswith("BRICK_STEP")) and all(isinstance(v, (int, float)) for v in (L, W, D)):
      qty, unit = float(L) * float(W) * float(D) / 1e9, "m3"
    elif item in AREA_ITEMS and all(isinstance(v, (int, float)) for v in (L, W)):
      qty, unit = float(L) * float(W) / 1e6, "m2"
    for k in keys:
      by_key.setdefault(k, []).append({"item": str(item), "label": c.label, "group": c, "quantity": qty, "unit": unit, "n": len(keys)})
  return by_key

def _length_m(c) -> float:
  return float(_facts(c).get("length_cc_m") or 0.0)

def rows(candidates: list, sheets: dict) -> list:
  rooms = _room_polys(candidates)
  shared = _share_items(candidates)
  walls = [c for c in candidates if c.category == "WALL" and c.decision != "REJECTED" and c.sheet_id in sheets and not _facts(c).get("foundation_item")]
  
  out: list = []
  for c in walls:
    sh = sheets[c.sheet_id]
    f = _facts(c)
    p = c.params or {}
    mm = SP._mm_per_pt(c) or getattr(sh, "mm_per_pt", None)
    a, b = _faces(c, rooms.get(c.sheet_id, []), mm)
    t, h, L = float(f.get("thickness_used_mm") or p.get("thickness_mm") or 0.0), p.get("height_mm"), _length_m(c)
    
    items = []
    for s in shared.get(_key(c), []):
      total = sum(_length_m(w) for w in walls if _key(w) in (_facts(s["group"]).get("wall_keys") or []))
      share = L / total if total > 0 else None
      items.append({"item": s["item"], "share": None if share is None else round(share, 4), "quantity": None if s["quantity"] is None or share is None else round(s["quantity"] * share, 4), "unit": s["unit"]})
    if h and t and L:
      items.insert(0, {"item": "BRICK_WALL_GROSS", "share": 1.0, "quantity": round(L * t * float(h) / 1e9 * 1000.0, 4), "unit": "m3"})
    pts = ((c.geometry or {}).get("points")) or [[0, 0]]
    out.append({"id": str(c.id), "key": _key(c), "sheet_id": c.sheet_id, "page_no": sh.page_no, "floor": SP.level_key(sh) or _facts(c).get("level_hint"), "name": f"{a} / {b}", "faces": [a, b],
      "thickness_mm": t, "thickness_basis": f.get("thickness_basis") or "UNKNOWN", "construction": f.get("construction") or "BRICK", "length_m": round(L, 3), "height_mm": h,
      "height_basis": p.get("dims_basis"), "items": items, "x": float(pts[0][0]), "y": float(pts[0][1]), "vs_below": None, "vs_above": None, "frame": None, "tol_mm": RUN_TOL_MM})
    
  out.sort(key=lambda r: (FLOOR_ORDER.index(r["floor"]) if r["floor"] in FLOOR_ORDER else len(FLOOR_ORDER), r["page_no"], round(r["y"] / 20.0), r["x"]))
  for i, r in enumerate(out, start=1):
    r["no"] = i
  _compare(out, walls, candidates, sheets)
  return out

def _seg_gap(p: tuple, a: tuple, b: tuple) -> float:
  dx, dy = b[0] - a[0], b[1] - a[1]
  L2 = dx * dx + dy * dy
  u = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
  return math.hypot(p[0] - (a[0] + u * dx), p[1] - (a[1] + u * dy))

def _compare(out: list, walls: list, candidates: list, sheets: dict) -> None:
  by_key = {_key(c): c for c in walls}
  floors = [k for k in FLOOR_ORDER if any(r["floor"] == k for r in out)]
  frames = SP._Frames(candidates)

  def points(r) -> list:
    return [(float(p[0]), float(p[1])) for p in ((by_key[r["key"]].geometry or {}).get("points")) or []]

  for lo_k, hi_k in zip(floors, floors[1:]):
    lo = [r for r in out if r["floor"] == lo_k]
    hi = [r for r in out if r["floor"] == hi_k]
    for mine, other, field in ((hi, lo, "vs_below"), (lo, hi, "vs_above")):
      for r in mine:
        c = by_key[r["key"]]
        pts = points(r)
        if len(pts) < 2:
          continue
      
        seen = None
        covered = False
        for o in other:
          oc = by_key[o["key"]]
          lo_c, hi_c = (oc, c) if field == "vs_below" else (c, oc)
          mm_lo, mm_hi = SP._mm_per_pt(lo_c), SP._mm_per_pt(hi_c)
          if mm_lo is None or mm_hi is None:
            continue
          how, reg = frames.between(lo_c.sheet_id, hi_c.sheet_id, mm_lo, mm_hi)
          if how is None:
            continue
          seen = how
          opts = points(o)
          if len(opts) < 2:
            continue
        
          to_lo = (lambda q: q) if reg is None else reg.apply
          mine_lo = [q if lo_c is c else to_lo(q) for q in pts]
          other_lo = [q if lo_c is oc else to_lo(q) for q in opts]
          tol = max(RUN_TOL_MM, REGISTER_ERROR_TIMES * (reg.rms * mm_lo if reg is not None else 0.0))
          r["tol_mm"] = round(tol, 1)
          if all(_seg_gap(q, other_lo[0], other_lo[-1]) * mm_lo <= tol for q in (mine_lo[0], mine_lo[-1])):
            covered = True
            break
        r[field] = NO_FRAME if seen is None else (COVERED if covered else ONLY_THIS_FLOOR)
        r["frame"] = r["frame"] or seen

XLSX_COLUMNS = (("No", "no"), ("Floor", "floor"), ("Sheet", "page_no"), ("Wall (space / space)", "name"), ("Thickness mm", "thickness_mm"), ("Thickness from", "thickness_basis"),
  ("Length m", "length_m"), ("Height mm", "height_mm"), ("Height from", "height_basis"), ("Items", "items_text"), ("Against floor below", "vs_below"), ("Against floor above", "vs_above"))

def _items_text(r: dict) -> str:
  parts = []
  for i in r["items"]:
    q = "" if i["quantity"] is None else f" {i['quantity']:g} {i['unit']}"
    parts.append(f"{i['item']}{q}")
  return "; ".join(parts)

def to_xlsx(rows_: list, summary_: list) -> bytes:
  from io import BytesIO
  from openpyxl import Workbook
  from openpyxl.styles import Font
  wb = Workbook()
  ws = wb.active
  ws.title = "Walls"
  ws.append([h for h, _k in XLSX_COLUMNS])
  
  for r in rows_:
    ws.append([_items_text(r) if k == "items_text" else r.get(k) for _h, k in XLSX_COLUMNS])
  for cell in ws[1]:
    cell.font = Font(bold=True)
  sm = wb.create_sheet("Floors")
  sm.append(["Floor", "Runs", "Length m", "Length m by thickness (mm)", "Runs only on this floor (against floor below)", "Runs only on this floor (against floor above)"])
  for s in summary_:
    sm.append([s["floor"], s["runs"], s["length_m"], "; ".join(f"{k:g}: {v:g}" for k, v in sorted(s["by_thickness_mm"].items())), s["only_vs_below"], s["only_vs_above"]])
  for cell in sm[1]:
    cell.font = Font(bold=True)
    
  buf = BytesIO()
  wb.save(buf)
  return buf.getvalue()

def summary(rows_: list) -> list:
  out: list = []
  for k in FLOOR_ORDER:
    rs = [r for r in rows_ if r["floor"] == k]
    if not rs:
      continue
  
    by_t: dict = {}
    for r in rs:
      by_t[r["thickness_mm"]] = round(by_t.get(r["thickness_mm"], 0.0) + r["length_m"], 3)
    out.append({"floor": k, "runs": len(rs), "length_m": round(sum(r["length_m"] for r in rs), 3), "by_thickness_mm": by_t,
      "only_vs_below": sum(1 for r in rs if r["vs_below"] == ONLY_THIS_FLOOR), "only_vs_above": sum(1 for r in rs if r["vs_above"] == ONLY_THIS_FLOOR)})
  return out
