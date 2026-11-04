from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field

class SteelFigureOut(BaseModel):
  formula: str
  kg: Decimal | None
  origin: str | None
  note: str | None = None
  applied_count: int | None = None
  applied_kg: Decimal | None = None
  signed_count: int | None = None

class SteelLineOut(BaseModel):
  formula: str | None
  source: str | None
  quantity_kg: Decimal | None
  unit: str
  note: str
  audited: bool

class OpenFindingsOut(BaseModel):
  count: int
  by_class: dict[str, int]
  by_code: dict[str, int]
  effect_kg: Decimal

class DiameterOut(BaseModel):
  dia: int
  label: str
  mm: Decimal | None
  bbs_kg: Decimal
  applied_kg: Decimal
  audited_kg: Decimal

class WastageOut(BaseModel):
  pct: Decimal
  kg: Decimal | None
  total_kg: Decimal | None

class SteelDocumentOut(BaseModel):
  document_id: UUID
  file_name: str | None
  version: int
  run_id: UUID | None
  run_level: str | None
  run_created_at: datetime | None

class SteelFiguresOut(BaseModel):
  figures: dict[str, SteelFigureOut]
  requested_source: str | None
  source: str | None
  fell_back_from: str | None
  line: SteelLineOut
  open_findings: OpenFindingsOut
  by_diameter: list[DiameterOut]
  unattributed_kg: Decimal | None
  allocated_kg: Decimal | None
  wastage: WastageOut | None
  ledger_gap_kg: Decimal | None
  ledger_bbs_kg: Decimal | None
  document: SteelDocumentOut | None
  has_document: bool
  has_audit: bool
  run_id: UUID
  project_id: UUID
  sources: list[str]

class SteelSourceIn(BaseModel):
  source: str = Field(min_length=3, max_length=20)

class SteelSourceOut(BaseModel):
  project_id: UUID
  source: str | None
  sources: list[str]
