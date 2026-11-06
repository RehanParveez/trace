from __future__ import annotations

COMPUTED, ENGINE = "COMPUTED", "ENGINE"
Interval = tuple

def exact(v: float) -> Interval:
  return (float(v), float(v), float(v))

def _first_less_rest(src: list, quantities: dict, pct) -> Interval:
  head, *rest = src
  a = quantities[head]
  lo = a[1] - sum(quantities[s][2] for s in rest if s in quantities)
  hi = a[2] - sum(quantities[s][1] for s in rest if s in quantities)
  v = a[0] - sum(quantities[s][0] for s in rest if s in quantities)
  return (max(v, 0.0), max(lo, 0.0), max(hi, 0.0))

def _binding(src: list, quantities: dict, pct) -> Interval:
  q = quantities[src[0]]
  return (q[0] * pct[0] / 100.0, q[1] * pct[1] / 100.0, q[2] * pct[2] / 100.0)

def _same(src: list, quantities: dict, pct) -> Interval:
  return quantities[src[0]]

RULES = {
  "excavation_minus_buried": {"kind": COMPUTED, "fn": _first_less_rest, "input": None,
    "text": "The excavation less the plain concrete, the footings, the plinth beam and the brick below ground; the first source is the excavation, the rest are buried."},
  "excavation_minus_fill": {"kind": COMPUTED, "fn": _first_less_rest, "input": None,
    "text": "The excavation less the filling put back under the floors."},
  "binding_wire_pct": {"kind": COMPUTED, "fn": _binding, "input": "binding_percent",
    "text": "The weight of the steel times the binding wire percentage."},
  "putty_from_paint_area": {"kind": COMPUTED, "fn": _same, "input": None,
    "text": "The wall putty area is the painted wall area."},
  "footing_contact_faces": {"kind": ENGINE, "text": "Formwork to the faces of the footings that touch concrete; the engine's formwork line."},
  "perimeter_x_height": {"kind": ENGINE, "text": "Formwork to the columns: perimeter times height; the engine's formwork line."},
  "soffit_plus_sides": {"kind": ENGINE, "text": "Formwork to the beams: soffit plus the two sides; the engine's formwork line."},
  "soffit_plus_edges": {"kind": ENGINE, "text": "Formwork to the slabs: soffit plus edges; the engine's formwork line."},
  "contact_faces": {"kind": ENGINE, "text": "Formwork to stairs, tanks and walls: the faces that touch concrete; the engine's formwork line."},
  "soffit_area_x_support_height": {"kind": ENGINE, "text": "Centring and props under a slab: soffit area times the support height; the engine's formwork line."},
}

def kind_of(rule: str) -> str | None:
  r = RULES.get(rule)
  return r["kind"] if r else None
