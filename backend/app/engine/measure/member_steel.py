from __future__ import annotations
from decimal import Decimal
from app.engine.measure.units import q6

MM = Decimal("1000")
EIGHTH_IN_MM = Decimal("3.175")
KG_M_DIVISOR = Decimal("162.2")
BAR_ROLES = ("bottom", "top", "bars", "vertical", "extra")
RING_FAMILIES = ("BEAM", "LINTEL", "COLUMN")
MESH_FAMILIES = ("FOOTING", "SLAB", "RCC_WALL")
STEEL_FAMILIES = RING_FAMILIES + MESH_FAMILIES
FAMILY_OF = {"COLUMN": "COLUMN", "BEAM": "BEAM", "LINTEL": "BEAM", "FOOTING": "FOOTING", "SLAB": "SLAB", "RCC_WALL": "WALL"}
MAX_COUNT = 30

def _num(v) -> Decimal | None:
  try:
    d = Decimal(str(v))
  except Exception:
    return None
  return d if d > 0 and d == d else None

def dia_mm(g: dict) -> Decimal:
  """Diameter of a bar set: a bar number is eighths of an inch (#4 is 12.7 mm); a metric set gives it in millimetres."""
  if g.get("bar") is not None:
    return Decimal(int(g["bar"])) * EIGHTH_IN_MM
  return Decimal(str(g["dia_mm"]))

bar_dia_mm_of = dia_mm

def kg_per_m(g: dict) -> Decimal:
  d = dia_mm(g)
  return (d * d / KG_M_DIVISOR).quantize(Decimal("0.0001"))

def _bar_of(g) -> dict | None:
  """The size of a set as {"bar": n} or {"dia_mm": d}, or None when it does not read."""
  if not isinstance(g, dict):
    return None
  bar, dia = _num(g.get("bar")), _num(g.get("dia_mm"))
  if bar is not None and bar == bar.to_integral_value() and 2 <= bar <= 12:
    return {"bar": int(bar)}
  if bar is None and dia is not None and 6 <= dia <= 40:
    return {"dia_mm": float(dia)}
  return None

def clean_steel(raw) -> dict | None:
  """The bars, rings and mesh of a member as plain numbers; anything that does not read is dropped. None when nothing is left."""
  if not isinstance(raw, dict):
    return None
  out: dict = {}
  for role in BAR_ROLES:
    g = raw.get(role)
    size, n = _bar_of(g), _num(g.get("n")) if isinstance(g, dict) else None
    if size and n is not None and n == n.to_integral_value() and n <= MAX_COUNT:
      out[role] = {"n": int(n), **size}
  ring = raw.get("ring")
  size = _bar_of(ring)
  
  spacing = _num(ring.get("spacing_mm")) if isinstance(ring, dict) else None
  if size and spacing is not None and spacing <= 1000:
    clean = {**size, "spacing_mm": float(spacing)}
    dense, zone = _num(ring.get("dense_spacing_mm")), _num(ring.get("dense_zone_mm"))
    if dense is not None and dense < spacing:
      clean["dense_spacing_mm"] = float(dense)
      if zone is not None and zone <= 3000:
        clean["dense_zone_mm"] = float(zone)
    out["ring"] = clean
    
  mesh = raw.get("mesh")
  size = _bar_of(mesh)
  spacing = _num(mesh.get("spacing_mm")) if isinstance(mesh, dict) else None
  if size and spacing is not None and spacing <= 1000:
    ways, layers = _num(mesh.get("ways")), _num(mesh.get("layers"))
    clean = {**size, "spacing_mm": float(spacing), "ways": 1 if ways == 1 else 2, "layers": 2 if layers == 2 else 1}
    if mesh.get("layer") in ("top", "bottom"):
      clean["layer"] = mesh["layer"]
    out["mesh"] = clean
  return out or None

def _ring_count(run: Decimal, ring: dict) -> int:
  spacing = Decimal(str(ring["spacing_mm"]))
  dense = ring.get("dense_spacing_mm")
  zone = ring.get("dense_zone_mm")
  if dense is not None and zone is not None:
    dense, zone = Decimal(str(dense)), Decimal(str(zone))
    if 2 * zone < run:
      return 2 * (int(zone // dense)) + int((run - 2 * zone) // spacing) + 1
  return int(run // spacing) + 1

def _line(kind: str, role: str, g: dict, count: int, cut: Decimal) -> dict:
  w = kg_per_m(g)
  kg = q6(Decimal(count) * cut * w / MM)
  return {"kind": kind, "role": role, "dia_mm": str(dia_mm(g)), "bar": g.get("bar"), "count": count, "cut_length_m": str(q6(cut / MM)),
    "kg_per_m": str(w), "length_m": str(q6(Decimal(count) * cut / MM)), "kg": str(kg)}

def member_lines(category: str, length: Decimal, width: Decimal, depth: Decimal, steel: dict, cover: Decimal, hook_dia: Decimal,
    lap_dia: Decimal = Decimal("0"), anchor_dia: Decimal = Decimal("0")) -> tuple:
  """The weighed lines of one member as (lines, kg). Each line is a bar set, a ring set or one direction of a mesh with its count, cut length and
  weight, so the trace of a mark can be checked by hand. Dimensions in mm; length, width and depth are those of the measurement (a column's depth is its height)."""
  lines: list = []
  
  if category in ("BEAM", "LINTEL"):
    run = length - 2 * cover
    if run <= 0:
      return [], Decimal("0")
    for role in BAR_ROLES:
      g = steel.get(role)
      if g:
        lines.append(_line("bars", role, g, g["n"], run + 2 * anchor_dia * dia_mm(g)))
    ring = steel.get("ring")
    inner_w, inner_d = width - 2 * cover, depth - 2 * cover
    if ring and inner_w > 0 and inner_d > 0:
      cut = 2 * (inner_w + inner_d) + hook_dia * dia_mm(ring)
      lines.append(_line("rings", "ring", ring, _ring_count(run, ring), cut))
  elif category == "COLUMN":
    height = depth
    if height <= 0:
      return [], Decimal("0")
    
    for role in BAR_ROLES:
      g = steel.get(role)
      if g:
        lines.append(_line("bars", role, g, g["n"], height + (lap_dia + anchor_dia) * dia_mm(g)))
    ring = steel.get("ring")
    inner_l, inner_w = length - 2 * cover, width - 2 * cover
    if ring and inner_l > 0 and inner_w > 0:
      cut = 2 * (inner_l + inner_w) + hook_dia * dia_mm(ring)
      lines.append(_line("rings", "ring", ring, _ring_count(height - 2 * cover if height > 2 * cover else height, ring), cut))
  elif category in MESH_FAMILIES:
    mesh = steel.get("mesh")
    
    if mesh:
      a, b = length - 2 * cover, width - 2 * cover
      if a > 0 and b > 0:
        spacing = Decimal(str(mesh["spacing_mm"]))
        layers = int(mesh.get("layers", 1))
        if int(mesh.get("ways", 2)) == 2:
          lines.append(_line("mesh", "along_length", mesh, (int(b // spacing) + 1) * layers, a))
          lines.append(_line("mesh", "along_width", mesh, (int(a // spacing) + 1) * layers, b))
        elif a >= b:
          lines.append(_line("mesh", "along_width", mesh, (int(a // spacing) + 1) * layers, b))
        else:
          lines.append(_line("mesh", "along_length", mesh, (int(b // spacing) + 1) * layers, a))
  total = q6(sum((Decimal(ln["kg"]) for ln in lines), Decimal("0")))
  return lines, total
