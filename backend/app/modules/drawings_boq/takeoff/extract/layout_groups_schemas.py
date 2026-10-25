from __future__ import annotations
from pydantic import BaseModel, Field, model_validator
from uuid import UUID

class LayoutSource(BaseModel):
  sheet_id: UUID
  page_no: int
  caption: str | None = None
  floor: str | None = Field(default=None, description="The floor the sheet's title names, when it names one.")
  advice: str | None = None
  role: str | None = None
  rooms: int = 0
  room_area_m2: float = 0.0
  wall_m: float = 0.0
  items: int = 0
  open: int = 0
  accepted: int = 0
  rejected: int = 0
  set_aside: bool = False

class LayoutGroup(BaseModel):
  key: str
  kind: str = Field(description="SAME (the same named rooms with the same areas on several sheets) or NEAR (the same room names and nearly the same total area; shown, never held).")
  state: str = Field(description="DOUBLE (two or more of the sheets are open), CHOSEN (one sheet is in use), NONE (nothing is open), NEAR.")
  floor: str | None = None
  rooms: int = 0
  room_area_m2: float = 0.0
  chosen_sheet_id: UUID | None = None
  suggested_sheet_id: UUID | None = None
  conflict: bool = Field(default=False, description="Two sheets both have accepted items: neither can be set aside until measurements are deleted.")
  choosable: bool = False
  counted_twice_m2: float = Field(default=0.0, description="Room area that would be counted again if the open sheets of this group were all accepted.")
  sources: list[LayoutSource]

class LayoutGroupsResponse(BaseModel):
  drawing_id: UUID
  groups: list[LayoutGroup]
  to_decide: int = 0
  repeated_room_area_m2: float = 0.0

class LayoutChoice(BaseModel):
  key: str = Field(min_length=1, max_length=20)
  sheet_id: UUID

class ChooseLayoutsRequest(BaseModel):
  choices: list[LayoutChoice] | None = Field(default=None, max_length=50)
  use_suggested: bool = Field(default=False, description="Choose the suggested sheet for every group that is open on two or more sheets.")

  @model_validator(mode="after")
  def _one_way(self):
    if bool(self.choices) == bool(self.use_suggested):
      raise ValueError("Give the choices, or ask for the suggested ones, not both and not neither.")
    return self

class ChooseLayoutsResponse(BaseModel):
  chosen: list[dict] = Field(default_factory=list)
  set_aside: int = 0
  restored: int = 0
  blocked: list[dict] = Field(default_factory=list)
  layouts: LayoutGroupsResponse
