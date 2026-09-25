from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field, model_validator
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from app.modules.change_orders.models import ChangeOrderStatus, ChangeOrderType

class ChangeOrderLineItemInput(BaseModel):
  description: str = Field(min_length=1, max_length=300)
  unit: str = Field(min_length=1, max_length=50)
  boq_item_id: UUID | None = None
  quantity: Decimal
  unit_rate: Decimal | None = Field(default=None, ge=0)

  @model_validator(mode="after")
  def _validate_shape(self) -> "ChangeOrderLineItemInput":
    if self.boq_item_id is None:
      if self.unit_rate is None:
        raise ValueError("unit_rate is required for a brand-new line item.")
      if self.quantity <= 0:
        raise ValueError("quantity must be positive for a brand-new line item.")
    else:
      if self.quantity == 0:
        raise ValueError("quantity delta must not be zero for an adjustment to an existing item.")
    return self

class ChangeOrderCreateRequest(BaseModel):
  project_id: UUID
  boq_version_id: UUID
  change_type: ChangeOrderType
  title: str = Field(min_length=1, max_length=300)
  description: str | None = None
  client_reference: str | None = Field(default=None, max_length=100)
  line_items: list[ChangeOrderLineItemInput] = Field(min_length=1)

class ChangeOrderApproveRequest(BaseModel):
  version: int

class ChangeOrderRejectRequest(BaseModel):
  version: int
  reason: str = Field(min_length=1, max_length=500)

class ChangeOrderCancelRequest(BaseModel):
  version: int

class ChangeOrderLineItemResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  description: str
  unit: str
  boq_item_id: UUID | None
  quantity: Decimal
  unit_rate: Decimal | None
  realized_value_impact: Decimal | None
  created_boq_item_id: UUID | None

class ChangeOrderResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  project_id: UUID
  boq_version_id: UUID
  change_order_number: int
  change_type: ChangeOrderType
  status: ChangeOrderStatus
  title: str
  description: str | None
  client_reference: str | None
  value_impact: Decimal
  currency: str
  approved_at: datetime | None
  rejected_at: datetime | None
  rejection_reason: str | None
  version: int
  created_at: datetime

class ChangeOrderDetailResponse(ChangeOrderResponse):
  line_items: list[ChangeOrderLineItemResponse] = Field(default_factory=list)

class ProjectChangeOrderSummaryResponse(BaseModel):
  project_id: UUID
  approved_count: int
  approved_net_value_impact: Decimal
  draft_count: int
  currency: str