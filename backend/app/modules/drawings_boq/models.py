from __future__ import annotations
import enum
import uuid
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, Boolean, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.shared.mixins import TimestampMixin
from sqlalchemy.dialects.postgresql import UUID as PGUUID

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
    cascade="all, delete-orphan",
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

class DrawingElement(Base, TimestampMixin):
  __tablename__ = "drawing_elements"

  __table_args__ = (
    Index("ix_drawing_elements_drawing", "drawing_id"),
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

  drawing: Mapped["Drawing"] = relationship(
    "Drawing",
    back_populates="elements",
  )

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
    JSON,
    nullable=False,
    default=dict,
    server_default=text("'{}'"),
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
  
  rule_set_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("measurement_rule_sets.id", ondelete="SET NULL"),
    nullable=True,
  )
  
  audit_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
  generation_meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

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
    ForeignKey("measurement_rule_sets.id", ondelete="SET NULL", name="fk_boq_items_rule_set_id"),
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

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4,
  )

  input_hash: Mapped[str] = mapped_column(
    String(64),
    nullable=False,
    unique=True,
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
  
class MeasurementRuleSet(Base, TimestampMixin):
  __tablename__ = "measurement_rule_sets"
  __table_args__ = (
    UniqueConstraint("organization_id", "code", name="uq_measurement_rule_sets_org_code"),
    Index("ix_measurement_rule_sets_org", "organization_id"),
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

class ElementTypeMapping(Base, TimestampMixin):
  __tablename__ = "element_type_mappings"
  __table_args__ = (
    UniqueConstraint("rule_set_id", "ifc_type", name="uq_element_type_mappings_rule_ifc"),
    Index("ix_element_type_mappings_rule", "rule_set_id"),
  )
  
  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  
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

class AssemblyRecipe(Base, TimestampMixin):
  __tablename__ = "assembly_recipes"
  __table_args__ = (
    UniqueConstraint("organization_id", "code", name="uq_assembly_recipes_org_code"),
    Index("ix_assembly_recipes_org", "organization_id"),
  )
  
  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  
  organization_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=True,
    index=True,
  )
  
  code: Mapped[str] = mapped_column(String(80), nullable=False)  
  name: Mapped[str] = mapped_column(String(200), nullable=False)
  description: Mapped[str | None] = mapped_column(Text, nullable=True)
  trigger_ifc_types: Mapped[list] = mapped_column(JSON, nullable=False, default=list)  
  trigger_conditions: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)  
  is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
  is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
  
  components: Mapped[list["AssemblyRecipeComponent"]] = relationship("AssemblyRecipeComponent", back_populates="recipe", cascade="all, delete-orphan")

class AssemblyRecipeComponent(Base, TimestampMixin):
  __tablename__ = "assembly_recipe_components"
  __table_args__ = (Index("ix_assembly_recipe_components_recipe", "recipe_id"),)
  
  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  
  recipe_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True), 
    ForeignKey("assembly_recipes.id", ondelete="SET NULL", name="fk_boq_items_recipe_id"),
    nullable=False,
  )
  
  sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
  work_item_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
  description_template: Mapped[str] = mapped_column(String(500), nullable=False)  
  unit: Mapped[str] = mapped_column(String(20), nullable=False)
  quantity_factor: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False, default=Decimal("1.0"))  
  quantity_formula: Mapped[str | None] = mapped_column(String(300), nullable=True) 
  category: Mapped[str | None] = mapped_column(String(150), nullable=True)
  
  item_type: Mapped[BOQItemType] = mapped_column(
    Enum(BOQItemType, name="boq_item_type"), 
      nullable=False,
      default=BOQItemType.MATERIAL,
    )
  
  waste_factor: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=Decimal("1.0"))
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