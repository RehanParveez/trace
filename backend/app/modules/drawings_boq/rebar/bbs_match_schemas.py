from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from uuid import UUID

class MatchRunOut(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  document_id: UUID
  floor_map: dict
  floor_map_proposed: dict
  floor_map_confirmed: bool
  member_count: int
  stats: dict
  created_at: datetime

class MatchItemOut(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  row_id: UUID | None
  kind: str
  family: str | None
  sheet_name: str | None
  member: str | None
  floors: list
  method: str | None
  confidence: float
  basis: str | None
  reason: str | None
  elements: list

class AskGroupOut(BaseModel):
  group: str
  sheet: str | None
  member: str | None
  family: str | None
  rows: int
  reason: str | None

class MatchItemList(BaseModel):
  run_id: UUID | None
  total: int
  page: int
  page_size: int
  items: list[MatchItemOut]
  asks: list[AskGroupOut]
  counts_by_kind: dict

class DecisionsOut(BaseModel):
  decisions: dict

class FloorMapRequest(BaseModel):
  value: dict[str, list[str]]

class ConfirmElement(BaseModel):
  pdf_key: str | None = None
  sheet: int | None = None
  class_: str = Field(alias="class", min_length=1, max_length=20)
  mark: str | None = Field(default=None, max_length=60)
  floor: str | None = Field(default=None, max_length=12)

  model_config = ConfigDict(populate_by_name=True)

class ConfirmRequest(BaseModel):
  group: str = Field(min_length=1, max_length=620)
  elements: list[ConfirmElement] = Field(default_factory=list, max_length=20)
  note: str | None = Field(default=None, max_length=500)
