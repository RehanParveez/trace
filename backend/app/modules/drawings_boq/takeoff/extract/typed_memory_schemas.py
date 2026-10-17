from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

class TypedValue(BaseModel):
  kind: str = Field(description="The kind of item it was typed for: COLUMN, BEAM, CHAJJA, PARAPET, ...")
  field: str = Field(description="The field it was typed in (site_thickness_mm, column_height_mm, ...).")
  value_mm: float
  times: int = Field(default=1, description="How many accepted items took this same value.")
  at: datetime

class TypedMemoryResponse(BaseModel):
  drawing_id: UUID
  values: list[TypedValue]