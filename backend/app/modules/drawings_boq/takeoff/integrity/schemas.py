from __future__ import annotations
from pydantic import BaseModel, Field
from uuid import UUID

class IntegrityCheck(BaseModel):
  code: str
  status: str = Field(description="OK, WARN or INFO.")
  title: str
  message: str
  pages: list[int] = Field(default_factory=list)
  count: int = 0

class IntegrityResponse(BaseModel):
  drawing_id: UUID
  status: str = Field(description="OK, PARTIAL (only information) or LOOK (something to look at).")
  code_version: int
  checks: list[IntegrityCheck] = Field(default_factory=list)
  summary: dict = Field(default_factory=dict)