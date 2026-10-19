from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime

class SupportGrantCreateRequest(BaseModel):
  reason: str = Field(min_length=10, max_length=500)
  hours: int = Field(default=24, ge=1, le=72)

class SupportGrantResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  reason: str
  starts_at: datetime
  expires_at: datetime
  revoked_at: datetime | None
  created_at: datetime
  granted_by_user_id: UUID | None
  status: str = "ACTIVE"

class ExportJobResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  status: str
  size_bytes: int | None
  table_count: int | None
  row_count: int | None
  file_count: int | None
  error_message: str | None
  created_at: datetime
  finished_at: datetime | None
  expires_at: datetime | None

class ExportDownloadResponse(BaseModel):
  url: str
  expires_in_seconds: int

class DeletionRequestCreate(BaseModel):
  confirm_name: str = Field(min_length=1, max_length=255)
  reason: str | None = Field(default=None, max_length=1000)

class DeletionRequestResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  status: str
  reason: str | None
  requested_at: datetime
  scheduled_for: datetime
  cancelled_at: datetime | None
  error_message: str | None

class EncryptionStatus(BaseModel):
  enabled: bool
  provider: str
  key_ready: bool
  fields: list[str]

class PrivacyOverviewResponse(BaseModel):
  organization_name: str
  encryption: EncryptionStatus
  active_support_grant: SupportGrantResponse | None
  latest_export: ExportJobResponse | None
  pending_deletion: DeletionRequestResponse | None
  grace_days: int
  support_grant_max_hours: int

class SupportDiagnosticsResponse(BaseModel):
  organization_id: UUID
  grant_expires_at: datetime
  subscription_status: str | None
  table_counts: dict[str, int]
  failed_runs: list[dict]
  failed_exports: list[dict]
