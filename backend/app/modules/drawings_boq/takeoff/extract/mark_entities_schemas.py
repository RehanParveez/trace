from __future__ import annotations
from pydantic import BaseModel, Field, model_validator
from uuid import UUID

class MarkSource(BaseModel):
  sheet_id: UUID
  page_no: int
  caption: str | None = None
  floor: str | None = Field(default=None, description="The floor the sheet's title names, when it names one.")
  advice: str | None = None
  count: int = Field(default=0, description="How many of the mark this sheet shows (open and accepted items).")
  shapes: list[list[int]] = Field(default_factory=list, description="The sizes this sheet prints for the mark, length, width and depth in whole inches (the ones it prints).")
  basis: str | None = Field(default=None, description="Where the sheet's size came from: SCHEDULE, DETAIL or PLAN.")
  open: int = 0
  accepted: int = 0
  set_aside: int = 0

class MarkEntity(BaseModel):
  key: str
  category: str
  mark: str = Field(description="The mark without spaces or dashes, capitals only.")
  tag: str | None = Field(default=None, description="The mark as it is printed.")
  floor: str | None = None
  state: str = Field(description="DOUBLE (two or more sheets show the same count and size), DIFFER (they show different counts or sizes), UNPLACED (the sheets do not name a floor), CHOSEN (one sheet is in use).")
  agree: bool = True
  live_sheets: int = 0
  suggested_sheet_id: UUID | None = None
  chosen_sheet_id: UUID | None = None
  conflict: bool = Field(default=False, description="Two sheets both have accepted items: neither can be set aside until measurements are deleted.")
  choosable: bool = True
  sources: list[MarkSource]

class MarkEntitiesResponse(BaseModel):
  drawing_id: UUID
  entities: list[MarkEntity]
  to_decide: int = 0
  differ: int = 0
  unplaced: int = 0
  single: int = 0

class MarkChoice(BaseModel):
  key: str = Field(min_length=1, max_length=120)
  sheet_id: UUID

class ChooseMarksRequest(BaseModel):
  choices: list[MarkChoice] | None = Field(default=None, max_length=200)
  use_suggested: bool = Field(default=False, description="Choose the suggested sheet for every mark whose sheets agree. Marks whose sheets differ are left to you.")

  @model_validator(mode="after")
  def _one_way(self):
    if bool(self.choices) == bool(self.use_suggested):
      raise ValueError("Give the choices, or ask for the suggested ones, not both and not neither.")
    return self

class ChooseMarksResponse(BaseModel):
  chosen: list[dict] = Field(default_factory=list)
  set_aside: int = 0
  restored: int = 0
  blocked: list[dict] = Field(default_factory=list)
  marks: MarkEntitiesResponse
