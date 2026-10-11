from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from datetime import date, datetime
from uuid import UUID
from decimal import Decimal

class SiteLogCreateRequest(BaseModel):
  project_id: UUID
  log_date: date
  workforce_count: int | None = Field(default=None, ge=0)
  weather: str | None = Field(default=None, max_length=255)
  work_done: str | None = None
  blockers: str | None = None
  client_instructions: str | None = None
  notes: str | None = None

class SiteLogUpdateRequest(BaseModel):
  log_date: date | None = None
  workforce_count: int | None = Field(default=None, ge=0)
  weather: str | None = Field(default=None, max_length=255)
  work_done: str | None = None
  blockers: str | None = None
  client_instructions: str | None = None
  notes: str | None = None

class SiteLogResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  project_id: UUID
  log_date: date
  workforce_count: int | None
  weather: str | None
  work_done: str | None = None
  blockers: str | None
  client_instructions: str | None = None
  notes: str | None
  created_by: UUID | None
  created_at: datetime
  updated_at: datetime

class DailyReportManpowerRow(BaseModel):
  trade: str
  units: Decimal

class DailyReportDeliveryRow(BaseModel):
  material_name: str
  unit: str
  quantity: Decimal
  supplier_name: str | None
  invoice_number: str | None

class DailyReportIssueRow(BaseModel):
  material_name: str
  unit: str
  quantity: Decimal
  issue_type: str
  issued_to: str | None

class DailyReportPhoto(BaseModel):
  photo_id: UUID
  photo_url: str
  location_text: str | None
  caption: str | None

class DailyReportResponse(BaseModel):
  project_id: UUID
  project_name: str
  report_date: date
  logs: list[SiteLogResponse]
  weather: str | None
  work_done: list[str]
  blockers: list[str]
  client_instructions: list[str]
  notes: list[str]
  manpower_total: Decimal
  manpower: list[DailyReportManpowerRow]
  reported_workforce: int | None
  manpower_mismatch: bool
  deliveries: list[DailyReportDeliveryRow]
  issues: list[DailyReportIssueRow]
  photos: list[DailyReportPhoto]
  photo_count: int