from __future__ import annotations
from pydantic import BaseModel, Field
from uuid import UUID

class ChooseMarkRequest(BaseModel):
  candidate_id: UUID = Field(description="The unmarked shapes item (a column row with no mark).")
  mark: str = Field(min_length=1, max_length=60, description="One of the marks the item offers.")

class ChooseDepthRequest(BaseModel):
  mark: str = Field(min_length=1, max_length=60)
  depth_mm: float = Field(gt=0, le=3000, description="One of the depths offered for the mark.")

class DecisionItem(BaseModel):
  id: UUID
  kind: str
  mark: str
  sheet_id: UUID | None = None
  page_no: int | None = None
  ckey: str | None = None
  value_mm: float | None = None
  applied: bool = False
  decided_by_user_id: UUID | None = None

class DetailOnlyResponse(BaseModel):
  drawing_id: UUID
  columns: list[dict] = Field(default_factory=list)
  beams: list[dict] = Field(default_factory=list)
  depth_gaps: list[dict] = Field(default_factory=list)
  decisions: list[DecisionItem] = Field(default_factory=list)
  summary: dict = Field(default_factory=dict)
