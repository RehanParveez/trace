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
  
class DeductionType(str, enum.Enum):
  OVERLAP_ALLOCATION = "OVERLAP_ALLOCATION"
  EXTENT_TRIMMING = "EXTENT_TRIMMING"
  VOID_DEDUCTION = "VOID_DEDUCTION"
  MATERIAL_SUBSTITUTION = "MATERIAL_SUBSTITUTION"
  MEASUREMENT_CONVENTION = "MEASUREMENT_CONVENTION"
  
class BOQLifecycle(str, enum.Enum):
  DRAFT = "DRAFT"
  CALCULATING = "CALCULATING"
  CALCULATED = "CALCULATED"
  UNDER_REVIEW = "UNDER_REVIEW"
  APPROVED = "APPROVED"
  ISSUED = "ISSUED"
  SUPERSEDED = "SUPERSEDED"
  ARCHIVED = "ARCHIVED"

class BOQVersionOrigin(str, enum.Enum):
  LEGACY = "LEGACY"
  MANUAL = "MANUAL"
  ENGINE = "ENGINE"

class BOQItemSourceKind(str, enum.Enum):
  LEGACY = "LEGACY"
  MODEL = "MODEL"
  SCHEDULE_IMPORT = "SCHEDULE_IMPORT"
  MANUAL = "MANUAL"
  ESTIMATE = "ESTIMATE"

class ItemReviewStatus(str, enum.Enum):
  OK = "OK"
  REVIEW_REQUIRED = "REVIEW_REQUIRED"
  WAIVED = "WAIVED"

class AdjustmentKind(str, enum.Enum):
  DELTA = "DELTA"
  REPLACE = "REPLACE"

class ReviewSeverity(str, enum.Enum):
  ERROR = "error"
  WARNING = "warning"
  INFO = "info"

class ReviewBlocks(str, enum.Enum):
  NONE = "NONE"
  APPROVAL = "APPROVAL"
  ISSUE = "ISSUE"

class ReviewStatus(str, enum.Enum):
  OPEN = "OPEN"
  RESOLVED = "RESOLVED"
  WAIVED = "WAIVED"

class SnapshotPurpose(str, enum.Enum):
  APPROVAL = "APPROVAL"
  ISSUE = "ISSUE"
  MANUAL = "MANUAL"

class ExportKind(str, enum.Enum):
  CONTRACT_BOQ = "CONTRACT_BOQ"
  PROCUREMENT = "PROCUREMENT"
  MEASUREMENT_BOOK = "MEASUREMENT_BOOK"
  AUDIT_REPORT = "AUDIT_REPORT"
  REVISION_COMPARISON = "REVISION_COMPARISON"
  BBS = "BBS"

class ExportStatus(str, enum.Enum):
  QUEUED = "QUEUED"
  RUNNING = "RUNNING"
  SUCCEEDED = "SUCCEEDED"
  FAILED = "FAILED" 
  
class SpaceSource(str, enum.Enum):
  IFC = "IFC"
  MANUAL = "MANUAL"
 
class FinishSurface(str, enum.Enum):
  FLOOR = "FLOOR"
  WALL = "WALL"
  CEILING = "CEILING"
  SKIRTING = "SKIRTING"
  DADO = "DADO"
 
class FinishSource(str, enum.Enum):
  IFC_PSET = "IFC_PSET"
  SCHEDULE_IMPORT = "SCHEDULE_IMPORT"
  MANUAL = "MANUAL"
  RULE_DEFAULT = "RULE_DEFAULT"
 
class RelationKind(str, enum.Enum):
  HOSTED_IN = "HOSTED_IN"
  SUPPORTS = "SUPPORTS"
  CONNECTS = "CONNECTS"
  ADJACENT = "ADJACENT"
 
class RelationSource(str, enum.Enum):
  IFC = "IFC"
  DERIVED = "DERIVED"
 
class BoundaryKind(str, enum.Enum):
  PHYSICAL = "PHYSICAL"
  VIRTUAL = "VIRTUAL"
 
class BoundarySide(str, enum.Enum):
  INTERNAL = "INTERNAL"
  EXTERNAL = "EXTERNAL"
  UNDEFINED = "UNDEFINED"
 
class ScheduleKind(str, enum.Enum):
  DOOR = "DOOR"
  WINDOW = "WINDOW"
  FINISH = "FINISH"
  FIXTURE = "FIXTURE"
  GENERAL = "GENERAL"
 
class ScheduleSource(str, enum.Enum):
  PDF_AI = "PDF_AI"
  PDF_TEXT = "PDF_TEXT"
  CSV = "CSV"
  MANUAL = "MANUAL"
 
class ScheduleImportStatus(str, enum.Enum):
  PENDING_REVIEW = "PENDING_REVIEW"
  CONFIRMED = "CONFIRMED"
  REJECTED = "REJECTED"
  ARCHIVED = "ARCHIVED"
 
class ScheduleRowStatus(str, enum.Enum):
  PENDING = "PENDING"
  CONFIRMED = "CONFIRMED"
  REJECTED = "REJECTED"
 
class LedgerReviewStatus(str, enum.Enum):
  OK = "OK"
  REVIEW_REQUIRED = "REVIEW_REQUIRED"       
 
_RUN_STATUSES = "'QUEUED','RUNNING','STAGED','PROMOTED','COMPLETED','FAILED','CANCELLED','SUPERSEDED'"
_ACTIVE_RUN_STATUSES = "'QUEUED','RUNNING','STAGED','PROMOTED'"
_SOLID_STATUSES = "'OK','REVIEW_REQUIRED','REJECTED'"
_GEOMETRY_KINDS = "'EXTRUDED_PROFILE','AXIS_SWEPT','BOX_ONLY','QTO_ONLY','UNSUPPORTED'"
_LEDGER_SOURCES = "'MODEL','SCHEDULE_IMPORT','MANUAL','ESTIMATE'"
_CANONICAL_UNITS = "'m3','m2','m','kg','nos'"
_DEDUCTION_TYPES = "'OVERLAP_ALLOCATION','EXTENT_TRIMMING','VOID_DEDUCTION','MATERIAL_SUBSTITUTION','MEASUREMENT_CONVENTION'"
_LIFECYCLES = "'DRAFT','CALCULATING','CALCULATED','UNDER_REVIEW','APPROVED','ISSUED','SUPERSEDED','ARCHIVED'"
_VERSION_ORIGINS = "'LEGACY','MANUAL','ENGINE'"
_ITEM_SOURCES = "'LEGACY','MODEL','SCHEDULE_IMPORT','MANUAL','ESTIMATE'"
_ITEM_REVIEW_STATUSES = "'OK','REVIEW_REQUIRED','WAIVED'"
_ADJUSTMENT_KINDS = "'DELTA','REPLACE'"
_REVIEW_SEVERITIES = "'error','warning','info'"
_REVIEW_BLOCKS = "'NONE','APPROVAL','ISSUE'"
_REVIEW_STATUSES = "'OPEN','RESOLVED','WAIVED'"
_SNAPSHOT_PURPOSES = "'APPROVAL','ISSUE','MANUAL'"
_EXPORT_KINDS = "'CONTRACT_BOQ','PROCUREMENT','MEASUREMENT_BOOK','AUDIT_REPORT','REVISION_COMPARISON','BBS'"
_EXPORT_FORMATS = "'PDF','XLSX'"
_EXPORT_STATUSES = "'QUEUED','RUNNING','SUCCEEDED','FAILED'"
_SPACE_SOURCES = "'IFC','MANUAL'"
_FINISH_SURFACES = "'FLOOR','WALL','CEILING','SKIRTING','DADO'"
_FINISH_SOURCES = "'IFC_PSET','SCHEDULE_IMPORT','MANUAL','RULE_DEFAULT'"
_RELATION_KINDS = "'HOSTED_IN','SUPPORTS','CONNECTS','ADJACENT'"
_RELATION_SOURCES = "'IFC','DERIVED'"
_BOUNDARY_KINDS = "'PHYSICAL','VIRTUAL'"
_BOUNDARY_SIDES = "'INTERNAL','EXTERNAL','UNDEFINED'"
_SCHEDULE_KINDS = "'DOOR','WINDOW','FINISH','FIXTURE','GENERAL'"
_SCHEDULE_SOURCES = "'PDF_AI','PDF_TEXT','CSV','MANUAL'"
_IMPORT_STATUSES = "'PENDING_REVIEW','CONFIRMED','REJECTED','ARCHIVED'"
_ROW_STATUSES = "'PENDING','CONFIRMED','REJECTED'"
_LEDGER_REVIEW = "'OK','REVIEW_REQUIRED'"
_NORMALIZATION_STATUSES = "'PENDING','VALID','WARNING','INVALID'"

 
class Drawing(Base, TimestampMixin):
  __tablename__ = "drawings"

  __table_args__ = (
    UniqueConstraint("id", "organization_id", name="uq_drawings_id_org"),
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
    UniqueConstraint("id", "organization_id", name="uq_drawing_elements_id_org"),
    Index("ix_drawing_elements_drawing", "drawing_id"),
    Index("ix_drawing_elements_org_drawing_type", "organization_id", "drawing_id", "ifc_type"),
    Index("ix_drawing_elements_drawing_level_role", "drawing_id", "level_id", "structural_role"),
    Index("ix_drawing_elements_drawing_status", "drawing_id", "normalization_status"),
    Index("ix_drawing_elements_drawing_type_mark", "drawing_id", "type_mark"),
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
  type_mark: Mapped[str | None] = mapped_column(String(100), nullable=True)
  type_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

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
   UniqueConstraint("id", "organization_id", name="uq_boq_versions_id_org"),
   Index("ix_boq_versions_org_project", "organization_id", "project_id"),
   Index("ix_boq_versions_project_lifecycle", "project_id", "lifecycle"),
   
   Index(
    "uq_boq_versions_project_approved_engine", "project_id",
    unique=True,
    postgresql_where=text("origin = 'ENGINE' AND lifecycle IN ('APPROVED','ISSUED')"),
  ),
   
    ForeignKeyConstraint(
      ["calculation_run_id", "organization_id"],
      ["calculation_runs.id", "calculation_runs.organization_id"],
      name="fk_boq_versions_calculation_run_tenant",
    ),
    
    CheckConstraint(f"lifecycle IN ({_LIFECYCLES})", name="ck_boq_versions_lifecycle"),
    CheckConstraint(f"origin IN ({_VERSION_ORIGINS})", name="ck_boq_versions_origin"),
    
    CheckConstraint(
      "lifecycle <> 'ISSUED' OR snapshot_id IS NOT NULL",
      name="ck_boq_versions_issued_has_snapshot",
    ),
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
  
  lifecycle: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default=BOQLifecycle.DRAFT.value,
    server_default="DRAFT",
  )

  origin: Mapped[str] = mapped_column(
    String(10),
    nullable=False,
    default=BOQVersionOrigin.LEGACY.value,
    server_default="LEGACY",
  )

  calculation_run_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)

  snapshot_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("boq_snapshots.id", ondelete="SET NULL", name="fk_boq_versions_snapshot_id", use_alter=True),
    nullable=True,
  )

  approved_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL", name="fk_boq_versions_approved_by"),
    nullable=True,
  )
  approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

  issued_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL", name="fk_boq_versions_issued_by"),
    nullable=True,
  )
  
  issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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
    UniqueConstraint("id", "organization_id", name="uq_boq_items_id_org"),
    Index("ix_boq_items_version", "boq_version_id"),
    Index("ix_boq_items_org_status", "organization_id", "status"),
    Index("ix_boq_items_org_version_work_item", "organization_id", "boq_version_id", "work_item_code"),
    
    Index(
      "uq_boq_items_version_item_key", "boq_version_id", "item_key",
      unique=True,
      postgresql_where=text("item_key IS NOT NULL"),
    ),
    
    ForeignKeyConstraint(
      ["calculation_run_id", "organization_id"],
      ["calculation_runs.id", "calculation_runs.organization_id"],
      name="fk_boq_items_calculation_run_tenant",
    ),
    
    CheckConstraint(f"source_kind IN ({_ITEM_SOURCES})", name="ck_boq_items_source_kind"),
    CheckConstraint(f"review_status IN ({_ITEM_REVIEW_STATUSES})", name="ck_boq_items_review_status"),
    
    CheckConstraint(
      f"canonical_unit IS NULL OR canonical_unit IN ({_CANONICAL_UNITS})",
      name="ck_boq_items_canonical_unit",
    ),
    
    CheckConstraint("is_manual = (source_kind = 'MANUAL')", name="ck_boq_items_manual_consistent"),
    CheckConstraint("net_quantity IS NULL OR net_quantity >= 0", name="ck_boq_items_net_non_negative"),
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
  
  item_key: Mapped[str | None] = mapped_column(String(300), nullable=True)

  level_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("building_levels.id", ondelete="SET NULL", name="fk_boq_items_level_id"),
    nullable=True,
  )
  material_grade: Mapped[str | None] = mapped_column(String(50), nullable=True)

  canonical_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
  unit_factor: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)

  adjustment_total: Mapped[Decimal] = mapped_column(
    Numeric(18, 4),
    nullable=False, default=Decimal("0"),
    server_default=text("0"),
  )

  review_status: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default=ItemReviewStatus.OK.value,
    server_default="OK",
  )

  source_kind: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default=BOQItemSourceKind.LEGACY.value,
    server_default="LEGACY",
  )
  
  is_manual: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    default=False,
    server_default=text("false"),
  )

  calculation_run_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
  engine_version: Mapped[str | None] = mapped_column(String(30), nullable=True)

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
  
  finish_rules: Mapped[list["FinishRule"]] = relationship(
    "FinishRule",
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
  
class _DeductionColumns:
  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  organization_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  run_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)

  from_solid_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  to_solid_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)

  deduction_type: Mapped[str] = mapped_column(String(30), nullable=False)
  quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
  unit: Mapped[str] = mapped_column(String(20), nullable=False)

  rule_code: Mapped[str] = mapped_column(String(80), nullable=False)
  rule_version: Mapped[str | None] = mapped_column(String(40), nullable=True)

  geometry: Mapped[dict] = mapped_column(
    JSONB,
    nullable=False,
    default=dict,
    server_default=text("'{}'::jsonb"),
  )
  
  explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
  engine_version: Mapped[str] = mapped_column(String(30), nullable=False)

class LedgerDeduction(_DeductionColumns, Base, TimestampMixin):
  __tablename__ = "ledger_deductions"

  __table_args__ = (
    UniqueConstraint("id", "organization_id", name="uq_ledger_deductions_id_org"),

    ForeignKeyConstraint(
      ["run_id", "organization_id"], ["calculation_runs.id", "calculation_runs.organization_id"],
      ondelete="CASCADE", name="fk_ledger_deductions_run_tenant",
    ),
    ForeignKeyConstraint(
      ["from_solid_id", "organization_id"], ["quantity_solids.id", "quantity_solids.organization_id"],
      ondelete="CASCADE", name="fk_ledger_deductions_from_solid_tenant",
    ),
    ForeignKeyConstraint(
      ["to_solid_id", "organization_id"], ["quantity_solids.id", "quantity_solids.organization_id"],
      ondelete="CASCADE", name="fk_ledger_deductions_to_solid_tenant",
    ),

    Index("ix_ledger_deductions_run_from", "run_id", "from_solid_id"),
    Index("ix_ledger_deductions_run_to", "run_id", "to_solid_id"),
    Index("ix_ledger_deductions_run_type", "run_id", "deduction_type"),

    CheckConstraint(f"deduction_type IN ({_DEDUCTION_TYPES})", name="ck_ledger_deductions_type"),
    CheckConstraint("quantity >= 0", name="ck_ledger_deductions_non_negative"),
    CheckConstraint(f"unit IN ({_CANONICAL_UNITS})", name="ck_ledger_deductions_unit"),
    CheckConstraint(
      "to_solid_id IS NULL OR to_solid_id <> from_solid_id",
      name="ck_ledger_deductions_distinct_solids",
    ),
    CheckConstraint(
      "deduction_type <> 'OVERLAP_ALLOCATION' OR to_solid_id IS NOT NULL",
      name="ck_ledger_deductions_overlap_needs_owner",
    ),
  )

class StagedLedgerDeduction(_DeductionColumns, Base, TimestampMixin):
  __tablename__ = "staged_ledger_deductions"

  __table_args__ = (
    ForeignKeyConstraint(
      ["run_id", "organization_id"], ["calculation_runs.id", "calculation_runs.organization_id"],
      ondelete="CASCADE", name="fk_staged_ledger_deductions_run_tenant",
    ),
    ForeignKeyConstraint(
      ["from_solid_id", "organization_id"], ["staged_quantity_solids.id", "staged_quantity_solids.organization_id"],
      ondelete="CASCADE", name="fk_staged_ledger_deductions_from_solid_tenant",
    ),
    ForeignKeyConstraint(
      ["to_solid_id", "organization_id"], ["staged_quantity_solids.id", "staged_quantity_solids.organization_id"],
      ondelete="CASCADE", name="fk_staged_ledger_deductions_to_solid_tenant",
    ),

    Index("ix_staged_ledger_deductions_run_stage", "run_id", "stage"),

    CheckConstraint(f"deduction_type IN ({_DEDUCTION_TYPES})", name="ck_staged_ledger_deductions_type"),
    CheckConstraint("quantity >= 0", name="ck_staged_ledger_deductions_non_negative"),
    CheckConstraint(f"unit IN ({_CANONICAL_UNITS})", name="ck_staged_ledger_deductions_unit"),
    
    CheckConstraint(
      "to_solid_id IS NULL OR to_solid_id <> from_solid_id",
      name="ck_staged_ledger_deductions_distinct_solids",
    ),
    
    CheckConstraint(
      "deduction_type <> 'OVERLAP_ALLOCATION' OR to_solid_id IS NOT NULL",
      name="ck_staged_ledger_deductions_overlap_needs_owner",
    ),
  )

  stage: Mapped[str] = mapped_column(String(40), nullable=False)
  
class BOQItemLedgerLink(Base, TimestampMixin):
  __tablename__ = "boq_item_ledger_links"

  __table_args__ = (
    UniqueConstraint("boq_item_id", "ledger_id", name="uq_boq_item_ledger_links_item_ledger"),
    UniqueConstraint("boq_version_id", "ledger_id", name="uq_boq_item_ledger_links_version_ledger"),
    
    ForeignKeyConstraint(
      ["boq_item_id", "organization_id"], ["boq_items.id", "boq_items.organization_id"],
      ondelete="CASCADE", name="fk_boq_item_ledger_links_item_tenant",
    ),
    
    ForeignKeyConstraint(
      ["boq_version_id", "organization_id"], ["boq_versions.id", "boq_versions.organization_id"],
      ondelete="CASCADE", name="fk_boq_item_ledger_links_version_tenant",
    ),
    
    ForeignKeyConstraint(
      ["ledger_id", "organization_id"], ["quantity_ledger.id", "quantity_ledger.organization_id"],
      ondelete="CASCADE", name="fk_boq_item_ledger_links_ledger_tenant",
    ),
    
    Index("ix_boq_item_ledger_links_ledger", "ledger_id"),
    CheckConstraint("quantity_contributed >= 0", name="ck_boq_item_ledger_links_non_negative"),
  )

  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  organization_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  boq_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  boq_item_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  ledger_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  quantity_contributed: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)

class BOQItemAdjustment(Base, TimestampMixin):
  __tablename__ = "boq_item_adjustments"

  __table_args__ = (
    UniqueConstraint("id", "organization_id", name="uq_boq_item_adjustments_id_org"),
    
    ForeignKeyConstraint(
      ["boq_item_id", "organization_id"], ["boq_items.id", "boq_items.organization_id"],
      ondelete="CASCADE", name="fk_boq_item_adjustments_item_tenant",
    ),
    Index("ix_boq_item_adjustments_item", "boq_item_id"),
    
    Index(
      "uq_boq_item_adjustments_active_replace", "boq_item_id",
      unique=True,
      postgresql_where=text("kind = 'REPLACE' AND revoked_at IS NULL"),
    ),
    
    CheckConstraint(f"kind IN ({_ADJUSTMENT_KINDS})", name="ck_boq_item_adjustments_kind"),
    CheckConstraint("char_length(btrim(reason)) > 0", name="ck_boq_item_adjustments_reason"),
    CheckConstraint("kind <> 'REPLACE' OR value >= 0", name="ck_boq_item_adjustments_replace_non_negative"),
  )

  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  organization_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  boq_item_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)

  kind: Mapped[str] = mapped_column(String(10), nullable=False)
  value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
  reason: Mapped[str] = mapped_column(Text, nullable=False)

  created_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL", name="fk_boq_item_adjustments_created_by"),
    nullable=True,
  )
  
  revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  
  revoked_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL", name="fk_boq_item_adjustments_revoked_by"),
    nullable=True,
  )
  revoke_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

class BOQSnapshot(Base, TimestampMixin):
  __tablename__ = "boq_snapshots"

  __table_args__ = (
    UniqueConstraint("id", "organization_id", name="uq_boq_snapshots_id_org"),
    UniqueConstraint("boq_version_id", "version_no", name="uq_boq_snapshots_version_no"),
    
    ForeignKeyConstraint(
      ["boq_version_id", "organization_id"], ["boq_versions.id", "boq_versions.organization_id"],
      ondelete="CASCADE", name="fk_boq_snapshots_version_tenant",
    ),
    
    ForeignKeyConstraint(
      ["calculation_run_id", "organization_id"],
      ["calculation_runs.id", "calculation_runs.organization_id"],
      name="fk_boq_snapshots_run_tenant",
    ),
    
    Index("ix_boq_snapshots_version", "boq_version_id"),
    CheckConstraint("version_no >= 1", name="ck_boq_snapshots_version_no"),
    CheckConstraint("item_count >= 0", name="ck_boq_snapshots_item_count"),
    CheckConstraint("char_length(content_hash) = 64", name="ck_boq_snapshots_hash_len"),
    CheckConstraint(f"purpose IN ({_SNAPSHOT_PURPOSES})", name="ck_boq_snapshots_purpose"),
  )

  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  organization_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  boq_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
  
  purpose: Mapped[str] = mapped_column(
    String(10),
    nullable=False,
    default=SnapshotPurpose.ISSUE.value,
  )

  content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
  item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
  
  totals: Mapped[dict] = mapped_column(
    JSONB,
    nullable=False,
    default=dict,
    server_default=text("'{}'::jsonb"),
  )

  calculation_run_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
  
  rule_set_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("measurement_rule_sets.id", ondelete="SET NULL", name="fk_boq_snapshots_rule_set_id"),
    nullable=True,
  )
  rule_set_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
  rule_set_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
  convention_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
  engine_version: Mapped[str | None] = mapped_column(String(30), nullable=True)

  note: Mapped[str | None] = mapped_column(Text, nullable=True)
  
  created_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL", name="fk_boq_snapshots_created_by"),
    nullable=True,
  )

class BOQSnapshotItem(Base, TimestampMixin):
  __tablename__ = "boq_snapshot_items"

  __table_args__ = (
    UniqueConstraint("snapshot_id", "line_no", name="uq_boq_snapshot_items_line"),
    
    ForeignKeyConstraint(
      ["snapshot_id", "organization_id"], ["boq_snapshots.id", "boq_snapshots.organization_id"],
      ondelete="CASCADE", name="fk_boq_snapshot_items_snapshot_tenant",
    ),
    
    Index("ix_boq_snapshot_items_snapshot", "snapshot_id"),
    Index("ix_boq_snapshot_items_source", "source_item_id"),
    CheckConstraint("line_no >= 1", name="ck_boq_snapshot_items_line_no"),
  )

  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  organization_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  snapshot_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  line_no: Mapped[int] = mapped_column(Integer, nullable=False)

  source_item_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
  item_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
  work_item_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
  material_name: Mapped[str] = mapped_column(String(300), nullable=False)
  description: Mapped[str | None] = mapped_column(Text, nullable=True)
  category: Mapped[str | None] = mapped_column(String(150), nullable=True)
  item_type: Mapped[str] = mapped_column(String(20), nullable=False)
  level_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
  material_grade: Mapped[str | None] = mapped_column(String(50), nullable=True)

  unit: Mapped[str] = mapped_column(String(20), nullable=False)
  canonical_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
  unit_factor: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)

  net_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
  adjustment_total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
  quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
  waste_factor_applied: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
  gross_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)

  unit_rate: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
  rate_source: Mapped[str | None] = mapped_column(String(20), nullable=True)
  amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)

  confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
  review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="OK")
  source_kind: Mapped[str] = mapped_column(String(20), nullable=False, default="MODEL")
  is_manual: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
  ledger_row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
  ledger_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

class ReviewIssue(Base, TimestampMixin):
  __tablename__ = "review_issues"

  __table_args__ = (
    
    ForeignKeyConstraint(
      ["boq_version_id", "organization_id"], ["boq_versions.id", "boq_versions.organization_id"],
      ondelete="CASCADE", name="fk_review_issues_version_tenant",
    ),
    
    ForeignKeyConstraint(
      ["calculation_run_id", "organization_id"],
      ["calculation_runs.id", "calculation_runs.organization_id"],
      ondelete="CASCADE", name="fk_review_issues_run_tenant",
    ),
    
    ForeignKeyConstraint(
      ["ledger_id", "organization_id"], ["quantity_ledger.id", "quantity_ledger.organization_id"],
      ondelete="CASCADE", name="fk_review_issues_ledger_tenant",
    ),
    
    ForeignKeyConstraint(
      ["boq_item_id", "organization_id"], ["boq_items.id", "boq_items.organization_id"],
      ondelete="CASCADE", name="fk_review_issues_item_tenant",
    ),
    
    ForeignKeyConstraint(
      ["adjustment_id", "organization_id"],
      ["boq_item_adjustments.id", "boq_item_adjustments.organization_id"],
      ondelete="CASCADE", name="fk_review_issues_adjustment_tenant",
    ),
    
    Index("ix_review_issues_org_project_status", "organization_id", "project_id", "status"),
    Index("ix_review_issues_version_status", "boq_version_id", "status"),
    
    Index(
      "ix_review_issues_open_blocking", "boq_version_id",
      postgresql_where=text("status = 'OPEN' AND blocks <> 'NONE'"),
    ),
    
    Index(
      "uq_review_issues_version_dedupe", "boq_version_id", "dedupe_key",
      unique=True, postgresql_where=text("boq_version_id IS NOT NULL"),
    ),
    
    Index(
      "uq_review_issues_project_dedupe", "project_id", "dedupe_key",
      unique=True, postgresql_where=text("boq_version_id IS NULL"),
    ),
    
    CheckConstraint(f"severity IN ({_REVIEW_SEVERITIES})", name="ck_review_issues_severity"),
    CheckConstraint(f"blocks IN ({_REVIEW_BLOCKS})", name="ck_review_issues_blocks"),
    CheckConstraint(f"status IN ({_REVIEW_STATUSES})", name="ck_review_issues_status"),
    CheckConstraint("status = 'OPEN' OR resolved_at IS NOT NULL", name="ck_review_issues_resolved_at"),
    
    CheckConstraint(
      "status <> 'WAIVED' OR char_length(btrim(coalesce(resolution_note, ''))) > 0",
      name="ck_review_issues_waiver_needs_reason",
    ),
    
    CheckConstraint(
      "(CASE WHEN drawing_element_id IS NULL THEN 0 ELSE 1 END) "
      "+ (CASE WHEN ledger_id IS NULL THEN 0 ELSE 1 END) "
      "+ (CASE WHEN boq_item_id IS NULL THEN 0 ELSE 1 END) "
      "+ (CASE WHEN adjustment_id IS NULL THEN 0 ELSE 1 END) <= 1",
      name="ck_review_issues_single_target",
    ),
  )

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4,
  )
  
  organization_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)

  project_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("projects.id", ondelete="CASCADE", name="fk_review_issues_project_id"),
    nullable=False,
  )
  
  boq_version_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
  calculation_run_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)

  drawing_element_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("drawing_elements.id", ondelete="SET NULL", name="fk_review_issues_element_id"),
    nullable=True,
  )
  
  ledger_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
  boq_item_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
  adjustment_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)

  code: Mapped[str] = mapped_column(String(60), nullable=False)
  
  severity: Mapped[str] = mapped_column(
    String(10),
    nullable=False,
    default=ReviewSeverity.WARNING.value,
  )
  
  blocks: Mapped[str] = mapped_column(
    String(10),
    nullable=False,
    default=ReviewBlocks.NONE.value, server_default="NONE",
  )
  
  message: Mapped[str] = mapped_column(Text, nullable=False)
  suggested_fix: Mapped[str | None] = mapped_column(Text, nullable=True)
  
  details: Mapped[dict] = mapped_column(
    JSONB,
    nullable=False,
    default=dict,
    server_default=text("'{}'::jsonb"),
  )
  
  dedupe_key: Mapped[str] = mapped_column(String(200), nullable=False)

  status: Mapped[str] = mapped_column(
    String(10),
    nullable=False,
    default=ReviewStatus.OPEN.value,
    server_default="OPEN",
  )
  
  resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
  
  resolved_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL", name="fk_review_issues_resolved_by"),
    nullable=True,
  )
  
  resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class ExportJob(Base, TimestampMixin):
  __tablename__ = "export_jobs"

  __table_args__ = (
    ForeignKeyConstraint(
      ["boq_version_id", "organization_id"], ["boq_versions.id", "boq_versions.organization_id"],
      ondelete="CASCADE", name="fk_export_jobs_version_tenant",
    ),
    
    ForeignKeyConstraint(
      ["snapshot_id", "organization_id"], ["boq_snapshots.id", "boq_snapshots.organization_id"],
      ondelete="CASCADE", name="fk_export_jobs_snapshot_tenant",
    ),
    
    Index("ix_export_jobs_org_version", "organization_id", "boq_version_id"),
    Index("ix_export_jobs_snapshot", "snapshot_id"),
    CheckConstraint(f"kind IN ({_EXPORT_KINDS})", name="ck_export_jobs_kind"),
    CheckConstraint(f"format IN ({_EXPORT_FORMATS})", name="ck_export_jobs_format"),
    CheckConstraint(f"status IN ({_EXPORT_STATUSES})", name="ck_export_jobs_status"),
  )

  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  organization_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  boq_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  snapshot_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)

  kind: Mapped[str] = mapped_column(String(30), nullable=False)
  format: Mapped[str] = mapped_column(String(10), nullable=False)
  
  status: Mapped[str] = mapped_column(
    String(10),
    nullable=False,
    default=ExportStatus.QUEUED.value,
    server_default="QUEUED",
  )
  
  parameters: Mapped[dict] = mapped_column(
    JSONB,
    nullable=False,
    default=dict,
    server_default=text("'{}'::jsonb"),
  )
  
  requested_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL", name="fk_export_jobs_requested_by"),
    nullable=True,
  )
  
  storage_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)
  file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
  error_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
  error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
  started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  
class BuildingSpace(Base, TimestampMixin):
  __tablename__ = "building_spaces"
 
  __table_args__ = (
    UniqueConstraint("id", "organization_id", name="uq_building_spaces_id_org"),
    UniqueConstraint("drawing_id", "ifc_global_id", name="uq_building_spaces_drawing_global_id"),
    
    ForeignKeyConstraint(
      ["drawing_id", "organization_id"], ["drawings.id", "drawings.organization_id"],
      ondelete="CASCADE", name="fk_building_spaces_drawing_tenant",
    ),
    
    Index("ix_building_spaces_org_project", "organization_id", "project_id"),
    Index("ix_building_spaces_drawing_level", "drawing_id", "level_id"),
    CheckConstraint(f"source IN ({_SPACE_SOURCES})", name="ck_building_spaces_source"),
    
    CheckConstraint(f"geometry_kind IN ({_GEOMETRY_KINDS})", name="ck_building_spaces_geometry_kind"),
    
    CheckConstraint(
      f"normalization_status IN ({_NORMALIZATION_STATUSES})", name="ck_building_spaces_normalization_status",
    ),
    
    CheckConstraint("source <> 'IFC' OR drawing_id IS NOT NULL", name="ck_building_spaces_ifc_has_drawing"),
    
    CheckConstraint(
      "(gross_floor_area_mm2 IS NULL OR gross_floor_area_mm2 >= 0) "
      "AND (net_floor_area_mm2 IS NULL OR net_floor_area_mm2 >= 0) "
      "AND (perimeter_mm IS NULL OR perimeter_mm >= 0) "
      "AND (height_mm IS NULL OR height_mm >= 0)",
      name="ck_building_spaces_non_negative",
    ),
  )
 
  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
 
  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  project_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  drawing_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
  
  level_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True), 
    ForeignKey("building_levels.id", ondelete="SET NULL"),
    nullable=True,
  )
 
  source: Mapped[str] = mapped_column(
    String(10), 
    nullable=False, 
    default=SpaceSource.IFC.value, server_default="IFC",
  )
  
  ifc_global_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
  number: Mapped[str | None] = mapped_column(String(100), nullable=True)
  name: Mapped[str | None] = mapped_column(String(300), nullable=True)
  long_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
  
  category: Mapped[str] = mapped_column(
    String(40),
    nullable=False,
    default="UNKNOWN",
    server_default="UNKNOWN",
  )
  
  usage_text: Mapped[str | None] = mapped_column(String(300), nullable=True)
  
  is_external: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    default=False,
    server_default=text("false"),
  )
  
  is_active: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False, 
    default=True, server_default=text("true"),
  )
 
  gross_floor_area_mm2: Mapped[Decimal | None] = mapped_column(Numeric(20, 3), nullable=True)
  net_floor_area_mm2: Mapped[Decimal | None] = mapped_column(Numeric(20, 3), nullable=True)
  perimeter_mm: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
  height_mm: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
  elevation_base_mm: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
 
  geometry_kind: Mapped[str] = mapped_column(
    String(20), 
    nullable=False,
    default="UNSUPPORTED",
    server_default="UNSUPPORTED",
  )
  
  footprint: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
  
  properties: Mapped[dict] = mapped_column(
    JSONB,
    nullable=False, 
    default=dict,
    server_default=text("'{}'::jsonb"),
  )
  
  normalization_status: Mapped[str] = mapped_column(
    String(10), 
    nullable=False,
    default="VALID",
    server_default="VALID",
  )
  
  normalization_issues: Mapped[list] = mapped_column(
    JSONB,
    nullable=False,
    default=list, 
    server_default=text("'[]'::jsonb"),
  )
 
  created_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"), 
    nullable=True,
  )
 
class SpaceBoundary(Base, TimestampMixin):
  __tablename__ = "space_boundaries"
 
  __table_args__ = (
    UniqueConstraint("space_id", "element_id", name="uq_space_boundaries_space_element"),
    
    ForeignKeyConstraint(
      ["space_id", "organization_id"], ["building_spaces.id", "building_spaces.organization_id"],
      ondelete="CASCADE", name="fk_space_boundaries_space_tenant",
    ),
    
    ForeignKeyConstraint(
      ["element_id", "organization_id"], ["drawing_elements.id", "drawing_elements.organization_id"],
      ondelete="CASCADE", name="fk_space_boundaries_element_tenant",
    ),
    
    Index("ix_space_boundaries_element", "element_id"),
    CheckConstraint(f"boundary_kind IN ({_BOUNDARY_KINDS})", name="ck_space_boundaries_kind"),
    CheckConstraint(f"side IN ({_BOUNDARY_SIDES})", name="ck_space_boundaries_side"),
    CheckConstraint(f"source IN ({_RELATION_SOURCES})", name="ck_space_boundaries_source"),
  )
 
  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  organization_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  space_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  element_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
 
  boundary_kind: Mapped[str] = mapped_column(String(10), nullable=False, default="PHYSICAL", server_default="PHYSICAL")
  side: Mapped[str] = mapped_column(String(10), nullable=False, default="UNDEFINED", server_default="UNDEFINED")
  source: Mapped[str] = mapped_column(String(10), nullable=False, default="IFC", server_default="IFC")
 
class ElementRelation(Base, TimestampMixin):
  __tablename__ = "element_relations"
 
  __table_args__ = (
    UniqueConstraint("from_element_id", "to_element_id", "relation", name="uq_element_relations_pair_kind"),
    ForeignKeyConstraint(
      ["drawing_id", "organization_id"], ["drawings.id", "drawings.organization_id"],
      ondelete="CASCADE", name="fk_element_relations_drawing_tenant",
    ),
    
    ForeignKeyConstraint(
      ["from_element_id", "organization_id"], ["drawing_elements.id", "drawing_elements.organization_id"],
      ondelete="CASCADE", name="fk_element_relations_from_tenant",
    ),
    
    ForeignKeyConstraint(
      ["to_element_id", "organization_id"], ["drawing_elements.id", "drawing_elements.organization_id"],
      ondelete="CASCADE", name="fk_element_relations_to_tenant",
    ),
    
    Index("ix_element_relations_drawing_relation", "drawing_id", "relation"),
    Index("ix_element_relations_to_element", "to_element_id"),
    CheckConstraint(f"relation IN ({_RELATION_KINDS})", name="ck_element_relations_relation"),
    CheckConstraint(f"source IN ({_RELATION_SOURCES})", name="ck_element_relations_source"),
    CheckConstraint("from_element_id <> to_element_id", name="ck_element_relations_distinct"),
  )
 
  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  organization_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  drawing_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  from_element_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  to_element_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
 
  relation: Mapped[str] = mapped_column(String(12), nullable=False)
  
  source: Mapped[str] = mapped_column(
    String(10),
    nullable=False, 
    default="IFC",
    server_default="IFC",
  )
  
  details: Mapped[dict] = mapped_column(
    JSONB,
    nullable=False,
    default=dict,
    server_default=text("'{}'::jsonb"),
  )
 
class ScheduleImport(Base, TimestampMixin):
  __tablename__ = "schedule_imports"
 
  __table_args__ = (
    UniqueConstraint("id", "organization_id", name="uq_schedule_imports_id_org"),
    Index("ix_schedule_imports_org_project", "organization_id", "project_id"),
    
    Index(
      "uq_schedule_imports_project_hash", "project_id", "content_hash",
      unique=True,
      postgresql_where=text("content_hash IS NOT NULL AND status IN ('PENDING_REVIEW','CONFIRMED')"),
    ),
    
    CheckConstraint(f"source IN ({_SCHEDULE_SOURCES})", name="ck_schedule_imports_source"),
    CheckConstraint(f"schedule_kind IN ({_SCHEDULE_KINDS})", name="ck_schedule_imports_kind"),
    CheckConstraint(f"status IN ({_IMPORT_STATUSES})", name="ck_schedule_imports_status"),
    
    CheckConstraint(
      "row_count >= 0 AND confirmed_count >= 0 AND confirmed_count <= row_count",
      name="ck_schedule_imports_counts",
    ),
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
  
  drawing_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("drawings.id", ondelete="SET NULL"),
    nullable=True,
  )
 
  source: Mapped[str] = mapped_column(String(12), nullable=False)
  schedule_kind: Mapped[str] = mapped_column(String(12), nullable=False)
  
  status: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default=ScheduleImportStatus.PENDING_REVIEW.value,
    server_default="PENDING_REVIEW",
  )
  
  file_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
  content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
  
  row_count: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    default=0, server_default=text("0"),
  )
  
  confirmed_count: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    default=0,
    server_default=text("0"),
  )
  
  extraction_meta: Mapped[dict] = mapped_column(
    JSONB,
    nullable=False,
    default=dict,
    server_default=text("'{}'::jsonb"),
  )
  
  notes: Mapped[str | None] = mapped_column(Text, nullable=True)
 
  created_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )
  
  confirmed_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"), 
    nullable=True,
  )
  
  confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
 
class ScheduleRow(Base, TimestampMixin):
  __tablename__ = "schedule_rows"
 
  __table_args__ = (
    UniqueConstraint("schedule_import_id", "row_no", name="uq_schedule_rows_import_row"),
    
    ForeignKeyConstraint(
      ["schedule_import_id", "organization_id"], ["schedule_imports.id", "schedule_imports.organization_id"],
      ondelete="CASCADE", name="fk_schedule_rows_import_tenant",
    ),
    
    Index("ix_schedule_rows_import", "schedule_import_id"),
    Index("ix_schedule_rows_org_status", "organization_id", "review_status"),
    CheckConstraint(f"schedule_kind IN ({_SCHEDULE_KINDS})", name="ck_schedule_rows_kind"),
    CheckConstraint(f"review_status IN ({_ROW_STATUSES})", name="ck_schedule_rows_review_status"),
    
    CheckConstraint(
      f"canonical_unit IS NULL OR canonical_unit IN ({_CANONICAL_UNITS})", name="ck_schedule_rows_canonical_unit",
    ),
    
    CheckConstraint("row_no >= 1", name="ck_schedule_rows_row_no"),
    
    CheckConstraint(
      "(quantity IS NULL OR quantity >= 0) AND (canonical_quantity IS NULL OR canonical_quantity >= 0)",
      name="ck_schedule_rows_non_negative",
    ),
    
    CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_schedule_rows_confidence"),
    
    CheckConstraint(
      "review_status <> 'CONFIRMED' OR (work_item_code IS NOT NULL AND canonical_unit IS NOT NULL "
      "AND canonical_quantity IS NOT NULL)",
      name="ck_schedule_rows_confirmed_is_mapped",
    ),
  )
 
  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  organization_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  schedule_import_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  row_no: Mapped[int] = mapped_column(Integer, nullable=False)
  schedule_kind: Mapped[str] = mapped_column(String(12), nullable=False)
 
  page_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
  raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
  mark: Mapped[str | None] = mapped_column(String(100), nullable=True)
  description: Mapped[str | None] = mapped_column(String(500), nullable=True)
  location_text: Mapped[str | None] = mapped_column(String(300), nullable=True)
  
  level_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("building_levels.id", ondelete="SET NULL"), 
    nullable=True,
  )
  
  space_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("building_spaces.id", ondelete="SET NULL"), 
    nullable=True,
  )
 
  unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
  quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
  width_mm: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
  height_mm: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
 
  work_item_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
  canonical_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
  canonical_quantity: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
 
  confidence: Mapped[Decimal] = mapped_column(
    Numeric(5, 4),
    nullable=False,
    default=Decimal("0.5"), 
    server_default="0.5",
  )
  
  review_status: Mapped[str] = mapped_column(
    String(10),
    nullable=False,
    default=ScheduleRowStatus.PENDING.value,
    server_default="PENDING",
  )
  
  review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
  
  reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )
  
  reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  
  matched_element_count: Mapped[int] = mapped_column(
    Integer, 
    nullable=False,
    default=0, 
    server_default=text("0"),
  )
  
  extra: Mapped[dict] = mapped_column(
    JSONB, 
    nullable=False,
    default=dict,
    server_default=text("'{}'::jsonb"),
  )
 
class SpaceFinish(Base, TimestampMixin):
  __tablename__ = "space_finishes"
 
  __table_args__ = (
    UniqueConstraint("space_id", "surface", "work_item_code", name="uq_space_finishes_space_surface_work_item"),
    
    ForeignKeyConstraint(
      ["space_id", "organization_id"], ["building_spaces.id", "building_spaces.organization_id"],
      ondelete="CASCADE", name="fk_space_finishes_space_tenant",
    ),
    
    Index("ix_space_finishes_space", "space_id"),
    CheckConstraint(f"surface IN ({_FINISH_SURFACES})", name="ck_space_finishes_surface"),
    CheckConstraint(f"source IN ({_FINISH_SOURCES})", name="ck_space_finishes_source"),
    CheckConstraint(f"review_status IN ({_LEDGER_REVIEW})", name="ck_space_finishes_review_status"),
    CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_space_finishes_confidence"),
    CheckConstraint("height_mm IS NULL OR height_mm > 0", name="ck_space_finishes_height"),
  )
 
  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  organization_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  space_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
 
  surface: Mapped[str] = mapped_column(String(12), nullable=False)
  work_item_code: Mapped[str] = mapped_column(String(50), nullable=False)
  finish_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
  height_mm: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
 
  source: Mapped[str] = mapped_column(
    String(20),
    nullable=False, 
    default="MANUAL", 
    server_default="MANUAL",
  )
  
  schedule_row_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("schedule_rows.id", ondelete="SET NULL"), 
    nullable=True,
  )
  
  confidence: Mapped[Decimal] = mapped_column(
    Numeric(5, 4),
    nullable=False,
    default=Decimal("1"),
    server_default="1",
  )
  
  review_status: Mapped[str] = mapped_column(
    String(20), 
    nullable=False,
    default="OK",
    server_default="OK",
  )
  
  is_active: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False, 
    default=True,
    server_default=text("true"),
  )
  
  extra: Mapped[dict] = mapped_column(
    JSONB,
    nullable=False,
    default=dict, 
    server_default=text("'{}'::jsonb"),
  )
  
  created_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )
 
class FinishRule(Base, TimestampMixin):
  __tablename__ = "finish_rules"
 
  __table_args__ = (
    UniqueConstraint(
      "rule_set_id", "space_category", "surface", "work_item_code",
      name="uq_finish_rules_scope_surface_item",
    ),
    
    Index("ix_finish_rules_rule_set", "rule_set_id"),
    CheckConstraint(f"surface IN ({_FINISH_SURFACES})", name="ck_finish_rules_surface"),
    CheckConstraint("height_mm IS NULL OR height_mm > 0", name="ck_finish_rules_height"),
  )
 
  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  
  rule_set_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("measurement_rule_sets.id", ondelete="CASCADE"),
    nullable=False,
  )
 
  space_category: Mapped[str] = mapped_column(
    String(40),
    nullable=False,
    default="ALL",
    server_default="ALL",
  )
  
  surface: Mapped[str] = mapped_column(String(12), nullable=False)
  work_item_code: Mapped[str] = mapped_column(String(50), nullable=False)
  height_mm: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
  
  deduct_openings: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False, 
    default=True,
    server_default=text("true"),
  )
  
  priority: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    default=0,
    server_default=text("0"),
  )
  
  extra_config: Mapped[dict] = mapped_column(
    JSONB,
    nullable=False,
    default=dict,
    server_default=text("'{}'::jsonb"),
  )
 
  rule_set: Mapped["MeasurementRuleSet"] = relationship(
    "MeasurementRuleSet",
    back_populates="finish_rules",
  )