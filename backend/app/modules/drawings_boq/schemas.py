from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.modules.drawings_boq.models import BOQItemStatus, DrawingFormat, DrawingStatus

class DrawingResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  project_id: UUID
  original_filename: str
  format: DrawingFormat
  status: DrawingStatus
  file_size_bytes: int
  error_message: str | None
  parsed_at: datetime | None
  created_at: datetime

class DrawingElementResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  ifc_global_id: str | None
  ifc_type: str
  name: str | None
  raw_material_text: str | None
  unit: str | None
  quantity: Decimal
  properties: dict

class BOQVersionResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  project_id: UUID
  drawing_id: UUID | None
  label: str
  created_at: datetime

class BOQItemResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  boq_version_id: UUID
  drawing_element_id: UUID | None
  material_name: str
  category: str | None
  unit: str
  quantity: Decimal
  unit_rate: Decimal | None
  status: BOQItemStatus
  version: int
  approved_at: datetime | None

class BOQItemUpdateRequest(BaseModel):
  version: int = Field(
    ...,
    description="Version last read by the client; enforces optimistic locking.",
  )
  material_name: str | None = Field(
    default=None,
    min_length=1,
    max_length=300,
  )
  category: str | None = Field(
    default=None,
    max_length=150,
  )
  unit: str | None = Field(
    default=None,
    min_length=1,
    max_length=20,
  )
  quantity: Decimal | None = None
  unit_rate: Decimal | None = None

class MaterialLibraryCreateRequest(BaseModel):
  raw_text: str = Field(
    min_length=1,
    max_length=300,
  )
  normalized_name: str = Field(
    min_length=1,
    max_length=300,
  )
  category: str | None = Field(
    default=None,
    max_length=150,
  )
  default_unit: str | None = Field(
    default=None,
    max_length=20,
  )

class MaterialLibraryResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  raw_text: str
  normalized_name: str
  category: str | None
  default_unit: str | None