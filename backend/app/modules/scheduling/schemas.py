from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from datetime import date
from decimal import Decimal
from uuid import UUID

class ScheduleTaskCreateRequest(BaseModel):
  name: str = Field(min_length=1, max_length=300)
  description: str | None = None
  planned_start_date: date | None = None
  planned_duration_days: int = Field(default=1, ge=0)
  is_milestone_marker: bool = False
  predecessor_task_ids: list[UUID] = Field(default_factory=list)

class ScheduleTaskUpdateRequest(BaseModel):
  name: str | None = Field(default=None, min_length=1, max_length=300)
  description: str | None = None
  planned_start_date: date | None = None
  planned_duration_days: int | None = Field(default=None, ge=0)
  actual_start_date: date | None = None
  actual_end_date: date | None = None
  percent_complete: Decimal | None = Field(default=None, ge=0, le=100)
  is_milestone_marker: bool | None = None

class ScheduleDependencyCreateRequest(BaseModel):
  predecessor_task_id: UUID

class ProjectScheduleSettingsUpdateRequest(BaseModel):
  target_completion_date: date | None = None

class ScheduleTaskResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  name: str
  description: str | None
  planned_start_date: date | None
  planned_duration_days: int
  is_milestone_marker: bool
  actual_start_date: date | None
  actual_end_date: date | None
  percent_complete: Decimal
  status: str
  sort_order: int

class ScheduleTaskComputedResponse(ScheduleTaskResponse):
  predecessor_task_ids: list[UUID]
  is_computable: bool
  earliest_start: date | None
  earliest_finish: date | None
  latest_start: date | None
  latest_finish: date | None
  total_float_days: int | None
  is_critical: bool

class ProjectScheduleResponse(BaseModel):
  project_id: UUID
  target_completion_date: date | None
  natural_completion_date: date | None
  days_ahead_or_behind_target: int | None
  warnings: list[str]
  tasks: list[ScheduleTaskComputedResponse]