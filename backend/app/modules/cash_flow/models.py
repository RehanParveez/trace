from __future__ import annotations
from app.core.database import Base
from app.shared.mixins import TimestampMixin
from sqlalchemy import UniqueConstraint, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid

class CashFlowSettings(Base, TimestampMixin):
  __tablename__ = "cash_flow_settings"
  __table_args__ = (UniqueConstraint("organization_id", name="uq_cash_flow_settings_org"),)

  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  
  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False,
  )

  procurement_payment_days: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
  subcontractor_payment_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
  client_collection_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
  labour_lookback_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)