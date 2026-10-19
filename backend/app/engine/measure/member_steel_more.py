from __future__ import annotations
from decimal import Decimal
from app.engine.measure.units import q6

MORE_FAMILIES = ("STAIR", "TANK", "PARAPET", "CHAJJA", "BALCONY_SLAB")
SLAB_LIKE = ("CHAJJA", "BALCONY_SLAB")

def _mesh_of(m) -> dict | None:
  from app.engine.measure.member_steel import _bar_of, _num
  if not isinstance(m, dict):
    return None
  size, spacing = _bar_of(m), _num(m.get("spacing_mm"))
  if not size or spacing is None or spacing > 1000:
    return None
  ways, layers = _num(m.get("ways")), _num(m.get("layers"))
  clean = {**size, "spacing_mm": float(spacing), "ways": 1 if ways == 1 else 2, "layers": 2 if layers == 2 else 1}
  if m.get("layer") in ("top", "bottom"):
    clean["layer"] = m["layer"]
  return clean

def clean_more(raw: dict, out: dict) -> None:
  """Keep the second way of a mesh and the slab mesh of a tank when they read."""
  from app.engine.measure.member_steel import _bar_of, _num
  slab = _mesh_of(raw.get("slab_mesh"))
  
  if slab:
    out["slab_mesh"] = slab
  across = (raw.get("mesh") or {}).get("across") if isinstance(raw.get("mesh"), dict) else None
  if across and "mesh" in out:
    size, spacing = _bar_of(across), _num(across.get("spacing_mm")) if isinstance(across, dict) else None
    if size and spacing is not None and spacing <= 1000:
      out["mesh"]["across"] = {**size, "spacing_mm": float(spacing)}

def two_way(length: Decimal, width: Decimal, mesh: dict, cover: Decimal) -> list:
  from app.engine.measure.member_steel import _line
  a, b = length - 2 * cover, width - 2 * cover
  if a <= 0 or b <= 0:
    return []
  layers = int(mesh.get("layers", 1))
  s1, across = Decimal(str(mesh["spacing_mm"])), mesh["across"]
  s2 = Decimal(str(across["spacing_mm"]))
  return [_line("mesh", "along_length", mesh, (int(b // s1) + 1) * layers, a), _line("mesh", "along_width", across, (int(a // s2) + 1) * layers, b)]

def _mesh_part(prefix: str, length: Decimal, width: Decimal, mesh: dict | None, cover: Decimal) -> list:
  from app.engine.measure.member_steel import member_lines
  if not mesh:
    return []
  lines, _ = member_lines("SLAB", length, width, Decimal("0"), {"mesh": mesh}, cover, Decimal("0"))
  return [{**ln, "role": f"{prefix}_{ln['role']}"} for ln in lines]

def stair_slope_mm(stair: dict | None, fallback: Decimal) -> Decimal:
  if not stair:
    return fallback
  riser, tread, steps = Decimal(str(stair["riser_mm"])), Decimal(str(stair["tread_mm"])), Decimal(str(stair["steps"]))
  return steps * (riser * riser + tread * tread).sqrt()

def more_lines(category: str, length: Decimal, width: Decimal, depth: Decimal, steel: dict, cover: Decimal, extra: dict | None) -> tuple:
  """(lines, kg) for one member. length, width and depth are those of the measurement; extra is {"stair": {...}} or {"site": {...}} as the formwork reads them."""
  extra = extra or {}
  lines: list = []
  
  mesh = steel.get("mesh")
  if category == "STAIR":
    slope = stair_slope_mm(extra.get("stair"), length)
    lines = _mesh_part("flight", slope, width, mesh, cover)
  elif category in SLAB_LIKE:
    lines = _mesh_part("slab", length, width, mesh, cover)
  elif category == "PARAPET":
    lines = _mesh_part("parapet", length, depth, mesh, cover)
  elif category == "TANK":
    site = extra.get("site") or {}
    
    height, wall = Decimal(str(site.get("height_mm") or 0)), Decimal(str(site.get("wall_mm") or 0))
    if height > 0 and wall > 0 and length > 2 * wall and width > 2 * wall:
      perimeter = 2 * ((length - wall) + (width - wall))
      lines = _mesh_part("wall", perimeter, height, mesh, cover)
      slab = steel.get("slab_mesh")
      lines += _mesh_part("top", length, width, slab, cover) + _mesh_part("bottom", length, width, slab, cover)
  return lines, q6(sum((Decimal(ln["kg"]) for ln in lines), Decimal("0")))
