from __future__ import annotations
from uuid import UUID
from decimal import Decimal
from dataclasses import dataclass, field

@dataclass(frozen=True)
class ModelElement:
  id: UUID
  ifc_type: str
  role: str
  level_id: UUID | None
  geometry_kind: str | None
  profile: dict | None
  placement: dict | None
  volume_mm3: Decimal | None
  bbox_min_mm: tuple | None
  bbox_max_mm: tuple | None
  classification_confidence: Decimal
  normalization_status: str

@dataclass(frozen=True)
class MappingInput:
  ifc_type: str
  work_item_code: str | None
  confidence_base: Decimal

@dataclass(frozen=True)
class CalculationContext:
  run_id: UUID
  engine_version: str
  fingerprint: str
  convention_code: str | None
  rule_set_code: str
  rule_set_version: int
  mappings: tuple[MappingInput, ...]
  convention_params: dict = field(default_factory=dict)

@dataclass(frozen=True)
class Solid:
  id: UUID
  element_id: UUID
  ifc_type: str
  role: str
  level_id: UUID | None
  geometry_kind: str
  classification_confidence: Decimal
  confidence_factor: Decimal
  component_type: str = "BODY"
  material_grade: str | None = None
  gross_volume_m3: Decimal | None = None
  gross_area_m2: Decimal | None = None
  gross_length_m: Decimal | None = None
  count: int | None = None
  status: str = "OK"
  issues: tuple = ()

@dataclass(frozen=True)
class LedgerEntry:
  solid_id: UUID
  element_id: UUID
  level_id: UUID | None
  work_item_code: str
  quantity: Decimal
  unit: str
  material_grade: str | None
  confidence: Decimal
  formula_code: str
  trace: dict
  warnings: tuple = ()

@dataclass(frozen=True)
class Rejected:
  element_id: UUID
  ifc_type: str
  code: str
  message: str

@dataclass(frozen=True)
class CalculationResult:
  solids: list[Solid]
  ledger: list[LedgerEntry]
  rejected: list[Rejected]
  skipped_by_role: dict = field(default_factory=dict)
  unmapped_by_type: dict = field(default_factory=dict)
  deductions: list = field(default_factory=list)
  
@dataclass(frozen=True)
class Prism:
  plan: tuple
  z0: float
  z1: float
  exact: bool

@dataclass(frozen=True)
class SpatialIndex:
  prisms: dict
  polys: dict
  candidates: list
  unallocated: frozenset

@dataclass(frozen=True)
class Overlap:
  a: UUID
  b: UUID
  volume_mm3: float

@dataclass(frozen=True)
class Deduction:
  from_solid_id: UUID
  to_solid_id: UUID | None
  deduction_type: str
  quantity: Decimal
  unit: str
  rule_code: str
  geometry: dict
  explanation: str

@dataclass(frozen=True)
class AllocationResult:
  deductions: list = field(default_factory=list)
  approximate_solids: frozenset = frozenset()
  unallocated_solids: frozenset = frozenset()
  solid_warnings: dict = field(default_factory=dict)
  conservation_failures: tuple = ()
  applied: bool = False
  stats: dict = field(default_factory=dict)

  @classmethod
  def empty(cls) -> "AllocationResult":
    return cls()