from __future__ import annotations
import enum
import uuid
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from sqlalchemy import BigInteger, CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, Boolean, text, Date, ForeignKeyConstraint, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.shared.mixins import TimestampMixin
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.dialects.postgresql import JSONB

class DrawingFormat(str, enum.Enum):
  IFC = "IFC"
  PDF = "PDF"
  DWG = "DWG"
  DXF = "DXF"
  RVT = "RVT"

class DrawingStatus(str, enum.Enum):
  UPLOADED = "UPLOADED"
  PROCESSING = "PROCESSING"
  PARSED = "PARSED"
  FAILED = "FAILED"

class BOQItemStatus(str, enum.Enum):
  DRAFT = "DRAFT"
  APPROVED = "APPROVED"
  
class BOQItemType(str, enum.Enum):
  MATERIAL = "MATERIAL"
  LABOUR = "LABOUR"
  CUSTOM = "CUSTOM"
  
class BOQItemRateSource(str, enum.Enum):
  LIBRARY = "LIBRARY"
  AI_SUGGESTED = "AI_SUGGESTED"
  MANUAL = "MANUAL"

class BOQVersionStatus(str, enum.Enum):
  ACTIVE = "ACTIVE"
  SUPERSEDED = "SUPERSEDED"
  
class RuleSetStatus(str, enum.Enum):
  DRAFT = "DRAFT"
  ACTIVE = "ACTIVE"
  SUPERSEDED = "SUPERSEDED"
  ARCHIVED = "ARCHIVED"
  
class CalculationRunStatus(str, enum.Enum):
  QUEUED = "QUEUED"
  RUNNING = "RUNNING"
  STAGED = "STAGED"
  PROMOTED = "PROMOTED"
  COMPLETED = "COMPLETED"
  FAILED = "FAILED"
  CANCELLED = "CANCELLED"
  SUPERSEDED = "SUPERSEDED"
 
class RunStageStatus(str, enum.Enum):
  PENDING = "PENDING"
  RUNNING = "RUNNING"
  SUCCEEDED = "SUCCEEDED"
  FAILED = "FAILED"
  SKIPPED = "SKIPPED"
 
class SolidStatus(str, enum.Enum):
  OK = "OK"
  REVIEW_REQUIRED = "REVIEW_REQUIRED"  
  REJECTED = "REJECTED"                 
 
class LedgerSourceKind(str, enum.Enum):
  MODEL = "MODEL"
  SCHEDULE_IMPORT = "SCHEDULE_IMPORT"  
  MANUAL = "MANUAL"                     
  ESTIMATE = "ESTIMATE"                 
 
_RUN_STATUSES = "'QUEUED','RUNNING','STAGED','PROMOTED','COMPLETED','FAILED','CANCELLED','SUPERSEDED'"
_ACTIVE_RUN_STATUSES = "'QUEUED','RUNNING','STAGED','PROMOTED'"
_SOLID_STATUSES = "'OK','REVIEW_REQUIRED','REJECTED'"
_GEOMETRY_KINDS = "'EXTRUDED_PROFILE','AXIS_SWEPT','BOX_ONLY','QTO_ONLY','UNSUPPORTED'"
_LEDGER_SOURCES = "'MODEL','SCHEDULE_IMPORT','MANUAL','ESTIMATE'"
_CANONICAL_UNITS = "'m3','m2','m','kg','nos'"
 
class Drawing(Base, TimestampMixin):
  __tablename__ = "drawings"

  __table_args__ = (
    Index("ix_drawings_org_project", "organization_id", "project_id"),
  )

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4,
  )

  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
  )

  project_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("projects.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
  )

  uploaded_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )

  original_filename: Mapped[str] = mapped_column(
    String(500),
    nullable=False,
  )

  storage_key: Mapped[str] = mapped_column(
    String(1000),
    nullable=False,
  )

  format: Mapped[DrawingFormat] = mapped_column(
    Enum(DrawingFormat, name="drawing_format"),
    nullable=False,
  )

  status: Mapped[DrawingStatus] = mapped_column(
    Enum(DrawingStatus, name="drawing_status"),
    nullable=False,
    default=DrawingStatus.UPLOADED,
    index=True,
  )

  file_size_bytes: Mapped[int] = mapped_column(
    BigInteger,
    nullable=False,
    default=0,
  )

  error_message: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
  )

  parsed_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
  )

  elements: Mapped[list["DrawingElement"]] = relationship(
    "DrawingElement",
    back_populates="drawing",
    cascade="all, delete-orphan",
  )

  boq_versions: Mapped[list["BOQVersion"]] = relationship(
    "BOQVersion",
    back_populates="drawing",
  )
  
  revision_group_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    nullable=False,
    index=True,
  )

  revision_label: Mapped[str | None] = mapped_column(
    String(100),
    nullable=True,
  )
  
  is_current_revision: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    default=True,
  )
  
  superseded_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
  )
  
  latest_audit_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("model_audit_results.id", ondelete="SET NULL", name="fk_drawings_latest_audit_id", use_alter=True),
    nullable=True,
  )
  
  ingestion_meta: Mapped[dict] = mapped_column(
    JSONB,
    nullable=False,
    default=dict,
    server_default=text("'{}'::jsonb"),
  )

class DrawingElement(Base, TimestampMixin):
  __tablename__ = "drawing_elements"

  __table_args__ = (
    Index("ix_drawing_elements_drawing", "drawing_id"),
    Index("ix_drawing_elements_org_drawing_type", "organization_id", "drawing_id", "ifc_type"),
    Index("ix_drawing_elements_drawing_level_role", "drawing_id", "level_id", "structural_role"),
    Index("ix_drawing_elements_drawing_status", "drawing_id", "normalization_status"),
    CheckConstraint(
      "geometry_kind IS NULL OR geometry_kind IN "
      "('EXTRUDED_PROFILE','AXIS_SWEPT','BOX_ONLY','QTO_ONLY','UNSUPPORTED')",
      name="ck_drawing_elements_geometry_kind",
    ),
    CheckConstraint(
      "normalization_status IN ('PENDING','VALID','WARNING','INVALID')",
      name="ck_drawing_elements_normalization_status",
    ),
  )

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4,
  )

  drawing_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("drawings.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
  )

  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
  )

  ifc_global_id: Mapped[str | None] = mapped_column(
    String(64),
    nullable=True,
  )

  ifc_type: Mapped[str] = mapped_column(
    String(100),
    nullable=False,
  )

  name: Mapped[str | None] = mapped_column(
    String(500),
    nullable=True,
  )

  raw_material_text: Mapped[str | None] = mapped_column(
    String(500),
    nullable=True,
  )

  unit: Mapped[str | None] = mapped_column(
    String(20),
    nullable=True,
  )

  quantity: Mapped[Decimal] = mapped_column(
    Numeric(18, 4),
    nullable=False,
    default=0,
  )

  properties: Mapped[dict] = mapped_column(
    JSON,
    nullable=False,
    default=dict,
  )
  
  discipline: Mapped[str | None] = mapped_column(String(20), nullable=True)
  structural_role: Mapped[str | None] = mapped_column(String(30), nullable=True)
  classification_source: Mapped[str | None] = mapped_column(String(30), nullable=True)
  
  classification_confidence: Mapped[Decimal | None] = mapped_column(
    Numeric(5, 4),
    nullable=True,
  )
  quantity_source: Mapped[str | None] = mapped_column(String(20), nullable=True)

  level_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("building_levels.id", ondelete="SET NULL"),
    nullable=True,
  )

  length_mm: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
  width_mm: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
  height_mm: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
  thickness_mm: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
  elevation_base_mm: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
  elevation_top_mm: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
  area_mm2: Mapped[Decimal | None] = mapped_column(Numeric(20, 3), nullable=True)
  volume_mm3: Mapped[Decimal | None] = mapped_column(Numeric(24, 3), nullable=True)

  bbox_min_x_mm: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
  bbox_min_y_mm: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
  bbox_min_z_mm: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
  bbox_max_x_mm: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
  bbox_max_y_mm: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
  bbox_max_z_mm: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)

  geometry_kind: Mapped[str | None] = mapped_column(String(20), nullable=True)
  profile: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
  placement: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

  normalization_status: Mapped[str] = mapped_column(
    String(10),
    nullable=False,
    default="PENDING",
    server_default="PENDING",
  )
  normalization_issues: Mapped[list] = mapped_column(
    JSONB,
    nullable=False,
    default=list,
    server_default=text("'[]'::jsonb"),
  ) 
   
  drawing: Mapped["Drawing"] = relationship(
    "Drawing",
    back_populates="elements",
  )

class BuildingLevel(Base, TimestampMixin):
  __tablename__ = "building_levels"
  __table_args__ = (
    UniqueConstraint("drawing_id", "ifc_storey_id", name="uq_building_levels_drawing_storey"),
    Index("ix_building_levels_drawing_sequence", "drawing_id", "sequence"),
  )

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4,
  )

  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
  )

  drawing_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("drawings.id", ondelete="CASCADE"),
    nullable=False,
  )

  name: Mapped[str] = mapped_column(String(200), nullable=False)
  elevation_mm: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
  ifc_storey_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
  sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

class BOQVersion(Base, TimestampMixin):
  __tablename__ = "boq_versions"

  __table_args__ = (
    Index("ix_boq_versions_org_project", "organization_id", "project_id"),
  )

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4,
  )

  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
  )

  project_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("projects.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
  )

  drawing_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("drawings.id", ondelete="SET NULL"),
    nullable=True,
  )

  label: Mapped[str] = mapped_column(
    String(200),
    nullable=False,
  )
  
  status: Mapped[BOQVersionStatus] = mapped_column(
    Enum(BOQVersionStatus, name="boq_version_status"),
    nullable=False,
    default=BOQVersionStatus.ACTIVE,
    index=True,
  )

  covered_area_sqft: Mapped[Decimal | None] = mapped_column(
    Numeric(14, 2),
    nullable=True,
  )

  export_meta: Mapped[dict] = mapped_column(
    JSON,
    nullable=False,
    default=dict,
  )

  rule_set_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("measurement_rule_sets.id", ondelete="SET NULL",
      name="fk_boq_versions_rule_set_id"),
      nullable=True,
    )

  audit_score: Mapped[Decimal | None] = mapped_column(
    Numeric(5, 2),
    nullable=True,
  )

  generation_meta: Mapped[dict] = mapped_column(
    JSONB,
    nullable=False,
    default=dict,
    server_default=text("'{}'::jsonb"),
  )

  drawing: Mapped["Drawing | None"] = relationship(
    "Drawing",
    back_populates="boq_versions",
  )

  items: Mapped[list["BOQItem"]] = relationship(
    "BOQItem",
    back_populates="boq_version",
    cascade="all, delete-orphan",
  )

class BOQItem(Base, TimestampMixin):
  __tablename__ = "boq_items"

  __table_args__ = (
    Index("ix_boq_items_version", "boq_version_id"),
    Index("ix_boq_items_org_status", "organization_id", "status"),
  )

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4,
  )

  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
  )

  boq_version_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("boq_versions.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
  )

  drawing_element_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("drawing_elements.id", ondelete="SET NULL"),
    nullable=True,
  )

  material_name: Mapped[str] = mapped_column(
    String(300),
    nullable=False,
  )

  category: Mapped[str | None] = mapped_column(
    String(150),
    nullable=True,
  )

  unit: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
  )

  quantity: Mapped[Decimal] = mapped_column(
    Numeric(18, 4),
    nullable=False,
    default=0,
  )

  unit_rate: Mapped[Decimal | None] = mapped_column(
    Numeric(14, 2),
    nullable=True,
  )
  
  rate_source: Mapped[BOQItemRateSource | None] = mapped_column(
    Enum(BOQItemRateSource, name="boq_item_rate_source"),
    nullable=True,
  )
  
  item_type: Mapped[BOQItemType] = mapped_column(
    Enum(BOQItemType, name="boq_item_type"),
    nullable=False,
    default=BOQItemType.MATERIAL,
    index=True,
  )

  created_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )

  status: Mapped[BOQItemStatus] = mapped_column(
    Enum(BOQItemStatus, name="boq_item_status"),
    nullable=False,
    default=BOQItemStatus.DRAFT,
    index=True,
  )

  version: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    default=1,
  )

  approved_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )

  approved_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
  )

  boq_version: Mapped["BOQVersion"] = relationship(
    "BOQVersion",
    back_populates="items",
  )
  
  work_item_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
  description: Mapped[str | None] = mapped_column(Text, nullable=True) 
  calculation_formula: Mapped[str | None] = mapped_column(String(500), nullable=True)
  confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
  
  rule_set_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("measurement_rule_sets.id", ondelete="SET NULL", name="fk_boq_items_rule_set_id"),
    nullable=True,
  )
  
  recipe_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("assembly_recipes.id", ondelete="SET NULL", name="fk_boq_items_recipe_id"),
    nullable=True,
  )
  
  gross_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
  net_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
  waste_factor_applied: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
  source_element_count: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    default=0,
    server_default=text("0"),
  )

class MaterialLibrary(Base, TimestampMixin):
  __tablename__ = "material_library"

  __table_args__ = (
    UniqueConstraint(
      "organization_id",
      "raw_text",
      name="uq_material_library_org_raw_text",
    ),
    Index("ix_material_library_org", "organization_id"),
  )

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4,
  )

  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
  )

  raw_text: Mapped[str] = mapped_column(
    String(300),
    nullable=False,
  )

  normalized_name: Mapped[str] = mapped_column(
    String(300),
    nullable=False,
  )

  category: Mapped[str | None] = mapped_column(
    String(150),
    nullable=True,
  )

  default_unit: Mapped[str | None] = mapped_column(
    String(20),
    nullable=True,
  )
  
  default_rate: Mapped[Decimal | None] = mapped_column(
    Numeric(14, 2),
    nullable=True,
  )
  
class LabourRate(Base, TimestampMixin):
  __tablename__ = "labour_rates"

  __table_args__ = (
    UniqueConstraint(
      "organization_id",
      "trade",
      name="uq_labour_rates_org_trade",
    ),
    Index("ix_labour_rates_org", "organization_id"),
  )

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4,
  )

  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
  )

  trade: Mapped[str] = mapped_column(String(150), nullable=False)
  unit: Mapped[str] = mapped_column(String(20), nullable=False)
  rate: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

class MaterialNormalizationCache(Base, TimestampMixin):
  __tablename__ = "material_normalization_cache"
  
  __table_args__ = (
    Index(
      "uq_material_norm_cache_org_hash",
      "organization_id",
      "input_hash",
      unique=True,
      postgresql_where=text("organization_id IS NOT NULL"),
    ),
    Index(
      "uq_material_norm_cache_system_hash",
      "input_hash",
      unique=True,
      postgresql_where=text("organization_id IS NULL"),
    ),
  )

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4,
  )

  input_hash: Mapped[str] = mapped_column(
    String(64),
    nullable=False,
    index=True,
  )

  normalized_name: Mapped[str] = mapped_column(
    String(300),
    nullable=False,
  )

  category: Mapped[str | None] = mapped_column(
    String(150),
    nullable=True,
  )

  source: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default="dictionary",
  )
  
  organization_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=True,          
    index=True,
  )
  
class BOQItemSourceElement(Base):
  __tablename__ = "boq_item_source_elements"

  __table_args__ = (
    UniqueConstraint("boq_item_id", "drawing_element_id", name="uq_boq_item_source_element"),
  )

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4,
  )
  
  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"), 
    nullable=False,
  )
  
  boq_item_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("boq_items.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  drawing_element_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("drawing_elements.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  quantity_contributed: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
  
  formula_snippet: Mapped[str | None] = mapped_column(String(300), nullable=True)
  contribution_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
  
class MeasurementConvention(Base, TimestampMixin):
  __tablename__ = "measurement_conventions"
  
  __table_args__ = (
    UniqueConstraint("code", name="uq_measurement_conventions_code"),
    Index("ix_measurement_conventions_active", "is_active"),
  )
  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
 
  code: Mapped[str] = mapped_column(String(80), nullable=False) 
  name: Mapped[str] = mapped_column(String(200), nullable=False)
  description: Mapped[str | None] = mapped_column(Text, nullable=True)
  is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
  is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
  conserves_volume: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
  
  parameters: Mapped[dict] = mapped_column(
    JSONB,
    nullable=False,
    default=dict,
    server_default=text("'{}'::jsonb"),
  )
  
class MeasurementRuleSet(Base, TimestampMixin):
  __tablename__ = "measurement_rule_sets"
  
  __table_args__ = (
    
    UniqueConstraint(
      "organization_id", "code", "immutable_version",
      name="uq_measurement_rule_sets_org_code_version",
    ),
  
    Index(
      "uq_measurement_rule_sets_system_code_version",
      "code", "immutable_version",
      unique=True,
      postgresql_where=text("organization_id IS NULL"),
    ),
    
    Index(
      "uq_measurement_rule_sets_active_org",
      "organization_id", "code",
      unique=True,
      postgresql_where=text("status = 'ACTIVE' AND organization_id IS NOT NULL"),
    ),
    Index(
      "uq_measurement_rule_sets_active_system",
      "code",
      unique=True,
      postgresql_where=text("status = 'ACTIVE' AND organization_id IS NULL"),
    ),
    
    Index("ix_measurement_rule_sets_org", "organization_id"),
    Index("ix_measurement_rule_sets_status", "status"),
    
    CheckConstraint(
      "status IN ('DRAFT','ACTIVE','SUPERSEDED','ARCHIVED')",
      name="ck_measurement_rule_sets_status",
    ),
    
    CheckConstraint(
      "net_vs_gross_preference IN ('net','gross')",
      name="ck_measurement_rule_sets_net_gross",
    ),
    
    CheckConstraint("immutable_version >= 1", name="ck_measurement_rule_sets_version_pos"),
    
    CheckConstraint(
      "effective_from IS NULL OR effective_to IS NULL OR effective_to >= effective_from",
      name="ck_measurement_rule_sets_effective_range",
    ),
    
    CheckConstraint(
      "status = 'DRAFT' OR published_at IS NOT NULL",
      name="ck_measurement_rule_sets_published_at",
    ),
  )

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4,
  )
  
  organization_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id",
      ondelete="CASCADE"),
      nullable=True, index=True,
    )  
  
  code: Mapped[str] = mapped_column(String(50), nullable=False)  
  name: Mapped[str] = mapped_column(String(200), nullable=False)
  description: Mapped[str | None] = mapped_column(Text, nullable=True)
  is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
  is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
  
  jurisdiction: Mapped[str | None] = mapped_column(String(50), nullable=True)      
  province: Mapped[str | None] = mapped_column(String(50), nullable=True)        
  city: Mapped[str | None] = mapped_column(String(100), nullable=True)
  standard_name: Mapped[str | None] = mapped_column(String(100), nullable=True)    
  standard_edition: Mapped[str | None] = mapped_column(String(50), nullable=True) 
  effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
  effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
 
  convention_code: Mapped[str | None] = mapped_column(
    String(80),
    ForeignKey("measurement_conventions.code", ondelete="RESTRICT",
      name="fk_measurement_rule_sets_convention_code"),
      nullable=True,
  )
 
  status: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default=RuleSetStatus.DRAFT.value, server_default="DRAFT",
  )
  
  immutable_version: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    default=1,
    server_default=text("1"),
  )
  
  published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  
  published_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL",
      name="fk_measurement_rule_sets_published_by"),
      nullable=True,
  )
  
  content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True) 
  
  supersedes_rule_set_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("measurement_rule_sets.id", ondelete="SET NULL",
      name="fk_measurement_rule_sets_supersedes"),
      nullable=True,
  )
 
  opening_deduction_threshold_m2: Mapped[Decimal] = mapped_column(
    Numeric(10, 4),
    nullable=False,
    default=Decimal("0.5"),
  )
  
  wall_measurement_method: Mapped[str] = mapped_column(
    String(30),
    nullable=False,
    default="centre_line",
  ) 
 
  preferred_units: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)  
  waste_factors: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)  
  net_vs_gross_preference: Mapped[str] = mapped_column(String(10), nullable=False, default="net")  
  extra_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
  
  opening_rules: Mapped[list["OpeningMeasurementRule"]] = relationship(
    "OpeningMeasurementRule",
    back_populates="rule_set",
    cascade="all, delete-orphan",
  )
  
  wastage_rules: Mapped[list["MaterialWastageRule"]] = relationship(
    "MaterialWastageRule",
    back_populates="rule_set",
    cascade="all, delete-orphan",
  )
  
  reinforcement_rules: Mapped[list["ReinforcementRule"]] = relationship(
    "ReinforcementRule",
    back_populates="rule_set",
    cascade="all, delete-orphan",
  )
  
  element_type_mappings: Mapped[list["ElementTypeMapping"]] = relationship(
    "ElementTypeMapping",
    back_populates="rule_set",
    cascade="all, delete-orphan",
  )
  
class OpeningMeasurementRule(Base, TimestampMixin):
  __tablename__ = "opening_measurement_rules"
  
  __table_args__ = (
    UniqueConstraint(
      "rule_set_id", "element_scope", "lower_area_m2",
      name="uq_opening_measurement_rules_scope_lower",
    ),
    
    Index("ix_opening_measurement_rules_rule_set", "rule_set_id"),
    CheckConstraint(
      "deduction_behavior IN ('DEDUCT','IGNORE','PARTIAL')",
      name="ck_opening_measurement_rules_deduction",
    ),
    
    CheckConstraint("lower_area_m2 >= 0", name="ck_opening_measurement_rules_lower"),
    
    CheckConstraint(
      "upper_area_m2 IS NULL OR upper_area_m2 > lower_area_m2",
      name="ck_opening_measurement_rules_range",
    ),
    
    CheckConstraint(
      "deduction_fraction IS NULL OR (deduction_fraction >= 0 AND deduction_fraction <= 1)",
      name="ck_opening_measurement_rules_fraction",
    ),
    
    CheckConstraint(
      "deduction_behavior <> 'PARTIAL' OR deduction_fraction IS NOT NULL",
      name="ck_opening_measurement_rules_partial_needs_fraction",
    ),
  )
 
  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
 
  rule_set_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("measurement_rule_sets.id", ondelete="CASCADE"),
    nullable=False,
  )
 
  element_scope: Mapped[str] = mapped_column(String(50), nullable=False, default="ALL")  
  
  lower_area_m2: Mapped[Decimal] = mapped_column(
    Numeric(10, 4),
    nullable=False,
    default=Decimal("0"),
  )
  upper_area_m2: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True) 
  
  deduction_behavior: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default="DEDUCT",
  )
  
  deduction_fraction: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)  
  edge_behavior: Mapped[str | None] = mapped_column(String(50), nullable=True)
  
  extra_config: Mapped[dict] = mapped_column(
    JSONB,
    nullable=False,
    default=dict,
    server_default=text("'{}'::jsonb"),
  )
 
  rule_set: Mapped["MeasurementRuleSet"] = relationship("MeasurementRuleSet", back_populates="opening_rules")
  
class ReinforcementRule(Base, TimestampMixin):
  __tablename__ = "reinforcement_rules"
  __table_args__ = (
    UniqueConstraint(
      "rule_set_id", "element_scope", "bar_role",
      name="uq_reinforcement_rules_scope_role",
    ),
    Index("ix_reinforcement_rules_rule_set", "rule_set_id"),
    CheckConstraint(
      "lap_coefficient IS NULL OR lap_coefficient >= 0",
      name="ck_reinforcement_rules_lap_coeff",
    ),
  )
 
  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
 
  rule_set_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("measurement_rule_sets.id", ondelete="CASCADE"),
    nullable=False,
  )
 
  element_scope: Mapped[str] = mapped_column(String(50), nullable=False, default="ALL")  
  bar_role: Mapped[str] = mapped_column(String(50), nullable=False) 
  lap_basis: Mapped[str | None] = mapped_column(String(30), nullable=True)  
  lap_coefficient: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
  
  hook_rules: Mapped[dict] = mapped_column(
    JSONB,
    nullable=False,
    default=dict,
    server_default=text("'{}'::jsonb"),
  )
  
  bend_rules: Mapped[dict] = mapped_column(
    JSONB,
    nullable=False,
    default=dict,
    server_default=text("'{}'::jsonb"),
  )
  
  dev_length_method: Mapped[str | None] = mapped_column(String(40), nullable=True)
  
  splice_constraints: Mapped[dict] = mapped_column(
    JSONB,
    nullable=False,
    default=dict, server_default=text("'{}'::jsonb"),
  )
  
  extra_config: Mapped[dict] = mapped_column(
    JSONB,
    nullable=False,
    default=dict,
    server_default=text("'{}'::jsonb"),
  )
 
  rule_set: Mapped["MeasurementRuleSet"] = relationship(
    "MeasurementRuleSet",
    back_populates="reinforcement_rules",
  )
  
class MaterialWastageRule(Base, TimestampMixin):
  __tablename__ = "material_wastage_rules"
  
  __table_args__ = (
    UniqueConstraint(
      "rule_set_id", "material_class", "procurement_stage",
      name="uq_material_wastage_rules_class_stage",
    ),
    
    Index("ix_material_wastage_rules_rule_set", "rule_set_id"),
    CheckConstraint("factor >= 1 AND factor <= 2", name="ck_material_wastage_rules_factor"),
  )
 
  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
 
  rule_set_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("measurement_rule_sets.id", ondelete="CASCADE"),
    nullable=False,
  )
 
  material_class: Mapped[str] = mapped_column(String(80), nullable=False)  
  procurement_stage: Mapped[str] = mapped_column(String(40), nullable=False, default="SITE")
  factor: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=Decimal("1.0"))
  unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
  justification: Mapped[str | None] = mapped_column(Text, nullable=True)
 
  rule_set: Mapped["MeasurementRuleSet"] = relationship(
    "MeasurementRuleSet",
    back_populates="wastage_rules",
  )
 

class ElementTypeMapping(Base, TimestampMixin):
  __tablename__ = "element_type_mappings"
  __table_args__ = (
    UniqueConstraint("rule_set_id", "ifc_type", name="uq_element_type_mappings_rule_ifc"),
    Index("ix_element_type_mappings_rule", "rule_set_id"),
  )
  
  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4,
  )
  
  rule_set_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("measurement_rule_sets.id", ondelete="CASCADE"),
    nullable=False
  )
  
  ifc_type: Mapped[str] = mapped_column(String(100), nullable=False)
  work_item_code: Mapped[str | None] = mapped_column(String(50), nullable=True)  
  default_category: Mapped[str | None] = mapped_column(String(150), nullable=True)
  
  quantity_source_preference: Mapped[str] = mapped_column(
    String(30),
    nullable=False,
    default="qto_first"
  )  
  
  unit_override: Mapped[str | None] = mapped_column(String(20), nullable=True)
  confidence_base: Mapped[Decimal] = mapped_column(
    Numeric(5, 4), 
    nullable=False, 
    default=Decimal("0.85"),
  )
  
  extra_mapping: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
  
  rule_set: Mapped["MeasurementRuleSet"] = relationship(
    "MeasurementRuleSet",
    back_populates="element_type_mappings",
  )
  
class WorkItem(Base, TimestampMixin):
  __tablename__ = "work_items"
  __table_args__ = (
    UniqueConstraint("organization_id", "code", name="uq_work_items_org_code"),
    Index(
      "uq_work_items_system_code", "code",
      unique=True,
      postgresql_where=text("organization_id IS NULL"),
    ),
    Index("ix_work_items_org", "organization_id"),
    Index("ix_work_items_code", "code"),
  )
 
  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
 
  organization_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=True,
    index=True,
  )
 
  code: Mapped[str] = mapped_column(String(50), nullable=False)
  description: Mapped[str] = mapped_column(String(500), nullable=False)
  unit: Mapped[str] = mapped_column(String(20), nullable=False)
  trade: Mapped[str | None] = mapped_column(String(80), nullable=True)
  wbs_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
  specification: Mapped[str | None] = mapped_column(Text, nullable=True)
  csr_ref: Mapped[str | None] = mapped_column(String(80), nullable=True)
  default_formula_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
  is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
  is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
  
  extra: Mapped[dict] = mapped_column(
    JSONB,
    nullable=False,
    default=dict,
    server_default=text("'{}'::jsonb"),
  )

class AssemblyRecipe(Base, TimestampMixin):
  __tablename__ = "assembly_recipes"
  __table_args__ = (
    
    Index(
      "uq_assembly_recipes_ruleset_code", "rule_set_id", "code",
      unique=True,
      postgresql_where=text("rule_set_id IS NOT NULL"),
    ),
    
    Index(
      "uq_assembly_recipes_org_code_unbound", "organization_id", "code",
      unique=True,
      postgresql_where=text("rule_set_id IS NULL AND organization_id IS NOT NULL"),
    ),
   
    Index(
      "uq_assembly_recipes_system_code_unbound", "code",
      unique=True,
      postgresql_where=text("rule_set_id IS NULL AND organization_id IS NULL"),
    ),
    
    Index("ix_assembly_recipes_org", "organization_id"),
    Index("ix_assembly_recipes_rule_set", "rule_set_id"),
  )
  
  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  
  organization_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=True,
    index=True,
  )
  
  rule_set_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("measurement_rule_sets.id", ondelete="CASCADE", name="fk_assembly_recipes_rule_set_id"),
    nullable=True,
  )
  
  code: Mapped[str] = mapped_column(String(80), nullable=False)  
  name: Mapped[str] = mapped_column(String(200), nullable=False)
  description: Mapped[str | None] = mapped_column(Text, nullable=True)
  trigger_ifc_types: Mapped[list] = mapped_column(JSON, nullable=False, default=list)  
  trigger_conditions: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)  
  is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
  is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
  
  components: Mapped[list["AssemblyRecipeComponent"]] = relationship(
    "AssemblyRecipeComponent",
    back_populates="recipe", cascade="all, delete-orphan",
    order_by="AssemblyRecipeComponent.sequence",
  )

class AssemblyRecipeComponent(Base, TimestampMixin):
  __tablename__ = "assembly_recipe_components"
  __table_args__ = (
    Index("ix_assembly_recipe_components_recipe", "recipe_id"),
    CheckConstraint(
      "item_type IN ('MATERIAL','LABOUR','CUSTOM')",
      name="ck_assembly_recipe_components_item_type",
    ),
    CheckConstraint("unit = output_unit", name="ck_assembly_recipe_components_unit_safe"),
    CheckConstraint("waste_factor >= 1", name="ck_assembly_recipe_components_waste"),
  )
  
  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  
  recipe_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True), 
    ForeignKey("assembly_recipes.id", ondelete="CASCADE", name="fk_assembly_recipe_components_recipe_id"),
    nullable=False,
  )
  
  sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
  work_item_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
  description_template: Mapped[str] = mapped_column(String(500), nullable=False)  
  unit: Mapped[str] = mapped_column(String(20), nullable=False)
  
  quantity_formula_code: Mapped[str] = mapped_column(String(80), nullable=False)
  output_unit: Mapped[str] = mapped_column(String(20), nullable=False) 
 
  quantity_factor: Mapped[Decimal | None] = mapped_column(
    Numeric(12, 6), nullable=True, default=Decimal("1.0"), server_default="1.0",
  )
  quantity_formula: Mapped[str | None] = mapped_column(String(300), nullable=True)
 
  category: Mapped[str | None] = mapped_column(String(150), nullable=True)
 
  item_type: Mapped[str] = mapped_column(
    String(20),
    nullable=False, 
    default=BOQItemType.MATERIAL.value,
  )
 
  waste_factor: Mapped[Decimal] = mapped_column(
    Numeric(8, 4),
    nullable=False,
    default=Decimal("1.0"),
  )
  
  is_optional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
 
  recipe: Mapped["AssemblyRecipe"] = relationship("AssemblyRecipe", back_populates="components")

class ModelAuditResult(Base, TimestampMixin):
  __tablename__ = "model_audit_results"
  __table_args__ = (Index("ix_model_audit_results_drawing", "drawing_id"),)
  
  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  
  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id",
      ondelete="CASCADE"),
      nullable=False,
      index=True,
    )
  
  drawing_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True), 
    ForeignKey("drawings.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  overall_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False) 
  issues: Mapped[list] = mapped_column(JSON, nullable=False, default=list)  
  element_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
  missing_material_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
  zero_quantity_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
  unclassified_proxy_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
  extra_stats: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
  
class CalculationRun(Base, TimestampMixin):
  __tablename__ = "calculation_runs"
  
  __table_args__ = (
    UniqueConstraint("id", "organization_id", name="uq_calculation_runs_id_org"),
    Index("ix_calculation_runs_org_project_status", "organization_id", "project_id", "status"),
    
    Index(
      "uq_calculation_runs_completed_fingerprint", "organization_id", "fingerprint",
      unique=True, postgresql_where=text("status = 'COMPLETED'"),
    ),
  
    Index(
      "uq_calculation_runs_active_project", "project_id",
      unique=True, postgresql_where=text(f"status IN ({_ACTIVE_RUN_STATUSES})"),
    ),
    
    CheckConstraint(f"status IN ({_RUN_STATUSES})", name="ck_calculation_runs_status"),
    CheckConstraint("progress_pct >= 0 AND progress_pct <= 100", name="ck_calculation_runs_progress"),
  )
 
  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
 
  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  project_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("projects.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  requested_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )
 
  rule_set_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("measurement_rule_sets.id", name="fk_calculation_runs_rule_set_id"),
    nullable=False,
  )
  
  convention_code: Mapped[str | None] = mapped_column(String(80), nullable=True)  
 
  drawing_revision_ids: Mapped[list[UUID]] = mapped_column(
    ARRAY(PGUUID(as_uuid=True)),
    nullable=False,
    default=list,
    server_default=text("'{}'::uuid[]"),
  )
 
  engine_version: Mapped[str] = mapped_column(String(30), nullable=False)  
  fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)     
 
  status: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default=CalculationRunStatus.QUEUED.value, server_default="QUEUED",
  )
  progress_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
  started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  error_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
  error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
 
  settings: Mapped[dict] = mapped_column(
    JSONB,
    nullable=False,
    default=dict,
    server_default=text("'{}'::jsonb"),
  )
  
  stats: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
  
class RunStageLog(Base, TimestampMixin):
  __tablename__ = "run_stage_log"
  
  __table_args__ = (
    UniqueConstraint("run_id", "stage", name="uq_run_stage_log_run_stage"),
    ForeignKeyConstraint(
      ["run_id", "organization_id"], ["calculation_runs.id", "calculation_runs.organization_id"],
      ondelete="CASCADE", name="fk_run_stage_log_run_tenant",
    ),
    
    CheckConstraint("status IN ('PENDING','RUNNING','SUCCEEDED','FAILED','SKIPPED')", name="ck_run_stage_log_status"),
    CheckConstraint("attempt >= 1", name="ck_run_stage_log_attempt"),
  )
 
  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  organization_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  run_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
 
  stage: Mapped[str] = mapped_column(String(40), nullable=False)
  status: Mapped[str] = mapped_column(
    String(20), nullable=False, default=RunStageStatus.PENDING.value, server_default="PENDING",
  )
  attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
  started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  
  counts: Mapped[dict] = mapped_column(
    JSONB,
    nullable=False,
    default=dict, server_default=text("'{}'::jsonb"),
  )
  
  error: Mapped[str | None] = mapped_column(Text, nullable=True)
 
class _SolidColumns:
  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  organization_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  run_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
 
  element_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("drawing_elements.id", ondelete="SET NULL"),
    nullable=True,
  )
  
  level_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("building_levels.id", ondelete="SET NULL"),
    nullable=True,
  )
 
  role: Mapped[str] = mapped_column(String(30), nullable=False, default="UNKNOWN")   
  component_type: Mapped[str] = mapped_column(String(30), nullable=False, default="BODY")  
  
  geometry_kind: Mapped[str] = mapped_column(String(20), nullable=False)
  material_grade: Mapped[str | None] = mapped_column(String(50), nullable=True)
 
  gross_volume_m3: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
  gross_area_m2: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
  gross_length_m: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
  count: Mapped[int | None] = mapped_column(Integer, nullable=True)
 
  status: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default=SolidStatus.OK.value, server_default="OK",
  )
  
  issues: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
  engine_version: Mapped[str] = mapped_column(String(30), nullable=False)
  
class QuantitySolid(_SolidColumns, Base, TimestampMixin):
  __tablename__ = "quantity_solids"
  
  __table_args__ = (
    UniqueConstraint("id", "organization_id", name="uq_quantity_solids_id_org"),
    UniqueConstraint("run_id", "element_id", "component_type", name="uq_quantity_solids_run_element_component"),
    
    ForeignKeyConstraint(
      ["run_id", "organization_id"], ["calculation_runs.id", "calculation_runs.organization_id"],
      ondelete="CASCADE", name="fk_quantity_solids_run_tenant",
    ),
    
    Index("ix_quantity_solids_run_level", "run_id", "level_id"),
    Index("ix_quantity_solids_element", "element_id"),
    CheckConstraint(f"status IN ({_SOLID_STATUSES})", name="ck_quantity_solids_status"),
    CheckConstraint(f"geometry_kind IN ({_GEOMETRY_KINDS})", name="ck_quantity_solids_geometry_kind"),
    CheckConstraint(
      "(gross_volume_m3 IS NULL OR gross_volume_m3 >= 0) AND (gross_area_m2 IS NULL OR gross_area_m2 >= 0) "
      "AND (gross_length_m IS NULL OR gross_length_m >= 0) AND (count IS NULL OR count >= 0)",
      name="ck_quantity_solids_non_negative",
    ),
  )
  
class StagedQuantitySolid(_SolidColumns, Base, TimestampMixin):
  __tablename__ = "staged_quantity_solids"
  
  __table_args__ = (
    UniqueConstraint("id", "organization_id", name="uq_staged_quantity_solids_id_org"),
    ForeignKeyConstraint(
      ["run_id", "organization_id"], ["calculation_runs.id", "calculation_runs.organization_id"],
      ondelete="CASCADE", name="fk_staged_quantity_solids_run_tenant",
    ),
    
    Index("ix_staged_quantity_solids_run_stage", "run_id", "stage"),
    CheckConstraint(f"status IN ({_SOLID_STATUSES})", name="ck_staged_quantity_solids_status"),
    CheckConstraint(f"geometry_kind IN ({_GEOMETRY_KINDS})", name="ck_staged_quantity_solids_geometry_kind"),
  )
 
  stage: Mapped[str] = mapped_column(String(40), nullable=False) 
  
class _LedgerColumns:
  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  organization_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  run_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  solid_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
 
  element_id: Mapped[UUID | None] = mapped_column(  
    PGUUID(as_uuid=True),
    ForeignKey("drawing_elements.id", ondelete="SET NULL"),
    nullable=True,
  )
  
  level_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("building_levels.id", ondelete="SET NULL"),
    nullable=True,
  )
 
  work_item_code: Mapped[str] = mapped_column(String(50), nullable=False)  
  quantity_net: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
  unit: Mapped[str] = mapped_column(String(20), nullable=False)             
  material_grade: Mapped[str | None] = mapped_column(String(50), nullable=True)
 
  source_kind: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default=LedgerSourceKind.MODEL.value, server_default="MODEL",
  )
  
  confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("1"))
  formula_code: Mapped[str] = mapped_column(String(80), nullable=False)
  
  trace: Mapped[dict] = mapped_column(
    JSONB,
    nullable=False, 
    default=dict, server_default=text("'{}'::jsonb"),
  )
  
  warnings: Mapped[list] = mapped_column(
    JSONB,
    nullable=False, default=list, server_default=text("'[]'::jsonb"),
  )
  
  engine_version: Mapped[str] = mapped_column(String(30), nullable=False)
  
class QuantityLedger(_LedgerColumns, Base, TimestampMixin):
  __tablename__ = "quantity_ledger"
  
  __table_args__ = (
    UniqueConstraint("id", "organization_id", name="uq_quantity_ledger_id_org"),
    UniqueConstraint("run_id", "solid_id", "work_item_code", name="uq_quantity_ledger_run_solid_work_item"),
    
    ForeignKeyConstraint(
      ["run_id", "organization_id"], ["calculation_runs.id", "calculation_runs.organization_id"],
      ondelete="CASCADE", name="fk_quantity_ledger_run_tenant",
    ),
    
    ForeignKeyConstraint(
      ["solid_id", "organization_id"], ["quantity_solids.id", "quantity_solids.organization_id"],
      ondelete="CASCADE", name="fk_quantity_ledger_solid_tenant",
    ),
    
    Index("ix_quantity_ledger_run_work_item_level", "run_id", "work_item_code", "level_id"),
    Index("ix_quantity_ledger_run_solid", "run_id", "solid_id"),
    
    CheckConstraint("quantity_net >= 0", name="ck_quantity_ledger_non_negative"),  
    CheckConstraint(f"unit IN ({_CANONICAL_UNITS})", name="ck_quantity_ledger_unit"),  
    CheckConstraint(f"source_kind IN ({_LEDGER_SOURCES})", name="ck_quantity_ledger_source_kind"),
    CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_quantity_ledger_confidence"),
  )
  
class StagedQuantityLedger(_LedgerColumns, Base, TimestampMixin):
 
  __tablename__ = "staged_quantity_ledger"

  __table_args__ = (
  UniqueConstraint("run_id", "solid_id", "work_item_code", name="uq_staged_quantity_ledger_run_solid_work_item"),
    
  ForeignKeyConstraint(
    ["run_id", "organization_id"], ["calculation_runs.id", "calculation_runs.organization_id"],
      ondelete="CASCADE", name="fk_staged_quantity_ledger_run_tenant",
    ),
    
  ForeignKeyConstraint(
    ["solid_id", "organization_id"], ["staged_quantity_solids.id", "staged_quantity_solids.organization_id"],
      ondelete="CASCADE", name="fk_staged_quantity_ledger_solid_tenant",
    ),
    
    Index("ix_staged_quantity_ledger_run_stage", "run_id", "stage"),
    CheckConstraint("quantity_net >= 0", name="ck_staged_quantity_ledger_non_negative"),
    CheckConstraint(f"unit IN ({_CANONICAL_UNITS})", name="ck_staged_quantity_ledger_unit"),
    )
 
  stage: Mapped[str] = mapped_column(String(40), nullable=False)