from __future__ import annotations
from pydantic import BaseModel, Field
from uuid import UUID

class StampRequest(BaseModel):
  include_confirmed: bool = Field(default=False, description="Also give the grade to confirmed measurements. They go back to draft, as for any other change to a material field.")

class GradesResponse(BaseModel):
  drawing_id: UUID
  concrete: list[dict] = Field(default_factory=list)
  steel: list[dict] = Field(default_factory=list)
  members: list[dict] = Field(default_factory=list)
  plaster: dict = Field(default_factory=dict)
  soil: dict | None = None
  conflicts: list[dict] = Field(default_factory=list)
  summary: dict = Field(default_factory=dict)
  changed: int = 0
