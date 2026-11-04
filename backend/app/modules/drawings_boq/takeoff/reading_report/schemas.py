from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import datetime
from app.modules.drawings_boq.takeoff.reading_report import build as B

class ReasonOut(BaseModel):
  code: str
  text: str
  class_: str | None = Field(default=None, alias="class")
  model_config = {"populate_by_name": True}

class ItemOut(BaseModel):
  id: UUID
  ckey: str
  class_: str = Field(alias="class")
  category: str
  kind: str
  label: str
  mark: str | None = None
  status: str
  reasons: list[str] = Field(default_factory=list)
  source: str
  confidence: float | None = None
  count: int = 1
  decision: str
  valid: str
  points: list[list[float]] = Field(default_factory=list)
  box: list[float] | None = None
  missing: list[str] = Field(default_factory=list)
  joins: list[dict] = Field(default_factory=list)
  conflict: str | None = None
  model_config = {"populate_by_name": True}

class ClassRow(BaseModel):
  class_: str = Field(alias="class")
  expected: bool
  status: str | None = None
  reasons: list[str] = Field(default_factory=list)
  no_reader: bool = False
  count: int = 0
  by_status: dict[str, int] = Field(default_factory=dict)
  model_config = {"populate_by_name": True}

class SheetCard(BaseModel):
  sheet_id: UUID
  page_no: int
  title: str | None = None
  role: str | None = None
  plan_kind: str | None = None
  floor: str | None = None
  discipline: str | None = None
  scale_text: str | None = None
  scale: str
  text_type: str | None = None
  status: str | None = None
  ran: bool
  width_pt: float | None = None
  height_pt: float | None = None
  rotation: int = 0
  items: int
  by_status: dict[str, int]
  classes: list[ClassRow]
  reasons: list[ReasonOut]
  held: dict | None = None
  overrides: int = 0
  misreads: int = 0
  extract_version: int | None = None
  item_rows: list[ItemOut] | None = None

class ReportTotals(BaseModel):
  sheets: int
  ran: int
  items: int
  by_status: dict[str, int]
  empty_sheets: list[int]

class ReadingReportResponse(BaseModel):
  drawing_id: UUID
  sheets: list[SheetCard]
  totals: ReportTotals
  manual_marks_are_scored: bool = False
  joins_applied_to_quantities: bool = False

class SheetItemsResponse(BaseModel):
  sheet_id: UUID
  items: list[ItemOut]

class InputRow(BaseModel):
  input: str
  label: str
  state: str
  items: int
  marks: list[str] = Field(default_factory=list)

class ElementRow(BaseModel):
  element: str
  items: int
  complete: int
  accepted: int
  state: str
  inputs: list[InputRow]
  work_items: list[str] = Field(default_factory=list)

class BlockingRow(InputRow):
  element: str
  blocks: list[str] = Field(default_factory=list)

class CompletenessResponse(BaseModel):
  project_id: UUID
  elements: list[ElementRow]
  blocking: list[BlockingRow]
  items: int
  complete: int

class OverrideRequest(BaseModel):
  sheet_id: UUID
  item_class: str = Field(min_length=2, max_length=32)
  mark: str | None = Field(default=None, max_length=60)
  geometry: dict = Field(default_factory=dict)
  attrs: dict = Field(default_factory=dict)
  note: str | None = Field(default=None, max_length=2000)

  @field_validator("item_class")
  @classmethod
  def _class(cls, v: str) -> str:
    v = v.strip().upper()
    if v not in B.ITEM_CLASSES:
      raise ValueError("Unknown item class.")
    return v

  @field_validator("geometry")
  @classmethod
  def _geometry(cls, g: dict) -> dict:
    pts = g.get("points")
    box = g.get("box")
    if pts is None and box is None:
      raise ValueError("Give the place on the sheet: points or a box.")
    if pts is not None and (not isinstance(pts, list) or not pts or len(pts) > 200 or any(not isinstance(p, list) or len(p) != 2 or not all(isinstance(n, (int, float)) for n in p) for p in pts)):
      raise ValueError("points must be a list of [x, y] numbers.")
    if box is not None and (not isinstance(box, list) or len(box) != 4 or not all(isinstance(n, (int, float)) for n in box)):
      raise ValueError("box must be [x0, y0, x1, y1].")
    return g

class OverrideOut(BaseModel):
  id: UUID
  drawing_id: UUID
  sheet_id: UUID
  item_class: str
  mark: str | None = None
  geometry: dict
  attrs: dict
  note: str | None = None
  status: str
  image_checked: bool
  created_at: datetime
  counts_as_truth: bool = False
  model_config = {"from_attributes": True}

class OverrideListResponse(BaseModel):
  drawing_id: UUID
  overrides: list[OverrideOut]

class MisreadRequest(BaseModel):
  sheet_id: UUID
  kind: str
  candidate_id: UUID | None = None
  item_class: str | None = Field(default=None, max_length=32)
  mark: str | None = Field(default=None, max_length=60)
  box: list[float] | None = None
  expected: dict = Field(default_factory=dict)
  read_as: dict = Field(default_factory=dict)
  note: str | None = Field(default=None, max_length=2000)

  @field_validator("kind")
  @classmethod
  def _kind(cls, v: str) -> str:
    v = v.strip().upper()
    if v not in B.MISREAD_KINDS:
      raise ValueError("Unknown kind of misread.")
    return v

  @field_validator("box")
  @classmethod
  def _box(cls, b):
    if b is not None and len(b) != 4:
      raise ValueError("box must be [x0, y0, x1, y1].")
    return b

class MisreadOut(BaseModel):
  id: UUID
  drawing_id: UUID
  sheet_id: UUID
  candidate_id: UUID | None = None
  ckey: str | None = None
  item_class: str | None = None
  mark: str | None = None
  kind: str
  box: list | None = None
  expected: dict
  read_as: dict
  note: str | None = None
  extract_version: int | None = None
  status: str
  created_at: datetime
  model_config = {"from_attributes": True}
