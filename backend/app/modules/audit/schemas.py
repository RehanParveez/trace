from __future__ import annotations
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.modules.audit.models import AuditAction, AuditEntityType

class AuditLogResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  actor_user_id: UUID | None
  actor_name: str | None
  actor_email: str | None
  entity_type: AuditEntityType
  entity_id: UUID | None
  action: AuditAction
  summary: str
  changes: dict
  created_at: datetime