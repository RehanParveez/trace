from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from typing import Literal

class BbsDocumentOut(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  project_id: UUID
  file_name: str | None
  sha256: str
  status: str
  version: int
  title: str | None
  pages: int
  profile: str
  created_at: datetime
  row_count: int = 0
  sheet_count: int = 0

class BbsUploadResponse(BaseModel):
  document: BbsDocumentOut
  summary: dict
  previous_version: int | None

class BbsSheetOut(BaseModel):
  id: UUID
  idx: int
  name: str
  first_page: int
  last_page: int
  printed_total_kg: Decimal | None
  computed_kg: Decimal
  diff_kg: Decimal | None
  row_count: int
  dia_totals: dict

class BbsRowOut(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  sheet_id: UUID
  row_no: int
  page: int
  y: Decimal | None
  member: str | None
  sr: int | None
  description: str
  dia: int | None
  spacing_in: Decimal | None
  members: Decimal | None
  each: Decimal | None
  total: Decimal | None
  cut_ft: Decimal | None
  total_ft: Decimal | None
  unit_kg_ft: Decimal | None
  total_kg: Decimal | None
  parts: list
  notes: list
  issues: list

class BbsDetailResponse(BaseModel):
  document: BbsDocumentOut
  sheets: list[BbsSheetOut]
  rows: list[BbsRowOut]
  row_total: int
  page: int
  page_size: int
  page_counters: list
  unread_lines: list
  dropped_repeats: list

class AuditRunOut(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  document_id: UUID
  level: str
  engine_digest: str
  rules_digest: str
  decisions_digest: str
  previous_document_id: UUID | None
  totals: dict
  diff: dict
  created_at: datetime

class FindingOut(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  run_id: UUID
  code: str
  finding_class: str
  rule: str
  bbs_ref: dict
  drawing_ref: dict | None
  effect_basis: str | None
  convention: dict | None
  bbs_value: str | None
  trace_value: str | None
  diff_kg: Decimal | None
  diff_pct: Decimal | None
  confidence: Decimal
  question: str | None
  status: str
  reason: str | None
  decided_by_user_id: UUID | None
  decided_at: datetime | None

class FindingListResponse(BaseModel):
  run_id: UUID | None
  total: int
  page: int
  page_size: int
  items: list[FindingOut]
  counts_by_class: dict
  counts_by_status: dict

class FindingDecisionRequest(BaseModel):
  status: Literal["OPEN", "ACCEPTED", "REJECTED"]
  reason: str = Field(min_length=1, max_length=2000)
