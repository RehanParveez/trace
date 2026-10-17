from __future__ import annotations
from uuid import UUID
from pydantic import BaseModel, Field

class CrossCheck(BaseModel):
  code: str
  status: str = Field(description="WARN (two readings disagree), INFO (a floor was only half read), PASS (they agree).")
  floor: str | None = None
  message: str
  pages: list[int] = Field(default_factory=list)
  numbers: dict = Field(default_factory=dict)

class CrossChecksResponse(BaseModel):
  drawing_id: UUID
  checks: list[CrossCheck]
  warnings: int = 0
  info: int = 0
  passed: int = 0


class ReadyItem(BaseModel):
  id: str
  category: str
  tag: str | None = None
  floor: str | None = None
  page_no: int
  grade: str | None = None

class HeldReason(BaseModel):
  code: str
  message: str

class HeldItem(ReadyItem):
  reasons: list[HeldReason] = Field(default_factory=list)

class ReadyToAcceptResponse(BaseModel):
  drawing_id: UUID
  ready: list[ReadyItem]
  held: list[HeldItem]
  held_by_reason: dict[str, int] = Field(default_factory=dict)
  checks_warning: int = 0