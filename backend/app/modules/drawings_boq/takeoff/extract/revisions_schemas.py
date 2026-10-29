from __future__ import annotations
from pydantic import BaseModel, Field, model_validator
from uuid import UUID

class RevisionSample(BaseModel):
  id: str
  label: str | None = None
  geometry: dict | list | None = None

class RevisionOption(BaseModel):
  value: str
  label: str
  text: str
  pages: list[int]
  sheet_ids: list[UUID]
  items: int = 0
  open: int = 0
  accepted: int = 0
  set_aside: bool = False
  live: int = Field(default=0, description="Items open or accepted: what is measured while this value is in force.")
  sample: RevisionSample | None = Field(default=None, description="One item of the sheet, for a picture of it.")

class RevisionGroup(BaseModel):
  id: str
  kind: str = Field(description="OPTION (the set prints alternatives: which was built) or REVISION (one sheet printed more than once: which is current).")
  caption: str
  floor: str | None = None
  sheet_no: str | None = None
  question: str
  state: str = Field(description="OPEN (two or more values are still measured), CHOSEN (one is), NONE (none is).")
  default: str | None = Field(default=None, description="The later revision; an option has no default.")
  chosen: str | None = None
  choosable: bool = True
  options: list[RevisionOption]

class RevisionsResponse(BaseModel):
  drawing_id: UUID
  groups: list[RevisionGroup]
  to_decide: int = 0
  tolerance: dict[str, str] = Field(default_factory=dict)

class RevisionChoice(BaseModel):
  id: str = Field(min_length=1, max_length=20)
  value: str = Field(min_length=1, max_length=80)

class ChooseRevisionsRequest(BaseModel):
  choices: list[RevisionChoice] | None = Field(default=None, max_length=50)
  use_default: bool = Field(default=False, description="Take the later revision of every revision group that is open on two or more sheets. Options have no default.")

  @model_validator(mode="after")
  def _one_way(self):
    if bool(self.choices) == bool(self.use_default):
      raise ValueError("Give the choices, or ask for the default, not both and not neither.")
    return self

class ChooseRevisionsResponse(BaseModel):
  chosen: list[dict] = Field(default_factory=list)
  set_aside: int = 0
  restored: int = 0
  blocked: list[dict] = Field(default_factory=list)
  revisions: RevisionsResponse
