from __future__ import annotations
from decimal import Decimal
from datetime import date
from uuid import UUID
from app.modules.material_stock.models import MaterialIssueType
from pydantic import BaseModel, ConfigDict, Field

class MaterialIssueCreateRequest(BaseModel):
  material_name: str = Field(min_length=1, max_length=200)
  unit: str = Field(min_length=1, max_length=50)
  quantity: Decimal = Field(gt=0)
  issue_type: MaterialIssueType
  issued_to: str | None = Field(default=None, max_length=200)
  issue_date: date
  notes: str | None = None

class MaterialIssueResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  material_name: str
  unit: str
  quantity: Decimal
  issue_type: MaterialIssueType
  issued_to: str | None
  issue_date: date
  notes: str | None

class MaterialStockLineResponse(BaseModel):
  material_name: str
  unit: str
  total_received: Decimal
  total_issued: Decimal
  total_wastage: Decimal
  balance: Decimal
  wastage_percentage: float | None
  estimated_wastage_cost: Decimal | None

class MaterialStockReconciliationResponse(BaseModel):
  project_id: UUID
  lines: list[MaterialStockLineResponse]
  currency: str