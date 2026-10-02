from __future__ import annotations
from decimal import Decimal
from dataclasses import dataclass
from typing import Callable

CANONICAL_UNITS = frozenset({"m3", "m2", "m", "kg", "nos"})

def _identity(quantity: Decimal) -> Decimal:
  return quantity

@dataclass(frozen=True)
class FormulaSpec:
  code: str
  output_unit: str
  description: str
  input_unit: str | None = None 
  group_evaluator: Callable[[Decimal], Decimal] | None = None

  @property
  def needs_kernel(self) -> bool:
    return self.group_evaluator is None

  def evaluate_group(self, parent_quantity: Decimal, parent_unit: str) -> Decimal | None:
    if self.group_evaluator is None or parent_unit != self.input_unit:
      return None
    return self.group_evaluator(parent_quantity)

_SPECS = (
  FormulaSpec("SOLID_NET_VOLUME", "m3", "Net solid volume after allocation (concrete, masonry, PCC).", "m3", _identity),
  FormulaSpec("WALL_NET_VOLUME", "m3", "Wall L x H x T less openings at/above threshold and allocated intrusions.", "m3", _identity),
  FormulaSpec("WALL_FACE_AREA_NET", "m2", "Wall face area per face less openings at/above threshold; reveals per convention."),
  FormulaSpec("PAINT_AREA", "m2", "Plaster area x coats."),
  FormulaSpec("SOLID_FORMWORK_AREA", "m2", "Exposed faces by role less contact faces with other concrete."),
  FormulaSpec("SLAB_SOFFIT_AREA", "m2", "Slab plan area less column footprints."),
  FormulaSpec("FLOOR_FINISH_AREA", "m2", "From space boundaries, else slab top net."),
  FormulaSpec("OPENING_COUNT", "nos", "Doors/windows by type mark and size.", "nos", _identity),
  FormulaSpec("FOOTING_PCC_VOLUME", "m3", "Footing plan plus projection x blinding thickness."),
  FormulaSpec("EXCAVATION_VOLUME", "m3", "Footing plan plus working space x depth (convention parameters)."),
  FormulaSpec("REBAR_KG", "kg", "Sum of bar marks."),
)

FORMULAS: dict[str, FormulaSpec] = {s.code: s for s in _SPECS}

def get_formula(code: str | None) -> FormulaSpec | None:
  return FORMULAS.get(code) if code else None

def check_component_units(
  formula_code: str,
  unit: str,
  output_unit: str | None = None,
) -> list[tuple[str, str]]:
  """Returns [(issue_code, message)]; empty list means unit-safe."""
  spec = get_formula(formula_code)
  if spec is None:
    return [("FORMULA_UNKNOWN", f"Unknown formula code '{formula_code}'.")]
  problems: list[tuple[str, str]] = []
  if unit != spec.output_unit:
    problems.append((
      "RECIPE_UNIT_MISMATCH",
      f"Component unit '{unit}' does not match formula {formula_code} output unit '{spec.output_unit}'.",
    ))
  if output_unit is not None and output_unit != spec.output_unit:
    problems.append((
      "RECIPE_UNIT_MISMATCH",
      f"Component output_unit '{output_unit}' does not match formula {formula_code} output unit '{spec.output_unit}'.",
    ))
  return problems