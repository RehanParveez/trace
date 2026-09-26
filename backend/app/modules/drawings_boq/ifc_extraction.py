from __future__ import annotations
import re
import ifcopenshell.util.element
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass, field
from uuid import UUID
from app.modules.drawings_boq.ifc_types import QUANTITY_LOOKUP_ORDER

def humanize_ifc_type(ifc_type: str) -> str:
  """'IfcWallStandardCase' -> 'Wall Standard Case'."""
  stripped = ifc_type[3:] if ifc_type.startswith("Ifc") else ifc_type
  return re.sub(r"(?<!^)(?=[A-Z])", " ", stripped).strip()

def resolve_material_name(element) -> tuple[str, bool]:
  material = ifcopenshell.util.element.get_material(element)
  if material is not None:
    material_name = getattr(material, "Name", None)
    if material_name and material_name.strip():
      return material_name.strip(), False

  element_name = getattr(element, "Name", None)
  if element_name and element_name.strip():
    return element_name.strip(), False

  return humanize_ifc_type(element.is_a()), True

def extract_quantity(element) -> tuple[Decimal, str] | None:

  psets = ifcopenshell.util.element.get_psets(element, qtos_only=True)
  for property_names, unit in QUANTITY_LOOKUP_ORDER:
    for _qto_name, qto_values in psets.items():
      for prop_name in property_names:
        value = qto_values.get(prop_name)
        if value is None:
          continue
        try:
          quantity = Decimal(str(value))
        except (InvalidOperation, TypeError):
          continue
        if quantity > 0:
          return quantity, unit
  return None

@dataclass
class AggregatedGroup:
  ifc_type: str
  raw_material_text: str
  unit: str
  total_quantity: Decimal = field(default_factory=lambda: Decimal("0"))
  element_ids: list[UUID] = field(default_factory=list)
  element_quantities: dict[UUID, Decimal] = field(default_factory=dict)

def aggregate_drawing_elements(elements: list) -> list[AggregatedGroup]:
  groups: dict[tuple[str, str, str], AggregatedGroup] = {}

  for el in elements:
    key = (el.ifc_type, (el.raw_material_text or "").strip().lower(), el.unit)
    group = groups.get(key)
    if group is None:
      group = AggregatedGroup(
        ifc_type=el.ifc_type,
        raw_material_text=el.raw_material_text or humanize_ifc_type(el.ifc_type),
        unit=el.unit,
      )
      groups[key] = group
    group.total_quantity += el.quantity
    group.element_ids.append(el.id)
    group.element_quantities[el.id] = el.quantity

  return list(groups.values())