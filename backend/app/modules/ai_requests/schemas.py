from __future__ import annotations
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.modules.ai_requests.models import AIEntityType, AIProvider, AIRequestPurpose, AIResponseStatus

class AIResponseSummary(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  status: AIResponseStatus
  parsed_output: dict | None
  error_message: str | None
  latency_ms: int | None

class AIRequestResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  purpose: AIRequestPurpose
  entity_type: AIEntityType | None
  entity_id: UUID | None
  provider: AIProvider
  model: str
  requested_by: UUID | None
  created_at: datetime
  response: AIResponseSummary | None

class AIUsageSummaryResponse(BaseModel):
  total_requests: int
  succeeded: int
  failed: int
  average_latency_ms: float | None