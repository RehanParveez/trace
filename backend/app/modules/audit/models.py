from __future__ import annotations
import enum
import uuid
from datetime import datetime
from uuid import UUID
from sqlalchemy import DateTime, Enum, ForeignKey, Index, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.modules.identity.models import User

class AuditEntityType(str, enum.Enum):
  ORGANIZATION = "ORGANIZATION"
  ROLE = "ROLE"
  MEMBER = "MEMBER"
  INVITATION = "INVITATION"
  SUBSCRIPTION = "SUBSCRIPTION"
  PROJECT = "PROJECT"
  BOQ_ITEM = "BOQ_ITEM"
  DRAWING = "DRAWING"
  PROGRESS_CLAIM = "PROGRESS_CLAIM"
  WHATSAPP_CHANNEL = "WHATSAPP_CHANNEL"
  MATERIAL_LIBRARY = "MATERIAL_LIBRARY"

class AuditAction(str, enum.Enum):
  CREATE = "CREATE"
  UPDATE = "UPDATE"
  DELETE = "DELETE"
  APPROVE = "APPROVE"
  REJECT = "REJECT"
  STATUS_CHANGE = "STATUS_CHANGE"

class AuditLog(Base):
  __tablename__ = "audit_log"

  __table_args__ = (
    Index(
      "ix_audit_log_org_created",
      "organization_id",
      "created_at",
    ),
    Index(
      "ix_audit_log_entity",
      "entity_type",
      "entity_id",
    ),
    Index(
      "ix_audit_log_actor",
      "actor_user_id",
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

  actor_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )

  entity_type: Mapped[AuditEntityType] = mapped_column(
    Enum(AuditEntityType, name="audit_entity_type"),
    nullable=False,
    index=True,
  )

  entity_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    nullable=True,
  )

  action: Mapped[AuditAction] = mapped_column(
    Enum(AuditAction, name="audit_action"),
    nullable=False,
    index=True,
  )

  summary: Mapped[str] = mapped_column(
    String(500),
    nullable=False,
  )

  changes: Mapped[dict] = mapped_column(
    JSON,
    nullable=False,
    default=dict,
  )

  ip_address: Mapped[str | None] = mapped_column(
    String(64),
    nullable=True,
  )

  created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    server_default=func.now(),
    nullable=False,
  )

  actor: Mapped["User | None"] = relationship(
    "User",
    foreign_keys=[actor_user_id],
    lazy="joined",
  )

  @property
  def actor_email(self) -> str | None:
    return self.actor.email if self.actor is not None else None

  @property
  def actor_name(self) -> str | None:
    if self.actor is None:
      return None
    return f"{self.actor.first_name} {self.actor.last_name}".strip()