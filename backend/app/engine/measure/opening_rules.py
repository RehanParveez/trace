from __future__ import annotations
from app.engine.measure import readings as QS
from app.engine.measure.wall_finishes import opening_faces, reveal_mm2

CHOICE = "opening_rules_basis"
SHEET, IS1200 = "SHEET", "IS1200"

BRICK_MIN_M2 = 0.1
RCC_WALL_MIN_M2 = 0.4
PLASTER_MIN_M2 = 0.5
PLASTER_ONE_FACE_MAX_M2 = 3.0
SHEET_MIN_M2 = 0.5

def is1200() -> bool:
  return QS.choice(CHOICE) == IS1200

def each_m2(o: dict) -> float:
  return float(o.get("width_mm") or 0.0) * float(o.get("height_mm") or 0.0) / 1_000_000.0

def wall_kind(wall) -> str | None:
  """BRICK or RCC for a wall whose openings the rules apply to; None for tank walls and foundation items."""
  f = wall.facts or {}
  if wall.category != "WALL" or f.get("enclosure") or f.get("foundation_item"):
    return None
  return "RCC" if f.get("construction") == "RCC" else "BRICK"

def deducts(kind: str, area_m2: float) -> bool:
  return area_m2 >= (RCC_WALL_MIN_M2 if kind == "RCC" else BRICK_MIN_M2)

def apply(walls: list) -> dict:
  stats = {"basis": QS.choice(CHOICE), "walls": 0, "openings": 0, "off": 0, "not_off": 0}
  if not is1200():
    return stats
  for w in walls:
    kind = wall_kind(w)
    ops = (w.params or {}).get("openings")
    if kind is None or not ops:
      continue
    stats["walls"] += 1
    for o in ops:
      flag = deducts(kind, each_m2(o))
      o["deduct"] = flag
      stats["openings"] += int(o.get("nos") or 1)
      stats["off" if flag else "not_off"] += int(o.get("nos") or 1)
  return stats

def plaster_sides(openings: list, thickness_mm: float, faces_in: int, faces_out: int) -> tuple:
  d_in = d_out = rev = 0.0
  for o in openings or []:
    a, n = each_m2(o), int(o.get("nos") or 1)
    fi, fo, reveals = opening_faces(a, 1.0, PLASTER_MIN_M2, PLASTER_ONE_FACE_MAX_M2, faces_in, faces_out)
    d_in += n * a * fi
    d_out += n * a * fo
    if reveals:
      rev += n * reveal_mm2(str(o.get("role") or "OPENING").upper(), float(o.get("width_mm") or 0.0), float(o.get("height_mm") or 0.0), thickness_mm) / 1_000_000.0
  return d_in, d_out, rev
