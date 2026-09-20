from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.modules.subscriptions.models import BillingInterval, SubscriptionStatus, UsagePeriod, InvoiceStatus, PaymentStatus

class PlanResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  name: str
  slug: str
  description: str | None
  price_monthly: Decimal
  price_yearly: Decimal
  currency: str
  price_monthly_original: Decimal | None = None
  price_yearly_original: Decimal | None = None
  offer_label: str | None = None
  offer_ends_at: datetime | None = None
  version: int
  trial_days: int
  sort_order: int
  is_default: bool
  is_active: bool
  is_public: bool
  features: dict
  quotas: dict
  limit_policy: dict

class SubscriptionResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  organization_id: UUID
  plan_id: UUID
  status: SubscriptionStatus
  billing_interval: BillingInterval
  quantity: int
  started_at: datetime
  current_period_start: datetime
  current_period_end: datetime
  trial_ends_at: datetime | None
  cancelled_at: datetime | None
  cancel_at_period_end: bool
  grace_period_ends_at: datetime | None = None
  cancellation_reason: str | None = None
  last_payment_at: datetime | None = None
  next_billing_at: datetime | None = None
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
  quantity: int = Field(default=1, ge=1)

class CancelSubscriptionRequest(BaseModel):
  cancel_at_period_end: bool = True
  reason: str | None = None
  feedback: str | None = None
  
class IncrementUsageRequest(BaseModel):
  metric: str = Field(min_length=1, max_length=100)
  quantity: int = Field(gt=0)
  
class SubscriptionListResponse(BaseModel):
  items: list[SubscriptionResponse]
  total: int
  page: int
  page_size: int
  
class CreateInvoiceRequest(BaseModel):
  pass
  
class InvoiceResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  organization_id: UUID
  subscription_id: UUID | None
  status: InvoiceStatus
  currency: str
  subtotal: Decimal
  tax: Decimal
  total: Decimal
  amount_paid: Decimal
  amount_due: Decimal
  period_start: datetime
  period_end: datetime
  due_date: datetime | None
  paid_at: datetime | None
  provider: str
  line_items: list

class PaymentResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: UUID
  organization_id: UUID
  invoice_id: UUID | None
  status: PaymentStatus
  amount: Decimal
  currency: str
  provider: str
  paid_at: datetime | None
  failure_reason: str | None