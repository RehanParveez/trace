from __future__ import annotations
from pydantic import BaseModel, Field, model_validator
from uuid import UUID

class FloorSource(BaseModel):
  sheet_id: UUID
  page_no: int
  from_plans: bool = Field(description="The floor was read from one plan among the plans of a sheet that holds every plan.")
  caption: str | None = None
  wall_m: float = 0.0
  walls: int = 0
  items: int = 0
  open: int = 0
  accepted: int = 0
  rejected: int = 0
  combined: int = Field(default=0, description="Items of this sheet set aside because the floor's other sheet holds the same item.")
  added: int = Field(default=0, description="Items of this sheet that the floor's other sheet does not show, kept so the floor is complete.")
  added_wall_m: float = Field(default=0.0, description="Length of the walls among the added items. Beams, plaster, termite treatment and the other items worked out from the walls follow the floor's own sheet and do not include these walls.")
  set_aside: bool = False

class FloorEntry(BaseModel):
  floor: str
  state: str = Field(description="SINGLE (one source), LISTED (several, none of them a sheet of many plans), DOUBLE (two sources are open), COMBINED (two sources are open and the items they share were merged), CHOSEN (one source is in use), NONE (nothing is open).")
  choosable: bool
  chosen_sheet_id: UUID | None = None
  suggested_sheet_id: UUID | None = None
  conflict: bool = Field(default=False, description="Two sources both have accepted items: neither can be set aside until measurements are deleted.")
  sources: list[FloorSource]

class FloorSourcesResponse(BaseModel):
  drawing_id: UUID
  floors: list[FloorEntry]
  to_decide: int = 0

class FloorChoice(BaseModel):
  floor: str = Field(min_length=1, max_length=20)
  sheet_id: UUID

class ChooseFloorSourcesRequest(BaseModel):
  choices: list[FloorChoice] | None = Field(default=None, max_length=20)
  use_suggested: bool = Field(default=False, description="Choose the suggested source for every floor that is open on two sources.")

  @model_validator(mode="after")
  def _one_way(self):
    if bool(self.choices) == bool(self.use_suggested):
      raise ValueError("Give the choices, or ask for the suggested ones, not both and not neither.")
    return self

class ChooseFloorSourcesResponse(BaseModel):
  chosen: list[dict] = Field(default_factory=list)
  set_aside: int = 0
  restored: int = 0
  blocked: list[dict] = Field(default_factory=list)
  floors: FloorSourcesResponse
