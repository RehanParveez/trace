from __future__ import annotations
from app.engine.measure import readings as QS
from app.engine.measure.wall_finishes import opening_faces, reveal_mm2

CHOICE = "opening_rules_basis"
SHEET, IS1200 = "SHEET", "IS1200"

def brick_min_m2() -> float:
  return float(QS.param("brick_opening_min_m2"))

def rcc_wall_min_m2() -> float:
  return float(QS.param("rcc_wall_opening_min_m2"))

def plaster_min_m2() -> float:
  """The smallest opening deducted from plaster and paint, on the sheet's own rule and on IS 1200 alike (rule plaster_opening_min_m2, 0.5 m2)."""
  return float(QS.param("plaster_opening_min_m2"))

def plaster_one_face_max_m2() -> float:
  """The largest opening that comes off one face of the plaster only, under IS 1200 (rule plaster_opening_one_face_max_m2, 3.0 m2)."""
  return float(QS.param("plaster_opening_one_face_max_m2"))

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
  return area_m2 >= (rcc_wall_min_m2() if kind == "RCC" else brick_min_m2())

def _conventions(kind: str, brick_off: bool) -> list:
  out = [{"key": "opening_rules_basis", "value": QS.choice(CHOICE)}]
  if kind == "BRICK":
    out += [{"key": "deduct_opening_brick", "value": not brick_off}, {"key": "brick_opening_min_m2", "value": brick_min_m2()}]
  else:
    out.append({"key": "rcc_wall_opening_min_m2", "value": rcc_wall_min_m2()})
  return out

def apply(walls: list) -> dict:
  stats = {"basis": QS.choice(CHOICE), "walls": 0, "openings": 0, "off": 0, "not_off": 0}
  brick_off = not QS.flag("deduct_opening_brick")
  stats["brick_deducted"] = not brick_off
  if not is1200() and not brick_off:
    return stats
  for w in walls:
    kind = wall_kind(w)
    ops = (w.params or {}).get("openings")
    if kind is None or not ops:
      continue
    if not is1200() and kind != "BRICK":
      continue
    stats["walls"] += 1
    w.facts = {**(w.facts or {}), "conventions": _conventions(kind, brick_off)}
    for o in ops:
      flag = False if (brick_off and kind == "BRICK") else deducts(kind, each_m2(o))
      o["deduct"] = flag
      stats["openings"] += int(o.get("nos") or 1)
      stats["off" if flag else "not_off"] += int(o.get("nos") or 1)
  return stats

def plaster_sides(openings: list, thickness_mm: float, faces_in: int, faces_out: int) -> tuple:
  d_in = d_out = rev = 0.0
  for o in openings or []:
    a, n = each_m2(o), int(o.get("nos") or 1)
    fi, fo, reveals = opening_faces(a, 1.0, plaster_min_m2(), plaster_one_face_max_m2(), faces_in, faces_out)
    d_in += n * a * fi
    d_out += n * a * fo

    if reveals:
      rev += n * reveal_mm2(str(o.get("role") or "OPENING").upper(), float(o.get("width_mm") or 0.0), float(o.get("height_mm") or 0.0), thickness_mm) / 1_000_000.0
  return d_in, d_out, rev
