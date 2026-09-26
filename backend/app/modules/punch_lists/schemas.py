from __future__ import annotations
from uuid import UUID
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.modules.punch_lists.models import PunchListPhotoPurpose, PunchListItemStatus, PunchListStatus

class PunchListCreateRequest(BaseModel):
  project_id: UUID
  title: str = Field(min_length=1, max_length=300)
  inspection_date: date
  notes: str | None = None

class PunchListItemCreateRequest(BaseModel):
  location: str = Field(min_length=1, max_length=200)
  description: str = Field(min_length=1)
  assigned_to_user_id: UUID | None = None
  assigned_to_subcontractor_id: UUID | None = None
  due_date: date | None = None

  @model_validator(mode="after")
  def _validate_single_assignee(self) -> "PunchListItemCreateRequest":
    if self.assigned_to_user_id is not None and self.assigned_to_subcontractor_id is not None:
      raise ValueError("Assign an item to either a team member or a subcontractor, not both.")
    return self

class PunchListItemUpdateRequest(BaseModel):
  location: str | None = Field(default=None, min_length=1, max_length=200)
  description: str | None = None
  assigned_to_user_id: UUID | None = None
  assigned_to_subcontractor_id: UUID | None = None
  status: PunchListItemStatus | None = None
  due_date: date | None = None
  resolution_notes: str | None = None

class PunchListItemPhotoCreateRequest(BaseModel):
  site_photo_id: UUID
  photo_purpose: PunchListPhotoPurpose

class PunchListItemPhotoResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  site_photo_id: UUID
  photo_purpose: PunchListPhotoPurpose

class PunchListItemResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  location: str
  description: str
  assigned_to_user_id: UUID | None
  assigned_to_subcontractor_id: UUID | None
  status: PunchListItemStatus
  due_date: date | None
  resolved_at: datetime | None
  resolution_notes: str | None
  photos: list[PunchListItemPhotoResponse] = Field(default_factory=list)

class PunchListResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  project_id: UUID
  title: str
  inspection_date: date
  status: PunchListStatus
  notes: str | None
  closed_at: datetime | None
  created_at: datetime

class PunchListDetailResponse(PunchListResponse):
  items: list[PunchListItemResponse] = Field(default_factory=list)

class ProjectPunchListSummaryResponse(BaseModel):
  project_id: UUID
  open_lists_count: int
  total_open_items: int
  is_project_clear: bool