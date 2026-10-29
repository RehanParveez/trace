from __future__ import annotations
from pydantic import BaseModel, Field
from uuid import UUID
from app.modules.drawings_boq.takeoff.extract.revisions_schemas import RevisionGroup

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

class FactDecisionSource(BaseModel):
  discipline: str
  page_no: int | None = None
  basis: str

class FactDecisionOption(BaseModel):
  value: str
  label: str | None = None
  trust: str | None = None
  default: bool = False
  quantity: float | None = None
  unit: str | None = None
  sources: list[FactDecisionSource] = Field(default_factory=list)

class FactDecisionItem(BaseModel):
  id: str
  kind: str
  title: str
  question: str
  affects: str
  tolerance: float
  unit: str
  facts: list[str]
  rows: int
  default: str | None = Field(default=None, description="The value from the most trusted source; None when two values tie.")
  chosen: str | None = None
  open: bool = True
  options: list[FactDecisionOption]

class DecisionsResponse(BaseModel):
  drawing_id: UUID
  items: list[DecisionItem]
  sheets: list[RevisionGroup] = Field(default_factory=list, description="Options the set prints (which was built) and sheets printed with more than one revision (which is current), one decision each, with the sheets of each value.")
  facts: list[FactDecisionItem] = Field(default_factory=list, description="Printed facts the sheets read differently, one decision each, with the sources and the rows they affect.")
  stale_pages: list[int] = Field(default_factory=list)
  sheets_read: int = 0

class ChooseDecisionRequest(BaseModel):
  key: str = Field(default="", description="A decision of the catalog; empty when decision_id names a fact decision.")
  decision_id: str | None = Field(default=None, description="A fact decision (from facts): value is then the option's value.")
  value: str | None = Field(default=None, description="The option chosen; null goes back to the default.")
