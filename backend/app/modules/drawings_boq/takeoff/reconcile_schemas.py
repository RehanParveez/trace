from __future__ import annotations
from typing import Literal
from uuid import UUID
from pydantic import BaseModel

class ReconcilePdfPlace(BaseModel):
  marks: list[str] = []
  views: list[str] = []

class ReconcileModelPlace(BaseModel):
  names: list[str] = []
  element_ids: list[str] = []

class ReconcilePair(BaseModel):
  pdf: ReconcilePdfPlace
  model: ReconcileModelPlace
  distance_mm: float

class ReconcileSizeDiffers(BaseModel):
  pdf: ReconcilePdfPlace
  model: ReconcileModelPlace
  pdf_size: list[float] | None = None
  model_size: list[float] | None = None

class ReconcileModelChoice(BaseModel):
  drawing_id: UUID
  filename: str
  columns: int

class ReconcileResponse(BaseModel):
  drawing_id: UUID
  model_drawing_id: UUID | None = None
  models: list[ReconcileModelChoice] = []
  status: Literal["NONE", "MATCHED", "UNMATCHED"] = "NONE"
  reason: str | None = None
  grade: Literal["ASSUMED", "CONFIRMED"] = "ASSUMED"
  method: str = ""
  dx_mm: float = 0.0
  dy_mm: float = 0.0
  supporters: int = 0
  compared: int = 0
  pdf_places: int = 0
  model_places: int = 0
  agrees: bool = False
  pairs: list[ReconcilePair] = []
  pdf_only: list[ReconcilePdfPlace] = []
  model_only: list[ReconcileModelPlace] = []
  size_differs: list[ReconcileSizeDiffers] = []
