from __future__ import annotations
import math
import re
from app.modules.drawings_boq.takeoff.extract import finish_rules as FR
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.prep import schedules as S

ITEMS = ("FACADE_ZONES",)
WORK_ITEM: dict = {}
FRONT, REAR, SIDE, LEFT, RIGHT, UNNAMED = "FRONT", "REAR", "SIDE", "LEFT", "RIGHT", "UNNAMED"
VIEW = ((FRONT, re.compile(r"\bFRONT\b")), (REAR, re.compile(r"\bREAR\b")), (LEFT, re.compile(r"\bLEFT\b")), (RIGHT, re.compile(r"\bRIGHT\b")), (SIDE, re.compile(r"\bSIDE\b")))
FINISH_LABEL = re.compile(r"\b(?:MATERIAL|FINISH)\b")
SIGNS = ("+", "±", "-", "–")

MIN_LINE_MM = 150.0              
MODULE_MIN_MM, MODULE_MAX_MM = 250.0, 1500.0
MODULE_TOL = 0.08
MIN_LINES = 3
PEN_SLACK = 0.01             
MIN_ZONE_M2 = 1.0
JOIN_GAP_MM = 30.0
OVERLAP = 0.5
SCALE_AGREE = 0.05
LEVEL_SIDE_MM = 150.0
CELL_MM = 30.0
MAX_RUNS = 4000

def view_of(words: list) -> str:
  text = " ".join(w.text for w in sorted(words, key=lambda w: -w.size)[:12]).upper()
  for name, rx in VIEW:
    if rx.search(text):
      return name
  return UNNAMED

def levels(words: list) -> list:
  out = []
  for w in words:
    if not w.text or "'" not in w.text:
      continue
    quarter = round(w.angle / 90.0)
    if abs(w.angle - 90.0 * quarter) > 2.0:
      continue
    mm = S.feet_inches_mm(w.text)
    if mm is None:
      continue
    ux, uy = math.cos(math.radians(90.0 * quarter)), math.sin(math.radians(90.0 * quarter))   
    nx, ny = -uy, ux                                                                              

    def before(s) -> bool:
      dx, dy = w.cx - s.cx, w.cy - s.cy
      return abs(dx * nx + dy * ny) <= 0.8 * w.height and 0 < dx * ux + dy * uy <= 6.0 * w.height
    sign = next((s for s in words if s.text in SIGNS and before(s)), None)
    if sign is None:
      continue
    out.append({"mm": 0.0 if sign.text == "±" else (mm if sign.text == "+" else -mm), "text": f"{sign.text} {w.text}", "side": round(w.cx * ux + w.cy * uy, 2), "up": round(w.cx * nx + w.cy * ny, 2)})
  return out

def level_scale(found: list, f: float) -> dict | None:
  sides: dict = {}
  for lv in found:
    sides.setdefault(round(lv["side"] / 40.0), []).append(lv)
  best = None
  for _k, group in sides.items():
    hi, lo = max(group, key=lambda l: l["mm"]), min(group, key=lambda l: l["mm"])
    span_mm, span_pt = hi["mm"] - lo["mm"], abs(hi["up"] - lo["up"])
    if span_mm < 3000.0 or span_pt <= 0:
      continue
    fit = span_mm / span_pt
    if best is None or span_mm > best["span_mm"]:
      best = {"mm_per_pt": round(fit, 4), "span_mm": round(span_mm, 1), "from": lo["text"], "to": hi["text"]}
  if best is None:
    return None

  best["sheet_mm_per_pt"] = round(f, 4)
  best["difference"] = round(best["mm_per_pt"] / f - 1.0, 4)
  best["agrees"] = abs(best["difference"]) <= SCALE_AGREE
  return best

def _runs(index, f: float) -> tuple:
  hl: dict = {}
  vl: dict = {}
  tol = 0.3
  if not index.n:
    return [], []
  fine = min(float(index.segs[i * 5 + 4]) for i in range(index.n)) + PEN_SLACK
  for i in range(index.n):
    x1, y1, x2, y2 = index.seg(i)
    if float(index.segs[i * 5 + 4]) > fine:
      continue
    if math.hypot(x2 - x1, y2 - y1) * f < MIN_LINE_MM:
      continue
    if abs(y1 - y2) < tol:
      hl.setdefault(round(y1, 0), []).append((min(x1, x2), max(x1, x2)))
    elif abs(x1 - x2) < tol:
      vl.setdefault(round(x1, 0), []).append((min(y1, y2), max(y1, y2)))
      
  gap = JOIN_GAP_MM / f

  def merged(table: dict) -> list:
    out = []
    for pos, items in table.items():
      cur = None
      for a, b in sorted(items):
        if cur is not None and a <= cur[1] + gap:
          cur[1] = max(cur[1], b)
        else:
          cur = [a, b]
          out.append((pos, cur))
    return [(p, c[0], c[1]) for p, c in out]
  return merged(hl), merged(vl)

def _chains(runs: list, f: float) -> list:
  runs = sorted(runs)[:MAX_RUNS]
  
  found = []
  for p, a, b in runs:
    chain = [(p, a, b)]
    while True:
      cur = chain[-1]
      nxt = None
      for q in runs:
        if q[0] > cur[0] + 5.0 and min(cur[2], q[2]) - max(cur[1], q[1]) >= OVERLAP * min(cur[2] - cur[1], q[2] - q[1]) and (nxt is None or q[0] < nxt[0]):
          nxt = q
      if nxt is None:
        break
      if len(chain) >= 2:
        step = chain[-1][0] - chain[-2][0]
        if abs((nxt[0] - chain[-1][0]) - step) > MODULE_TOL * step:
          break
      chain.append(nxt)
      
    if len(chain) >= MIN_LINES:
      spacing = (chain[1][0] - chain[0][0]) * f
      if MODULE_MIN_MM <= spacing <= MODULE_MAX_MM:
        found.append(([c[0] for c in chain], min(c[1] for c in chain), max(c[2] for c in chain), spacing))
  return found

def joint_zones(index, f: float) -> list:
  hr, vr = _runs(index, f)
  zones = []
  for ps, a, b, sp in _chains(hr, f):
    zones.append({"box": (a, min(ps), b, max(ps)), "lines": len(ps), "spacing_mm": round(sp, 1), "direction": "H"})
  for ps, a, b, sp in _chains(vr, f):
    zones.append({"box": (min(ps), a, max(ps), b), "lines": len(ps), "spacing_mm": round(sp, 1), "direction": "V"})
    
  out = []
  for z in zones:
    x0, y0, x1, y1 = z["box"]
    area = (x1 - x0) * (y1 - y0) * f * f / 1e6
    if area >= MIN_ZONE_M2:
      out.append({**z, "area_m2": round(area, 3)})
  return out

def union_area(zones: list, f: float) -> float:
  cell = CELL_MM / f
  cells: set = set()
  for z in zones:
    x0, y0, x1, y1 = z["box"]
    for i in range(int(x0 // cell), int(x1 // cell) + 1):
      for j in range(int(y0 // cell), int(y1 // cell) + 1):
        cells.add((i, j))
  return len(cells) * CELL_MM * CELL_MM / 1e6

def read(index, f: float, ctx: dict, level_hint: str | None, cls, finish, make) -> dict:
  words = index.words
  view = view_of(words)
  found = levels(words)
  scale = level_scale(found, f)
  labels = [w for w in words if FINISH_LABEL.search(w.text.upper())]
  zones = joint_zones(index, f)
  area = union_area(zones, f)
  
  stats = {"view": view, "levels": [{"mm": l["mm"], "text": l["text"]} for l in sorted(found, key=lambda l: l["mm"])], "level_scale": scale, "finish_labels": len(labels),
    "joint_zones": [{k: v for k, v in z.items() if k != "box"} | {"box_mm": [round(c * f, 1) for c in z["box"]]} for z in zones], "joint_area_m2": round(area, 3)}
  result: dict = {"candidates": [], "notes": [], "stats": stats}
  if scale is not None:
    result["notes"].append(C.note("ELEVATION_LEVELS_AGREE" if scale["agrees"] else "ELEVATION_LEVELS_DIFFER", **{k: scale[k] for k in ("mm_per_pt", "sheet_mm_per_pt", "difference", "from", "to")}))
  if not zones:
    return result

  code, rule = FR.facade_item(view)
  facts = {"derived_from": "ELEVATION_JOINT_ZONES", "elevation": view, "area_m2": round(area, 3), "zones": len(zones), "item_rule": FR.evidence(FR.FACADE_ITEM, rule, elevation=view), "finish_labels": len(labels),
    "level_scale": scale}
  notes = [C.note("ELEVATION_ZONES_ESTIMATED", view=view, area_m2=round(area, 3), zones=len(zones))]
  if code == FR.NONE:
    result["notes"].extend(notes)
    result["notes"].append(C.note("ELEVATION_ZONES_UNBILLED", view=view, area_m2=round(area, 3)))
    return result

  x0 = min(z["box"][0] for z in zones)
  y0 = min(z["box"][1] for z in zones)
  x1 = max(z["box"][2] for z in zones)
  y1 = max(z["box"][3] for z in zones)
  result["candidates"].append(make(cls, ctx, finish, ("FACADE_ZONES", view, level_hint or ""), "FACADE_ZONES", f"Facade finish, {view.lower()} elevation · {area:.2f} m² (estimated)", f"FACADE-{view}",
    [[(x0 + x1) / 2.0, (y0 + y1) / 2.0]], {"length_mm": round(area * 1000.0, 1), "width_mm": 1000.0}, [], notes, facts, 0.45, work_item=code))
  return result
