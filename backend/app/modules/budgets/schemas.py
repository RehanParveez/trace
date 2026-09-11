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
  currency: str = Field(default="PKR", min_length=3, max_length=3)
  notes: str | None = None
  categories: list[BudgetCategoryInput] = Field(default_factory=list)

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
  categories: list[BudgetCategoryResponse] = Field(default_factory=list)
  created_at: datetime
  updated_at: datetime

class BudgetOrganizationSummaryResponse(BaseModel):
  total_approved_amount: Decimal
  budget_count: int
  currency: str = "PKR"