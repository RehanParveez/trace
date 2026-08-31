from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.modules.verification.models import ProgressClaimStatus

class ProgressClaimCreateRequest(BaseModel):
  project_id: UUID
  boq_item_id: UUID

  claim_date: date

  claimed_quantity: Decimal = Field(
    gt=0,
    max_digits=18,
    decimal_places=4,
  )

  claimed_percentage: Decimal = Field(
    ge=0,
    le=100,
    max_digits=7,
    decimal_places=4,
  )

  notes: str | None = Field(
    default=None,
    max_length=5000,
  )

class ProgressClaimUpdateRequest(BaseModel):
  claimed_quantity: Decimal | None = Field(
    default=None,
    gt=0,
    max_digits=18,
    decimal_places=4,
  )

  claimed_percentage: Decimal | None = Field(
    default=None,
    ge=0,
    le=100,
    max_digits=7,
    decimal_places=4,
  )

  claim_date: date | None = None

  notes: str | None = Field(
    default=None,
    max_length=5000,
  )

  version: int = Field(
    ge=1,
  )

class ProgressClaimReviewRequest(BaseModel):
  version: int = Field(
    ge=1,
  )

  note: str | None = Field(
    default=None,
    max_length=5000,
  )

class ProgressClaimResponse(BaseModel):
  model_config = ConfigDict(
    from_attributes=True,
  )

  id: UUID
  organization_id: UUID
  project_id: UUID
  boq_item_id: UUID
  claim_date: date
  claimed_quantity: Decimal
  claimed_percentage: Decimal
  notes: str | None
  status: ProgressClaimStatus
  submitted_by: UUID | None
  submitted_at: datetime | None
  reviewed_by: UUID | None
  reviewed_at: datetime | None
  review_note: str | None
  version: int
  created_at: datetime
  updated_at: datetime

class PhotoBOQLinkCreateRequest(BaseModel):
  progress_claim_id: UUID
  site_photo_id: UUID
  boq_item_id: UUID

  note: str | None = Field(
    default=None,
    max_length=5000,
  )

class PhotoBOQLinkResponse(BaseModel):
  model_config = ConfigDict(
    from_attributes=True,
  )

  id: UUID
  organization_id: UUID
  project_id: UUID
  progress_claim_id: UUID
  site_photo_id: UUID
  boq_item_id: UUID
  note: str | None
  created_by: UUID | None
  created_at: datetime
  updated_at: datetime