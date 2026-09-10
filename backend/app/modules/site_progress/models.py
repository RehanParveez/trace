from __future__ import annotations
from app.core.database import Base
from app.shared.mixins import TimestampMixin
from sqlalchemy import Index, Date, ForeignKey, Integer, String, Text
from uuid import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid
from datetime import date

class SiteLogEntry(Base, TimestampMixin):
  __tablename__ = "site_logs"
  __table_args__ = (
    Index("ix_site_logs_project", "project_id"),
    Index("ix_site_logs_org", "organization_id"),
    Index("ix_site_logs_project_date", "project_id", "log_date"),
  )

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
  )
  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False, index=True,
  )
  project_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("projects.id", ondelete="CASCADE"),
    nullable=False, index=True,
  )
  log_date: Mapped[date] = mapped_column(Date, nullable=False)
  workforce_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
  weather: Mapped[str | None] = mapped_column(String(255), nullable=True)
  blockers: Mapped[str | None] = mapped_column(Text, nullable=True)
  notes: Mapped[str | None] = mapped_column(Text, nullable=True)
  created_by: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )