from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import Any

class ExpectRunOut(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  document_id: UUID
  decisions: dict
  decisions_digest: str
  member_count: int
  complete_count: int
  stats: dict
  created_at: datetime

class ExpectationOut(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  member_class: str
  mark: str
  floor: str | None
  count: float | None
  total_ft: float | None
  kg: float | None
  complete: bool
  plan_count: int | None
  source_page: int | None
  decision_only: bool
  lines: list
  inputs: list
  blocked: list
  notes: list

class ExpectationList(BaseModel):
  run_id: UUID | None
  total: int
  page: int
  page_size: int
  items: list[ExpectationOut]
  counts_by_class: dict

class DecisionValue(BaseModel):
  value: Any = None
