from __future__ import annotations
import enum
import uuid
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.shared.mixins import TimestampMixin

class DrawingFormat(str, enum.Enum):
  IFC = "IFC"
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