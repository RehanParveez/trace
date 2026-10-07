from __future__ import annotations
from typing import Any
from decimal import Decimal
import json
import hashlib
from dataclasses import asdict, dataclass, field
from uuid import UUID, uuid4

def _jsonable(value: Any) -> Any:
  if isinstance(value, Decimal):
    return format(value.normalize(), "f")
  raise TypeError(f"Unserialisable {type(value)!r}")

def _digest(data: dict) -> str:
  raw = json.dumps(data, sort_keys=True, separators=(",", ":"), default=_jsonable)
  return hashlib.sha256(raw.encode("utf-8")).hexdigest()

@dataclass(frozen=True)
class OpeningRuleSpec:
  element_scope: str
  lower_area_m2: Decimal
  upper_area_m2: Decimal | None
  behavior: str  
  fraction: Decimal | None = None
  edge_behavior: str | None = None

@dataclass(frozen=True)
class WastageRuleSpec:
  material_class: str
  procurement_stage: str
  factor: Decimal  

@dataclass(frozen=True)
class ReinforcementRuleSpec:
  element_scope: str
  bar_role: str
  lap_basis: str | None
  lap_coefficient: Decimal | None
  hook_rules: dict = field(default_factory=dict)
  bend_rules: dict = field(default_factory=dict)
  dev_length_method: str | None = None
  splice_constraints: dict = field(default_factory=dict)
  extra_config: dict = field(default_factory=dict)
  stock_length_mm: Decimal | None = None
  cover_mm: Decimal | None = None
  min_lap_mm: Decimal | None = None
  use_couplers: bool = False
  weight_tolerance_pct: Decimal = Decimal("2.0")

@dataclass(frozen=True)
class MappingSpec:
  ifc_type: str
  work_item_code: str | None
  default_category: str | None
  quantity_source_preference: str
  unit_override: str | None
  confidence_base: Decimal
  material_class: str | None = None

@dataclass(frozen=True)
class RecipeComponentSpec:
  sequence: int
  work_item_code: str | None
  description_template: str
  unit: str
  formula_code: str
  category: str | None
  item_type: str
  is_optional: bool
  material_class: str | None = None

@dataclass(frozen=True)
class RecipeSpec:
  id: str
  code: str
  name: str
  trigger_ifc_types: tuple[str, ...]
  trigger_conditions: dict
  components: tuple[RecipeComponentSpec, ...]

def _conditions_match(conditions: dict, props: dict) -> bool:
  for key, expected in (conditions or {}).items():
    actual = props.get(key)
    if actual is None:
      return False
    if str(actual).lower() == str(expected).lower():
      continue
    try:
      if abs(float(actual) - float(expected)) > 1e-3:
        return False
    except (TypeError, ValueError):
      return False
  return True

@dataclass(frozen=True)
class FinishRuleSpec:
  space_category: str
  surface: str
  work_item_code: str
  height_mm: Decimal | None
  deduct_openings: bool = True
  priority: int = 0
  exclude: bool = False
  id: UUID = field(default_factory=uuid4)

@dataclass(frozen=True)
class ResolvedRuleProfile:
  rule_set_id: str
  code: str
  immutable_version: int
  content_hash: str | None
  convention_code: str | None
  conserves_volume: bool
  jurisdiction: str | None
  province: str | None
  standard_name: str | None
  standard_edition: str | None
  wall_measurement_method: str
  net_vs_gross_preference: str
  preferred_units: dict
  tolerances: dict
  opening_rules: tuple[OpeningRuleSpec, ...] = ()
  wastage_rules: tuple[WastageRuleSpec, ...] = ()
  reinforcement_rules: tuple[ReinforcementRuleSpec, ...] = ()
  mappings: tuple[MappingSpec, ...] = ()
  recipes: tuple[RecipeSpec, ...] = ()
  finish_rules: tuple[FinishRuleSpec, ...] = ()

  def waste_factor(self, material_class: str | None, stage: str = "SITE") -> Decimal:
    wanted = (material_class or "DEFAULT").upper()
    for cls in (wanted, "DEFAULT"):
      exact = [r for r in self.wastage_rules if r.material_class == cls and r.procurement_stage == stage]
      if exact:
        return exact[0].factor
      any_stage = sorted((r for r in self.wastage_rules if r.material_class == cls), key=lambda r: r.procurement_stage)
      if any_stage:
        return any_stage[0].factor
    return Decimal("1")

  def opening_behavior(self, element_scope: str, area_m2: Decimal) -> tuple[str, Decimal]:
    for scope in (element_scope, "ALL"):
      rules = sorted((r for r in self.opening_rules if r.element_scope == scope), key=lambda r: r.lower_area_m2)
      for r in rules:
        if area_m2 >= r.lower_area_m2 and (r.upper_area_m2 is None or area_m2 < r.upper_area_m2):
          if r.behavior == "IGNORE":
            return "IGNORE", Decimal("0")
          if r.behavior == "PARTIAL":
            return "PARTIAL", r.fraction or Decimal("0")
          return "DEDUCT", Decimal("1")
    return "DEDUCT", Decimal("1")

  def mapping_for(self, ifc_type: str) -> MappingSpec | None:
    return next((m for m in self.mappings if m.ifc_type == ifc_type), None)

  def recipes_for(self, ifc_type: str, properties: dict | None = None) -> tuple[RecipeSpec, ...]:
    props = properties or {}
    return tuple(
      r for r in self.recipes
      if ifc_type in r.trigger_ifc_types and _conditions_match(r.trigger_conditions, props)
    )

  def to_dict(self) -> dict:
    return asdict(self)

  def fingerprint(self) -> str:
    return _digest(self.to_dict())

  def content_fingerprint(self) -> str:
    data = self.to_dict()
    for key in ("rule_set_id", "immutable_version", "content_hash"):
      data.pop(key, None)
    for recipe in data.get("recipes", []):
      recipe.pop("id", None)
    return _digest(data)