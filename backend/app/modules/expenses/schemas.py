from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from app.modules.expenses.models import ExpenseStatus

class ExpenseCreateRequest(BaseModel):
  project_id: UUID
  category: str = Field(min_length=1, max_length=150)
  description: str | None = None
  amount: Decimal = Field(gt=0)
  expense_date: date

class ExpenseReviewRequest(BaseModel):
  note: str | None = None

class ExpenseResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  project_id: UUID
  category: str
  description: str | None
  amount: Decimal
  expense_date: date
  status: ExpenseStatus
  submitted_by: UUID | None
  reviewed_by: UUID | None
  review_note: str | None
  created_at: datetime
  updated_at: datetime
  
class ExpenseOrganizationSummaryResponse(BaseModel):
  total_approved_amount: Decimal
  expense_count: int