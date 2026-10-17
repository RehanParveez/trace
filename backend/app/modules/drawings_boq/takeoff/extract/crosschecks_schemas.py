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