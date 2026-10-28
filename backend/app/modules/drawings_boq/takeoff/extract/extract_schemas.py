from __future__ import annotations
from app.modules.drawings_boq.takeoff.schemas import SteelParam
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.modules.drawings_boq.takeoff.extract import kinds as KD
from uuid import UUID
from datetime import datetime
from decimal import Decimal

class ExtractRequest(BaseModel):
  auto_calibrate: bool = Field(default=False, description="If the sheet has no scale yet, set the recommended one, but only when the drawn scale and the printed dimensions agree.")
  budget_seconds: int = Field(default=25, ge=5, le=90)
  only_unread: bool = Field(default=False, description="Whole-drawing reads only: leave out sheets that were already read from the current prepared version of the sheet.")
  choose_floors: bool = Field(default=True, description="After the read, a floor that is open on two sheets (its own sheet and a sheet of several plans) uses the suggested sheet and the other is set aside, so the floor is not counted twice. It can be changed afterwards.")

class CandidateResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  sheet_id: UUID
  category: str
  kind: str
  quantity_mode: str
  label: str
  tag: str | None
  geometry: dict
  params: dict
  missing: list
  suggested_work_item: str | None
  count: int
  status: str
  confidence: Decimal
  facts: dict
  notes: list
  source: str
  decision: str
  measurement_id: UUID | None
  decided_at: datetime | None
  mm_per_pt: Decimal | None

class ExtractionMeta(BaseModel):
  sheet_id: UUID
  ran: bool
  ran_at: datetime | None = None
  stale: bool = False
  stale_reasons: list[str] = Field(default_factory=list)
  mm_per_pt: Decimal | None = None
  scale_unverified: bool = False
  stats: dict = Field(default_factory=dict)
  unmapped_tags: list = Field(default_factory=list)
  notes: list = Field(default_factory=list)

class CandidateListResponse(BaseModel):
  sheet_id: UUID
  extraction: ExtractionMeta
  candidates: list[CandidateResponse]
  summary: dict

class DrawingCandidatesResponse(BaseModel):
  drawing_id: UUID
  sheets: list[CandidateListResponse]

class ExtractResponse(CandidateListResponse):
  added: int = 0
  updated: int = 0
  removed: int = 0
  calibration_created: bool = False
  floors_chosen: list[dict] = Field(default_factory=list, description="The floors that were read twice and the sheet that was put in use for each by this read.")

class DrawingExtractResponse(BaseModel):
  drawing_id: UUID
  done: list[ExtractResponse]
  skipped: list[dict]

class AcceptRequest(BaseModel):
  ids: list[UUID] = Field(min_length=1, max_length=500)
  wall_height_mm: Decimal | None = Field(default=None, gt=0, le=20000)
  column_height_mm: Decimal | None = Field(default=None, gt=0, le=20000)
  footing_depth_mm: Decimal | None = Field(default=None, gt=0, le=10000)
  slab_thickness_mm: Decimal | None = Field(default=None, gt=0, le=2000)
  beam_depth_mm: Decimal | None = Field(default=None, gt=0, le=3000)
  plinth_beam_depth_mm: Decimal | None = Field(default=None, gt=0, le=3000)
  tie_band_depth_mm: Decimal | None = Field(default=None, gt=0, le=1000)
  excavation_depth_mm: Decimal | None = Field(default=None, gt=0, le=20000)
  trench_depth_mm: Decimal | None = Field(default=None, gt=0, le=10000)
  fill_depth_mm: Decimal | None = Field(default=None, gt=0, le=5000, description="Earth filling under the floor: the depth of the fill.")
  pcc_thickness_mm: Decimal | None = Field(default=None, gt=0, le=1000)
  pcc_strip_width_mm: Decimal | None = Field(default=None, gt=0, le=10000)
  pcc_strip_width_thin_mm: Decimal | None = Field(default=None, gt=0, le=10000)
  brick_step_1_height_mm: Decimal | None = Field(default=None, gt=0, le=3000)
  brick_step_2_height_mm: Decimal | None = Field(default=None, gt=0, le=3000)
  brick_step_3_height_mm: Decimal | None = Field(default=None, gt=0, le=3000)
  brick_step_4_height_mm: Decimal | None = Field(default=None, gt=0, le=3000)
  brick_step_offset_mm: Decimal | None = Field(default=None, gt=0, le=1000)
  membrane_width_mm: Decimal | None = Field(default=None, gt=0, le=3000)
  door_frame_width_mm: Decimal | None = Field(default=None, gt=0, le=1000)
  door_frame_width_thin_mm: Decimal | None = Field(default=None, gt=0, le=1000)
  tile_height_mm: Decimal | None = Field(default=None, gt=0, le=6000, description="Kitchen wall tile: the height of the tile above the floor.")
  stair_waist_mm: Decimal | None = Field(default=None, gt=0, le=500)
  neck_height_mm: Decimal | None = Field(default=None, gt=0, le=10000, description="Neck columns: top of the footing to the lowest floor.")
  tank_wall_height_mm: Decimal | None = Field(default=None, gt=0, le=10000, description="Walls of water tanks.")
  site_length_mm: Decimal | None = Field(default=None, gt=0, le=60000, description="Items outside the building (tanks, boundary wall, gate, ramp): the length, or the width of a gate.")
  site_width_mm: Decimal | None = Field(default=None, gt=0, le=60000, description="Items outside the building: the width of a tank or a ramp.")
  site_height_mm: Decimal | None = Field(default=None, gt=0, le=10000, description="Items outside the building: the height of a tank, a boundary wall or a gate.")
  site_thickness_mm: Decimal | None = Field(default=None, gt=0, le=3000, description="Items outside the building: the thickness of the walls and slabs of a tank, of a boundary wall or of a ramp slab.")
  boundary_side_mm: Decimal | None = Field(default=None, ge=0, le=60000, description="Boundary wall: the length of one side wall (the two sides are taken as equal); 0 where there is none.")
  boundary_rear_mm: Decimal | None = Field(default=None, ge=0, le=60000, description="Boundary wall: the length of the rear wall; 0 where there is none.")
  rain_pipe_length_mm: Decimal | None = Field(default=None, gt=0, le=60000, description="Rain water pipes: the length of one pipe, from the roof to the ground. Replaces the fall worked out from the levels of the building sections.")
  sewer_length_mm: Decimal | None = Field(default=None, gt=0, le=60000, description="Sewer pipe line: the total length of the line, which the sheet draws as a diagram that is not to scale.")
  work_items: dict[str, str] | None = Field(default=None, description="Work item code to use per kind of item: a category, or the name of a piece of work worked out from other readings (TERMITE_STRIP, MEMBRANE, DOOR_FRAME and the rest), e.g. {\"WALL\": \"MAS-BLOCK\", \"TERMITE_STRIP\": \"PRO-TERMITE\"}.")
  level_id: UUID | None = None
  section_picks: dict[UUID, str] | None = Field(default=None, max_length=500, description="The beam section (mark) chosen for a beam that lists several, by candidate id. Its depth and bars are put on the beam.")
  steel: dict[UUID, SteelParam] | None = Field(default=None, description="Bars, rings or mesh typed for a candidate, by candidate id. They replace the ones read from the drawing.")
  allow_repeat_marks: bool = Field(default=False, description="True accepts a column, footing, door or window mark even when the same mark of the same floor is already accepted from another sheet. Left false, the second one is refused (MARK_ACCEPTED_ELSEWHERE) so the mark is not counted twice. It also lets a stair flight through that is the second view of a stair measured on another floor (STAIR_TWIN_ABOVE), and a roof beam worked out from the walls of a floor whose framing plan draws the beams (BEAM_FROM_FRAMING_PLAN).")

  @field_validator("work_items")
  @classmethod
  def _work_item_kinds(cls, value):
    if not value:
      return None
    bad = sorted(k for k in value if k not in KD.KINDS)
    if bad:
      raise ValueError(f"Work items are chosen per kind of item; these are not kinds: {', '.join(bad[:5])}. Read the page again.")
    return {k: v.strip().upper() for k, v in value.items() if v and v.strip()} or None

class AcceptResponse(BaseModel):
  accepted: list[dict]
  failed: list[dict]

class DecideRequest(BaseModel):
  ids: list[UUID] = Field(min_length=1, max_length=500)

class DecideResponse(BaseModel):
  changed: list[UUID]
  failed: list[dict]

class RegisterSyncResponse(BaseModel):
  drawing_id: UUID
  total: int
  added: int
  updated: int
  removed: int
  by_type: dict = Field(default_factory=dict)
  sheets: int = 0
  sheets_read: int = 0
  waiting: list = Field(default_factory=list)
  set_aside: list = Field(default_factory=list)
  sheet_status: list = Field(default_factory=list)
  measured: int = 0
  needs_review: int = 0
  decisions: int = 0
  evidence: dict = Field(default_factory=dict)
  totals: list = Field(default_factory=list)
  source_mix: dict = Field(default_factory=dict)
  floors_to_decide: int = 0
  floors_undecided: list = Field(default_factory=list)
