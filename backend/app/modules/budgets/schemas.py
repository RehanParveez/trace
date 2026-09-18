from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class BudgetCategoryInput(BaseModel):
  name: str = Field(min_length=1, max_length=200)
  allocated_amount: Decimal = Field(ge=0)

class BudgetSaveRequest(BaseModel):
  project_id: UUID
  approved_amount: Decimal = Field(ge=0)
  currency: str | None = Field(
    default=None,
    min_length=3,
    max_length=3,
    description="Omit to use the organization's operating currency. If provided, it must match it.",
  )
  notes: str | None = None
  categories: list[BudgetCategoryInput] = Field(default_factory=list)
  version: int | None = Field(
    default=None,
    description="Required when updating an existing budget; omit when creating the first budget for a project.",
  )

class BudgetCategoryResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  name: str
  allocated_amount: Decimal

class BudgetResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  project_id: UUID
  approved_amount: Decimal
  currency: str
  notes: str | None
  version: int
  categories: list[BudgetCategoryResponse] = Field(default_factory=list)
  created_at: datetime
  updated_at: datetime

class BudgetOrganizationSummaryResponse(BaseModel):
  total_approved_amount: Decimal
  budget_count: int
  currency: str = "PKR"
  
class BudgetProjectSummaryResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  project_id: UUID
  approved_amount: Decimal
  currency: str