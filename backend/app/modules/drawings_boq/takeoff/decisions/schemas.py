from __future__ import annotations
from pydantic import BaseModel, Field
from uuid import UUID

class DecisionFigure(BaseModel):
  key: str
  value: float
  unit: str

class DecisionEffect(BaseModel):
  figures: list[DecisionFigure] = Field(default_factory=list)
  diff: float | None = Field(default=None, description="The change against the option in force, in diff_unit; None when it cannot be worked out from what is stored.")
  diff_unit: str = "m3"
  diffs: list[DecisionFigure] = Field(default_factory=list, description="Every change against the option in force, one per quantity, when a choice changes more than one.")

class DecisionOption(BaseModel):
  value: str
  label: str
  text: str
  is_default: bool
  in_force: bool
  effect: DecisionEffect | None = None

class DecisionItem(BaseModel):
  key: str
  rule: str = Field(description="The registry item that proposes the default (P43-1, P44-1).")
  kind: str
  title: str
  question: str
  affects: str
  default: str
  current: str
  made_by_person: bool
  made_at: str | None = None
  applies: bool = Field(description="False when nothing read from this drawing depends on the choice.")
  walls: int = 0
  floors: list[str] = Field(default_factory=list)
  options: list[DecisionOption]
  stale_pages: list[int] = Field(default_factory=list, description="Pages read before the choice in force; they are read again to apply it.")
  accepted_stale: int = Field(default=0, description="Items already accepted from those pages; they keep the value they were accepted with.")

class DecisionsResponse(BaseModel):
  drawing_id: UUID
  items: list[DecisionItem]
  stale_pages: list[int] = Field(default_factory=list)
  sheets_read: int = 0

class ChooseDecisionRequest(BaseModel):
  key: str
  value: str | None = Field(default=None, description="The option chosen; null goes back to the default.")
