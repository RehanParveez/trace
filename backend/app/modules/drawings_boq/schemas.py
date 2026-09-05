from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.modules.drawings_boq.models import BOQItemStatus, BOQItemType, BOQVersionStatus, DrawingFormat, DrawingStatus, BOQItemRateSource

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
  status: BOQVersionStatus
  covered_area_sqft: Decimal | None
  export_meta: dict

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
  rate_source: str | None
  status: BOQItemStatus
  version: int
  approved_at: datetime | None
  item_type: BOQItemType
  created_by_user_id: UUID | None

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
  save_as_library_default: bool = Field(
    default=False,
    description="If true and unit_rate is set, save this rate as the org's default for this material going forward.",
  )

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
  default_rate: Decimal | None = None

class MaterialLibraryResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  raw_text: str
  normalized_name: str
  category: str | None
  default_unit: str | None
  default_rate: Decimal | None
  
class MaterialLibraryUpdateRequest(BaseModel):
  normalized_name: str | None = Field(default=None, min_length=1, max_length=300)
  category: str | None = Field(default=None, max_length=150)
  default_unit: str | None = Field(default=None, max_length=20)
  default_rate: Decimal | None = None

class LabourRateCreateRequest(BaseModel):
  trade: str = Field(min_length=1, max_length=150)
  unit: str = Field(min_length=1, max_length=20)
  rate: Decimal

class LabourRateUpdateRequest(BaseModel):
  trade: str | None = Field(default=None, min_length=1, max_length=150)
  unit: str | None = Field(default=None, min_length=1, max_length=20)
  rate: Decimal | None = None

class LabourRateResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  trade: str
  unit: str
  rate: Decimal

class BOQCustomItemCreateRequest(BaseModel):
  material_name: str = Field(min_length=1, max_length=300)
  category: str | None = Field(default=None, max_length=150)
  unit: str = Field(min_length=1, max_length=20)
  quantity: Decimal
  unit_rate: Decimal | None = None

class BOQVersionUpdateRequest(BaseModel):
  covered_area_sqft: Decimal | None = None
  export_meta: dict | None = None

class BOQSummaryResponse(BaseModel):
  boq_version_id: UUID
  materials_total: Decimal
  labour_total: Decimal
  custom_total: Decimal
  grand_total: Decimal
  cost_per_sqft: Decimal | None
  covered_area_sqft: Decimal | None
  amount_in_words: str
  unpriced_item_count: int
  unapproved_item_count: int
  item_count: int