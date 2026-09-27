from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from datetime import date
from decimal import Decimal

class CashFlowSettingsUpdateRequest(BaseModel):
  procurement_payment_days: int | None = Field(default=None, ge=0, le=180)
  subcontractor_payment_days: int | None = Field(default=None, ge=0, le=180)
  client_collection_days: int | None = Field(default=None, ge=0, le=180)
  labour_lookback_days: int | None = Field(default=None, ge=7, le=180)

class CashFlowSettingsResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  procurement_payment_days: int
  subcontractor_payment_days: int
  client_collection_days: int
  labour_lookback_days: int

class CashFlowLineItemResponse(BaseModel):
  event_date: date
  category: str
  direction: str
  amount: Decimal
  description: str
  is_estimated_timing: bool
  is_overdue: bool

class WeeklyBucketResponse(BaseModel):
  week_start: date
  week_end: date
  total_inflow: Decimal
  total_outflow: Decimal
  net_change: Decimal
  cumulative_net: Decimal
  projected_balance: Decimal | None

class HorizonSummaryResponse(BaseModel):
  days: int
  cumulative_net: Decimal
  projected_balance: Decimal | None

class CashFlowForecastResponse(BaseModel):
  as_of_date: date
  horizon_days: int
  currency: str
  starting_cash_balance: Decimal | None
  weekly_buckets: list[WeeklyBucketResponse]
  summaries: dict[int, HorizonSummaryResponse]
  line_items: list[CashFlowLineItemResponse]
  assumptions: CashFlowSettingsResponse
  labour_daily_run_rate: Decimal
  limitations: list[str]