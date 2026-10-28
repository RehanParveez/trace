from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from typing import Literal

class FrameMemberResponse(BaseModel):
  measurement_id: str
  instance: int
  category: str
  tag: str | None = None
  length_mm: float
  width_mm: float
  sheet_x_mm: float
  sheet_y_mm: float
  x_mm: float | None = None
  y_mm: float | None = None

class FrameViewResponse(BaseModel):
  key: str
  reference: bool
  method: str
  grade: str
  dx_mm: float
  dy_mm: float
  supporters: int
  compared: int
  residual_mm: float
  confidence: float
  anchors: int
  decided: bool
  members: list[FrameMemberResponse] = []

class FrameColumnAtPlace(BaseModel):
  view: str
  tag: str | None = None
  length_mm: float
  width_mm: float

class FrameColumnIssue(BaseModel):
  code: Literal["COLUMN_TAG_DIFFERS", "COLUMN_SIZE_DIFFERS"]
  x_mm: float
  y_mm: float
  grade: Literal["ASSUMED", "CONFIRMED"]
  columns: list[FrameColumnAtPlace] = []

class FrameColumnsResponse(BaseModel):
  places: int = 0
  shared: int = 0
  agree: int = 0
  issues: list[FrameColumnIssue] = []

class FrameResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  drawing_id: UUID
  reference: str | None = None
  origin_mm: list[float] = [0.0, 0.0]
  views: list[FrameViewResponse] = []
  columns: FrameColumnsResponse = FrameColumnsResponse()
  status: Literal["NONE", "ASSUMED", "CONFIRMED"] = "NONE"
  open_views: list[str] = []
  unplaced: list[str] = []
  unconfirmed: list[str] = []
  cleared_placements: int = 0

class FramePlaceRequest(BaseModel):
  view: str = Field(min_length=1, max_length=200)
  action: Literal["CONFIRM", "SET", "CLEAR"]
  dx_mm: float | None = None
  dy_mm: float | None = None

class FrameReferenceRequest(BaseModel):
  view: str = Field(min_length=1, max_length=200)

class FloorLevelResponse(BaseModel):
  key: str
  level_mm: float | None = None
  clear_mm: float | None = None
  floor_to_floor_mm: float | None = None
  soffit_mm: float | None = None
  top_mm: float | None = None
  source: str | None = None
  level_source: str | None = None
  grade: Literal["PRINTED", "TYPED", "ASSUMED"] = "ASSUMED"
  reason: str | None = None
  sources: list[dict] = []
  decisions: list[dict] = []

class FootingLevelResponse(BaseModel):
  ngl_mm: float | None = None
  ngl_source: Literal["TYPED", "LEVEL_MARK"] | None = None
  bottom_below_ngl_mm: float | None = None
  usable: bool = False

class FloorDatumsResponse(BaseModel):
  drawing_id: UUID
  datum: Literal["DRAWING_LEVEL_ZERO", "GROUND_FLOOR_LEVEL"] = "GROUND_FLOOR_LEVEL"
  floors: list[FloorLevelResponse] = []
  footing: FootingLevelResponse = FootingLevelResponse()
