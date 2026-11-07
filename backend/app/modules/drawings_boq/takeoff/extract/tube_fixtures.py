from __future__ import annotations
import math
from app.engine.measure import rule_registry as RR

RULE = "TUBE_FIXTURE_ITEMS"
META_KEY = "tube_fixture_items"
SOURCE_KEY = "tube_fixtures"
DISCIPLINES = ("ELECTRICAL",)
ROLES = ("PLAN",)
HEAVY_SHARE = 0.5
ANGLE_TOL = math.radians(1.5)
LENGTH_TOL_SHARE = 0.04
ALONG_TOL_SEP = 1.0
LENGTH_MM = (300.0, 1500.0)
GAP_MM = (10.0, 60.0)
CELL = 60.0

def enabled() -> bool:
  return RR.on(RULE)

def _unique_heavy(segs) -> list:
  widest = 0.0
  for i in range(4, len(segs), 5):
    widest = max(widest, float(segs[i]))
  if widest <= 0.0:
    return []
  
  out, seen = [], set()
  for i in range(0, len(segs) - 4, 5):
    x0, y0, x1, y1, w = (float(v) for v in segs[i:i + 5])
    if w < HEAVY_SHARE * widest:
      continue
    k = (round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1))
    if k in seen or (k[2], k[3], k[0], k[1]) in seen:
      continue
    seen.add(k)
    L = math.hypot(x1 - x0, y1 - y0)
    if L > 0.0:
      out.append((x0, y0, x1, y1, L))
  return out

def _pair(a: tuple, b: tuple) -> tuple | None:
  ax, ay = (a[2] - a[0]) / a[4], (a[3] - a[1]) / a[4]
  bx, by = (b[2] - b[0]) / b[4], (b[3] - b[1]) / b[4]
  if abs(ax * by - ay * bx) > math.sin(ANGLE_TOL) or abs(a[4] - b[4]) > LENGTH_TOL_SHARE * a[4]:
    return None
  nx, ny = -ay, ax
  gap = abs((b[0] - a[0]) * nx + (b[1] - a[1]) * ny)
  if gap <= 0.0:
    return None
  
  if ax * bx + ay * by < 0.0:
    b = (b[2], b[3], b[0], b[1], b[4])
  along = abs((b[0] - a[0]) * ax + (b[1] - a[1]) * ay) + abs((b[2] - a[2]) * ax + (b[3] - a[3]) * ay)
  if along > ALONG_TOL_SEP * max(gap, 1.0) * 2.0:
    return None
  return gap, a[4], [round((a[0] + a[2] + b[0] + b[2]) / 4, 1), round((a[1] + a[3] + b[1] + b[3]) / 4, 1)]

def pairs_of(segs) -> list:
  heavy = _unique_heavy(segs)
  grid: dict = {}
  
  for i, s in enumerate(heavy):
    grid.setdefault((int((s[0] + s[2]) / 2 // CELL), int((s[1] + s[3]) / 2 // CELL)), []).append(i)
  out, used = [], set()
  for i, a in enumerate(heavy):
    cx, cy = int((a[0] + a[2]) / 2 // CELL), int((a[1] + a[3]) / 2 // CELL)
    for dx in (-1, 0, 1):
      for dy in (-1, 0, 1):
        for j in grid.get((cx + dx, cy + dy), ()):
          if j <= i or i in used or j in used:
            continue
          p = _pair(a, heavy[j])
          if p is not None:
            used.update((i, j))
            out.append({"gap": round(p[0], 2), "length": round(p[1], 2), "at": p[2]})
            
  return sorted(out, key=lambda r: (r["at"][1], r["at"][0]))

def read(raw) -> dict | None:
  if not enabled() or not len(getattr(raw, "segs", ())):
    return None
  got = pairs_of(raw.segs)
  return {"pairs": got} if got else None

def fixtures(pairs: list, mm_per_pt: float | None) -> list:
  if not mm_per_pt:
    return []
  return [p for p in pairs if LENGTH_MM[0] <= p["length"] * mm_per_pt <= LENGTH_MM[1] and GAP_MM[0] <= p["gap"] * mm_per_pt <= GAP_MM[1]]

def apply(rows: list) -> int:
  made = 0
  for row in rows:
    meta = row.get("meta")
    if meta is None:
      continue
    meta.pop(META_KEY, None)
    if not enabled():
      continue
    
    ident = meta.get("identity") or {}
    if ident.get("discipline") not in DISCIPLINES or ident.get("role") not in ROLES:
      continue
    pairs = ((meta.get("structure_tables") or {}).get(SOURCE_KEY) or {}).get("pairs") or []
    got = fixtures(pairs, row.get("mm_per_pt"))
    if got:
      meta[META_KEY] = {"fixtures": [{"at": p["at"], "length": p["length"]} for p in got]}
      made += len(got)
  return made
