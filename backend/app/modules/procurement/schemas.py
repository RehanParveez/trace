from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from decimal import Decimal
from datetime import date, datetime
from app.modules.procurement.models import ProcurementStatus

class ProcurementCreateRequest(BaseModel):
  project_id: UUID
  material_name: str = Field(min_length=1, max_length=300)
  quantity: Decimal = Field(gt=0)
  unit: str = Field(min_length=1, max_length=50)
  estimated_amount: Decimal | None = Field(default=None, ge=0)
  needed_by_date: date | None = None
  notes: str | None = None

class ProcurementStatusUpdateRequest(BaseModel):
  status: ProcurementStatus

class ProcurementResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  project_id: UUID
  material_name: str
  quantity: Decimal
  unit: str
  estimated_amount: Decimal | None
  status: ProcurementStatus
  needed_by_date: date | None
  notes: str | None
  requested_by: UUID | None
  created_at: datetime
  updated_at: datetime