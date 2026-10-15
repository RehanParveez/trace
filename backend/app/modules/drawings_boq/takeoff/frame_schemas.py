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

class FrameResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  drawing_id: UUID
  reference: str | None = None
  origin_mm: list[float] = [0.0, 0.0]
  views: list[FrameViewResponse] = []
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
