from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field, model_validator
from decimal import Decimal
from typing import Literal
from datetime import date, datetime
from uuid import UUID

ItemType = Literal["MATERIAL", "LABOUR", "CUSTOM"]

class OpeningRuleSchema(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  element_scope: str = Field(default="ALL", min_length=1, max_length=50)
  lower_area_m2: Decimal = Field(default=Decimal("0"), ge=0)
  upper_area_m2: Decimal | None = Field(default=None, gt=0)
  deduction_behavior: Literal["DEDUCT", "IGNORE", "PARTIAL"] = "DEDUCT"
  deduction_fraction: Decimal | None = Field(default=None, ge=0, le=1)
  edge_behavior: str | None = Field(default=None, max_length=50)
  extra_config: dict = Field(default_factory=dict)

  @model_validator(mode="after")
  def _check(self):
    if self.upper_area_m2 is not None and self.upper_area_m2 <= self.lower_area_m2:
      raise ValueError("upper_area_m2 must be greater than lower_area_m2")
    if self.deduction_behavior == "PARTIAL" and self.deduction_fraction is None:
      raise ValueError("PARTIAL deduction requires deduction_fraction")
    return self

class WastageRuleSchema(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  material_class: str = Field(min_length=1, max_length=80)
  procurement_stage: str = Field(default="SITE", min_length=1, max_length=40)
  factor: Decimal = Field(default=Decimal("1.0"), ge=1, le=2, description="1.03 = 3 % extra")
  unit: str | None = Field(default=None, max_length=20)
  justification: str | None = None

class ReinforcementRuleSchema(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  element_scope: str = Field(default="ALL", min_length=1, max_length=50)
  bar_role: str = Field(min_length=1, max_length=50)
  lap_basis: str | None = Field(default=None, max_length=30)
  lap_coefficient: Decimal | None = Field(default=None, ge=0)
  hook_rules: dict = Field(default_factory=dict)
  bend_rules: dict = Field(default_factory=dict)
  dev_length_method: str | None = Field(default=None, max_length=40)
  splice_constraints: dict = Field(default_factory=dict)
  extra_config: dict = Field(default_factory=dict)
  stock_length_mm: Decimal | None = Field(default=None, gt=0)
  cover_mm: Decimal | None = Field(default=None, ge=0)
  min_lap_mm: Decimal | None = Field(default=None, ge=0)
  use_couplers: bool = False
  weight_tolerance_pct: Decimal = Field(default=Decimal("2.0"), ge=0)

class MappingSchema(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  ifc_type: str = Field(min_length=1, max_length=100)
  work_item_code: str | None = Field(default=None, max_length=50)
  default_category: str | None = Field(default=None, max_length=150)
  quantity_source_preference: str = Field(default="qto_first", max_length=30)
  unit_override: str | None = Field(default=None, max_length=20)
  confidence_base: Decimal = Field(default=Decimal("0.85"), ge=0, le=1)
  extra_mapping: dict = Field(default_factory=dict, description='Optional {"material_class": "CONCRETE"}')
  
class FinishRuleSchema(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  space_category: str = Field(default="ALL", min_length=1, max_length=40)
  surface: Literal["FLOOR", "WALL", "CEILING", "SKIRTING", "DADO", "STAIR", "WATERPROOFING"]
  work_item_code: str = Field(min_length=1, max_length=50)
  height_mm: Decimal | None = Field(default=None, gt=0)
  deduct_openings: bool = True
  priority: int = Field(default=0, description="Stored but not used by the engine yet")
  exclude: bool = Field(default=False, description="Remove this finish for the category (needs a matching ALL rule)")
  extra_config: dict = Field(default_factory=dict)

  @model_validator(mode="before")
  @classmethod
  def _from_row(cls, data):
    if isinstance(data, dict):
      return data
    extra = dict(getattr(data, "extra_config", None) or {})
    return {"space_category": data.space_category, "surface": data.surface, "work_item_code": data.work_item_code,
      "height_mm": data.height_mm, "deduct_openings": data.deduct_openings, "priority": data.priority,
      "exclude": bool(extra.pop("exclude", False)), "extra_config": extra}

class RecipeComponentRequest(BaseModel):
  sequence: int = Field(default=0, ge=0)
  work_item_code: str | None = Field(default=None, max_length=50)
  description_template: str = Field(min_length=1, max_length=500)
  unit: str = Field(min_length=1, max_length=20, description="Must equal the formula's output unit")
  quantity_formula_code: str = Field(min_length=1, max_length=80)
  category: str | None = Field(default=None, max_length=150)
  item_type: ItemType = "MATERIAL"
  is_optional: bool = False

class RecipeUpsertRequest(BaseModel):
  code: str = Field(min_length=1, max_length=80)
  name: str = Field(min_length=1, max_length=200)
  description: str | None = None
  trigger_ifc_types: list[str] = Field(min_length=1)
  trigger_conditions: dict = Field(default_factory=dict)
  components: list[RecipeComponentRequest] = Field(min_length=1)

class RecipeComponentResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  sequence: int
  work_item_code: str | None
  description_template: str
  unit: str
  quantity_formula_code: str
  output_unit: str
  category: str | None
  item_type: str
  is_optional: bool

class RecipeResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  code: str
  name: str
  description: str | None
  trigger_ifc_types: list
  trigger_conditions: dict
  is_active: bool
  components: list[RecipeComponentResponse]

class RuleSetResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  organization_id: UUID | None
  code: str
  name: str
  description: str | None
  jurisdiction: str | None
  province: str | None
  city: str | None
  standard_name: str | None
  standard_edition: str | None
  effective_from: date | None
  effective_to: date | None
  status: str
  immutable_version: int
  convention_code: str | None
  is_system: bool
  published_at: datetime | None
  content_hash: str | None
  supersedes_rule_set_id: UUID | None
  wall_measurement_method: str
  net_vs_gross_preference: str
  preferred_units: dict
  extra_config: dict

class RuleSetDetailResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  rule_set: RuleSetResponse
  opening_rules: list[OpeningRuleSchema]
  wastage_rules: list[WastageRuleSchema]
  reinforcement_rules: list[ReinforcementRuleSchema]
  mappings: list[MappingSchema]
  recipes: list[RecipeResponse]
  finish_rules: list[FinishRuleSchema] = Field(default_factory=list)

class RuleSetCreateRequest(BaseModel):
  code: str = Field(min_length=1, max_length=50)
  name: str = Field(min_length=1, max_length=200)
  description: str | None = None
  jurisdiction: str | None = Field(default=None, max_length=50)
  province: str | None = Field(default=None, max_length=50)
  city: str | None = Field(default=None, max_length=100)
  standard_name: str | None = Field(default=None, max_length=100)
  standard_edition: str | None = Field(default=None, max_length=50)
  effective_from: date | None = None
  effective_to: date | None = None
  convention_code: str | None = Field(default=None, max_length=80)

class RuleSetDraftUpdateRequest(BaseModel):
  name: str | None = Field(default=None, min_length=1, max_length=200)
  description: str | None = None
  jurisdiction: str | None = Field(default=None, max_length=50)
  province: str | None = Field(default=None, max_length=50)
  city: str | None = Field(default=None, max_length=100)
  standard_name: str | None = Field(default=None, max_length=100)
  standard_edition: str | None = Field(default=None, max_length=50)
  effective_from: date | None = None
  effective_to: date | None = None
  convention_code: str | None = Field(default=None, max_length=80)
  wall_measurement_method: str | None = Field(default=None, max_length=30)
  net_vs_gross_preference: Literal["net", "gross"] | None = None
  preferred_units: dict | None = None
  extra_config: dict | None = None
  opening_rules: list[OpeningRuleSchema] | None = None
  wastage_rules: list[WastageRuleSchema] | None = None
  reinforcement_rules: list[ReinforcementRuleSchema] | None = None
  mappings: list[MappingSchema] | None = None
  finish_rules: list[FinishRuleSchema] | None = None

class ValidationIssue(BaseModel):
  code: str
  severity: Literal["error", "warning", "info"]
  message: str
  ref: str | None = None

class ValidationResponse(BaseModel):
  valid: bool
  issues: list[ValidationIssue]

class PublishResponse(BaseModel):
  rule_set: RuleSetResponse
  warnings: list[ValidationIssue]

class WorkItemCreateRequest(BaseModel):
  code: str = Field(min_length=1, max_length=50)
  description: str = Field(min_length=1, max_length=500)
  unit: str = Field(min_length=1, max_length=20, description="Canonical unit: m3, m2, m, kg, nos")
  trade: str | None = Field(default=None, max_length=80)
  wbs_code: str | None = Field(default=None, max_length=50)
  specification: str | None = None
  csr_ref: str | None = Field(default=None, max_length=80)
  default_formula_code: str | None = Field(default=None, max_length=80)
  extra: dict = Field(default_factory=dict, description='e.g. {"material_class": "CONCRETE"}')

class WorkItemUpdateRequest(BaseModel):
  description: str | None = Field(default=None, min_length=1, max_length=500)
  trade: str | None = Field(default=None, max_length=80)
  wbs_code: str | None = Field(default=None, max_length=50)
  specification: str | None = None
  csr_ref: str | None = Field(default=None, max_length=80)
  default_formula_code: str | None = Field(default=None, max_length=80)
  is_active: bool | None = None
  extra: dict | None = None

class WorkItemResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  organization_id: UUID | None
  code: str
  description: str
  unit: str
  trade: str | None
  wbs_code: str | None
  specification: str | None
  csr_ref: str | None
  default_formula_code: str | None
  is_system: bool
  is_active: bool
  extra: dict

class FormulaResponse(BaseModel):
  code: str
  output_unit: str
  description: str
  input_unit: str | None
  needs_kernel: bool


class ConventionResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  code: str
  name: str
  description: str | None
  conserves_volume: bool
  parameters: dict
  
class FinishRuleSchema(BaseModel):
  space_category: str = Field(default="ALL", min_length=1, max_length=40)
  surface: Literal["FLOOR", "WALL", "CEILING", "SKIRTING", "DADO", "STAIR", "WATERPROOFING"]
  work_item_code: str = Field(min_length=1, max_length=50)
  height_mm: Decimal | None = Field(default=None, gt=0)
  deduct_openings: bool = True
  priority: int = 0
  exclude: bool = False
  extra_config: dict = Field(default_factory=dict)