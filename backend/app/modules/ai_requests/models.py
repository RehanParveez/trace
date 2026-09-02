from __future__ import annotations
import enum
import uuid
from datetime import datetime
from uuid import UUID
from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class AIRequestPurpose(str, enum.Enum):
  MATERIAL_NORMALIZATION = "MATERIAL_NORMALIZATION"
  CAPTION_PARSING = "CAPTION_PARSING"
  PHOTO_TAGGING = "PHOTO_TAGGING"

class AIEntityType(str, enum.Enum):
  DRAWING_ELEMENT = "DRAWING_ELEMENT"
  SITE_PHOTO = "SITE_PHOTO"
  WHATSAPP_MESSAGE = "WHATSAPP_MESSAGE"

class AIProvider(str, enum.Enum):
  OLLAMA = "OLLAMA"
  ANTHROPIC = "ANTHROPIC"

class AIResponseStatus(str, enum.Enum):
  SUCCEEDED = "SUCCEEDED"
  FAILED = "FAILED"

class AIRequest(Base):
  __tablename__ = "ai_requests"

  __table_args__ = (
    Index(
      "ix_ai_requests_org_created",
      "organization_id",
      "created_at",
    ),
    Index(
      "ix_ai_requests_org_purpose",
      "organization_id",
      "purpose",
    ),
    Index(
      "ix_ai_requests_entity",
      "entity_type",
      "entity_id",
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

  purpose: Mapped[AIRequestPurpose] = mapped_column(
    Enum(AIRequestPurpose, name="ai_request_purpose"),
    nullable=False,
    index=True,
  )

  entity_type: Mapped[AIEntityType | None] = mapped_column(
    Enum(AIEntityType, name="ai_entity_type"),
    nullable=True,
  )

  entity_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    nullable=True,
  )

  provider: Mapped[AIProvider] = mapped_column(
    Enum(AIProvider, name="ai_provider"),
    nullable=False,
  )

  model: Mapped[str] = mapped_column(
    String(100),
    nullable=False,
  )

  prompt_text: Mapped[str] = mapped_column(
    Text,
    nullable=False,
  )

  requested_by: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
  )

  created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    server_default=func.now(),
    nullable=False,
  )

  response: Mapped["AIResponse | None"] = relationship(
    "AIResponse",
    back_populates="request",
    uselist=False,
    cascade="all, delete-orphan",
  )

class AIResponse(Base):
  __tablename__ = "ai_responses"

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4,
  )

  ai_request_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("ai_requests.id", ondelete="CASCADE"),
    nullable=False,
    unique=True,
  )

  status: Mapped[AIResponseStatus] = mapped_column(
    Enum(AIResponseStatus, name="ai_response_status"),
    nullable=False,
    index=True,
  )

  raw_response: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
  )

  parsed_output: Mapped[dict | None] = mapped_column(
    JSON,
    nullable=True,
  )

  error_message: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
  )

  latency_ms: Mapped[int | None] = mapped_column(
    Integer,
    nullable=True,
  )

  created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    server_default=func.now(),
    nullable=False,
  )

  request: Mapped["AIRequest"] = relationship(
    "AIRequest",
    back_populates="response",
  )