from __future__ import annotations
from app.core.database import Base
from app.shared.mixins import TimestampMixin
from sqlalchemy import UniqueConstraint, CheckConstraint, Index, BigInteger, Boolean, Date, DateTime, ForeignKey, ForeignKeyConstraint, Integer, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from decimal import Decimal
from uuid import UUID
import uuid
from datetime import date, datetime
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID

IMPORT_STATUSES = ("UPLOADED", "PARSING", "REVIEW", "PUBLISHED", "FAILED", "CANCELLED")
_STATUS_SQL = ",".join(f"'{s}'" for s in IMPORT_STATUSES)

class RateImport(Base, TimestampMixin):
  __tablename__ = "rate_imports"
  __table_args__ = (
    UniqueConstraint("id", "organization_id", name="uq_rate_imports_id_org"),
    Index("ix_rate_imports_org_created", "organization_id", "created_at"),
    Index("ix_rate_imports_org_hash", "organization_id", "content_hash"),
    CheckConstraint(f"status IN ({_STATUS_SQL})", name="ck_rate_imports_status"),
    CheckConstraint("source_kind IN ('PDF','CSV')", name="ck_rate_imports_kind"),
    CheckConstraint("file_size >= 0", name="ck_rate_imports_size"),
  )

  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  organization_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
  created_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

  status: Mapped[str] = mapped_column(String(12), nullable=False, default="UPLOADED", server_default="UPLOADED")
  source_kind: Mapped[str] = mapped_column(String(4), nullable=False)
  filename: Mapped[str] = mapped_column(String(255), nullable=False)
  storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
  file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default=text("0"))
  content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

  layout_profile: Mapped[str] = mapped_column(String(40), nullable=False, default="GENERIC", server_default="GENERIC")
  first_page: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
  last_page: Mapped[int | None] = mapped_column(Integer, nullable=True)

  book_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
  book_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
  edition: Mapped[str | None] = mapped_column(String(50), nullable=True)
  jurisdiction: Mapped[str | None] = mapped_column(String(50), nullable=True)
  province: Mapped[str | None] = mapped_column(String(50), nullable=True)
  city: Mapped[str | None] = mapped_column(String(100), nullable=True)
  currency: Mapped[str] = mapped_column(String(3), nullable=False, default="PKR", server_default="PKR")
  effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
  effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)

  page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
  row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
  report: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
  sample_seq: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
  error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
  parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

  rate_book_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("rate_books.id", ondelete="SET NULL"), nullable=True)
  published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
  published_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

class RateImportRow(Base, TimestampMixin):
  __tablename__ = "rate_import_rows"
  __table_args__ = (
    UniqueConstraint("import_id", "seq", name="uq_rate_import_rows_seq"),
    ForeignKeyConstraint(["import_id", "organization_id"], ["rate_imports.id", "rate_imports.organization_id"],
      ondelete="CASCADE", name="fk_rate_import_rows_import_tenant"),
    Index("ix_rate_import_rows_import_review", "import_id", "needs_review"),
    Index("ix_rate_import_rows_import_code", "import_id", "work_item_code"),
    Index("ix_rate_import_rows_org", "organization_id"),
    CheckConstraint("basis_qty > 0", name="ck_rate_import_rows_basis"),
    CheckConstraint("mapping_source IS NULL OR mapping_source IN ('SUGGESTED','MANUAL','CSR_REF')", name="ck_rate_import_rows_mapping_source"),
  )

  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  import_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
  organization_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
  seq: Mapped[int] = mapped_column(Integer, nullable=False)

  page: Mapped[int | None] = mapped_column(Integer, nullable=True)
  line_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
  chapter: Mapped[str | None] = mapped_column(String(200), nullable=True)
  item_no: Mapped[str | None] = mapped_column(String(60), nullable=True)
  description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
  raw_line: Mapped[str | None] = mapped_column(Text, nullable=True)

  unit_raw: Mapped[str | None] = mapped_column(String(60), nullable=True)
  basis_qty: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("1"), server_default=text("1"))
  unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
  unit_known: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
  rate_raw: Mapped[str | None] = mapped_column(String(60), nullable=True)
  rate: Mapped[Decimal | None] = mapped_column(Numeric(16, 4), nullable=True)
  rate_alt: Mapped[Decimal | None] = mapped_column(Numeric(16, 4), nullable=True)
  unit_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
  spec_key: Mapped[str | None] = mapped_column(String(80), nullable=True)       
  labour: Mapped[Decimal | None] = mapped_column(Numeric(16, 4), nullable=True)  
  rate_kind: Mapped[str | None] = mapped_column(String(12), nullable=True)       

  flags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
  needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
  reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
  skipped: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
  edited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
  original: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
  note: Mapped[str | None] = mapped_column(Text, nullable=True)

  work_item_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
  mapping_source: Mapped[str | None] = mapped_column(String(10), nullable=True)
  suggestions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))

  is_sample: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
  sample_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
