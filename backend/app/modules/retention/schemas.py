from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.modules.retention.models import RetentionHolderType
from uuid import UUID
from decimal import Decimal
from datetime import date, datetime

class RetentionReleaseCreateRequest(BaseModel):
  holder_type: RetentionHolderType
  project_id: UUID
  boq_version_id: UUID | None = None
  agreement_id: UUID | None = None
  amount: Decimal = Field(gt=0)
  release_date: date
  is_final_release: bool = False
  notes: str | None = None

  @model_validator(mode="after")
  def _validate_reference(self) -> "RetentionReleaseCreateRequest":
    if self.holder_type == RetentionHolderType.CLIENT:
      if self.boq_version_id is None:
        raise ValueError("boq_version_id is required when releasing client-held retention.")
      if self.agreement_id is not None:
        raise ValueError("agreement_id must not be set for client-held retention.")
    else:
      if self.agreement_id is None:
        raise ValueError("agreement_id is required when releasing subcontractor retention.")
      if self.boq_version_id is not None:
        raise ValueError("boq_version_id must not be set for subcontractor retention.")
    return self

class RetentionReleaseResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  project_id: UUID
  holder_type: RetentionHolderType
  boq_version_id: UUID | None
  agreement_id: UUID | None
  amount: Decimal
  release_date: date
  is_final_release: bool
  notes: str | None
  created_at: datetime

class ClientRetentionLineResponse(BaseModel):
  boq_version_id: UUID
  boq_version_label: str
  retention_held: Decimal
  retention_released: Decimal
  retention_outstanding: Decimal

class SubcontractorRetentionLineResponse(BaseModel):
  agreement_id: UUID
  subcontractor_name: str
  retention_held: Decimal
  retention_released: Decimal
  retention_outstanding: Decimal

class ProjectRetentionSummaryResponse(BaseModel):
  project_id: UUID
  client_lines: list[ClientRetentionLineResponse]
  client_total_outstanding: Decimal
  subcontractor_lines: list[SubcontractorRetentionLineResponse]
  subcontractor_total_outstanding: Decimal
  currency: str

class OrganizationRetentionSummaryResponse(BaseModel):
  client_retention_held: Decimal
  subcontractor_retention_held: Decimal
  currency: str