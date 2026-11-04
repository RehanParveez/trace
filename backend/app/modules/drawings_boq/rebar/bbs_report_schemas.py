from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
from decimal import Decimal
from uuid import UUID
from app.modules.drawings_boq.rebar.bbs_schemas import FindingOut

class ReportSheetOut(BaseModel):
  idx: int
  name: str
  first_page: int
  last_page: int
  row_count: int
  printed_total_kg: Decimal | None
  computed_kg: Decimal
  printed_diff_kg: Decimal | None
  effect_kg: Decimal
  expected_kg: Decimal
  findings: int
  open_findings: int

class ReportUnassignedOut(BaseModel):
  findings: int
  effect_kg: Decimal

class ReportSummaryOut(BaseModel):
  document_id: UUID
  version: int
  file_name: str | None
  has_run: bool
  run_id: UUID | None
  level: str | None
  run_created_at: datetime | None
  bbs_total_kg: Decimal
  expected_total_kg: Decimal
  diff_kg: Decimal
  diff_pct: Decimal | None
  printed_total_kg: Decimal
  effect_by_class: dict[str, Decimal]
  effect_by_basis: dict[str, Decimal]
  excluded_kg: dict[str, Decimal]
  counts_by_class: dict[str, int]
  counts_by_status: dict[str, int]
  finding_count: int
  open_questions: int
  sheets: list[ReportSheetOut]
  unassigned: ReportUnassignedOut
  note: str

class ReportFindingOut(FindingOut):
  no: int

class ReportFindingListOut(BaseModel):
  run_id: UUID | None
  total: int
  page: int
  page_size: int
  items: list[ReportFindingOut]
  counts_by_class: dict[str, int]
  counts_by_status: dict[str, int]

class QuestionOut(BaseModel):
  no: int
  finding_id: UUID
  finding_no: int
  code: str
  finding_class: str
  where: str
  member: str | None
  question: str
  text: str

class QuestionListOut(BaseModel):
  items: list[QuestionOut]
  text: str

class CropOut(BaseModel):
  png_base64: str | None
  reason: str | None
  message: str | None
  text: str

class CropsOut(BaseModel):
  finding_id: UUID
  bbs: CropOut
  drawing: CropOut

class SignRequest(BaseModel):
  reason: str = Field(min_length=1, max_length=2000)
