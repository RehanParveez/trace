from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from datetime import date, datetime
from uuid import UUID

class SiteLogCreateRequest(BaseModel):
  project_id: UUID
  log_date: date
  workforce_count: int | None = Field(default=None, ge=0)
  weather: str | None = Field(default=None, max_length=255)
  blockers: str | None = None
  notes: str | None = None

class SiteLogUpdateRequest(BaseModel):
  log_date: date | None = None
  workforce_count: int | None = Field(default=None, ge=0)
  weather: str | None = Field(default=None, max_length=255)
  blockers: str | None = None
  notes: str | None = None

class SiteLogResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  project_id: UUID
  log_date: date
  workforce_count: int | None
  weather: str | None
  blockers: str | None
  notes: str | None
  created_by: UUID | None
  created_at: datetime
  updated_at: datetime