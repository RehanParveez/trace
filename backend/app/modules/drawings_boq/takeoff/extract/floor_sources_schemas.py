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
  floor_basis: str | None = Field(default=None, description="How the sheet's floor was found: TITLE (written on the sheet, also read by the character reader), VIEW (the captions of its plans), ORDER (a guess from the rooms it shares with named sheets and from the order of the pages), PERSON.")
  floor_guess: str | None = Field(default=None, description="For ORDER: SHARES_ROOM_SIZES, PORCH_OR_LAWN_LABELS, MUMTY_OR_STAIR_TOWER_LABELS or PAGE_ORDER.")
  drawing_id: UUID | None = Field(default=None, description="The PDF the sheet is in. Plans of one floor can come from several PDFs of the project.")
  drawing_name: str | None = None
  plan_kind: str | None = Field(default=None, description="WORKING, FURNITURE, OVERLAY, FRAMING or FOUNDATION (null when the kind is not known). OVERLAY, FRAMING and FOUNDATION plans take no part in the choice of the floor's base plan.")
  dims: int = Field(default=0, description="Dimension strings read on the sheet; of two working drawings, the one with more is the base plan.")
  base: bool = Field(default=False, description="This is the floor's base plan: the one whose items are kept when the floor is shown by several plans.")

class FloorEntry(BaseModel):
  floor: str
  state: str = Field(description="SINGLE (one source), LISTED (several, none of them a sheet of many plans), DOUBLE (two sources are open), COMBINED (two sources are open and the items they share were merged), CHOSEN (one source is in use), NONE (nothing is open).")
  choosable: bool
  chosen_sheet_id: UUID | None = None
  suggested_sheet_id: UUID | None = None
  base_sheet_id: UUID | None = Field(default=None, description="The base plan of a floor shown by several plans (null when the floor has one plan or the plans are not alternatives).")
  base_reason: str | None = None
  conflict: bool = Field(default=False, description="Two sources both have accepted items: neither can be set aside until measurements are deleted.")
  sources: list[FloorSource]
  notes: list[dict] = Field(default_factory=list, description="FLOOR_FROM_SHEET_ORDER when a source's floor is a guess.")

class FloorSourcesResponse(BaseModel):
  drawing_id: UUID
  project_wide: bool = Field(default=False, description="The floors were gathered from every current PDF of the project, not from this drawing alone.")
  drawings: int = 1
  project_wide: bool = Field(default=False, description="The floors were gathered from every current PDF of the project, not from this drawing alone.")
  drawings: int = 1
  floors: list[FloorEntry]
  to_decide: int = 0
  ordered: list[dict] = Field(default_factory=list, description="Every sheet whose floor was guessed (floor_basis ORDER): sheet_id, page_no, floor, reason, pages.")

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
 