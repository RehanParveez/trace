from __future__ import annotations
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.modules.subscriptions.models import BillingInterval, SubscriptionStatus, UsagePeriod

class PlanResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  name: str
  slug: str
  description: str | None
  price_monthly: float
  price_yearly: float
  currency: str
  is_active: bool
  is_public: bool
  features: dict
  quotas: dict

class SubscriptionResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  organization_id: UUID
  plan_id: UUID
  status: SubscriptionStatus
  billing_interval: BillingInterval
  started_at: datetime
  current_period_start: datetime
  current_period_end: datetime
  trial_ends_at: datetime | None
  cancelled_at: datetime | None
  cancel_at_period_end: bool
  provider: str

class SubscriptionSummaryResponse(BaseModel):
  subscription: SubscriptionResponse
  plan: PlanResponse

class UsageCounterResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  organization_id: UUID
  metric: str
  period: UsagePeriod
  period_start: datetime
  period_end: datetime
  quantity: int

class UsageMetricResponse(BaseModel):
  metric: str
  used: int
  limit: int | None
  remaining: int | None
  percentage: float | None

class UsageResponse(BaseModel):
  period_start: datetime
  period_end: datetime
  metrics: list[UsageMetricResponse]

class ChangePlanRequest(BaseModel):
  plan_id: UUID
  billing_interval: BillingInterval = BillingInterval.MONTHLY

class CancelSubscriptionRequest(BaseModel):
  cancel_at_period_end: bool = True

class IncrementUsageRequest(BaseModel):
  metric: str = Field(min_length=1, max_length=100)
  quantity: int = Field(gt=0)