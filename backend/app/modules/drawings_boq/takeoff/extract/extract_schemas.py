from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from decimal import Decimal

class ExtractRequest(BaseModel):
  auto_calibrate: bool = Field(default=False, description="If the sheet has no scale yet, set the recommended one, but only when the drawn scale and the printed dimensions agree.")
  budget_seconds: int = Field(default=25, ge=5, le=90)
  only_unread: bool = Field(default=False, description="Whole-drawing reads only: leave out sheets that were already read from the current prepared version of the sheet.")

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

class DrawingExtractResponse(BaseModel):
  drawing_id: UUID
  done: list[ExtractResponse]
  skipped: list[dict]

class AcceptRequest(BaseModel):
  ids: list[UUID] = Field(min_length=1, max_length=500)
  wall_height_mm: Decimal | None = Field(default=None, gt=0, le=20000)
  column_height_mm: Decimal | None = Field(default=None, gt=0, le=20000)
  footing_depth_mm: Decimal | None = Field(default=None, gt=0, le=10000)
  work_items: dict[str, str] | None = Field(default=None, description="Work item code to use per category, e.g. {\"WALL\": \"MAS-BLOCK\"}.")
  level_id: UUID | None = None

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
  measured: int = 0
  needs_review: int = 0