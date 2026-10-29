from __future__ import annotations
from pydantic import BaseModel, Field
from uuid import UUID

class MemberSightingOut(BaseModel):
  drawing_id: str = ""
  page_no: int
  sheet_id: UUID | None = None
  candidate_key: str = ""
  basis: str = Field(default="PLAN", description="Where the size of this sighting came from: SCHEDULE, DETAIL or PLAN.")

class MemberOut(BaseModel):
  id: str
  kind: str = Field(description="COLUMN, FOOTING or BEAM.")
  mark: str | None = None
  floor: str | None = None
  size_mm: list[float] | None = Field(default=None, description="Length and width of a column; length, width and depth of a footing; width and depth of a beam: those of the best sighting (a schedule, then a detail, then the plan).")
  height_mm: float | None = Field(default=None, description="The floor-to-floor height of the floor the member stands on, from the levels of the building model.")
  positioned: bool = Field(default=False, description="Whether the member has a place in the plan (a footing or column seen only by its mark has none).")
  sightings: list[MemberSightingOut]

class MemberDecisionOut(BaseModel):
  id: str
  question: str
  options: list[dict] = Field(default_factory=list)
  chosen: object | None = None
  open: bool = True

class MembersResponse(BaseModel):
  drawing_id: UUID
  project_wide: bool = False
  members: list[MemberOut]
  decisions: list[MemberDecisionOut] = Field(default_factory=list)
  summary: dict = Field(default_factory=dict)
