from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal

ImportStatus = Literal["UPLOADED", "PARSING", "REVIEW", "PUBLISHED", "FAILED", "CANCELLED"]
RowFilter = Literal["all", "review", "unmapped", "mapped", "skipped", "sample", "flagged"]

class RateImportResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  status: ImportStatus
  source_kind: Literal["PDF", "CSV"]
  filename: str
  file_size: int
  content_hash: str
  layout_profile: str
  first_page: int
  last_page: int | None
  book_code: str | None
  book_name: str | None
  edition: str | None
  jurisdiction: str | None
  province: str | None
  city: str | None
  currency: str
  effective_from: date | None
  effective_to: date | None
  page_count: int | None
  row_count: int
  report: dict | None
  error_message: str | None
  parsed_at: datetime | None
  rate_book_id: UUID | None
  published_at: datetime | None
  created_at: datetime
  duplicate_of_id: UUID | None = None
  counts: dict = Field(default_factory=dict)

class ImportRowResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  seq: int
  page: int | None
  line_no: int | None
  chapter: str | None
  item_no: str | None
  description: str
  raw_line: str | None
  unit_raw: str | None
  basis_qty: Decimal
  unit: str | None
  unit_known: bool
  rate_raw: str | None
  rate: Decimal | None
  rate_alt: Decimal | None
  unit_rate: Decimal | None
  spec_key: str | None = None
  labour: Decimal | None = None
  rate_kind: str | None = None
  flags: list[str]
  needs_review: bool
  reviewed: bool
  skipped: bool
  edited: bool
  original: dict | None
  note: str | None
  work_item_code: str | None
  mapping_source: str | None
  suggestions: list[dict]
  is_sample: bool
  sample_verified: bool

class RowUpdateRequest(BaseModel):
  description: str | None = Field(default=None, max_length=4000)
  item_no: str | None = Field(default=None, max_length=60)
  chapter: str | None = Field(default=None, max_length=200)
  unit: str | None = Field(default=None, max_length=60)
  basis_qty: Decimal | None = Field(default=None, gt=0, le=100000)
  rate: Decimal | None = Field(default=None, ge=0, le=Decimal("999999999999"))
  work_item_code: str | None = Field(default=None, max_length=50)
  clear_mapping: bool = False
  spec_key: str | None = Field(default=None, max_length=80)
  reviewed: bool | None = None
  skipped: bool | None = None
  sample_verified: bool | None = None
  note: str | None = Field(default=None, max_length=1000)

  @field_validator("work_item_code")
  @classmethod
  def _code(cls, v: str | None) -> str | None:
    if v is None:
      return None
    v = v.strip().upper()
    if not v:
      raise ValueError("work_item_code is empty")
    return v

class BulkRowsRequest(BaseModel):
  action: Literal["confirm", "skip", "unskip", "map", "clear_mapping", "accept_suggestions"]
  row_ids: list[UUID] | None = Field(default=None, max_length=2000)
  filter: RowFilter | None = None
  chapter: str | None = None
  q: str | None = Field(default=None, max_length=100)
  work_item_code: str | None = Field(default=None, max_length=50)
  min_score: float = Field(default=0.9, ge=0.5, le=1.0)

  @model_validator(mode="after")
  def _need_target(self):
    if self.action == "map" and not self.work_item_code:
      raise ValueError("work_item_code is required to map rows")
    if self.action != "accept_suggestions" and not self.row_ids and not self.filter and not self.chapter and not self.q:
      raise ValueError("choose rows by id or by filter")
    return self

class BulkRowsResponse(BaseModel):
  changed: int
  skipped: int = 0

class ReparseRequest(BaseModel):
  layout_profile: str | None = Field(default=None, max_length=40)
  first_page: int | None = Field(default=None, ge=1)
  last_page: int | None = Field(default=None, ge=1)

class PublishRequest(BaseModel):
  """Where the rates go: a new draft book, or an existing draft of yours (rates with the same work item and unit are updated)."""
  existing_book_id: UUID | None = None
  code: str | None = Field(default=None, min_length=1, max_length=50)
  name: str | None = Field(default=None, min_length=1, max_length=200)
  edition: str | None = Field(default=None, max_length=50)
  jurisdiction: str | None = Field(default=None, max_length=50)
  province: str | None = Field(default=None, max_length=50)
  city: str | None = Field(default=None, max_length=100)
  effective_from: date | None = None
  effective_to: date | None = None
  include_unmapped: bool = False

  @field_validator("code")
  @classmethod
  def _code(cls, v: str | None) -> str | None:
    return v.strip().upper() if v else v

class ReadinessResponse(BaseModel):
  can_publish: bool
  blockers: list[dict]
  warnings: list[dict]
  counts: dict

class PublishResponse(BaseModel):
  rate_book_id: UUID
  created: int
  updated: int
  left_out: int
  unit_changes: list[dict]
  spec_notes: list[dict] = Field(default_factory=list)

class SuggestResponse(BaseModel):
  rows_with_suggestions: int
  rows_without: int
  catalog_size: int

class ImportUpdateRequest(BaseModel):
  book_code: str | None = Field(default=None, min_length=1, max_length=50)
  book_name: str | None = Field(default=None, min_length=1, max_length=200)
  edition: str | None = Field(default=None, max_length=50)
  jurisdiction: str | None = Field(default=None, max_length=50)
  province: str | None = Field(default=None, max_length=50)
  city: str | None = Field(default=None, max_length=100)
  effective_from: date | None = None
  effective_to: date | None = None
