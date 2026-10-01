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
  revision_group_id: UUID
  revision_label: str | None
  is_current_revision: bool
  superseded_at: datetime | None
  ingestion_meta: dict
  latest_audit_id: UUID | None

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
  discipline: str | None = None
  structural_role: str | None = None
  classification_source: str | None = None
  classification_confidence: Decimal | None = None
  quantity_source: str | None = None
  level_id: UUID | None = None
  length_mm: Decimal | None = None
  width_mm: Decimal | None = None
  height_mm: Decimal | None = None
  thickness_mm: Decimal | None = None
  elevation_base_mm: Decimal | None = None
  elevation_top_mm: Decimal | None = None
  area_mm2: Decimal | None = None
  volume_mm3: Decimal | None = None
  geometry_kind: str | None = None
  normalization_status: str = "PENDING"
  normalization_issues: list[dict] = Field(default_factory=list)

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
  
class ProjectBOQCountResponse(BaseModel):
  project_id: UUID
  latest_boq_item_count: int

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
  
class PDFExtractionResultResponse(BaseModel):
  boq_version_id: UUID
  created_item_count: int
  items: list[BOQItemResponse]
  
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
  
class BOQVersionCreateRequest(BaseModel):
  label: str = Field(min_length=1, max_length=200)

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
  
class BuildingLevelResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  name: str
  elevation_mm: Decimal | None
  ifc_storey_id: str | None
  sequence: int

class ModelAuditResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  drawing_id: UUID
  overall_score: Decimal
  issues: list[dict]
  element_count: int
  missing_material_count: int
  zero_quantity_count: int
  unclassified_proxy_count: int
  extra_stats: dict
  created_at: datetime